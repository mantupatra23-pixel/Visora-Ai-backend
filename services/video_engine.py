# services/video_engine.py
import os
from pathlib import Path
from typing import Optional
import hashlib
import time

OUT_DIR = Path("static/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Try advanced lipsync libs (placeholders detection)
_HAS_WAV2LIP = False
try:
    import subprocess  # we use external wav2lip repo if present
    _HAS_WAV2LIP = True  # keep True as we can call external script later if user installs it
except Exception:
    _HAS_WAV2LIP = False

# moviepy fallback
_HAS_MOVIEPY = False
try:
    from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip
    _HAS_MOVIEPY = True
except Exception as e:
    print("moviepy not available:", e)
    _HAS_MOVIEPY = False

class VideoService:
    def __init__(self):
        self.out_dir = OUT_DIR

    def _safe_name(self, seed: str):
        h = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
        return h

    def make_simple_video(self, image_path: str, audio_path: str, out_filename: Optional[str] = None, vertical: bool = False, add_subtitles: bool = False, subtitle_text: Optional[str] = None) -> str:
        """
        Simple moviepy-based video: shows the image for the length of audio and adds audio.
        Returns relative path to mp4.
        """
        if not _HAS_MOVIEPY:
            raise RuntimeError("moviepy not installed")

        img_p = Path(image_path)
        aud_p = Path(audio_path)
        if not img_p.exists():
            raise FileNotFoundError(f"Image not found: {img_p}")
        if not aud_p.exists():
            raise FileNotFoundError(f"Audio not found: {aud_p}")

        # name
        seed = f"{image_path}-{audio_path}-{time.time()}"
        name = out_filename or f"video_{self._safe_name(seed)}.mp4"
        out_path = self.out_dir / name

        # load audio
        audio = AudioFileClip(str(aud_p))
        duration = audio.duration if hasattr(audio, "duration") else None
        # create image clip lasting audio duration (or 5s fallback)
        dur = float(duration) if duration else 5.0

        # decide size: vertical if requested, else keep image size
        clip = ImageClip(str(img_p))
        # resize for vertical shorts if needed
        if vertical:
            clip = clip.resize(height=1920) if clip.h < 1920 else clip.resize(height=1920)
            # crop/center to 1080x1920
            clip = clip.on_color(size=(1080,1920), color=(0,0,0), pos=("center","center"))
        else:
            # default to 1280 width for landscape
            clip = clip.resize(width=1280) if clip.w < 1280 else clip

        clip = clip.set_duration(dur).set_audio(audio)

        # optional subtitles (simple TextClip overlay)
        if add_subtitles and subtitle_text:
            try:
                txt = TextClip(subtitle_text, fontsize=40, method="caption", size=(clip.w - 100, None))
                txt = txt.set_position(("center", clip.h - 150)).set_duration(dur)
                final = CompositeVideoClip([clip, txt])
            except Exception as e:
                print("Subtitle render failed:", e)
                final = clip
        else:
            final = clip

        # write file
        # Use reasonable codec settings
        final.write_videofile(str(out_path), fps=24, codec="libx264", audio_codec="aac", threads=2, logger=None)
        # close clips
        final.close()
        clip.close()
        audio.close()
        return str(out_path)

    def make_lipsync_wav2lip(self, image_path: str, audio_path: str, out_filename: Optional[str] = None, wav2lip_repo_path: Optional[str] = None) -> str:
        """
        If you have the Wav2Lip repo cloned and the environment set up, this function will attempt to call
        the Wav2Lip inference script to perform lip-syncing. This function assumes a CLI is available.
        Provide wav2lip_repo_path where the repo lives (the 'inference.py' script).
        """
        if not wav2lip_repo_path:
            raise RuntimeError("wav2lip_repo_path required for lipsync mode")

        inf_script = Path(wav2lip_repo_path) / "inference.py"
        if not inf_script.exists():
            raise FileNotFoundError(f"Wav2Lip inference.py not found at {inf_script}")

        out_name = out_filename or f"video_wav2lip_{self._safe_name(audio_path+image_path)}.mp4"
        out_path = self.out_dir / out_name

        cmd = [
            "python", str(inf_script),
            "--checkpoint_path", str(Path(wav2lip_repo_path)/"checkpoints"/"wav2lip_gan.pth"),
            "--face", str(image_path),
            "--audio", str(audio_path),
            "--outfile", str(out_path)
        ]
        # call subprocess
        import subprocess
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"Wav2Lip failed: {p.stderr}\n{p.stdout}")
        return str(out_path)

    def orchestrate(self, image_or_prompt: Optional[str] = None, audio_text: Optional[str] = None, audio_file: Optional[str] = None, output_name: Optional[str] = None, vertical: bool = False, use_lipsync: bool = False, wav2lip_repo: Optional[str] = None, add_subtitles: bool = False):
        """
        High-level helper that will:
         - If image_or_prompt looks like a local path and exists, use it; otherwise if prompt, call image service (if available).
         - If audio_text provided, call TTS client to synthesize; otherwise use audio_file.
         - Finally call make_simple_video or make_lipsync_wav2lip depending on use_lipsync.
        """
        # lazy imports to avoid heavy deps upfront
        img_path = None
        aud_path = None

        # If local path exists, use it as image
        if image_or_prompt:
            p = Path(image_or_prompt)
            if p.exists():
                img_path = str(p)
            else:
                # try to call image service if available
                try:
                    # local import to avoid circular deps
                    from services.image_engine import ImageService
                    isvc = ImageService()
                    img_path = isvc.generate(prompt=image_or_prompt)
                except Exception as e:
                    print("Image generation failed or image not found:", e)
                    raise

        # audio: prefer audio_file
        if audio_file:
            if Path(audio_file).exists():
                aud_path = audio_file
            else:
                raise FileNotFoundError(f"Audio file not found: {audio_file}")
        elif audio_text:
            # try tts client
            try:
                from services.tts_client import TTSClient
                tclient = TTSClient()
                # use sync synthesize (it downloads file locally)
                res = tclient.synthesize(audio_text)
                # res: {"ok": True, "remote_file":..., "downloaded": "static/outputs/xxx.mp3"}
                aud_path = res.get("downloaded") or res.get("remote_file")
                if not aud_path:
                    raise RuntimeError("TTS did not return audio file")
            except Exception as e:
                print("TTS synth failed:", e)
                raise

        if not img_path or not aud_path:
            raise RuntimeError("Missing image or audio to create video")

        # generate final
        if use_lipsync:
            return self.make_lipsync_wav2lip(img_path, aud_path, out_filename=output_name, wav2lip_repo_path=wav2lip_repo)
        else:
            return self.make_simple_video(img_path, aud_path, out_filename=output_name, vertical=vertical, add_subtitles=add_subtitles, subtitle_text=audio_text)
