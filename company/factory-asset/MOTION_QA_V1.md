# Motion QA v1

Task: `FA-042`
Status: implementation/acceptance surface for motion codec, container, frame and sampled visual integrity.

## Positive contract

The current FA-041 reference fixture must decode as:

- MP4 container magic;
- exactly one H.264 video stream;
- `yuv420p`;
- 1080x1080;
- 30 FPS;
- exactly 180 frames;
- exactly 6.000 seconds;
- no audio stream for `audio.policy = NONE`;
- five sampled frames decode successfully and demonstrate non-blank, non-frozen visual change.

## Negative controls

The inspector must fail closed on:

- mislabeled media whose extension claims MP4 but bytes are not a valid MP4;
- truncated media that retains enough metadata to probe but cannot decode the required sampled timeline;
- technically valid blank video;
- technically valid frozen video.

Metadata-only QA is insufficient: truncated media can preserve `moov` metadata, and blank/frozen renders can satisfy codec/container/frame/duration contracts while carrying no useful motion.

## Marketplace compatibility

Compatibility is projected only from `marketplace-delivery-profiles.v1.json`. A technically valid file is not enough to promote an `UNKNOWN` marketplace profile. Current FA-042 evidence marks the pinned Adobe Stock `MP4/H.264` route compatible; profiles lacking an exact current pinned match remain UNKNOWN.

## Runtime boundary

`company/factory-asset/bin/run_motion_qa.py` accepts explicit FFmpeg/FFprobe binary paths. Windows FA-042 uses the Remotion compositor binaries proven in FA-041; Linux may use native binaries without changing QA logic. The QA engine has no provider, credential, upload, publication or spend authority.