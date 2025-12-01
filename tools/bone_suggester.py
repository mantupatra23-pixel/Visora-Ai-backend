# tools/bone_suggester.py
"""
Usage:
python tools/bone_suggester.py bones_list.json
bones_list.json should be a JSON array of bone names extracted from Blender (use blender_scripts/export_bones.py earlier)
Outputs suggested mapping for common slots.
"""
import sys, json
from services.bone_alias import COMMON_ALIASES, find_best_bone

if len(sys.argv) < 2:
    print("usage: bones_list.json")
    sys.exit(1)
bones = json.load(open(sys.argv[1]))
slots = list(COMMON_ALIASES.keys())
mapping = {}
for s in slots:
    b = find_best_bone(bones, s)
    mapping[s] = b
print(json.dumps(mapping, indent=2))
