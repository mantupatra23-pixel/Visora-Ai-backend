# blender_scripts/optimize_render.py
import bpy, os
from math import ceil
def configure_cycles_gpu(device_type='CUDA', tile_size_gpu=256, tile_size_cpu=32, use_gpu=True):
    """
    Call early in baker script to set Cycles device, tiles and denoise.
    device_type: 'CUDA' | 'OPTIX' | 'OPENCL'
    """
    prefs = bpy.context.preferences
    try:
        cprefs = prefs.addons['cycles'].preferences
    except Exception:
        # if cycles addon missing, nothing to do
        cprefs = None
    # set device type if available
    try:
        bpy.context.scene.render.engine = 'CYCLES'
        if use_gpu and cprefs:
            # set compute device type if supported
            cprefs.compute_device_type = device_type
            # enable all devices
            for d in cprefs.devices:
                d.use = True
        # device-specific tile recommendations
        if use_gpu:
            bpy.context.scene.cycles.device = 'GPU'
            bpy.context.scene.render.tile_x = tile_size_gpu
            bpy.context.scene.render.tile_y = tile_size_gpu
        else:
            bpy.context.scene.cycles.device = 'CPU'
            bpy.context.scene.render.tile_x = tile_size_cpu
            bpy.context.scene.render.tile_y = tile_size_cpu
        # set samples & denoising defaults
        bpy.context.scene.cycles.samples = 64
        bpy.context.scene.cycles.max_bounces = 8
        bpy.context.scene.cycles.use_adaptive_sampling = True
        # enable denoising (preferred: OptiX/AMD Intel denoiser if available)
        try:
            bpy.context.scene.view_layers["ViewLayer"].cycles.use_denoising = True
        except Exception:
            bpy.context.scene.cycles.use_denoising = True
        # if using OptiX set denoiser
        print("Cycles GPU settings applied (use_gpu=%s, device=%s)" % (use_gpu, device_type))
    except Exception as e:
        print("Failed to configure cycles GPU:", e)

def set_render_resolution(x, y, percentage=100):
    scene = bpy.context.scene
    scene.render.resolution_x = x
    scene.render.resolution_y = y
    scene.render.resolution_percentage = percentage

def set_output_format_png():
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
