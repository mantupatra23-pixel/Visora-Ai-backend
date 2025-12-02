# services/prop_engine.py
import json, time, uuid
from pathlib import Path
from services.prop_library import get_prop, list_props
from services.prop_utils import choose_prop_for_line

ROOT = Path(".").resolve()
JOBS = ROOT / "jobs" / "props"
JOBS.mkdir(parents=True, exist_ok=True)

def _tid():
    return uuid.uuid4().hex[:8]

def build_prop_job(script_line: str, character: str = "charA", hand_hint: str | None = None, name: str | None = None):
    prop_name = choose_prop_for_line(script_line)
    if hand_hint:
        # override selection if explicit
        prop = get_prop(hand_hint) or get_prop(prop_name)
    else:
        prop = get_prop(prop_name)
    if not prop:
        # fallback: return a 'generic' prop placeholder if available
        job = {"ok": False, "error": "no_prop_detected", "suggestion": list(list_props().keys())}
        return job
    job_id = name or f"prop_{_tid()}"
    job = {
        "job_id": job_id,
        "created_at": time.time(),
        "character": character,
        "script_line": script_line,
        "prop_key": prop_name,
        "prop": prop,
        "attach": {
            "primary_bone": prop.get("hand","right") == "right" and "hand.R" or "hand.L",
            "secondary_bone": None
        },
        "output_path": str(JOBS / (job_id + ".json"))
    }
    Path(job['output_path']).write_text(json.dumps(job, indent=2))
    return job
