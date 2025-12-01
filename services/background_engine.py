# services/background_engine.py
import re
from pathlib import Path
import random
import time
import hashlib

OUT = Path("static/outputs")
OUT.mkdir(parents=True, exist_ok=True)

# try to import ImageService (if present)
_HAS_IMAGE_SVC = False
try:
    from services.image_engine import ImageService
    _HAS_IMAGE_SVC = True
except Exception:
    _HAS_IMAGE_SVC = False

def _safe(seed: str):
    return hashlib.sha1(seed.encode()).hexdigest()[:10]

# small vocabulary -> mood mapping
MOOD_MAP = {
    "happy": ["bright", "sunlit", "cheerful", "vibrant", "warm colors"],
    "sad": ["moody", "muted colors", "rainy", "overcast", "cool tones"],
    "heroic": ["cinematic", "dramatic rim lighting", "epic clouds", "sunset backlight"],
    "mysterious": ["foggy", "neon lights", "night city", "low-key lighting"],
    "calm": ["soft morning light", "pastel colors", "serene landscape"],
    "angry": ["stormy", "high contrast", "dark clouds", "dramatic lighting"],
    "funny": ["cartoon background", "colorful studio", "playful props"]
}

# default background hints per preset (can be extended)
PRESET_BG_HINTS = {
    "anime_boy": ["studio portrait, soft bokeh background", "school rooftop at sunset", "city neon at night (anime style)"],
    "anime_girl": ["flower field at golden hour", "pastel studio room", "cinematic city lights"],
    "tiger_3d": ["cinematic jungle clearing", "ancient temple ruins at golden hour", "dramatic stormy cliffs"],
    "monkey_3d": ["tropical jungle, playful props", "treehouse playground", "bright cartoon forest"],
    "human_cartoon": ["minimalist studio", "vibrant gradient background", "office desk with soft light"]
}

def _extract_moods(text: str):
    text = (text or "").lower()
    found = set()
    for mood in MOOD_MAP.keys():
        if mood in text:
            found.add(mood)
    # also check for keywords
    keywords = {
        "hero": "heroic", "heroic": "heroic", "battle": "heroic",
        "love":"happy","romance":"happy","happy":"happy",
        "sad":"sad","cry":"sad","tears":"sad",
        "mystery":"mysterious","dark":"mysterious","night":"mysterious",
        "calm":"calm","peace":"calm","relax":"calm",
        "funny":"funny","comedy":"funny","joke":"funny",
        "angry":"angry","rage":"angry","fight":"angry"
    }
    for k,v in keywords.items():
        if k in text:
            found.add(v)
    return list(found)

class BackgroundEngine:
    def __init__(self):
        self.image_svc = ImageService() if _HAS_IMAGE_SVC else None

    def select_prompt(self, preset_key: str | None, script_text: str | None, explicit_mood: str | None = None):
        """
        Returns a crafted prompt string for image generation.
        """
        base_hints = PRESET_BG_HINTS.get(preset_key, [])
        moods = _extract_moods(script_text)
        if explicit_mood:
            moods.insert(0, explicit_mood)

        # choose a base hint from preset if any
        base = random.choice(base_hints) if base_hints else "cinematic background, high quality, detailed"
        mood_phrases = []
        for m in moods:
            mood_phrases += MOOD_MAP.get(m, [])

        # also infer environment from script: e.g., "space", "city", "forest", "office", "temple"
        env = None
        env_keywords = ["space","planet","city","jungle","forest","office","temple","beach","desert","mountain","school","stadium"]
        st = (script_text or "").lower()
        for ek in env_keywords:
            if ek in st:
                env = ek
                break

        prompt_parts = [base]
        if env:
            prompt_parts.append(f"{env} environment")
        if mood_phrases:
            prompt_parts.append(", ".join(mood_phrases[:3]))
        # some safety defaults
        prompt_parts.append("8k, ultra-detailed, cinematic lighting, high quality")

        prompt = ", ".join([p for p in prompt_parts if p])
        return prompt

    def generate_background(self, preset_key: str | None, script_text: str | None, explicit_mood: str | None = None, out_name: str | None = None):
        """
        Returns dict: {ok: True, prompt: "...", image: "static/outputs/xxx.png"}
        """
        prompt = self.select_prompt(preset_key, script_text, explicit_mood)
        seed = _safe(prompt + (script_text or "") + str(time.time()))
        out_name = out_name or f"bg_{seed}.png"
        out_path = OUT / out_name

        # Try to generate via ImageService if available
        if self.image_svc:
            try:
                # image_service.generate(prompt=..., out_filename=...) returns path
                img = self.image_svc.generate(prompt=prompt, out_filename=out_name)
                return {"ok": True, "prompt": prompt, "image": img}
            except Exception as e:
                # fallback to placeholder
                print("ImageService generate failed:", e)

        # Fallback: create simple placeholder image with prompt text
        try:
            from PIL import Image, ImageDraw, ImageFont
            w,h = 1280,720
            img = Image.new("RGB", (w,h), color=(30,30,30))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", 20)
            except Exception:
                font = ImageFont.load_default()
            text = f"BG Prompt:\n{prompt[:400]}"
            draw.multiline_text((20,20), text, fill=(230,230,230), font=font)
            img.save(out_path)
            return {"ok": True, "prompt": prompt, "image": str(out_path)}
        except Exception as e:
            return {"ok": False, "error": str(e), "prompt": prompt}
