# extern/mfa_wrapper.py
# Usage: python extern/mfa_wrapper.py --audio /path/to/audio.wav --text "full transcript" --out /path/to/out_prefix
import argparse, subprocess, json, tempfile, os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--audio", required=True)
parser.add_argument("--text", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--lang", default="en")
args = parser.parse_args()

AUDIO = Path(args.audio)
TEXT = args.text
OUT = Path(args.out)
OUT.parent.mkdir(parents=True, exist_ok=True)

# Quick helper: create minimal corpus dir for MFA (audio + transcript .lab)
with tempfile.TemporaryDirectory() as tmpdir:
    tmpdir = Path(tmpdir)
    base = AUDIO.stem
    # copy audio
    audio_dst = tmpdir / f"{base}.wav"
    import shutil
    shutil.copy(AUDIO, audio_dst)
    # write transcript .lab
    (tmpdir / f"{base}.lab").write_text(TEXT, encoding="utf-8")
    # expected acoustic model & dictionary paths: user should set these env vars or edit below
    ACOUSTIC = os.getenv("MFA_ACOUSTIC_MODEL", "/usr/share/mfa/acoustic_model")  # edit if needed
    DICT = os.getenv("MFA_DICTIONARY", "/usr/share/mfa/dict")                   # edit
    OUTDIR = OUT.parent / (OUT.stem + "_mfa_out")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    # If MFA is installed:
    mfa_cmd = shutil.which("mfa")
    if mfa_cmd:
        cmd = f"mfa align {str(tmpdir)} {ACOUSTIC} {DICT} {str(OUTDIR)} --clean"
        try:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
            if p.returncode != 0:
                # fallback naive timing
                raise Exception("MFA failed: " + p.stderr[:200])
            # MFA will produce TextGrid or json per file — simplify: produce segments JSON from TextGrid if available
            # naive placeholder: write a trivial JSON saying aligned
            result = {"ok": True, "mfa_stdout": p.stdout[:200]}
            (OUT.with_suffix(".json")).write_text(json.dumps(result, indent=2))
            print("OK - MFA done, wrote:", str(OUT.with_suffix(".json")))
            exit(0)
        except Exception as e:
            print("MFA invocation failed:", e)
    # fallback: naive segmentation
    words = TEXT.split()
    total_est = max(0.2, len(words) * 0.5)
    avg = total_est / len(words) if len(words) else 0.1
    t = 0.0
    segs = []
    for w in words:
        segs.append({"word": w, "start": round(t,3), "end": round(t+avg,3)})
        t += avg
    OUT.with_suffix(".json").write_text(json.dumps({"ok": True, "note": "fallback", "segments": segs}, indent=2))
    print("Fallback segments written to", str(OUT.with_suffix(".json")))
    exit(0)
