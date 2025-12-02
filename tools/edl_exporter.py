# tools/edl_exporter.py
import xml.etree.ElementTree as ET
from pathlib import Path
import json

def timeline_to_fcpxml(timeline, out_path, fps=24):
    # Minimal FCPXML structure — many editors accept simplified XML
    root = ET.Element("fcpxml", version="1.8")
    resources = ET.SubElement(root, "resources")
    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", name="Visora_Event")
    project = ET.SubElement(event, "project", name="Visora_Project")
    sequence = ET.SubElement(project, "sequence", duration=str(int(sum([t['frames'] for t in timeline]) * (1e9/fps))))
    media = ET.SubElement(sequence, "spine")
    current_tc = 0
    for t in timeline:
        clip = ET.SubElement(media, "asset-clip", name=t.get('shot', 'shot'), offset=str(int(current_tc)), duration=str(int(t['frames']*(1e9/fps))))
        current_tc += t['frames'] * (1e9/fps)
    tree = ET.ElementTree(root)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    return out_path
