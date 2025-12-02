# services/subtitle_service.py
import json
from pathlib import Path

def segments_to_srt(segments, out_path):
    """
    segments: list of {"start": float, "end": float, "text": "..."}
    Writes SRT file.
    """
    def fmt_time(t):
        h = int(t//3600); m = int((t%3600)//60); s = int(t%60); ms = int((t - int(t))*1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    lines = []
    for i,s in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{fmt_time(s['start'])} --> {fmt_time(s['end'])}")
        lines.append(s['text'])
        lines.append("")
    Path(out_path).write_text("\n".join(lines, ))
    return str(out_path)
