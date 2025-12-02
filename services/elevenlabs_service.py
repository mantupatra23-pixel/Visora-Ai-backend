# services/elevenlabs_service.py
import os, uuid, time
from pathlib import Path

ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY", None)
OUT = Path("assets/elevenlabs")
OUT.mkdir(parents=True, exist_ok=True)

# Try official SDK first, else fallback to direct HTTP (requests)
def _client_available():
    try:
        import elevenlabs
        return True
    except Exception:
        return False

def tts_generate(text, voice_id=None, model="eleven_multilingual_v1", output_name=None, stability=None, similarity_boost=None):
    """
    Generate speech using ElevenLabs.
    - voice_id: use an existing voice id (from your account) OR None to use default.
    - model: ElevenLabs model (default multilingual)
    Returns: {"ok":True,"path":...} or {"ok":False,"error":...}
    """
    outfile = OUT / (output_name or f"eleven_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp3")
    if _client_available():
        try:
            from elevenlabs import set_api_key, generate, save
            set_api_key(ELEVEN_KEY)
            # SDK: generate(text=..., voice="Rachel", model="...") returns audio bytes or object
            audio = generate(text=text, voice=voice_id or "alloy", model=model,
                             stability=stability, similarity_boost=similarity_boost)
            # save from SDK helper
            save(audio, str(outfile))
            return {"ok": True, "path": str(outfile)}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        # fallback: direct REST call
        try:
            import requests, json
            url = "https://api.elevenlabs.io/v1/text-to-speech/" + (voice_id or "alloy")
            headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
            payload = {"text": text, "model": model}
            # stability/similarity optional
            if stability is not None: payload["stability"] = stability
            if similarity_boost is not None: payload["similarity_boost"] = similarity_boost
            r = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
            if r.status_code != 200:
                return {"ok": False, "error": f"{r.status_code} {r.text}"}
            with open(outfile, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return {"ok": True, "path": str(outfile)}
        except Exception as e:
            return {"ok": False, "error": str(e)}
