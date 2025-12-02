# services/eleven_voice_clone.py
import os, json, time, uuid
from pathlib import Path

ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY", None)
CLONE_DIR = Path("assets/eleven_clones")
CLONE_DIR.mkdir(parents=True, exist_ok=True)

def require_consent(consent_flag):
    if not consent_flag:
        raise PermissionError("Voice cloning requires explicit written consent. Provide consent=True.")

def create_instant_clone(sample_audio_path, voice_name=None, consent=False):
    """
    Uses ElevenLabs 'instant clone' flow via REST.
    Returns: {"ok":True,"voice_id":..., "meta":...}
    """
    require_consent(consent)
    import requests
    voice_name = voice_name or f"clone_{uuid.uuid4().hex[:6]}"
    url = "https://api.elevenlabs.io/v1/voices/add"
    headers = {"xi-api-key": ELEVEN_KEY}
    # file upload: sample audio (wav)
    files = {"file": open(sample_audio_path, "rb")}
    data = {"voice_name": voice_name, "source": "instant_clone"}
    r = requests.post(url, headers=headers, files=files, data=data, timeout=120)
    if r.status_code not in (200,201):
        return {"ok": False, "status": r.status_code, "error": r.text}
    resp = r.json()
    # save metadata locally
    vid = resp.get("id") or resp.get("voice_id") or resp.get("voice") or voice_name
    d = CLONE_DIR / vid
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(json.dumps(resp, indent=2))
    return {"ok": True, "voice_id": vid, "resp": resp}

def synthesize_clone_text(text, voice_id, output_name=None, **kwargs):
    # wrapper to call tts_generate from elevenlabs_service using voice_id
    from services.elevenlabs_service import tts_generate
    return tts_generate(text, voice_id=voice_id, output_name=output_name, **kwargs)
