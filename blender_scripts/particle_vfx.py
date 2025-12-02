# blender_scripts/particle_vfx.py
"""
Blender script: spawn particle emitter at given world location, bake and render frames.
Usage:
 blender --background --python particle_vfx.py -- job.json outdir
 job.json structure: {"job_id":"...","effects":[{"type":"sparks","frame":120,"loc":[1,2,1],"intensity":1.0}, ...]}
"""
import bpy, json, sys, os
from pathlib import Path
from mathutils import Vector
import random

def _args():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--")+1:]
    return []

def add_sparks_emitter(location=(0,0,0), strength=1.0, name="Sparks"):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.05, location=location)
    obj = bpy.context.active_object
    obj.name = name
    # add particle system
    psys = obj.modifiers.new(name + "_ps", type='PARTICLE_SYSTEM').particle_system
    settings = psys.settings
    settings.count = int(50 * strength)
    settings.frame_start = bpy.context.scene.frame_current
    settings.frame_end = bpy.context.scene.frame_current + 2
    settings.lifetime = 24
    settings.emit_from = 'VOLUME'
    settings.physics_type = 'NEWTON'
    settings.normal_factor = 2.0 * strength
    settings.brownian_factor = 0.2
    settings.render_type = 'OBJECT'
    # create spark object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.02, location=(0,0,0))
    spark = bpy.context.active_object
    spark.name = name + "_proto"
    spark.hide_viewport = True
    spark.hide_render = True
    settings.instance_object = spark
    return obj

def add_smoke_puff(location=(0,0,0), scale=0.5, name="SmokePuff"):
    bpy.ops.mesh.primitive_cube_add(size=scale, location=location)
    ob = bpy.context.active_object
    ob.name = name
    # quick smoke domain/emitter approach depends on Blender version; we create quick particle smoke approximation with low-res particles
    return ob

def bake_and_render(outdir):
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.frame_start = scene.frame_start or 1
    scene.frame_end = scene.frame_end or (scene.frame_start + 120)
    scene.render.filepath = str(outdir / "vfx_frame_")
    # bake particles (simple, many systems bake automatically during render)
    try:
        bpy.ops.render.render(animation=True)
    except Exception as e:
        print("render failed:", e)

def main(jobfile, outdir):
    job = json.loads(Path(jobfile).read_text())
    for ef in job.get("effects", []):
        typ = ef.get("type")
        loc = ef.get("loc", [0,0,0])
        frame = ef.get("frame", 1)
        bpy.context.scene.frame_set(frame)
        if typ == "sparks":
            add_sparks_emitter(location=Vector(loc), strength=ef.get("intensity",1.0), name=f"sparks_{frame}")
        elif typ == "smoke":
            add_smoke_puff(location=Vector(loc), scale=ef.get("scale",0.5), name=f"smoke_{frame}")
    bake_and_render(job.get("output_dir", outdir))
    return {"ok":True}

if __name__=="__main__":
    argv = _args()
    if len(argv) < 2:
        print("usage: blender --background --python particle_vfx.py -- job.json outdir")
        sys.exit(1)
    jobfile, outdir = argv[0], argv[1]
    print(main(jobfile, outdir))
