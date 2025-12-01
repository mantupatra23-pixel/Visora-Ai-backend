# services/tts_client.py
import os
from pathlib import Path
import httpx
from typing import Optional

TTS_SERVER_URL = os.getenv("TTS_SERVER_URL", "http://127.0.0.1:8000")  # change if remote

# ensure outputs dir exists locally for downloaded files
LOCAL_OUT_DIR = Path("static/outputs")
LOCAL_OUT_DIR.mkdir(parents=True, exist_ok=True)

class TTSClient:
    def __init__(self, base_url: str | None = None, timeout: int = 60):
        self.base_url = base_url or TTS_SERVER_URL
        self.timeout = timeout

    async def synthesize_async(self, text: str, filename: Optional[str] = None) -> dict:
        """
        Calls external TTS server async and returns a dict:
        {"ok": True, "remote_file": "static/outputs/xyz.mp3", "downloaded": "static/outputs/xyz.mp3"}
        """
        payload = {"text": text}
        if filename:
            payload["filename"] = filename

        url = f"{self.base_url}/tts/speak"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            resp = r.json()

        remote_path = resp.get("file")
        if not remote_path:
            raise RuntimeError("TTS server did not return file path")

        # Attempt to download the produced file (if accessible)
        # remote file may be served at e.g. http://server/static/outputs/<name>
        file_name = Path(remote_path).name
        file_url = f"{self.base_url}/static/outputs/{file_name}"
        local_path = LOCAL_OUT_DIR / file_name

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                dr = await client.get(file_url)
                dr.raise_for_status()
                local_path.write_bytes(dr.content)
        except Exception as e:
            # If download fails, still return remote path
            return {"ok": True, "remote_file": remote_path, "downloaded": None, "error": str(e)}

        return {"ok": True, "remote_file": remote_path, "downloaded": str(local_path)}

    def synthesize(self, text: str, filename: Optional[str] = None) -> dict:
        import asyncio
        return asyncio.run(self.synthesize_async(text, filename))
