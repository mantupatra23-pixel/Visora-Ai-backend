# services/template_engine.py
import os
from pathlib import Path
from typing import Optional, Dict, Any
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import textwrap
import hashlib
import time

OUT_DIR = Path("static/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Helper - create text image with PIL so we don't depend on ImageMagick
def render_text_image(text: str, width: int, fontsize: int = 48, color=(255,255,255), bg=(0,0,0,0), padding=20):
    """
    Returns a PIL Image containing wrapped text sized to width.
    """
    # choose default font (system)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # create image canvas with long height then crop
    img = Image.new("RGBA", (width, 2000), bg)
    draw = ImageDraw.Draw(img)
    # wrap text
    lines = textwrap.wrap(text, width=40)
    y = padding
    for line in lines:
        draw.text((padding, y), line, fill=color, font=font)
        y += fontsize + 6
    # crop to used height
    cropped = img.crop((0,0,width, min(y+padding, img.height)))
    return cropped

def _safe_name(seed: str):
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]

# Simple effects
def apply_zoom(clip, zoom_factor=1.1, duration=None):
    """
    Zoom effect: gradually scale from 1.0 to zoom_factor over clip duration.
    """
    duration = duration or clip.duration
    return clip.fx(lambda c, t: c.resize(1 + (zoom_factor - 1) * (t / duration)))

def apply_fadeinout(clip, fade=0.6):
    return clip.fx(lambda c, t: c).crossfadein(fade).crossfadeout(fade) if hasattr(clip, "crossfadein") else clip

class TemplateEngine:
    def __init__(self):
        # preset templates
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict]:
        return {
            "motivation_shorts": {
                "resolution": (1080, 1920),
                "bg_color": (0,0,0),
                "music_volume": 0.12,
                "voice_volume": 1.0,
                "title_fontsize": 60,
                "body_fontsize": 44,
                "default_music": None,   # provide path or None
                "duration_sec": 25,
                "effects": ["zoom","fade"]
            },
            "promo": {
                "resolution": (1280,720),
                "bg_color": (10,10,10),
                "music_volume": 0.18,
                "voice_volume": 1.0,
                "title_fontsize": 56,
                "body_fontsize": 36,
                "default_music": None,
                "duration_sec": 30,
                "effects": ["pan","fade"]
            },
            "news_flash": {
                "resolution": (1280,720),
                "bg_color": (20,20,20),
                "music_volume": 0.1,
                "voice_volume": 1.0,
                "title_fontsize": 48,
                "body_fontsize": 30,
                "default_music": None,
                "duration_sec": 20,
                "effects": ["none"]
            }
        }

    def render_template(self,
                        template_name: str,
                        title: str,
                        body: str,
                        image_path: Optional[str] = None,
                        audio_path: Optional[str] = None,
                        music_path: Optional[str] = None,
                        output_name: Optional[str] = None,
                        vertical: bool = True,
                        add_subtitles: bool = True) -> Dict[str, Any]:
        """
        Renders a video using the template.
        Returns {"ok": True, "video": path}
        """
        tpl = self.templates.get(template_name)
        if not tpl:
            return {"ok": False, "error": f"Unknown template: {template_name}"}

        res_w, res_h = tpl["resolution"]
        # override vertical resizing if requested
        if vertical:
            res_w, res_h = (1080, 1920)

        seed = f"{template_name}-{title[:40]}-{time.time()}"
        out_name = output_name or f"template_{_safe_name(seed)}.mp4"
        out_path = OUT_DIR / out_name

        # prepare base image clip
        if image_path and Path(image_path).exists():
            img_clip = ImageClip(str(image_path)).set_duration(tpl["duration_sec"])
            # resize to fit canvas while keeping aspect
            img_clip = img_clip.resize(height=res_h) if img_clip.h < res_h else img_clip
            # center crop/pad to resolution
            img_clip = img_clip.on_color(size=(res_w,res_h), color=tpl["bg_color"], pos=("center","center"))
        else:
            # create a plain background
            bg_image = Image.new("RGB", (res_w, res_h), tpl["bg_color"])
            bg_path = OUT_DIR / f"bg_{_safe_name(seed)}.png"
            bg_image.save(bg_path)
            img_clip = ImageClip(str(bg_path)).set_duration(tpl["duration_sec"])

        # add zoom/pan effects
        if "zoom" in tpl.get("effects", []):
            try:
                img_clip = img_clip.fx(lambda c, t: c.resize(1 + 0.05 * (t / c.duration)))
            except Exception:
                pass

        # create title and body text images
        title_img = render_text_image(title, width=res_w, fontsize=tpl["title_fontsize"])
        title_clip = ImageClip(np.array(title_img)).set_duration(min(4, img_clip.duration)).set_position(("center", int(res_h*0.12)))
        body_img = render_text_image(body, width=int(res_w*0.9), fontsize=tpl["body_fontsize"])
        body_clip = ImageClip(np.array(body_img)).set_duration(img_clip.duration).set_position(("center", int(res_h*0.55)))

        # If subtitles requested, create a smaller text strip at bottom
        subtitle_clip = None
        if add_subtitles:
            sub_img = render_text_image(body, width=int(res_w*0.9), fontsize=36)
            subtitle_clip = ImageClip(np.array(sub_img)).set_duration(img_clip.duration).set_position(("center", res_h - 220))

        # audio handling
        audio_clip = None
        if audio_path and Path(audio_path).exists():
            try:
                audio_clip = AudioFileClip(str(audio_path))
            except Exception:
                audio_clip = None

        # background music
        music_clip = None
        chosen_music = music_path or tpl.get("default_music")
        if chosen_music and Path(chosen_music).exists():
            try:
                music_clip = AudioFileClip(str(chosen_music)).volumex(tpl["music_volume"])
            except Exception:
                music_clip = None

        # Compose video: base image + overlays
        overlay_clips = [title_clip, body_clip]
        if subtitle_clip:
            overlay_clips.append(subtitle_clip)

        final = CompositeVideoClip([img_clip] + overlay_clips).set_duration(img_clip.duration)

        # attach audio: prefer speech audio as main, then mix music underneath
        if audio_clip:
            # set main audio
            final = final.set_audio(audio_clip.volumex(tpl["voice_volume"]))
            if music_clip:
                # mix music with voice (background)
                combined = audio_clip.audio_mask if hasattr(audio_clip, "audio_mask") else audio_clip
                # moviepy mixing: use CompositeAudioClip
                try:
                    from moviepy.audio.AudioClip import CompositeAudioClip
                    music_clip = music_clip.set_duration(final.duration)
                    combined_audio = CompositeAudioClip([audio_clip.volumex(tpl["voice_volume"]), music_clip.volumex(tpl["music_volume"])])
                    final = final.set_audio(combined_audio)
                except Exception:
                    # fallback: set voice only
                    final = final.set_audio(audio_clip)
        else:
            # no speech; use music if available
            if music_clip:
                final = final.set_audio(music_clip.set_duration(final.duration))

        # write file with safe codec params
        final.write_videofile(str(out_path), fps=24, codec="libx264", audio_codec="aac", threads=2, logger=None)
        # close resources
        try:
            final.close()
        except Exception:
            pass

        return {"ok": True, "video": str(out_path)}
