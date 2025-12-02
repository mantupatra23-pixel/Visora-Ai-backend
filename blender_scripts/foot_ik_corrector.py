# blender_scripts/foot_ik_corrector.py
"""
Run inside Blender.
Usage:
 blender --background --python foot_ik_corrector.py -- armature_name left_foot_bone right_foot_bone start_frame end_frame
This will add IK constraints to foot bones and bake corrected keyframes with simple contact detection.
"""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def add_ik_constraint(armature_obj, chain_root_bone, target_empty_name):
    # create empty target
    empty = bpy.data.objects.new(target_empty_name, None)
    bpy.context.collection.objects.link(empty)
    # add IK constraint to chain root bone
    pb = armature_obj.pose.bones.get(chain_root_bone)
    if not pb:
        print("bone missing:", chain_root_bone); return None
    ik = pb.constraints.new('IK')
    ik.target = empty
    ik.chain_count = 2
    return empty, ik

def detect_contacts(arm_obj, foot_bone_name, start, end, velocity_thresh=0.02):
    contacts = []
    prev_loc = None
    for f in range(start, end+1):
        bpy.context.scene.frame_set(f)
        mat = arm_obj.matrix_world @ arm_obj.pose.bones[foot_bone_name].head
        loc = Vector((mat.x, mat.y, mat.z))
        if prev_loc:
            vel = (loc - prev_loc).length
            if vel < velocity_thresh:
                contacts.append(f)
        prev_loc = loc
    return contacts

def bake_foot_lock(arm_name, foot_bone, start, end):
    arm = bpy.data.objects.get(arm_name)
    if arm is None:
        print("armature not found", arm_name); return
    # add ik target
    tgt_name = f"{arm_name}_{foot_bone}_ik_tgt"
    empty, ik = add_ik_constraint(arm, foot_bone, tgt_name)
    contacts = detect_contacts(arm, foot_bone, start, end)
    print("contacts detected:", contacts[:10])
    # for each contiguous contact frame range, lock empty and keyframe it
    if not contacts:
        print("no contacts -> nothing to lock")
    else:
        # group contiguous frames
        ranges = []
        s = contacts[0]; p = s
        for c in contacts[1:]:
            if c == p + 1:
                p = c
            else:
                ranges.append((s,p))
                s = c; p = c
        ranges.append((s,p))
        for (rs,re) in ranges:
            bpy.context.scene.frame_set(rs)
            # set empty location to foot world pos
            foot_world = arm.matrix_world @ arm.pose.bones[foot_bone].head
            empty.location = foot_world
            empty.keyframe_insert(data_path="location", frame=rs)
            empty.keyframe_insert(data_path="location", frame=re)
    # bake action to keyframes then remove ik target (cleanup)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    try:
        bpy.ops.nla.bake(frame_start=start, frame_end=end, only_selected=False, visual_keying=True, clear_constraints=False, use_current_action=True, bake_types={'POSE'})
    except Exception as e:
        print("bake failed:", e)
    # cleanup: remove empty/constraint
    try:
        arm.pose.bones[foot_bone].constraints.remove(ik)
        bpy.data.objects.remove(empty, do_unlink=True)
    except Exception as e:
        print("cleanup failed:", e)
    print("Foot IK correction completed for", foot_bone)

if __name__ == "__main__":
    argv = _args()
    if len(argv) < 5:
        print("usage: blender --background --python foot_ik_corrector.py -- armature_name left_foot_bone right_foot_bone start end")
        sys.exit(1)
    arm_name = argv[0]; left_bone = argv[1]; right_bone = argv[2]; start = int(argv[3]); end = int(argv[4])
    bake_foot_lock(arm_name, left_bone, start, end)
    bake_foot_lock(arm_name, right_bone, start, end)
