# services/prop_injector.py
import os, json, uuid, shutil, subprocess
from pathlib import Path
ROOT = Path(".").resolve()
PROPS_DIR = ROOT / "assets" / "props"
OUT_DIR = ROOT / "static" / "props_out"
JOB_DIR = ROOT / "jobs" / "props"
PROPS_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
JOB_DIR.mkdir(parents=True, exist_ok=True)

BLENDER_SCRIPT = str(ROOT / "blender_scripts" / "prop_injector_worker.py")

def _task_id():
    return uuid.uuid4().hex[:10]

def list_available_props():
    """Return list of prop files and metadata (scan assets/props/*.json + model files)."""
    props = []
    for meta in PROPS_DIR.glob("*.json"):
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            name = data.get("name") or meta.stem
            model = data.get("model")
            if model:
                model_path = PROPS_DIR / model
                data["model_path"] = str(model_path) if model_path.exists() else None
            props.append(data)
        except Exception:
            continue
    return props

def register_prop(prop_meta: dict):
    """
    prop_meta sample:
    {
      "name":"sword_long",
      "model":"sword_long.glb",
      "bbox":[0.5,0.05,0.02],  # approx size (m)
      "hand_grip":{"offset":[0,0,0],"bone":"RightHand"},
      "physics":{"mass":1.2, "shape":"convex"}
    }
    """
    name = prop_meta.get("name") or f"prop_{_task_id()}"
    meta_path = PROPS_DIR / f"{name}.json"
    meta_path.write_text(json.dumps(prop_meta, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(meta_path)}

def create_injection_job(scene_blend: str, actions: list, out_prefix: str | None = None):
    """
    actions: list of injection actions:
      {"prop":"sword_long", "target":"Boy", "attach":"right_hand", "position":[0,0,0], "rotation":[0,0,0], "scale":1.0, "physics":True}
    returns: job file path and task id
    """
    tid = _task_id()
    job = {"task_id": tid, "scene_blend": scene_blend, "actions": actions, "out_prefix": out_prefix or str(OUT_DIR / f"job_{tid}_")}
    jf = JOB_DIR / f"prop_job_{tid}.json"
    jf.write_text(json.dumps(job, indent=2), encoding="utf-8")
    # spawn Blender worker (non-blocking recommended; in production use Celery)
    cmd = f"blender --background {shlex_quote(scene_blend)} --python {shlex_quote(BLENDER_SCRIPT)} -- {shlex_quote(str(jf))} {shlex_quote(job['out_prefix'])}"
    try:
        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "task_id": tid, "job": str(jf), "out_prefix": job["out_prefix"]}

def shlex_quote(s):
    # helper to quote None-safe
    import shlex
    return shlex.quote(s or "")
