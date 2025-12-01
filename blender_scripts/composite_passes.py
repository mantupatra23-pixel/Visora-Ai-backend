# blender_scripts/composite_passes.py
"""
Headless Blender compositor for multi-pass EXR compositing.

Usage:
blender --background --python blender_scripts/composite_passes.py -- /path/to/job.json /out/dir/

Job JSON fields:
- input_passes: { "beauty":"renders/beauty_####.exr", "diffuse":"...", ... }
- start_frame, end_frame
- denoise: {"method":"openimageio"|"blender","strength":0.5}
- grade: {"type":"lut","path":"grades/cube.cube"} or {"type":"preset","name":"filmic_warm"}
- output: {"type":"exr"|"png"|"mp4", "path": "static/compositor/out_%04d.png", "fps":25}
"""
import sys, json, os
from pathlib import Path

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--")+1:]
else:
    argv = []

if len(argv) < 2:
    print("Usage: blender --background --python composite_passes.py -- <job.json> <out_dir>")
    sys.exit(1)

jobfile = Path(argv[0])
outdir = Path(argv[1])
job = json.loads(jobfile.read_text())

import bpy

# ensure use nodes
scene = bpy.context.scene
scene.use_nodes = True
nodes = scene.node_tree.nodes
links = scene.node_tree.links
nodes.clear()

# create input file node per pass using ImageSequence (for EXR or PNG sequences)
start = job.get("start_frame",1)
end = job.get("end_frame",120)
input_nodes = {}
for pass_name, pattern in job.get("input_passes", {}).items():
    # pattern like renders/beauty_####.exr -> convert to frame seq
    # Replace #### with %0Nd pattern for ffmpeg style; Blender ImageSequence wants list of files
    pattern_str = str(pattern)
    # create Image node and set image sequence
    img_node = nodes.new(type="CompositorNodeImage")
    # simple approach: load single file per frame by formatting frame number on the fly later
    input_nodes[pass_name] = img_node

# create composite node and viewer
comp = nodes.new(type="CompositorNodeComposite")
comp.location = (800,0)

# create a Mix node stack: start from beauty if available otherwise merge diffuse+spec
if "beauty" in input_nodes:
    beauty = input_nodes["beauty"]
    # link beauty directly
    links.new(beauty.outputs[0], comp.inputs[0])
else:
    # naive merge: diffuse + specular * spec_strength
    mix = nodes.new(type="CompositorNodeMixRGB")
    mix.blend_type = 'ADD'
    diffuse = input_nodes.get("diffuse")
    spec = input_nodes.get("specular") or input_nodes.get("spec")
    if diffuse:
        links.new(diffuse.outputs[0], mix.inputs[1])
    if spec:
        links.new(spec.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], comp.inputs[0])

# add denoise step if requested: use Denoise node (Blender) or skip
denoise = job.get("denoise", {})
if denoise and denoise.get("method") == "blender":
    dn = nodes.new(type="CompositorNodeDenoise")
    # connect existing comp input into denoise then to composite
    # for simplicity we assume beauty->dn->comp
    if "beauty" in input_nodes:
        links.new(input_nodes["beauty"].outputs[0], dn.inputs[0])
        links.new(dn.outputs[0], comp.inputs[0])

# Note: loading image sequences into Blender compositor headlessly per-frame is tricky.
# Simpler approach: for each frame, use bpy.data.images.load with formatted filename and set node.image, then render to file.
out_spec = job.get("output", {})
out_type = out_spec.get("type","png")
out_path_template = out_spec.get("path","static/compositor/out_%04d.png")
outdir.mkdir(parents=True, exist_ok=True)

# grading: if LUT provided, apply via OpenColorIO node or use a Color Balance node for presets.
grade = job.get("grade", {})
use_lut = grade and grade.get("type")=="lut"

# Frame loop: for each frame, load files for each pass, composite, write result
for frame in range(start, end+1):
    bpy.context.scene.frame_set(frame)
    # load images
    for pname, pnode in input_nodes.items():
        pattern = job["input_passes"][pname]
        # replace #### with frame number padded
        if "####" in pattern:
            num_hash = pattern.count("#")
            fname = pattern.replace("#"*num_hash, str(frame).zfill(num_hash))
        else:
            # if pattern contains %d style
            try:
                fname = pattern % frame
            except Exception:
                fname = pattern
        # load image
        try:
            img = bpy.data.images.load(str(Path(fname).resolve()), check_existing=True)
            pnode.image = img
        except Exception as e:
            print("Warning loading", fname, e)
    # perform grade: simple color balance if preset
    if grade and grade.get("type")=="preset":
        name = grade.get("name","filmic")
        # basic filmic-ish tone mapping: use color balance node (not a real filmic)
        cb = nodes.get("ColorBalance") or nodes.new(type="CompositorNodeColorBalance")
        # link current main output to color balance then to composite
        # find current source socket (either mix or beauty)
        src_output = None
        if "beauty" in input_nodes:
            src_output = input_nodes["beauty"].outputs[0]
        elif 'mix' in locals():
            src_output = mix.outputs[0]
        if src_output:
            links.new(src_output, cb.inputs[1])
            links.new(cb.outputs[0], comp.inputs[0])
    # render a single frame to out path
    # set render settings for one-off write via compositor
    out_path = out_path_template % frame if ("%d" in out_path_template or "%04d" in out_path_template) else out_path_template.replace("####", str(frame).zfill(4))
    scene.render.filepath = str(out_path)
    # set image_settings
    if out_type.lower() == "exr":
        scene.render.image_settings.file_format = 'OPEN_EXR'
    else:
        scene.render.image_settings.file_format = 'PNG'
    # execute composite node tree and write
    bpy.ops.render.render(write_still=True)
    print("Wrote composited frame:", out_path)

# Optionally pack frames into video if requested
if out_spec.get("type") in ("mp4","mov"):
    # after frames export, call ffmpeg to assemble (this example uses external ffmpeg call)
    import subprocess
    pattern = out_path_template.replace("####","%04d")
    fps = out_spec.get("fps",25)
    outfile = out_spec.get("path")
    cmd = f'ffmpeg -y -r {fps} -i {pattern} -c:v libx264 -pix_fmt yuv420p {outfile}'
    subprocess.run(cmd, shell=True)
    print("Wrote video:", outfile)

print("Compositing job complete.")
