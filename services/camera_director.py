# services/camera_director.py
"""
Camera Director Engine
- analyze_scene(script_text, characters, mood_hint) -> returns camera choreography JSON
- key ideas:
   * Break script into beats/sentences
   * Assign camera intent per beat (establishing, closeup, reaction, action)
   * Create camera cuts list: [{start, end, type, params}]
   * Create camera shot list for blender/job composer or fallback 2D composer
"""

import re
import math
import random
from typing import List, Dict

# simple sentence splitter (keeps punctuation end)
def _split_sentences(text: str):
    items = [s.strip() for s in re.split(r'(?<=[\.\?\!])\s+', text) if s.strip()]
    return items if items else [text]

# small heuristics
ACTION_KEYWORDS = ["run", "jump", "fight", "attack", "chase", "explode", "punch", "kick", "fall", "shoot", "battle", "jumped", "jumping"]
EMOTION_ACTION = ["shout", "scream", "yell", "cry", "laugh", "sob", "whisper", "whispers"]
ESTABLISHING_KEYWORDS = ["arrive", "enter", "arrives", "entering", "walks in", "arrived"]
REACTION_KEYWORDS = ["looks", "stares", "sees", "notices", "watches", "gazes"]

# camera choreography presets (generic)
CAM_PRESETS = {
    "establishing": {"type":"wide", "radius":8.0, "height":3.0, "revs":0.05},
    "closeup": {"type":"closeup", "radius":2.0, "height":1.6},
    "medium": {"type":"medium", "radius":4.0, "height":1.8},
    "over_shoulder": {"type":"oss", "radius":3.0, "height":1.6},
    "action": {"type":"action", "shake":True, "radius":5.0, "height":1.2},
    "dramatic_push": {"type":"push", "speed":1.2, "radius":3.0, "height":1.6},
    "reaction": {"type":"reaction", "radius":2.5, "height":1.6},
    "wide_pan": {"type":"wide_pan", "radius":9.0, "height":3.5, "revs":0.02}
}

class CameraDirector:
    def __init__(self, base_fps: int = 24):
        self.fps = base_fps

    def _detect_intent(self, sentence: str):
        s = sentence.lower()
        # priority: action > establishing > reaction > emotional
        for kw in ACTION_KEYWORDS:
            if kw in s:
                return "action"
        for kw in ESTABLISHING_KEYWORDS:
            if kw in s:
                return "establishing"
        for kw in REACTION_KEYWORDS:
            if kw in s:
                return "reaction"
        for kw in EMOTION_ACTION:
            if kw in s:
                return "dramatic"
        return "dialogue"

    def _duration_estimate(self, sentence: str, min_sec=1.0, max_sec=6.0):
        words = len(sentence.split())
        # avg speaking speed ~ 150 wpm -> 0.4 sec per word? Use conservative 0.4
        est = max(min_sec, min(max_sec, words * 0.35))
        return round(est, 2)

    def generate_choreography(self, script_text: str, characters: List[Dict] | None = None, mood: str | None = None, start_time: float = 0.0):
        """
        Returns:
        {
          "duration": total_seconds,
          "fps": 24,
          "camera_cuts": [ {start:float, end:float, type:str, params:dict, focus_on: optional character index or name } ... ],
          "notes": "..."
        }
        """
        sentences = _split_sentences(script_text)
        t = start_time
        cuts = []
        # assign characters order if provided (for focus mapping)
        char_names = []
        if characters:
            for ch in characters:
                # ch may be dict with 'name' or 'preset' keys
                name = ch.get("name") or ch.get("preset") or ch.get("type") or None
                char_names.append(name)
        # iterate sentences and create cuts
        for idx, sent in enumerate(sentences):
            intent = self._detect_intent(sent)
            dur = self._duration_estimate(sent)
            cut = {"index": idx, "start": round(t,3), "end": round(t+dur,3), "type": intent, "text": sent, "params": {}}
            # focus heuristic: if character name appears in sentence, focus there
            focus = None
            if char_names:
                low = sent.lower()
                for i,name in enumerate(char_names):
                    if not name: continue
                    if name.lower() in low:
                        focus = {"char_index": i, "char_name": name}
                        break
            # map intent -> preset params
            if intent == "action":
                cut["params"] = CAM_PRESETS["action"].copy()
                # actions get shorter fast cuts and possible multiple microcuts
                # microcuts: split into two quick cuts for intensity
                if dur > 2.2:
                    mid = t + dur*0.5
                    cut["end"] = round(mid,3)
                    cuts.append(cut)
                    cut2 = {"index": f"{idx}_2", "start": round(mid,3), "end": round(t+dur,3), "type":"action", "text": sent, "params": CAM_PRESETS["action"].copy()}
                    if focus: 
                        cut["focus"] = focus
                        cut2["focus"] = focus
                    cuts.append(cut2)
                    t += dur
                    continue
            elif intent == "establishing":
                cut["params"] = CAM_PRESETS["establishing"].copy()
            elif intent == "reaction":
                cut["params"] = CAM_PRESETS["reaction"].copy()
            elif intent == "dramatic":
                cut["params"] = CAM_PRESETS["dramatic_push"].copy()
            else:  # dialogue or default
                # choose closeup if short single-line emotional, else medium
                if len(sent.split()) <= 6:
                    cut["params"] = CAM_PRESETS["closeup"].copy()
                else:
                    cut["params"] = CAM_PRESETS["medium"].copy()

            if focus:
                cut["focus"] = focus
            else:
                # randomize some camera variety
                if random.random() < 0.15:
                    cut["params"] = CAM_PRESETS["wide_pan"].copy()
            cuts.append(cut)
            t += dur
        total_dur = round(t - start_time, 3)
        return {"duration": total_dur, "fps": self.fps, "camera_cuts": cuts, "notes": f"generated {len(cuts)} cuts from {len(sentences)} sentences"}
