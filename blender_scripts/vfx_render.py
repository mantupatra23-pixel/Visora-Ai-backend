# blender_scripts/vfx_render.py
"""
Blender VFX render template
- Reads job JSON describing vfx_passes, camera, output_dir, frames range, render settings
- Sets up view layers and render passes (beauty, emission, mist/depth, alpha)
- Renders EXR multilayer or PNG passes per frame
- At end optionally calls ffmpeg to assemble into an EXR sequence movie or PNG->MP4

USAGE:
blender --background scene.blend --python blender_scripts/vfx_render.py -- /abs/path/to/job.json
"""
import sys
import json
import os
from pathlib import Path

# parse args after '--'
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

if len(argv) < 1:
    print("Usage: blender --background file.blend --python blender_scripts/vfx_render.py -- /path/to/job.json")
    sys.exit(1)

job_file = Path(argv[0])
if not job_file.exists():
    print("Job file not found:", job_file)
    sys.exit(2)

with open(job_file, "r") as f:
    job = json.load(f)

# now import bpy
import bpy

def ensure_dir(p):
    Path(p).mkdir(parents=True, exist_ok=True)

out_dir = job.get("out_dir", str(Path.cwd() / "static" / "vfx" / "blender_" + job_file.stem))
ensure_dir(out_dir)
frames = job.get("frames")  # optional list [start, end] in frames
fps = job.get("fps", 24)
scene = bpy.context.scene
scene.render.fps = fps

# set frame range
if frames and isinstance(frames, list) and len(frames) >= 2:
    scene.frame_start = int(frames[0])
    scene.frame_end = int(frames[1])

# Render settings for EXR multilayer
def setup_render_exr():
    scene.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'
    scene.render.image_settings.color_depth = '16'  # 16 or 32
    scene.render.resolution_percentage = job.get("resolution_pct", 100)
    scene.render.engine = job.get("engine", "CYCLES")  # or 'BLENDER_EEVEE'
    if scene.render.engine == "CYCLES":
        scene.cycles.device = job.get("device", "GPU") if hasattr(scene, "cycles") else "CPU"
    # enable passes
    view_layer = bpy.context.view_layer
    view_layer.use_pass_combined = True
    view_layer.use_pass_emit = True
    view_layer.use_pass_z = True
    view_layer.use_pass_diffuse_color = True

# fallback to PNG beauty + extras
def setup_render_png():
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.resolution_percentage = job.get("resolution_pct", 100)
    scene.render.engine = job.get("engine", "BLENDER_EEVEE")

# choose render target
render_mode = job.get("render_mode", "exr")
if render_mode == "exr":
    setup_render_exr()
else:
    setup_render_png()

# optional: override output resolution
if job.get("width") and job.get("height"):
    scene.render.resolution_x = int(job.get("width"))
    scene.render.resolution_y = int(job.get("height"))

# optionally set camera transform if provided
cam = scene.camera
if job.get("camera"):
    cam_job = job.get("camera")
    if cam_job.get("location"):
        cam.location = tuple(cam_job["location"])
    if cam_job.get("rotation_euler"):
        cam.rotation_euler = tuple(cam_job["rotation_euler"])

# optionally hide/show collections based on job
for name, show in job.get("collections_visibility", {}).items():
    col = bpy.data.collections.get(name)
    if col:
        col.hide_render = not bool(show)

# enable denoising if requested and using cycles
if job.get("denoise", False) and scene.render.engine == "CYCLES":
    try:
        scene.cycles.use_denoising = True
    except Exception:
        pass

# render frames loop
start = scene.frame_start
end = scene.frame_end
print("Rendering frames", start, end, "to", out_dir, "mode", render_mode)

# output filename pattern
if render_mode == "exr":
    ext = "exr"
    filename_pattern = os.path.join(out_dir, "frame_%06d.exr")
else:
    ext = "png"
    filename_pattern = os.path.join(out_dir, "frame_%06d.png")

scene.render.filepath = filename_pattern

# Optionally set render samples for cycles
if scene.render.engine == "CYCLES":
    scene.cycles.samples = job.get("samples", 64)

# Render
bpy.ops.render.render(animation=True)

# After render, optionally call ffmpeg to assemble
assemble = job.get("assemble", True)
if assemble:
    out_movie = job.get("out_movie") or str(Path(out_dir) / "vfx_composite.mp4")
    # build ffmpeg command for sequence
    seq_pattern = os.path.join(out_dir, "frame_%06d."+ext)
    ff = f'ffmpeg -y -framerate {fps} -i "{seq_pattern}" -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p "{out_movie}"'
    print("Assemble command:", ff)
    os.system(ff)

print("Done render job. outputs in", out_dir)
