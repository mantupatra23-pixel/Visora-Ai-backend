# blender_scripts/horror_vfx.py
import bpy, sys, json, random, math
from pathlib import Path
from mathutils import Vector

def _args():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--")+1:]
    return []

def setup_fog(density=0.08, color=(0.05,0.05,0.06)):
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs['Density'].default_value = density
    vol.inputs['Color'].default_value = (*color,1.0)
    nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])

def strobe_light(frame, strength=5000, duration=2, loc=(0,0,2)):
    # add short flash at frame
    bpy.ops.object.light_add(type='POINT', location=loc)
    l = bpy.context.active_object
    l.data.energy = 0
    l.keyframe_insert(data_path="data.energy", frame=frame-1)
    l.data.energy = strength
    l.keyframe_insert(data_path="data.energy", frame=frame)
    l.data.energy = 0
    l.keyframe_insert(data_path="data.energy", frame=frame+duration)

def spawn_shadow_figure(start_frame, end_frame, loc=(5,0,0)):
    # spawn simple empty silhouette object and animate opacity of a plane
    bpy.ops.mesh.primitive_plane_add(size=2, location=loc)
    p = bpy.context.active_object
    p.name = f"Shadow_{start_frame}"
    # give dark material
    mat = bpy.data.materials.new(name=f"ShadowMat_{start_frame}")
    mat.diffuse_color = (0.02,0.02,0.02,1)
    p.data.materials.append(mat)
    # animate visibility
    p.hide_viewport = True
    p.keyframe_insert(data_path="hide_viewport", frame=start_frame-1)
    p.hide_viewport = False
    p.keyframe_insert(data_path="hide_viewport", frame=start_frame)
    p.hide_viewport = True
    p.keyframe_insert(data_path="hide_viewport", frame=end_frame)
    return p

def apply_romantic_like_soft_light():
    # not for horror — but keep function placeholder
    pass

def main(jobfile, outdir):
    job = json.loads(Path(jobfile).read_text())
    level = job.get("level","low")
    tags = job.get("tags",[])
    # configure
    if level in ("medium","high"):
        setup_fog(density=0.06 if level=="medium" else 0.12, color=(0.03,0.03,0.04))
    # add some random shadow spawns for 'silhouette' tags
    start = 1
    for timeline_item in job.get("timeline", []):
        shot = timeline_item
        if "shadow" in tags or "silhouette" in tags:
            spawn_shadow_figure(shot['start']+int(shot['frames']/3), shot['start']+int(shot['frames']/2), loc=(random.uniform(3,7), random.uniform(-2,2), 1.0))
        if shot['shot']=="jump_close":
            # schedule a strobe/flash at mid frame
            mid = shot['start'] + int(shot['frames']/2)
            strobe_light(mid, strength=7000, duration=2, loc=(0,0,2))
    # optionally render quick previews
    outp = Path(outdir); outp.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(outp/"frame_")
    try:
        bpy.ops.render.render(animation=True)
    except Exception as e:
        print("render error:", e)
    return {"ok":True}
