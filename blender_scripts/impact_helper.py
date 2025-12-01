# blender_scripts/impact_helper.py
"""
Usage:
blender --background scene.blend --python blender_scripts/impact_helper.py -- /path/to/job.json

job.json:
{
  "impact_point": [0.0, 0.0, 1.0],
  "impact_frame": 30,
  "impulse_strength": 300.0,
  "radius": 3.0,
  "spawn_smoke": true,
  "smoke_strength": 1.0,
  "spawn_particles": true,
  "particle_count": 200
}
"""
import sys, json
from pathlib import Path
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []
if not argv:
    print("Provide job.json")
    sys.exit(1)
job = json.loads(Path(argv[0]).read_text())

import bpy, mathutils
pt = mathutils.Vector(job.get("impact_point", [0,0,1]))
frame = int(job.get("impact_frame", 30))
strength = float(job.get("impulse_strength", 200.0))
radius = float(job.get("radius", 2.5))

# create empty at impact location
empty = bpy.data.objects.new("Impact_Empty", None)
bpy.context.scene.collection.objects.link(empty)
empty.location = pt

# at impact frame, apply impulse to rigid bodies within radius
scene = bpy.context.scene
scene.frame_set(frame)
for ob in bpy.context.scene.objects:
    if ob.rigid_body:
        dist = (ob.location - pt).length
        if dist <= radius:
            # compute direction
            dir = (ob.location - pt).normalized()
            force = dir * (strength * (1.0 - (dist/radius)))
            # apply impulsive velocity change via keyframed velocity? Blender doesn't allow direct velocity keyframes easily.
            # Instead we can apply force as an impulse by temporarily switching to dynamics? We'll use rigid_body_apply_impulse method if available.
            try:
                ob.rigid_body.kinematic = False
            except Exception:
                pass
            # Use bpy.ops.rigidbody.apply_force if available (it isn't). Fallback: set initial linear velocity via object.rigid_body.linear_velocity
            try:
                ob.rigid_body.linear_velocity = (force.x, force.y, force.z)
            except Exception:
                try:
                    ob.linear_velocity = (force.x, force.y, force.z)
                except Exception:
                    print("Could not set velocity for", ob.name)
# spawn smoke domain and flow if requested
if job.get("spawn_smoke", False):
    # quick smoke add near point
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=pt)
    flow = bpy.context.active_object
    bpy.context.view_layer.objects.active = flow
    try:
        bpy.ops.object.modifier_add(type='SMOKE')
        flow.modifiers["Smoke"].smoke_type = 'FLOW'
        flow.modifiers["Smoke"].flow_settings.flow_type = 'BOTH'
        flow.modifiers["Smoke"].flow_settings.surface_distance = 0.5
    except Exception as e:
        print("Unable to add smoke flow:", e)
# spawn particle emitter
if job.get("spawn_particles", False):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.05, location=pt)
    psrc = bpy.context.active_object
    psrc.name = "Impact_Particle_Source"
    bpy.ops.object.particle_system_add()
    psys = psrc.particle_systems[-1]
    settings = psys.settings
    settings.count = int(job.get("particle_count",200))
    settings.frame_start = frame
    settings.frame_end = frame + 2
    settings.lifetime = 50
    settings.emit_from = 'VOLUME'
    settings.physics_type = 'NEWTON'
    settings.normal_factor = 4.0
    settings.factor_random = 1.2

print("Impact helper done for frame", frame)
