# services/actor_expression.py
import json, re

EMOTION_MAP = {
    "happy": {"smile":0.8,"eyes_squint":0.4,"brows_up":0.2},
    "sad": {"mouth_frown":0.7,"brows_inner_up":0.5,"eyes_down":0.3},
    "angry": {"brows_down":0.8,"eyes_narrow":0.6,"jaw_clench":0.6},
    "fear": {"eyes_wide":0.8,"brows_up":0.6,"mouth_open":0.5},
    "surprise": {"eyes_wide":1.0,"brows_up":0.8,"mouth_open":0.9},
    "neutral": {"smile":0.0,"brows_up":0.0,"eyes_squint":0.0},
}

def detect_emotion(text: str):
    t = text.lower()
    if any(w in t for w in ["sad","cry","loss"]): return "sad"
    if any(w in t for w in ["angry","rage"]): return "angry"
    if any(w in t for w in ["fear","scared"]): return "fear"
    if any(w in t for w in ["wow","surprised"]): return "surprise"
    if any(w in t for w in ["happy","laugh","smile"]): return "happy"
    return "neutral"

def build_face_pose(emotion: str):
    return EMOTION_MAP.get(emotion, EMOTION_MAP["neutral"])
