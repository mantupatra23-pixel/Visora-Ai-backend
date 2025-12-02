# blender_scripts/weather_baker.py
import bpy, sys, json, os, math, random
from pathlib import Path
from mathutils import Vector, Color

# small helper: append path so we can import local modules if needed
ROOT = Path(__file__).parent.parent.resolve()
sys.path.append(str(ROOT))

def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--")+1:]
    else:
        argv = []
    return argv

def load_job(path):
    return json.loads(Path(path).read_text())

def ensure_scene(scene_file=None):
    # If scene_file provided, try to open it
    if scene_file and Path(scene_file).exists():
        bpy.ops.wm.open_mainfile(filepath=str(scene_file))
        return
    # else start with a new scene with default cube removed
    bpy.ops.wm.read_factory_settings(use_empty=True)

def make_volume_fog(density=0.05, height=5.0, color=[0.9,0.95,1.0]):
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = density
    vol.inputs["Color"].default_value = (*color, 1.0)
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])

def add_sun_light(strength=5, angle=0.1):
    light_data = bpy.data.lights.new(name="Sun", type='SUN')
    light_data.energy = strength
    light_object = bpy.data.objects.new(name="Sun", object_data=light_data)
    bpy.context.collection.objects.link(light_object)
    light_object.rotation_euler = (math.radians(50), 0, math.radians(30))
    return light_object

def create_particle_rain(intensity=0.6, particle_size=0.02, wind=5):
    # create emitter plane high above scene
    bpy.ops.mesh.primitive_plane_add(size=50, location=(0,0,20))
    emitter = bpy.context.active_object
    emitter.name = "RainEmitter"
    # particle system
    ps = emitter.modifiers.new(name="RainPS", type='PARTICLE_SYSTEM').particle_system
    settings = ps.settings
    settings.count = int(5000 * intensity)
    settings.frame_start = 1
    settings.frame_end = 250
    settings.lifetime = 80
    settings.render_type = 'OBJECT'
    # make a simple drop object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=particle_size, location=(0,0,0))
    drop = bpy.context.active_object
    drop.name = "Drop"
    drop.scale = (0.1,0.1,1.0)
    settings.instance_object = drop
    # wind force
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
    wind = bpy.context.active_object
    wind.name = "Wind"
    wf = wind.constraints.new(type='DAMPED_TRACK') if False else None
    # add force field
    bpy.ops.object.forcefield_toggle()
    # better: create wind object
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
    wind_obj = bpy.context.active_object
    wind_obj.name = "WindField"
    wind_obj.field.type = 'WIND'
    wind_obj.field.strength = wind
    wind_obj.field.flow = 1.0
    return emitter, drop, wind_obj

def create_snow(intensity=0.4, particle_size=0.05, wind=1):
    # reuse rain emitter but change physics
    emitter, drop, wind_obj = create_particle_rain(intensity=max(0.1,intensity), particle_size=particle_size, wind=wind)
    drop.scale = (0.8,0.8,0.8)
    # change physics to use drag and slower fall
    ps = emitter.particle_systems[0]
    ps.settings.physics_type = 'NEWTON'
    ps.settings.normal_factor = 0.02
    ps.settings.brownian_factor = 0.2
    ps.settings.drag_factor = 0.4
    return emitter, drop, wind_obj

def add_volumetric_lights():
    # sun + volumetric lighting -> god rays in compositor (render passes required)
    add_sun_light(strength=8)
    # compositor nodes setup for bloom/god ray (simple)
    bpy.context.scene.use_nodes = True
    nt = bpy.context.scene.node_tree
    nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers")
    glare = nt.nodes.new("CompositorNodeGlare")
    glare.glare_type = 'FOG_GLOW'
    glare.quality = 'HIGH'
    comp_out = nt.nodes.new("CompositorNodeComposite")
    nt.links.new(rl.outputs['Image'], glare.inputs['Image'])
    nt.links.new(glare.outputs['Image'], comp_out.inputs['Image'])

def make_wet_shader_on_objects(wetness=0.5):
    # Simple approach: for each mesh, mix original material with glossy layer
    for ob in bpy.data.objects:
        if ob.type=='MESH':
            for mat_slot in ob.material_slots:
                mat = mat_slot.material
                if not mat: continue
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links
                # add mix node for glossy
                glossy = nodes.new("ShaderNodeBsdfGlossy")
                glossy.inputs['Roughness'].default_value = max(0.05,1.0 - wetness)
                mix = nodes.new("ShaderNodeMixShader")
                # find material output
                out = None
                for n in nodes:
                    if n.type == 'OUTPUT_MATERIAL':
                        out = n; break
                if not out: continue
                # connect existing principled to mix[0], glossy to mix[1]
                principled = None
                for n in nodes:
                    if n.type == 'BSDF_PRINCIPLED':
                        principled = n; break
                if not principled: continue
                links.new(principled.outputs['BSDF'], mix.inputs[1])
                links.new(glossy.outputs['BSDF'], mix.inputs[2])
                # factor from wetness
                mix.inputs['Fac'].default_value = wetness
                links.new(mix.outputs['Shader'], out.inputs['Surface'])

def create_lightning_effect(chance=0.2, flashes=3):
    # Create point light and animate brightness to simulate lightning
    for i in range(flashes):
        # random frame
        frame = random.randint(10, 200)
        light_data = bpy.data.lights.new(name=f"Lightning_{i}", type='POINT')
        light_obj = bpy.data.objects.new(name=f"Lightning_{i}", object_data=light_data)
        bpy.context.collection.objects.link(light_obj)
        light_obj.location = (random.uniform(-10,10), random.uniform(-10,10), random.uniform(5,15))
        light_data.energy = 0
        light_obj.keyframe_insert(data_path="data.energy", frame=frame-1)
        light_data.energy = 2000
        light_obj.keyframe_insert(data_path="data.energy", frame=frame)
        light_data.energy = 0
        light_obj.keyframe_insert(data_path="data.energy", frame=frame+3)

def bake_and_export(out_dir, frames, export):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = frames
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    if export == "frames":
        # render frames as PNG sequence
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str(Path(out_dir) / "frame_")
        bpy.ops.render.render(animation=True)
    elif export == "exr":
        scene.render.image_settings.file_format = 'OPEN_EXR'
        scene.render.filepath = str(Path(out_dir) / "frame_")
        bpy.ops.render.render(animation=True)
    else:
        # export .blend and FBX snapshot
        blend_out = Path(out_dir) / "scene_with_weather.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))
        # export FBX of whole scene
        fbx_out = Path(out_dir) / "scene_weather.fbx"
        bpy.ops.export_scene.fbx(filepath=str(fbx_out))
    return True

def main(jobfile, outdir):
    job = load_job(jobfile)
    cfg = job.get("config", {})
    frames = job.get("frames", 240)
    export = job.get("export", "frames")
    scene_file = job.get("scene_file")
    ensure_scene(scene_file)
    t = cfg.get("type","rain")
    # basic environment
    if t in ("fog","mist"):
        make_volume_fog(density=cfg.get("density",0.05), height=cfg.get("height",5.0), color=cfg.get("color",[0.9,0.95,1.0]))
    if t in ("rain","storm"):
        intensity = cfg.get("intensity",0.7)
        particle_size = cfg.get("particle_size",0.02)
        wind = cfg.get("wind",6)
        create_particle_rain(intensity=intensity, particle_size=particle_size, wind=wind)
        make_wet_shader_on_objects(wetness=cfg.get("wetness",0.5))
    if t == "snow":
        create_snow(intensity=cfg.get("intensity",0.6), particle_size=cfg.get("particle_size",0.05), wind=cfg.get("wind",1))
    if t == "storm" and cfg.get("lightning", False):
        create_lightning_effect()
    # volumetric lights / god-rays optional
    add_volumetric_lights()
    # bake/export
    success = bake_and_export(outdir, frames, export)
    return {"ok": success}

if __name__ == "__main__":
    argv = _args()
    if len(argv) < 2:
        print("usage: blender --background --python weather_baker.py -- job.json outdir")
        sys.exit(1)
    jobfile, outdir = argv[0], argv[1]
    res = main(jobfile, outdir)
    print(res)
