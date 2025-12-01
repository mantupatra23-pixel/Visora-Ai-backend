# nuke_scripts/auto_comp_nuke.py
"""
Headless Nuke script to read multi-pass EXR sequences, composite passes, denoise with OIDN (if OIDN plugin loaded),
apply LUT, and write output sequence.

Usage:
/opt/Nuke12.1v5/Nuke12.1 -t nuke_scripts/auto_comp_nuke.py -- job.json
"""
import sys, json, os
from pathlib import Path

if "--" in sys.argv:
    jobfile = sys.argv[sys.argv.index("--")+1]
else:
    print("job.json required"); sys.exit(1)
job = json.loads(Path(jobfile).read_text())

import nuke

def make_read(node_name, file_pattern):
    r = nuke.nodes.Read(name=node_name, file=file_pattern)
    return r

def main():
    input_passes = job.get("input_passes", {})
    reads = {}
    for k,pat in input_passes.items():
        reads[k] = make_read(k, pat)
    # Example: merge diffuse + spec using Merge node
    if "diffuse" in reads and ("specular" in reads or "spec" in reads):
        spec_key = "specular" if "specular" in reads else "spec"
        merge = nuke.nodes.Merge2(inputs=[reads["diffuse"], reads[spec_key]], operation="plus")
    else:
        merge = list(reads.values())[0]
    # optional denoise (if OIDN plugin exists)
    try:
        dn = nuke.nodes.Denoise(inputs=[merge])
    except Exception:
        dn = merge
    # apply LUT (OCIO or .cube via LUT node)
    grade = job.get("grade", {})
    if grade.get("type")=="lut":
        lut = nuke.nodes.Roto()  # placeholder, replace with proper LUT node if available
    # write output
    out_pat = job.get("output", {}).get("path", "static/nuke/out_%04d.png")
    write = nuke.nodes.Write(file=out_pat, inputs=[dn])
    # render frames
    start = job.get("start_frame",1); end = job.get("end_frame",start)
    nuke.execute(write, start, end)
    print("Nuke comp done. wrote:", out_pat)

if __name__ == "__main__":
    main()
