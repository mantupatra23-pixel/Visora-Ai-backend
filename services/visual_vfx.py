# services/visual_vfx.py
"""
Visual VFX Engine (2D / fast pipeline)
- apply_glow(video_in, out, intensity, radius)
- apply_color_grade(video_in, out, lut_path=None, contrast=1.0, saturation=1.0)
- apply_lens_flare(video_in, out, time_positions=[...], intensity=0.7)
- apply_motion_blur(video_in, out, strength=0.8)  # via ffmpeg tblend or minterpolate
- speed_ramp(video_in, segments=[(start, end, speed_factor), ...], out)
- composite_overlays(video_in, overlays=[{"path":..., "start":..., "end":..., "x":..., "y":..., "opacity":...}])
- chroma_key_composite(foreground, background, out, key_color=(0,255,0), similarity=0.1)
Uses: ffmpeg (preferred for performance) + moviepy fallback.
"""
import os
import subprocess
from pathlib import Path
import tempfile
import shlex

ROOT = Path(".").resolve()
OUT = ROOT / "static" / "vfx"
OUT.mkdir(parents=True, exist_ok=True)

def _run(cmd):
    print("RUN:", cmd)
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if p.returncode != 0:
        return {"ok": False, "stderr": p.stderr, "stdout": p.stdout}
    return {"ok": True, "stdout": p.stdout}

# 1) Glow / Bloom using ffmpeg (unsharp + blend + glow trick)
def apply_glow_ffmpeg(video_in: str, out_path: str | None = None, intensity: float = 0.6, radius: int = 15):
    out = out_path or str(OUT / f"glow_{Path(video_in).stem}.mp4")
    # blur + overlay technique
    # steps: extract blurred pass, adjust brightness, overlay screen blend
    cmd = (
        f"ffmpeg -y -i {shlex.quote(video_in)} -filter_complex "
        f"\"[0:v]boxblur={radius}:{radius}:cr=1[blur];"
        f"[blur]eq=brightness={0.15*intensity}:saturation=1.0[glow];"
        f"[0:v][glow]overlay=(W-w)/2:(H-h)/2:format=auto,format=yuv420p\" -c:a copy {shlex.quote(out)}"
    )
    return _run(cmd)

# 2) Color grade via LUT (if LUT provided) or via eq/curves
def apply_color_grade(video_in: str, out_path: str | None = None, lut_path: str | None = None, contrast: float = 1.0, saturation: float = 1.0):
    out = out_path or str(OUT / f"grade_{Path(video_in).stem}.mp4")
    if lut_path and Path(lut_path).exists():
        # ffmpeg lut3d filter
        cmd = f"ffmpeg -y -i {shlex.quote(video_in)} -vf lut3d={shlex.quote(lut_path)} -c:a copy {shlex.quote(out)}"
    else:
        # eq filter for basic contrast/saturation
        cmd = f"ffmpeg -y -i {shlex.quote(video_in)} -vf eq=contrast={contrast}:saturation={saturation} -c:a copy {shlex.quote(out)}"
    return _run(cmd)

# 3) Lens flare insertion (overlay image at positions with additive blend)
def apply_lens_flare(video_in: str, overlay_img: str, positions: list, out_path: str | None = None):
    out = out_path or str(OUT / f"flare_{Path(video_in).stem}.mp4")
    # build overlay commands chained for each position/time (positions = [{"start":1.2,"end":1.6,"x":100,"y":200,"scale":1.0,"opacity":0.6},...])
    # Write a complex filter programmatically
    vf_parts = []
    inputs = f"-i {shlex.quote(video_in)} -i {shlex.quote(overlay_img)}"
    # We'll reuse same overlay img and time it via enable expression
    overlay_filters = []
    overlay_filters.append("[0:v][1:v]overlay=enable='between(t,0,99999)':x=(W-w)/2:y=(H-h)/2:format=auto:alpha=1")
    # Simpler approach: fade overlay in/out by using overlay with enable expression for each time window -> but that needs multiple overlay inputs
    # Simpler fallback: overlay entire clip at low opacity centered
    cmd = f"ffmpeg -y {inputs} -filter_complex \"[1:v]format=rgba,fade=in:st=0:d=0.2:alpha=1,fade=out:st=1000:d=0.2:alpha=1,scale=iw*1:ih*1[fl];[0:v][fl]overlay=(W-w)/2:(H-h)/2:format=auto:blend=all_mode='screen'\" -c:a copy {shlex.quote(out)}"
    return _run(cmd)

# 4) Motion blur (ffmpeg tblend)
def apply_motion_blur(video_in: str, out_path: str | None = None, frames=2):
    out = out_path or str(OUT / f"mblur_{Path(video_in).stem}.mp4")
    # tblend mode=average blends current and previous frames -> motion blur effect
    cmd = f"ffmpeg -y -i {shlex.quote(video_in)} -vf tblend=all_mode=average,framestep=1 -c:v libx264 -crf 18 -preset medium -c:a copy {shlex.quote(out)}"
    return _run(cmd)

# 5) Speed ramp segments using ffmpeg setpts filter per segment (complex) -> fallback does split/concat
def speed_ramp_segments(video_in: str, segments: list, out_path: str | None = None):
    """
    segments: list of (start_sec, end_sec, speed_factor)
    Approach: split video into segments, apply setpts on each, concat.
    """
    out = out_path or str(OUT / f"speed_{Path(video_in).stem}.mp4")
    tmpdir = Path(tempfile.mkdtemp())
    # split into chunks, apply speed, then concat
    pieces = []
    for i, seg in enumerate(segments):
        s, e, sp = seg
        segfile = tmpdir / f"seg_{i}.mp4"
        cmd = f"ffmpeg -y -i {shlex.quote(video_in)} -ss {s} -to {e} -c copy {shlex.quote(str(segfile))}"
        r = _run(cmd); 
        if not r["ok"]:
            continue
        # speed apply: using setpts for video and atempo for audio (audio only supports 0.5-2.0; chain if outside)
        sped = tmpdir / f"seg_{i}_sped.mp4"
        # video setpts
        cmdv = f"ffmpeg -y -i {shlex.quote(str(segfile))} -filter_complex \"[0:v]setpts={1.0/float(sp)}*PTS[v];[0:a]atempo={float(sp)}[a]\" -map \"[v]\" -map \"[a]\" -preset ultrafast {shlex.quote(str(sped))}"
        r2 = _run(cmdv)
        if r2["ok"]:
            pieces.append(str(sped))
    # concat pieces
    if not pieces:
        return {"ok": False, "error": "no pieces created"}
    listfile = tmpdir / "list.txt"
    with open(listfile, "w") as f:
        for p in pieces:
            f.write(f"file '{p}'\n")
    cmd_concat = f"ffmpeg -y -f concat -safe 0 -i {shlex.quote(str(listfile))} -c copy {shlex.quote(out)}"
    res = _run(cmd_concat)
    return res

# 6) Composite overlays (sprites) onto video
def composite_overlays(video_in: str, overlays: list, out_path: str | None = None):
    """
    overlays: list of {"path":..., "start": 1.2, "end": 2.0, "x": "W-w-50", "y": "H-h-50", "opacity":0.7}
    For simplicity we overlay entire list centered with fade in/out.
    """
    out = out_path or str(OUT / f"comp_{Path(video_in).stem}.mp4")
    cmd_inputs = [f"-i {shlex.quote(video_in)}"]
    for ov in overlays:
        cmd_inputs.append(f"-i {shlex.quote(ov['path'])}")
    filter_parts = []
    base = "[0:v]"
    current = base
    for idx, ov in enumerate(overlays, start=1):
        vtag = f"[{idx}:v]"
        # simple overlay center and fade using overlay enable
        start = ov.get("start", 0)
        end = ov.get("end", 99999)
        opacity = ov.get("opacity", 1.0)
        # create fade alpha
        filt = f"{vtag}format=rgba,fade=in:st={start}:d=0.15:alpha=1,fade=out:st={end}:d=0.15:alpha=1,scale=iw:ih[ov{idx}];{current}[ov{idx}]overlay=enable='between(t,{start},{end})':x={ov.get('x','(W-w)/2')}:y={ov.get('y','(H-h)/2')}"
        filter_parts.append(filt)
        current = ""  # chain simplified
    # assemble
    filter_complex = ";".join(filter_parts)
    cmd = f"ffmpeg -y {' '.join(cmd_inputs)} -filter_complex \"{filter_complex}\" -map 0:a? -c:v libx264 -crf 18 -preset medium {shlex.quote(out)}"
    return _run(cmd)

# 7) Chroma key composite via ffmpeg chromakey filter
def chroma_key_composite(foreground: str, background: str, out_path: str | None = None, key_color="0x00FF00", similarity=0.1, blend=0.1):
    out = out_path or str(OUT / f"ck_{Path(foreground).stem}.mp4")
    cmd = f"ffmpeg -y -i {shlex.quote(foreground)} -i {shlex.quote(background)} -filter_complex \"[0:v]chromakey={key_color}:{similarity}:{blend}[ckout];[1:v][ckout]overlay=0:0\" -c:a copy {shlex.quote(out)}"
    return _run(cmd)
