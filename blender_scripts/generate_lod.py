# blender_scripts/generate_lod.py
"""
Usage:
blender --background --python blender_scripts/generate_lod.py -- /path/to/model.glb /out/dir/LODNAME base_scale 0.5 "lod_levels" 
Example:
python args: input_model out_dir model_base_name "0.5,0.25,0.12"
"""
import sys, os, json
from pathlib import Path

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv = []

if len(argv) < 4:
    print("Usage: blender --background --python generate_lod.py -- input_model out_dir base_name lod_csv")
    sys.exit(1)

input_model = Path(argv[0])
out_dir = Path(argv[1])
base = argv[2]
lod_csv = argv[3]  # e.g., "0.5,0.25,0.12"
lods = [float(x) for x in lod_csv.split(",")]

import bpy
from mathutils import Vector, Euler

# import model
ext = input_model.suffix.lower()
if ext in [".glb", ".gltf"]:
    bpy.ops.import_scene.gltf(filepath=str(input_model))
elif ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=str(input_model))
else:
    bpy.ops.import_scene.obj(filepath=str(input_model))

objs = list(bpy.context.selected_objects)
if not objs:
    print("No objects imported.")
    sys.exit(2)

out_dir.mkdir(parents=True, exist_ok=True)

# apply decimate for each lod level
for i, r in enumerate(lods):
    # duplicate imported objects into collection for LOD
    bpy.ops.object.select_all(action='DESELECT')
    copies = []
    for o in objs:
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.duplicate()
        d = bpy.context.selected_objects[0]
        copies.append(d)
        d.select_set(False)
    # apply decimate
    for obj in copies:
        try:
            bpy.context.view_layer.objects.active = obj
            mod = obj.modifiers.new(name=f"Decimate_LOD_{i}", type='DECIMATE')
            mod.ratio = r
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception as e:
            print("Decimate error", e)
    # export glb
    outp = out_dir / f"{base}_lod{i+1}.glb"
    bpy.ops.export_scene.gltf(filepath=str(outp), export_format='GLB')
    print("Exported LOD:", outp)
# cleanup if needed
print("LOD generation complete.")
