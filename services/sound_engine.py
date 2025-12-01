# services/sound_engine.py
import os
from pathlib import Path
from pydub import AudioSegment, effects
import numpy as np
import librosa
import soundfile as sf
import math
import hashlib
import time

OUT_DIR = Path("static/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def _safe_name(seed: str):
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]

# --- Basic helpers ---
def load_audio(path: str) -> AudioSegment:
    return AudioSegment.from_file(path)

def save_audio(segment: AudioSegment, path: str, format: str = "mp3"):
    segment.export(path, format=format)
    return str(path)

# --- Effects ---
def apply_reverb(pydub_seg: AudioSegment, decay: float = 0.4) -> AudioSegment:
    """
    Simple reverb via multiple delayed attenuated copies.
    decay: 0..1 smaller = light, bigger = more reverb
    """
    base = pydub_seg
    combined = base
    delay_ms = 50
    attenuation = 0.6 * decay
    # add few echoes
    for i in range(1, 6):
        delayed = base - (i * 6)  # reduce gain
        delayed = delayed.delay(i * delay_ms)
        delayed = delayed - (i * (6 + attenuation*10))
        combined = combined.overlay(delayed)
    return combined

def apply_echo(segment: AudioSegment, delay_ms: int = 200, repeats: int = 3, attenuation_db: float = 6.0) -> AudioSegment:
    out = segment
    for i in range(1, repeats+1):
        echo = segment - (attenuation_db * i)
        out = out.overlay(echo, position=delay_ms * i)
    return out

def change_pitch(segment: AudioSegment, semitones: float) -> AudioSegment:
    """
    Change pitch by resampling technique (preserves length by re-speeding).
    Positive semitones => higher pitch.
    """
    # convert to numpy
    samples = np.array(segment.get_array_of_samples()).astype(np.float32)
    sr = segment.frame_rate
    # librosa pitch shift
    try:
        shifted = librosa.effects.pitch_shift(samples, sr, n_steps=semitones)
        # convert back to AudioSegment
        tmp_path = OUT_DIR / f"tmp_pitch_{_safe_name(str(time.time()))}.wav"
        sf.write(str(tmp_path), shifted, sr)
        out = AudioSegment.from_wav(str(tmp_path))
        tmp_path.unlink(missing_ok=True)
        return out
    except Exception as e:
        # fallback: speed change (affects duration)
        rate = 2.0 ** (semitones / 12.0)
        return speed_change(segment, rate)

def speed_change(sound: AudioSegment, speed=1.0) -> AudioSegment:
    # change frame_rate then set to original to change speed
    new_frame_rate = int(sound.frame_rate * speed)
    sped = sound._spawn(sound.raw_data, overrides={"frame_rate": new_frame_rate})
    return sped.set_frame_rate(sound.frame_rate)

# --- Advanced: auto-ducking (voice over music) ---
def auto_duck(music: AudioSegment, voice: AudioSegment, duck_amount_db: float = 12.0, padding_ms: int = 120):
    """
    Reduce music volume when voice is present.
    Approach: break music into chunks, detect voice presence by rms of voice, reduce music where voice > threshold.
    """
    # convert to mono and same frame_rate
    voice = voice.set_frame_rate(music.frame_rate).set_channels(1)
    music = music.set_channels(1)

    # chunk size
    chunk_ms = 200
    music_chunks = [music[i:i+chunk_ms] for i in range(0, len(music), chunk_ms)]
    voice_chunks = [voice[i:i+chunk_ms] for i in range(0, len(voice), chunk_ms)]

    out = AudioSegment.silent(duration=0)
    for idx, mchunk in enumerate(music_chunks):
        # corresponding voice chunk index
        vchunk = voice_chunks[idx] if idx < len(voice_chunks) else AudioSegment.silent(duration=chunk_ms)
        # compute rms
        vrms = vchunk.rms
        # threshold for presence
        threshold = 500  # empirical
        if vrms > threshold:
            # duck music chunk
            mchunk = mchunk - duck_amount_db
        out += mchunk
    # mix voice on top
    # pad music or voice to equal length
    final_length = max(len(out), len(voice))
    out = out + AudioSegment.silent(duration=max(0, final_length - len(out)))
    voice_pad = voice + AudioSegment.silent(duration=max(0, final_length - len(voice)))
    mixed = out.overlay(voice_pad)
    return mixed

# --- Overlay sound effect at timestamp ---
def overlay_sfx(base: AudioSegment, sfx_path: str, at_ms: int = 0, gain_during_sfx_db: float = -6.0):
    sfx = AudioSegment.from_file(sfx_path)
    # reduce base volume slightly during sfx (duck)
    before = base[:at_ms]
    mid = base[at_ms: at_ms + len(sfx)]
    after = base[at_ms + len(sfx):]
    mid = mid + gain_during_sfx_db
    combined_mid = mid.overlay(sfx)
    return before + combined_mid + after

# --- High level: mix voice + music with presets ---
def mix_voice_and_music(voice_path: str, music_path: str = None, out_name: str = None, auto_ducking: bool = True, music_gain_db: float = -6.0, voice_gain_db: float = 0.0):
    """
    voice_path: path to speech mp3/wav
    music_path: background music (optional)
    returns path to mixed file
    """
    voice = load_audio(voice_path).normalize()
    voice = voice + voice_gain_db

    if music_path and Path(music_path).exists():
        music = load_audio(music_path).normalize() + music_gain_db
        # make music at least as long as voice
        if len(music) < len(voice):
            # loop music
            repeated = AudioSegment.silent(duration=0)
            while len(repeated) < len(voice):
                repeated += music
            music = repeated
        else:
            music = music[:len(voice)]
        if auto_ducking:
            final = auto_duck(music, voice)
        else:
            # naive mix: lower music and overlay
            final = music.overlay(voice)
    else:
        final = voice

    out_name = out_name or f"mix_{_safe_name(voice_path + (music_path or ''))}.mp3"
    out_path = OUT_DIR / out_name
    save_audio(final, out_path, format="mp3")
    return str(out_path)
