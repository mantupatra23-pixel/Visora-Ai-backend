#!/usr/bin/env python3
"""
Generate a few starter .cube LUTs (teal_orange, filmic-ish, warm, cold).
Creates files under assets/luts/.
"""
from pathlib import Path
from tools.lut_generator import write_cube, generate_simple_lut_matrix
import numpy as np

OUTDIR = Path("assets/luts"); OUTDIR.mkdir(parents=True, exist_ok=True)

def make_and_save(name, slope, offset, power, size=33):
    lut = generate_simple_lut_matrix(size=size, slope_rgb=slope, offset_rgb=offset, power_rgb=power)
    path = OUTDIR / f"{name}.cube"
    write_cube(path, lut, size=size)
    print("Saved", path)

if __name__=="__main__":
    # teal-orange (slightly boost red, reduce blue, mild contrast)
    make_and_save("teal_orange", slope=(0.95,1.0,1.05), offset=(0.01,0.0,-0.02), power=(0.98,1.0,0.96))
    # filmic-ish (gentle rolloff)
    make_and_save("filmic", slope=(1.02,1.01,0.98), offset=(0.0,0.0,0.0), power=(0.96,0.98,0.98))
    # warm
    make_and_save("warm", slope=(1.05,1.02,0.95), offset=(0.02,0.01,0.0), power=(1.0,1.0,0.98))
    # cold
    make_and_save("cold", slope=(0.95,1.0,1.05), offset=(0.0,0.0,0.02), power=(0.98,0.98,1.02))
    # high contrast
    make_and_save("hc", slope=(1.2,1.2,1.2), offset=(0.0,0.0,0.0), power=(0.9,0.9,0.9))
    print("All sample LUTs generated in assets/luts/")
