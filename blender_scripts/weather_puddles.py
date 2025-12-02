# blender_scripts/weather_puddles.py
import bpy, sys, json
from pathlib import Path
from mathutils import Vector

def _args():
    argv = sys.argv
    if "--" in argv: argv = argv[argv.index("--")+1:]
    else: argv = []
    return argv

def load_job(path): return json.loads(Path(path).read_text())

def find_ground_plane():
    # naive: pick the largest horizontal mesh by area as ground
    best = None; best_area = 0
    for ob in bpy.data.objects:
        if ob.type=='MESH':
            area = sum((p.area for p in ob.data.polygons)) if ob.data.polygons else 0
            # assume horizontal by normals average close to Z
            best = ob if area>best_area else best
            best_area = max(best_area, area)
    return best

def create_puddle_at(location, radius=1.0, name="Puddle"):
    bpy.ops.mesh.primitive_circle_add(radius=radius, location=location)
    obj = bpy.context.active_object
    obj.name = name
    # extrude tiny solid
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.fill()
    bpy.ops.object.mode_set(mode='OBJECT')
    # create wet material
    mat = bpy.data.materials.new(name="PuddleMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes; links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    glass = nodes.new("ShaderNodeBsdfGlossy")
    glass.inputs['Roughness'].default_value = 0.02
    mix = nodes.new("ShaderNodeMixShader")
    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.inputs['Roughness'].default_value = 0.1
    links.new(diffuse.outputs['BSDF'], mix.inputs[1])
    links.new(glass.outputs['BSDF'], mix.inputs[2])
    mix.inputs['Fac'].default_value = 0.8
    links.new(mix.outputs['Shader'], out.inputs['Surface'])
    obj.data.materials.append(mat)
    return obj

def main(jobfile, outdir):
    job = load_job(jobfile)
    ground = find_ground_plane()
    if not ground:
        # create single puddle at origin
        p = create_puddle_at((0,0,0.01), radius=job.get("config",{}).get("puddle_radius",2.0))
    else:
        # sample few positions across bounding box
        minx = min((v.co.x for v in ground.data.vertices))
        maxx = max((v.co.x for v in ground.data.vertices))
        miny = min((v.co.y for v in ground.data.vertices))
        maxy = max((v.co.y for v in ground.data.vertices))
        cx = (minx+maxx)/2; cy=(miny+maxy)/2
        p = create_puddle_at((cx,cy,0.01), radius=job.get("config",{}).get("puddle_radius",1.5))
    # ensure render settings for reflections: enable screen space/reflection probes if needed
    print("puddle created")
    return {"ok": True}

if __name__=="__main__":
    argv = _args()
    if len(argv)<2:
        print("usage: blender --background --python weather_puddles.py -- job.json outdir")
        sys.exit(1)
    jobfile, outdir = argv[0], argv[1]
    print(main(jobfile, outdir))
