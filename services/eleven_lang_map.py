LANG_MAP = {
    # INDIA
    "hi": {"name":"Hindi", "model":"eleven_multilingual_v2", "voice":"alloy"},
    "bn": {"name":"Bengali","model":"eleven_multilingual_v2","voice":"alloy"},
    "ta": {"name":"Tamil","model":"eleven_multilingual_v2","voice":"alloy"},
    "te": {"name":"Telugu","model":"eleven_multilingual_v2","voice":"alloy"},
    "mr": {"name":"Marathi","model":"eleven_multilingual_v2","voice":"alloy"},
    "pa": {"name":"Punjabi","model":"eleven_multilingual_v2","voice":"alloy"},
    "gu": {"name":"Gujarati","model":"eleven_multilingual_v2","voice":"alloy"},
    "ml": {"name":"Malayalam","model":"eleven_multilingual_v2","voice":"alloy"},
    "kn": {"name":"Kannada","model":"eleven_multilingual_v2","voice":"alloy"},
    "or": {"name":"Odia","model":"eleven_multilingual_v2","voice":"alloy"},
    # GLOBAL
    "en": {"name":"English","model":"eleven_monolingual_v1","voice":"Rachel"},
    "es": {"name":"Spanish","model":"eleven_multilingual_v2","voice":"alloy"},
    "fr": {"name":"French","model":"eleven_multilingual_v2","voice":"alloy"},
    "de": {"name":"German","model":"eleven_multilingual_v2","voice":"alloy"},
    "ja": {"name":"Japanese","model":"eleven_multilingual_v2","voice":"alloy"},
}

def get_lang_config(code):
    return LANG_MAP.get(code, LANG_MAP["en"])
