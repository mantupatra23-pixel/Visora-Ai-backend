# services/phoneme_aligner.py
import os, shlex, subprocess, uuid, json
from pathlib import Path

ROOT = Path(".").resolve()
OUT = ROOT / "static" / "align"
OUT.mkdir(parents=True, exist_ok=True)

def _tid(): return uuid.uuid4().hex[:8]

def run_montreal_forced_aligner(audio_path: str, transcript: str, lang: str = "en", out_prefix: str | None = None):
    """
    Wrapper for Montreal Forced Aligner (MFA).
    Requires MFA installed and models downloaded.
    CLI example:
      mfa align <corpus_dir> <acoustic_model> <dictionary> output_dir
    For simplicity, use a small external script extern/mfa_wrapper.py that accepts audio+text.
    """
    wrapper = ROOT / "extern" / "mfa_wrapper.py"
    if not wrapper.exists():
        # fallback: use gentle or estimate durations via TTS speed heuristics
        # Return coarse boundaries using naive word timing
        words = transcript.split()
        total =  max(0.1, len(words) * 0.5)  # naive seconds
        t = 0.0; segs=[]
        avg = total/len(words) if len(words)>0 else 0.1
        for w in words:
            segs.append({"word":w,"start":round(t,3),"end":round(t+avg,3)})
            t += avg
        return {"ok": True, "segments": segs, "note":"fallback_naive_timing"}
    out_prefix = out_prefix or str(OUT / f"align_{_tid()}")
    cmd = f"python {shlex.quote(str(wrapper))} --audio {shlex.quote(audio_path)} --text {shlex.quote(transcript)} --out {shlex.quote(out_prefix)}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
    if p.returncode!=0:
        return {"ok":False,"stderr":p.stderr,"stdout":p.stdout}
    # wrapper should write out JSON segments at out_prefix + ".json"
    segf = Path(out_prefix+".json")
    if segf.exists():
        return {"ok":True,"segments": json.loads(segf.read_text())}
    return {"ok":False,"error":"no_output"}
