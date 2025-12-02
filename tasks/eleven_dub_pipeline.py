# Full dubbing pipeline using ElevenLabs
from celery import Celery
import json, os
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER", "redis://redis:6379/0")
app = Celery("eleven_dub", broker=BROKER, backend=BROKER)

@app.task(bind=True)
def eleven_full_dub(self, video_path, target_lang="hi", voice_id=None):
    from services.asr_service import transcribe_with_whisper
    from services.eleven_lang_map import get_lang_config
    from services.elevenlabs_service import eleven_tts
    from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip

    config = get_lang_config(target_lang)
    model = config["model"]
    default_voice = config["voice"]

    # ASR
    res = transcribe_with_whisper(video_path)
    segs = res.get("segments", [])

    audio_clips = []
    for s in segs:
        txt = s["text"]
        tts = eleven_tts(txt, voice_id=voice_id or default_voice, model=model)
        if tts["ok"]:
            a = AudioFileClip(tts["path"]).set_start(s["start"])
            audio_clips.append(a)

    v = VideoFileClip(video_path)
    comp = CompositeAudioClip(audio_clips)
    out = f"jobs/eleven_dub/{target_lang}_{Path(video_path).stem}.mp4"
    Path("jobs/eleven_dub").mkdir(parents=True, exist_ok=True)

    v2 = v.set_audio(comp)
    v2.write_videofile(out, codec="libx264", audio_codec="aac", logger=None)

    return {"ok": True, "dubbed": out}
