# services/bone_alias.py
"""
Provide bone alias map and auto-detect best bone name for common slots.
"""
COMMON_ALIASES = {
    "RightHand": ["RightHand","right_hand","hand.R","hand_R","r_hand","Hand_R","Right_Hand"],
    "LeftHand": ["LeftHand","left_hand","hand.L","hand_L","l_hand","Left_Hand"],
    "Spine": ["spine","Spine","hips","Hips","pelvis","Pelvis"],
    "Head": ["head","Head","HeadTop","neck","Neck"]
}

def find_best_bone(target_bone_list, desired_alias):
    desired_candidates = COMMON_ALIASES.get(desired_alias, [desired_alias])
    # try exact then similarity
    for cand in desired_candidates:
        for b in target_bone_list:
            if b.lower() == cand.lower():
                return b
    # fallback: substring match
    for cand in desired_candidates:
        for b in target_bone_list:
            if cand.lower() in b.lower() or b.lower() in cand.lower():
                return b
    # else return first bone
    return target_bone_list[0] if target_bone_list else None
