# extern/speech2motion/inference.py
# Usage: python extern/speech2motion/inference.py --audio /path.wav --ckpt /path.ckpt --out /path/out.npz --device cuda:0 --profile '{"style":"energetic"}'
import argparse, json, numpy as np, sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--audio", required=True)
parser.add_argument("--ckpt", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--device", default="cuda:0")
parser.add_argument("--profile", default="{}")
args = parser.parse_args()

AUDIO = Path(args.audio)
OUT = Path(args.out)
PROFILE = json.loads(args.profile)

# -----------------------------
# Replace below with real model load & inference
# -----------------------------
print("Stub Speech2Motion inference — replace with real model code", file=sys.stderr)
# Example fake output: time steps x joints (T x J)
# We'll produce small synthetic waving motion as placeholder
duration = 4.0
fps = 25
T = int(duration * fps)
J = 15  # pretend 15 joint channels
motion = np.zeros((T, J), dtype=np.float32)
# simple sinusoidal arm swing on columns 10-11
import math
for t in range(T):
    motion[t,10] = 20.0 * math.sin(2*math.pi*(t/T)*2.0)  # left arm swing
    motion[t,11] = 18.0 * math.sin(2*math.pi*(t/T)*2.0 + 0.3)
# save out
OUT.parent.mkdir(parents=True, exist_ok=True)
np.savez_compressed(str(OUT), motion=motion, fps=fps)
print("Wrote synthetic NPZ to", str(OUT))
