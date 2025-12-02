# services/actor_personality.py
PERSONALITY = {
    "calm":{"gesture_speed":0.4,"expression_strength":0.5},
    "energetic":{"gesture_speed":1.2,"expression_strength":1.0},
    "serious":{"gesture_speed":0.6,"expression_strength":0.7},
    "funny":{"gesture_speed":1.4,"expression_strength":1.2},
}

def apply_personality(emotion_data, personality="calm"):
    p = PERSONALITY.get(personality, PERSONALITY["calm"])
    # scale expressions
    scaled_face = {k:v*p["expression_strength"] for k,v in emotion_data["face_pose"].items()}
    return {
        "emotion":emotion_data["emotion"],
        "face_pose":scaled_face,
        "gestures":emotion_data["gestures"],
        "personality":personality,
        "gesture_speed":p["gesture_speed"],
    }
