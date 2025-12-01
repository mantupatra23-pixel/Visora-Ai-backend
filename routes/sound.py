# routes/sound.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.sound_engine import mix_voice_and_music, apply_reverb, apply_echo, overlay_sfx, change_pitch
from pathlib import Path

router = APIRouter()

class MixReq(BaseModel):
    voice_path: str     # local path e.g. static/outputs/voice.mp3
    music_path: str | None = None
    out_name: str | None = None
    auto_duck: bool | None = True
    music_gain_db: float | None = -6.0
    voice_gain_db: float | None = 0.0

@router.post("/mix")
def mix_audio(req: MixReq):
    try:
        if not Path(req.voice_path).exists():
            raise HTTPException(status_code=404, detail="Voice file not found")
        out = mix_voice_and_music(req.voice_path, req.music_path, out_name=req.out_name, auto_ducking=req.auto_duck, music_gain_db=req.music_gain_db, voice_gain_db=req.voice_gain_db)
        return {"ok": True, "file": out}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class EffectReq(BaseModel):
    audio_path: str
    effect: str   # "reverb" | "echo" | "pitch_up" | "pitch_down"
    value: float | None = None
    out_name: str | None = None

@router.post("/effect")
def apply_effect(req: EffectReq):
    try:
        if not Path(req.audio_path).exists():
            raise HTTPException(status_code=404, detail="File not found")
        seg = None
        if req.effect == "reverb":
            seg = apply_reverb(load_audio(req.audio_path), decay=float(req.value or 0.4))
        elif req.effect == "echo":
            seg = apply_echo(load_audio(req.audio_path), delay_ms=int(req.value or 200))
        elif req.effect == "pitch_up":
            seg = change_pitch(load_audio(req.audio_path), semitones=float(req.value or 2.0))
        elif req.effect == "pitch_down":
            seg = change_pitch(load_audio(req.audio_path), semitones=float(req.value or -2.0))
        else:
            raise HTTPException(status_code=400, detail="Unknown effect")
        out_name = req.out_name or f"effect_{req.effect}_{Path(req.audio_path).name}"
        out_path = Path("static/outputs") / out_name
        save_audio(seg, out_path, format="mp3")
        return {"ok": True, "file": str(out_path)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
