# services/analytics.py
"""
Lightweight local analytics store (JSON files) to track events and simple KPIs.
For production connect to real analytics DB (Influx/Timescale/GA).
"""
import json, time
from pathlib import Path
ROOT = Path(".").resolve()
ANALYTICS_DIR = ROOT / "data" / "analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

def record_event(name: str, payload: dict):
    ev = {"event": name, "ts": time.time(), "payload": payload}
    f = ANALYTICS_DIR / f"ev_{int(time.time()*1000)}_{name}.json"
    f.write_text(json.dumps(ev))

def list_events(limit=100):
    files = sorted(list(ANALYTICS_DIR.glob("ev_*.json")), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    return [json.loads(p.read_text()) for p in files]

def report_summary():
    # produce count per event type
    evs = list_events(1000)
    summary = {}
    for e in evs:
        summary[e['event']] = summary.get(e['event'],0)+1
    return summary
