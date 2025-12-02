# services/emotion_motion_mapper.py
from services.actor_expression import detect_emotion, build_face_pose
from services.actor_gesture import get_gestures

def map_script_to_motion(script_line: str):
    emotion = detect_emotion(script_line)
    face = build_face_pose(emotion)
    gestures = get_gestures(emotion)
    return {
        "emotion": emotion,
        "face_pose": face,
        "gestures": gestures
    }
