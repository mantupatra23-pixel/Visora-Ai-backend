# services/horror_audio.py
HEARTBEAT = {
  "low":"assets/sfx/heartbeat_low.wav",
  "medium":"assets/sfx/heartbeat_med.wav",
  "high":"assets/sfx/heartbeat_fast.wav"
}
JUMP_SFX = "assets/sfx/jump_sfx.wav"
AMBIENTS = {
  "low":"assets/sfx/ambient_low.wav",
  "medium":"assets/sfx/ambient_creak.wav",
  "high":"assets/sfx/ambient_howl.wav"
}

def pick_audio(level):
    return {"heartbeat": HEARTBEAT.get(level), "ambient": AMBIENTS.get(level), "jump": JUMP_SFX}
