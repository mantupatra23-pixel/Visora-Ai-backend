# services/thumbnail_ab.py
"""
Generate A/B thumbnail variants automatically.
Strategies:
 - text overlay variants (big CTA / subtle)
 - color grade variants (warm/cool)
 - crop variants (center/left/right)
Provides functions:
  generate_variants(video_path, base_text, count=4) -> list of file paths
  pick_best_variant(metric='ctr') -> used by orchestrator after A/B run (requires analytics)
"""
import os, uuid, shlex, subprocess
from pathlib import Path
from services.promo_generator import _run

OUT = Path("static/promo_thumbs")
OUT.mkdir(parents=True, exist_ok=True)

def generate_variants(video_path: str, base_text: str = None, count: int = 4, times: list | None = None):
    times = times or [1.0, 2.0, 3.0, 0.5]
    variants = []
    for i in range(count):
        t = times[i % len(times)]
        out = OUT / f"thumb_ab_{uuid.uuid4().hex[:6]}_{i}.png"
        # basic: extract frame + overlay text variant + color adjust via ffmpeg
        draw = f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{(base_text or '')} {i+1}':fontcolor=white:fontsize={38 + i*4}:box=1:boxcolor=black@0.6:x=(w-text_w)/2:y=h-140"
        color = "eq=1.1:gamma=1.0" if i%2==0 else "eq=0.9:gamma=1.05"
        cmd = f"ffmpeg -y -ss {t} -i {shlex.quote(video_path)} -frames:v 1 -vf \"{draw},{color}\" {shlex.quote(str(out))}"
        r = _run(cmd)
        if r['ok']:
            variants.append(str(out))
    return {"ok": True, "variants": variants}
