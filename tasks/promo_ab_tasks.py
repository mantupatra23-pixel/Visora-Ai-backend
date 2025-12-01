# tasks/promo_ab_tasks.py
from celery import Celery
import json, os, time
from services.thumbnail_ab import generate_variants
from services.analytics import record_event

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
app = Celery('promo_ab', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def run_ab_test(self, jobfile_path, platform="local", publish_path=None):
    # jobfile contains info: promo_video, title, caption, thumbnail_base_text
    job = json.loads(open(jobfile_path).read())
    vid = job.get('promo_video')
    base_text = job.get('title') or "Watch now"
    variants = generate_variants(vid, base_text=base_text, count=4).get('variants',[])
    # publish variants as separate posts (or upload manifests) and record analytics hooks
    posted = []
    for v in variants:
        # for demo we copy to static/published with variant suffix and record event
        import shutil
        dest = Path("static/published/thumbs")
        dest.mkdir(parents=True, exist_ok=True)
        key = dest / Path(v).name
        shutil.copy(v, key)
        posted.append(str(key))
        record_event("ab_posted", {"job": job.get("job_id"), "thumb": str(key), "platform": platform})
    # orchestrator should now wait/collect CTR metrics and pick winner
    return {"ok": True, "posted": posted, "variants_count": len(posted)}
