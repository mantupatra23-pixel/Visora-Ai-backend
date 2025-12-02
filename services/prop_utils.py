# services/prop_utils.py
from mathutils import Matrix, Vector
import math
# NOTE: mathutils available only inside Blender. For offline meta logic we use plain python.
def choose_prop_for_line(text: str):
    txt = text.lower()
    # priority keyword match; extendable
    if "talwar" in txt or "sword" in txt or "knife" in txt: return "sword"
    if "kulhadi" in txt or "axe" in txt: return "axe"
    if "phone" in txt or "mobile" in txt: return "phone"
    if "cup" in txt or "glass" in txt: return "cup"
    if "laptop" in txt or "computer" in txt: return "laptop"
    # default: return none
    return None

def grip_profile_for_prop(prop_name: str):
    # defines basic attach bone and transform offsets per grip_style
    profiles = {
        "onehand": {"attach_bone":"hand.R","offset":[0,0,0],"rot":[0,0,0],"scale":1.0},
        "twohand": {"attach_bone":"hand.R","attach_bone_2":"hand.L","offset":[0,0,0],"rot":[0,0,0],"scale":1.0},
        "lap": {"attach_bone":"spine","offset":[0,0,0],"rot":[0,0,0],"scale":1.0}
    }
    return profiles
