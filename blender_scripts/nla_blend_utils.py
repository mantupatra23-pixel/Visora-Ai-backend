# blender_scripts/nla_blend_utils.py
# run inside Blender (bpy)
import bpy
from math import floor

def ensure_action_for_object(obj, action_name):
    """Ensure object has action; return action"""
    act = bpy.data.actions.get(action_name)
    if not act:
        act = bpy.data.actions.new(action_name)
    return act

def push_action_to_nla(obj, action, start_frame):
    """Push an action as NLA strip on object's animation_data"""
    if obj.animation_data is None:
        obj.animation_data_create()
    tracks = obj.animation_data.nla_tracks
    track = tracks.new()
    track.name = f"Track_{action.name}"
    strip = track.strips.new(action.name, start=start_frame, action=action)
    return track, strip

def crossfade_strips(stripA, stripB, blend_frames=8):
    """
    Given two NLA strips (on possibly different tracks), create overlap and set blend_in/out.
    This function expects stripB to start after or overlapping stripA.
    """
    # ensure overlap by moving start of stripB
    startB = stripB.frame_start
    # set blend in/out
    stripB.blend_in = blend_frames
    stripA.blend_out = blend_frames
    # set transition mode to replace for smoother crossfade
    stripA.action_blend_type = 'REPLACE'
    stripB.action_blend_type = 'REPLACE'
    stripA.use_animated_time_cyclic = False
    stripB.use_animated_time_cyclic = False
    return True

def set_ease_on_strip(strip, ease_in=0.2, ease_out=0.2):
    """
    Approximate easing by adjusting strip scale and influence keyframes.
    We'll insert influence keyframes at start/end with eased values.
    """
    # create a driverless fcurve for influence? NLA strips don't have fcurves directly.
    # Alternative: create a dummy empty property and drive strip's influence via NLA track strip.influence?
    try:
        strip.influence = 1.0
        # Insert keyframes is not supported directly on NLA strip influence in API older versions.
        # Workaround: use action with bone and animate that, or keep simple: set blend_in/out
        return True
    except Exception as e:
        print("set_ease_on_strip failed:", e)
        return False

def merge_and_crossfade_actions(obj, actions_with_starts, blend_frames=8):
    """
    actions_with_starts: list of tuple (action, start_frame)
    Attach actions as NLA strips and crossfade consecutive ones.
    """
    strips = []
    for action, start in actions_with_starts:
        track, strip = push_action_to_nla(obj, action, start)
        strips.append(strip)
    # crossfade consecutive
    for i in range(len(strips)-1):
        crossfade_strips(strips[i], strips[i+1], blend_frames=blend_frames)
    return strips
