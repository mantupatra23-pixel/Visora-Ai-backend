# tasks/promo_orchestrator.py
from celery import Celery
import time, json
from services.analytics import list_events, report_summary, record_event

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
app = Celery('promo_orch', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def decide_ab_winner(self, job_id, wait_seconds=3600):
    """
    Naive orchestrator: wait for wait_seconds, then inspect analytics for events 'ab_click' or 'ab_view' related to job_id.
    Pick variant with highest clicks/views ratio and record as winner.
    """
    time.sleep(wait_seconds)
    evs = list_events(1000)
    # filter ab metrics
    counters = {}
    for e in evs:
        if e['event'].startswith("ab_"):
            p = e['payload']
            if p.get("job") == job_id:
                thumb = p.get("thumb")
                counters.setdefault(thumb, {"views":0,"clicks":0})
                if e['event']=="ab_view": counters[thumb]["views"] += 1
                if e['event']=="ab_click": counters[thumb]["clicks"] += 1
    # decide
    best = None; best_score = -1
    for thumb, m in counters.items():
        views = m.get("views",1)
        clicks = m.get("clicks",0)
        score = clicks / float(views) if views>0 else 0
        if score > best_score:
            best_score = score; best = thumb
    record_event("ab_winner", {"job": job_id, "winner": best, "score": best_score})
    return {"ok": True, "winner": best, "score": best_score}
