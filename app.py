from flask import Flask
from routes.text import text_bp
from routes.tts import tts_bp
from routes.image import image_bp
from routes.video import video_bp
from routes.auto import auto_bp

app = Flask(__name__)

app.register_blueprint(text_bp, url_prefix="/text")
app.register_blueprint(tts_bp, url_prefix="/tts")
app.register_blueprint(image_bp, url_prefix="/image")
app.register_blueprint(video_bp, url_prefix="/video")
app.register_blueprint(auto_bp, url_prefix="/auto")

@app.get("/")
def home():
    return {"status": "Visora Engine Running"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
