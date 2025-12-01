# blender_scripts/export_shapekeys.py
"""
blender --background rig.blend --python blender_scripts/export_shapekeys.py -- mesh_name out.json
"""
import bpy, sys, json
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv=[]
if len(argv) < 2:
    print("mesh_name out.json needed"); exit(1)
mesh_name, out = argv[0], argv[1]
mesh = bpy.data.objects.get(mesh_name)
if not mesh:
    print("mesh not found"); exit(2)
keys = []
if mesh.data.shape_keys:
    keys = [k.name for k in mesh.data.shape_keys.key_blocks]
open(out,"w").write(json.dumps(keys, indent=2))
print("exported", len(keys), "shapekeys to", out)
