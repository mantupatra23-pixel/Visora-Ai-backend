# blender_scripts/multi_reframe.py
"""
Given two or more character objects, generate cameras for two-shot / OTS / group framing.
This script is intended to be imported from camera_choreographer.py
"""
import bpy
from mathutils import Vector
from services.multi_framing import compute_centroid, two_shot_positions

def create_two_shot_camera(name, obj_a, obj_b, lens=35, offset_factor=1.0):
    mid = (obj_a.matrix_world.translation + obj_b.matrix_world.translation) / 2.0
    pair = two_shot_positions(obj_a.matrix_world.translation, obj_b.matrix_world.translation, distance_factor=offset_factor)
    cam = bpy.data.cameras.new(name)
    cam_obj = bpy.data.objects.new(name, cam)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = pair["camera_pos"]
    cam.lens = lens
    cam_obj.rotation_euler = (1.2, 0.0, 0.0)
    return cam_obj
