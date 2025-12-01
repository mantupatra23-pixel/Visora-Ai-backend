# tools/install_sample_luts.py
from pathlib import Path
ROOT = Path(".").resolve()
lut_dir = ROOT / "assets" / "luts"
lut_dir.mkdir(parents=True, exist_ok=True)
identity = lut_dir / "identity.cube"
if not identity.exists():
    identity.write_text("""# identity.cube
LUT_3D_SIZE 2
0 0 0
0 0 1
0 1 0
0 1 1
1 0 0
1 0 1
1 1 0
1 1 1
""", encoding="utf-8")
print("Installed sample LUTs at", lut_dir)
