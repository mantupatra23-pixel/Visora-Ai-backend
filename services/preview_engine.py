# services/preview_engine.py
import time
import hashlib
from pathlib import Path
import random

OUT = Path("static/outputs")
OUT.mkdir(parents=True, exist_ok=True)

# try to import preset and image services
try:
    from services.preset_engine import PresetEngine
    _HAS_PRESET = True
except Exception:
    PresetEngine = None
    _HAS_PRESET = False

try:
    from services.image_engine import ImageService
    _HAS_IMAGE = True
except Exception:
    ImageService = None
    _HAS_IMAGE = False

def _safe(seed: str):
    return hashlib.sha1(seed.encode()).hexdigest()[:10]

class PreviewEngine:
    def __init__(self):
        self.preset = PresetEngine() if _HAS_PRESET else None
        self.imgsvc = ImageService() if _HAS_IMAGE else None

    def _variations_for_prompt(self, base_prompt: str, n: int = 3):
        # create simple variations by adding style/mood modifiers
        modifiers = [
            "cinematic lighting, ultra-detailed, 4k",
            "soft pastel colors, studio portrait, bokeh",
            "high contrast, dramatic rim light, filmic"
        ]
        # if n more than modifiers, add random adjectives
        out = []
        for i in range(n):
            mod = modifiers[i % len(modifiers)] if i < len(modifiers) else "high quality"
            # small random tweak
            tweak = random.choice(["", ", octane render", ", volumetric light", ", portrait lens"])
            out.append(f"{base_prompt}, {mod}{tweak}")
        return out

    def generate_candidates(self, script_text: str, preset_key: str | None = None, n: int = 3, out_prefix: str | None = None):
        """
        Returns list of {prompt, image_path}
        """
        # determine base prompt
        if self.preset and preset_key:
            try:
                meta = self.preset.prepare_prompt_only(preset_key, extra=None)
                base_prompt = meta.get("prompt")
            except Exception:
                base_prompt = script_text or "portrait"
        elif self.preset:
            # auto-pick preset from script heuristics - reuse PresetEngine if available
            try:
                # naive: use first preset if nothing matched
                lst = self.preset.list_presets()
                if lst:
                    key = lst[0]["key"]
                    meta = self.preset.prepare_prompt_only(key, extra=None)
                    base_prompt = meta.get("prompt")
                else:
                    base_prompt = script_text or "portrait"
            except Exception:
                base_prompt = script_text or "portrait"
        else:
            base_prompt = script_text or "portrait, detailed"

        variations = self._variations_for_prompt(base_prompt, n=n)

        results = []
        for idx, var in enumerate(variations):
            seed = _safe(var + str(time.time()) + str(idx))
            fname = out_prefix or f"preview_{seed}_{idx}.png"
            out_path = OUT / fname
            # try image service
            if self.imgsvc:
                try:
                    img = self.imgsvc.generate(prompt=var, out_filename=str(out_path.name))
                    results.append({"prompt": var, "image": img})
                    continue
                except Exception as e:
                    # fallback to placeholder below
                    print("ImageService failed for preview:", e)

            # fallback placeholder using PIL
            try:
                from PIL import Image, ImageDraw, ImageFont
                w,h = 512,512
                img = Image.new("RGB", (w,h), color=(30+idx*20,30,50+idx*30))
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", 16)
                except Exception:
                    font = ImageFont.load_default()
                txt = var[:180]
                draw.multiline_text((10,10), txt, fill=(240,240,240), font=font)
                img.save(out_path)
                results.append({"prompt": var, "image": str(out_path)})
            except Exception as e:
                results.append({"prompt": var, "image": None, "error": str(e)})

        return results
