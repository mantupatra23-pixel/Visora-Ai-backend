# blender_scripts/remap_abc_paths.py
"""
Usage:
blender some.blend --background --python blender_scripts/remap_abc_paths.py -- /old/prefix /new/prefix
"""
import sys
from pathlib import Path
import bpy
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv=[]
if len(argv) < 2:
    print("Need old_prefix new_prefix")
    sys.exit(1)
old_pref, new_pref = argv[0], argv[1]
for ob in bpy.data.objects:
    # Alembic path often saved in modifier or cache attribute: check modif.abc for Alembic
    for mod in ob.modifiers:
        try:
            if mod.type == 'MESH_SEQUENCE_CACHE' and hasattr(mod, 'filepath'):
                fp = mod.filepath
                if fp.startswith(old_pref):
                    newfp = fp.replace(old_pref, new_pref, 1)
                    mod.filepath = newfp
                    print("Remapped", fp, "->", newfp)
        except Exception:
            pass
    # Alembic modifier
    for mod in ob.modifiers:
        try:
            if mod.type == 'FLUID' and hasattr(mod, 'filepath'):
                fp = mod.filepath
                if fp.startswith(old_pref):
                    mod.filepath = fp.replace(old_pref, new_pref, 1)
        except Exception:
            pass
print("Remap complete")
