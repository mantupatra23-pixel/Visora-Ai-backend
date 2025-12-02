#!/usr/bin/env python3
# tools/generate_high_quality_luts.py
"""
Generate higher-quality starter LUTs with multi-stage color transforms:
- lift / gamma / gain (shadows/mids/highlights)
- hue shifts (teal-orange split)
- filmic knee rolloff
Outputs 33x33x33 .cube files into assets/luts/
"""
import numpy as np
from pathlib import Path
from tools.lut_generator import write_cube
Path("assets/luts").mkdir(parents=True, exist_ok=True)

def filmic_tonemap(x):
    # simple filmic curve approximation
    a = 0.22; b = 0.3; c = 0.1; d = 0.2; e = 0.02; f = 0.3
    return ((x*(a*x + b)) / (x*(c*x + d) + e)) - f

def apply_lift_gamma_gain(rgb, lift=(0.0,0.0,0.0), gamma=(1.0,1.0,1.0), gain=(1.0,1.0,1.0)):
    r = ((rgb[...,0] + lift[0]) ** (1.0/gamma[0])) * gain[0]
    g = ((rgb[...,1] + lift[1]) ** (1.0/gamma[1])) * gain[1]
    b = ((rgb[...,2] + lift[2]) ** (1.0/gamma[2])) * gain[2]
    out = np.stack([r,g,b], axis=-1)
    return np.clip(out, 0.0, 1.0)

def teal_orange_transform(rgb):
    # push shadows cyan/teal, highlights orange
    # convert to luma-ish
    lum = 0.299*rgb[...,0] + 0.587*rgb[...,1] + 0.114*rgb[...,2]
    # map by luminance to tint factor
    tint = (lum[...,None] - 0.4) * 1.2  # highlights positive
    # teal in shadows (-) and orange in highlights (+)
    teal = np.array([0.0, 0.15, 0.2])
    orange = np.array([0.06, -0.01, -0.06])
    out = rgb + (tint.clip(-0.6,0.6) * orange) + ((- (1.0 - lum)[...,None]) * teal * 0.2)
    return np.clip(out, 0.0, 1.0)

def create_lut(name="hq_teal_orange", size=33):
    lin = np.linspace(0.0,1.0,size)
    lut = np.zeros((size,size,size,3), dtype=np.float32)
    for r_i,r in enumerate(lin):
        for g_i,g in enumerate(lin):
            for b_i,b in enumerate(lin):
                rgb = np.array([r,g,b], dtype=np.float32)
                # stage1: lift/gamma/gain subtle
                rgb = apply_lift_gamma_gain(rgb.reshape(1,1,3), lift=(-0.02,-0.01,-0.01), gamma=(0.95,0.98,1.02), gain=(1.02,1.01,0.98))[0,0]
                # stage2: teal-orange tone split
                rgb = teal_orange_transform(rgb)
                # stage3: filmic tonemap
                rgb = filmic_tonemap(rgb)
                lut[r_i,g_i,b_i] = np.clip(rgb,0,1)
    out_path = Path("assets/luts") / f"{name}.cube"
    write_cube(out_path, lut, size=size)
    print("Saved", out_path)
    return out_path

if __name__=="__main__":
    create_lut("hq_teal_orange", size=33)
    create_lut("hq_filmic", size=33)
    create_lut("hq_warm", size=33)
    print("High-quality starter LUTs created in assets/luts/")
