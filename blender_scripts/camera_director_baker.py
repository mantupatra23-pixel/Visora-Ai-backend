# blender_scripts/camera_director_baker.py
import bpy, sys, json, os, math
from pathlib import Path
from mathutils import Vector, Euler
# allow importing local modules
SCRIPT_DIR = Path(__file__).parent
import sys as _sys
_sys.path.append(str(SCRIPT_DIR))
# import helper rigs
from camera_rigs import create_dolly_rig, create_drone_orbit, add_handheld_noise, add_camera

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def load_job(jobfile):
    return json.loads(Path(jobfile).read_text())

def ensure_scene(scene_file=None):
    if scene_file and Path(scene_file).exists():
        bpy.ops.wm.open_mainfile(filepath=str(scene_file))
        return
    bpy.ops.wm.read_factory_settings(use_empty=True)

def create_camera_for_shot(shot_name, preset):
    # preset: dict with focal, distance, type etc.
    focal = preset.get("focal",50)
    cam = add_camera(shot_name+"_cam", focal=focal)
    # position camera depending on type
    t = preset.get("type","medium")
    if t == "closeup":
        cam.location = Vector((0, -preset.get("distance",1.0), 1.6))
    elif t == "wide":
        cam.location = Vector((0, -preset.get("distance",8.0), 4.0))
    elif t == "drone":
        # create drone orbit rig
        cam, empty = create_drone_orbit(cam_name=shot_name + "_drone", center=(0,0,1.5), radius=preset.get("orbit_radius",6.0), altitude=preset.get("altitude",6.0))
    else:
        cam.location = Vector((0, -preset.get("distance",2.5), 1.6))
    return cam

def keyframe_camera_location(cam, frame, loc=None, rot=None):
    if loc:
        cam.location = Vector(loc)
        cam.keyframe_insert(data_path="location", frame=frame)
    if rot:
        cam.rotation_euler = Euler((math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2])), 'XYZ')
        cam.keyframe_insert(data_path="rotation_euler", frame=frame)

def apply_shot_sequence(job, out_dir):
    plan = job.get("plan", {})
    timeline = plan.get("timeline", [])
    presets_map = {}
    # load presets from assets
    import json as _json
    presets_file = Path("assets/camera_presets.json")
    if presets_file.exists():
        presets_map = _json.loads(presets_file.read_text())
    from services.shot_presets import load_presets
    if not presets_map:
        presets_map = load_presets()

    cameras = []
    cur_frame = 1
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = plan.get("total_frames", 240)

    for item in timeline:
        shot_key = item['shot']
        frames = item['frames']
        preset = presets_map.get(shot_key, presets_map.get("medium", {"focal":50,"distance":2.5,"type":"medium"}))
        cam = create_camera_for_shot(shot_key, preset)
        # camera movement heuristics by shot type
        if shot_key in ("close_up","intense_close"):
            # slow push in
            start_loc = cam.location.copy()
            end_loc = start_loc + Vector((0, 0.3, 0))
            keyframe_camera_location(cam, item['start_frame'], loc=start_loc)
            keyframe_camera_location(cam, item['start_frame'] + frames - 1, loc=end_loc)
            # gentle depth of field (set focus distance)
            if cam.data:
                cam.data.dof.use_dof = True
                cam.data.dof.focus_distance = preset.get("distance",1.0)
        elif shot_key == "drone_orbit" or preset.get("type") == "drone":
            # rotate parent empty for orbit
            # if cam has parent empty created in create_drone_orbit, animate its rotation
            parent = cam.parent
            if parent:
                parent.rotation_euler = (0,0,0)
                parent.keyframe_insert(data_path="rotation_euler", frame=item['start_frame'])
                parent.rotation_euler = (0,0,math.radians(360))
                parent.keyframe_insert(data_path="rotation_euler", frame=item['start_frame'] + frames - 1)
        elif shot_key == "car_follow" or preset.get("type") == "car_follow":
            # simple translation along X axis as car movement
            start = cam.location.copy()
            end = start + Vector((frames*0.05, 0, 0))
            keyframe_camera_location(cam, item['start_frame'], loc=start)
            keyframe_camera_location(cam, item['start_frame'] + frames - 1, loc=end)
        else:
            # static with small zoom in/out
            keyframe_camera_location(cam, item['start_frame'], loc=cam.location.copy())
            keyframe_camera_location(cam, item['start_frame'] + frames - 1, loc=cam.location.copy())

        # optionally add handheld shake for action/tense
        if shot_key in ("handheld","action_sequence"):
            add_handheld_noise(cam, amplitude=0.02, start=item['start_frame'], end=item['start_frame']+frames-1)
        cameras.append({"cam": cam.name, "start": item['start_frame'], "frames": frames})
        cur_frame += frames
    # after cameras created, optionally render preview frames or export cameras
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # export camera animation to FBX for external pipeline
    fbx_out = out_dir / (job['job_id'] + "_cameras.fbx")
    bpy.ops.export_scene.fbx(filepath=str(fbx_out), use_selection=False, bake_space_transform=True)
    # optional: render frames with active camera switching per shot
    # We'll set scene.camera to shot camera per shot and render frame ranges to images (fast preview)
    for c in cameras:
        cam_obj = bpy.data.objects.get(c['cam'])
        if not cam_obj: continue
        # set camera and render its shot range
        scene.camera = cam_obj
        start = c['start']; end = c['start'] + c['frames'] - 1
        scene.frame_start = start; scene.frame_end = end
        scene.render.filepath = str(out_dir / f"{c['cam']}_frame_")
        # use quick render (no heavy settings)
        try:
            bpy.ops.render.render(animation=True)
        except Exception as e:
            print("render failed for", c['cam'], e)
    return {"ok": True, "fbx": str(fbx_out)}

if __name__ == "__main__":
    argv = _args()
    if len(argv) < 2:
        print("usage: blender --background --python camera_director_baker.py -- job.json outdir")
        sys.exit(1)
    jobfile, outdir = argv[0], argv[1]
    job = load_job(jobfile)
    ensure_scene(job.get("options",{}).get("scene_file"))
    res = apply_shot_sequence(job, outdir)
    print(res)
