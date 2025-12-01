# tools/download_vfx_assets.py
import os
import requests
from pathlib import Path

ASSETS = {
    "sfx": [
        # replace these with actual permissive-license URLs or your GDrive links
        ("tiger_roar.mp3", "https://example.com/freesfx/tiger_roar.mp3"),
        ("footstep1.wav", "https://example.com/freesfx/footstep1.wav")
    ],
    "ambience": [
        ("rain_loop.mp3", "https://example.com/freesfx/rain_loop.mp3")
    ],
    "music": [
        ("tense_loop.mp3", "https://example.com/freesfx/tense_loop.mp3")
    ],
    "vfx": [
        ("smoke_sprite.png", "https://example.com/vfx/smoke_sprite.png")
    ]
}

ROOT = Path(".").resolve()
for folder, items in ASSETS.items():
    d = ROOT / "assets" / folder
    d.mkdir(parents=True, exist_ok=True)
    for fname, url in items:
        out = d / fname
        if out.exists():
            print("exists:", out)
            continue
        print("downloading", url, "->", out)
        try:
            r = requests.get(url, stream=True, timeout=60)
            r.raise_for_status()
            with open(out, "wb") as f:
                for chunk in r.iter_content(1024*32):
                    f.write(chunk)
            print("saved", out)
        except Exception as e:
            print("failed", url, e)
