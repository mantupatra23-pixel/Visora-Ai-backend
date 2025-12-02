# blender_scripts/retarget_mixamo.py
import bpy, json
from pathlib import Path

def import_fbx(path):
    bpy.ops.import_scene.fbx(filepath=str(path), axis_forward='-Z', axis_up='Y')
    # assume imported armature is active
    for obj in bpy.context.selected_objects:
        if obj.type=='ARMATURE':
            return obj
    return None

def simple_retarget(source_arm, target_arm, bone_map: dict):
    # bone_map: {"source_bone":"target_bone", ...}
    for s_b, t_b in bone_map.items():
        sb = source_arm.pose.bones.get(s_b)
        tb = target_arm.pose.bones.get(t_b)
        if sb and tb:
            tb.matrix = sb.matrix
            tb.keyframe_insert(data_path="location")
            tb.keyframe_insert(data_path="rotation_quaternion")
            tb.keyframe_insert(data_path="scale")
