# services/edl_exporter.py
"""
Exports:
- SRT subtitles using shot 'start_time'/'end_time' and text
- EDL (simple CMX3600-like) for editorial timeline imports
Functions:
- export_srt(shot_list, out_path)
- export_edl(shot_list, out_path)
"""

from pathlib import Path
import math

def _secs_to_srt(ts: float) -> str:
    h = int(ts // 3600); ts -= h*3600
    m = int(ts // 60); ts -= m*60
    s = int(ts)
    ms = int(round((ts - s)*1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def export_srt(shot_list: list, out_path: str):
    out = []
    idx = 1
    for s in shot_list:
        start = s.get("start_time", 0.0)
        end = s.get("end_time", start + s.get("duration_hint", 1.0))
        text = s.get("text", "")
        out.append(f"{idx}")
        out.append(f"{_secs_to_srt(start)} --> {_secs_to_srt(end)}")
        out.append(f"{text}")
        out.append("")  # blank
        idx += 1
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(out), encoding="utf-8")
    return {"ok": True, "path": out_path}

def export_edl(shot_list: list, out_path: str, reel="AX"):
    """
    Very simple EDL: CMX3600 style entries:
    001  AX V C 00:00:00:00 00:00:05:10 00:00:00:00 00:00:05:10
    We'll convert seconds to HH:MM:SS:FF (assuming 25 fps)
    """
    fps = 25
    def secs_to_tc(secs):
        frames = int(round(secs * fps))
        h = frames // (3600*fps); frames %= (3600*fps)
        m = frames // (60*fps); frames %= (60*fps)
        s = frames // fps; f = frames % fps
        return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"
    lines = []
    idx = 1
    for s in shot_list:
        start = s.get("start_time",0.0)
        end = s.get("end_time", start + s.get("duration_hint",1.0))
        in_tc = secs_to_tc(start)
        out_tc = secs_to_tc(end)
        lines.append(f"{idx:03d}  {reel} V C {in_tc} {out_tc} {in_tc} {out_tc}")
        lines.append("* FROM CLIP NAME: " + str(s.get("type")))
        lines.append("")
        idx += 1
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    return {"ok": True, "path": out_path}
