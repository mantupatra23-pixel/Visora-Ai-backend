# services/monetization.py
import os, json, stripe, datetime
from pathlib import Path

# load env
STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")  # use to verify incoming webhooks
STRIPE_PRICE_IDS_JSON = os.getenv("STRIPE_PRICE_IDS_JSON", "{}")  # e.g. '{"monthly":"price_xxx","yearly":"price_yyy"}'

if STRIPE_SECRET:
    stripe.api_key = STRIPE_SECRET

DATA_DIR = Path("data/monetize")
DATA_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_FILE = DATA_DIR / "events.log"  # append-only ledger of events

def _log_event(ev: dict):
    ev['received_at'] = datetime.datetime.utcnow().isoformat()
    EVENTS_FILE.write_text(EVENTS_FILE.read_text() + json.dumps(ev) + "\n") if EVENTS_FILE.exists() else EVENTS_FILE.write_text(json.dumps(ev) + "\n")
    return True

def create_checkout_session(customer_email: str, price_id: str, success_url: str, cancel_url: str, mode: str = "subscription"):
    """
    mode: 'payment' or 'subscription'
    price_id: Stripe Price ID for product/tier
    returns session url
    """
    if not STRIPE_SECRET:
        return {"ok": False, "error": "stripe_not_configured"}
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode=mode,
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=customer_email,
            success_url=success_url,
            cancel_url=cancel_url
        )
        _log_event({"type":"checkout_created","session":session.id,"email":customer_email,"price":price_id})
        return {"ok": True, "session_id": session.id, "url": session.url}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def handle_stripe_webhook(payload: bytes, sig_header: str | None = None):
    """
    Verify signature if webhook secret present; then process event; returns (ok, result)
    """
    if STRIPE_WEBHOOK_SECRET and sig_header:
        try:
            event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=STRIPE_WEBHOOK_SECRET)
        except Exception as e:
            return {"ok": False, "error": "webhook_signature_invalid", "detail": str(e)}
    else:
        # best-effort parse
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception as e:
            return {"ok": False, "error": "invalid_payload", "detail": str(e)}
    # log raw
    _log_event({"type":"stripe_raw_event","id": event.get("id"), "kind": event.get("type")})
    # Basic handling for common events
    typ = event.get("type")
    data = event.get("data", {}).get("object", {})
    if typ == "checkout.session.completed":
        # mark user subscribed/paid
        cust_email = data.get("customer_email") or data.get("customer")
        _log_event({"type":"checkout_completed","session": data.get("id"), "email": cust_email})
        # maybe create subscription record or send tasks
        return {"ok": True, "action": "checkout_completed", "email": cust_email}
    if typ == "invoice.payment_succeeded":
        _log_event({"type":"invoice_payment_succeeded","invoice": data.get("id"), "subscription": data.get("subscription")})
        return {"ok": True, "action": "invoice_success", "invoice": data.get("id")}
    if typ == "customer.subscription.deleted":
        _log_event({"type":"subscription_deleted","sub": data.get("id"), "status": data.get("status")})
        return {"ok": True, "action": "sub_deleted", "sub": data.get("id")}
    # fallback
    _log_event({"type":"stripe_other","event": typ})
    return {"ok": True, "action": "noop", "event": typ}

def get_price_ids():
    try:
        return json.loads(STRIPE_PRICE_IDS_JSON)
    except:
        return {}

def record_manual_payment(user_id: str, amount_cents: int, currency: str = "usd", note: str | None = None):
    ev = {"type":"manual_payment","user":user_id,"amount_cents": amount_cents,"currency":currency}
    if note: ev['note']=note
    _log_event(ev)
    return {"ok": True}
