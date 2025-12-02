# services/actor_gesture.py
GESTURES = {
    "happy":["hand_wave","open_pose","head_tilt"],
    "sad":["slow_shoulder_drop","head_down"],
    "angry":["fist_tight","lean_forward","shake_head"],
    "fear":["step_back","tremble","protective_hands"],
    "surprise":["step_back","arms_up"],
    "neutral":["idle_stance"],
}

def get_gestures(emotion):
    return GESTURES.get(emotion, ["idle_stance"])
