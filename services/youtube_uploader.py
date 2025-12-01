# services/youtube_uploader.py
import os
import json
import pathlib
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import google.auth.exceptions
import pickle

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]

TOKEN_PATH = pathlib.Path("tokens")
TOKEN_PATH.mkdir(parents=True, exist_ok=True)
CREDENTIALS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS", "client_secrets.json")
PICKLE_PATH = TOKEN_PATH / "youtube_token.pickle"

def get_authenticated_service():
    creds = None
    if PICKLE_PATH.exists():
        with open(PICKLE_PATH, "rb") as f:
            creds = pickle.load(f)
    # If no valid creds, start flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_console()  # shows URL & paste code (desktop flow)
        # save token
        with open(PICKLE_PATH, "wb") as f:
            pickle.dump(creds, f)
    service = build("youtube", "v3", credentials=creds)
    return service

def upload_video(file_path: str, title: str, description: str = "", tags: list | None = None, privacy_status: str = "unlisted", categoryId: str = "22", thumbnail_path: str | None = None, chunk_size: int = 256*1024):
    """
    Uploads video to YouTube and returns dict with videoId and status.
    privacy_status: "public" | "unlisted" | "private"
    categoryId default 22 (People & Blogs) — change as needed.
    """
    if not pathlib.Path(file_path).exists():
        raise FileNotFoundError("Video file not found: " + file_path)

    service = get_authenticated_service()
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": categoryId
        },
        "status": {
            "privacyStatus": privacy_status
        }
    }

    media = MediaFileUpload(file_path, chunksize=chunk_size, resumable=True)

    request = service.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    error = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                # percent done
                percent = int(status.progress() * 100)
                print(f"Upload progress: {percent}%")
        except google.auth.exceptions.RefreshError as re:
            raise RuntimeError("Authentication Error: " + str(re))
        except Exception as e:
            error = e
            print("Error during upload chunk:", e)
            raise

    video_id = response.get("id")
    # optional: set thumbnail
    if thumbnail_path and pathlib.Path(thumbnail_path).exists():
        try:
            service.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_path)).execute()
        except Exception as e:
            print("Thumbnail upload failed:", e)

    return {"ok": True, "videoId": video_id, "response": response}
