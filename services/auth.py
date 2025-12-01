# services/auth.py
from fastapi import Request, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
import os

API_KEY_NAME = os.getenv("ADMIN_API_KEY_NAME", "x-api-key")
ADMIN_KEYS = set([k.strip() for k in os.getenv("ADMIN_KEYS","").split(",") if k.strip()])

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_admin_api_key(api_key_header_val: str = Security(api_key_header)):
    """
    Simple API-Key check. Provide ADMIN_KEYS env like "key1,key2".
    Raises HTTPException(403) if invalid.
    """
    if not ADMIN_KEYS:
        # If no admin keys configured, deny by default (safer)
        raise HTTPException(status_code=403, detail="admin auth not configured")
    if not api_key_header_val or api_key_header_val not in ADMIN_KEYS:
        raise HTTPException(status_code=403, detail="invalid api key")
    return api_key_header_val

# role decorator helper (very simple)
def require_roles(roles: list):
    def dep(api_key: str = Security(get_admin_api_key)):
        # placeholder: if you want role mapping for api_key, expand here.
        # For now allow any valid admin key to pass.
        return True
    return dep
