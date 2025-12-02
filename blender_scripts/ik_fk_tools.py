# blender_scripts/ik_fk_tools.py
# run inside Blender (bpy available)
import bpy, math

def get_armature(name=None):
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            if not name or obj.name==name:
                return obj
    return None

def switch_to_ik(arm, chain_root_bone='thigh.L', ik_bone='IK_FOOT.L'):
    # simple example: enable IK constraint weight = 1
    pb = arm.pose.bones.get(chain_root_bone)
    if not pb: return
    for c in pb.constraints:
        if c.type == 'IK':
            c.influence = 1.0

def switch_to_fk(arm, chain_root_bone='thigh.L'):
    pb = arm.pose.bones.get(chain_root_bone)
    if not pb: return
    for c in pb.constraints:
        if c.type == 'IK':
            c.influence = 0.0

def add_foot_roll(foot_ctrl_name='Foot_CTRL.L'):
    ctrl = bpy.data.objects.get(foot_ctrl_name)
    if not ctrl: return
    # create drivers or custom properties for foot roll (minimal)
    if "foot_roll" not in ctrl.keys():
        ctrl["foot_roll"] = 0.0
