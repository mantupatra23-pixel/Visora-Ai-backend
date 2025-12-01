# services/preset_engine.py
import json
from pathlib import Path
import subprocess
import os
import hashlib
import time

ROOT = Path(".").resolve()
PRESETS_FILE = ROOT / "presets" / "presets.json"
OUT = Path("static/characters")
OUT.mkdir(parents=True, exist_ok=True)

def _safe(seed: str):
    return hashlib.sha1(seed.encode()).hexdigest()[:10]

class PresetEngine:
    def __init__(self, presets_file: str | None = None):
        self.presets_file = Path(presets_file) if presets_file else PRESETS_FILE
        if not self.presets_file.exists():
            raise RuntimeError("Presets file not found: " + str(self.presets_file))
        with open(self.presets_file, "r") as f:
            self.presets = json.load(f)

    def list_presets(self):
        return [{ "key": k, "name": v.get("name"), "description": v.get("description") } for k,v in self.presets.items()]

    def get_preset(self, key: str):
        return self.presets.get(key)

    def apply_preset_to_image(self, preset_key: str, input_image: str, out_prefix: str | None = None, extra_prompt_add: str | None = None):
        """
        Applies a preset to an input image by preparing a composed prompt and optionally
        triggering the Zero123 / SD multiview + 3D pipeline.
        Returns path to multiview folder (or prepared prompt info) — user engine will call generate_character next.
        """
        if preset_key not in self.presets:
            raise ValueError("Unknown preset: " + preset_key)
        p = self.presets[preset_key]
        prompt = p.get("example_prompt", "")
        if extra_prompt_add:
            prompt = prompt + ", " + extra_prompt_add

        # Save a small JSON that the 3D pipeline can consume (multiview/zero123 tool)
        seed = _safe(input_image + prompt + str(time.time()))
        meta_dir = OUT / f"preset_{preset_key}_{seed}"
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "preset": preset_key,
            "prompt": prompt,
            "sd_model": p.get("sd_model"),
            "lora": p.get("lora"),
            "controlnet": p.get("controlnet"),
            "input_image": input_image,
            "output_meta": str(meta_dir / "meta.json")
        }
        with open(meta["output_meta"], "w") as f:
            json.dump(meta, f, indent=2)

        # Optionally: if you have a Zero123 script that accepts meta JSON, call it.
        # Example: python zero123_repo/infer_with_meta.py --meta <meta.json> --outdir <meta_dir>
        # We'll not call it automatically here (to keep safe); front service (character3d_engine) can call it.
        return {"ok": True, "meta": meta, "meta_dir": str(meta_dir)}

    def prepare_prompt_only(self, preset_key: str, extra: str | None = None):
        if preset_key not in self.presets:
            raise ValueError("Unknown preset")
        p = self.presets[preset_key]
        prompt = p.get("example_prompt", "")
        if extra:
            prompt = prompt + ", " + extra
        return {"ok": True, "prompt": prompt, "sd_model": p.get("sd_model"), "lora": p.get("lora"), "controlnet": p.get("controlnet")}
