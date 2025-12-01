# services/llm_variant.py
"""
LLM-driven variant generator for shot_list / scene variations.
- Provides prompt templates for different cinematic styles.
- If OPENAI_API_KEY (or other LLM endpoint) provided, will call that LLM.
- Otherwise returns a set of deterministic template-based variants.
Functions:
- generate_variants(scene_plan, style='cinematic', n=3)
- generate_prompt_for_shot(shot, style)
"""

import os, json, random, textwrap

OPENAI_KEY = os.getenv("OPENAI_API_KEY")

def _local_variant_template(shot, style):
    base = shot.get("notes","")
    text = f"{shot['type']} | focus:{shot.get('speaker') or 'env'} | duration:{shot.get('duration_hint')}s"
    if style == "noir":
        return f"{text} -> High-contrast lighting, low-key shadows, tight closeup on face, slow zoom-in for dramatic reveal."
    if style == "epic":
        return f"{text} -> Wide frame, low-angle camera, heroic push-in, orchestral swell on cut."
    if style == "documentary":
        return f"{text} -> Handheld feel, slight camera shake, naturalistic light, longer reaction beats."
    return f"{text} -> Classic cinematic: match-on-action cuts, 180-degree rule, mix medium and close shots."

def generate_prompt_for_shot(shot, style):
    """
    Returns human-readable prompt to feed LLM or human director.
    """
    st = style or "cinematic"
    prompt = f"Create a cinematic description for this shot in style {st}:\n\nShot: {shot['type']}\nSpeaker: {shot.get('speaker')}\nText: {shot.get('text')}\nDurationHint: {shot.get('duration_hint')}s\nBlocking: {shot.get('blocking')}\nLighting: {shot.get('lighting')}\n\nProvide: camera movement, lens choice, mood, color notes, suggested VFX (if any), music cue."
    return prompt

def call_llm(prompt: str, max_tokens: int = 200) -> dict:
    """
    If OPENAI_KEY present, call OpenAI completions. Otherwise return a local template result.
    (Keep this isolated: you can replace with any LLM adapter.)
    """
    if OPENAI_KEY:
        try:
            import openai
            openai.api_key = OPENAI_KEY
            resp = openai.ChatCompletion.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=max_tokens)
            return {"ok":True, "text": resp.choices[0].message.content}
        except Exception as e:
            return {"ok":False, "error":str(e)}
    # fallback: return template
    return {"ok": True, "text": _local_variant_template({"type":"unknown","notes":prompt}, style="cinematic")}

def generate_variants(scene_plan: dict, style: str = "cinematic", n: int = 3) -> dict:
    """
    Returns n variants for the whole shot list. For each shot, creates a small LLM prompt or template.
    """
    shots = scene_plan.get("shot_list", [])
    variants = []
    for i in range(n):
        variant = {"style": style, "shots": []}
        for s in shots:
            if OPENAI_KEY:
                prompt = generate_prompt_for_shot(s, style)
                res = call_llm(prompt)
                text = res.get("text") if res.get("ok") else _local_variant_template(s, style)
            else:
                text = _local_variant_template(s, style)
            # small random tweak to camera distance for variety
            cam = dict(s.get("camera", {}))
            cam["distance"] = cam.get("distance",5) * (1.0 + (i-1)*0.08)
            variant["shots"].append({"index": s["index"], "variant_notes": text, "camera": cam})
        variants.append(variant)
    return {"ok": True, "variants": variants}
