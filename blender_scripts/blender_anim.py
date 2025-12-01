# blender_scripts/blender_anim.py
"""
Blender animation runner.
Usage (CLI):
blender --background --python blender_scripts/blender_anim.py -- job.json /path/to/out.mp4

This script reads a job JSON (first CLI arg after --) and an output path (second),
then imports models, applies keyframe transforms, sets camera cuts, and renders video.
NOTE: This is a general template. For rigged character animation, customize bone names & actions.
"""
import bpy, sys, json, os, math
from mathutils import Vector, Euler

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

if len(argv) < 2:
    print("Usage: blender --background --python blender_anim.py -- <job.json> <out.mp4>")
    sys.exit(1)

jobfile = argv[0]
outpath = argv[1]

with open(jobfile, "r") as f:
    job = json.load(f)

# Basic render settings
scene = bpy.context.scene
scene.render.engine = 'CYCLES'  # or 'BLENDER_EEVEE' for speed
scene.render.resolution_x = job.get("resolution_x", 1920)
scene.render.resolution_y = job.get("resolution_y", 1080)
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
cam.location = (0, -6, 1.5)
cam.rotation_euler = Euler((math.radians(75), 0, 0), 'XYZ')

# Lighting
light_data = bpy.data.lights.new(name="key_light", type='AREA')
light = bpy.data.objects.new(name="key_light", object_data=light_data)
scene.collection.objects.link(light)
light.location = (3, -3, 5)
light.data.energy = 2000

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
    model_path = ch.get("model_path") or ch.get("mesh")
    if not model_path or not os.path.exists(model_path):
        continue
    objs = import_model(model_path)
    # group objects for this character
    grp = bpy.data.collections.new(f"char_{idx}")
    scene.collection.children.link(grp)
    for o in objs:
        # move imported objects to collection
        scene.collection.objects.unlink(o)
        grp.objects.link(o)
        # set initial transform
        o.location = (ch.get("x", idx*2.0), ch.get("y", 0.0), ch.get("z", 0.0))
        o.scale = (ch.get("scale", 1.0),)*3
        # keyframe entry (simple translate)
        start_frame = int(ch.get("entry_start", 1))
        enter_frames = int(ch.get("entry_duration", scene.render.fps))
        o.keyframe_insert(data_path="location", frame=start_frame)
        o.location = (o.location.x, o.location.y, o.location.z + ch.get("entry_lift", 0.5))
        o.keyframe_insert(data_path="location", frame=start_frame + enter_frames)

# Camera cuts: list of {frame_start, frame_end, type: orbit/pan/closeup, params}
cuts = job.get("camera_cuts", [])
for cut in cuts:
    fs = int(cut.get("start", 1) * scene.render.fps)
    fe = int(cut.get("end", scene.frame_end/scene.render.fps) * scene.render.fps)
    typ = cut.get("type","orbit")
    if typ == "orbit":
        # simple orbit: animate camera rotation around Z
        for f in range(fs, fe+1, int(scene.render.fps/4) if scene.render.fps>1 else 1):
            t = (f - fs) / max(1, (fe-fs))
            angle = t * 2 * math.pi * (cut.get("revs", 0.25))
            radius = cut.get("radius", 6.0)
            cam.location.x = math.cos(angle) * radius
            cam.location.y = math.sin(angle) * radius * -1
            cam.location.z = cut.get("height", 1.5)
            cam.keyframe_insert(data_path="location", frame=f)

# Optional: attach audio if provided
audio = job.get("audio")
if audio and os.path.exists(audio):
    # add speaker and sound strip in sequence editor
    bpy.context.scene.sequence_editor_create()
    bpy.context.scene.sequence_editor.sequences.new_sound("Voice", filepath=audio, channel=1, frame_start=1)

# Render animation to video
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.audio_codec = 'AAC'
scene.render.filepath = outpath

bpy.ops.render.render(animation=True)
print("Rendered:", outpath)
