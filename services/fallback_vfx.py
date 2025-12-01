# services/fallback_vfx.py
"""
Fallback 2D VFX helpers for moviepy pipeline.
- apply_action_effects(clip, beat) : returns modified clip
- add_impact_flash(composite, time, duration, size)
- shake_clip(clip, magnitude, freq)
Note: moviepy lacks advanced motion blur; use ffmpeg filters for better effect if needed.
"""

import random
from moviepy.editor import vfx, ImageClip, CompositeVideoClip
import numpy as np

def shake_clip(clip, magnitude=15, freq=15):
    import math
    def jitter(t):
        return (int(random.uniform(-magnitude, magnitude)), int(random.uniform(-magnitude/2, magnitude/2)))
    return clip.set_position(lambda t: jitter(t))

def zoom_in_clip(clip, zoom_factor=1.15):
    # simulate zoom by resizing progressively
    def resizer(t):
        # t in seconds within clip.duration
        frac = t / max(clip.duration, 0.001)
        return 1.0 + (zoom_factor - 1.0) * frac
    return clip.fl_time(lambda t: t).resize(lambda t: resizer(t))

def impact_flash(composite, start_time, duration=0.15, color=(255,255,255)):
    # add a short white clip overlay at start_time
    w,h = composite.size
    flash = ImageClip(np.full((h,w,3), color, dtype='uint8')).set_duration(duration).set_start(start_time).set_opacity(0.9)
    return CompositeVideoClip([composite, flash])

def apply_action_effects(clip, beat):
    typ = beat.get('type', '')
    vfxs = beat.get('vfx', [])
    dur = beat.get('duration', clip.duration)
    out = clip.set_duration(dur)
    if 'motion_blur' in vfxs:
        # crude approximation: add semi-transparent blurred duplicate offset behind
        blurred = out.fx(vfx.blur, 3)
        out = CompositeVideoClip([blurred.set_opacity(0.4), out])
    if beat.get('camera',{}).get('shake', False):
        out = shake_clip(out, magnitude=int(20 * beat.get('camera',{}).get('intensity',1.0)))
    if 'flash' in vfxs or 'impact' in typ:
        # create a tiny flash at middle of clip
        mid = dur * 0.5
        out = impact_flash(out, start_time=mid, duration=0.12)
    if 'motion_blur' in vfxs and hasattr(out, 'fx'):
        try:
            out = out.fx(vfx.colorx, 1.02)
        except Exception:
            pass
    # zoom for slam/jump
    if typ in ('jump','slam','impact'):
        out = zoom_in_clip(out, zoom_factor=1.18)
    return out
