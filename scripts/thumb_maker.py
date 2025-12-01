#!/usr/bin/env python3
# scripts/thumb_maker.py
import sys, os
from services.promo_generator import make_thumbnail_from_video
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: thumb_maker.py <video> [time_sec] [overlay_text]")
        sys.exit(1)
    video = sys.argv[1]
    t = float(sys.argv[2]) if len(sys.argv)>2 else 1.0
    txt = sys.argv[3] if len(sys.argv)>3 else None
    r = make_thumbnail_from_video(video, time_sec=t, overlay_text=txt)
    print(r)
