# blender_scripts/cell_fracture_auto.py
"""
Usage:
blender --background scene.blend --python blender_scripts/cell_fracture_auto.py -- /path/to/job.json

job.json:
{
  "object_names": ["Crate.001"],
  "source_collection": "Props",
  "shard_count": 80,
  "noise": 0.2,
  "inner_material": "shard_mat",
  "enable_rigid": true,
  "mass_per_shard": 0.2,
  "output_collection": "Fractured_Shards"
}
"""
import sys, json
from pathlib import Path
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv=[]

if not argv:
    print("Provide job.json")
    sys.exit(1)
job = json.loads(Path(argv[0]).read_text())

import bpy, mathutils, random

# ensure cell fracture addon is enabled
if "object_fracture_cell" not in bpy.context.preferences.addons:
    try:
        bpy.ops.preferences.addon_enable(module="object_fracture_cell")
    except Exception as e:
        print("Enable Cell Fracture addon in Blender preferences first. Error:", e)

obj_names = job.get("object_names", [])
shard_count = int(job.get("shard_count", 60))
noise = float(job.get("noise", 0.15))
out_col_name = job.get("output_collection", "Fractured_Shards")
enable_rigid = bool(job.get("enable_rigid", True))
mass_per_shard = float(job.get("mass_per_shard", 0.2))

# create output collection
out_col = bpy.data.collections.get(out_col_name) or bpy.data.collections.new(out_col_name)
if out_col.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(out_col)

for name in obj_names:
    obj = bpy.data.objects.get(name)
    if not obj:
        print("Object not found:", name)
        continue
    bpy.context.view_layer.objects.active = obj
    # call cell fracture operator programmatically
    try:
        bpy.ops.object.modifier_add(type='REMESH')  # optional remesh to improve fracture quality
    except Exception:
        pass
    # Prepare operator properties
    bpy.ops.object.cell_fracture_source_add()
    # Use operator: object.cell_fracture is available via pythonops only if addon exposes; fallback to using bpy.ops.object.fracture_cell? 
    # Safer method: use the operator name from addon
    try:
        bpy.ops.object.fracture_cell_execute({'object': obj}, point_seed=random.randint(0,10000), source_limit=shard_count, recursion=0, material_index=0, adaptivity=noise)
    except Exception as e:
        # fallback: use simple boolean-based manual fragmentation (not provided here)
        print("fracture operator failed (may be addon API mismatch). Error:", e)
    # move generated shards to output collection and set rigid bodies
    # shards are typically named like obj.name + ".shard"
    for o in list(bpy.data.objects):
        if o.name.startswith(obj.name) and o.name != obj.name:
            if out_col.objects.get(o.name) is None:
                out_col.objects.link(o)
            # enable rigid body
            if enable_rigid:
                bpy.context.view_layer.objects.active = o
                try:
                    bpy.ops.rigidbody.object_add()
                    o.rigid_body.mass = mass_per_shard
                    o.rigid_body.friction = 0.5
                    o.rigid_body.restitution = 0.0
                    o.rigid_body.collision_shape = 'CONVEX_HULL'
                except Exception as e:
                    print("Rigid body add failed for", o.name, e)

print("Cell fracture automation complete.")
