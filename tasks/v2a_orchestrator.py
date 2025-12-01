# tasks/v2a_orchestrator.py
from celery import Celery
import os, time, uuid, json
from pathlib import Path

BROKER = os.getenv("CELERY_BROKER","redis://redis:6379/0")
app = Celery('v2a_orch', broker=BROKER, backend=BROKER)

@app.task(bind=True)
def orchestrate_voice2anim(self, package_json: str):
    """
    package_json contains:
      {
        "wav": "uploads/..wav",
        "transcript": "full text",
        "character": {"name":"Boy","profile":"energetic","rig":"BoyArm"},
        "mode":"hq"|"fast",
        "out_prefix":"static/..."
      }
    Steps:
      1) alignment (phoneme timing)
      2) if mode==hq: call speech2motion infer -> npz
         else: extract features + predict_fast -> frames
      3) apply personality_blender
      4) inertial_filter smoothing + clamp
      5) export bvh or npz for Blender retarget
    """
    pkg = json.load(open(package_json))
    out_pref = pkg.get("out_prefix") or f"static/voice2anim/{uuid.uuid4().hex[:6]}_"
    wav = pkg.get("wav")
    profile = pkg.get("character", {}).get("profile","neutral")
    mode = pkg.get("mode","fast")

    # 1) alignment (best-effort)
    from services.phoneme_aligner import run_montreal_forced_aligner
    align = run_montreal_forced_aligner(wav, pkg.get("transcript",""))
    # 2) prediction
    if mode=="hq":
        from services.speech2motion_wrapper import infer_speech2motion
        res = infer_speech2motion(wav, speaker_profile={"style":profile}, out_npz=str(Path(out_pref)+"motion.npz"))
        if not res.get("ok"):
            return {"ok":False,"error":"hq_failed","detail":res}
        # assume res['out'] is npz: hand off to blender retarget later
        result = {"ok":True,"type":"npz","path":res.get("out")}
    else:
        from services.voice2anim import extract_audio_features, predict_motion_fast, export_bvh_simple, run_voice2anim_pipeline
        feats = extract_audio_features(wav)
        pred = predict_motion_fast(feats, {"profile":profile})
        # apply personality
        from services.personality_blender import apply_personality_to_motion
        motion = apply_personality_to_motion(pred.get("motion",[]), personality=profile)
        # smoothing
        from services.inertial_filter import exponential_smooth, velocity_clamp
        motion = exponential_smooth(motion, alpha=0.3)
        motion = velocity_clamp(motion, max_deg_per_sec=420.0, fps=round(1000/40))
        # export bvh
        out_bvh = str(Path(out_pref) + "v2a.bvh")
        from services.voice2anim import export_bvh_simple
        exp = export_bvh_simple(motion, out_bvh)
        if not exp.get("ok"):
            return {"ok":False,"error":"export_failed","detail":exp}
        result = {"ok":True,"type":"bvh","path":out_bvh}
    # write meta
    meta = {"package": package_json, "result": result, "align": align}
    meta_path = str(Path(out_pref)+"meta.json")
    open(meta_path,"w").write(json.dumps(meta, indent=2))
    return {"ok":True,"meta":meta_path, "result": result}
