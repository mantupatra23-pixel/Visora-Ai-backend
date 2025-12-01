# routes/realtime_ws.py
from fastapi import APIRouter, WebSocket
from services.realtime_pipeline import process_chunk_fast, RT_TMP
import base64, uuid, os

router = APIRouter()

@router.websocket("/realtime/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    # protocol: client sends JSON with {"type":"chunk","audio_b64":"...","face":"uploads/face.jpg"}
    while True:
        msg = await ws.receive_json()
        if msg.get("type") == "chunk":
            audio_b64 = msg.get("audio_b64")
            face = msg.get("face")
            raw = base64.b64decode(audio_b64)
            tmp_wav = str(RT_TMP / f"chunk_{uuid.uuid4().hex}.wav")
            open(tmp_wav,"wb").write(raw)
            out_chunk = str(RT_TMP / f"out_{uuid.uuid4().hex}.mp4")
            res = process_chunk_fast(face, tmp_wav, out_chunk)
            if res.get("ok"):
                data_b = open(out_chunk,"rb").read()
                await ws.send_bytes(data_b)
            else:
                await ws.send_json({"error": res})
        else:
            await ws.send_json({"error":"unknown_type"})
