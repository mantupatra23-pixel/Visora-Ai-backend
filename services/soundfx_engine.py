# services/soundfx_engine.py
"""
Sound FX & Ambient Engine
- detect_events(script_text) -> list of events with rough timestamps (relative)
- select_sfx_for_event(event_key) -> path to sfx file (from assets/sfx)
- mix_audio(dialogue_tracks, events, ambience, music) -> final audio path

Dependencies: pydub (and ffmpeg installed on system)
pip install pydub
ffmpeg must be available in PATH
"""

import os
import re
import random
import math
from pathlib import Path
from typing import List, Dict, Any

try:
    from pydub import AudioSegment, effects
except Exception as e:
    raise RuntimeError("pydub required. pip install pydub and ensure ffmpeg present.") from e

# Directory layout expectations
SFX_DIR = Path("assets/sfx")           # put fx files here (e.g., tiger_roar.mp3, footstep1.wav)
AMBIENCE_DIR = Path("assets/ambience") # ambient loops (rain.mp3, wind.mp3, crowd.mp3)
MUSIC_DIR = Path("assets/music")       # background music tracks

OUT_DIR = Path("static/audio")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# keywords -> event mapping (extendable)
EVENT_HINTS = {
    "tiger_roar": ["tiger", "roar", "growl"],
    "footsteps": ["walk", "walks", "walking", "walked", "footstep", "steps", "ran", "running", "run"],
    "door": ["door", "open", "closed", "knock", "knocked", "enter", "opened"],
    "wind": ["wind", "breeze", "gust"],
    "rain": ["rain", "storm", "stormy", "raining", "drizzle"],
    "crowd": ["crowd", "people", "cheer", "applause", "audience"],
    "impact": ["hit", "punch", "kick", "slam", "impact", "collision", "crash"],
    "scream": ["scream", "shout", "yell", "cry"],
    "engine": ["car", "engine", "vehicle", "truck"],
    # add more as needed
}

# For each event key, prefer certain sfx file name patterns — fallback picks random file in sfx dir
PREFERRED_PATTERNS = {
    "tiger_roar": ["tiger", "roar"],
    "footsteps": ["footstep", "step"],
    "door": ["door", "knock"],
    "wind": ["wind", "gust"],
    "rain": ["rain", "storm"],
    "crowd": ["crowd", "cheer", "applause"],
    "impact": ["impact", "hit", "punch"],
    "scream": ["scream", "shout"],
    "engine": ["car", "engine"]
}

def _find_best_file_for(patterns: List[str], dirpath: Path):
    if not dirpath.exists():
        return None
    files = list(dirpath.glob("*"))
    best = None
    for f in files:
        lname = f.name.lower()
        for p in patterns:
            if p in lname:
                return str(f)
    # fallback random
    return str(random.choice(files)) if files else None

class SoundFXEngine:
    def __init__(self, sfx_dir: str | None = None, ambience_dir: str | None = None, music_dir: str | None = None):
        self.sfx_dir = Path(sfx_dir) if sfx_dir else SFX_DIR
        self.ambience_dir = Path(ambience_dir) if ambience_dir else AMBIENCE_DIR
        self.music_dir = Path(music_dir) if music_dir else MUSIC_DIR

    def detect_events(self, script_text: str) -> List[Dict[str,Any]]:
        """
        Very simple event detection via keywords.
        Returns list: [{"event":"tiger_roar","score":0.8,"snippet":"...","approx_time": seconds}]
        approx_time is relative sequence position (0..N) — actual timing will be matched to dialogue timeline externally.
        """
        text = script_text.lower()
        events = []
        words = re.split(r'\s+', text)
        total_words = max(1, len(words))
        # naive: scan for keywords and set approx_time based on index of first occurrence
        for ev, kws in EVENT_HINTS.items():
            for kw in kws:
                if kw in text:
                    idx = text.find(kw)
                    # approximate time as fraction of length * estimated total duration (caller may remap)
                    frac = idx / max(1, len(text))
                    events.append({"event": ev, "keyword": kw, "pos": idx, "frac": frac})
                    break
        # sort by pos
        events = sorted(events, key=lambda x: x["pos"])
        return events

    def select_sfx_for_event(self, event_key: str) -> str | None:
        # pick best candidate from SFX_DIR based on patterns
        patterns = PREFERRED_PATTERNS.get(event_key, [event_key])
        f = _find_best_file_for(patterns, self.sfx_dir)
        return f

    def select_ambience(self, mood: str | None = None) -> str | None:
        # choose ambience by mood if possible
        if mood:
            mood_l = mood.lower()
            # simple mapping
            if "rain" in mood_l or "storm" in mood_l: 
                return _find_best_file_for(["rain","storm"], self.ambience_dir)
            if "city" in mood_l or "crowd" in mood_l: 
                return _find_best_file_for(["city","crowd","street"], self.ambience_dir)
            if "wind" in mood_l:
                return _find_best_file_for(["wind","gust"], self.ambience_dir)
        # fallback random ambience
        return _find_best_file_for([], self.ambience_dir)

    def select_music(self, intensity: str | None = None) -> str | None:
        # intensity: calm / tense / epic / playful
        if intensity:
            if "tense" in intensity: return _find_best_file_for(["tense","dramatic","suspense"], self.music_dir)
            if "epic" in intensity: return _find_best_file_for(["epic","hero"], self.music_dir)
            if "calm" in intensity: return _find_best_file_for(["calm","ambient","soft"], self.music_dir)
            if "play" in intensity: return _find_best_file_for(["playful","fun"], self.music_dir)
        return _find_best_file_for([], self.music_dir)

    def _ensure_audiosegment(self, path: str) -> AudioSegment | None:
        if not path:
            return None
        if not Path(path).exists():
            return None
        return AudioSegment.from_file(path)

    def mix_tracks(self, dialogue_tracks: List[Dict], script_text: str, mood: str | None = None, music_intensity: str | None = None, ducking_db: float = -10.0) -> Dict[str,Any]:
        """
        dialogue_tracks: list of {"path": "/path/to/line.mp3", "start": seconds, "end": seconds, "speaker": "young_male"}
        Steps:
          1) load each dialogue track and place at start time onto master (silence background)
          2) detect events from script_text and overlay SFX at approximated times
          3) add ambience loop (low vol)
          4) add music (looped) and apply ducking during dialogue (reduce music volume by ducking_db)
          5) export final audio path
        Returns: {"ok": True, "final_audio": path, "details": {...}}
        """
        # estimate total duration from dialogues
        total_dur = 0.0
        for lt in dialogue_tracks:
            total_dur = max(total_dur, lt.get("end", lt.get("start",0) + 0.0))
        total_dur = max(total_dur, 1.0)

        # make silent base
        master = AudioSegment.silent(duration = int(total_dur * 1000) + 2000)  # ms

        details = {"dialogue":[], "sfx":[], "ambience": None, "music": None}
        # 1) place dialogue tracks
        for lt in dialogue_tracks:
            ap = lt.get("audio") or lt.get("path") or lt.get("audio_path")
            if not ap or not Path(ap).exists():
                continue
            seg = self._ensure_audiosegment(ap)
            if not seg:
                continue
            start_ms = int(lt.get("start",0) * 1000)
            master = master.overlay(seg, position=start_ms)
            details["dialogue"].append({"path":ap, "start":lt.get("start"), "dur":len(seg)/1000.0})

        # 2) detect events and overlay SFX
        events = self.detect_events(script_text)
        for ev in events:
            sfx = self.select_sfx_for_event(ev["event"])
            if not sfx:
                continue
            # place sfx at approx time; map frac -> time within total_dur
            approx_time = ev.get("frac", 0.0) * total_dur
            # jitter small positive to avoid overlap at zero
            approx_time = max(0.1, approx_time)
            seg = self._ensure_audiosegment(sfx)
            if not seg:
                continue
            # apply light random pitch/volume variance for realism
            vol_change = random.uniform(-2.0, 1.0)
            seg = seg + vol_change
            master = master.overlay(seg, position=int(approx_time * 1000))
            details["sfx"].append({"event":ev["event"], "file":sfx, "time": approx_time})
        # 3) ambience
        amb_file = self.select_ambience(mood)
        if amb_file:
            amb_seg = self._ensure_audiosegment(amb_file)
            if amb_seg:
                # loop ambience to cover total_dur
                needed = int(total_dur * 1000) + 2000
                looped = amb_seg * math.ceil(needed / len(amb_seg))
                # lower the ambience volume
                looped = looped - 12
                master = master.overlay(looped, position=0)
                details["ambience"] = {"file": str(amb_file)}
        # 4) music
        music_file = self.select_music(music_intensity)
        if music_file:
            mseg = self._ensure_audiosegment(music_file)
            if mseg:
                needed = int(total_dur * 1000) + 2000
                looped = mseg * math.ceil(needed / len(mseg))
                # normalize and lower music initial volume
                looped = effects.normalize(looped) - 6
                # apply ducking: for each dialogue segment, lower music by ducking_db for that window
                for lt in dialogue_tracks:
                    start_ms = int(lt.get("start",0) * 1000)
                    end_ms = int(lt.get("end", lt.get("start",0) + len(self._ensure_audiosegment(lt.get("audio")))/1000.0) * 1000) if lt.get("audio") and Path(lt.get("audio")).exists() else start_ms + int( (lt.get("dur",1.0) or 1.0) * 1000 )
                    # slice parts and reduce volume
                    pre = looped[:start_ms] if start_ms>0 else AudioSegment.silent(duration=0)
                    mid = looped[start_ms:end_ms] - abs(ducking_db)
                    post = looped[end_ms:] if end_ms < len(looped) else AudioSegment.silent(duration=0)
                    looped = pre + mid + post
                # overlay music under master (music should be quieter)
                master = master.overlay(looped - 6, position=0)
                details["music"] = {"file": str(music_file)}
        # final normalization
        final = effects.normalize(master)
        out_name = OUT_DIR / f"final_mix_{int(random.random()*100000)}.mp3"
        final.export(str(out_name), format="mp3", bitrate="192k")
        return {"ok": True, "final_audio": str(out_name), "details": details}
