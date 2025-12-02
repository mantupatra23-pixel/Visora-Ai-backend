import os, json, uuid
from pathlib import Path

ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")
CLONES = Path("assets/eleven_clones")
CLONES.mkdir(parents=True, exist_ok=True)

def require_consent(consent_flag):
    if not consent_flag:
        raise PermissionError("Consent required for voice cloning.")

def eleven_clone(sample_path, voice_name=None, consent=False):
    require_consent(consent)
    import requests

    voice_name = voice_name or f"clone_{uuid.uuid4().hex[:6]}"
    files = {"file": open(sample_path, "rb")}
    data = {"voice_name": voice_name, "source": "instant_clone"}

    url = "https://api.elevenlabs.io/v1/voices/add"
    headers = {"xi-api-key": ELEVEN_KEY}

    r = requests.post(url, headers=headers, files=files, data=data)
    if r.status_code not in (200, 201):
        return {"ok": False, "error": r.text}

    resp = r.json()

    vid = resp.get("voice_id") or resp.get("id") or voice_name
    (CLONES / vid).mkdir(parents=True, exist_ok=True)
    (CLONES / vid / "meta.json").write_text(json.dumps(resp, indent=2))

    return {"ok": True, "voice_id": vid, "meta": resp}
