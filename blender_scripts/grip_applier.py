# blender_scripts/grip_applier.py
import bpy, json, sys
from pathlib import Path
from mathutils import Euler, Vector, Matrix

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def load_json(path):
    return json.loads(Path(path).read_text())

def apply_finger_pose(arm_obj, finger_pose: dict):
    # finger_pose: {"Thumb1.R":{"rot":[x,y,z],"loc":[x,y,z]}, ...}
    if not arm_obj or arm_obj.type!='ARMATURE': return
    bpy.context.view_layer.objects.active = arm_obj
    for bone_name, t in finger_pose.items():
        pb = arm_obj.pose.bones.get(bone_name)
        if not pb: continue
        rot = t.get("rot",[0,0,0])
        loc = t.get("loc",[0,0,0])
        # apply small rotation (Euler assumed)
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = Euler((rot[0], rot[1], rot[2]), 'XYZ')
        pb.location = Vector((loc[0], loc[1], loc[2]))
        pb.keyframe_insert(data_path="rotation_euler", frame=bpy.context.scene.frame_current)
        pb.keyframe_insert(data_path="location", frame=bpy.context.scene.frame_current)

def parent_prop_to_bone(prop_obj, arm_obj, bone_name, offset):
    prop_obj.parent = arm_obj
    prop_obj.parent_type = 'BONE'
    prop_obj.parent_bone = bone_name
    prop_obj.location = Vector(offset.get("loc",[0,0,0]))
    prop_obj.rotation_euler = Euler(offset.get("rot",[0,0,0]), 'XYZ')
    s = offset.get("scale",1.0)
    prop_obj.scale = (s,s,s)
    prop_obj.keyframe_insert(data_path="location", frame=bpy.context.scene.frame_current)
    prop_obj.keyframe_insert(data_path="rotation_euler", frame=bpy.context.scene.frame_current)
    prop_obj.keyframe_insert(data_path="scale", frame=bpy.context.scene.frame_current)

def main(jobfile, outdir):
    job = json.loads(Path(jobfile).read_text())
    grip_name = job.get("grip_name")
    grip = json.loads(Path(job.get("grip_path")).read_text()) if job.get("grip_path") else None
    prop_path = job.get("prop_path")
    # import prop
    bpy.ops.import_scene.fbx(filepath=prop_path) if prop_path.lower().endswith(".fbx") else bpy.ops.import_scene.gltf(filepath=prop_path)
    imported = bpy.context.selected_objects[:]
    prop_obj = imported[0] if imported else None
    # find armature
    arm = None
    for o in bpy.data.objects:
        if o.type=='ARMATURE':
            arm = o; break
    if not arm:
        bpy.ops.object.armature_add(); arm = bpy.context.active_object
    # apply grip offsets & finger pose
    offset = grip.get("offset",{"loc":[0,0,0],"rot":[0,0,0],"scale":1.0}) if grip else {"loc":[0,0,0],"rot":[0,0,0],"scale":1.0}
    bone = grip.get("attach_bone","hand.R") if grip else "hand.R"
    parent_prop_to_bone(prop_obj, arm, bone, offset)
    if grip and grip.get("finger_pose"):
        apply_finger_pose(arm, grip.get("finger_pose"))
    # export
    Path(outdir).mkdir(parents=True, exist_ok=True)
    outf = Path(outdir) / f"{job['job_id']}_grip.fbx"
    bpy.ops.export_scene.fbx(filepath=str(outf), embed_textures=False)
    print("exported", outf)
    return {"ok": True, "out": str(outf)}

if __name__=="__main__":
    argv = _args()
    if len(argv) < 2:
        print("usage: blender --background --python grip_applier.py -- job.json outdir")
        sys.exit(1)
    jobfile, outdir = argv[0], argv[1]
    print(main(jobfile, outdir))
