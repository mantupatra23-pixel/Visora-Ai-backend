# routes/edl.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.edl_exporter import export_srt, export_edl

router = APIRouter()

class ExportReq(BaseModel):
    shot_list: list
    srt_out: str | None = "static/edl/out.srt"
    edl_out: str | None = "static/edl/out.edl"

@router.post("/export")
def export(req: ExportReq):
    srt_res = export_srt(req.shot_list, req.srt_out)
    edl_res = export_edl(req.shot_list, req.edl_out)
    return {"ok": True, "srt": srt_res, "edl": edl_res}
