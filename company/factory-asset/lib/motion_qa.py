from __future__ import annotations

import hashlib
import json
import math
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

class MotionQAError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f'{code}: {message}')
        self.code = code


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def _mp4_magic(path: Path) -> bool:
    data=path.read_bytes()[:32]
    return len(data)>=12 and data[4:8]==b'ftyp'


def _run_json(binary: str|Path, args: list[str]) -> dict[str, Any]:
    proc=subprocess.run([str(binary),*args],capture_output=True,text=True,timeout=60)
    if proc.returncode!=0:
        raise MotionQAError('PROBE_FAILED',(proc.stderr or proc.stdout or 'probe failed').strip()[:1000])
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise MotionQAError('PROBE_JSON_INVALID',proc.stdout[:500]) from exc


def _fps(value: str|None) -> float|None:
    if not value or value in {'0/0','N/A'}: return None
    try: return float(Fraction(value))
    except Exception: return None


def probe_video(path: str|Path, *, ffprobe_path: str|Path) -> dict[str,Any]:
    p=Path(path)
    if not p.is_file(): raise MotionQAError('FILE_NOT_FOUND',str(p))
    data=_run_json(ffprobe_path,['-v','error','-show_streams','-show_format','-of','json',str(p)])
    streams=data.get('streams',[])
    videos=[s for s in streams if s.get('codec_type')=='video']
    audios=[s for s in streams if s.get('codec_type')=='audio']
    fmt=data.get('format',{})
    return {
      'magic_mp4':_mp4_magic(p),
      'sha256':sha256_file(p),'bytes':p.stat().st_size,
      'video_stream_count':len(videos),'audio_stream_count':len(audios),
      'video':videos[0] if len(videos)==1 else None,
      'format':fmt,
      'raw':data,
    }


def _frame_indices(frame_count:int)->list[int]:
    if frame_count<5: return sorted(set(range(frame_count)))
    return sorted(set([0,frame_count//4,frame_count//2,(frame_count*3)//4,frame_count-1]))


def sample_frames(path:str|Path, *, ffmpeg_path:str|Path, frame_count:int, fps:float) -> dict[str,Any]:
    indices=_frame_indices(frame_count)
    if fps <= 0:
        raise MotionQAError('INVALID_SAMPLE_FPS',str(fps))
    with tempfile.TemporaryDirectory(prefix='fa042-samples-') as td:
        arrays=[]; sample_rows=[]
        for ordinal,idx in enumerate(indices):
            out=Path(td)/f'frame-{ordinal:03d}.png'
            seconds=idx/fps
            proc=subprocess.run([str(ffmpeg_path),'-v','error','-i',str(path),'-ss',f'{seconds:.9f}','-frames:v','1',str(out)],capture_output=True,text=True,timeout=60)
            if proc.returncode!=0 or not out.is_file():
                raise MotionQAError('FRAME_SAMPLE_DECODE_FAILED',(proc.stderr or proc.stdout or f'frame {idx} missing').strip()[:1000])
            with Image.open(out) as im:
                im.load(); rgb=im.convert('RGB').resize((64,64),Image.Resampling.BILINEAR)
                arr=np.asarray(rgb,dtype=np.float32)
            std=float(arr.std()); mean=float(arr.mean())
            percept=np.rint(arr/8.0).astype(np.uint8)
            phash=hashlib.sha256(percept.tobytes()).hexdigest()
            arrays.append(arr)
            sample_rows.append({'frame':idx,'timestamp_seconds':round(seconds,9),'stddev':round(std,6),'mean':round(mean,6),'perceptual_sha256':phash})
        diffs=[]
        for i in range(len(arrays)):
            for j in range(i+1,len(arrays)):
                diffs.append(float(np.mean(np.abs(arrays[i]-arrays[j]))))
        blank_count=sum(1 for row in sample_rows if row['stddev']<2.0)
        max_mae=max(diffs) if diffs else 0.0
        distinct=len({row['perceptual_sha256'] for row in sample_rows})
        return {'sample_indices':indices,'sample_count':len(sample_rows),'samples':sample_rows,'blank_sample_count':blank_count,'all_samples_blank':blank_count==len(sample_rows),'distinct_perceptual_samples':distinct,'max_pairwise_mae':round(max_mae,6),'frozen':distinct<=1 or max_mae<0.5}


def evaluate_motion(*, probe:dict[str,Any], visual:dict[str,Any]|None, expected:dict[str,Any]) -> dict[str,Any]:
    failures=[]
    if expected['container']=='MP4' and not probe.get('magic_mp4'): failures.append('CONTAINER_MAGIC_MISMATCH')
    if probe.get('video_stream_count')!=1: failures.append('VIDEO_STREAM_COUNT_MISMATCH')
    v=probe.get('video') or {}
    codec_map={'H264':'h264','H265':'hevc','PRORES_422':'prores'}
    if v.get('codec_name')!=codec_map.get(expected['codec']): failures.append('CODEC_MISMATCH')
    if v.get('pix_fmt')!=expected['pixel_format'].lower(): failures.append('PIXEL_FORMAT_MISMATCH')
    if v.get('width')!=expected['width'] or v.get('height')!=expected['height']: failures.append('DIMENSIONS_MISMATCH')
    actual_fps=_fps(v.get('avg_frame_rate') or v.get('r_frame_rate'))
    if actual_fps is None or abs(actual_fps-float(expected['fps']))>1e-6: failures.append('FPS_MISMATCH')
    try: actual_frames=int(v.get('nb_frames'))
    except Exception: actual_frames=None
    if actual_frames!=expected['frame_count']: failures.append('FRAME_COUNT_MISMATCH')
    duration_raw=v.get('duration') or probe.get('format',{}).get('duration')
    try: actual_duration=float(duration_raw)
    except Exception: actual_duration=None
    if actual_duration is None or abs(actual_duration-float(expected['duration_seconds']))>0.001: failures.append('DURATION_MISMATCH')
    if expected['audio_policy']=='NONE' and probe.get('audio_stream_count')!=0: failures.append('UNEXPECTED_AUDIO_STREAM')
    if visual is None:
        failures.append('VISUAL_SAMPLING_MISSING')
    else:
        if visual.get('all_samples_blank'): failures.append('BLANK_RENDER')
        if visual.get('frozen'): failures.append('FROZEN_RENDER')
        if visual.get('sample_count')!=len(_frame_indices(expected['frame_count'])): failures.append('VISUAL_SAMPLE_COUNT_MISMATCH')
    return {'schema':'die.factory-asset.motion-qa.v1','result':'PASS' if not failures else 'FAIL','failures':failures,'technical':{'container_magic_mp4':probe.get('magic_mp4'),'codec':v.get('codec_name'),'pixel_format':v.get('pix_fmt'),'width':v.get('width'),'height':v.get('height'),'fps':actual_fps,'frame_count':actual_frames,'duration_seconds':actual_duration,'video_stream_count':probe.get('video_stream_count'),'audio_stream_count':probe.get('audio_stream_count'),'sha256':probe.get('sha256'),'bytes':probe.get('bytes')},'visual':visual}


def inspect_motion(path:str|Path, *, ffprobe_path:str|Path, ffmpeg_path:str|Path, expected:dict[str,Any]) -> dict[str,Any]:
    try:
        probe=probe_video(path,ffprobe_path=ffprobe_path)
    except MotionQAError as exc:
        return {'schema':'die.factory-asset.motion-qa.v1','result':'FAIL','failures':[exc.code],'error':str(exc),'technical':None,'visual':None}
    visual=None
    if probe.get('video_stream_count')==1:
        try: visual=sample_frames(path,ffmpeg_path=ffmpeg_path,frame_count=expected['frame_count'],fps=float(expected['fps']))
        except MotionQAError as exc:
            return {'schema':'die.factory-asset.motion-qa.v1','result':'FAIL','failures':[exc.code],'error':str(exc),'technical':probe,'visual':None}
    return evaluate_motion(probe=probe,visual=visual,expected=expected)


def marketplace_compatibility(*, marketplace_profile:dict[str,Any], qa_result:dict[str,Any], expected:dict[str,Any])->dict[str,Any]:
    if qa_result.get('result')!='PASS': return {'state':'INCOMPATIBLE','reason':'MOTION_QA_FAILED'}
    state=marketplace_profile.get('profile_state')
    if state!='EVIDENCE_PINNED': return {'state':'UNKNOWN','reason':f'PROFILE_STATE_{state or "UNKNOWN"}'}
    delivery=marketplace_profile.get('delivery',{})
    video=[str(x).upper() for x in delivery.get('video',[])]
    target=f"{expected['container']} {expected['codec']}".upper()
    if expected['container'].upper()=='MP4' and expected['codec'].upper()=='H264' and any('MP4' in x and 'H.264' in x.replace('H264','H.264') for x in video):
        return {'state':'COMPATIBLE','reason':'PINNED_PROFILE_MATCH'}
    if expected['container'].upper()=='MOV' and any('MOV' in x for x in video): return {'state':'COMPATIBLE','reason':'PINNED_PROFILE_MATCH'}
    return {'state':'UNKNOWN','reason':'NO_EXACT_PINNED_VIDEO_MATCH'}