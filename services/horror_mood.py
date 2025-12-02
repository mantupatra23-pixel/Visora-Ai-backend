# services/horror_mood.py
def detect_tension_level(text: str):
    t = text.lower()
    # heuristics — extendable to ML later
    if any(w in t for w in ["murder","blood","kill","attack","scream","dead"]):
        return "high"
    if any(w in t for w in ["creepy","dark","door","shadow","follow"]):
        return "medium"
    return "low"

def emotion_tags(text: str):
    t = text.lower()
    tags = []
    if "scream" in t or "shout" in t: tags.append("scream")
    if "creak" in t or "door" in t: tags.append("creak")
    if "shadow" in t or "figure" in t: tags.append("silhouette")
    return tags
