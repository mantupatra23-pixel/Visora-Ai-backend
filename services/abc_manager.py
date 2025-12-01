# services/abc_manager.py
"""
Alembic and cache manager utilities
- verify_alembic(path) -> basic validation (existence + size)
- list_caches(cache_dir) -> list abc/pc files
- remap_alembic_references(blend_file, old_prefix, new_prefix) -> runs blender script to remap path references
"""
import os, json
from pathlib import Path
import subprocess, shlex

ROOT = Path(".").resolve()

def verify_alembic(path: str):
    p = Path(path)
    if not p.exists():
        return {"ok": False, "error": "missing"}
    size_mb = p.stat().st_size / (1024*1024)
    return {"ok": True, "path": str(p), "size_mb": round(size_mb,2)}

def list_caches(cache_dir: str):
    p = Path(cache_dir)
    if not p.exists():
        return {"ok": False, "error": "dir_missing"}
    files = [str(x) for x in p.glob("**/*") if x.suffix.lower() in (".abc",".mc",".pc",".bphys",".vdb")]
    return {"ok": True, "files": files}

def remap_alembic_in_blend(blend_path: str, old_prefix: str, new_prefix: str):
    # call blender script that loads blend and remaps filepaths in alembic modifiers / caches
    script = str(ROOT / "blender_scripts" / "remap_abc_paths.py")
    cmd = f"blender --background {shlex.quote(blend_path)} --python {shlex.quote(script)} -- {shlex.quote(old_prefix)} {shlex.quote(new_prefix)}"
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr}
