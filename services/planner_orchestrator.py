# services/planner_orchestrator.py
"""
High-level helper that runs:
1) scene planner -> plan
2) llm variant generation -> variants
3) storyboard thumbnails -> thumbnails (moviepy)
4) continuity check
5) export SRT/EDL
Returns a package with everything ready for the pipeline.
"""

from services.scene_planner import analyze_scene
from services.llm_variant import generate_variants
from services.storyboard_renderer import render_batch_thumbnails
from services.continuity_checker import check_continuity
from services.edl_exporter import export_srt, export_edl
from pathlib import Path
import uuid, os, json

ROOT = Path(".").resolve()
OUTROOT = ROOT / "static" / "planner_packages"
OUTROOT.mkdir(parents=True, exist_ok=True)

def make_package(script_text: str, characters: list = None, env: dict = None, style: str = "cinematic", n_variants: int = 2):
    # 1) plan
    plan = analyze_scene(script_text, env=env or {}, characters=characters or [])
    if not plan.get("ok"):
        return {"ok": False, "error":"planner_failed", "detail": plan}
    # 2) variants
    variants = generate_variants(plan, style=style, n=n_variants)
    # 3) thumbnails spec from storyboard frames
    frames = plan.get("storyboard_frames", [])
    specs = []
    for f in frames:
        specs.append({"text": f.get("thumb_hint"), "width":640, "height":360})
    thumbs = render_batch_thumbnails(specs)
    # 4) continuity
    cont = check_continuity(plan.get("shot_list", []))
    # 5) export srt/edl
    pkgid = uuid.uuid4().hex[:8]
    pkgdir = OUTROOT / pkgid
    pkgdir.mkdir(parents=True, exist_ok=True)
    srt_path = str(pkgdir / "out.srt")
    edl_path = str(pkgdir / "out.edl")
    export_srt(plan.get("shot_list", []), srt_path)
    export_edl(plan.get("shot_list", []), edl_path)
    # assemble package
    meta = {"plan": plan, "variants": variants, "thumbnails": thumbs.get("outs", []), "continuity": cont, "srt": srt_path, "edl": edl_path}
    (pkgdir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"ok": True, "package_id": pkgid, "meta": meta}
