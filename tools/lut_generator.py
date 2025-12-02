# tools/lut_generator.py
import numpy as np, json, math
from pathlib import Path

def write_cube(path, lut, size=33, title="VisoraLUT"):
    p = Path(path)
    with p.open("w") as fh:
        fh.write(f"# Created by Visora\nLUT_3D_SIZE {size}\n")
        for b in lut.reshape(-1,3):
            fh.write(f"{b[0]:.6f} {b[1]:.6f} {b[2]:.6f}\n")

def generate_simple_lut_matrix(size=33, slope_rgb=(1.0,1.0,1.0), offset_rgb=(0.0,0.0,0.0), power_rgb=(1.0,1.0,1.0)):
    # produce normalized LUT (0..1)
    lin = np.linspace(0.0,1.0,size)
    lut = np.zeros((size,size,size,3), dtype=np.float32)
    for r_i,r in enumerate(lin):
        for g_i,g in enumerate(lin):
            for b_i,b in enumerate(lin):
                r2 = ((r * slope_rgb[0]) + offset_rgb[0]) ** power_rgb[0]
                g2 = ((g * slope_rgb[1]) + offset_rgb[1]) ** power_rgb[1]
                b2 = ((b * slope_rgb[2]) + offset_rgb[2]) ** power_rgb[2]
                lut[r_i,g_i,b_i] = [r2,g2,b2]
    return lut

def create_teal_orange_cube(out_path="luts/teal_orange.cube", size=33):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    # simple approx by scaling blues/reds (not perfect cinematic LUT but ok as starting point)
    lut = generate_simple_lut_matrix(size=size, slope_rgb=(0.9,1.0,1.1), offset_rgb=(0.02,0.0,-0.03), power_rgb=(0.98,1.0,0.95))
    write_cube(out_path, lut, size=size)
    return out_path

if __name__=="__main__":
    from pathlib import Path
    Path("luts").mkdir(exist_ok=True)
    print("Generating sample LUTs...")
    print(create_teal_orange_cube("luts/teal_orange.cube", size=33))
