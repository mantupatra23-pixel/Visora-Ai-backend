# blender_scripts/vfx_helpers.py
"""
Blender VFX helper functions:
- add_debris_emitter(scene, location, start_frame, end_frame, amount)
- add_smoke_fire(scene, location, start_frame, end_frame, density)
- add_camera_shake(cam_obj, start_frame, end_frame, strength, scale)
- quick_add_flash(scene, start_frame, duration_frames)
Notes: these functions are generic helpers — adjust particle settings / materials per your project.
"""

import bpy
import math
import random
from mathutils import Vector

def _ensure_collection(name):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col

def add_debris_emitter(location=(0,0,0), start_frame=1, end_frame=30, amount=120, name_prefix="debris"):
    col = _ensure_collection("VFX_Debris")
    # create emitter mesh (a small plane)
    mesh = bpy.data.meshes.new(f"{name_prefix}_mesh")
    obj = bpy.data.objects.new(f"{name_prefix}_emitter", mesh)
    col.objects.link(obj)
    # simple create a plane
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=0.05)
    bm.to_mesh(mesh)
    bm.free()
    obj.location = Vector(location)
    # add particle system
    ps = obj.modifiers.new(name="debris_ps", type='PARTICLE_SYSTEM')
    psettings = ps.particle_system.settings
    psettings.count = amount
    psettings.frame_start = start_frame
    psettings.frame_end = min(end_frame, start_frame + 5)
    psettings.lifetime = (end_frame - start_frame) * 1.2
    psettings.physics_type = 'NEWTON'
    psettings.render_type = 'OBJECT'
    # create debris object for render (small icosphere)
    icos = bpy.data.meshes.new(f"{name_prefix}_piece")
    ico_obj = bpy.data.objects.new(f"{name_prefix}_piece_obj", icos)
    col.objects.link(ico_obj)
    import bmesh
    bm2 = bmesh.new()
    bmesh.ops.create_icosphere(bm2, subdivisions=1, diameter=0.06)
    bm2.to_mesh(icos)
    bm2.free()
    psettings.instance_object = ico_obj
    # add some random velocity
    psettings.normal_factor = 3.0
    psettings.factor_random = 1.8
    return obj

def add_smoke_fire(location=(0,0,0), start_frame=1, end_frame=60, density=1.0, name_prefix="smoke"):
    col = _ensure_collection("VFX_Smoke")
    # create flow object (a UV sphere)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=location)
    flow = bpy.context.selected_objects[0]
    flow.name = f"{name_prefix}_flow"
    # ensure domain exists (create a cube domain)
    dom_name = f"{name_prefix}_domain"
    bpy.ops.mesh.primitive_cube_add(size=4.0, location=location)
    domain = bpy.context.selected_objects[0]
    domain.name = dom_name
    # quick add smoke domain modifier
    try:
        bpy.context.view_layer.objects.active = domain
        bpy.ops.object.modifier_add(type='SMOKE')
        domain.modifiers["Smoke"].smoke_type = 'DOMAIN'
        domain.modifiers["Smoke"].domain_settings.resolution_max = 64
        # add flow
        bpy.context.view_layer.objects.active = flow
        bpy.ops.object.modifier_add(type='SMOKE')
        flow.modifiers["Smoke"].smoke_type = 'FLOW'
        flow.modifiers["Smoke"].flow_settings.flow_type = 'SMOKE'
        flow.modifiers["Smoke"].flow_settings.flow_source = 'MESH'
        # keyframe visibility for flow
        flow.hide_render = False
        flow.keyframe_insert(data_path="hide_render", frame=start_frame-1)
        flow.hide_render = False
        flow.keyframe_insert(data_path="hide_render", frame=start_frame)
        flow.hide_render = True
        flow.keyframe_insert(data_path="hide_render", frame=end_frame+1)
    except Exception as e:
        print("Smoke addition may need Blender smoke system available:", e)
    return flow, domain

def add_camera_shake(cam_obj, start_frame=1, end_frame=30, strength=0.2, scale=1.0):
    """
    Add noise modifiers to camera location fcurves between frames.
    strength ~ magnitude in Blender units.
    """
    if cam_obj.animation_data is None:
        cam_obj.animation_data_create()
    # Ensure location fcurves exist by keyframing at start and end
    for axis in range(3):
        cam_obj.location[axis] += 0.0
        cam_obj.keyframe_insert(data_path=f"location", index=axis, frame=max(1, start_frame-1))
        cam_obj.keyframe_insert(data_path=f"location", index=axis, frame=end_frame+1)
    # add noise modifier
    act = cam_obj.animation_data.action
    for fcu in act.fcurves:
        mod = fcu.modifiers.new(type='NOISE')
        mod.strength = strength * scale
        mod.scale = 5.0
        mod.phase = random.random() * 10.0
    return True

def quick_add_flash(scene, start_frame=1, duration_frames=3, intensity=1.0):
    """
    Add a quick white plane in front of camera and keyframe its alpha for flash effect
    """
    # create plane in camera local space
    cam = scene.camera
    if cam is None:
        return None
    # create plane
    bpy.ops.mesh.primitive_plane_add(size=10, location=cam.location + cam.matrix_world.to_quaternion() @ Vector((0, -3, 0)))
    plane = bpy.context.active_object
    plane.name = "vfx_flash"
    # material
    mat = bpy.data.materials.new(name="flash_mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Emission'].default_value = (1.0,1.0,1.0,1)
        bsdf.inputs['Emission Strength'].default_value = 20.0 * intensity
    plane.data.materials.append(mat)
    # keyframe visibility (fade out)
    plane.keyframe_insert(data_path="hide_render", frame=start_frame-1)
    plane.hide_render = False
    plane.keyframe_insert(data_path="hide_render", frame=start_frame)
    plane.hide_render = True
    plane.keyframe_insert(data_path="hide_render", frame=start_frame + duration_frames)
    return plane
