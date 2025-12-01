# services/dialogue_timing.py
"""
Dialogue Timing & Beat Engine
- analyze_script(script_text) -> returns beats, per-line suggested pauses and timing estimates
- emit_ssml_lines(lines) -> returns list of SSML strings per line (with <break time="Xms"/> etc.)
- estimate_timing_from_words(text, wpm=150) -> seconds estimate
- make_timeline(dialogue_lines, initial_offset=0.0, min_pause=0.15) -> assign start/end for each line
"""

import re
import math
from typing import List, Dict, Any

# small helpers
def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r'(?<=[\.\?\!])\s+', text) if s.strip()]

def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))

def estimate_timing_from_words(text: str, wpm: int = 150) -> float:
    """
    Rough estimate of speaking duration in seconds given words-per-minute.
    default wpm 150 -> 2.5 words/sec => 0.4 sec/word approx -> we use 60/wpm
    """
    if not text or not text.strip():
        return 0.2
    words = _word_count(text)
    sec_per_word = 60.0 / float(max(1, wpm))
    est = words * sec_per_word
    # clamp
    return max(0.25, min(est, max(0.25, est)))

# Beat detection heuristics
PAUSE_KEYWORDS_LONG = ["...", "—", "—", "—", "silence", "pause", "drumroll"]
PAUSE_KEYWORDS_MEDIUM = [",", ";", "but", "and then", "so", "then", "but then"]
EMPHASIS_KEYWORDS = ["very", "really", "never", "always", "stop", "listen", "attention", "watch out"]

class DialogueTiming:
    def __init__(self, wpm: int = 150):
        self.wpm = wpm

    def analyze_script(self, script_text: str) -> Dict[str, Any]:
        """
        Returns:
        {
          "lines": [ {"index":0, "text":"...", "est_dur": 2.3, "suggest_pause_after": 0.4, "type":"dialogue|beat|action|reaction", "emphasis": 0..1 }, ... ],
          "timeline_hint": total_est_duration,
          "notes": "..."
        }
        """
        sentences = _split_sentences(script_text)
        out_lines = []
        total = 0.0
        for i, s in enumerate(sentences):
            est = estimate_timing_from_words(s, wpm=self.wpm)
            # base pause
            pause = 0.18  # default short pause in seconds
            s_low = s.lower()
            # punctuation heuristics
            if any(sym in s for sym in PAUSE_KEYWORDS_LONG):
                pause = 0.6
            elif any(p in s for p in PAUSE_KEYWORDS_MEDIUM):
                pause = 0.35
            # emotional emphasis heuristic (increase pause after strong emotive sentences)
            emphasis = 0.0
            for kw in EMPHASIS_KEYWORDS:
                if kw in s_low:
                    emphasis += 0.25
            # sentence length based adjustment
            words = _word_count(s)
            if words <= 3:
                # short lines get slightly longer pause for punch
                pause = max(pause, 0.3)
            # detect action/onomatopoeia -> shorter/longer depending
            typ = "dialogue"
            if re.search(r'\b(roar|bang|boom|explosion|scream|laugh)\b', s_low):
                typ = "action"
                pause = max(pause, 0.25)
            # compute start/end (cumulative)
            start = total
            end = round(start + est, 3)
            out_lines.append({
                "index": i,
                "text": s,
                "est_dur": round(est, 3),
                "suggest_pause_after": round(pause + emphasis, 3),
                "type": typ,
                "emphasis_score": round(min(1.0, emphasis), 3),
                "words": words,
                "start_hint": round(start, 3),
                "end_hint": round(end, 3)
            })
            total = end + pause + emphasis
        return {"lines": out_lines, "total_estimated_duration": round(total, 3), "notes": f"{len(out_lines)} lines analyzed"}

    def make_timeline(self, lines: List[Dict[str,Any]], initial_offset: float = 0.0, min_pause: float = 0.12) -> List[Dict[str,Any]]:
        """
        Given lines (with est_dur and suggest_pause_after) assign start/end times (absolute)
        Returns updated list with start,end fields.
        """
        t = initial_offset
        out = []
        for l in lines:
            dur = l.get("est_dur", estimate_timing_from_words(l.get("text",""), wpm=self.wpm))
            start = round(t, 3)
            end = round(t + dur, 3)
            pause = max(min_pause, float(l.get("suggest_pause_after", 0.18)))
            # attach
            nl = dict(l)
            nl["start"] = start
            nl["end"] = end
            nl["pause_after"] = round(pause, 3)
            out.append(nl)
            t = end + pause
        return out

    def emit_ssml_lines(self, lines: List[Dict[str,Any]], include_wrapper: bool = False) -> List[Dict[str,str]]:
        """
        Returns list of dicts: {"index":i, "ssml":"<speak>..</speak>", "plain": "..."}
        SSML uses <break time="Xms"/> after each line. Also inserts emphasis tags if emphasis_score > threshold.
        """
        out = []
        for l in lines:
            text = l.get("text","")
            pause_ms = int(round((l.get("pause_after", 0.18)) * 1000))
            # emphasis heuristics
            emph = float(l.get("emphasis_score", 0.0))
            if emph >= 0.5:
                ss = f"<emphasis level='strong'>{text}</emphasis>"
            elif emph >= 0.25:
                ss = f"<emphasis level='moderate'>{text}</emphasis>"
            else:
                ss = text
            ssml = f"{ss}<break time='{pause_ms}ms'/>"
            if include_wrapper:
                ssml = f"<speak>{ssml}</speak>"
            out.append({"index": l.get("index"), "ssml": ssml, "plain": text})
        return out

    def adjust_for_emotion(self, lines: List[Dict[str,Any]], emotion_map: Dict[int,str]):
        """
        Optional: receives mapping line_index -> emotion (e.g., from EmotionEngine)
        and adjusts pause/emphasis/durations accordingly in-place.
        Example emotion_map: {0:"fear", 2:"joy"}
        """
        for l in lines:
            idx = l.get("index")
            emo = emotion_map.get(idx)
            if not emo:
                continue
            if emo == "fear":
                # faster, higher pitch -> reduce duration slightly, shorten pause
                l["est_dur"] = round(max(0.25, l["est_dur"] * 0.9),3)
                l["suggest_pause_after"] = round(max(0.12, l.get("suggest_pause_after",0.18) * 0.8),3)
                l["emphasis_score"] = max(l.get("emphasis_score",0.0), 0.2)
            if emo == "sadness":
                l["est_dur"] = round(l["est_dur"] * 1.05,3)
                l["suggest_pause_after"] = round(l.get("suggest_pause_after",0.18) * 1.3,3)
                l["emphasis_score"] = max(l.get("emphasis_score",0.0), 0.1)
            if emo == "joy":
                l["est_dur"] = round(l["est_dur"] * 0.98,3)
                l["suggest_pause_after"] = round(l.get("suggest_pause_after",0.18) * 1.0,3)
                l["emphasis_score"] = max(l.get("emphasis_score",0.0), 0.25)
        return lines
