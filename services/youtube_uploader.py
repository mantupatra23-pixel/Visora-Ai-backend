"""
YouTube uploader using google-auth / google-api-python-client.

- Usage overview:
  1) Perform OAuth consent flow with get_authorize_url() and exchange_code_for_tokens()
     to store refresh token (saved under secrets/ by default).
  2) Call upload_video(filepath, title, description, tags, thumbnail_path, publish_at_iso, token_name)
     to upload a video.

Notes:
- Requires: google-auth, google-auth-oauthlib, google-api-python-client
- Ensure CLIENT_SECRETS_FILE points to a valid Google client_secrets JSON.
"""
import os
import json
import datetime
from pathlib import Path
from typing import Optional, List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Config: override with env vars if needed
CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
TOKENS_DIR = Path(os.getenv("YOUTUBE_TOKENS_DIR", "secrets"))
TOKENS_DIR.mkdir(parents=True, exist_ok=True)

def get_authorize_url(state: str = "visora_promos", redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
    """
    Return an OAuth2 consent URL. Open it in browser, copy the code back and call exchange_code_for_tokens().
    """
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true",
        state=state
    )
    return auth_url

def exchange_code_for_tokens(code: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob", token_name: str = "default") -> dict:
    """
    Exchange authorization code for tokens and save refresh token to TOKENS_DIR/yt_{token_name}.json.
    """
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_file = TOKENS_DIR / f"yt_{token_name}.json"
    token_file.write_text(json.dumps({
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": flow.client_config.get('client_id'),
        "client_secret": flow.client_config.get('client_secret')
    }, indent=2))
    return {"ok": True, "token_file": str(token_file)}

def _load_creds(token_name: str = "default") -> Optional[Credentials]:
    """
    Load stored refresh token and build google.oauth2.credentials.Credentials object.
    Attempt to refresh to get access token (best-effort).
    """
    token_file = TOKENS_DIR / f"yt_{token_name}.json"
    if not token_file.exists():
        return None
    data = json.loads(token_file.read_text())
    creds = Credentials(
        token=None,
        refresh_token=data.get("refresh_token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        token_uri="https://oauth2.googleapis.com/token"
    )
    try:
        from google.auth.transport.requests import Request
        request = Request()
        creds.refresh(request)
    except Exception:
        # If refresh fails here, googleapiclient will try when building the service.
        pass
    return creds

def upload_video(
    filepath: str,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    thumbnail_path: Optional[str] = None,
    publish_at_iso: Optional[str] = None,
    token_name: str = "default",
    privacy_status: str = "private"
) -> dict:
    """
    Upload a video file to YouTube.

    Args:
      - filepath: path to video file
      - title, description: metadata
      - tags: list of strings
      - thumbnail_path: optional path to thumbnail image
      - publish_at_iso: RFC3339 timestamp string to schedule publish (requires privacyStatus='private' and publishAt set)
      - token_name: which saved token to use (yt_{token_name}.json)
      - privacy_status: 'public'|'unlisted'|'private' (if publish_at_iso provided, use 'private')

    Returns:
      dict {"ok": True, "video_id": ..., "resp": <api response>} or {"ok": False, "error": ...}
    """
    # verify file
    fp = Path(filepath)
    if not fp.exists():
        return {"ok": False, "error": f"file_not_found: {filepath}"}

    creds = _load_creds(token_name)
    if not creds:
        return {"ok": False, "error": "no_credentials"}

    try:
        service = build("youtube", "v3", credentials=creds)
    except Exception as e:
        return {"ok": False, "error": f"service_build_failed: {str(e)}"}

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or []
        },
        "status": {
            "privacyStatus": privacy_status
        }
    }

    if publish_at_iso:
        # schedule publish
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = publish_at_iso

    media = MediaFileUpload(str(fp), chunksize=-1, resumable=True)
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    try:
        response = request.execute()
        video_id = response.get("id")
        # set thumbnail if given
        if thumbnail_path and Path(thumbnail_path).exists():
            try:
                thumb_req = service.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path)))
                thumb_req.execute()
            except Exception as e:
                # thumbnail failure shouldn't block main upload
                print("Thumbnail upload failed:", e)
        return {"ok": True, "video_id": video_id, "resp": response}
    except Exception as e:
        return {"ok": False, "error": str(e), "resp": response}
