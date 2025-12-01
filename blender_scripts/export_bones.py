# blender_scripts/export_bones.py
"""
blender --background rig.blend --python blender_scripts/export_bones.py -- /path/to/out_bones.json
"""
import sys, json
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv=[]
if len(argv)<1:
    print("out path needed")
    exit(1)
out = argv[0]
import bpy
arm = None
for ob in bpy.data.objects:
    if ob.type=='ARMATURE':
        arm = ob
        break
if arm is None:
    print("no armature")
    exit(2)
bones = [b.name for b in arm.data.bones]
open(out,"w").write(json.dumps(bones, indent=2))
print("exported bones to", out)
