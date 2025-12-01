# routes/monetize.py
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel
from services.monetization import create_checkout_session, handle_stripe_webhook, get_price_ids, record_manual_payment
import json

router = APIRouter()

class CheckoutReq(BaseModel):
    email: str
    tier: str  # key name matching STRIPE_PRICE_IDS_JSON keys
    success_url: str
    cancel_url: str
    mode: str = "subscription"

@router.post("/create_checkout")
async def create_checkout(req: CheckoutReq):
    price_map = get_price_ids()
    price_id = price_map.get(req.tier)
    if not price_id:
        raise HTTPException(status_code=400, detail="tier_not_found")
    res = create_checkout_session(req.email, price_id, req.success_url, req.cancel_url, mode=req.mode)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res)
    return res

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(None)):
    body = await request.body()
    res = handle_stripe_webhook(body, stripe_signature)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res)
    return {"ok": True, "handled": res.get("action")}

class ManualPay(BaseModel):
    user_id: str
    amount_cents: int
    currency: str = "usd"
    note: str | None = None

@router.post("/admin/manual_payment")
def admin_manual_payment(req: ManualPay):
    # For admin use only — protect with auth in real app
    r = record_manual_payment(req.user_id, req.amount_cents, req.currency, req.note)
    return r

@router.get("/prices")
def prices():
    return get_price_ids()
