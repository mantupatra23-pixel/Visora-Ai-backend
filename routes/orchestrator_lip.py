# routes/orchestrator_lip.py
from fastapi import APIRouter
from pydantic import BaseModel
from tasks.lip_orchestrator import orchestrate_scene
import json, uuid
from pathlib import Path
ROOT = Path(".").resolve()
JOBROOT = ROOT / "jobs" / "lip_orch"
JOBROOT.mkdir(parents=True, exist_ok=True)

router = APIRouter()

class OrchReq(BaseModel):
    package: dict

@router.post("/submit")
def submit(req: OrchReq):
    pkg = req.package
    path = JOBROOT / f"pkg_{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(pkg, indent=2))
    task = orchestrate_scene.delay(str(path))
    return {"ok": True, "task_id": task.id, "pkg": str(path)}
