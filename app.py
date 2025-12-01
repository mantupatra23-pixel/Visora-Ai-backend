# app.py

from fastapi import FastAPI
from dotenv import load_dotenv

# Import all routers
from routes.tts import router as tts_router
from routes.tts_proxy import router as tts_proxy_router
from routes.text import router as text_router
from routes.image import router as image_router
from routes.video import router as video_router     # <-- NEW
from routes.auto import router as auto_router
from routes.template import router as template_router
from routes.distribute import router as distribute_router
from routes.lipsync import router as lipsync_router
from routes.sadtalker import router as sadtalker_router
from routes.character3d import router as character3d_router
from routes.presets import router as presets_router
from routes.background import router as background_router
from routes.universe import router as universe_router
from routes.preview import router as preview_router
from fastapi.middleware.cors import CORSMiddleware
from routes.character_detect import router as character_detect_router
from routes.multichar import router as multichar_router
from routes.multichar_anim import router as multichar_anim_router
from routes.dialogue_split import router as dialogue_split_router
from routes.multichar_enhanced import router as multichar_enhanced_router
from routes.queue import router as queue_router
from routes.emotion import router as emotion_router
from routes.camera import router as camera_router
from routes.soundfx import router as soundfx_router
from routes.subtitle import router as subtitle_router
from routes.voiceclone import router as voiceclone_router
from routes.face_reenact import router as facere_router
from routes.dialogue_timing import router as dialog_timing_router
from routes.personality import router as personality_router
from routes.vfx import router as vfx_router
from routes.mocap import router as mocap_router
from routes.scene_planner import router as scene_planner_router
from routes.storyboard import router as storyboard_router
from routes.variants import router as variants_router
from routes.continuity import router as continuity_router
from routes.edl import router as edl_router
from routes.orchestrator import router as orchestrator_router
from routes.physics import router as physics_router

# Load environment variables from .env
load_dotenv()

app = FastAPI(
    title="Visora AI Engine",
    description="Visora - FastAPI core with TTS / Text / Image / Video",
    version="1.0.0",
)

# root healthcheck
@app.get("/")
def home():
    return {"status": "Visora Engine Running (FastAPI)"}

# Mount routers under their prefixes
app.include_router(text_router, prefix="/text")
app.include_router(tts_proxy_router, prefix="/proxy")
app.include_router(tts_router, prefix="/tts")
app.include_router(image_router, prefix="/image")
app.include_router(video_router, prefix="/video")   # <-- NEW
app.include_router(auto_router, prefix="/auto")
app.include_router(template_router, prefix="/template")
app.include_router(sound_router, prefix="/sound")
app.include_router(distribute_router, prefix="/distribute")
app.include_router(lipsync_router, prefix="/lipsync")
app.include_router(sadtalker_router, prefix="/sadtalker")
app.include_router(character3d_router, prefix="/character3d")
app.include_router(presets_router, prefix="/character3d/presets")
app.include_router(background_router, prefix="/character3d/background")
app.include_router(universe_router, prefix="/universe")
app.include_router(preview_router, prefix="/character3d/preview")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(character_detect_router, prefix="/characters")
app.include_router(multichar_router, prefix="/multichar")
app.include_router(multichar_anim_router, prefix="/anim")
app.include_router(dialogue_split_router, prefix="/dialogue")
app.include_router(multichar_enhanced_router, prefix="/multichar")
app.include_router(queue_router, prefix="/queue")
app.include_router(emotion_router, prefix="/emotion")
app.include_router(camera_router, prefix="/camera")
app.include_router(soundfx_router, prefix="/soundfx")
app.include_router(subtitle_router, prefix="/subtitle")
app.include_router(voiceclone_router, prefix="/voice")
app.include_router(facere_router, prefix="/face")
app.include_router(dialog_timing_router, prefix="/timing")
app.include_router(personality_router, prefix="/persona")
app.include_router(vfx_router, prefix="/vfx")
app.include_router(mocap_router, prefix="/mocap")
app.include_router(scene_planner_router, prefix="/planner")
app.include_router(storyboard_router, prefix="/storyboard")
app.include_router(variants_router, prefix="/variants")
app.include_router(continuity_router, prefix="/continuity")
app.include_router(edl_router, prefix="/edl")
app.include_router(orchestrator_router, prefix="/orchestrator")
app.include_router(physics_router, prefix="/physics")

# Optional: run with python app.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
