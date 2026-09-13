from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "company/company-os/die-h01/engineering/marketplace_delivery_adapter.py"
SPEC = importlib.util.spec_from_file_location("marketplace_delivery_adapter", ADAPTER)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD  # type: ignore
SPEC.loader.exec_module(MOD)  # type: ignore

try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None  # type: ignore


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_svg(viewbox: str = "0 0 100 100") -> bytes:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}"><path d="M10 10 L90 10 L90 90 L10 90 Z" fill="#336699"/></svg>'.encode()


def _make_eps(bbox: str = "0 0 4000 4000") -> bytes:
    # bbox like "0 0 4000 4000"
    w, h = bbox.split()[-2:]
    return (
        b"%!PS-Adobe-3.0 EPSF-3.0\n"
        b"%%Creator: test\n"
        b"%%LanguageLevel: 2\n"
        b"%%DocumentData: Clean7Bit\n"
        b"%%HiResBoundingBox: 0 0 " + w.encode() + b" " + h.encode() + b"\n"
        + f"%%BoundingBox: {bbox}\n".encode()
        + b"%%EndComments\n"
        b"newpath 0 0 moveto 100 0 lineto 100 100 lineto 0 100 lineto closepath\n"
        b"0 0 1 setrgbcolor fill\n"
        b"showpage\n"
        b"%%EOF\n"
    )


def _make_jpg(path: Path, size=(2000, 2000), color=(200, 100, 50)) -> None:
    if Image is None:
        # fallback: write minimal jpeg header (not valid for PIL but for copy)
        path.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9")
        return
    img = Image.new("RGB", size, color)
    img.save(path, format="JPEG", quality=95, subsampling=0, optimize=False, progressive=False)


def _make_workspace(base: Path, preview_size=(2000, 2000), eps_bbox="0 0 4000 4000", svg_viewbox="0 0 100 100") -> Path:
    ws = base / "workspace"
    post = ws / "postproduction"
    post.mkdir(parents=True, exist_ok=True)
    # SVGs
    (post / "optimized-master.svg").write_bytes(_make_svg(svg_viewbox))
    (post / "canonical-master.svg").write_bytes(_make_svg(svg_viewbox))
    # EPS
    (post / "master.eps").write_bytes(_make_eps(eps_bbox))
    # preview jpg
    _make_jpg(post / "preview.jpg", size=preview_size)
    # Also need master.pdf placeholder? not required for delivery
    # metadata.json at workspace root
    meta = {
        "title": "Test Vector Asset",
        "description": "A test isolated editable vector for delivery.",
        "keywords": ["test", "vector", "delivery"],
        "ai_generated": True,
        "ai_disclosure": "GENERATIVE_AI",
        "semantic_asset_id": "SEM-TEST-001",
    }
    # compute metadata_sha if adapter expects
    meta["metadata_sha256"] = _sha_bytes(json.dumps({k: meta.get(k) for k in ("title", "description", "keywords", "ai_generated", "ai_disclosure", "semantic_asset_id")}, sort_keys=True, separators=(",", ":")).encode())
    (ws / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    # rights-signal.json at root
    rights = {"result": "PASS", "source": "test"}
    (ws / "rights-signal.json").write_text(json.dumps(rights, indent=2) + "\n", encoding="utf-8")
    return ws


class H01134MarketplaceDeliveryAdapterV1(unittest.TestCase):
    def test_all_6_profiles_build(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _make_workspace(Path(td))
            out = Path(td) / "out"
            results = MOD.build_all_marketplace_packages(ws, out, founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertEqual(set(results.keys()), {"ADOBE", "VECTEEZY", "123RF", "DREAMSTIME", "VECTORSTOCK", "MOTIONELEMENTS"})
            for mp, manifest in results.items():
                self.assertEqual(manifest["marketplace"], mp)
                self.assertIn("artifacts", manifest)
                self.assertIn("compatibility", manifest)
                self.assertTrue((Path(manifest["output_dir"]) / "files").is_dir())
                self.assertTrue((Path(manifest["output_dir"]) / "manifest.json").is_file())
                self.assertTrue((Path(manifest["output_dir"]) / "delivery.receipt.json").is_file())
                # each manifest must have deterministic flag
                self.assertTrue(manifest["deterministic"])
                self.assertEqual(manifest["semantic_identity_effect"], "NONE")

    def test_action_lock_none(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _make_workspace(Path(td))
            out = Path(td) / "out"
            results = MOD.build_all_marketplace_packages(ws, out, founder_qc="PASS", rights_signal={"result": "PASS"})
            for mp, manifest in results.items():
                for key in ("login_action", "upload_action", "submission_action", "publication_action", "spend_action"):
                    self.assertEqual(manifest[key], "NONE", f"{mp} {key}")
                # receipt also
                receipt = json.loads((Path(manifest["output_dir"]) / "delivery.receipt.json").read_text(encoding="utf-8"))
                for key in ("login_action", "upload_action", "submission_action", "publication_action", "spend_action"):
                    self.assertEqual(receipt[key], "NONE")

    def test_eligibility_gate(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _make_workspace(Path(td))
            out = Path(td) / "out"
            # PASS requires all three PASS
            m_pass = MOD.build_marketplace_package(ws, "ADOBE", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertTrue(m_pass["submission_eligible"])
            self.assertEqual(m_pass["compatibility"]["result"], "PASS")
            # founder fail
            m_fail_founder = MOD.build_marketplace_package(ws, "ADOBE", Path(td)/"out2", founder_qc="FAIL", rights_signal={"result": "PASS"})
            self.assertFalse(m_fail_founder["submission_eligible"])
            # rights fail
            m_fail_rights = MOD.build_marketplace_package(ws, "ADOBE", Path(td)/"out3", founder_qc="PASS", rights_signal={"result": "BLOCK"})
            self.assertFalse(m_fail_rights["submission_eligible"])
            # compatibility fail: use small JPG for 123RF
            ws2 = _make_workspace(Path(td)/"ws2", preview_size=(500, 500))
            m_fail_compat = MOD.build_marketplace_package(ws2, "123RF", Path(td)/"out4", founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertFalse(m_fail_compat["submission_eligible"])
            self.assertEqual(m_fail_compat["compatibility"]["status"], "REVIEW_REQUIRED")

    def test_idempotency_and_collision(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _make_workspace(Path(td))
            out = Path(td) / "out"
            m1 = MOD.build_marketplace_package(ws, "ADOBE", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            # second run same bytes should be idempotent (no error, same sha)
            m2 = MOD.build_marketplace_package(ws, "ADOBE", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertEqual(m1["manifest_file_sha256"], m2["manifest_file_sha256"])
            self.assertEqual(m1["manifest_content_sha256"], m2["manifest_content_sha256"])
            # check file content unchanged
            manifest_path = Path(m1["manifest_path"])
            self.assertEqual(_sha_bytes(manifest_path.read_bytes()), m1["manifest_file_sha256"])
            # collision: tamper existing delivery file with different bytes, rerun should fail closed
            adobe_file = Path(out / "adobe" / "files" / "asset.svg")
            adobe_file.write_text("<svg>tampered</svg>", encoding="utf-8")
            with self.assertRaises(MOD.MarketplaceDeliveryError) as ctx:
                MOD.build_marketplace_package(ws, "ADOBE", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertEqual(ctx.exception.code, "OUTPUT_COLLISION")

    def test_adobe_16mp_delivery_svg(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _make_workspace(Path(td), svg_viewbox="0 0 100 100")
            # ensure source preserved: read original
            src = ws / "postproduction" / "optimized-master.svg"
            src_hash_before = _sha_bytes(src.read_bytes())
            src_text_before = src.read_text(encoding="utf-8")
            out = Path(td) / "out"
            m = MOD.build_marketplace_package(ws, "ADOBE", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            delivery = Path(out / "adobe" / "files" / "asset.svg")
            self.assertTrue(delivery.is_file())
            # source not mutated
            self.assertEqual(_sha_bytes(src.read_bytes()), src_hash_before)
            self.assertEqual(src.read_text(encoding="utf-8"), src_text_before)
            # viewBox preserved exactly
            delivery_text = delivery.read_text(encoding="utf-8")
            self.assertIn('viewBox="0 0 100 100"', delivery_text)
            # width/height explicit and area ~16M within 15-65MP
            wm = re.search(r'width="([0-9.]+)"', delivery_text)
            hm = re.search(r'height="([0-9.]+)"', delivery_text)
            self.assertIsNotNone(wm)
            self.assertIsNotNone(hm)
            w = float(wm.group(1)); h = float(hm.group(1))
            area = w * h
            self.assertGreaterEqual(area, 15_000_000)
            self.assertLessEqual(area, 65_000_000)
            # should be ~16M (within 10% tolerance)
            self.assertAlmostEqual(area, 16_000_000, delta=1_000_000)
            # hashes recorded
            art = next(a for a in m["artifacts"] if a["target"] == "asset.svg")
            self.assertEqual(art["source_sha256"], src_hash_before)
            self.assertNotEqual(art["sha256"], src_hash_before)
            self.assertEqual(art["transformation"], "EXPLICIT_ARTBOARD_16MP_PRESERVE_VIEWBOX")
            self.assertEqual(art["semantic_identity_effect"], "NONE")
            self.assertEqual(m["semantic_identity_effect"], "NONE")
            # compatibility PASS
            self.assertEqual(m["compatibility"]["status"], "COMPATIBLE")
            # fallback test: remove optimized, use canonical
            ws2 = _make_workspace(Path(td)/"ws2b", svg_viewbox="0 0 50 200")
            (ws2 / "postproduction" / "optimized-master.svg").unlink()
            m_fallback = MOD.build_marketplace_package(ws2, "ADOBE", Path(td)/"out_fallback", founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertEqual(m_fallback["compatibility"]["status"], "COMPATIBLE")

    def test_vecteezy_4_25mp_check(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _make_workspace(Path(td), eps_bbox="0 0 4000 4000")
            out = Path(td) / "out"
            m = MOD.build_marketplace_package(ws, "VECTEEZY", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertEqual(m["compatibility"]["status"], "COMPATIBLE")
            # EPS declared
            self.assertEqual(m["eps_compatibility"], "ILLUSTRATOR_10_COMPATIBLE_TARGET")
            self.assertFalse(m["native_illustrator_save_certified"])
            self.assertIn("ILLUSTRATOR_10_STRUCTURAL_TARGET_ONLY", m["compatibility"]["notes"])
            # out of range -> REVIEW_REQUIRED
            ws_small = _make_workspace(Path(td)/"ws_small", eps_bbox="0 0 100 100")
            m_small = MOD.build_marketplace_package(ws_small, "VECTEEZY", Path(td)/"out_small", founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertEqual(m_small["compatibility"]["status"], "REVIEW_REQUIRED")
            self.assertIn("VECTEEZY_EPS_ARTBOARD_OUTSIDE_RANGE", m_small["compatibility"]["blockers"])
            ws_large = _make_workspace(Path(td)/"ws_large", eps_bbox="0 0 6000 6000")
            m_large = MOD.build_marketplace_package(ws_large, "VECTEEZY", Path(td)/"out_large", founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertEqual(m_large["compatibility"]["status"], "REVIEW_REQUIRED")
            # check files exist: asset.eps + preview.jpg
            self.assertTrue((Path(out / "vecteezy" / "files" / "asset.eps")).is_file())
            self.assertTrue((Path(out / "vecteezy" / "files" / "preview.jpg")).is_file())

    def test_same_basename(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _make_workspace(Path(td), preview_size=(2000, 2000))
            out = Path(td) / "out"
            # 123RF same basename asset.eps + asset.jpg
            m123 = MOD.build_marketplace_package(ws, "123RF", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertTrue(m123["same_basename_required"])
            self.assertTrue(m123["same_basename_actual"])
            self.assertEqual(set(m123["same_basename_stems"]), {"asset"})
            # VECTORSTOCK same basename
            mvs = MOD.build_marketplace_package(ws, "VECTORSTOCK", Path(td)/"out_vs", founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertTrue(mvs["same_basename_required"])
            self.assertTrue(mvs["same_basename_actual"])
            # MOTIONELEMENTS
            mme = MOD.build_marketplace_package(ws, "MOTIONELEMENTS", Path(td)/"out_me", founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertTrue(mme["same_basename_required"])
            self.assertTrue(mme["same_basename_actual"])
            # DREAMSTIME same basename (asset.jpg + asset.svg)
            mdt = MOD.build_marketplace_package(ws, "DREAMSTIME", Path(td)/"out_dt", founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertTrue(mdt["same_basename_required"])
            self.assertTrue(mdt["same_basename_actual"])
            # 123RF with missing basename: should block if we manually break
            # Verify targets are asset.* for these marketplaces
            for mp in ("123RF", "VECTORSTOCK", "MOTIONELEMENTS", "DREAMSTIME"):
                manifest = MOD.build_marketplace_package(ws, mp, Path(td)/f"out_check_{mp.lower()}", founder_qc="PASS", rights_signal={"result": "PASS"})
                targets = [a["target"] for a in manifest["artifacts"]]
                stems = {Path(t).stem for t in targets}
                self.assertEqual(stems, {"asset"}, f"{mp} stems {stems}")

    def test_vectorstock_zip_members(self):
        with tempfile.TemporaryDirectory() as td:
            # preview large to trigger normalization
            ws = _make_workspace(Path(td), preview_size=(3500, 2500))
            out = Path(td) / "out"
            m = MOD.build_marketplace_package(ws, "VECTORSTOCK", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            # preview normalized
            preview = Path(out / "vectorstock" / "files" / "asset.jpg")
            self.assertTrue(preview.is_file())
            if Image is not None:
                with Image.open(preview) as im:
                    self.assertLessEqual(max(im.size), 3000)
                    self.assertGreaterEqual(min(im.size), 1000)
                    self.assertEqual(im.mode, "RGB")
            # ZIP contains EPS only deterministically
            zip_path = Path(out / "vectorstock" / "files" / "asset.zip")
            self.assertTrue(zip_path.is_file())
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = sorted(zf.namelist())
                self.assertEqual(names, ["asset.eps"])
                # deterministic timestamp
                for info in zf.infolist():
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                    self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)
            # ZIP hash stable
            h1 = _sha_bytes(zip_path.read_bytes())
            # rerun idempotent
            m2 = MOD.build_marketplace_package(ws, "VECTORSTOCK", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            h2 = _sha_bytes(zip_path.read_bytes())
            self.assertEqual(h1, h2)
            self.assertEqual(m["package_zip"]["sha256"], h1)
            self.assertEqual(m["package_zip"]["contains"], ["asset.eps"])

    def test_motionelements_zip_members(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _make_workspace(Path(td), preview_size=(2000, 2000))
            out = Path(td) / "out"
            m = MOD.build_marketplace_package(ws, "MOTIONELEMENTS", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            zip_path = Path(out / "motionelements" / "files" / "asset.zip")
            self.assertTrue(zip_path.is_file())
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = sorted(zf.namelist())
                self.assertEqual(names, ["asset.eps", "asset.jpg"])
                # same basename inside ZIP
                stems = {Path(n).stem for n in names}
                self.assertEqual(stems, {"asset"})
                for info in zf.infolist():
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
            # deterministic
            h1 = _sha_bytes(zip_path.read_bytes())
            m2 = MOD.build_marketplace_package(ws, "MOTIONELEMENTS", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            h2 = _sha_bytes(zip_path.read_bytes())
            self.assertEqual(h1, h2)
            self.assertEqual(sorted(m["package_zip"]["contains"]), ["asset.eps", "asset.jpg"])
            # same basename required
            self.assertTrue(m["same_basename_actual"])

    def test_ai_disclosure_from_workspace_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _make_workspace(Path(td))
            out = Path(td) / "out"
            m = MOD.build_marketplace_package(ws, "ADOBE", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            self.assertEqual(m["ai_generated"], True)
            self.assertEqual(m["ai_disclosure"], "GENERATIVE_AI")
            self.assertEqual(m["sidecar_metadata"]["content"]["ai_disclosure"], "GENERATIVE_AI")
            self.assertEqual(m["sidecar_metadata"]["content"]["ai_generated"], True)

    def test_manifest_self_hash_non_circular(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _make_workspace(Path(td))
            out = Path(td) / "out"
            m = MOD.build_marketplace_package(ws, "ADOBE", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            manifest_path = Path(m["manifest_path"])
            receipt_path = Path(m["receipt_path"]) if "receipt_path" in m else manifest_path.parent / "delivery.receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            # manifest file hash must equal receipt manifest_file_sha256 / manifest_sha256
            file_sha = _sha_bytes(manifest_path.read_bytes())
            self.assertEqual(file_sha, receipt["manifest_file_sha256"])
            self.assertEqual(file_sha, receipt["manifest_sha256"])
            self.assertEqual(file_sha, m["manifest_file_sha256"])
            # manifest file should not contain an invalid self-hash: if it contains manifest_sha256 it must equal file hash
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            if "manifest_sha256" in manifest_data:
                self.assertEqual(manifest_data["manifest_sha256"], file_sha)
            if "manifest_file_sha256" in manifest_data:
                self.assertEqual(manifest_data["manifest_file_sha256"], file_sha)
            # receipt content hash is hash of manifest content (without receipt)
            # ensure it's stable across runs
            m2 = MOD.build_marketplace_package(ws, "ADOBE", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            receipt2 = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["manifest_file_sha256"], receipt2["manifest_file_sha256"])
            self.assertEqual(receipt["manifest_content_sha256"], receipt2["manifest_content_sha256"])

    def test_dreamstime_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _make_workspace(Path(td))
            # remove optimized svg to force fallback to eps for DREAMSTIME
            (ws / "postproduction" / "optimized-master.svg").unlink()
            out = Path(td) / "out"
            m = MOD.build_marketplace_package(ws, "DREAMSTIME", out, founder_qc="PASS", rights_signal={"result": "PASS"})
            # should have used fallback EPS for vector role
            targets = {a["target"]: a for a in m["artifacts"]}
            self.assertIn("asset.jpg", targets)
            self.assertIn("asset.eps", targets)
            self.assertEqual(targets["asset.eps"]["format"], "EPS")
            self.assertEqual(targets["asset.eps"]["transformation"], "COPY_EXACT")
            self.assertTrue((Path(out / "dreamstime" / "files" / "asset.eps")).is_file())

    def test_cli(self):
        with tempfile.TemporaryDirectory() as td:
            import subprocess
            ws = _make_workspace(Path(td))
            out = Path(td) / "out_cli"
            cmd = [sys.executable, str(ADAPTER), "--workspace", str(ws), "--output", str(out), "--marketplace", "ADOBE", "--founder-qc", "PASS", "--rights-result", "PASS"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["marketplace"], "ADOBE")
            self.assertTrue(Path(out / "adobe" / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
