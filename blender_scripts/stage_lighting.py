# blender_scripts/stage_lighting.py
# run inside Blender: creates stage lights, color ramps, moving spotlights synced to beats via keyframes
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector

def _args():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--")+1:]
    return []

def load_job(path):
    return json.loads(Path(path).read_text())

def create_spot(name, loc, energy=800, color=(1,0.2,0.6)):
    bpy.ops.object.light_add(type='SPOT', location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.energy = energy
    obj.data.color = color
    obj.data.spot_size = math.radians(45)
    return obj

def keyframe_spot_color(spot_obj, frame, color):
    spot_obj.data.color = color
    spot_obj.data.keyframe_insert(data_path="color", frame=frame)

def build_stage(jobfile, outdir):
    job = load_job(jobfile)
    beats = [b["time"] for b in job.get("timeline",[])]
    # create 4 moving spots
    spots = []
    for i in range(4):
        s = create_spot(f"Spot_{i}", ( -6 + i*4, -6, 6 ), energy=1000)
        spots.append(s)
    # keyframe colors on beat times (index->color cycle)
    colors = [ (1,0.1,0.1), (0.1,0.1,1.0), (0.1,1.0,0.2), (1.0,0.8,0.2) ]
    fps = job.get("bpm",120) and 24 or 24
    for idx, t in enumerate(beats):
        frame = int(t * fps) + 1
        for s in spots:
            c = colors[idx % len(colors)]
            keyframe_spot_color(s, frame, c)
    # optional strobe on strong beats
    for idx, b in enumerate(beats):
        if idx % 4 == 0:
            frame = int(b*fps)
            # quick strobe: amplify energy then drop
            for s in spots:
                s.data.energy = s.data.energy * 1.0
                s.data.keyframe_insert(data_path="energy", frame=frame-1)
                s.data.energy = s.data.energy * 4.0
                s.data.keyframe_insert(data_path="energy", frame=frame)
                s.data.energy = s.data.energy * 1.0
                s.data.keyframe_insert(data_path="energy", frame=frame+2)
    # render preview frames
    outp = Path(outdir); outp.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(outp / "frame_")
    try:
        bpy.ops.render.render(animation=True)
    except Exception as e:
        print("render failed:", e)
    return {"ok": True}
