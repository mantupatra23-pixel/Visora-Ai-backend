# services/iap_verifier.py
import os, json, requests
from pathlib import Path

def verify_google_play_receipt(package_name: str, product_id: str, purchase_token: str, access_token: str | None = None):
    """
    Use Google Play Developer API: purchases.products.get
    Requires a service account and OAuth2 token with Android Publisher scopes.
    Here we provide a HTTP template. Prefer googleapiclient in production.
    """
    url = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{package_name}/purchases/products/{product_id}/tokens/{purchase_token}"
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return {"ok": True, "data": r.json()}
    return {"ok": False, "status": r.status_code, "text": r.text}

def verify_apple_receipt(receipt_data_base64: str, password: str | None = None, sandbox: bool = False):
    """
    Use App Store verifyReceipt endpoint.
    For production you must supply the shared secret (password) for auto-renewable subscriptions.
    """
    url = "https://buy.itunes.apple.com/verifyReceipt" if not sandbox else "https://sandbox.itunes.apple.com/verifyReceipt"
    payload = {"receipt-data": receipt_data_base64}
    if password: payload["password"]=password
    r = requests.post(url, json=payload)
    if r.status_code == 200:
        return {"ok": True, "data": r.json()}
    return {"ok": False, "status": r.status_code, "text": r.text}
