# services/character3d_engine.py
import os
import subprocess
from pathlib import Path
import hashlib
import time

OUT = Path("static/characters")
OUT.mkdir(parents=True, exist_ok=True)

class Character3DEngine:
    def __init__(self, zero123_path="zero123_repo", tripo_path="tripo_repo"):
        self.zero123 = Path(zero123_path)
        self.tripo = Path(tripo_path)

    def _safe(self, s):
        import hashlib
        return hashlib.sha1(s.encode()).hexdigest()[:10]

    # 1. Generate multi-view 3D images from 1 input image
    def generate_multiview(self, image_path):
        seed = self._safe(image_path + str(time.time()))
        out_dir = OUT / f"multiview_{seed}"
        out_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "python", str(self.zero123 / "infer.py"),
            "--input", image_path,
            "--output_dir", str(out_dir),
            "--num_views", "8"
        ]

        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(p.stderr)

        return str(out_dir)

    # 2. Convert multi-view images to 3D mesh (TripoSR)
    def reconstruct_mesh(self, multiview_folder):
        seed = self._safe(multiview_folder + str(time.time()))
        out_path = OUT / f"character_{seed}.obj"

        cmd = [
            "python", str(self.tripo / "infer.py"),
            "--input_dir", str(multiview_folder),
            "--output", str(out_path)
        ]

        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(p.stderr)

        return str(out_path)

    # FULL PIPELINE: 2D → MultiView → Mesh
    def generate_character(self, image_path):
        mv = self.generate_multiview(image_path)
        mesh = self.reconstruct_mesh(mv)
        return mesh
