# services/sync_edit.py
from pathlib import Path
import json

def build_cut_list_from_beats(job):
    # job: choreography job object produced earlier
    cuts = []
    for t in job.get("timeline", []):
        frame = int(t["time"] * 24) + 1
        # create small clip around beat e.g., +/- 4 frames
        cuts.append({"dancer": t["dancer"], "clip": t["clip"], "frame": frame, "duration_frames": t.get("frames",8)})
    return cuts

def export_fcpxml_from_cuts(cuts, out_path, fps=24):
    from tools.edl_exporter import timeline_to_fcpxml
    timeline = [{"shot": c["clip"], "frames": c["duration_frames"]} for c in cuts]
    return timeline_to_fcpxml(timeline, out_path, fps)
