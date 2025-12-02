# blender_scripts/auto_grip_fit.py
import bpy, json, sys
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion, Euler

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def load_handle_json(path):
    return json.loads(Path(path).read_text())

def apply_grip_using_handle(prop_obj, arm_obj, bone_name, handle_centroid, principal_axis):
    # Move origin of prop to handle centroid
    # Note: This is approximate — better to edit mesh origin in modeling step.
    prop_obj.location = Vector(handle_centroid)
    # Orient prop so principal axis roughly aligns with bone forward (X) — simple heuristic
    # bone forward vector approximate:
    bone_forward = Vector((1,0,0))
    axis = Vector(principal_axis)
    rot = axis.rotation_difference(bone_forward).to_euler()
    prop_obj.rotation_euler = rot
    prop_obj.keyframe_insert(data_path="location", frame=bpy.context.scene.frame_current)
    prop_obj.keyframe_insert(data_path="rotation_euler", frame=bpy.context.scene.frame_current)

def main(jobfile, handle_json, outdir):
    job = json.loads(Path(jobfile).read_text())
    prop_path = job.get("prop_path")
    bpy.ops.import_scene.fbx(filepath=prop_path) if prop_path.lower().endswith(".fbx") else bpy.ops.import_scene.gltf(filepath=prop_path)
    imported = bpy.context.selected_objects[:]
    prop_obj = imported[0] if imported else None
    # load handle
    handle = load_handle_json(handle_json)
    centroid = handle.get("centroid")
    axis = handle.get("principal_axis")
    # find armature
    arm = None
    for o in bpy.data.objects:
        if o.type=='ARMATURE':
            arm = o; break
    if not arm:
        bpy.ops.object.armature_add(); arm = bpy.context.active_object
    bone = job.get("attach_primary","hand.R")
    apply_grip_using_handle(prop_obj, arm, bone, centroid, axis)
    # parent
    prop_obj.parent = arm; prop_obj.parent_type='BONE'; prop_obj.parent_bone = bone
    Path(outdir).mkdir(parents=True, exist_ok=True)
    outf = Path(outdir) / f"{job['job_id']}_autofit.fbx"
    bpy.ops.export_scene.fbx(filepath=str(outf))
    print("exported", outf)
    return {"ok": True, "out": str(outf)}

if __name__=="__main__":
    argv = _args()
    if len(argv) < 3:
        print("usage: blender --background --python auto_grip_fit.py -- job.json handle.json outdir")
        sys.exit(1)
    jobfile, handle_json, outdir = argv[0], argv[1], argv[2]
    print(main(jobfile, handle_json, outdir))
