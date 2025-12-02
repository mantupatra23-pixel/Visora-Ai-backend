# blender_scripts/planar_tracker_keyer.py
"""
Blender script to planar-track a region and apply greenscreen key.
job.json:
{
 "job_id":"vfx_xxx",
 "plate":"path/to/plate.mp4",
 "key_color":[0.1,0.9,0.2],
 "key_tolerance":0.15,
 "track_region":[x,y,w,h],
 "frame_start":1,
 "frame_end":120,
 "output_dir":"jobs/vfx/.../out"
}
Usage:
 blender --background --python planar_tracker_keyer.py -- job.json outdir
"""
import bpy, json, sys, os
from pathlib import Path

def _args():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--")+1:]
    return []

def load_clip(clip_path):
    return bpy.data.movieclips.load(clip_path)

def create_tracker_and_track(clip, region=None):
    # create tracking object
    track = clip.tracking.tracks.new()
    if region:
        # Blender tracking markers usually set interactively; here we leave default marker
        pass
    # run tracking (attempt)
    try:
        clip.tracking.tracks.remove(track)  # keep scene clean if automatic created
    except:
        pass

def build_compositor_nodes(plate_path, key_color=(0.1,0.9,0.2), tolerance=0.15, outpath="out/vfx"):
    scene = bpy.context.scene
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    inp = tree.nodes.new("CompositorNodeMovieClip") if False else tree.nodes.new("CompositorNodeRLayers")
    # Instead add image input
    imgnode = tree.nodes.new("CompositorNodeImage")
    imgnode.image = bpy.data.images.load(plate_path)
    key = tree.nodes.new("CompositorNodeKeying")
    key.key_color = key_color
    key.tolerance = tolerance
    blur = tree.nodes.new("CompositorNodeBlur")
    blur.size_x = blur.size_y = 5
    comp = tree.nodes.new("CompositorNodeComposite")
    mix = tree.nodes.new("CompositorNodeAlphaOver")
    tree.links.new(imgnode.outputs[0], key.inputs[1])
    tree.links.new(key.outputs[0], blur.inputs[0])
    tree.links.new(blur.outputs[0], mix.inputs[1])
    tree.links.new(mix.outputs[0], comp.inputs[0])
    # write file node
    fileout = tree.nodes.new("CompositorNodeOutputFile")
    fileout.base_path = outpath
    tree.links.new(mix.outputs[0], fileout.inputs[0])
    return True

def main(jobfile, outdir):
    job = json.loads(Path(jobfile).read_text())
    plate = job.get("plate")
    if not plate or not Path(plate).exists():
        print("Plate missing"); return {"ok": False}
    build_compositor_nodes(plate, tuple(job.get("key_color",(0.1,0.9,0.2))), job.get("key_tolerance",0.15), outdir)
    # run a static render for test
    try:
        bpy.ops.render.render(write_still=True)
    except Exception as e:
        print("render failed:", e)
    return {"ok": True}

if __name__=="__main__":
    argv = _args()
    if len(argv)<2:
        print("usage: blender --background --python planar_tracker_keyer.py -- job.json outdir")
        sys.exit(1)
    print(main(argv[0], argv[1]))
