# blender_scripts/crowd_builder.py
"""
Create instanced crowd from a simple low-poly proxy and scatter on a region.
Usage: blender --background --python crowd_builder.py -- proxy.blend count rows cols spacing outblend.blend
"""
import bpy, sys
from pathlib import Path
from mathutils import Vector

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def import_proxy(proxy_path):
    bpy.ops.wm.append(filepath=str(proxy_path) + "/Object/", directory=str(proxy_path))
    # fallback: user should have proxy object named "Proxy"
    return bpy.data.objects.get("Proxy") or (bpy.data.objects[0] if bpy.data.objects else None)

def scatter_instances(proxy_obj, rows, cols, spacing):
    base_collection = bpy.data.collections.new("Crowd")
    bpy.context.scene.collection.children.link(base_collection)
    for i in range(rows):
        for j in range(cols):
            inst = proxy_obj.copy()
            inst.data = proxy_obj.data
            inst.location = Vector((i*spacing, j*spacing, 0))
            inst.scale = (0.9 + ( (i+j)%3 )*0.05,)*3
            base_collection.objects.link(inst)
    return base_collection

def set_cycles_gpu(device_type='CUDA', tile_size_gpu=256, use_optix=False):
    try:
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.device = 'GPU'
        prefs = bpy.context.preferences
        cprefs = prefs.addons['cycles'].preferences
        cprefs.compute_device_type = 'OPTIX' if use_optix else device_type
        for d in cprefs.devices: d.use = True
        bpy.context.scene.render.tile_x = tile_size_gpu
        bpy.context.scene.render.tile_y = tile_size_gpu
        bpy.context.scene.cycles.samples = 64
        bpy.context.scene.cycles.use_adaptive_sampling = True
    except Exception as e:
        print("GPU config failed:", e)

def main(proxy_path, count, rows, cols, spacing, outblend):
    # assume proxy present in current file or linked; else user should import
    proxy = bpy.data.objects.get("Proxy")
    if not proxy:
        print("Proxy object missing; please add a low-poly proxy named 'Proxy'.")
        return
    coll = scatter_instances(proxy, int(rows), int(cols), float(spacing))
    # optional: add light probes (Irradiance volumes or reflection cubes)
    bpy.ops.object.lightprobe_add(type='GRID', location=(rows*spacing/2, cols*spacing/2, 2))
    bpy.ops.wm.save_mainfile(filepath=outblend)
    print("Crowd saved to", outblend)

if __name__=="__main__":
    argv = _args()
    if len(argv) < 6:
        print("usage: blender --background --python crowd_builder.py -- proxy.blend count rows cols spacing outblend.blend")
    else:
        proxy, count, rows, cols, spacing, outblend = argv
        main(proxy, int(count), int(rows), int(cols), float(spacing), outblend)
