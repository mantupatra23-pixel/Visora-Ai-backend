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

# Optional: run with python app.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
