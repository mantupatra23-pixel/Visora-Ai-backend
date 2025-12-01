# tasks/composite_orchestrator.py
from celery import Celery, group, chain
import json, os, tarfile, uuid, subprocess, shlex
from pathlib import Path
from tasks.compositor_worker import render_frame_task, upload_to_s3
from services.resolve_export import make_resolve_xml

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
app = Celery('comp_orch', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def orchestrate_comp(self, jobfile):
    job = json.load(open(jobfile))
    start = job.get("start_frame",1); end = job.get("end_frame",start)
    outdir = Path(job.get("output",{}).get("dir","static/compositor/frames")) / job.get("job_id",str(uuid.uuid4())[:6])
    outdir.mkdir(parents=True, exist_ok=True)
    # submit parallel frame tasks
    frames = list(range(start, end+1))
    grp = group(render_frame_task.s(jobfile, f, str(outdir)) for f in frames)
    res = grp.apply_async()
    # wait synchronously (or return group id and let client poll) — here we'll wait naive (not recommended for very long jobs)
    res.get()  # blocks until done
    # optional grade into video (if output.type == mp4)
    out_spec = job.get("output", {})
    if out_spec.get("type") in ("mp4","mov"):
        pattern = str(outdir / "out_%04d.png")
        lut = job.get("grade", {}).get("path")
        final_path = job.get("output", {}).get("path", str(outdir / "final.mp4"))
        if lut:
            cmd = f'ffmpeg -y -r {out_spec.get("fps",25)} -i {pattern} -vf lut3d=file={shlex.quote(lut)} -c:v libx264 -crf 18 {shlex.quote(final_path)}'
        else:
            cmd = f'ffmpeg -y -r {out_spec.get("fps",25)} -i {pattern} -c:v libx264 -crf 18 {shlex.quote(final_path)}'
        subprocess.run(cmd, shell=True)
    # optional archive + upload
    if job.get("upload",{}).get("s3",False):
        archive = str(outdir.parent / (outdir.name + ".tar.gz"))
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(outdir, arcname=outdir.name)
        bucket = job["upload"]["s3"]["bucket"]
        key = job["upload"]["s3"].get("key", outdir.name + ".tar.gz")
        upload_to_s3.delay(archive, bucket, key)
    # produce Resolve XML for the final clip
    clips = [{"file": job.get("output",{}).get("path", ""), "start_time":0.0, "duration": (end-start+1)/job.get("output",{}).get("fps",25)}]
    xml_path = str(outdir / "resolve_import.xml")
    make_resolve_xml(clips, xml_path, fps=job.get("output",{}).get("fps",25))
    return {"ok": True, "frames": len(frames), "final": job.get("output",{}).get("path",""), "resolve_xml": xml_path}
