# blender_scripts/lipsync_baker.py
import bpy, json, sys
from pathlib import Path

def _args():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--")+1:]
    return []

def apply_phonemes(obj, phonemes, start_frame=1):
    f = start_frame
    for ph in phonemes:
        sk = obj.data.shape_keys.key_blocks.get(ph)
        if sk:
            sk.value = 1.0
            sk.keyframe_insert("value", frame=f)
            sk.value = 0.0
            sk.keyframe_insert("value", frame=f+2)
        f += 3

if __name__=="__main__":
    args = _args()
    if len(args)<3:
        print("usage: blender --python lipsync_baker.py -- obj phoneme_json out")
        sys.exit(0)

    obj_name, phoneme_file, out = args
    obj = bpy.data.objects.get(obj_name)
    ph = json.loads(Path(phoneme_file).read_text())
    apply_phonemes(obj, ph.get("phonemes", []))
    bpy.ops.wm.save_mainfile(filepath=out)
