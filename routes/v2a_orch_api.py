# routes/v2a_orch_api.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json, uuid
from tasks.v2a_orchestrator import orchestrate_voice2anim

router = APIRouter()
JOBROOT = Path("jobs/v2a")
JOBROOT.mkdir(parents=True, exist_ok=True)

class OrchPkg(BaseModel):
    wav: str
    transcript: str | None = ""
    character: dict | None = {}
    mode: str | None = "fast"
    out_prefix: str | None = None

@router.post("/submit")
def submit(pkg: OrchPkg):
    # simple validation
    if not Path(pkg.wav).exists():
        raise HTTPException(status_code=404, detail="audio missing")
    ppath = JOBROOT / f"pkg_{uuid.uuid4().hex[:8]}.json"
    ppath.write_text(json.dumps(pkg.dict(), indent=2))
    task = orchestrate_voice2anim.delay(str(ppath))
    return {"ok":True,"task_id": task.id, "pkg": str(ppath)}
