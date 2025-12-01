# services/personality_engine.py
import json
from pathlib import Path
from typing import Dict, Any, Optional

ROOT = Path(".").resolve()
PERSONA_DIR = ROOT / "data" / "personas"
PERSONA_DIR.mkdir(parents=True, exist_ok=True)

# Default persona presets (tune values as per your TTS/client)
DEFAULT_PERSONAS = {
    "brave": {
        "label":"brave",
        "tts": {"voice":"male_deep","rate":1.0,"pitch":1.0,"style":"confident"},
        "emotion_bias": {"joy":0.2, "fear":-0.2, "anger":0.1},
        "gesture_intensity": 0.9,
        "camera_pref": {"shot":"hero_closeup", "distance":2.0},
        "animation_presets": ["strong_pose","chest_out","stomp"],
        "vocab_style": {"add_prefix":"","replace":{}}
    },
    "shy": {
        "label":"shy",
        "tts": {"voice":"female_soft","rate":0.9,"pitch":0.95,"style":"soft"},
        "emotion_bias": {"joy":0.0, "fear":0.2, "sadness":0.2},
        "gesture_intensity": 0.25,
        "camera_pref": {"shot":"medium","distance":4.0},
        "animation_presets": ["small_moves","look_away","hands_together"],
        "vocab_style": {"add_prefix":"","replace":{}}
    },
    "wise_old": {
        "label":"wise_old",
        "tts": {"voice":"old_male","rate":0.85,"pitch":0.85,"style":"wise"},
        "emotion_bias": {"sadness":0.05, "joy":0.05},
        "gesture_intensity": 0.35,
        "camera_pref": {"shot":"medium_closeup","distance":3.0},
        "animation_presets": ["slow_gesture","index_point","nod"],
        "vocab_style": {"add_prefix":"(slow) ","replace":{}}
    },
    "villain": {
        "label":"villain",
        "tts": {"voice":"male_gruff","rate":0.95,"pitch":0.9,"style":"menacing"},
        "emotion_bias": {"anger":0.3, "joy":-0.1},
        "gesture_intensity": 0.8,
        "camera_pref": {"shot":"low_angle_closeup","distance":1.8},
        "animation_presets": ["smirk","slow_hand_raise","lean_forward"],
        "vocab_style": {"add_prefix":"","replace":{"you":"you fool"}}
    },
    "comic": {
        "label":"comic",
        "tts": {"voice":"male_bright","rate":1.1,"pitch":1.05,"style":"playful"},
        "emotion_bias": {"joy":0.5},
        "gesture_intensity": 0.75,
        "camera_pref": {"shot":"wide","distance":6.0},
        "animation_presets": ["exaggerated_moves","jumpy","fast_hands"],
        "vocab_style": {"add_prefix":"","replace":{}}
    }
}

def _persona_path(name: str) -> Path:
    return PERSONA_DIR / f"{name}.json"

class PersonalityEngine:
    def __init__(self):
        # ensure default personas saved
        for k,v in DEFAULT_PERSONAS.items():
            p = _persona_path(k)
            if not p.exists():
                p.write_text(json.dumps(v, indent=2), encoding="utf-8")

    def list_personas(self):
        outs = []
        for f in PERSONA_DIR.glob("*.json"):
            try:
                outs.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue
        return outs

    def get_persona(self, name: str) -> Optional[Dict[str,Any]]:
        p = _persona_path(name)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_persona(self, persona: Dict[str,Any]) -> bool:
        name = persona.get("label") or persona.get("name")
        if not name:
            raise ValueError("persona must include 'label' or 'name'")
        p = _persona_path(name)
        p.write_text(json.dumps(persona, indent=2), encoding="utf-8")
        return True

    def apply_persona_to_character(self, character: Dict[str,Any], persona_name: str) -> Dict[str,Any]:
        """
        Returns a new character dict with persona applied:
         - merges tts params into character['tts'] (or create)
         - sets animation presets, gesture_intensity, camera preference, emotion bias
         - applies simple vocab style replacements (non-destructive)
        """
        persona = self.get_persona(persona_name)
        if not persona:
            raise ValueError("persona not found: " + persona_name)
        out = dict(character)  # shallow copy
        # merge tts
        out_tts = out.get("tts", {})
        out_tts.update(persona.get("tts", {}))
        out["tts"] = out_tts
        # set animation presets and gesture intensity
        out["gesture_intensity"] = persona.get("gesture_intensity", out.get("gesture_intensity", 0.5))
        out["animation_presets"] = persona.get("animation_presets", out.get("animation_presets", []))
        out["camera_pref"] = persona.get("camera_pref", out.get("camera_pref", {}))
        out["emotion_bias"] = persona.get("emotion_bias", out.get("emotion_bias", {}))
        out["persona_label"] = persona_name
        out["vocab_style"] = persona.get("vocab_style", out.get("vocab_style", {}))
        # apply simple replacement to character's display_name if configured
        if "display_name" in out and persona.get("vocab_style", {}).get("replace"):
            for a,b in persona["vocab_style"]["replace"].items():
                out["display_name"] = out["display_name"].replace(a, b)
        return out
