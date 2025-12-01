# tools/blendshape_suggester.py
"""
Input:
 - generated_blend_names.json  (list of names produced by model, e.g., ['mouth_open','smile_R',...])
 - target_shapekeys.json       (list of shapekey names from Blender)
Output:
 - mapping.json  {gen_name: shapekey_name or null}
"""
import json, difflib, sys
def suggest(src_list, tgt_list):
    mapping = {}
    for s in src_list:
        candidates = difflib.get_close_matches(s, tgt_list, n=1, cutoff=0.45)
        if candidates:
            mapping[s] = candidates[0]
            continue
        # heuristics: remove digits/underscores, try substrings
        s_norm = ''.join([c for c in s.lower() if c.isalpha()])
        found = next((t for t in tgt_list if s_norm in ''.join([c for c in t.lower() if c.isalpha()])), None)
        mapping[s] = found
    return mapping

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: python tools/blendshape_suggester.py generated.json target.json out.json")
        sys.exit(1)
    src = json.load(open(sys.argv[1]))
    tgt = json.load(open(sys.argv[2]))
    out = sys.argv[3]
    mapping = suggest(src, tgt)
    json.dump(mapping, open(out, "w"), indent=2)
    print("wrote", out)
