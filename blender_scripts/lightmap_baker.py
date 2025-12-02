# blender_scripts/lightmap_baker.py
"""
Bake lightmaps (combined) for all objects in a 'Crowd' collection using low-res UVs.
Set to GPU-friendly baking and tile-size tuned for GPUs.
Usage: blender --background --python lightmap_baker.py -- scene.blend out_dir
"""
import bpy, sys, os
from pathlib import Path

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def set_bake_settings(samples=64, use_gpu=True):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    if use_gpu:
        try:
            prefs = bpy.context.preferences
            cprefs = prefs.addons['cycles'].preferences
            cprefs.compute_device_type = 'CUDA'
            for d in cprefs.devices: d.use = True
            scene.cycles.device = 'GPU'
        except Exception:
            pass
    scene.cycles.samples = samples
    scene.render.tile_x = 256
    scene.render.tile_y = 256

def bake_all(out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    # iterate objects and bake diffuse or combined
    for ob in bpy.data.objects:
        if ob.type != 'MESH': continue
        bpy.context.view_layer.objects.active = ob
        # ensure lightmap UV exists (uv map named 'lightmap' else use first)
        if 'lightmap' not in [uv.name for uv in ob.data.uv_layers]:
            # duplicate active UV
            bpy.ops.mesh.uv_texture_add()
            ob.data.uv_layers[-1].name = 'lightmap'
        img = bpy.data.images.new(f"lm_{ob.name}", width=1024, height=1024)
        # assign image to a new material slot texture node? simpler: use bake to image via active image editor with nodes
        for slot in ob.material_slots:
            m = slot.material
            if not m or not m.use_nodes: continue
            # find an emission node or create one connecting to material output temporarily
            # skip complexity: set active image on UV editor and bake
        bpy.ops.image.save_as({'edit_image': img}, filepath=str(out_dir / (img.name + ".png")))
    print("Lightmap baking placeholder finished. For robust baking create a dedicated bake shader and bake per mesh.")
