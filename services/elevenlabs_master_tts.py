import os, uuid, time
from pathlib import Path

ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")
OUT = Path("assets/eleven")
OUT.mkdir(parents=True, exist_ok=True)

def eleven_tts(text, voice_id="alloy", model="eleven_multilingual_v2", stability=None, similarity=None):
    import requests, json
    out_file = OUT / f"tts_{uuid.uuid4().hex[:8]}.mp3"

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
    
    payload = {
        "text": text,
        "model": model,
        "voice_settings":{
            "stability": stability or 0.4,
            "similarity_boost": similarity or 0.8
        }
    }

    r = requests.post(url, headers=headers, json=payload, stream=True)
    if r.status_code != 200:
        return {"ok": False, "error": r.text}

    with open(out_file, "wb") as f:
        for chunk in r.iter_content(1024):
            if chunk:
                f.write(chunk)

    return {"ok": True, "path": str(out_file)}
