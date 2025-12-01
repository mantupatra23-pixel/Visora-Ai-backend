# routes/farm.py
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Any, List

from services.farm_manager import create_job, get_job_status, TASKS_DIR
from services.node_monitor import heartbeat, list_nodes

router = APIRouter()


class FarmJob(BaseModel):
    type: str
    job_name: str
    start_frame: int = 1
    end_frame: int = 1
    priority: int = 5
    payload: Dict[str, Any] = {}
    max_retries: int = 2


@router.post("/submit")
def submit(job: FarmJob):
    """
    Submit a farm job JSON — this will create task files / schedule job.
    """
    try:
        res = create_job(job.dict())
        if not res.get("ok"):
            raise HTTPException(status_code=500, detail=res)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
def status(job_id: str):
    """
    Get status for a job id.
    """
    try:
        res = get_job_status(job_id)
        if not res.get("ok"):
            raise HTTPException(status_code=404, detail=res)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list_pending")
def list_pending():
    """
    Return a list of pending task JSONs from TASKS_DIR.
    """
    try:
        tasks: List[str] = []
        # TASKS_DIR expected to be a pathlib.Path
        for tfile in Path(TASKS_DIR).glob("*.json"):
            try:
                t = tfile.read_text()
                tasks.append(t)
            except Exception:
                # ignore unreadable files
                continue
        return {"ok": True, "pending_count": len(tasks), "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Node endpoints (heartbeat, list)
@router.post("/node/heartbeat")
def node_heartbeat(node_id: str = Body(...), info: Dict[str, Any] = Body(...)):
    """
    Called by worker nodes to send heartbeat + info (cpu/gpu/load etc).
    Expects JSON body with two fields: node_id (string) and info (dict).
    """
    try:
        res = heartbeat(node_id, info)
        return {"ok": True, "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes")
def nodes_list():
    """
    Return list of known nodes and their status.
    """
    try:
        nodes = list_nodes()
        return {"ok": True, "nodes": nodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
