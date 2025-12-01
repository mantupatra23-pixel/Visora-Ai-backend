# services/multichar_enhanced.py
import time, traceback, json
from pathlib import Path
from typing import Dict, Any, List

OUT = Path("static/outputs")
OUT.mkdir(parents=True, exist_ok=True)

# optional imports (best-effort)
try:
    from services.dialogue_split_engine import DialogueSplitter
    _HAS_DS = True
except Exception:
    DialogueSplitter = None
    _HAS_DS = False

try:
    from services.preset_engine import PresetEngine
    _HAS_PRESET = True
except Exception:
    PresetEngine = None
    _HAS_PRESET = False

try:
    from services.background_engine import BackgroundEngine
    _HAS_BG = True
except Exception:
    BackgroundEngine = None
    _HAS_BG = False

try:
    from services.image_engine import ImageService
    _HAS_IMG = True
except Exception:
    ImageService = None
    _HAS_IMG = False

try:
    from services.tts_client import TTSClient
    _HAS_TTS = True
except Exception:
    TTSClient = None
    _HAS_TTS = False

try:
    from services.lipsync_engine import LipSyncEngine
    _HAS_LIP = True
except Exception:
    LipSyncEngine = None
    _HAS_LIP = False

try:
    from services.video_engine import VideoService
    _HAS_VIDEO = True
except Exception:
    VideoService = None
    _HAS_VIDEO = False

# for audio duration measurement
_HAS_PYDUB = False
try:
    from pydub import AudioSegment
    _HAS_PYDUB = True
except Exception:
    _HAS_PYDUB = False

# moviepy fallback for timing/composition if necessary
_HAS_MOVIEPY = False
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
    _HAS_MOVIEPY = True
except Exception:
    _HAS_MOVIEPY = False

class MultiCharEnhancedEngine:
    """
    Combines:
      - DialogueSplitter -> who speaks what
      - preset engine -> prompts / presets
      - TTS per-speaker voice mapping
      - lip-sync per-line (if available)
      - timeline (start/end based on audio durations)
      - composition -> concatenated timeline
    """
    def __init__(self, voice_map: Dict[str,str] | None = None):
        # instantiate sub-engines if available
        self.ds = DialogueSplitter() if _HAS_DS else None
        self.preset = PresetEngine() if _HAS_PRESET else None
        self.bg = BackgroundEngine() if _HAS_BG else None
        self.imgsvc = ImageService() if _HAS_IMG else None
        self.tts = TTSClient() if _HAS_TTS else None
        self.lip = LipSyncEngine() if _HAS_LIP else None
        self.video = VideoService() if _HAS_VIDEO else None

        # default voice mapping — adjust to your TTS voices ids or names
        # keys are speaker types returned by DialogueSplitter (e.g., old_male, young_male, adult_female, tiger, monkey, narrator)
        default_map = {
            "old_male": "voice_old_male",
            "old_female": "voice_old_female",
            "adult_male": "voice_male",
            "adult_female": "voice_female",
            "young_male": "voice_boy",
            "young_female": "voice_girl",
            "child": "voice_child",
            "tiger": "voice_deep_cinematic",     # for animals you can map to special fx voices
            "monkey": "voice_playful",
            "narrator": "voice_male"
        }
        # merge provided mapping
        self.voice_map = default_map
        if voice_map:
            self.voice_map.update(voice_map)

    def _get_voice_for(self, speaker_type: str):
        return self.voice_map.get(speaker_type, self.voice_map.get("narrator"))

    def _measure_audio_duration(self, path: str) -> float:
        """Return duration in seconds. Try pydub first, then moviepy. Return 0 on failure."""
        try:
            if _HAS_PYDUB:
                seg = AudioSegment.from_file(path)
                return len(seg) / 1000.0
            if _HAS_MOVIEPY:
                a = AudioFileClip(path)
                dur = a.duration
                a.close()
                return dur
        except Exception:
            pass
        return 0.0

    def create_scene(self,
                     script_text: str,
                     prefer_upload: bool = False,
                     user_images: Dict[str,str] | None = None,
                     make_lipsync: bool = True,
                     bg_override: str | None = None,
                     out_name: str | None = None,
                     pause_between_lines: float = 0.2) -> Dict[str, Any]:
        """
        High level:
         1) split dialogue -> list of {speaker, text}
         2) for each unique speaker prepare character image (user_image or generate)
         3) synthesize each line with speaker-specific voice
         4) measure durations and assign timeline start times (cumulative)
         5) produce per-line clip: lipsync if available else image+audio via VideoService
         6) concatenate clips in timeline order -> final video
        """
        result = {"ok": True, "steps": {}, "errors": []}
        try:
            # 1) dialogue split
            if not self.ds:
                raise RuntimeError("DialogueSplitter service missing")
            dialogue = self.ds.split_dialogue(script_text)
            result["steps"]["dialogue"] = dialogue

            # 2) detect unique speakers
            speakers = []
            for d in dialogue:
                sp = d.get("speaker")
                if sp not in [s["speaker"] for s in speakers]:
                    speakers.append({"speaker": sp, "speaker_raw": d.get("speaker_raw")})
            result["steps"]["speakers"] = speakers

            # 3) prepare character images (user uploads override)
            char_assets = {}
            for s in speakers:
                key = s["speaker"]
                user_img = None
                if user_images and key in user_images:
                    user_img = user_images[key]
                img_path = None
                if user_img:
                    img_path = user_img
                else:
                    # try PresetEngine + ImageService
                    if self.preset:
                        try:
                            meta = self.preset.prepare_prompt_only(key, extra=None)
                            prompt = meta.get("prompt") or (script_text[:200])
                        except Exception:
                            prompt = script_text[:200]
                    else:
                        prompt = script_text[:200]
                    if self.imgsvc:
                        try:
                            name = f"char_{key}_{int(time.time())}.png"
                            img_path = self.imgsvc.generate(prompt=prompt, out_filename=name)
                        except Exception as e:
                            img_path = None
                            result["errors"].append({"step":"image_gen","speaker":key,"error":str(e)})
                    else:
                        img_path = None
                char_assets[key] = {"image": img_path}
            result["steps"]["char_assets"] = char_assets

            # 4) background
            bg_path = bg_override
            if not bg_path and self.bg:
                try:
                    bg_res = self.bg.generate_background(preset_key=None, script_text=script_text)
                    bg_path = bg_res.get("image")
                    result["steps"]["background"] = bg_res
                except Exception as e:
                    result["steps"]["background"] = {"ok": False, "error": str(e)}
            else:
                result["steps"]["background"] = {"image": bg_path, "source": "override" if bg_path else "none"}

            # 5) synthesize lines → produce audio files
            line_assets = []  # list of dicts per line: {speaker, text, audio_path, duration_seconds}
            for idx, d in enumerate(dialogue):
                sp = d.get("speaker")
                text = d.get("text")
                voice_id = self._get_voice_for(sp)
                # prepare filename
                audio_name = f"line_{idx}_{sp}.mp3"
                audio_path = None
                if self.tts:
                    try:
                        # TTSClient.synthesize may accept voice param; adapt if your client uses other key
                        # try both keywords 'voice' and 'speaker' to be safe
                        try:
                            res = self.tts.synthesize(text, filename=audio_name, voice=voice_id)
                        except TypeError:
                            # older client signature
                            res = self.tts.synthesize(text, filename=audio_name)
                        if isinstance(res, dict):
                            audio_path = res.get("downloaded") or res.get("remote_file")
                        elif isinstance(res, str):
                            audio_path = res
                    except Exception as e:
                        audio_path = None
                        result["errors"].append({"step":"tts","line":idx,"speaker":sp,"error":str(e)})
                else:
                    result["errors"].append({"step":"tts_missing","line":idx,"speaker":sp})
                # measure duration
                dur = 0.0
                if audio_path:
                    dur = self._measure_audio_duration(audio_path)
                # if missing duration -> estimate by words (0.5s per 3 words) fallback
                if dur <= 0:
                    words = len(text.split())
                    dur = max(0.5, words * 0.35)
                line_assets.append({"index": idx, "speaker": sp, "text": text, "audio": audio_path, "dur": dur})
            result["steps"]["line_assets"] = line_assets

            # 6) compute timeline start times (cumulative)
            t = 0.0
            for la in line_assets:
                la["start"] = t
                la["end"] = round(t + la["dur"], 3)
                t = la["end"] + pause_between_lines

            result["steps"]["timeline"] = [{"index":la["index"], "speaker":la["speaker"], "start":la["start"], "end":la["end"]} for la in line_assets]

            # 7) for each line -> create clip (lip sync preferred) -> collect final clip paths in order
            clips = []
            for la in line_assets:
                sp = la["speaker"]
                audio = la["audio"]
                img = char_assets.get(sp, {}).get("image")
                clip_path = None
                # attempt lipsync (needs both image and audio and lip engine)
                if make_lipsync and self.lip and img and audio:
                    try:
                        clip_path = self.lip.lipsync(img, audio, output_name=f"lip_{la['index']}_{sp}.mp4")
                    except Exception as e:
                        result["errors"].append({"step":"lipsync_failed","line":la["index"], "error": str(e)})
                        clip_path = None
                # fallback to VideoService simple composer
                if not clip_path:
                    if self.video and img and audio:
                        try:
                            clip_path = self.video.make_simple_video(img, audio, out_filename=f"clip_{la['index']}_{sp}.mp4", vertical=True, add_subtitles=True)
                        except Exception as e:
                            result["errors"].append({"step":"compose_failed","line":la["index"], "error": str(e)})
                            clip_path = None
                    else:
                        # fallback: silent placeholder video or skip
                        result["errors"].append({"step":"no_clip","line":la["index"], "reason":"missing img or video service"})
                        clip_path = None
                clips.append({"line": la, "clip": clip_path})

            result["steps"]["clips"] = clips

            # 8) assemble final timeline:
            #    - Simple approach: concatenate clips in their sequence order.
            #    - More advanced: place clips at absolute start times on a longer timeline (requires CompositeVideoClip).
            final_video_path = None
            # Attempt to assemble via moviepy by concatenation (fast & simple)
            if _HAS_MOVIEPY:
                try:
                    clip_objs = []
                    from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
                    for cinfo in clips:
                        cp = cinfo.get("clip")
                        if not cp:
                            continue
                        vc = VideoFileClip(cp)
                        clip_objs.append(vc)
                    if not clip_objs:
                        raise RuntimeError("No clip files available to concatenate")
                    final_clip = concatenate_videoclips(clip_objs, method="compose")
                    out_fname = out_name or f"multichar_enhanced_{int(time.time())}.mp4"
                    out_path = OUT / out_fname
                    final_clip.write_videofile(str(out_path), fps=24, codec="libx264", audio_codec="aac", logger=None)
                    # close
                    for v in clip_objs:
                        v.close()
                    final_clip.close()
                    final_video_path = str(out_path)
                except Exception as e:
                    result["errors"].append({"step":"moviepy_concat","error":str(e)})
                    final_video_path = None
            else:
                # fallback: if VideoService has concat helper, try that (not guaranteed)
                if self.video and hasattr(self.video, "concat_videos"):
                    try:
                        video_paths = [c["clip"] for c in clips if c["clip"]]
                        final_video_path = self.video.concat_videos(video_paths, out_filename=out_name or f"multichar_enh_{int(time.time())}.mp4")
                    except Exception as e:
                        result["errors"].append({"step":"video_service_concat","error":str(e)})
                        final_video_path = None

            result["steps"]["final_video"] = final_video_path

            if result["errors"]:
                result["ok"] = False
            return result

        except Exception as e:
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
