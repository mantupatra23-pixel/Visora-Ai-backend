# services/multichar_anim_engine.py
import os, subprocess, time, json
from pathlib import Path
import hashlib

OUT = Path("static/animations")
OUT.mkdir(parents=True, exist_ok=True)

def _safe(seed: str):
    return hashlib.sha1(seed.encode()).hexdigest()[:10]

class MultiCharAnimEngine:
    """
    High-level wrapper that:
     - If blender available -> calls blender CLI with a python script (blender_anim.py) passing a JSON job file.
     - Else -> runs a fallback 2D parallax compositor using moviepy.
    """

    def __init__(self, blender_path: str = "blender", blender_script: str = "blender_scripts/blender_anim.py"):
        self.blender_path = blender_path
        self.blender_script = Path(blender_script)
        # create blender_scripts dir if not exists
        Path("blender_scripts").mkdir(parents=True, exist_ok=True)

    def _write_job_json(self, job: dict, jobname: str = None):
        jn = jobname or f"anim_job_{_safe(json.dumps(job) + str(time.time()))}.json"
        p = OUT / jn
        with open(p, "w") as f:
            json.dump(job, f, indent=2)
        return str(p)

    def animate_with_blender(self, job: dict, output_name: str = None):
        """
        job: dict containing characters: [{name, model_path(.glb/.obj), rigged(bool), entry, actions(list)}],
             camera_cuts: [{start, end, type, params}], duration, fps
        Returns output video path.
        """
        if not self.blender_script.exists():
            raise RuntimeError("Blender script not found: blender_scripts/blender_anim.py. Put the script from repo into that path.")
        jobfile = self._write_job_json(job)
        out_name = output_name or f"anim_{_safe(jobfile)}.mp4"
        out_path = OUT / out_name

        cmd = [
            self.blender_path, "--background", "--python", str(self.blender_script), "--",
            jobfile, str(out_path)
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Blender failed:\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}")
        if not out_path.exists():
            raise RuntimeError("Blender finished but output not found: " + str(out_path))
        return str(out_path)

    def animate_fallback_2d(self, job: dict, output_name: str = None):
        """
        Lightweight fallback using moviepy: layering character images + parallax + camera cuts.
        job expects keys: duration, fps, background (image path), characters: [{image, start, end, x,y,scale, entry}] etc.
        """
        try:
            from moviepy.editor import ImageClip, concatenate_videoclips, CompositeVideoClip, AudioFileClip
        except Exception as e:
            raise RuntimeError("moviepy not installed for fallback animation: " + str(e))

        duration = job.get("duration", 20)
        fps = job.get("fps", 24)
        out_name = output_name or f"anim2d_{int(time.time())}.mp4"
        out_path = OUT / out_name

        clips = []
        # background clip
        bg = job.get("background")
        if bg and os.path.exists(bg):
            bgclip = ImageClip(bg).set_duration(duration)
        else:
            # solid color fallback: create small image
            from PIL import Image
            tmpbg = OUT / f"tmp_bg_{int(time.time())}.png"
            Image.new("RGB", (1080,1920), (20,20,30)).save(tmpbg)
            bgclip = ImageClip(str(tmpbg)).set_duration(duration)

        layers = [bgclip]
        # create per-character clips (simple: static image with zoom/pan)
        for ch in job.get("characters", []):
            img = ch.get("image")
            st = ch.get("start", 0)
            en = ch.get("end", duration)
            dur = max(0.1, en - st)
            if img and os.path.exists(img):
                ic = ImageClip(img).set_start(st).set_duration(dur)
                # apply simple pan/zoom using resize and set_pos animated
                # note: moviepy supports lambda for position
                x = ch.get("x", "center")
                y = ch.get("y", "center")
                # resize if scale provided
                scale = ch.get("scale")
                if scale:
                    ic = ic.resize(scale)
                ic = ic.set_position(lambda t: (('center' if x=='center' else x), ('center' if y=='center' else y)))
                layers.append(ic)
        composition = CompositeVideoClip(layers).set_duration(duration)
        composition.write_videofile(str(out_path), fps=fps, codec="libx264", audio=False, logger=None)
        composition.close()
        return str(out_path)

    def animate(self, job: dict, prefer_blender: bool = True, output_name: str = None):
        """
        High-level call: try blender if prefer & available, else fallback.
        """
        if prefer_blender:
            # check blender existence by running --version
            try:
                proc = subprocess.run([self.blender_path, "--version"], capture_output=True, text=True)
                if proc.returncode == 0:
                    return self.animate_with_blender(job, output_name=output_name)
            except Exception:
                pass
        # fallback
        return self.animate_fallback_2d(job, output_name=output_name)
