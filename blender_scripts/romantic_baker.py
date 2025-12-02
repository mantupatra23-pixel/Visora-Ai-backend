# blender_scripts/romantic_baker.py
import bpy, json, sys
from pathlib import Path
from romantic_lighting import setup_romantic_light

def _args():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--")+1:]
    return []

def load_job(path):
    return json.loads(Path(path).read_text())

def main(jobfile, outdir):
    job = load_job(jobfile)
    setup_romantic_light()

    # set DOF on main camera
    cam = bpy.data.objects.get("Camera")
    if cam:
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = 1.4
        cam.data.dof.aperture_fstop = 1.8

    # do camera motions
    timeline = job["timeline"]
    for item in timeline:
        shot = item["shot"]
        cam = bpy.data.objects.get("Camera")
        if not cam: continue

        sf = item["start"]
        ef = item["start"] + item["frames"]

        if shot == "camera_push":
            cam.location.z += 0.2
            cam.keyframe_insert("location", frame=sf)
            cam.location.z -= 0.6
            cam.keyframe_insert("location", frame=ef)

    # Render
    outp = Path(outdir)
    outp.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(outp / "frame_")
    bpy.ops.render.render(animation=True)

    Path(outp/"result.json").write_text(json.dumps({"ok":True}))
    return {"ok":True}
