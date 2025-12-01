# tasks/payment_tasks.py
from celery import Celery
import os, time, json
from services.monetization import _log_event
from pathlib import Path
import smtplib
from email.message import EmailMessage

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
app = Celery('payments', broker=BROKER, backend=BROKER)

@a pp.task(bind=True)
def process_webhook_event(self, raw_event: dict):
    """
    Receives parsed webhook event; do heavier tasks here:
      - update DB user subscription record
      - send welcome / invoice email
      - reconcile with accounting
    """
    try:
        # stub: write to file
        p = Path("data/monetize/processed")
        p.mkdir(parents=True, exist_ok=True)
        fname = p / f"{int(time.time()*1000)}_{raw_event.get('type','event')}.json"
        fname.write_text(json.dumps(raw_event, indent=2))
        # example: if checkout_completed -> send welcome email (call send_email task)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def send_email_smtp(to_email: str, subject: str, body: str):
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    if not SMTP_HOST or not SMTP_USER:
        return {"ok": False, "error": "smtp_not_configured"}
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
