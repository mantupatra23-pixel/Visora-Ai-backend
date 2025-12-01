# services/caption_hashtag_enhancer.py
"""
Enhanced caption & hashtag suggester.
- Input: title, script_text, transcript_text (optional)
- Uses small heuristics: keyword extraction, frequency, emoji insertion, CTA templates.
- Optional: if OPENAI_API_KEY is present, can call OpenAI (chat/completions) to craft catchy captions.
"""
import os, re, json, math
from collections import Counter
from pathlib import Path

def simple_keywords(text, topk=6):
    words = re.findall(r"\b[a-zA-Z]{3,}\b", (text or "").lower())
    stop = set(["this","that","with","your","from","there","about","which","their","would","could","should"])
    filt = [w for w in words if w not in stop]
    counts = Counter(filt)
    return [w for w,_ in counts.most_common(topk)]

def craft_caption(title=None, script=None, transcript=None, tone="energetic"):
    base = title or (script and script.split("\n")[0]) or (transcript and transcript.split("\n")[0]) or "Watch this"
    kws = simple_keywords(" ".join([t for t in [title or "", script or "", transcript or ""] if t]))
    hashtags = ["#"+k for k in kws[:5]] if kws else ["#AI","#Visora"]
    # templates
    if tone == "energetic":
        caption = f"{base} 🚀\nDon’t miss this — hit like & follow for more! { ' '.join(hashtags) }"
    elif tone=="calm":
        caption = f"{base}\nRelax and enjoy. { ' '.join(hashtags) }"
    else:
        caption = f"{base}\n{ ' '.join(hashtags) }"
    # optionally call OpenAI for polish if key present
    if os.getenv("OPENAI_API_KEY"):
        try:
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            prompt = f"Create a short engaging social caption (max 150 chars) for: {base}. Use tone: {tone}. Include hashtags from {kws}."
            resp = openai.ChatCompletion.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=60, temperature=0.8)
            cap = resp['choices'][0]['message']['content'].strip()
            # ensure hashtags present
            ht = [h for h in cap.split() if h.startswith("#")]
            if len(ht) < 2:
                cap = cap + " " + " ".join(hashtags[:2])
            return {"ok": True, "caption": cap, "hashtags": hashtags}
        except Exception as e:
            # fallback to simple
            return {"ok": True, "caption": caption, "hashtags": hashtags, "note":"openai_failed"}
    return {"ok": True, "caption": caption, "hashtags": hashtags}
