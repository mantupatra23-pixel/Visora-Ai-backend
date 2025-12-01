# blender_scripts/physics_worker.py
"""
Run inside Blender:
blender --background scene.blend --python blender_scripts/physics_worker.py -- /path/to/job.json /out/prefix_
This script:
- loads job JSON
- sets up simulation parameters (rigid body, cloth, softbody, smoke, fluid, cell fracture)
- bakes simulation frames into caches
- optionally renders frames or exports Alembic/FBX caches
Note: This is a template; adapt per your .blend structure and object names.
"""
import sys, json, os
from pathlib import Path

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv = []

if len(argv) < 2:
    print("Usage: blender --background scene.blend --python blender_scripts/physics_worker.py -- /path/to/job.json /out/prefix_")
    sys.exit(1)

jobfile = Path(argv[0])
out_prefix = argv[1]
with open(jobfile, "r") as f:
    job = json.load(f)

import bpy
from mathutils import Vector

# helper
def ensure_scene_loaded():
    # assume current scene is correct (or load from job['scene_blend'] earlier)
    return bpy.context.scene

scene = ensure_scene_loaded()
start_frame, end_frame = job.get("frames", [1, 250])
scene.frame_start = int(start_frame)
scene.frame_end = int(end_frame)
scene.frame_set(scene.frame_start)

# Example: ensure rigid body world exists
def ensure_rigid_world():
    if not scene.rigidbody_world:
        bpy.ops.rigidbody.world_add()
    # set substeps / solver iterations
    rw = scene.rigidbody_world
    params = job.get("rigid_world", {})
    rw.point_cache.frame_start = scene.frame_start
    rw.point_cache.frame_end = scene.frame_end
    rw.steps_per_second = int(params.get("steps_per_second", 60))
    rw.solver_iterations = int(params.get("solver_iterations", 10))

# Apply properties to target objects specified in job
def apply_targets(targets):
    for t in targets:
        name = t.get("object")
        obj = bpy.data.objects.get(name)
        if not obj:
            print("object not found:", name)
            continue
        typ = t.get("type","rigid")
        if typ == "rigid":
            if not obj.rigid_body:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.rigidbody.object_add()
            obj.rigid_body.mass = float(t.get("mass", obj.rigid_body.mass if obj.rigid_body else 1.0))
            obj.rigid_body.friction = float(t.get("friction", 0.5))
            obj.rigid_body.restitution = float(t.get("restitution", 0.0))
            # dynamic/static
            obj.rigid_body.type = 'ACTIVE' if t.get("active", True) else 'PASSIVE'
        if typ == "cloth":
            # add cloth modifier if not present
            if not any(m.type=="CLOTH" for m in obj.modifiers):
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_add(type='CLOTH')
            cloth = next((m for m in obj.modifiers if m.type=="CLOTH"), None)
            if cloth:
                cloth.settings.quality = int(t.get("quality", 5))
                cloth.settings.mass = float(t.get("mass", 0.3))
        if typ == "softbody":
            if not obj.modifiers or not any(m.type=="SOFT_BODY" for m in obj.modifiers):
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_add(type='SOFT_BODY')
            # set softbody params
            sb = next((m for m in obj.modifiers if m.type=="SOFT_BODY"), None)
            if sb:
                sb.settings.mass = float(t.get("mass", 1.0))
        # more types can be added...

# Bake function
def bake_simulation():
    # for rigid world
    if scene.rigidbody_world:
        print("Baking rigid body world...")
        bpy.ops.ptcache.bake_all(bake=True)
    # for cloth/softbody, baking occurs with cache as well
    # ensure all modifiers caches baked if needed
    # we will iterate frames to force evaluation
    for f in range(scene.frame_start, scene.frame_end+1):
        scene.frame_set(f)
    print("Bake complete.")

# Export caches / Alembic / FBX
def export_outputs(out_prefix, export_spec):
    Path(out_prefix).parent.mkdir(parents=True, exist_ok=True)
    # Alembic export
    if export_spec.get("type") == "abc":
        path = out_prefix + "_.abc"
        bpy.ops.wm.alembic_export(filepath=path, selected=False, apply_subdiv=False, flatten=False, start=scene.frame_start, end=scene.frame_end)
        print("Alembic exported:", path)
    if export_spec.get("type") == "fbx":
        path = out_prefix + ".fbx"
        bpy.ops.export_scene.fbx(filepath=path, use_selection=False, apply_unit_scale=True, bake_space_transform=True)
        print("FBX exported:", path)
    if export_spec.get("type") == "exr" or export_spec.get("type") == "png":
        # render sequence (assumes compositor set up)
        scene.render.image_settings.file_format = 'OPEN_EXR' if export_spec.get("type")=="exr" else 'PNG'
        scene.render.filepath = out_prefix + "frame_"
        bpy.ops.render.render(animation=True)
        print("Rendered frames to", out_prefix)

# Main flow
targets = job.get("targets", [])
ensure_rigid_world()
apply_targets(targets)
bake_simulation()
export_spec = job.get("export", {"type":"abc"})
export_outputs(out_prefix, export_spec)
print("Physics job complete:", job.get("task_id"))
