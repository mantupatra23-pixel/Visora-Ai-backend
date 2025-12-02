#!/usr/bin/env python3
"""
Apply a .cube LUT using OpenColorIO Python (if available).
Usage:
  python3 scripts/apply_lut_ocio.py --input in.png --output out.png --cube assets/luts/teal_orange.cube
"""
import argparse, PyOpenColorIO as ocio, cv2, numpy as np
from pathlib import Path

def load_cube_as_processor(cube_path):
    # use FileTransform with LUT file
    tr = ocio.FileTransform()
    tr.setSrc(cube_path)
    tr.setInterpolation(ocio.Constants.INTERP_LINEAR)
    config = ocio.GetCurrentConfig()
    proc = config.getProcessor(tr)
    return proc

def apply_processor_to_image(proc, img_bgr):
    # OCIO expects RGB floats 0..1
    h,w = img_bgr.shape[:2]
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype('float32')/255.0
    # flatten to Nx3
    flat = rgb.reshape(-1,3)
    # create CPU processor
    cpu_proc = proc.getDefaultCPUProcessor()
    # prepare output array
    out = cpu_proc.applyRGB(flat.tolist())
    out_np = np.array(out).reshape(h,w,3)
    out_bgr = cv2.cvtColor((out_np*255.0).astype('uint8'), cv2.COLOR_RGB2BGR)
    return out_bgr

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--cube", required=True)
    args = p.parse_args()
    inp = Path(args.input)
    out = Path(args.output)
    img = cv2.imread(str(inp))
    proc = load_cube_as_processor(str(Path(args.cube).resolve()))
    out_img = apply_processor_to_image(proc, img)
    cv2.imwrite(str(out), out_img)

if __name__=="__main__":
    main()
