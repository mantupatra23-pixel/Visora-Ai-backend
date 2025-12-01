# services/promo_generator.py
"""
Auto Promo Generator
- Inputs: master_video (path) OR list of clips + script (text)
- Options: promo_length (sec), style ("trailer"/"short"/"teaser"), captions (auto), ratio (9:16/1:1/16:9)
- Outputs: promo_video (mp4), thumbnail (png), caption_text (string), hashtags (list)
- Relies on ffmpeg + existing engines (voice2anim, lip_emotion) if needed.
"""
import os, uuid, json, shlex, subprocess
from pathlib import Path

ROOT = Path(".").resolve()
OUT = ROOT / "static" / "promo"
OUT.mkdir(parents=True, exist_ok=True)

def _tid():
    return uuid.uuid4().hex[:8]

def _run(cmd, timeout=300):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return {"ok": p.returncode==0, "stdout": p.stdout, "stderr": p.stderr, "rc": p.returncode}

def pick_best_clips(master_video: str, length: int = 15, ratio: str = "9:16"):
    """
    Simple strategy: sample uniformly multiple short cutouts and stack them.
    For now: take N segments of equal length and concat (fast).
    """
    out_prefix = OUT / f"promo_{_tid()}"
    out_prefix.mkdir(parents=True, exist_ok=True)
    # get duration
    cmd_dur = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(master_video)}"
    p = subprocess.run(cmd_dur, shell=True, capture_output=True, text=True)
    try:
        dur = float(p.stdout.strip())
    except:
        dur = length * 3
    # decide clip segments — take 3 segments of length/3 each spaced across video
    seg_count = 3
    seg_len = max(1.0, length / seg_count)
    starts = [max(0, (dur - seg_len) * (i/(seg_count-1))) if seg_count>1 else 0 for i in range(seg_count)]
    parts = []
    for i, s in enumerate(starts):
        out_clip = out_prefix / f"clip_{i}.mp4"
        cmd = f"ffmpeg -y -ss {s:.3f} -i {shlex.quote(master_video)} -t {seg_len:.3f} -c:v libx264 -crf 20 -preset veryfast -c:a aac -ac 1 -ar 22050 {shlex.quote(str(out_clip))}"
        r = _run(cmd)
        if not r['ok']:
            return {"ok": False, "error": "clip_failed", "detail": r}
        parts.append(str(out_clip))
    # concat clips
    concat_list = out_prefix / "concat.txt"
    concat_list.write_text("\n".join([f"file '{p}'" for p in parts]))
    out_final = str(out_prefix / f"promo_{_tid()}.mp4")
    cmd_cat = f"ffmpeg -y -f concat -safe 0 -i {shlex.quote(str(concat_list))} -c copy {shlex.quote(out_final)}"
    r = _run(cmd_cat)
    if not r['ok']:
        # fallback re-encode
        cmd_cat2 = f"ffmpeg -y -f concat -safe 0 -i {shlex.quote(str(concat_list))} -c:v libx264 -crf 20 -preset fast -c:a aac {shlex.quote(out_final)}"
        r = _run(cmd_cat2)
        if not r['ok']:
            return {"ok": False, "error": "concat_failed", "detail": r}
    return {"ok": True, "promo_video": out_final}

def auto_caption_and_hashtags(script_text: str | None = None, title: str | None = None):
    """
    Lightweight caption & hashtag suggester:
    - If script provided: pick short sentence, generate hashtags from keywords.
    - Fallback: use title keywords.
    """
    text = script_text or title or "Watch this now"
    # simple shorten to 120 chars
    caption = (text.strip()[:117] + "...") if len(text)>120 else text.strip()
    # generate hashtags: pick words >4 letters, top 5 unique
    words = [w.strip(".,!?()[]{}\"'").lower() for w in text.split()]
    kw = []
    for w in words:
        if len(w)>4 and w.isalpha() and w not in kw:
            kw.append(w)
        if len(kw)>=5: break
    hashtags = ["#" + k for k in kw] if kw else ["#AI","#Shorts"]
    return {"ok": True, "caption": caption, "hashtags": hashtags}

def make_thumbnail_from_video(video_path: str, out_path: str | None = None, time_sec: float = 1.0, overlay_text: str | None = None):
    out_path = out_path or str(OUT / f"thumb_{_tid()}.png")
    # extract frame
    cmd = f"ffmpeg -y -ss {time_sec} -i {shlex.quote(video_path)} -frames:v 1 -q:v 2 {shlex.quote(out_path)}"
    r = _run(cmd)
    if not r['ok']:
        return {"ok": False, "error": "thumbnail_frame_failed", "detail": r}
    # optional overlay text using ffmpeg drawtext (if requested)
    if overlay_text:
        tmp = out_path + ".tmp.png"
        draw = f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{overlay_text}':fontcolor=white:fontsize=48:box=1:boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y=h-120"
        cmd2 = f"ffmpeg -y -i {shlex.quote(out_path)} -vf \"{draw}\" -frames:v 1 {shlex.quote(tmp)}"
        r2 = _run(cmd2)
        if r2['ok']:
            os.replace(tmp, out_path)
    return {"ok": True, "thumbnail": out_path}
