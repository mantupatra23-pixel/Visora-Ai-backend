# services/lens_picker.py
import math

# Simple circle-of-confusion values for common sensors (approx)
COC = {
    "full_frame": 0.030,  # mm
    "aps-c": 0.019,
    "micro_four_thirds": 0.015
}

def hyperfocal(focal_mm, fstop, coc):
    # hyperfocal distance in mm
    return (focal_mm**2) / (fstop * coc) + focal_mm

def depth_of_field(focal_mm, fstop, subject_dist_m, coc=0.03):
    # return near and far focus distances in meters
    H = hyperfocal(focal_mm, fstop, coc)
    s = subject_dist_m * 1000.0  # to mm
    near = (H * s) / (H + (s - focal_mm))
    far = (H * s) / (H - (s - focal_mm)) if (H - (s - focal_mm)) != 0 else float('inf')
    return near/1000.0, (far/1000.0 if far != float('inf') else float('inf'))

def pick_lens_for_shot(desired_dof='shallow', subject_distance_m=2.0, sensor='full_frame', desired_focal_hint=None):
    """
    desired_dof: 'shallow'|'medium'|'deep'
    Returns: dict {focal_mm, fstop, focus_distance_m, coc}
    """
    coc = COC.get(sensor, 0.03)
    # heuristic focal choices
    if desired_focal_hint:
        focal = desired_focal_hint
    else:
        # choose focal length based on shot style
        focal = 85 if desired_dof == 'shallow' else (50 if desired_dof=='medium' else 24)
    # choose fstop: shallow -> low f-number, deep -> high f-number
    if desired_dof=='shallow':
        fstop = 1.8
    elif desired_dof=='medium':
        fstop = 4.0
    else:
        fstop = 8.0
    near, far = depth_of_field(focal, fstop, subject_distance_m, coc)
    return {"focal_mm": focal, "fstop": fstop, "focus_distance_m": subject_distance_m, "near_m": near, "far_m": far, "coc": coc}
