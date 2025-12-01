# blender_scripts/retarget_mocap.py
"""
Run inside Blender:
blender --background your_scene_with_rig.blend --python blender_scripts/retarget_mocap.py -- /path/to/mocap.bvh --out /path/to/output/fbx

This script:
- imports BVH
- finds target armature in scene by name (or uses first)
- retargets BVH action onto target via basic bone mapping (user may need to adjust mapping)
- bakes action and exports FBX
Note: This is a template — depending on rig naming you must update BONE_MAP.
"""
import sys, json, os
from pathlib import Path

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv = []

if len(argv) < 2:
    print("Usage: blender --background scene.blend --python blender_scripts/retarget_mocap.py -- /path/to/mocap.bvh /path/to/out.fbx")
    sys.exit(1)

bvh_path = Path(argv[0])
out_fbx = Path(argv[1])

import bpy

# Simple map: BVH joint names -> Rig bone names (user should adapt)
BONE_MAP = {
    "Hips": "hips",
    # add more mapping as per your rig
}

# import bvh
bpy.ops.import_anim.bvh(filepath=str(bvh_path), axis_forward='-Z', axis_up='Y', global_scale=1.0)
# imported armature is selected
imported = bpy.context.selected_objects[0]
imported.name = "MocapArmature"

# find target armature
target = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE' and obj.name != imported.name:
        target = obj
        break
if target is None:
    print("No target armature found in scene. Exiting.")
    sys.exit(2)

# basic retarget: copy transforms per frame from source to target using bone_map
scene = bpy.context.scene
start = scene.frame_start
end = scene.frame_end

# ensure pose mode
bpy.context.view_layer.objects.active = target

# create new action for target
target.animation_data_create()
action = bpy.data.actions.new(name="RetargetedAction")
target.animation_data.action = action

# For simplicity: bake object constraint - parent target to imported using Copy Transforms per bone (slow)
for src_bname, tgt_bname in BONE_MAP.items():
    if src_bname in imported.pose.bones and tgt_bname in target.pose.bones:
        src_b = imported.pose.bones[src_bname]
        tgt_b = target.pose.bones[tgt_bname]
        # add constraint on target bone
        const = tgt_b.constraints.new('COPY_TRANSFORMS')
        const.target = imported
        const.subtarget = src_bname

# bake action to remove constraints
bpy.ops.nla.bake(frame_start=start, frame_end=end, only_selected=False, visual_keying=True, clear_constraints=True, use_current_action=True, bake_types={'POSE'})

# export FBX
out_fbx.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(out_fbx), use_selection=False, apply_unit_scale=True, bake_space_transform=True)
print("Exported retargeted FBX to", out_fbx)
