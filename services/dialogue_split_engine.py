# services/dialogue_split_engine.py
import re

class DialogueSplitter:
    """
    Extracts dialogue lines + speaker from script.

    Supports 3 types:
    1) NAME: "Dialogue..."
    2) NAME - Dialogue
    3) Dialogue (speaker guessed from nearest keyword)
    """

    # Map keywords to character types
    # You can expand keywords anytime.
    CHAR_HINTS = {
        "man": "adult_male",
        "old man": "old_male",
        "boy": "young_male",
        "girl": "young_female",
        "lady": "adult_female",
        "woman": "adult_female",
        "child": "child",
        "baby": "child",
        "tiger": "tiger",
        "monkey": "monkey",
        "hero": "hero",
        "narrator": "narrator"
    }

    SPEAKER_PATTERNS = [
        r'^([A-Za-z ]+):\s*(.+)$',
        r'^([A-Za-z ]+)\s*-\s*(.+)$'
    ]

    def _guess_speaker(self, text: str):
        """
        अगर script में direct speaker name न हो → closest keyword से बोलने वाले का अनुमान.
        """
        t = text.lower()
        for k, v in self.CHAR_HINTS.items():
            if k in t:
                return v
        return "narrator"

    def split_dialogue(self, script: str):
        """
        Returns list:
        [
          {"speaker":"adult_male","text":"Hello there."},
          {"speaker":"young_female","text":"Hi Sir!"}
        ]
        """
        lines = [
            l.strip()
            for l in script.split("\n")
            if l.strip()
        ]

        out = []
        for line in lines:
            matched = False
            for pat in self.SPEAKER_PATTERNS:
                m = re.match(pat, line)
                if m:
                    spk_raw = m.group(1).strip().lower()
                    txt = m.group(2).strip()

                    # convert raw speaker to model preset using hints
                    spk = self._guess_speaker(spk_raw)

                    out.append({
                        "speaker_raw": spk_raw,
                        "speaker": spk,
                        "text": txt
                    })
                    matched = True
                    break

            if matched:
                continue

            # If no NAME: format → treat as narrator OR nearest character
            spk_guess = self._guess_speaker(line)
            out.append({
                "speaker_raw": None,
                "speaker": spk_guess,
                "text": line
            })

        return out
