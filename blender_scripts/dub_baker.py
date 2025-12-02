# blender_scripts/dub_baker.py
"""
Bakes dubbed audio into video frames/time-sync or exports audio tracks aligned to video.
Accepts job.json:
{
  "job_id":"dub_xxx",
  "video":"path/to/video.mp4",
  "segments":[{"start":0.0,"end":1.2,"text":"...", "tts_path":"..."}],
  "out_dir":"jobs/dub/job_out"
}
Usage:
blender --background --python dub_baker.py -- job.json outdir
"""
import bpy, json, sys, os
from pathlib import Path
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_audioclips

def _args():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--")+1:]
    return []

def load_job(jobfile):
    return json.loads(Path(jobfile).read_text())

def assemble_audio_for_segments(segments, fps=24):
    # concatenate tts segments into single audio track at their timeline positions
    # We'll create a silent base and overlay each clip at appropriate time using moviepy
    clips = []
    max_end = 0.0
    for s in segments:
        if not s.get("tts_path"):
            continue
        ac = AudioFileClip(s["tts_path"])
        start = s["start"]
        # pad silence before clip
        if start > 0:
            silence = AudioFileClip(s["tts_path"]).subclip(0,0)  # placeholder: moviepy requires real clips; we'll place with set_start
        ac = ac.set_start(start)
        clips.append(ac)
        max_end = max(max_end, s["start"] + ac.duration)
    if not clips:
        return None
    final = concatenate_audioclips(clips)
    return final

def bake(jobfile, outdir):
    job = load_job(jobfile)
    video_path = job.get("video")
    if not video_path or not Path(video_path).exists():
        return {"ok": False, "error": "video_missing"}
    segments = job.get("segments", [])
    # build audio track (moviepy)
    try:
        from moviepy.editor import AudioFileClip, VideoFileClip, CompositeAudioClip
        v = VideoFileClip(video_path)
        audio_clips = []
        for s in segments:
            if s.get("tts_path") and Path(s["tts_path"]).exists():
                a = AudioFileClip(s["tts_path"]).set_start(s["start"])
                audio_clips.append(a)
        if audio_clips:
            comp = CompositeAudioClip(audio_clips)
            v2 = v.set_audio(comp)
            out = Path(outdir) / (job.get("job_id") + "_dubbed.mp4")
            v2.write_videofile(str(out), codec="libx264", audio_codec="aac", threads=0, logger=None)
            return {"ok": True, "out": str(out)}
        else:
            return {"ok": False, "error": "no_tts_segments"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__=="__main__":
    argv = _args()
    if len(argv) < 2:
        print("usage: blender --background --python dub_baker.py -- job.json outdir")
        sys.exit(1)
    print(bake(argv[0], argv[1]))
