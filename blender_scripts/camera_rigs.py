# blender_scripts/camera_rigs.py
"""
Helper to create different camera rigs in Blender: dolly, crane, drone, car-follow, handheld (noise).
This file runs inside Blender (bpy).
"""
import bpy, math, random
from mathutils import Vector, Euler

def add_camera(name="Cam", focal=50):
    cam_data = bpy.data.cameras.new(name + "_data")
    cam_obj = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_data.lens = focal
    return cam_obj

def create_dolly_rig(cam_name="Cam_Dolly", start_loc=(0,-6,1.6)):
    cam = add_camera(cam_name, focal=50)
    cam.location = Vector(start_loc)
    # create empty target for dolly (to parent)
    empty = bpy.data.objects.new(cam_name + "_track", None)
    empty.empty_display_size = 0.2
    bpy.context.collection.objects.link(empty)
    # parent camera to empty for dolly movement
    cam.parent = empty
    return cam, empty

def create_drone_orbit(cam_name="Cam_Drone", center=(0,0,1.5), radius=6.0, altitude=6.0):
    cam = add_camera(cam_name, focal=35)
    # create an empty at center
    empty = bpy.data.objects.new(cam_name + "_orbit_center", None)
    bpy.context.collection.objects.link(empty)
    empty.location = Vector(center)
    # position camera at radius
    cam.location = Vector((center[0] + radius, center[1], altitude))
    # parent camera to empty & set rotation to look at center
    cam.parent = empty
    cam.constraints.new(type='TRACK_TO').target = empty
    return cam, empty

def add_handheld_noise(obj, amplitude=0.02, freq=3.0, start=1, end=240):
    # add small animated noise to object location
    for f in range(start, end+1):
        t = (f - start) / (end - start + 1)
        obj.location.x += (random.uniform(-1,1) * amplitude * (1.0 - 0.5*abs(0.5 - t)))
        obj.location.y += (random.uniform(-1,1) * amplitude * (1.0 - 0.5*abs(0.5 - t)))
        obj.keyframe_insert(data_path="location", frame=f)
