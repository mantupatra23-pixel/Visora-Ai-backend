# services/voice_clone.py
"""
High-level helper to clone/convert voice.

SAFETY NOTE:
- Voice cloning is privacy-sensitive. Only use if you have explicit written consent from
  the speaker. The functions here enforce a consent flag and otherwise use safe fallbacks.
- Replace the placeholder commands with your real model invocation (e.g. RTVC, Resemble or other)
  on a GPU worker when you enable real cloning.

Provides:
- clone_voice_sample(sample_audio_path, speaker_name=None, consent=False)
    -> registers/copies sample and (optional) runs encoder to make speaker embedding.
- synthesize_with_clone(text, clone_id, out_name=None)
    -> synthesize using cloned speaker (placeholder uses safe fallback TTS unless configured).
"""

import os
import uuid
import json
from pathlib import Path
from shutil import copyfile

ROOT = Path(".").resolve()
CLONE_DIR = ROOT / "assets" / "voice_clones"
CLONE_DIR.mkdir(parents=True, exist_ok=True)

# Path to external real-time voice cloning repo (optional). Set via env if available.
RTVC_PATH = os.getenv("RTVC_PATH", "")

def require_consent(consent_flag: bool):
    """Raise if consent is not provided."""
    if not consent_flag:
        raise PermissionError("Voice cloning requires explicit consent. Set consent=True with written permission.")

def _safe_id() -> str:
    return uuid.uuid4().hex[:12]

def clone_voice_sample(sample_audio_path: str, speaker_name: str | None = None, consent: bool = False, extra_args: list | None = None):
    """
    Register a speaker from one or more sample files.

    - sample_audio_path: path to an audio file (wav/ogg/mp3). If a folder is passed, copies all files.
    - speaker_name: optional name/id; generated if missing.
    - consent: MUST be True to proceed.
    - extra_args: list of extra args passed to encoder script (if using a real encoder).
    """
    require_consent(consent)
    sid = speaker_name or _safe_id()
    speaker_dir = CLONE_DIR / sid

    # if already exists, return existing (do not overwrite unless caller removes)
    if speaker_dir.exists():
        return {"ok": True, "speaker_id": sid, "msg": "speaker already registered", "path": str(speaker_dir)}

    try:
        speaker_dir.mkdir(parents=True, exist_ok=True)
        samples_dir = speaker_dir / "samples"
        samples_dir.mkdir(parents=True, exist_ok=True)

        s_path = Path(sample_audio_path)
        if s_path.is_dir():
            # copy all files
            for f in s_path.iterdir():
                if f.is_file():
                    copyfile(str(f), str(samples_dir / f.name))
        else:
            # copy single file
            dest = samples_dir / (s_path.name or f"sample_{_safe_id()}.wav")
            copyfile(str(s_path), str(dest))

        # placeholder: if you have an encoder script (RTVC etc), call it here to make embedding
        embed_out = speaker_dir / "embedding.npy"
        if RTVC_PATH:
            # Example: python <RTVC_PATH>/encode_speaker.py --input <samples_dir> --out <embed_out>
            cmd = ["python", str(Path(RTVC_PATH) / "encode_speaker.py"), "--input", str(samples_dir), "--out", str(embed_out)]
            if extra_args:
                cmd += extra_args
            try:
                import subprocess
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if proc.returncode != 0:
                    # encoder failed — still return registration but mark error
                    meta = {"speaker_id": sid, "registered": True, "consent": True, "embed_status": "encoder_failed", "encoder_stdout": proc.stdout[:2000], "encoder_stderr": proc.stderr[:2000]}
                    (speaker_dir / "meta.json").write_text(json.dumps(meta, indent=2))
                    return {"ok": True, "speaker_id": sid, "note": "registered, encoder failed", "meta": meta}
            except Exception as e:
                meta = {"speaker_id": sid, "registered": True, "consent": True, "embed_status": "encoder_exception", "error": str(e)}
                (speaker_dir / "meta.json").write_text(json.dumps(meta, indent=2))
                return {"ok": True, "speaker_id": sid, "note": "registered, encoder exception", "meta": meta}

        # if no encoder or encoder succeeded, write metadata
        meta = {"speaker_id": sid, "registered": True, "consent": True}
        (speaker_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        return {"ok": True, "speaker_id": sid, "path": str(speaker_dir)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def synthesize_with_clone(text: str, clone_id: str, out_name: str | None = None, tts_args: list | None = None):
    """
    Synthesize text using a cloned speaker.
    - If a real TTS/cloning pipeline is configured, call it here.
    - Otherwise we fallback to a safe generic TTS (pyttsx3) to avoid producing a real cloned voice.
    Returns { ok: bool, path: "<wav>" }
    """
    speaker_dir = CLONE_DIR / clone_id
    if not speaker_dir.exists():
        return {"ok": False, "error": "clone_id_not_found"}

    out_name = out_name or f"{clone_id}_synth_{_safe_id()}.wav"
    out_path = speaker_dir / out_name

    # If a real cloning TTS CLI exists under RTVC_PATH, call it:
    if RTVC_PATH:
        cmd = ["python", str(Path(RTVC_PATH) / "synthesize.py"), "--embedding", str(speaker_dir / "embedding.npy"), "--text", text, "--out", str(out_path)]
        if tts_args:
            cmd += tts_args
        try:
            import subprocess
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if proc.returncode != 0:
                return {"ok": False, "error": "synthesis_failed", "stdout": proc.stdout[:2000], "stderr": proc.stderr[:2000]}
            return {"ok": True, "path": str(out_path)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # FALLBACK (safe): use pyttsx3 or system TTS as placeholder
    try:
        # Try services.tts_service if you have a wrapper (preferred)
        try:
            from services.tts_service import tts_pyttsx3
            res = tts_pyttsx3(text, out_name=out_name, out_dir=str(speaker_dir))
            if res.get("ok"):
                return {"ok": True, "path": res["path"], "note": "fallback-tts-used"}
        except Exception:
            pass

        # Last resort: minimal pyttsx3 inline (may not work in headless envs)
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(text, str(out_path))
            engine.runAndWait()
            return {"ok": True, "path": str(out_path), "note": "pyttsx3-fallback"}
        except Exception as e:
            return {"ok": False, "error": "no_tts_available", "detail": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
