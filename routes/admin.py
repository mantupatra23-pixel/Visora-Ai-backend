# routes/admin.py
from fastapi import APIRouter, Depends
from services.auth import get_admin_api_key, require_roles

router = APIRouter()

# Simple admin API-key check
@router.get("/admin/secret")
def admin_secret(_ok: bool = Depends(get_admin_api_key)):
    return {"ok": True, "msg": "you are admin"}

# Role-based protected action
@router.post("/admin/invoice")
def create_invoice(payload: dict, _check=Depends(require_roles(["billing"]))):
    # TODO: implement invoice system
    return {"ok": True, "msg": "invoice created", "data": payload}
