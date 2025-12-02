# tasks/india_localization_tasks.py
from celery import Celery, chain
import os, json, shlex, subprocess, uuid
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
app = Celery('india_localize', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def step_asr(self, jobfile):
    from services.india_localize_service import update_job
    from services.asr_service import transcribe_with_whisper, transcribe_with_vosk
    job = json.loads(Path(jobfile).read_text())
    src = job['source_media']
    # try whisper first (auto language detect)
    res = transcribe_with_whisper(src, lang=None, model="small")
    if not res.get("ok"):
        # fallback to vosk (requires model install) or fail
        res = transcribe_with_vosk(src)
    job['asr'] = res
    job['steps'].append("asr_done")
    Path(jobfile).write_text(json.dumps(job, indent=2))
    return jobfile

@app.task(bind=True)
def step_translate(self, jobfile):
    from services.india_localize_service import update_job
    job = json.loads(Path(jobfile).read_text())
    segments = job.get('asr', {}).get('segments', [])
    # if segments empty, use whole text as one segment
    if not segments and job.get('asr', {}).get('text'):
        segments = [{"start":0.0, "end":0.0, "text": job['asr']['text']}]
    translations = {}
    # try argos-translate if available, else fallback to cloud placeholder
    try:
        import argostranslate.package, argostranslate.translate
        # ensure target languages installed externally; here we try dynamic translate
        for tl in job['target_langs']:
            translated_segments = []
            for seg in segments:
                translated = argostranslate.translate.translate(seg['text'], job.get('asr',{}).get('lang','auto'), tl)
                translated_segments.append({"start": seg.get('start'), "end": seg.get('end'), "text": translated})
            translations[tl] = translated_segments
    except Exception:
        # fallback: keep original text (user can plug cloud translate)
        for tl in job['target_langs']:
            translations[tl] = [{"start":s.get('start'), "end": s.get('end'), "text": s.get('text')} for s in segments]
    job['translations'] = translations
    job['steps'].append("translate_done")
    Path(jobfile).write_text(json.dumps(job, indent=2))
    return jobfile

@app.task(bind=True)
def step_tts_all(self, jobfile):
    from services.tts_service import tts_coqui, tts_pyttsx3
    job = json.loads(Path(jobfile).read_text())
    translations = job.get('translations', {})
    tts_map = {}
    for tl, segs in translations.items():
        tts_map[tl] = []
        for seg in segs:
            text = seg['text']
            # resolve language model hint (coqui preferred)
            res = tts_coqui(text, lang=tl)
            if not res.get("ok"):
                res = tts_pyttsx3(text, lang=tl)
            tts_map[tl].append({"start": seg.get('start'), "end": seg.get('end'), "text": text, "tts_path": res.get("path")})
    job['tts_map'] = tts_map
    job['steps'].append("tts_done")
    Path(jobfile).write_text(json.dumps(job, indent=2))
    return jobfile

@app.task(bind=True)
def step_subtitles(self, jobfile):
    from services.subtitle_service import segments_to_srt
    job = json.loads(Path(jobfile).read_text())
    out_dir = Path(job['output_dir'])
    srt_files = {}
    for tl, segs in job.get('translations', {}).items():
        srt_path = out_dir / f"{job['job_id']}_{tl}.srt"
        segments_to_srt(segs, str(srt_path))
        srt_files[tl] = str(srt_path)
    job['srt_files'] = srt_files
    job['steps'].append("srt_done")
    Path(jobfile).write_text(json.dumps(job, indent=2))
    return jobfile

@app.task(bind=True)
def step_dub_bake(self, jobfile, do_bake: bool = True):
    # if do_bake True, create dubbed video for each target (moviepy used)
    job = json.loads(Path(jobfile).read_text())
    out_dir = Path(job['output_dir'])
    results = {}
    if not do_bake:
        job['steps'].append("dub_skipped")
        job['dub_results'] = {}
        Path(jobfile).write_text(json.dumps(job, indent=2))
        return jobfile
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
    except Exception as e:
        job['steps'].append("dub_failed_no_moviepy")
        Path(jobfile).write_text(json.dumps(job, indent=2))
        return jobfile
    src_video = job['source_media']
    v = VideoFileClip(src_video)
    for tl, segs in job.get('tts_map', {}).items():
        audio_clips = []
        for s in segs:
            if s.get('tts_path'):
                a = AudioFileClip(s['tts_path']).set_start(float(s.get('start') or 0.0))
                audio_clips.append(a)
        if audio_clips:
            comp = CompositeAudioClip(audio_clips)
            v2 = v.set_audio(comp)
            outp = out_dir / f"{job['job_id']}_dub_{tl}.mp4"
            v2.write_videofile(str(outp), codec="libx264", audio_codec="aac", logger=None)
            results[tl] = str(outp)
    job['dub_results'] = results
    job['steps'].append("dub_done")
    Path(jobfile).write_text(json.dumps(job, indent=2))
    return jobfile

@app.task(bind=True)
def full_localization_pipeline(self, job_id_or_file):
    # Accept either jobfile path or job id (path resolution)
    if Path(job_id_or_file).exists():
        jobfile = job_id_or_file
    else:
        jobfile = str(Path("jobs/india_localize") / (job_id_or_file + ".json"))
    # run chain
    res1 = step_asr.run(jobfile)
    res2 = step_translate.run(res1)
    res3 = step_tts_all.run(res2)
    res4 = step_subtitles.run(res3)
    res5 = step_dub_bake.run(res4, True)
    return {"ok": True, "jobfile": jobfile}
