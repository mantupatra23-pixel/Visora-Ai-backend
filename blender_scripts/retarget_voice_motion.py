# blender_scripts/retarget_voice_motion.py
"""
Run in Blender:
blender --background rig.blend --python blender_scripts/retarget_voice_motion.py -- /path/to/motion.bvh rig_name /out/prefix_
OR for NPZ motion: pass .npz and use custom mapping
"""
import sys, os
from pathlib import Path
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv = []
if len(argv) < 3:
    print("Usage: blender ... -- retarget_voice_motion.py <motion_file> <rig_name> <out_prefix>")
    sys.exit(1)

motion_file = Path(argv[0])
rig_name = argv[1]
out_prefix = argv[2]

import bpy

# import BVH if provided
if motion_file.suffix.lower() == ".bvh":
    bpy.ops.import_anim.bvh(filepath=str(motion_file), axis_forward='-Z', axis_up='Y', global_scale=1.0)
    mocap_arm = bpy.context.selected_objects[0]
else:
    # if npz, expect exported joint transforms — user must implement custom importer
    print("NPZ import not implemented in this script. Provide BVH for now.")
    sys.exit(2)

# find target rig
target = bpy.data.objects.get(rig_name)
if not target:
    # try startswith
    for ob in bpy.data.objects:
        if ob.type=='ARMATURE' and ob.name.startswith(rig_name):
            target = ob
            break
if not target:
    print("target rig not found:", rig_name)
    sys.exit(3)

# basic retarget method: add copy transforms constraints per bone using a small bone mapping
# simplest approach: copy whole armature transforms per bone name if matching
mapping = {}
for bone in mocap_arm.pose.bones:
    if bone.name in target.pose.bones:
        mapping[bone.name] = bone.name

# apply copy transforms and bake
for src_name, tgt_name in mapping.items():
    tgt_b = target.pose.bones[tgt_name]
    const = tgt_b.constraints.new('COPY_TRANSFORMS')
    const.target = mocap_arm
    const.subtarget = src_name

# bake action
scene = bpy.context.scene
start = scene.frame_start
end = scene.frame_end
bpy.context.view_layer.objects.active = target
bpy.ops.nla.bake(frame_start=start, frame_end=end, only_selected=False, visual_keying=True, clear_constraints=True, use_current_action=True, bake_types={'POSE'})

# export FBX
out_fbx = str(Path(out_prefix) / "v2a_retargeted.fbx")
bpy.ops.export_scene.fbx(filepath=out_fbx, use_selection=False, apply_unit_scale=True, bake_space_transform=True)
print("Exported retargeted FBX:", out_fbx)
