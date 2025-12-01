# services/action_scene_engine.py
"""
Action Scene Engine
- detect_action_beats(script_text) -> list of beats with type, severity, hints
- plan_action_sequence(beats, characters, duration_hint) -> action plan JSON
- prepare_blender_job(plan) -> job dict consumable by multichar_anim_engine.animate()
- prepare_fallback_job(plan) -> job dict for animate_fallback_2d

Heuristics-first: keyword-based detection + severity estimation.
"""

import re, math, random
from typing import List, Dict

ACTION_KEYWORDS = {
    "jump": ["jump","leap","vault"],
    "chase": ["chase","run after","pursue","running away","runs away","chased"],
    "explosion": ["explode","explosion","blast","bomb","detonate"],
    "fight": ["fight","punch","kick","hit","slap","combat"],
    "impact": ["impact","collide","collision","crash"],
    "fall": ["fall","fell","fell down","slipped","tripped"],
    "dodge": ["dodge","evade","avoid"],
    "shoot": ["shoot","gun","fire","shot"],
    "jump_attack": ["pounce","leap and attack","jumped on"],
    "slam": ["slams","slammed","smash"]
}

# mapping to animation templates (names are suggestions; you must have matching actions in your rig pipeline)
ANIM_TEMPLATES = {
    "jump": {"template":"jump_anim", "dur":0.8, "energy":0.7},
    "chase": {"template":"run_cycle", "dur":2.5, "energy":0.8},
    "explosion": {"template":"explosion_vfx", "dur":1.8, "energy":1.0},
    "fight": {"template":"fight_combo", "dur":2.2, "energy":0.9},
    "impact": {"template":"hit_react", "dur":0.7, "energy":0.85},
    "fall": {"template":"fall_react", "dur":1.2, "energy":0.8},
    "dodge": {"template":"dodge_anim", "dur":0.6, "energy":0.6},
    "shoot": {"template":"shoot_anim", "dur":0.5, "energy":0.75},
    "slam": {"template":"slam_anim", "dur":1.0, "energy":0.95}
}

def _split_sentences(text: str):
    return [s.strip() for s in re.split(r'(?<=[\.\?\!])\s+', text) if s.strip()]

class ActionSceneEngine:
    def __init__(self):
        pass

    def detect_action_beats(self, script_text: str) -> List[Dict]:
        """
        Returns list of beats:
        [{"index":0,"sentence":"...","type":"jump","severity":0.8,"keywords":["jump","climb"], "approx_pos": frac }]
        """
        text = script_text.lower()
        sentences = _split_sentences(script_text)
        beats = []
        for i,s in enumerate(sentences):
            low = s.lower()
            for act, kws in ACTION_KEYWORDS.items():
                for kw in kws:
                    if kw in low:
                        # severity heuristic: presence of strong verbs -> higher severity
                        severity = 0.6 + min(0.4, low.count(kw)/2.0)
                        beats.append({
                            "index": i,
                            "sentence": s,
                            "type": act,
                            "severity": round(severity,2),
                            "keywords": [kw],
                            "approx_frac": round(text.find(kw)/max(1,len(text)),3)
                        })
                        break
        return beats

    def plan_action_sequence(self, script_text: str, characters: List[Dict] | None = None, mood: str | None = None, start_time: float = 0.0):
        """
        Convert beats -> action plan containing:
          - per-beat: start,end (est), actors involved, anim_template, vfx list, camera_hint, smash_params
        """
        beats = self.detect_action_beats(script_text)
        plan = {"beats": [], "notes": "", "duration_est": 0.0}
        t = start_time
        # estimate durations from sentence length + template base
        for b in beats:
            typ = b["type"]
            template = ANIM_TEMPLATES.get(typ, {"template":"generic_action","dur":1.0,"energy":0.7})
            base = template["dur"]
            # extend base by severity and sentence word-length
            words = len(b["sentence"].split())
            dur = round(max(0.5, base + (words * 0.12) * (b["severity"])), 2)
            actors = []
            # guess actors by presence of character names or types in sentence
            if characters:
                low = b["sentence"].lower()
                for ch in characters:
                    name = (ch.get("name") or ch.get("preset") or ch.get("type") or "").lower()
                    if name and name in low:
                        actors.append(name)
            if not actors and characters:
                # fallback assign first character as primary
                actors = [characters[0].get("name") or characters[0].get("preset")]
            # vfx suggestions
            vfx = []
            if typ in ("explosion", "impact", "slam"):
                vfx.append("debris")
                vfx.append("dust")
            if typ == "explosion":
                vfx.append("fire")
                vfx.append("smoke")
            if typ in ("chase","run","dodge"):
                vfx.append("motion_blur")
            # camera hint
            cam_hint = {"style":"action", "intensity": b["severity"], "shake": True if b["severity"]>0.7 else False}
            beat_entry = {
                "index": b["index"],
                "type": typ,
                "sentence": b["sentence"],
                "start": round(t,3),
                "end": round(t+dur,3),
                "duration": dur,
                "actors": actors,
                "anim_template": template["template"],
                "vfx": vfx,
                "camera": cam_hint
            }
            plan["beats"].append(beat_entry)
            t += dur
        plan["duration_est"] = round(t - start_time,3)
        plan["notes"] = f"{len(plan['beats'])} action beats detected"
        return plan

    def prepare_blender_job(self, plan: Dict, characters: List[Dict], background: str | None = None, audio: str | None = None, out_name: str | None = None):
        """
        Build job dict consumable by multichar_anim_engine / blender script:
        - characters: include model_path & entry timings
        - camera_cuts derived from plan beats
        - vfx: particle/emitter instructions
        """
        job = {
            "duration": plan.get("duration_est", 6.0),
            "fps": 24,
            "background": background,
            "audio": audio,
            "characters": [],
            "camera_cuts": [],
            "vfx": [],
            "beats": plan.get("beats", []),
            "output_name": out_name
        }
        # include characters (expect user to pass model_path in characters list)
        for i,ch in enumerate(characters or []):
            c = {
                "name": ch.get("name") or ch.get("preset") or f"char_{i}",
                "model_path": ch.get("model_path"),
                "rigged": ch.get("rigged", True),
                "entry_start": ch.get("entry_start", 0.0),
                "entry_duration": ch.get("entry_duration", 1.0),
                "x": ch.get("x", i*2.0 - 2.0),
                "y": ch.get("y", 0.0),
                "z": ch.get("z", 0.0),
                "scale": ch.get("scale", 1.0),
            }
            job["characters"].append(c)
        # camera cuts -> from beats
        for b in plan.get("beats", []):
            cc = {
                "start": b["start"],
                "end": b["end"],
                "type": "action_shot" if b["camera"].get("shake") else "dynamic",
                "params": {"intensity": b["camera"].get("intensity", 0.8), "shake": b["camera"].get("shake", False)}
            }
            job["camera_cuts"].append(cc)
            # vfx instructions
            if b.get("vfx"):
                job["vfx"].append({"time": b["start"], "vfx_types": b["vfx"], "location_hint": b.get("actors")})
        return job

    def prepare_fallback_job(self, plan: Dict, characters: List[Dict], background: str | None = None, audio: str | None = None, out_name: str | None = None):
        """
        Prepare job for animate_fallback_2d: characters as images + per-beat transforms (zoom, pan, shake)
        """
        job = {"duration": plan.get("duration_est", 6.0), "fps":24, "background": background, "characters": [], "beats": plan.get("beats", []), "output_name": out_name}
        for i,ch in enumerate(characters or []):
            job["characters"].append({
                "image": ch.get("image"),
                "start": 0,
                "end": plan.get("duration_est", 6.0),
                "x": ch.get("x", "center"),
                "y": ch.get("y", "center"),
                "scale": ch.get("scale", 1.0)
            })
        return job
