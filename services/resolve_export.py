# services/resolve_export.py
"""
Create Resolve-compatible XML/EDL for timeline import.
Simple XML generator for an Edit with clips (frame-based).
"""
import xml.etree.ElementTree as ET
from pathlib import Path
import json

def seconds_to_tc(s, fps=25):
    frames = int(round(s*fps))
    h = frames // (3600*fps); frames %= (3600*fps)
    m = frames // (60*fps); frames %= (60*fps)
    sec = frames // fps; fr = frames % fps
    return f"{h:02d}:{m:02d}:{sec:02d}:{fr:02d}"

def make_resolve_xml(clips, out_xml, fps=25):
    """
    clips: list of dicts: {id, file, start_time, duration}
    Produces a very small Resolve XML for a single video track.
    """
    xroot = ET.Element("xmeml", version="4")
    seq = ET.SubElement(xroot, "sequence")
    ET.SubElement(seq, "name").text = "AutoSequence"
    media = ET.SubElement(seq, "media")
    video = ET.SubElement(media, "video")
    track = ET.SubElement(video, "track")
    for i, c in enumerate(clips):
        clipitem = ET.SubElement(track, "clipitem", id=f"clipitem-{i+1}")
        ET.SubElement(clipitem, "name").text = Path(c['file']).name
        ET.SubElement(clipitem, "start").text = str(int(round(c.get("start_time",0)*fps)))
        ET.SubElement(clipitem, "end").text = str(int(round((c.get("start_time",0)+c.get("duration",1))*fps)))
        ET.SubElement(clipitem, "in").text = "0"
        ET.SubElement(clipitem, "out").text = str(int(round(c.get("duration",1)*fps)))
        file_el = ET.SubElement(clipitem, "file", id=f"file-{i+1}")
        ET.SubElement(file_el, "name").text = Path(c['file']).name
        ET.SubElement(file_el, "pathurl").text = f"file://{Path(c['file']).absolute()}"
    tree = ET.ElementTree(xroot)
    tree.write(out_xml, encoding="utf-8", xml_declaration=True)
    return {"ok": True, "path": out_xml}
