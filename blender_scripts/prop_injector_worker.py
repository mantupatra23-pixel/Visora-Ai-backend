# blender_scripts/prop_injector_worker.py
"""
Blender headless prop injector
Usage:
    blender --background scene.blend --python blender_scripts/prop_injector_worker.py -- job.json out_prefix

Job JSON format:
{
  "task_id": "...",
  "scene_blend": "scenes/scene.blend",
  "actions": [
    {"prop":"sword_long","target":"Boy","attach":"RightHand","position":[0,0,0],"rotation":[0,0,0],"scale":1.0, "physics": {...}},
    ...
  ],
  "out_prefix": "static/props_out/job_123_"
}

This script:
 - imports prop model into scene (glb/fbx/obj)
 - locates target character object (by name) and armature
 - computes transform for grip, parents prop to bone with constraint and applies local transform
 - optionally adds rigid body if physics true
 - exports updated scene as FBX and writes a small result JSON
"""

import sys
import json
import os
from pathlib import Path

# ensure services package accessible if running from repo root
ROOT = Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# CLI args handling for Blender (-- ...)
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

if len(argv) < 2:
    print("Usage: blender --background scene.blend --python blender_scripts/prop_injector_worker.py -- <job.json> <out_prefix>")
    sys.exit(1)

jobfile = Path(argv[0])
out_prefix = argv[1]
job = json.loads(jobfile.read_text())

# Import Blender
import bpy
from mathutils import Matrix, Vector, Euler

PROPS_DIR = ROOT / "assets" / "props"

# try to import helper from services (guarded)
try:
    from services.bone_alias import find_best_bone
except Exception:
    find_best_bone = None
    # if services not importable, warn but continue
    print("Warning: services.bone_alias.find_best_bone not available. Bone selection will use direct names.")

def import_model(filepath: str):
    fp = Path(filepath)
    ext = fp.suffix.lower()
    imported = []
    if ext in [".glb", ".gltf"]:
        bpy.ops.import_scene.gltf(filepath=str(fp))
        imported = [o for o in bpy.context.selected_objects]
    elif ext in [".fbx"]:
        bpy.ops.import_scene.fbx(filepath=str(fp))
        imported = [o for o in bpy.context.selected_objects]
    elif ext in [".obj"]:
        bpy.ops.import_scene.obj(filepath=str(fp))
        imported = [o for o in bpy.context.selected_objects]
    else:
        raise Exception("unsupported model type: " + ext)
    return imported

def find_object_by_name(name: str):
    for ob in bpy.data.objects:
        if ob.name == name or ob.name.startswith(name) or name in ob.name:
            return ob
    return None

def attach_to_bone(prop_obj, arm_obj, bone_name, local_offset=None, local_rot=None):
    """
    Create an empty parented to armature bone and parent prop to it, preserving transform.
    local_offset: [x,y,z] relative to bone in bone space
    local_rot: [x,y,z] euler degrees to apply
    """
    # ensure armature is active for parenting to bone
    bpy.context.view_layer.objects.active = arm_obj

    empty = bpy.data.objects.new(f"prop_attach_{prop_obj.name}", None)
    bpy.context.scene.collection.objects.link(empty)

    # parent empty to armature bone
    empty.parent = arm_obj
    empty.parent_type = 'BONE'
    empty.parent_bone = bone_name

    # set local transform if provided
    if local_offset:
        empty.location = Vector(local_offset)
    if local_rot:
        rads = [r * (3.141592653589793 / 180.0) for r in local_rot]
        empty.rotation_euler = Euler(rads)

    # parent prop to empty but keep world transform
    # remember current world matrix of prop
    world_matrix = prop_obj.matrix_world.copy()
    prop_obj.parent = empty
    prop_obj.matrix_parent_inverse = empty.matrix_world.inverted()
    # set local transform to match previous world transform
    prop_obj.matrix_world = world_matrix

    return empty

def set_rigidbody(obj, mass=1.0, collision_shape="CONVEX_HULL", passive=True):
    try:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.rigidbody.object_add()
        obj.rigid_body.mass = mass
        obj.rigid_body.collision_shape = collision_shape
        obj.rigid_body.type = 'PASSIVE' if passive else 'ACTIVE'
    except Exception as e:
        print("rigid body add failed:", e)

def find_armature_and_bones(name):
    """Return (armature_object, list_of_bone_names). Tries matching name or substring, then first armature fallback."""
    for ob in bpy.data.objects:
        if ob.type == 'ARMATURE' and (ob.name == name or ob.name.startswith(name) or name in ob.name):
            return ob, [b.name for b in ob.data.bones]
    # fallback: first armature
    arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    return (arm, [b.name for b in arm.data.bones]) if arm else (None, [])

# main processing
results = []

for a in job.get("actions", []):
    prop_name = a.get("prop")
    meta_path = PROPS_DIR / f"{prop_name}.json"
    model_path = None
    hand_grip = None

    # load metadata if exists
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            model_path = PROPS_DIR / meta.get("model_path", "")
            hand_grip = meta.get("hand_grip")
        except Exception as e:
            print("Failed reading meta for", prop_name, e)

    # if no metadata, try common model extensions with same name
    if not model_path or not model_path.exists():
        for ext in [".glb", ".gltf", ".fbx", ".obj"]:
            cand = PROPS_DIR / f"{prop_name}{ext}"
            if cand.exists():
                model_path = cand
                break

    if not model_path or not model_path.exists():
        results.append({"prop": prop_name, "ok": False, "error": "model not found"})
        continue

    # import model
    try:
        imported = import_model(str(model_path))
    except Exception as e:
        results.append({"prop": prop_name, "ok": False, "error": f"import failed: {e}"})
        continue

    prop_obj = imported[0] if imported else None
    if not prop_obj:
        results.append({"prop": prop_name, "ok": False, "error": "no imported objects"})
        continue

    # apply scale/rotation/position if provided in action
    scale = a.get("scale", 1.0)
    prop_obj.scale = (scale, scale, scale)

    if a.get("rotation"):
        # expect [x,y,z] degrees
        r = a.get("rotation")
        prop_obj.rotation_euler = Euler([r[0]*(3.141592653589793/180.0),
                                         r[1]*(3.141592653589793/180.0),
                                         r[2]*(3.141592653589793/180.0)])

    if a.get("position"):
        prop_obj.location = Vector(a.get("position"))

    # find target armature
    target_name = a.get("target")
    arm = None
    bone_to_attach = None
    if target_name:
        # improved find: this returns arm and bone list
        arm, bone_list = find_armature_and_bones(target_name)
        if arm:
            # preference: explicit attach name in action, then metadata hand_grip, then default RightHand
            if a.get("attach"):
                want = a.get("attach")
                if find_best_bone:
                    bone_to_attach = find_best_bone(bone_list, want)
                else:
                    # simple best match: exact or startswith
                    bone_to_attach = next((b for b in bone_list if b == want or b.startswith(want) or want in b), None)
            elif hand_grip:
                grip_bone_name = hand_grip.get("bone")
                if find_best_bone:
                    bone_to_attach = find_best_bone(bone_list, grip_bone_name)
                else:
                    bone_to_attach = next((b for b in bone_list if b == grip_bone_name or b.startswith(grip_bone_name) or (grip_bone_name and grip_bone_name in b)), None)
            else:
                # fallback to common RightHand names
                if find_best_bone:
                    bone_to_attach = find_best_bone(bone_list, "RightHand")
                else:
                    candidates = ["RightHand", "hand_r", "hand.R", "Hand.R"]
                    bone_to_attach = next((b for b in bone_list if b in candidates or "hand" in b.lower() and "right" in b.lower()), None)

            # final fallback if nothing found: use first bone
            if not bone_to_attach and bone_list:
                bone_to_attach = bone_list[0]
        else:
            print("target armature not found or no armatures in scene for target:", target_name)
    else:
        print("no target specified for action, skipping attach")

    # compute local offset/rotation (action may provide position/rotation relative to bone)
    offset = a.get("position") or None
    rot = a.get("rotation") or None

    if arm and bone_to_attach:
        try:
            attach_to_bone(prop_obj, arm, bone_to_attach, local_offset=offset, local_rot=rot)
        except Exception as e:
            print("attach_to_bone failed:", e)
            results.append({"prop": prop_name, "ok": False, "error": f"attach failed: {e}"})
            continue
    else:
        print("Not parenting to bone (no arm or bone found) for prop:", prop_name)

    # physics
    if a.get("physics", False):
        phys = a.get("physics") or {}
        mass = phys.get("mass", 1.0)
        shape = phys.get("shape", "CONVEX_HULL")
        # passive if specified else active
        passive = phys.get("passive", True)
        set_rigidbody(prop_obj, mass=mass, collision_shape=shape, passive=passive)

    results.append({"prop": prop_name, "ok": True, "attached_to": bone_to_attach if bone_to_attach else None})

# export result: FBX or save blend
out_pref = Path(out_prefix)
out_pref.parent.mkdir(parents=True, exist_ok=True)
out_fbx = str(out_pref) + "injected.fbx"
try:
    bpy.ops.export_scene.fbx(filepath=out_fbx, use_selection=False)
except Exception as e:
    print("FBX export failed:", e)

res_json = str(out_pref) + "result.json"
Path(res_json).write_text(json.dumps({"task_id": job.get("task_id"), "results": results}, indent=2))

print("Prop injection complete. exported:", out_fbx)
