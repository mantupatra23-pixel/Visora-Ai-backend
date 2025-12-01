# services/asr_whisper.py
"""
ASR wrapper: tries (in order)
  1) openai-whisper (python package) if installed and model files available
  2) whisper.cpp CLI (if installed at WHISPER_CPP_BIN env)
  3) fallback: returns error

Exports:
  transcribe_file(path, lang=None, task='transcribe', format='srt'|'text') -> dict
"""
import os, subprocess, shlex, tempfile, json
from pathlib import Path

ROOT = Path(".").resolve()
OUT = ROOT / "static" / "asr"
OUT.mkdir(parents=True, exist_ok=True)

def _run(cmd, timeout=1800):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr, "rc": p.returncode}

def transcribe_file(filepath: str, lang: str | None = None, output_format: str = "srt", model: str | None = None):
    # try python whisper (if installed)
    try:
        import whisper
        m = model or "small"
        w = whisper.load_model(m)
        result = w.transcribe(filepath, language=lang) if lang else w.transcribe(filepath)
        text = result.get("text","")
        base = OUT / (Path(filepath).stem + "_whisper")
        base_txt = str(base) + ".txt"
        base_srt = str(base) + ".srt"
        open(base_txt, "w", encoding="utf-8").write(text)
        # produce simple SRT using segments if requested
        if output_format == "srt":
            segs = result.get("segments", [])
            with open(base_srt, "w", encoding="utf-8") as fh:
                for i, s in enumerate(segs, start=1):
                    start = s['start']; end = s['end']; segtext = s['text'].strip()
                    def fmt(t):
                        h = int(t//3600); m = int((t%3600)//60); s2 = int(t%60); ms = int((t - int(t))*1000)
                        return f"{h:02d}:{m:02d}:{s2:02d},{ms:03d}"
                    fh.write(f"{i}\n{fmt(start)} --> {fmt(end)}\n{segtext}\n\n")
            return {"ok": True, "text": base_txt, "srt": base_srt, "raw": result}
        return {"ok": True, "text": base_txt, "raw": result}
    except Exception as e:
        # try whisper.cpp CLI if set
        bin_path = os.getenv("WHISPER_CPP_BIN")
        if bin_path and Path(bin_path).exists():
            out_base = OUT / (Path(filepath).stem + "_whcpp")
            out_srt = str(out_base) + ".srt"
            cmd = f"{shlex.quote(bin_path)} -f {shlex.quote(filepath)} -m {shlex.quote(model or 'ggml-small.bin')} -ot {shlex.quote(out_srt)}"
            r = _run(cmd)
            if r['ok']:
                return {"ok": True, "srt": out_srt, "stdout": r['stdout']}
            else:
                return {"ok": False, "error": "whisper_cpp_failed", "detail": r}
        return {"ok": False, "error": "no_asr_available", "detail": str(e)}
