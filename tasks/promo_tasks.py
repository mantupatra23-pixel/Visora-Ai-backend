# tasks/promo_tasks.py (updated)
from celery import Celery, chain
import os, json
from pathlib import Path
from services.promo_generator import pick_best_clips, make_thumbnail_from_video
from services.asr_whisper import transcribe_file
from services.caption_hashtag_enhancer import craft_caption
from services.youtube_uploader import upload_video
from tasks.promo_ab_tasks import run_ab_test
from tasks.promo_orchestrator import decide_ab_winner
from services.analytics import record_event

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
app = Celery('promo', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def render_and_publish(self, jobfile_path):
    jf = Path(jobfile_path)
    if not jf.exists():
        return {"ok": False, "error": "missing_jobfile", "path": str(jf)}
    job = json.loads(jf.read_text())
    try:
        master = job['master_video']
        length = job.get('length',15)
        # 1) create promo video
        res = pick_best_clips(master, length=length, ratio=job.get('ratio','9:16'))
        if not res.get('ok'):
            job['status']='failed'
            job['error']=res
            jf.write_text(json.dumps(job,indent=2))
            return res
        promo_video = res['promo_video']

        # 2) generate subtitles (ASR) if requested
        if job.get('auto_subtitles', True):
            asr = transcribe_file(master, lang=job.get('lang'), output_format="srt")
            if asr.get('ok'):
                job['subtitles'] = asr.get('srt') or asr.get('text')

        # 3) craft caption & hashtags
        craft = craft_caption(job.get('title'), job.get('script'), job.get('subtitles'), tone=job.get('tone','energetic'))
        job['caption'] = craft.get('caption')
        job['hashtags'] = craft.get('hashtags')

        # 4) thumbnail base + A/B test optionally
        thumb = make_thumbnail_from_video(promo_video, overlay_text=job.get('title'))
        if thumb.get('ok'):
            job['thumbnail'] = thumb.get('thumbnail')

        jf.write_text(json.dumps(job, indent=2))

        # 5) schedule or upload to configured platforms
        platforms = job.get('platform',[])
        upload_results = {}
        for p in platforms:
            if p and p.lower() in ("youtube","yt"):
                publish_at = job.get('schedule_at')  # ISO string or None
                up = upload_video(
                    promo_video,
                    job.get('title') or "Visora Promo",
                    job.get('caption') or "",
                    tags=job.get('hashtags'),
                    thumbnail_path=job.get('thumbnail'),
                    publish_at_iso=publish_at
                )
                upload_results['youtube'] = up
            else:
                # placeholder: other platforms (tiktok, instagram) can be added
                upload_results[p] = {"ok": False, "error": "platform_not_supported"}

        job['upload_results'] = upload_results
        job['status'] = 'rendered'
        jf.write_text(json.dumps(job, indent=2))

        record_event("promo_rendered", {"job_id": job.get('job_id')})

        # 6) if AB testing requested -> schedule AB tasks
        if job.get('ab_test', False):
            t = run_ab_test.delay(str(jf), platform=job.get('ab_platform','local'))
            decide_ab_winner.apply_async((job.get('job_id'),), countdown=job.get('ab_wait_seconds',3600))
            job['ab_task_id'] = t.id
            jf.write_text(json.dumps(job, indent=2))

        return {"ok": True, "job": job}
    except Exception as e:
        # best-effort error saving
        try:
            job['status']='error'
            job['error']=str(e)
            jf.write_text(json.dumps(job,indent=2))
        except Exception:
            pass
        return {"ok": False, "error": str(e)}
PY
