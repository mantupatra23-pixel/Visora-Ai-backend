# blender_scripts/multicam_baker.py
"""
Creates multiple cameras and places cuts according to multicam plan.
Then renders each camera segment separately (fast preview) and writes EDL (simple).
Usage:
 blender --background --python multicam_baker.py -- plan.json outdir
"""
import bpy, sys, json
from pathlib import Path
from mathutils import Vector

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def make_camera(name, loc, focal=50):
    camdata = bpy.data.cameras.new(name + "_data")
    cam = bpy.data.objects.new(name, camdata)
    bpy.context.collection.objects.link(cam)
    cam.location = Vector(loc)
    camdata.lens = focal
    return cam

def load_plan(path):
    return json.loads(Path(path).read_text())

def run(planfile, outdir):
    plan = load_plan(planfile)
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    # create camera presets
    cams = {
        "wide": make_camera("Cam_wide", (0,-10,5), focal=24),
        "close": make_camera("Cam_close", (0,-2,1.6), focal=85),
        "dolly": make_camera("Cam_dolly", (0,-6,2), focal=50),
        "handheld": make_camera("Cam_handheld", (1.0,-3,1.8), focal=50)
    }
    scene = bpy.context.scene
    # For each timeline slot, set active camera and render that segment
    for slot in plan.get("timeline", []):
        # pick camera with highest weight
        cams_sorted = sorted(slot['cameras'], key=lambda c: c['weight'], reverse=True)
        cam_name = cams_sorted[0]['name']
        scene.camera = cams[cam_name]
        start = slot['start_frame']; end = start + slot['frames'] - 1
        scene.frame_start = start; scene.frame_end = end
        scene.render.filepath = str(outdir / f"{cam_name}_frame_")
        try:
            bpy.ops.render.render(animation=True)
        except Exception as e:
            print("render fail", e)
    # output simple edl mapping by chosen cams
    edl = []
    for i,slot in enumerate(plan.get("timeline", []), start=1):
        choice = sorted(slot['cameras'], key=lambda c: c['weight'], reverse=True)[0]['name']
        edl.append({"event": i, "cam": choice, "start": slot['start_frame'], "end": slot['start_frame']+slot['frames']-1})
    Path(outdir / "multicam_edl.json").write_text(json.dumps(edl, indent=2))
    return {"ok": True, "out": str(outdir)}
