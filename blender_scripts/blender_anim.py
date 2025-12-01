# blender_scripts/blender_anim.py
"""
Blender animation runner.
Usage (CLI):
    blender --background --python blender_scripts/blender_anim.py -- <job.json> <output_path>

This script reads a job JSON (first CLI arg after --), then imports models,
applies keyframe transforms, creates camera cuts, optional audio, and renders.

NOTE: This is a general template. For rigged characters / advanced rigs
you may need to adapt keyframing or use actions/NLA.
"""

import bpy
import sys
import json
import os
import math
from mathutils import Vector, Euler

# Optional vfx helper functions (should exist)
from blender_scripts.vfx_helpers import (
    add_debris_emitter,
    add_smoke_fire,
    add_camera_shake,
    quick_add_flash
)

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

if len(argv) < 2:
    print("Usage: blender --background --python blender_scripts/blender_anim.py -- <job.json> <output_path>")
    sys.exit(1)

jobfile = argv[0]
outpath = argv[1]

with open(jobfile, "r") as f:
    job = json.load(f)

# Basic render settings
scene = bpy.context.scene
scene.render.engine = job.get("engine", "CYCLES")  # or 'BLENDER_EEVEE'
scene.render.resolution_x = job.get("resolution_x", 1280)
scene.render.resolution_y = job.get("resolution_y", 720)
scene.render.fps = job.get("fps", 24)
scene.frame_start = 1
scene.frame_end = job.get("duration", 10) * scene.render.fps

# Clean default objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False, confirm=False)

# Create camera
cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# Create a basic light
light_data = bpy.data.lights.new(name="KeyLight", type='SUN')
light = bpy.data.objects.new(name="KeyLight", object_data=light_data)
scene.collection.objects.link(light)
light.location = (10, -10, 15)
light.data.energy = job.get("light_energy", 2.0) * 1000 if job.get("light_energy") else 2000

# helper function to import model
def import_model(path, name_hint="model"):
    ext = os.path.splitext(path)[1].lower()
    if ext in [".glb", ".gltf"]:
        bpy.ops.import_scene.gltf(filepath=path)
        objs = [o for o in bpy.context.selected_objects]
        return objs
    elif ext in [".obj"]:
        bpy.ops.import_scene.obj(filepath=path)
        objs = [o for o in bpy.context.selected_objects]
        return objs
    else:
        print("Unsupported model ext:", ext)
        return []

# place characters
chars = job.get("characters", [])
for idx, ch in enumerate(chars):
    model_path = ch.get("model_path") or ch.get("path")
    if not model_path or not os.path.exists(model_path):
        continue

    objs = import_model(model_path)
    # create a collection for this character
    grp = bpy.data.collections.new(f"char_{idx}")
    scene.collection.children.link(grp)

    for o in objs:
        # move imported objects to collection
        scene.collection.objects.unlink(o)
        grp.objects.link(o)
        # set initial transform
        o.location = (ch.get("x", idx * 2.0), ch.get("y", 0.0), ch.get("z", 0.0))
        o.scale = (ch.get("scale", 1.0),) * 3 if isinstance(ch.get("scale", 1.0), (int, float)) else ch.get("scale", (1.0,1.0,1.0))
        # keyframe entry (simple translate)
        start_frame = int(ch.get("entry_start", 1) * scene.render.fps)
        enter_frames = int(ch.get("entry_duration", 1.0) * scene.render.fps)
        o.keyframe_insert(data_path="location", frame=start_frame)
        o.location = (o.location.x + ch.get("entry_dx", 0.0),
                      o.location.y + ch.get("entry_dy", 0.0),
                      o.location.z + ch.get("entry_dz", 0.0))
        o.keyframe_insert(data_path="location", frame=start_frame + max(1, enter_frames))

# Camera cuts: list of {frame_start, frame_end, type, params}
cuts = job.get("camera_cuts", [])
for cut in cuts:
    fs = int(cut.get("start", 1) * scene.render.fps)
    fe = int(cut.get("end", scene.frame_end / scene.render.fps) * scene.render.fps)
    typ = cut.get("type", "orbit")
    if typ == "orbit":
        # simple orbit: animate camera rotation around origin
        radius = cut.get("radius", 6.0)
        height = cut.get("height", 2.0)
        for f in range(fs, fe + 1):
            t = (f - fs) / max(1, (fe - fs))
            angle = t * 2 * math.pi * cut.get("turns", 1)
            cam.location.x = math.cos(angle) * radius
            cam.location.y = math.sin(angle) * radius
            cam.location.z = height
            cam.keyframe_insert(data_path="location", frame=f)
            cam.keyframe_insert(data_path="rotation_euler", frame=f)
    elif typ == "static":
        # place camera at a specified position and keyframe once
        pos = cut.get("position", [0, -6, 2])
        rot = cut.get("rotation_euler", [math.radians(90), 0, 0])
        cam.location = (pos[0], pos[1], pos[2])
        cam.rotation_euler = Euler((rot[0], rot[1], rot[2]))
        cam.keyframe_insert(data_path="location", frame=fs)
        cam.keyframe_insert(data_path="rotation_euler", frame=fs)
    # other cut types can be added here

# ---- BEATS / VFX handling (added section) ----
for beat in job.get("beats", []):
    # beat times are in seconds in job JSON
    start_frame = int(beat.get('start', 0) * scene.render.fps) + 1
    end_frame = int(beat.get('end', start_frame / scene.render.fps) * scene.render.fps) + 1

    # optional animation template (placeholder)
    anim_template = beat.get('anim_template')

    # apply VFX
    vfx_list = beat.get('vfx', [])
    loc = (0, 0, 0)
    # try to get actor location if provided in job (first char)
    if job.get('characters'):
        ch0 = job['characters'][0]
        loc = (ch0.get('x', 0), ch0.get('y', 0), ch0.get('z', 0))

    # Debris emitter
    if 'debris' in vfx_list:
        add_debris_emitter(location=loc, start_frame=start_frame, end_frame=end_frame, amount=80)

    # Smoke / Fire
    if 'smoke' in vfx_list or 'fire' in vfx_list:
        add_smoke_fire(location=loc, start_frame=start_frame, end_frame=end_frame + 20)

    # Camera shake if requested
    cam = scene.camera
    if beat.get('camera', {}).get('shake', False):
        duration_sec = beat.get('duration', 1.0)
        add_camera_shake(
            cam,
            start_frame=start_frame,
            end_frame=end_frame,
            strength=0.25 * duration_sec,
            scale=1.0
        )

    # quick flash for impacts/explosions
    if 'fire' in vfx_list or 'explosion' in beat.get('type', ''):
        quick_add_flash(scene, start_frame=start_frame, duration_frames=4, intensity=1.2)

# ---- Optional: attach audio if provided ----
audio = job.get("audio")
if audio and os.path.exists(audio):
    # add speaker and sound strip in sequence editor
    if not scene.sequence_editor:
        bpy.context.scene.sequence_editor_create()
    se = bpy.context.scene.sequence_editor
    bpy.context.scene.sequence_editor.sequences.new_sound("Sound", filepath=audio, channel=1, frame_start=1)

# Render animation to video
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.audio_codec = 'AAC'
scene.render.filepath = outpath

bpy.ops.render.render(animation=True)
print("Rendered:", outpath)
