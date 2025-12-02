# blender_scripts/footplant_stabilizer.py
import bpy, math
from mathutils import Vector

def stabilize_foot(arm_name='Armature', foot_bone='foot.L', ground_z=0.0, threshold=0.02):
    arm = bpy.data.objects.get(arm_name)
    if not arm: return
    pb = arm.pose.bones.get(foot_bone)
    if not pb: return
    scene = bpy.context.scene
    sf = scene.frame_start
    ef = scene.frame_end
    for f in range(sf, ef+1):
        scene.frame_set(f)
        world_pos = arm.matrix_world @ pb.head
        dz = world_pos.z - ground_z
        if abs(dz) < threshold:
            # small correction - set bone location slightly to avoid sink
            pb.location.z += (threshold - dz) * 0.5
            pb.keyframe_insert(data_path="location", frame=f, index=2)
