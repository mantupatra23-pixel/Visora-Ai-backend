# services/multichar_dubbing.py
"""
Multichar dubbing helper:
Input:
  - script_lines: [{"speaker":"Old Man","text":"...","start":null}, ...]
  - voices: {"Old Man":"male_deep","Boy":"child_voice"}
Outputs:
  - produces per-speaker wav files, timing map (list of segments with start/end in seconds)
  - returns {"ok":True, "tracks": {"Old Man":"path.wav", ...}, "segments":[...]}
Notes:
  - Uses tts_offline from services.lip_emotion or external TTS
  - If start times needed, use forced pacing or speech-rate to estimate duration
"""
import os, json, uuid, shlex, subprocess
from pathlib import Path
from services.lip_emotion import tts_offline
ROOT = Path(".").resolve()
OUT = ROOT / "static" / "dubbing"
OUT.mkdir(parents=True, exist_ok=True)

def _task_id(): return uuid.uuid4().hex[:8]

def estimate_duration_from_text(text, wpm=140):
    words = len([w for w in text.split() if w.strip()])
    return max(0.2, words * 60.0 / wpm)

def generate_tracks(script_lines: list, voices: dict):
    """
    script_lines: ordered list of dicts {speaker, text}
    voices: mapping speaker->voice_id
    """
    tracks = {}
    segments = []
    time_cursor = 0.0
    for i, seg in enumerate(script_lines):
        speaker = seg.get("speaker") or "narrator"
        text = seg.get("text","")
        voice = voices.get(speaker)
        out_wav = OUT / f"{speaker.replace(' ','_')}_{_task_id()}.wav"
        # call TTS
        res = tts_offline(text, str(out_wav), voice=voice or "default")
        if not res.get("ok"):
            return {"ok": False, "error": "tts_failed", "detail": res}
        # estimate duration (or inspect wav length with sox/ffprobe)
        try:
            import soundfile as sf
            dur = sf.info(str(out_wav)).duration
        except Exception:
            dur = estimate_duration_from_text(text)
        segments.append({"speaker":speaker,"text":text,"start":round(time_cursor,3),"end":round(time_cursor+dur,3),"file":str(out_wav)})
        time_cursor += dur
        tracks.setdefault(speaker, []).append(str(out_wav))
    return {"ok": True, "tracks": tracks, "segments": segments, "total_duration":round(time_cursor,3)}
