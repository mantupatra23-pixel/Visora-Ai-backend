# blender_scripts/prop_attacher.py
import sys, json, os
from pathlib import Path
import bpy
import mathutils

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    return argv

def load_job(jobfile):
    return json.loads(Path(jobfile).read_text())

def import_prop(filepath):
    ext = Path(filepath).suffix.lower()
    if ext in [".fbx",".obj",".glb",".gltf"]:
        if ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=str(filepath))
        elif ext in [".glb",".gltf"]:
            bpy.ops.import_scene.gltf(filepath=str(filepath))
        else:
            bpy.ops.import_scene.obj(filepath=str(filepath))
    # find last imported object (approx)
    imported = [o for o in bpy.context.selected_objects]
    return imported

def find_character_armature(char_name_hint=None):
    # naive: return first armature or named one if present
    for ob in bpy.data.objects:
        if ob.type == 'ARMATURE':
            if char_name_hint and char_name_hint in ob.name:
                return ob
            return ob
    return None

def attach_prop_to_bone(prop_obj, arm_obj, bone_name, offset=(0,0,0), rot=(0,0,0), scale=1.0):
    # parent prop to bone with bone relative parenting
    prop_obj.parent = arm_obj
    prop_obj.parent_type = 'BONE'
    prop_obj.parent_bone = bone_name
    # apply local transform
    prop_obj.location = mathutils.Vector(offset)
    prop_obj.rotation_euler = mathutils.Euler([r for r in rot], 'XYZ')
    prop_obj.scale = (scale, scale, scale)
    prop_obj.keyframe_insert(data_path="location", frame=bpy.context.scene.frame_current)
    prop_obj.keyframe_insert(data_path="rotation_euler", frame=bpy.context.scene.frame_current)
    prop_obj.keyframe_insert(data_path="scale", frame=bpy.context.scene.frame_current)

def add_constraint_physics(prop_obj, mass=1.0):
    # minimal rigidbody attach for physical interaction
    try:
        bpy.context.view_layer.objects.active = prop_obj
        bpy.ops.rigidbody.object_add()
        prop_obj.rigid_body.mass = mass
        prop_obj.rigid_body.collision_shape = 'MESH'
    except Exception as e:
        print("rigidbody add failed", e)

def main(jobfile, outdir):
    job = load_job(jobfile)
    prop = job.get('prop', {})
    prop_path = prop.get('path')
    if not prop_path or not Path(prop_path).exists():
        print("prop asset missing:", prop_path)
        return {"ok": False, "error": "prop_missing"}
    # import prop
    imported = import_prop(prop_path)
    if not imported:
        print("import failed")
        return {"ok": False, "error": "import_failed"}
    # assume character rig present in scene
    arm = find_character_armature(job.get("character"))
    if not arm:
        print("no armature found, creating dummy armature")
        bpy.ops.object.armature_add()
        arm = bpy.context.active_object
    # pick primary prop object (first imported)
    prop_obj = imported[0]
    # attach bone name heuristics
    bone_name = job.get("attach", {}).get("primary_bone") or "hand.R"
    attach_prop_to_bone(prop_obj, arm, bone_name, offset=(0,0,0), rot=(0,0,0), scale=1.0)
    add_constraint_physics(prop_obj, mass=prop.get("mass",1.0))
    # optional: if two-hand grip -> create second prop duplicate and attach to other bone
    if prop.get("hand") == "both" or prop.get("grip_style") == "twohand":
        # create duplicate and attach to other bone for stability (simple approach)
        new = prop_obj.copy()
        new.data = prop_obj.data.copy()
        bpy.context.collection.objects.link(new)
        attach_prop_to_bone(new, arm, "hand.L", offset=(0,0,0), rot=(0,0,0), scale=1.0)
    # bake animation (if required) — for now export scene with prop bound
    Path(outdir).mkdir(parents=True, exist_ok=True)
    outpath = Path(outdir) / f"{job['job_id']}_prop.fbx"
    bpy.ops.export_scene.fbx(filepath=str(outpath), embed_textures=False)
    print("exported", outpath)
    return {"ok": True, "out": str(outpath)}

if __name__ == "__main__":
    argv = _args()
    if len(argv) < 2:
        print("usage: blender --background --python prop_attacher.py -- job.json out_dir")
        sys.exit(1)
    jobfile, outdir = argv[0], argv[1]
    res = main(jobfile, outdir)
    print(res)
