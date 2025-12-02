# services/lipsync_service.py
import re

PHONEMES = {
    "A":"aa",
    "E":"ee",
    "I":"ih",
    "O":"oh",
    "U":"uh",
    "M":"mm",
    "F":"ff",
}

def text_to_phonemes(text: str):
    seq = []
    for ch in text.upper():
        if ch in PHONEMES: seq.append(PHONEMES[ch])
    return seq
