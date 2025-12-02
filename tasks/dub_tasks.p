# tasks/dub_tasks.py
from celery import Celery
import os, json, shlex, subprocess
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
BLENDER_BIN = os.getenv("BLENDER_BIN","blender")
app = Celery('dubbing', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def full_dubbing_pipeline(self, video_path, lang_target, voice_clone_id=None, tts_engine="coqui", consent=False):
    from services.asr_service import transcribe_with_whisper
    from services.subtitle_service import segments_to_srt
    from services.tts_service import tts_coqui, tts_pyttsx3
    from services.voice_clone import synthesize_with_clone, clone_voice_sample, require_consent

    # 1) ASR original
    asr = transcribe_with_whisper(video_path)
    if not asr.get("ok"):
        return {"ok": False, "error": "asr_failed", "detail": asr}

    segments = asr.get("segments") or []
    # 2) (optional) translate segments to target language — placeholder, no-op
    # On request integrate argos-translate or cloud translate
    # 3) Generate TTS for each segment
    out_segments = []
    for seg in segments:
        text = seg["text"]
        # if voice_clone_id provided, use synthesize_with_clone (requires consent)
        if voice_clone_id:
            try:
                require_consent(consent)
            except Exception as e:
                return {"ok": False, "error": "no_consent"}
            tts_res = synthesize_with_clone(text, voice_clone_id)
        else:
            if tts_engine == "coqui":
                tts_res = tts_coqui(text)
                if not tts_res.get("ok"):
                    tts_res = tts_pyttsx3(text)
            else:
                tts_res = tts_pyttsx3(text)
        if not tts_res.get("ok"):
            return {"ok": False, "error": "tts_failed", "detail": tts_res}
        out_segments.append({"start": seg["start"], "end": seg["end"], "text": text, "tts_path": tts_res["path"]})

    # 4) Save SRT
    srt_path = Path("jobs/dub") / (Path(video_path).stem + "_auto.srt")
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    segments_to_srt(segments, str(srt_path))

    # 5) Bake/mux dubbed video (call moviepy or Blender baker externally)
    job = {"job_id": "dub_"+Path(video_path).stem, "video": video_path, "segments": out_segments}
    jobfile = Path("jobs/dub") / (job['job_id'] + ".json")
    jobfile.write_text(json.dumps(job, indent=2))

    # Prefer running mux in system python (safer) using moviepy directly
    from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
    v = VideoFileClip(video_path)
    audio_clips = []
    for s in out_segments:
        a = AudioFileClip(s["tts_path"]).set_start(s["start"])
        audio_clips.append(a)
    comp = CompositeAudioClip(audio_clips)
    v2 = v.set_audio(comp)
    outpath = Path("jobs/dub") / (job['job_id'] + "_dubbed.mp4")
    v2.write_videofile(str(outpath), codec="libx264", audio_codec="aac", logger=None)
    return {"ok": True, "dubbed": str(outpath), "srt": str(srt_path)}
