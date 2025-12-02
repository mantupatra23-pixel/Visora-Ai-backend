# blender_scripts/weather_flip_fluid.py
import bpy, sys, json, os
from pathlib import Path

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def load_job(path): return json.loads(Path(path).read_text())

def create_flip_domain(location=(0,0,0), size=20, resolution=64, cache_dir="/tmp/flip_cache"):
    # Add domain cube
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    dom = bpy.context.active_object
    dom.name = "FLIP_Domain"
    # enable fluid modifier (Mantaflow)
    mod = dom.modifiers.new("FLIP", type='FLUID')
    mod.fluid_type = 'DOMAIN'
    dom.domain_settings.domain_type = 'LIQUID'
    dom.domain_settings.resolution_max = resolution
    dom.domain_settings.cache_type = 'MODULAR'
    dom.domain_settings.cache_directory = cache_dir
    return dom

def create_flip_inflow(location=(0,0,8), radius=0.5, speed=5.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location)
    inflow = bpy.context.active_object
    inflow.name = "FLIP_Inflow"
    mod = inflow.modifiers.new("Inflow", type='FLUID')
    mod.fluid_type = 'FLOW'
    inflow.flow_settings.flow_type = 'LIQUID'
    inflow.flow_settings.flow_behavior = 'INFLOW'
    inflow.flow_settings.velocity = (0,0,-speed)
    return inflow

def run_sim(job, outdir):
    cfg = job.get("config",{})
    res = cfg.get("flip_resolution", 64)
    dom = create_flip_domain(size=cfg.get("domain_size",20), resolution=res, cache_dir=str(Path(outdir)/"flip_cache"))
    inflow = create_flip_inflow(location=(0,0,8), radius=cfg.get("inflow_radius",0.6), speed=cfg.get("inflow_speed",6.0))
    # bake
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = job.get("frames",240)
    try:
        bpy.ops.fluid.bake_all()
    except Exception as e:
        print("Bake failed", e)
    # After bake, optionally convert particles to mesh or export particle cache
    # Export domain mesh at final frame
    bpy.context.scene.frame_set(bpy.context.scene.frame_end)
    outmesh = Path(outdir) / f"{job['job_id']}_flip_final.obj"
    bpy.ops.export_scene.obj(filepath=str(outmesh), use_selection=False)
    print("Exported flip mesh:", outmesh)
    return True

if __name__=="__main__":
    argv = _args()
    if len(argv)<2:
        print("Usage: blender --background --python weather_flip_fluid.py -- job.json outdir")
        sys.exit(1)
    jobfile, outdir = argv[0], argv[1]
    job = load_job(jobfile)
    run_sim(job, outdir)
    print("flip done")
