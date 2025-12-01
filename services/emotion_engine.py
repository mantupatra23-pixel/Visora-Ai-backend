# services/emotion_engine.py
"""
Emotion AI Speech Engine
- detect_emotions(text): returns list of probable emotions with scores
- best_emotion(text): returns top emotion (string)
- map_emotion_to_tts(emotion): returns a dict of tts params (voice, rate, pitch, style, speed_factor)

Design:
- Primary: rule-based heuristics for fast on-device detection (works offline & deterministic)
- Optional: if transformers pipeline 'j-hartmann/emotion-english-distilroberta-base' (or other) available,
  engine will use it for better accuracy. This requires 'transformers' and torch installed.
"""

import re
from collections import Counter

# Optional HF model usage
_HAS_HF = False
try:
    from transformers import pipeline
    _HAS_HF = True
except Exception:
    _HAS_HF = False

# Simple vocabulary -> emotion hints (extendable)
EMO_HINTS = {
    "anger": ["angry","furious","rage","hate","kill","fight","shout","scream","mad","roar"],
    "fear": ["scared","afraid","fear","terrified","panic","run","hide","danger","threat"],
    "joy": ["happy","joy","laugh","smile","excited","yay","cheer","celebrate","pleased"],
    "sadness": ["sad","cry","tears","sorrow","lonely","regret","mourn","upset","tragic"],
    "surprise": ["surprise","surprised","wow","oh!","suddenly","unexpected"],
    "disgust": ["disgust","gross","nasty","eww","vomit","dislike"],
    "neutral": ["said","said calmly","announced","narrator","described","informed"]
}

# default tts mapping per emotion (tune values to your TTS client)
DEFAULT_TTS_MAP = {
    "anger":    {"voice":"male_deep", "rate":0.95, "pitch":0.9, "style":"angry",   "speed":1.05},
    "fear":     {"voice":"male_tense","rate":0.9,  "pitch":1.05,"style":"scared",  "speed":1.1},
    "joy":      {"voice":"female_bright","rate":1.05,"pitch":1.1,"style":"cheerful","speed":1.0},
    "sadness":  {"voice":"female_soft","rate":0.85,"pitch":0.85,"style":"sad","speed":0.9},
    "surprise": {"voice":"female_bright","rate":1.0,"pitch":1.2,"style":"surprised","speed":1.15},
    "disgust":  {"voice":"male_gruff","rate":0.95,"pitch":0.9,"style":"disgust","speed":0.95},
    "neutral":  {"voice":"male_default","rate":1.0,"pitch":1.0,"style":"neutral","speed":1.0}
}

class EmotionEngine:
    def __init__(self, use_hf_model: bool = False):
        self.use_hf = use_hf_model and _HAS_HF
        self.hf_classifier = None
        if self.use_hf:
            # recommended model name can be changed if you have better one
            try:
                self.hf_classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", return_all_scores=True)
            except Exception as e:
                # if load failed, fallback to non-hf
                print("HF model load failed:", e)
                self.hf_classifier = None
                self.use_hf = False

    def _rule_based_scores(self, text: str):
        txt = text.lower()
        counts = Counter()
        for emo, keywords in EMO_HINTS.items():
            for kw in keywords:
                # word boundary match to reduce false positives
                if re.search(r"\b" + re.escape(kw) + r"\b", txt):
                    counts[emo] += 1
        # Normalize to scores 0..1
        if counts:
            total = sum(counts.values())
            scores = {k: round(v/total, 3) for k,v in counts.items()}
        else:
            scores = {"neutral": 1.0}
        return scores

    def detect_emotions(self, text: str, top_k: int = 3):
        """
        Returns list of (emotion, score) sorted by score desc.
        If HF model available & enabled -> use it (more accurate).
        Else -> use rule-based.
        """
        if not text or not text.strip():
            return [("neutral", 1.0)]
        if self.use_hf and self.hf_classifier:
            try:
                preds = self.hf_classifier(text[:512])  # model expects reasonable length
                # preds is list of dicts with label & score; return top_k
                # some pipelines return list of lists (return_all_scores=True)
                if isinstance(preds, list) and len(preds)>0 and isinstance(preds[0], list):
                    scores = {p['label'].lower(): p['score'] for p in preds[0]}
                elif isinstance(preds, list) and isinstance(preds[0], dict):
                    scores = {p['label'].lower(): p['score'] for p in preds}
                else:
                    scores = {"neutral": 1.0}
                sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
                return [(k, round(float(v),3)) for k,v in sorted_items]
            except Exception as e:
                # fallback to rule-based
                print("HF classify failed:", e)
                rb = self._rule_based_scores(text)
                return sorted([(k,v) for k,v in rb.items()], key=lambda x:x[1], reverse=True)[:top_k]
        else:
            rb = self._rule_based_scores(text)
            return sorted([(k,v) for k,v in rb.items()], key=lambda x:x[1], reverse=True)[:top_k]

    def best_emotion(self, text: str):
        arr = self.detect_emotions(text, top_k=1)
        return arr[0][0] if arr else "neutral"

    def map_emotion_to_tts(self, emotion: str):
        # return tts params dict — if unknown emotion fallback to neutral
        emo = emotion if emotion in DEFAULT_TTS_MAP else "neutral"
        params = DEFAULT_TTS_MAP.get(emo, DEFAULT_TTS_MAP["neutral"])
        return params

    # convenience: full pipeline
    def analyze_and_map(self, text: str):
        detected = self.detect_emotions(text, top_k=3)
        best = detected[0][0] if detected else "neutral"
        tts_params = self.map_emotion_to_tts(best)
        return {"detected": detected, "best": best, "tts": tts_params}
