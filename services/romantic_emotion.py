# services/romantic_emotion.py
import re

LEVELS = {
    "light": ["smile","look","seeing","soft","cute"],
    "medium": ["touch","hold","eye","close","near","heartbeat"],
    "deep": ["kiss","hug","embrace","cry","tears"]
}

def romantic_level(text):
    t = text.lower()
    for lv, words in LEVELS.items():
        if any(w in t for w in words):
            return lv
    return "light"
