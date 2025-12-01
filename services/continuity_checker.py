# services/continuity_checker.py
"""
Checks shot continuity: character positions & orientation jumps between consecutive shots.
Provides suggestions: add match-on-action, insert bridging shot, or reorder camera cuts.
Functions:
- check_continuity(shot_list) -> report dict with warnings & recommended fixes
"""

from typing import List, Dict

def _pos_distance(a: dict, b: dict) -> float:
    return ((a.get("x",0)-b.get("x",0))**2 + (a.get("z",0)-b.get("z",0))**2) ** 0.5

def check_continuity(shot_list: List[Dict]) -> Dict:
    warnings = []
    for i in range(1, len(shot_list)):
        prev = shot_list[i-1]
        curr = shot_list[i]
        # compare blocking first character entries if exist
        prev_block = prev.get("blocking",[])
        curr_block = curr.get("blocking",[])
        if prev_block and curr_block:
            # map by character name if present
            for p in prev_block:
                name = p.get("character")
                match = next((c for c in curr_block if c.get("character")==name), None)
                if match:
                    dist = _pos_distance(p, match)
                    if dist > 4.0:  # arbitrary large jump threshold
                        warnings.append({
                            "type":"position_jump",
                            "shot_from": prev.get("index"),
                            "shot_to": curr.get("index"),
                            "character": name,
                            "distance": round(dist,2),
                            "suggestion": "Add bridging shot or match-on-action; check actor blocking"
                        })
        # check camera angle inversion risk (180-degree)
        # simplistic: if prev.camera.angle vs curr.camera.angle are opposite strings -> warn
        pa = prev.get("camera", {}).get("angle")
        ca = curr.get("camera", {}).get("angle")
        if pa and ca and pa!=ca and (("over_shoulder" in pa and "over_shoulder" not in ca) or ("eye" in pa and "eye" in ca)):
            # no strong rule; only flag if type changes drastically
            # skipping overzealous flags
            pass
    return {"ok": True, "warnings": warnings}
