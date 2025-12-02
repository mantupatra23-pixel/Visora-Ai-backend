# blender_scripts/throw_planner.py
import bpy, json, sys
from pathlib import Path
from mathutils import Vector

def _args():
    argv = sys.argv
    if "--" in argv: argv = argv[argv.index("--")+1:]
    else: argv=[]
    return argv

def apply_trajectory(prop_obj, traj, start_frame=1, fps=24):
    for i, s in enumerate(traj):
        frame = start_frame + int(s['t']*fps)
        bpy.context.scene.frame_set(frame)
        prop_obj.location = Vector(s['pos'])
        prop_obj.keyframe_insert(data_path="location", frame=frame)

def main(jobfile, planfile, outdir):
    job = json.loads(Path(jobfile).read_text())
    plan = json.loads(Path(planfile).read_text())
    # import prop (assume single)
    bpy.ops.import_scene.fbx(filepath=job['prop_path'])
    obj = bpy.context.selected_objects[0]
    apply_trajectory(obj, plan['trajectory'], start_frame=job.get('start_frame',1), fps=24)
    Path(outdir).mkdir(parents=True, exist_ok=True)
    outf = Path(outdir) / f"{job['job_id']}_throw.fbx"
    bpy.ops.export_scene.fbx(filepath=str(outf))
    print("exported", outf)
    return {"ok": True, "out": str(outf)}

if __name__=="__main__":
    argv=_args()
    if len(argv)<3:
        print("usage: blender --background --python throw_planner.py -- job.json plan.json outdir")
        sys.exit(1)
    print(main(argv[0], argv[1], argv[2]))
