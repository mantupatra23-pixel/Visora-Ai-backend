# blender_scripts/romantic_lighting.py
import bpy, math

def setup_romantic_light():
    # Warm key light
    bpy.ops.object.light_add(type='AREA', location=(3, -2, 2))
    key = bpy.context.active_object
    key.data.energy = 1200
    key.data.color = (1.0, 0.75, 0.55)  # warm tone
    key.data.shape = 'RECTANGLE'

    # Rim light
    bpy.ops.object.light_add(type='POINT', location=(-2, 2, 2))
    rim = bpy.context.active_object
    rim.data.energy = 600
    rim.data.color = (0.9, 0.7, 0.8)

    # Bloom & Soft DOF
    scene = bpy.context.scene
    scene.eevee.use_bloom = True
    scene.eevee.bloom_intensity = 0.08
    scene.eevee.bloom_threshold = 0.85

    # Optional colorgrading
    if scene.view_settings:
        scene.view_settings.look = 'Medium High Contrast'
        scene.view_settings.exposure = 0.3

    print("Romantic lighting applied!")
