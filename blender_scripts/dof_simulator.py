# blender_scripts/dof_simulator.py
# run inside Blender
import bpy, json, sys
from pathlib import Path
from mathutils import Vector

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def apply_lens_settings(cam_name, focal_mm, fstop, focus_distance_m, bokeh_blades=7, blade_rotation=0.0):
    cam = bpy.data.objects.get(cam_name)
    if not cam:
        print("camera not found:", cam_name)
        return False
    cam.data.lens = float(focal_mm)
    # DOF
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = float(focus_distance_m)
    # Blender uses fstop via aperture fstop in camera.data.dof.aperture_fstop
    try:
        cam.data.dof.aperture_fstop = float(fstop)
    except Exception:
        pass
    # Bokeh blades - for Cycles, set camera sensor? Not always available across versions; try nodes
    print(f"Applied lens: {focal_mm}mm f/{fstop}, focus {focus_distance_m}m to {cam_name}")
    return True

if __name__=="__main__":
    argv = _args()
    if len(argv) < 5:
        print("usage: blender --background --python dof_simulator.py -- cam_name focal_mm fstop focus_m")
        sys.exit(1)
    cam_name = argv[0]; focal=argv[1]; fstop=argv[2]; focus=argv[3]
    apply_lens_settings(cam_name, focal, fstop, focus)
