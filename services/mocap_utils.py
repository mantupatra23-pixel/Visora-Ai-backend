# services/mocap_utils.py
from pathlib import Path
import json
def read_job(path):
    p = Path(path)
    return json.loads(p.read_text())
def write_manifest(out_dir, manifest: dict):
    p = Path(out_dir) / "manifest.json"
    p.write_text(json.dumps(manifest, indent=2))
    return str(p)
