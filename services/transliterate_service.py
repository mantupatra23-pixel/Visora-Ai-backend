# services/transliterate_service.py
def transliterate_text(text, src_script="iast", tgt_script="devanagari"):
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        out = transliterate(text, src_script, tgt_script)
        return {"ok": True, "out": out}
    except Exception as e:
        # fallback: return original
        return {"ok": False, "error": str(e), "out": text}
