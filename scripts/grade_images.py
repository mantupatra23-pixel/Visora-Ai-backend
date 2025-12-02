# scripts/grade_images.py
import argparse, os, sys
import cv2, numpy as np
from pathlib import Path

def read_cube(cube_path):
    lines = [l.strip() for l in open(cube_path,'r').read().splitlines() if l.strip() and not l.startswith('#') and not l.startswith('TITLE')]
    size = 0
    for l in lines:
        if l.startswith("LUT_3D_SIZE"):
            size = int(l.split()[1])
            break
    # get numeric lines after header
    nums = []
    for l in lines:
        if l.startswith("LUT_3D_SIZE"): continue
        parts = l.split()
        if len(parts)==3:
            nums.append([float(p) for p in parts])
    if size==0:
        # guess size as cube_root of lines
        size = int(round(len(nums) ** (1/3)))
    lut = np.array(nums).reshape((size,size,size,3))
    return lut

def apply_cube_to_image(img, lut):
    # img: BGR 0..255 numpy
    h,w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32)/255.0
    size = lut.shape[0]
    # map each channel to index
    idx = (rgb * (size-1)).clip(0, size-1)
    # trilinear interpolation
    x = idx[...,0]; y = idx[...,1]; z = idx[...,2]
    x0 = np.floor(x).astype(int); x1 = np.ceil(x).astype(int)
    y0 = np.floor(y).astype(int); y1 = np.ceil(y).astype(int)
    z0 = np.floor(z).astype(int); z1 = np.ceil(z).astype(int)
    xd = x - x0; yd = y - y0; zd = z - z0
    def lut_at(xi, yi, zi):
        return lut[xi, yi, zi]
    c000 = lut[x0, y0, z0]
    c100 = lut[x1, y0, z0]
    c010 = lut[x0, y1, z0]
    c001 = lut[x0, y0, z1]
    c101 = lut[x1, y0, z1]
    c011 = lut[x0, y1, z1]
    c110 = lut[x1, y1, z0]
    c111 = lut[x1, y1, z1]
    c00 = c000*(1-xd[...,None]) + c100*(xd[...,None])
    c01 = c001*(1-xd[...,None]) + c101*(xd[...,None])
    c10 = c010*(1-xd[...,None]) + c110*(xd[...,None])
    c11 = c011*(1-xd[...,None]) + c111*(xd[...,None])
    c0 = c00*(1-yd[...,None]) + c10*(yd[...,None])
    c1 = c01*(1-yd[...,None]) + c11*(yd[...,None])
    c = c0*(1-zd[...,None]) + c1*(zd[...,None])
    out = (c * 255.0).astype(np.uint8)
    out_bgr = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
    return out_bgr

def apply_curve_exposure_contrast(img, exposure=1.0, contrast=1.0):
    # img in BGR 0..255
    f = (259*(contrast+255))/(255*(259-contrast))
    out = cv2.convertScaleAbs(img, alpha=exposure, beta=0)
    # simple contrast: using linear formula
    out = np.clip(f*(out-128)+128, 0,255).astype(np.uint8)
    return out

def process_single(infile, outfile, cube=None, exposure=1.0, contrast=1.0):
    img = cv2.imread(str(infile))
    if img is None: raise RuntimeError("cannot read image")
    if cube:
        lut = read_cube(cube)
        img = apply_cube_to_image(img, lut)
    img = apply_curve_exposure_contrast(img, exposure=exposure, contrast=contrast)
    cv2.imwrite(str(outfile), img)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="input file or folder")
    parser.add_argument("--output", required=True, help="output file or folder")
    parser.add_argument("--cube", help=".cube LUT path (optional)")
    parser.add_argument("--exposure", type=float, default=1.0)
    parser.add_argument("--contrast", type=float, default=1.0)
    args = parser.parse_args()
    inp = Path(args.input)
    out = Path(args.output)
    if inp.is_dir():
        out.mkdir(parents=True, exist_ok=True)
        files = sorted([p for p in inp.iterdir() if p.suffix.lower() in [".png",".jpg",".jpeg"]])
        for p in files:
            target = out / p.name
            process_single(p, target, cube=args.cube, exposure=args.exposure, contrast=args.contrast)
    else:
        if out.is_dir():
            outf = out / inp.name
        else:
            outf = out
        process_single(inp, outf, cube=args.cube, exposure=args.exposure, contrast=args.contrast)

if __name__=="__main__":
    main()
