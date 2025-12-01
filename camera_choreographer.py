# blender_scripts/camera_choreographer_enhanced.py
import sys, json
from pathlib import Path
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv = []
if len(argv) < 2:
    print("Usage: ...camera_choreographer_enhanced.py -- job.json out_prefix")
    sys.exit(1)

jobfile = Path(argv[0])
out_prefix = Path(argv[1])
job = json.loads(jobfile.read_text())

import bpy
from mathutils import Vector
scene = bpy.context.scene
fps = scene.render.fps or 25

# import helpers (ensure repo root on sys.path if needed)
import sys as _sys
_repo_root = Path.cwd()
if str(_repo_root) not in _sys.path:
    _sys.path.append(str(_repo_root))

from services.shot_selector import heuristic_selector, ml_rescorer
from services.visibility import check_visibility, DEFAULT_PARAMS as VIS_DEFAULT
from services.multi_framing import compute_centroid, two_shot_positions
from blender_scripts.multi_reframe import create_two_shot_camera
from blender_scripts.spline_camera_moves import create_spline_path, attach_camera_to_path, add_camera_shake
from services.camera_moves import move_params_for_shot

# Step 1: shot planning
timeline = job.get("timeline", {})
preset = job.get("preset", {})
shots = heuristic_selector(timeline, preset)
shots = ml_rescorer(shots, {})  # optional ML rescore

# Step 2: For each shot create camera; use visibility check and re-try offset search if occluded
def attempt_place_camera_for_shot(shot):
    # speaker-based framing
    speaker = shot.get("speaker")
    if speaker:
        # find object by name
        target = next((o for o in bpy.data.objects if (o.type in ('ARMATURE','MESH') and (speaker==o.name or speaker in o.name))), None)
        if target:
            # create cam
            cam_data = bpy.data.cameras.new(shot.get("name","cam"))
            cam_obj = bpy.data.objects.new(shot.get("name","camobj"), cam_data)
            bpy.context.collection.objects.link(cam_obj)
            # basic frame near target
            cam_obj.location = target.matrix_world.translation + Vector((0,-3,1.2))
            cam_data.lens = 50
            # check visibility
            vis_cfg = VIS_DEFAULT
            vis = check_visibility(cam_obj, target, samples=vis_cfg['samples'], radius=vis_cfg['sample_radius'], occlusion_threshold=vis_cfg['occlusion_threshold'])
            attempts = 0
            while not vis['ok'] and attempts < vis_cfg['max_attempts']:
                # nudge camera sideways / up to try to avoid occlusion
                cam_obj.location.x += 0.4 * ((-1)**attempts)
                cam_obj.location.z += 0.12 * attempts
                vis = check_visibility(cam_obj, target, samples=vis_cfg['samples'], radius=vis_cfg['sample_radius'], occlusion_threshold=vis_cfg['occlusion_threshold'])
                attempts += 1
            return cam_obj, target, vis
    # fallback: master camera
    cam_data = bpy.data.cameras.new("fallback_cam")
    cam_obj = bpy.data.objects.new("fallback_camobj", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = Vector((0,-10,3))
    cam_data.lens = 35
    return cam_obj, None, {"ok": True}
# create and animate cameras
exported_shots = []
for idx, s in enumerate(shots):
    sname = s.get("type","shot") + f"_{idx}"
    s['name'] = sname
    start = s.get("start",0.0); end = s.get("end", start+2.0)
    cam_obj, target_obj, vis = attempt_place_camera_for_shot(s)
    # add basic keyframes: position constant or simple reframe
    sf = int(start*fps) + scene.frame_start
    ef = int(end*fps) + scene.frame_start
    scene.frame_set(sf)
    cam_obj.keyframe_insert(data_path="location", frame=sf)
    scene.frame_set((sf+ef)//2)
    # generate small move depending on shot type using camera_moves
    params = move_params_for_shot(s.get("type"))
    if params['type']=="dolly_in":
        # push forward slightly toward target
        if target_obj:
            midpos = (cam_obj.location + target_obj.matrix_world.translation) / 2.0
            cam_obj.location = midpos
    elif params['type']=="subtle_reframe":
        cam_obj.location.x += 0.08
    # keyframe mid & end
    midf = (sf+ef)//2
    scene.frame_set(midf)
    cam_obj.keyframe_insert(data_path="location", frame=midf)
    scene.frame_set(ef)
    cam_obj.keyframe_insert(data_path="location", frame=ef)
    # optionally create path for smoother cinematic move
    path = create_spline_path(sname + "_path", [tuple(cam_obj.location), tuple(cam_obj.location + Vector((0,0.8,-0.1))), tuple(cam_obj.location)])
    attach_camera_to_path(cam_obj, path, sf, ef)
    # add gentle shake for high-emphasis shots
    if s.get("type")=="close" or (s.get("speaker") and s.get("type")=="medium" and s.get("end")-s.get("start")<1.0):
        add_camera_shake(cam_obj, amount=0.01, freq=6.0, start_frame=sf, end_frame=ef)
    exported_shots.append({"name": sname, "start": start, "end": end, "camera": cam_obj.name, "vis": vis})

# export JSON & FBX & save blend
out_prefix.mkdir(parents=True, exist_ok=True)
shots_file = out_prefix / "shots_enhanced.json"
shots_file.write_text(json.dumps({"shots": exported_shots}, indent=2))
bpy.ops.export_scene.fbx(filepath=str(out_prefix / "cameras_enhanced.fbx"), use_selection=False, apply_unit_scale=True, bake_space_transform=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out_prefix / "directed_enhanced.blend"))
print("Enhanced directing complete. wrote:", str(shots_file), str(out_prefix / "cameras_enhanced.fbx"))
