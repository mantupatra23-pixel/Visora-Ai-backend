# blender_scripts/retarget_v2a_full.py
"""
Usage:
blender --background rig.blend --python blender_scripts/retarget_v2a_full.py -- <motion_file> <rig_name> <mapping.json or 'none'> <out_prefix>
- motion_file: .bvh or .npz (npz must include 'motion' array shape (T, J) and 'fps')
- mapping.json: for npz, provide JSON mapping { "0": "Spine", "10": "LeftArm", ... } where keys are motion indices
"""
import sys, json, os
from pathlib import Path

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv = []
if len(argv) < 4:
    print("Usage: <motion_file> <rig_name> <mapping.json|'none'> <out_prefix>")
    sys.exit(1)

motion_file = Path(argv[0])
rig_name = argv[1]
mapping_in = argv[2]
out_prefix = Path(argv[3])
out_prefix.parent.mkdir(parents=True, exist_ok=True)

import bpy
import numpy as np

# find target rig
target = bpy.data.objects.get(rig_name)
if not target:
    for ob in bpy.data.objects:
        if ob.type == 'ARMATURE' and ob.name.startswith(rig_name):
            target = ob
            break
if not target:
    print("Target rig not found:", rig_name)
    sys.exit(2)

if motion_file.suffix.lower() == ".bvh":
    # import BVH and retarget via copy transforms then bake (simple)
    bpy.ops.import_anim.bvh(filepath=str(motion_file), axis_forward='-Z', axis_up='Y', global_scale=1.0)
    mocap_arm = bpy.context.selected_objects[0]
    # build mapping: use bones with same name if available
    mapping = {b.name: b.name for b in mocap_arm.pose.bones if b.name in target.pose.bones}
    # add copy transforms constraints
    for src, tgt in mapping.items():
        tb = target.pose.bones[tgt]
        c = tb.constraints.new('COPY_TRANSFORMS')
        c.target = mocap_arm
        c.subtarget = src
    # bake to action
    scene = bpy.context.scene
    bpy.context.view_layer.objects.active = target
    bpy.ops.nla.bake(frame_start=scene.frame_start, frame_end=scene.frame_end, only_selected=False, visual_keying=True, clear_constraints=True, use_current_action=True, bake_types={'POSE'})
    out_fbx = str(out_prefix / (motion_file.stem + "_retargeted.fbx"))
    bpy.ops.export_scene.fbx(filepath=out_fbx, use_selection=False, apply_unit_scale=True, bake_space_transform=True)
    print("Exported", out_fbx)
    sys.exit(0)

# NPZ path: need mapping file
if not motion_file.exists():
    print("motion file missing:", motion_file); sys.exit(3)
data = np.load(str(motion_file))
motion = data.get("motion")
fps = int(data.get("fps", 25))
if motion is None:
    print("NPZ missing 'motion' array"); sys.exit(4)
# mapping JSON
mapping = {}
if mapping_in and mapping_in.lower() != "none":
    mp = Path(mapping_in)
    if not mp.exists():
        print("mapping file missing:", mp); sys.exit(5)
    mapping = json.loads(mp.read_text())

# Create an empty armature skeleton that will be animated by motion indices or try to map directly to target bones
# Approach: for each mapped index -> bone name, create copy transforms driver from a helper empty, or directly keyframe target bone rotation values
scene = bpy.context.scene
start_frame = scene.frame_start
for t_idx in range(motion.shape[0]):
    frame = start_frame + t_idx
    scene.frame_set(frame)
    row = motion[t_idx]
    # for each mapping index
    for idx_str, bone_name in mapping.items():
        idx = int(idx_str)
        val = float(row[idx])
        if bone_name in target.pose.bones:
            pb = target.pose.bones[bone_name]
            # we will keyframe a single euler channel Zrotation as example
            # convert val degrees to radians
            import math
            rot = math.radians(val)
            pb.rotation_mode = 'XYZ'
            # set a simple rotation on X axis as demo
            pb.rotation_euler[0] = rot
            pb.keyframe_insert(data_path="rotation_euler", frame=frame, index=0)
# after keyframing, export FBX
out_fbx = str(out_prefix / (motion_file.stem + "_npz_retargeted.fbx"))
bpy.ops.export_scene.fbx(filepath=out_fbx, use_selection=False, apply_unit_scale=True, bake_space_transform=True)
print("Exported NPZ retargeted FBX:", out_fbx)
