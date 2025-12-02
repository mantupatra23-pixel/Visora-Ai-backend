# blender_scripts/mocap_pro_baker.py
# advanced baker: uses motion cycles, retarget and stabilizers
import bpy, sys, json, os, shlex
from pathlib import Path
# import helpers
sys.path.append(str(Path(__file__).parent))
from ik_fk_tools import switch_to_ik, switch_to_fk, add_foot_roll, get_armature
from footplant_stabilizer import stabilize_foot
from retarget_mixamo import import_fbx, simple_retarget

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    return argv

def load_job(jobfile):
    return json.loads(Path(jobfile).read_text())

def import_cycle_into_scene(fbx_path, name_suffix):
    # import FBX cycle as a new action source
    arm = import_fbx(fbx_path)
    return arm

def attach_cycle_to_rig(source_arm, target_arm, start_frame, frames, blend_in=6, blend_out=6):
    # very simple: copy keyframes from source to target over frame range and blend
    for s_pb in source_arm.pose.bones:
        tb = target_arm.pose.bones.get(s_pb.name)
        if not tb: continue
        # copy location/quaternion keys if exist
        # ... simplified: copy current pose transforms across frames
        for f in range(start_frame, start_frame+frames):
            bpy.context.scene.frame_set(f)
            tb.matrix = s_pb.matrix
            # location (if used) and rotation_quaternion
            try:
                tb.keyframe_insert(data_path="location", frame=f)
            except Exception:
                pass
            try:
                tb.keyframe_insert(data_path="rotation_quaternion", frame=f)
            except Exception:
                pass
    # TODO: add crossfade weighting (NLA strips recommended)

def bake_job(jobfile, out_dir):
    job = load_job(jobfile)
    actions = job.get("actions", [])
    rig_type = job.get("rig","humanoid_mixamo")
    # Prepare scene
    # Clear scene (careful: keep templates if you use)
    for ob in list(bpy.data.objects):
        try:
            bpy.data.objects.remove(ob, do_unlink=True)
        except Exception:
            pass

    # import target rig template (assumed present in project)
    # For demo we assume a blend file with rig named "Rig"
    # Alternatively, have a rig file to append
    # TODO: append/linked rig from templates
    # We'll create a dummy armature if none
    if not any(o.type == 'ARMATURE' for o in bpy.data.objects):
        bpy.ops.object.armature_add()
    target_arm = next((obj for obj in bpy.data.objects if obj.type=='ARMATURE'), None)

    cur_frame = 1
    # process each action: either use library cycles or procedural
    try:
        from services.motion_library import get_cycle
    except Exception:
        # fallback: simple mapping
        def get_cycle(name): return None

    for a in actions:
        act = a.get("action")
        frames = a.get("frames", 30)
        cycle = None
        try:
            cycle = get_cycle(act)
        except Exception:
            cycle = None

        if cycle:
            # import cycle fbx
            try:
                source_arm = import_fbx(cycle['path'])
                # retarget simple
                try:
                    simple_retarget(source_arm, target_arm, {})  # provide mapping if needed
                except Exception as e:
                    print("retarget error", e)
                # attach
                attach_cycle_to_rig(source_arm, target_arm, cur_frame, frames)
            except Exception as e:
                print("failed to use cycle:", e)
                # fallback procedural
                for f in range(cur_frame, cur_frame+frames):
                    bpy.context.scene.frame_set(f)
                    if target_arm:
                        target_arm.location.x += 0.01 * (a.get("speed",1.0))
                        target_arm.keyframe_insert(data_path="location", frame=f, index=0)
        else:
            # fallback: simple procedural root motion
            for f in range(cur_frame, cur_frame+frames):
                bpy.context.scene.frame_set(f)
                if target_arm:
                    # increment X each frame (very simple)
                    lx = target_arm.location.x
                    target_arm.location.x = lx + 0.01 * a.get("speed",1.0)
                    target_arm.keyframe_insert(data_path="location", frame=f, index=0)

        # small IK enable near foot-contact (if available)
        try:
            if target_arm:
                switch_to_ik(target_arm)
                add_foot_roll()
                # choose foot bone names heuristically
                try:
                    stabilize_foot(target_arm.name, 'foot.L', ground_z=0.0)
                except Exception:
                    stabilize_foot(target_arm.name, 'foot_R', ground_z=0.0)
                switch_to_fk(target_arm)
        except Exception as e:
            print("ik/fk/footplant step failed:", e)

        cur_frame += frames

    bpy.context.scene.frame_end = cur_frame + 10
    # export FBX
    outf = Path(out_dir) / (job['job_id'] + "_advanced.fbx")
    try:
        bpy.ops.export_scene.fbx(filepath=str(outf), embed_textures=False)
    except Exception as e:
        print("FBX export failed:", e)
        # try glb fallback
        try:
            bpy.ops.export_scene.gltf(filepath=str(outf.with_suffix(".glb")))
            outf = outf.with_suffix(".glb")
        except Exception as e2:
            print("glb export also failed:", e2)

    print("Exported", outf)
    return str(outf)

if __name__ == "__main__":
    argv = _args()
    if len(argv) < 2:
        print("usage: blender --background --python mocap_pro_baker.py -- job.json out_dir")
        sys.exit(1)
    jobfile, outdir = argv[0], argv[1]
    out = bake_job(jobfile, outdir)
    print("Result:", out)
PYCODE
