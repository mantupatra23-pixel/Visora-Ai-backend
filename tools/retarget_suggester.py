# tools/retarget_suggester.py
import difflib, json
from pathlib import Path
def suggest_mapping(source_joints, target_bones):
    mapping = {}
    for s in source_joints:
        # exact match
        if s in target_bones:
            mapping[s] = s
            continue
        # similarity
        best = difflib.get_close_matches(s, target_bones, n=1, cutoff=0.5)
        if best:
            mapping[s] = best[0]
            continue
        # heuristics (lowercase substring)
        low = s.lower()
        cand = [b for b in target_bones if low in b.lower() or b.lower() in low]
        if cand:
            mapping[s] = cand[0]
        else:
            mapping[s] = None
    return mapping

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python tools/retarget_suggester.py source_joints.json target_bones.json")
        sys.exit(1)
    src = json.load(open(sys.argv[1]))
    tgt = json.load(open(sys.argv[2]))
    print(json.dumps(suggest_mapping(src, tgt), indent=2))
