# routes/tts_proxy.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.tts_client import TTSClient

router = APIRouter()
tts_client = TTSClient()

class ProxyReq(BaseModel):
    text: str
    filename: str | None = None

@router.post("/speak")
async def proxy_speak(req: ProxyReq):
    try:
        res = await tts_client.synthesize_async(req.text, req.filename)
        return {"ok": True, "result": res}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
