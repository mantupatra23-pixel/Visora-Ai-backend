# routes/distribute.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.youtube_uploader import upload_video
from pathlib import Path

router = APIRouter()

class UploadReq(BaseModel):
    video_path: str
    title: str
    description: str | None = ""
    tags: list | None = None
    privacy: str | None = "unlisted"
    thumbnail: str | None = None
    categoryId: str | None = "22"

@router.post("/youtube/upload")
def youtube_upload(req: UploadReq):
    try:
        if not Path(req.video_path).exists():
            raise HTTPException(status_code=404, detail="Video file not found")
        res = upload_video(
            file_path=req.video_path,
            title=req.title,
            description=req.description or "",
            tags=req.tags or [],
            privacy_status=req.privacy or "unlisted",
            categoryId=req.categoryId or "22",
            thumbnail_path=req.thumbnail
        )
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
