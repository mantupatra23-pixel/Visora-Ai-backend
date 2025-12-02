# blender_scripts/fight_baker.py
"""
Run inside Blender. Reads job.json choreography -> apply actions to rigs,
bake simple offsets, trigger impact VFX + optional ragdoll via Blender Rigid Body / constraints.
This is a prototype: expects two character armatures named "ActorA" and "ActorB" in the scene.
"""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector

def _args():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--")+1:]
    return []

def load_job(path):
    return json.loads(Path(path).read_text())

def find_actor(name):
    # look for armature object named name
    return bpy.data.objects.get(name)

def apply_move_to_actor(actor_obj, move_name, start_frame, frames, delta):
    # delta is local translation to apply gradually; simple keyframe translation of root
    if actor_obj is None:
        return
    root = actor_obj
    start_loc = root.location.copy()
    end_loc = start_loc + Vector(delta)
    # set keyframes
    root.keyframe_insert(data_path="location", frame=start_frame)
    root.location = end_loc
    root.keyframe_insert(data_path="location", frame=start_frame+frames-1)

def spawn_impact_vfx(location, intensity=1.0):
    # create simple particle emitter (small)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=location)
    p = bpy.context.active_object
    p.name = "ImpactVFX"
    # quick emission: add particle system
    ps = p.modifiers.new("ImpactPS", type='PARTICLE_SYSTEM').particle_system
    ps.settings.count = int(30*intensity)
    ps.settings.frame_start = bpy.context.scene.frame_current
    ps.settings.frame_end = bpy.context.scene.frame_current + 2
    return p

def apply_ragdoll(actor_obj, frame):
    # simplified: enable rigid body on mesh children and bake physics (very basic)
    for ob in actor_obj.children_recursive:
        if ob.type == 'MESH':
            if not ob.rigid_body:
                bpy.ops.rigidbody.object_add({'object': ob})
            ob.rigid_body.kinematic = False
            ob.keyframe_insert(data_path="rigid_body.kinematic", frame=frame)

def main(jobfile, outdir):
    job = load_job(jobfile)
    timeline = job.get("timeline", [])
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    # find actors
    actorA = find_actor("ActorA")
    actorB = find_actor("ActorB")
    actors = {"A": actorA, "B": actorB}
    # ensure frame range
    fps = job.get("fps",24)
    total_frames = job.get("length_sec",6) * fps
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = total_frames
    impacts = []
    # apply moves
    for item in timeline:
        a = actors.get(item['actor'])
        apply_move_to_actor(a, item['move'], item['start_frame'], item['frames'], item.get('delta',[0,0,0]))
        # schedule impact VFX if force > 0
        if item.get('force',0) > 0:
            impact_frame = item['start_frame'] + int(item['frames']/2)
            bpy.context.scene.frame_set(impact_frame)
            # compute hit location: simple projection from actor to defender
            hitter = a
            defender = actors.get("B" if item['actor']=="A" else "A")
            loc = defender.location if defender else Vector((0,0,1))
            spawn_impact_vfx(loc, intensity=item.get('force',1)/30.0)
            # optionally ragdoll
            if item.get('force',0) >= 40:
                apply_ragdoll(defender, impact_frame)
            impacts.append({"frame":impact_frame,"loc":tuple(loc),"force":item.get('force')})
    # export baked scene or FBX
    fbx_out = outdir / (job['job_id'] + "_scene.fbx")
    bpy.ops.export_scene.fbx(filepath=str(fbx_out), use_selection=False, bake_space_transform=True)
    # render preview (optional): render whole timeline quickly (low samples)
    bpy.context.scene.render.filepath = str(outdir / "frame_")
    try:
        bpy.ops.render.render(animation=True)
    except Exception as e:
        print("render animation failed:", e)
    # save metadata
    Path(outdir / "impacts.json").write_text(json.dumps(impacts, indent=2))
    Path(outdir / "result.json").write_text(json.dumps({"ok":True,"fbx":str(fbx_out)}, indent=2))
    return {"ok":True, "out": str(fbx_out)}

if __name__=="__main__":
    argv = _args()
    if len(argv) < 2:
        print("usage: blender --background --python fight_baker.py -- job.json outdir")
        sys.exit(1)
    jobfile, outdir = argv[0], argv[1]
    print(main(jobfile, outdir))
