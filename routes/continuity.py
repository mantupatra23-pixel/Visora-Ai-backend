# routes/continuity.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.continuity_checker import check_continuity

router = APIRouter()

class ContinuityReq(BaseModel):
    shot_list: list

@router.post("/check")
def check(req: ContinuityReq):
    res = check_continuity(req.shot_list)
    return res
