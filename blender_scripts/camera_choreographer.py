# blender_scripts/camera_choreographer.py
"""
Camera Choreographer (Headless Blender)
Usage:
blender scene.blend --background --python blender_scripts/camera_choreographer.py -- /path/to/job.json /out/prefix_
Output:
 - <out_prefix>shots.json   (shot list with start/end, camera name, lens, move type)
 - <out_prefix>cameras.fbx  (animated cameras)
 - <out_prefix>edl.xml      (Resolve XML or simple EDL)
"""
import sys, json, math, os
from pathlib import Path

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv = []
if len(argv) < 2:
    print("Usage: ... camera_choreographer.py -- job.json out_prefix")
    sys.exit(1)

jobfile = Path(argv[0])
out_prefix = Path(argv[1])
job = json.loads(jobfile.read_text())

import bpy
from mathutils import Vector, Euler

scene = bpy.context.scene

# Utilities
def find_character_by_name(name):
    for ob in bpy.data.objects:
        if ob.type in ('ARMATURE','MESH') and (ob.name == name or name in ob.name):
            return ob
    return None

def bbox_center_world(obj):
    # compute world bounding box center
    mat = obj.matrix_world
    bb = [mat @ Vector(corner) for corner in obj.bound_box]
    center = sum(bb, Vector((0,0,0))) / 8.0
    minz = min([v.z for v in bb])
    maxz = max([v.z for v in bb])
    return center, (minz, maxz)

def create_camera(name):
    cam_data = bpy.data.cameras.new(name + "_cam")
    cam = bpy.data.objects.new(name + "_camobj", cam_data)
    bpy.context.collection.objects.link(cam)
    return cam

def frame_character(cam, target_obj, lens=35, distance_factor=2.0, shot_type="medium"):
    # place camera to frame character bounding box using simple heuristics
    center, (minz, maxz) = bbox_center_world(target_obj)
    height = maxz - minz
    # desired distance based on lens and shot type
    if shot_type == "wide":
        df = 4.0
    elif shot_type == "close":
        df = 0.9
    else:
        df = 2.0
    # compute offset along -Y axis in local world coordinates
    cam.location = center + Vector((0.0, -height*df*distance_factor, height*0.3))
    cam.rotation_euler = Euler((math.radians(75), 0, 0), 'XYZ')
    cam.data.lens = lens
    return cam

# Build shots based on timeline beats or segments
timeline = job.get("timeline", {})
preset = job.get("preset", {})
shots = []
cur_t = 0.0
duration = timeline.get("duration", 10.0)
beats = timeline.get("beats") or []
segments = timeline.get("segments") or []

# simple plan:
# - Master wide shot covering entire stage from t=0
# - For each beat/segment, create a shot based on speaker: close on speaker for emphasis, else medium
out_shots = []
camera_objs = []

# Master shot
master_cam = create_camera("master")
# choose lens from preset
lens_choice = preset.get("lens",[35,50,85])[0]
# frame whole scene: use scene bounds
# approximate by average of all chars
chars = [o for o in bpy.data.objects if o.type in ('ARMATURE','MESH') and o.name.lower()!='camera']
if chars:
    avg = sum([bbox_center_world(c)[0] for c in chars], Vector((0,0,0))) / len(chars)
    master_cam.location = avg + Vector((0.0, -10.0, 3.0))
    master_cam.rotation_euler = Euler((math.radians(75),0,0),'XYZ')
    master_cam.data.lens = lens_choice
else:
    master_cam.location = Vector((0,-10,3)); master_cam.rotation_euler = Euler((1.2,0,0)); master_cam.data.lens = lens_choice

camera_objs.append(master_cam)
out_shots.append({"name":"master","start":0.0,"end":duration,"camera":master_cam.name,"shot_type":"wide","lens":int(master_cam.data.lens)})

# Now generate coverage from beats (simple)
cut_points = set([0.0, duration])
for b in beats:
    cut_points.add(round(b.get("t",0.0),3))
cut_list = sorted(list(cut_points))
# For each interval, pick speaker (closest beat) and create camera if speaker exists
for i in range(len(cut_list)-1):
    s = cut_list[i]; e = cut_list[i+1]
    # find a beat within this interval with speaker
    beat = next((bb for bb in beats if bb.get("t")>=s and bb.get("t")<e and bb.get("speaker")), None)
    if beat:
        speaker = beat.get("speaker")
        char = find_character_by_name(speaker)
        if char:
            # choose shot type based on emphasis
            emph = beat.get("emphasis",0.0)
            if emph > 0.6:
                shot_type = "close"
                lens = preset.get("lens")[-1] if preset.get("lens") else 85
            elif emph > 0.2:
                shot_type = "medium"
                lens = preset.get("lens")[1] if len(preset.get("lens",[]))>1 else 50
            else:
                shot_type = "medium"
                lens = preset.get("lens")[0]
            cam = create_camera(f"{speaker}_{i}")
            frame_character(cam, char, lens=lens, shot_type=shot_type)
            camera_objs.append(cam)
            out_shots.append({"name":f"{speaker}_{i}","start":s,"end":e,"camera":cam.name,"shot_type":shot_type,"lens":int(lens)})
        else:
            # fallback to master
            out_shots.append({"name":f"cut_{i}","start":s,"end":e,"camera":master_cam.name,"shot_type":"wide","lens":int(master_cam.data.lens)})
    else:
        out_shots.append({"name":f"cut_{i}","start":s,"end":e,"camera":master_cam.name,"shot_type":"wide","lens":int(master_cam.data.lens)})

# Optionally generate camera moves: insert keyframes for minor push-in/dolly
for cam in camera_objs:
    # simple tiny push forward during shot center
    # find associated shot
    assoc = [sh for sh in out_shots if sh.get("camera")==cam.name]
    if not assoc: continue
    for sh in assoc:
        start = sh["start"]; end = sh["end"]; mid = (start+end)/2.0
        # set keyframes at start/mid/end (world frame numbers based on fps)
        fps = scene.render.fps or 25
        ks = int(start*fps) + scene.frame_start
        km = int(mid*fps) + scene.frame_start
        ke = int(end*fps) + scene.frame_start
        # record original loc
        orig = cam.location.copy()
        # start
        scene.frame_set(ks)
        cam.keyframe_insert(data_path="location", frame=ks)
        # mid: push slightly toward target
        scene.frame_set(km)
        cam.location = orig + Vector((0.0, 0.5 if sh["shot_type"]!="close" else 0.2, -0.05))
        cam.keyframe_insert(data_path="location", frame=km)
        # end: restore
        scene.frame_set(ke)
        cam.location = orig
        cam.keyframe_insert(data_path="location", frame=ke)

# Export shot list JSON
out_prefix.mkdir(parents=True, exist_ok=True)
shots_file = out_prefix / "shots.json"
shots_data = {"job_id": job.get("job_id"), "shots": out_shots, "fps": scene.render.fps}
shots_file.write_text(json.dumps(shots_data, indent=2))
print("Wrote shots:", str(shots_file))

# Export cameras as FBX
fbx_out = out_prefix / "cameras.fbx"
bpy.ops.export_scene.fbx(filepath=str(fbx_out), use_selection=False, apply_unit_scale=True, bake_space_transform=True)
print("Exported cameras FBX:", str(fbx_out))

# Create a simple Resolve XML/EDL
xml_lines = ['<?xml version="1.0"?>','<edl>']
for idx, sh in enumerate(out_shots):
    xml_lines.append(f"<shot><id>{idx+1}</id><name>{sh['name']}</name><start>{sh['start']}</start><end>{sh['end']}</end><camera>{sh['camera']}</camera><lens>{sh['lens']}</lens></shot>")
xml_lines.append("</edl>")
(edl_out := out_prefix / "shots.edl").write_text("\n".join(xml_lines))
print("Wrote simple EDL:", str(edl_out))

# Save updated blend with cameras if needed
blend_out = out_prefix / "directed.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))
print("Saved directed blend:", str(blend_out))
