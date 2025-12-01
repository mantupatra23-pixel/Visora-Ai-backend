# services/image_engine.py
import os
from pathlib import Path
import time

OUT_DIR = Path("static/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Try to import diffusers pipeline
_HAS_DIFFUSERS = False
try:
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
    import torch
    _HAS_DIFFUSERS = True
except Exception as e:
    print("Diffusers not available:", e)
    _HAS_DIFFUSERS = False

class ImageService:
    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or os.getenv("SD_MODEL", "runwayml/stable-diffusion-v1-5")
        # device: "cuda" or "cpu"
        self.device = device or ("cuda" if (torch and torch.cuda.is_available()) else "cpu") if _HAS_DIFFUSERS else "cpu"
        self.pipe = None
        if _HAS_DIFFUSERS:
            self._load_pipeline()

    def _load_pipeline(self):
        try:
            # Load pipeline (may download weights on first run)
            self.pipe = StableDiffusionPipeline.from_pretrained(self.model_name, torch_dtype=torch.float16 if self.device=="cuda" else None)
            # Use a faster scheduler if available
            try:
                self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(self.pipe.scheduler.config)
            except Exception:
                pass
            self.pipe = self.pipe.to(self.device)
            # reduce safety checks for speed (be mindful of safety)
            return True
        except Exception as e:
            print("Failed to load SD pipeline:", e)
            self.pipe = None
            return False

    def generate(self, prompt: str, out_filename: str = None, num_inference_steps: int = 20, guidance_scale: float = 7.5, height: int = 512, width: int = 512):
        """
        Generates an image and returns relative path.
        If diffusers not available, returns placeholder image path.
        """
        if not prompt:
            raise ValueError("Empty prompt")

        out_filename = out_filename or f"img_{abs(hash(prompt))%10_000_000}.png"
        out_path = OUT_DIR / out_filename

        if _HAS_DIFFUSERS and self.pipe is not None:
            try:
                generator = None
                # If using CPU, keep generator None for default
                image = self.pipe(prompt, height=height, width=width, num_inference_steps=num_inference_steps, guidance_scale=guidance_scale).images[0]
                image.save(out_path)
                return str(out_path)
            except Exception as e:
                print("Image generation failed:", e)
                # fallback to placeholder below

        # Fallback placeholder - create a simple PNG with prompt text (PIL)
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (width, height), color=(40, 40, 40))
            draw = ImageDraw.Draw(img)
            # try to draw prompt (may need default font)
            text = (prompt[:200] + "...") if len(prompt) > 200 else prompt
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
            draw.text((10, 10), text, fill=(255,255,255), font=font)
            img.save(out_path)
            return str(out_path)
        except Exception as e:
            # last resort: return a static placeholder path
            placeholder = OUT_DIR / "placeholder.png"
            if not placeholder.exists():
                # create minimal binary PNG (1x1)
                with open(placeholder, "wb") as f:
                    f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\xdac\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x02\xef\x00\x00\x00\x00IEND\xaeB`\x82")
            return str(placeholder)
