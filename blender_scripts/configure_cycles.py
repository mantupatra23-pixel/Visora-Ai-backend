# blender_scripts/configure_cycles.py
# Helper to programmatically configure Blender Cycles render settings
# This file is intended to be imported & run inside blender python (bpy available).

import bpy
from typing import Literal

Profile = Literal["small_cpu", "gpu_nvidia", "high_end_gpu"]

def configure_cycles(profile: Profile = "gpu_nvidia", resolution=(1920,1080)):
    """
    Configure cycles render settings for common worker types.
    profile: "small_cpu", "gpu_nvidia", "high_end_gpu"
    resolution: (width, height)
    """
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x = int(resolution[0])
    scene.render.resolution_y = int(resolution[1])
    scene.render.resolution_percentage = 100

    cycles = scene.cycles

    # defaults that apply to all
    cycles.use_adaptive_sampling = True
    # make sure Denoise nodes available; enabling denoising via view or compositor is optional
    try:
        cycles.use_denoising = True
    except Exception:
        # older Blender versions: fallback to nodes compositing-based denoise
        pass

    if profile == "small_cpu":
        # CPU only
        cycles.device = 'CPU'
        cycles.samples = 32
        # tile size for CPU - moderate tiles
        scene.render.tile_x = 32
        scene.render.tile_y = 32
        # reduce bounces for speed
        cycles.max_bounces = 8
        cycles.diffuse_bounces = 2
        cycles.glossy_bounces = 2
        cycles.transmission_bounces = 2
    elif profile == "gpu_nvidia":
        # Consumer NVIDIA CUDA
        # enable GPU devices if found
        cycles.device = 'GPU'
        # set compute device type if available
        try:
            cycles.compute_device_type = 'CUDA'
        except Exception:
            pass
        cycles.samples = 64
        scene.render.tile_x = 256
        scene.render.tile_y = 256
        cycles.max_bounces = 12
        cycles.diffuse_bounces = 4
        cycles.glossy_bounces = 4
        cycles.transmission_bounces = 4
        # Prefer OptiX if available will be overridden by high_end profile
    elif profile == "high_end_gpu":
        cycles.device = 'GPU'
        # prefer OPTIX if supported
        try:
            cycles.compute_device_type = 'OPTIX'
        except Exception:
            # fallback to CUDA if OPTIX not present
            try:
                cycles.compute_device_type = 'CUDA'
            except Exception:
                pass
        # lower samples if denoiser strong; balanced quality
        cycles.samples = 48
        scene.render.tile_x = 512
        scene.render.tile_y = 512
        cycles.max_bounces = 12
        cycles.diffuse_bounces = 4
        cycles.glossy_bounces = 4
        cycles.transmission_bounces = 4
    else:
        raise ValueError("Unknown profile: " + str(profile))

    # If OptiX available, enable - many blender builds expose this via devices selection.
    # Also enable experimental feature set if you rely on DENOISING or OptiX features:
    try:
        scene.view_settings.exposure = scene.view_settings.exposure  # noop to ensure scene exists
        # set performance prefs: pref to use GPU for rendering will often be set outside script
    except Exception:
        pass

    # Optional: enable denoising node in compositor if not using native cycles denoiser
    # (user can set up compositor nodes separately)
    print(f"[configure_cycles] applied profile={profile}, res={resolution}, samples={cycles.samples}")
