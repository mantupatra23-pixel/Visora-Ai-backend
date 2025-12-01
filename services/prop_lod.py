# services/prop_lod.py
import subprocess, shlex, uuid
from pathlib import Path
ROOT = Path(".").resolve()
LODDIR = ROOT / "assets" / "props" / "lods"
LODDIR.mkdir(parents=True, exist_ok=True)

def generate_lods(input_model: str, out_prefix: str | None = None, lod_levels: list | None = [0.5,0.25,0.12]):
    tid = uuid.uuid4().hex[:8]
    out_prefix = out_prefix or str(LODDIR / f"lod_{tid}_")
    lod_csv = ",".join([str(x) for x in lod_levels])
    cmd = f"blender --background --python blender_scripts/generate_lod.py -- {shlex.quote(input_model)} {shlex.quote(str(LODDIR))} {shlex.quote(Path(input_model).stem)} {shlex.quote(lod_csv)}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1800)
    return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr, "out_dir": str(LODDIR)}
