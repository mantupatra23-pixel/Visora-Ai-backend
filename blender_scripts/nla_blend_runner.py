# blender_scripts/nla_blend_runner.py
import bpy, sys, json
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent
import sys as _sys
_sys.path.append(str(SCRIPT_DIR))
from nla_blend_utils import merge_and_crossfade_actions

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def main(scene_path, object_name, actions_json_path):
    if Path(scene_path).exists():
        bpy.ops.wm.open_mainfile(filepath=str(scene_path))
    obj = bpy.data.objects.get(object_name)
    if not obj:
        print("object not found:", object_name); return {"ok": False}
    actions_list = json.loads(Path(actions_json_path).read_text())
    actions_with_starts = []
    for item in actions_list:
        act = bpy.data.actions.get(item['action'])
        if not act:
            print("Action missing:", item['action']); continue
        actions_with_starts.append((act, item['start']))
    strips = merge_and_crossfade_actions(obj, actions_with_starts, blend_frames= item.get('blend_frames', 12))
    print("NLA strips created:", [s.name for s in strips])
    return {"ok": True}

if __name__=="__main__":
    argv = _args()
    if len(argv) < 3:
        print("usage: blender --background --python nla_blend_runner.py -- scene.blend object_name actions.json")
        sys.exit(1)
    print(main(argv[0], argv[1], argv[2]))
