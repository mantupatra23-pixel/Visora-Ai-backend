# services/romantic_motion.py
from math import sin, pi

def slow_motion_factor(level):
    if level=="light": return 1.0
    if level=="medium": return 0.7
    if level=="deep": return 0.5
    return 1.0

def eye_contact_prob(level):
    return {
        "light":0.2,
        "medium":0.6,
        "deep":0.9
    }.get(level,0.2)
