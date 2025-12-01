# services/storyboard_renderer.py
"""
Quick storyboard thumbnail generator.
- Preferred: headless Blender renders (if you supply a .blend and camera presets)
- Fallback: MoviePy composite using character images / background or plain text placeholder
Functions:
- render_thumbnail_blender(job) -> path
- render_thumbnail_moviepy(spec) -> path
- render_batch_thumbnails(frames_list, out_dir) -> list(paths)
"""

from pathlib import Path
import json, os, tempfile, subprocess, uuid

ROOT = Path(".").resolve()
OUT = ROOT / "static" / "storyboards"
OUT.mkdir(parents=True, exist_ok=True)

def _id(): return uuid.uuid4().hex[:8]

def render_thumbnail_moviepy(spec: dict, out_path: str | None = None) -> dict:
    """
    spec example:
    {
      "width": 640, "height":360,
      "background": "static/outputs/bg.png" (optional),
      "characters": [{"image":"static/chars/oldman.png","x":0.3,"y":0.6,"scale":0.6}, ...],
      "text": "Old Man: Where are you going?",
      "focus_bbox":[0.3,0.2,0.4,0.6]
    }
    """
    try:
        from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, ColorClip
        import numpy as np
    except Exception as e:
        return {"ok": False, "error": "moviepy_not_installed", "msg": str(e)}

    w = spec.get("width", 640)
    h = spec.get("height", 360)
    out_path = out_path or str(OUT / f"thumb_{_id()}.png")

    # base background
    bg_path = spec.get("background")
    if bg_path and Path(bg_path).exists():
        bg = ImageClip(bg_path).resize((w,h)).set_duration(0.1)
    else:
        bg = ColorClip(size=(w,h), color=(30,30,30)).set_duration(0.1)

    layers = [bg]

    # characters
    for ch in spec.get("characters", []):
        img = ch.get("image")
        if img and Path(img).exists():
            ic = ImageClip(img)
            sc = ch.get("scale", 0.6)
            ic = ic.resize(width=int(w*sc))
            x = int(ch.get("x", 0.5)*w - ic.w/2)
            y = int(ch.get("y", 0.5)*h - ic.h/2)
            ic = ic.set_position((x,y)).set_duration(0.1)
            layers.append(ic)
    # text overlay
    txt = spec.get("text")
    if txt:
        try:
            tc = TextClip(txt, fontsize=22, color='white', method='caption', size=(w-40, None))
            tc = tc.set_position(("center", h-70)).set_duration(0.1)
            layers.append(tc)
        except Exception:
            pass

    comp = CompositeVideoClip(layers, size=(w,h))
    comp.save_frame(out_path, t=0)
    return {"ok": True, "path": out_path}

def render_thumbnail_blender(job: dict, blender_path: str = "blender") -> dict:
    """
    job: should contain scene_blend (optional), camera transform or use default scene in blend
    Runs blender headless with small script to setup camera and render a single frame to PNG.
    Requires Blender installed on worker.
    """
    try:
        import json, tempfile, os
        tmp = tempfile.mkdtemp()
        jobfile = os.path.join(tmp, "thumb_job.json")
        with open(jobfile, "w") as f:
            json.dump(job, f)
        script = Path(__file__).parent / "blender_story_thumb.py"
        out_png = job.get("out") or str(OUT / f"thumb_{_id()}.png")
        blend = job.get("scene_blend")
        if not blend or not Path(blend).exists():
            return {"ok": False, "error": "blend_missing", "msg":"provide scene_blend for blender render"}
        cmd = f"{blender_path} --background {blend} --python {script} -- {jobfile} {out_png}"
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        if p.returncode != 0:
            return {"ok": False, "stderr": p.stderr[:200], "stdout": p.stdout[:200]}
        return {"ok": True, "path": out_png}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def render_batch_thumbnails(frames_list: list, use_blender=False) -> dict:
    """
    frames_list: list of specs for moviepy or blender jobs.
    returns list of produced paths.
    """
    outs = []
    for spec in frames_list:
        if use_blender:
            res = render_thumbnail_blender(spec)
        else:
            res = render_thumbnail_moviepy(spec)
        if res.get("ok"):
            outs.append(res["path"])
    return {"ok": True, "outs": outs}
