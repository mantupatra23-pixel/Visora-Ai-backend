# services/beat_analyzer.py
# Simple beat analyzer: prefers librosa if installed, else falls back to naive onset detection.
import os, json
from pathlib import Path

def analyze_beats(audio_path, use_librosa=True, sr=22050):
    """
    Returns: {"bpm": float, "beats": [seconds,...], "onsets_frames": [int,...]}
    Requires librosa for best results. If librosa not available, asks for manual bpm param fallback.
    """
    try:
        if use_librosa:
            import librosa
            y, _ = librosa.load(audio_path, sr=sr, mono=True)
            # tempo and beat frames
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
            return {"ok": True, "bpm": float(round(tempo,2)), "beats": beat_times}
    except Exception as e:
        # fallback naive detection (very rough)
        from pydub import AudioSegment
        try:
            seg = AudioSegment.from_file(audio_path)
            dur_s = seg.duration_seconds
            # fallback: ask caller for bpm or assume 120
            return {"ok": False, "error": "librosa_missing_or_fail", "suggested_bpm": 120, "duration": dur_s}
        except Exception as e2:
            return {"ok": False, "error": str(e2)}
