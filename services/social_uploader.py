# services/social_uploader.py
"""
Wrappers to upload to platforms.
- For real uploads: fill YOUTUBE_API_KEY, X_TOKEN, FB_APP_TOKEN etc in env and implement OAuth flows.
- For now provide: upload_to_platforms() that tries available wrappers, else returns prepared manifest (local-only)
"""
import os, time, json, subprocess, shlex
from pathlib import Path

def upload_to_platforms(video_path, caption, hashtags, thumbnail_path=None, schedule_at=None, platforms=None):
    platforms = platforms or ["local"]
    results = {}
    # merge caption + hashtags
    caption_full = caption + "\n\n" + " ".join(hashtags)
    for p in platforms:
        if p.lower() in ("youtube","yt"):
            # stub: return manifest or call real upload if YT creds available
            res = upload_youtube(video_path, caption_full, thumbnail_path, schedule_at)
            results['youtube'] = res
        elif p.lower() in ("x","twitter"):
            res = upload_x(video_path, caption_full, thumbnail_path, schedule_at)
            results['x'] = res
        elif p.lower() in ("instagram","ig","facebook"):
            res = upload_instagram(video_path, caption_full, thumbnail_path, schedule_at)
            results['instagram'] = res
        else:
            # local: just copy to static/published/
            dest = Path("static/published")
            dest.mkdir(parents=True, exist_ok=True)
            import shutil
            key = Path(video_path).name
            shutil.copy(video_path, dest / key)
            if thumbnail_path:
                shutil.copy(thumbnail_path, dest / (Path(thumbnail_path).name))
            results['local'] = {"ok": True, "path": str(dest / key)}
    return results

def upload_youtube(video_path, caption, thumbnail, schedule_at):
    # If env var available, implement real upload flow; otherwise return manifest
    if os.getenv("YOUTUBE_API_KEY"):
        # placeholder: you must implement OAuth2 and use googleapiclient
        return {"ok": False, "error": "not_implemented_server_side_upload_requires_oauth"}
    return {"ok": True, "manifest": {"platform":"youtube","video": video_path, "caption": caption, "thumbnail": thumbnail, "schedule_at": schedule_at}}

def upload_x(video_path, caption, thumbnail, schedule_at):
    if os.getenv("X_API_TOKEN"):
        return {"ok": False, "error": "not_implemented_x_upload_requires_api"}
    return {"ok": True, "manifest": {"platform":"x","video":video_path,"caption":caption,"thumbnail":thumbnail,"schedule_at":schedule_at}}

def upload_instagram(video_path, caption, thumbnail, schedule_at):
    if os.getenv("FB_GRAPH_TOKEN"):
        return {"ok": False, "error": "not_implemented_ig_requires_graph_api"}
    return {"ok": True, "manifest": {"platform":"instagram","video":video_path,"caption":caption,"thumbnail":thumbnail,"schedule_at":schedule_at}}
