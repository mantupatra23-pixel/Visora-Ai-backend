# tasks.py
from celery_app import celery
import traceback
import json
from pathlib import Path
import os

# import the heavy engine
try:
    from services.multichar_enhanced import MultiCharEnhancedEngine
    _HAS_MCE = True
except Exception:
    MultiCharEnhancedEngine = None
    _HAS_MCE = False

# initialize engine once per worker process (may be heavy)
ENGINE = MultiCharEnhancedEngine() if _HAS_MCE else None

@celery.task(bind=True, name="create_multichar_scene", acks_late=True, autoretry_for=(Exception,), retry_kwargs={'max_retries':3, 'countdown':10})
def create_multichar_scene(self, payload: dict):
    """
    payload example:
    {
      "script_text": "...",
      "prefer_upload": false,
      "user_images": {...},
      "make_lipsync": true,
      "bg_override": null,
      "out_name": "job_output.mp4"
    }
    """
    try:
        if not ENGINE:
            raise RuntimeError("MultiCharEnhancedEngine not available in worker.")
        # run heavy pipeline
        res = ENGINE.create_scene(
            script_text=payload.get("script_text"),
            prefer_upload=payload.get("prefer_upload", False),
            user_images=payload.get("user_images"),
            make_lipsync=payload.get("make_lipsync", True),
            bg_override=payload.get("bg_override"),
            out_name=payload.get("out_name")
        )
        # store result JSON file (helpful)
        out_dir = Path("static/queue_results")
        out_dir.mkdir(parents=True, exist_ok=True)
        task_id = self.request.id
        result_path = out_dir / f"{task_id}.json"
        with open(result_path, "w") as f:
            json.dump(res, f, indent=2)
        # if final video path present, optionally copy/move to canonical location (already done by engine)
        return {"ok": True, "result_file": str(result_path), "result": res}
    except Exception as e:
        traceback.print_exc()
        # raise to let Celery retry depending on decorator settings
        raise

@celery.task(bind=True, name="render_with_blender", acks_late=True, autoretry_for=(Exception,), retry_kwargs={'max_retries':2, 'countdown':30})
def render_with_blender(self, job_json: dict):
    """
    Example wrapper to run blender-based animation job through MultiCharAnimEngine or a direct subprocess.
    job_json contains fields needed by your blender pipeline.
    """
    try:
        # you can either call MultiCharAnimEngine wrapper or run subprocess to blender with jobfile
        from services.multichar_anim_engine import MultiCharAnimEngine
        engine = MultiCharAnimEngine()
        # engine.animate expects job dict
        out = engine.animate(job_json, prefer_blender=True, output_name=job_json.get("output_name"))
        return {"ok": True, "video": out}
    except Exception as e:
        traceback.print_exc()
        raise
