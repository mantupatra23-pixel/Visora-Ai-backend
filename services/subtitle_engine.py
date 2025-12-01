# services/subtitle_engine.py
"""
Subtitle Engine
- generate_srt(lines, out_path): lines = [{"index":0,"text":"...","start":0.0,"end":3.2}, ...]
- generate_ass_karaoke(lines, out_path): produces simple ASS karaoke (word-level timing if provided)
- burn_in_subtitles(video_path, subtitle_path, out_path, font='DejaVuSans.ttf', fontsize=48, color='white')
- helper: seconds_to_srt_timestamp(seconds)
"""

from pathlib import Path
import srt
import datetime
import subprocess
import math
import json

OUT = Path("static/subtitles")
OUT.mkdir(parents=True, exist_ok=True)

def _secs_to_timedelta(s: float):
    return datetime.timedelta(seconds=float(s))

def generate_srt(lines: list, out_path: str | None = None):
    """
    lines: list of dicts with keys: index, text, start, end
    returns path to created srt file
    """
    subs = []
    for i, l in enumerate(lines):
        start = _secs_to_timedelta(l.get("start", 0.0))
        end = _secs_to_timedelta(l.get("end", l.get("start",0.0) + max(0.6, len(l.get("text","").split())*0.35)))
        sub = srt.Subtitle(index = i+1,
                           start = start,
                           end = end,
                           content = l.get("text",""))
        subs.append(sub)
    srt_str = srt.compose(subs)
    out_path = out_path or OUT / f"sub_{int(math.floor(1000000*math.random()))}.srt"
    # math.random used; fallback to timestamp-based filename
    try:
        out_path = Path(out_path)
        if out_path.exists() and out_path.is_dir():
            out_path = out_path / f"sub_{int(datetime.datetime.now().timestamp())}.srt"
    except Exception:
        pass
    # safe name
    out_path = out_path if isinstance(out_path, Path) else Path(out_path)
    out_path.write_text(srt_str, encoding="utf-8")
    return str(out_path)

def generate_srt_from_lines(lines: list, out_path: str | None = None):
    # convenience wrapper with predictable filename
    out_path = out_path or OUT / f"subs_{int(math.floor(datetime.datetime.now().timestamp()))}.srt"
    return generate_srt(lines, out_path=str(out_path))

def generate_ass_karaoke(lines: list, out_path: str | None = None, style_name: str = "VisoraKaraoke"):
    """
    Simple ASS generator — not full detailed karaoke but produces per-line ASS with basic style.
    For real word-level karaoke you need word timings. Here we place line-level ASS entries.
    """
    out_path = Path(out_path) if out_path else (OUT / f"subs_{int(datetime.datetime.now().timestamp())}.ass")
    header = "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
    header += "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    header += f"Style: {style_name},DejaVu Sans,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,40,1\n\n"
    header += "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    body = ""
    for l in lines:
        start = _tim(seconds=l.get("start",0.0))
        end = _tim(seconds=l.get("end", l.get("start",0.0)+1.0))
        text = l.get("text","").replace("\n", " ")
        body += f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}\n"
    out_path.write_text(header + body, encoding="utf-8")
    return str(out_path)

def _tim(seconds: float):
    # ASS time format H:MM:SS.cs (centiseconds)
    h = int(seconds // 3600); seconds -= h*3600
    m = int(seconds // 60); seconds -= m*60
    s = int(seconds)
    cs = int((seconds - s)*100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def burn_in_subtitles(video_path: str, subtitle_path: str, out_path: str | None = None, font: str = "DejaVuSans.ttf", fontsize: int = 48, color: str = "white"):
    """
    Uses ffmpeg drawtext to burn subtitles (for SRT use subtitles filter if ffmpeg compiled with libass)
    Simpler approach: convert SRT -> ASS via ffmpeg and then burn with -vf "subtitles=..."
    This function tries to use ffmpeg subtitles filter (libass).
    """
    out_path = out_path or (Path(video_path).with_name(Path(video_path).stem + "_subbed.mp4"))
    out_path = str(out_path)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"subtitles={subtitle_path}:force_style='FontName={font},Fontsize={fontsize},PrimaryColour=&H00FFFFFF,Outline=2,Shadow=0'",
        "-c:a", "copy",
        out_path
    ]
    # run
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {p.stderr[:300]}")
    return out_path
