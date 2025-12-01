# services/revenue_reporting.py
import datetime, json
from pathlib import Path
DATA = Path("data/monetize/events.log")

def parse_events():
    if not DATA.exists(): return []
    lines = DATA.read_text().strip().splitlines()
    evs = [json.loads(l) for l in lines if l.strip()]
    return evs

def report_daily(start_date: str | None = None):
    """
    start_date in YYYY-MM-DD. Aggregates totals by date and event type
    """
    evs = parse_events()
    daily = {}
    for e in evs:
        ts = e.get("received_at")
        if not ts:
            continue
        day = ts.split("T")[0]
        daily.setdefault(day, {"payments":0,"invoices":0,"events":0})
        if e.get("type","").startswith("invoice") or e.get("type")=="invoice_payment_succeeded":
            daily[day]["invoices"] += 1
        if e.get("type") in ("checkout_completed","invoice_payment_succeeded","manual_payment"):
            daily[day]["payments"] += 1
        daily[day]["events"] += 1
    return daily
