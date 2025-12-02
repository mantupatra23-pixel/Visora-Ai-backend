# services/india_lang_pack.py
# Master language pack for India Localization Engine
LANGS = {
    "hi": {"name":"Hindi","script":"Devanagari","iso":"hi","tts_hint":"coqui_hi_or_pyttsx3","asr_hint":"whisper_hi"},
    "en": {"name":"English","script":"Latin","iso":"en","tts_hint":"coqui_en","asr_hint":"whisper_en"},
    "bn": {"name":"Bengali","script":"Bengali","iso":"bn","tts_hint":"coqui_bn","asr_hint":"whisper_bn"},
    "ta": {"name":"Tamil","script":"Tamil","iso":"ta","tts_hint":"coqui_ta","asr_hint":"whisper_ta"},
    "te": {"name":"Telugu","script":"Telugu","iso":"te","tts_hint":"coqui_te","asr_hint":"whisper_te"},
    "mr": {"name":"Marathi","script":"Devanagari","iso":"mr","tts_hint":"coqui_mr","asr_hint":"whisper_mr"},
    "gu": {"name":"Gujarati","script":"Gujarati","iso":"gu","tts_hint":"coqui_gu","asr_hint":"whisper_gu"},
    "pa": {"name":"Punjabi","script":"Gurmukhi","iso":"pa","tts_hint":"coqui_pa","asr_hint":"whisper_pa"},
    "kn": {"name":"Kannada","script":"Kannada","iso":"kn","tts_hint":"coqui_kn","asr_hint":"whisper_kn"},
    "ml": {"name":"Malayalam","script":"Malayalam","iso":"ml","tts_hint":"coqui_ml","asr_hint":"whisper_ml"},
    "or": {"name":"Odia","script":"Odia","iso":"or","tts_hint":"coqui_or","asr_hint":"whisper_or"},
    "as": {"name":"Assamese","script":"Assamese","iso":"as","tts_hint":"coqui_as","asr_hint":"whisper_as"},
    "sd": {"name":"Sindhi","script":"Arabic/Devanagari","iso":"sd","tts_hint":"coqui_sd","asr_hint":"whisper_sd"},
    "bh": {"name":"Bhojpuri","script":"Devanagari","iso":"bh","tts_hint":"coqui_hi","asr_hint":"whisper_hi"},
    "mai": {"name":"Maithili","script":"Devanagari","iso":"mai","tts_hint":"coqui_hi","asr_hint":"whisper_hi"},
    "raj": {"name":"Rajasthani","script":"Devanagari","iso":"raj","tts_hint":"coqui_hi","asr_hint":"whisper_hi"},
    "sa": {"name":"Sanskrit","script":"Devanagari","iso":"sa","tts_hint":"coqui_sa","asr_hint":"whisper_sa"},
}

# helper get
def available_langs():
    return {k:v["name"] for k,v in LANGS.items()}

def resolve_lang(lang_code):
    if not lang_code: return None
    return LANGS.get(lang_code, None)
