# blender_scripts/face_retarget.py
"""
Blender script to retarget facial landmarks / blendshape outputs into your rig.
Inputs:
 - face_anim.json or npz (landmarks + blendshape weights per frame)
 - target rig in scene (armature or mesh with shapekeys)
 - mapping config: landmark->bone or blendshape name -> shapekey

Usage:
blender --background scene_with_rig.blend --python blender_scripts/face_retarget.py -- /path/to/anim.npz target_rig_name mapping.json /out/prefix_
"""
import sys, json, os
from pathlib import Path

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv = []

if len(argv) < 4:
    print("Usage: face_retarget.py <anim_npz> <rig_name> <mapping.json> <out_prefix>")
    sys.exit(1)

anim_npz = Path(argv[0])
rig_name = argv[1]
mapping_file = Path(argv[2])
out_prefix = argv[3]

import bpy
import numpy as np

data = np.load(str(anim_npz))

# expected keys: 'blendshapes' (T x N) or 'landmarks' (T x 68 x 2)
if 'blendshapes' in data:
    bsh = data['blendshapes']  # shape (T, N)
else:
    bsh = None

mapping = json.loads(mapping_file.read_text())

# find target mesh with shapekeys or armature
mesh = None
arm = None
for ob in bpy.data.objects:
    if ob.name == rig_name and ob.type=='ARMATURE':
        arm = ob
    if ob.type=='MESH' and ob.parent and ob.parent == arm:
        mesh = ob

if mesh is None and arm is None:
    print("Target rig/mesh not found")
    sys.exit(2)

# simple approach: if shapekeys present, keyframe shapekeys per frame
if bsh is not None and mesh and mesh.data.shape_keys:
    key_blocks = mesh.data.shape_keys.key_blocks
    for t in range(bsh.shape[0]):
        bpy.context.scene.frame_set(int(t)+1)
        weights = bsh[t]
        for i, val in enumerate(weights):
            mapped = mapping.get(str(i))  # mapping of blend index -> shapekey name
            if mapped and mapped in key_blocks:
                key_blocks[mapped].value = float(val)
                key_blocks[mapped].keyframe_insert("value")
    # export baked FBX
    out_fbx = str(Path(out_prefix) / "face_retargeted.fbx")
    bpy.ops.export_scene.fbx(filepath=out_fbx, use_selection=False, apply_unit_scale=True, bake_space_transform=True)
    print("Exported", out_fbx)
    sys.exit(0)

# fallback: landmark-driven bone rotations (not implemented here)
print("No blendshapes found or mapping provided. Provide blendshape mapping for automatic retarget.")
sys.exit(3)
