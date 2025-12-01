# blender_scripts/composite_passes_oidn.py
"""
Same as composite_passes.py but picks best denoiser:
- If GPU and OptiX available -> use Cycles/OptiX denoiser on render
- Else fallback to OpenImageDenoise node in compositor for EXR layers
Usage: blender --background --python composite_passes_oidn.py -- job.json out_dir
"""
import sys, json
from pathlib import Path
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv = []
if len(argv) < 2:
    print("job.json outdir required"); sys.exit(1)
job = json.loads(Path(argv[0]).read_text())
OUTDIR = Path(argv[1]); OUTDIR.mkdir(parents=True, exist_ok=True)

import bpy, os, subprocess

scene = bpy.context.scene
# choose denoiser
use_optix = False
try:
    prefs = bpy.context.preferences
    cycles_pref = prefs.addons['cycles'].preferences
    if hasattr(cycles_pref, "compute_device_type"):
        # Blender 3.x: check for OptiX devices
        for dev in cycles_pref.get_devices()[0]:
            if dev.type == 'OPTIX':
                use_optix = True
                break
except Exception:
    use_optix = False

# if using OptiX, enable OptiX denoiser for final render
if use_optix:
    try:
        scene.cycles.device = 'GPU'
        # enable OptiX denoiser in view layer
        for layer in scene.view_layers:
            layer.cycles.use_denoising = True
        print("Using OptiX denoiser (GPU) for rendering.")
    except Exception as e:
        print("OptiX setup failed:", e)
else:
    print("OptiX not detected — will use OpenImageDenoise in compositor if possible.")

# We'll reuse composite_passes logic but inject OIDN node when needed
nodes = scene.node_tree.nodes
links = scene.node_tree.links
scene.use_nodes = True
nodes.clear()

# create composite and viewer
comp = nodes.new(type="CompositorNodeComposite"); comp.location=(800,0)
# Create main input Image node for beauty sequence (we will set .image per frame)
img_node = nodes.new(type="CompositorNodeImage")
# If no beauty provided, try to compose diffuse+spec logic etc — (omitted for brevity)
links.new(img_node.outputs[0], comp.inputs[0])

# if no Optix, add OIDN denoise node (available as 'CompositorNodeDenoise')
if not use_optix:
    try:
        dn = nodes.new(type="CompositorNodeDenoise")
        dn.location = (400,0)
        # connect image->denoise->composite
        links.new(img_node.outputs[0], dn.inputs[0])
        links.new(dn.outputs[0], comp.inputs[0])
        print("Inserted OpenImageDenoise node.")
    except Exception as e:
        print("OIDN node not available:", e)

# Frame loop (similar to previous script). Minimal robust loader:
start = job.get("start_frame",1); end = job.get("end_frame",start)
inp = job.get("input_passes",{}).get("beauty") or job.get("input_passes",{}).get("beauty_exr") or ""
pattern = inp

for frame in range(start, end+1):
    if pattern:
        num_hash = pattern.count("#")
        if num_hash:
            fname = pattern.replace("#"*num_hash, str(frame).zfill(num_hash))
        else:
            try:
                fname = pattern % frame
            except:
                fname = pattern
        try:
            img = bpy.data.images.load(fname, check_existing=True)
            img_node.image = img
        except Exception as e:
            print("Warning: load failed", fname, e)
    # set render write path
    out_template = job.get("output", {}).get("path","static/compositor/out_%04d.png")
    out_frame = out_template.replace("####", str(frame).zfill(4)) if "####" in out_template else (out_template % frame if ("%d" in out_template) else out_template)
    scene.render.filepath = str(out_frame)
    scene.render.image_settings.file_format = 'OPEN_EXR' if out_frame.lower().endswith(".exr") else 'PNG'
    # For OptiX: render using cycles to apply OptiX denoiser
    if use_optix:
        # set cycles render engine and render
        scene.render.engine = 'CYCLES'
        bpy.ops.render.render(write_still=True)
    else:
        # composite node will process image and write still
        bpy.ops.render.render(write_still=True)
    print("Wrote frame:", out_frame)

print("OIDN/OptiX compositing done.")
