# services/text_engine.py
import os
from typing import Optional

# Try local transformers first
_HAS_TRANSFORMERS = False
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
    _HAS_TRANSFORMERS = True
except Exception:
    _HAS_TRANSFORMERS = False

# Try OpenAI fallback
_HAS_OPENAI = False
try:
    import openai
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False

# Model names (changeable)
LOCAL_MODEL_NAME = os.getenv("LOCAL_TEXT_MODEL", "google/flan-t5-small")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4")  # or gpt-3.5-turbo

# Lazy-loaded pipeline
_text_pipeline = None

def get_local_pipeline():
    global _text_pipeline
    if _text_pipeline is not None:
        return _text_pipeline
    if not _HAS_TRANSFORMERS:
        raise RuntimeError("transformers not installed")
    # Using seq2seq pipeline for flan-t5
    try:
        tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(LOCAL_MODEL_NAME)
        _text_pipeline = pipeline("text2text-generation", model=model, tokenizer=tokenizer)
        return _text_pipeline
    except Exception as e:
        raise RuntimeError(f"Failed to load local model {LOCAL_MODEL_NAME}: {e}")

def call_openai(prompt: str, max_tokens: int = 256):
    if not _HAS_OPENAI:
        raise RuntimeError("openai package not installed or OPENAI_API_KEY not set")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not found in environment")
    openai.api_key = key
    # Use chat completion if model is chat-capable, else text completion
    # We'll attempt chat first (gpt-3.5/gpt-4)
    try:
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL_NAME,
            messages=[{"role":"user","content":prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        text = resp["choices"][0]["message"]["content"].strip()
        return text
    except Exception as e:
        # try completion endpoint fallback
        resp = openai.Completion.create(
            model=OPENAI_MODEL_NAME,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return resp["choices"][0]["text"].strip()

def generate_text(prompt: str, mode: Optional[str] = None, max_length: int = 256) -> str:
    """
    mode: "local" | "openai" | None (auto)
    """
    if mode is None:
        # auto: prefer local if available, else openai
        if _HAS_TRANSFORMERS:
            mode = "local"
        elif _HAS_OPENAI:
            mode = "openai"
        else:
            raise RuntimeError("No text backend available (install transformers or openai)")

    if mode == "local":
        pl = get_local_pipeline()
        # generate using text2text
        out = pl(prompt, max_length=max_length, do_sample=True, top_p=0.95, num_return_sequences=1)
        if isinstance(out, list) and out:
            return out[0].get("generated_text") or out[0].get("text") or str(out[0])
        return str(out)
    elif mode == "openai":
        return call_openai(prompt, max_tokens=max_length)
    else:
        raise ValueError("Unknown mode for generate_text")
