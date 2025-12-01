# blender_scripts/check_visibility.py
"""
Check camera->target visibility by sampling multiple rays from camera to points on target's bbox/surface.
Usage within other Blender scripts: import or call main_check_visibility(camera_obj, target_obj, params)
"""
import bpy, math, random
from mathutils import Vector

def sample_target_points(obj, n=9, radius=0.15):
    # sample points around object's bounding box center
    mat = obj.matrix_world
    bb = [mat @ Vector(c) for c in obj.bound_box]
    center = sum(bb, Vector((0,0,0))) / 8.0
    pts = [center]
    for i in range(n-1):
        # jitter around center
        jitter = Vector((random.uniform(-radius,radius), random.uniform(-radius,radius), random.uniform(-radius,radius)))
        pts.append(center + jitter)
    return pts

def is_point_visible(cam_obj, target_point, ignore_objects=None):
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    origin = cam_obj.matrix_world.translation
    direction = (target_point - origin).normalized()
    # ray_cast returns (hit, location, normal, index, object, matrix)
    hit, loc, normal, face_index, ob, mat = scene.ray_cast(depsgraph, origin, direction, distance=(origin - target_point).length)
    if not hit:
        return True
    # if hit object is the target (or child) then visible, otherwise occluded
    if ignore_objects and ob and ob.name in ignore_objects:
        return True
    return False

def check_visibility(cam_obj, target_obj, samples=9, radius=0.15, occlusion_threshold=0.25, ignore_objects=None):
    pts = sample_target_points(target_obj, n=samples, radius=radius)
    occluded = 0
    for p in pts:
        if not is_point_visible(cam_obj, p, ignore_objects=ignore_objects):
            occluded += 1
    frac = occluded / float(samples)
    ok = frac <= occlusion_threshold
    return {"ok": ok, "occluded_fraction": frac, "occluded": occluded, "samples": samples}
