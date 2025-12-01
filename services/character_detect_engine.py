# services/character_detect_engine.py
import re

class CharacterDetectEngine:

    # Master mapping of script keywords → type & preset
    MAP = [
        # Old people
        (r"\bold man\b|\belderly man\b|\bgrandpa\b", ("old_male", "old_man_preset")),
        (r"\bold woman\b|\bgrandma\b|\belderly woman\b", ("old_female", "old_lady_preset")),

        # Adult male / female
        (r"\bman\b|\bhusband\b|\bmale\b", ("adult_male", "human_cartoon_male")),
        (r"\bwoman\b|\bwife\b|\bfemale\b|\blady\b", ("adult_female", "human_cartoon_female")),

        # Young
        (r"\byoung man\b|\bboy\b|\bteen boy\b|\bteenage boy\b", ("young_male", "anime_boy")),
        (r"\byoung woman\b|\bgirl\b|\bteen girl\b|\bteenage girl\b", ("young_female", "anime_girl")),

        # Children
        (r"\bchild\b|\bbaby\b|\btoddler\b|\bkid\b", ("child", "child_cartoon")),

        # Animals
        (r"\btiger\b", ("tiger", "tiger_3d")),
        (r"\bmonkey\b|\bbandar\b", ("monkey", "monkey_3d")),
        (r"\bdog\b", ("dog", "dog_3d")),
        (r"\bcat\b", ("cat", "cat_3d")),

        # Non-human entities
        (r"\brobot\b|\bandroid\b|\bcyborg\b", ("robot", "robot_3d")),
        (r"\bghost\b|\bspirit\b|\bsoul\b", ("ghost", "ghost_3d")),
        (r"\balien\b|\bet\b", ("alien", "alien_3d")),

        # Hero / Warrior
        (r"\bwarrior\b|\bhero\b|\bsoldier\b", ("hero", "hero_3d")),
    ]

    def detect_characters(self, script: str):
        script_lower = script.lower()
        found = []

        for pattern, (ctype, preset) in self.MAP:
            matches = re.findall(pattern, script_lower)
            if matches:
                count = len(matches)
                for i in range(count):
                    found.append({
                        "type": ctype,
                        "preset": preset,
                        "raw": matches[i]
                    })

        # If no character found → default narrator
        if not found:
            found.append({
                "type": "narrator",
                "preset": "human_cartoon_male",
                "raw": "narrator"
            })

        return found
