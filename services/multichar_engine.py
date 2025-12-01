# services/multichar_engine.py
import time, traceback, math
from pathlib import Path
from typing import List, Dict, Any

OUT = Path("static/outputs")
OUT.mkdir(parents=True, exist_ok=True)

# Try imports of previously created engines (best-effort)
try:
    from services.character_detect_engine import CharacterDetectEngine
except Exception:
    CharacterDetectEngine = None

try:
    from services.preset_engine import PresetEngine
except Exception:
    PresetEngine = None

try:
    from services.background_engine import BackgroundEngine
except Exception:
    BackgroundEngine = None

try:
    from services.image_engine import ImageService
except Exception:
    ImageService = None

try:
    from services.tts_client import TTSClient
except Exception:
    TTSClient = None

try:
    from services.video_engine import VideoService
except Exception:
    VideoService = None

# lip sync engines (optional)
try:
    from services.lipsync_engine import LipSyncEngine
except Exception:
    LipSyncEngine = None

# moviepy for composition (lightweight cuts)
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
    _HAS_MOVIEPY = True
except Exception:
    _HAS_MOVIEPY = False

class MultiCharacterEngine:
    def __init__(self):
        self.detector = CharacterDetectEngine() if CharacterDetectEngine else None
        self.preset = PresetEngine() if PresetEngine else None
        self.bg = BackgroundEngine() if BackgroundEngine else None
        self.imgsvc = ImageService() if ImageService else None
        self.tts = TTSClient() if TTSClient else None
        self.video = VideoService() if VideoService else None
        self.lip = LipSyncEngine() if LipSyncEngine else None

    def _split_dialogue_simple(self, script: str, characters: List[Dict]) -> List[Dict]:
        """
        Very simple heuristic:
         - split script by sentences ('.','?','!')
         - assign sentences round-robin to detected characters in order they appear
        Returns list of {'char':preset_key, 'text': sentence}
        """
        import re
        sents = [s.strip() for s in re.split(r'(?<=[\.\?\!])\s+', script) if s.strip()]
        if not sents:
            sents = [script]
        # order characters by first occurrence in script if possible
        ordered = []
        script_lower = script.lower()
        for c in characters:
            # check raw match
            raw = c.get("raw","")
            idx = script_lower.find(raw.lower()) if raw else -1
            ordered.append((idx if idx>=0 else 999999, c))
        ordered.sort(key=lambda x:x[0])
        char_list = [c for _,c in ordered]
        if not char_list:
            # default to single narrator
            char_list = [{"preset":"human_cartoon_male","type":"narrator"}]
        assignments = []
        ci = 0
        for sent in sents:
            ch = char_list[ci % len(char_list)]
            assignments.append({"char": ch, "text": sent})
            ci += 1
        return assignments

    def build_character_asset(self, char_meta: Dict, scene_prompt: str=None, image_override: str=None) -> Dict[str,Any]:
        """
        For a detected character entry, produce:
         - image_path (generated or override)
         - voice_path (TTS)
        Returns metadata dict.
        """
        out = {"ok": True, "char_meta": char_meta}
        preset_key = char_meta.get("preset")
        # 1) image: if image_override provided use it, else try ImageService via preset prompt
        img_path = None
        try:
            if image_override:
                img_path = image_override
            else:
                if self.preset:
                    meta = self.preset.prepare_prompt_only(preset_key, extra=scene_prompt or "")
                    prompt = meta.get("prompt")
                else:
                    prompt = (scene_prompt or "portrait of character")
                if self.imgsvc:
                    name = f"char_{preset_key}_{int(time.time())}.png"
                    img_path = self.imgsvc.generate(prompt=prompt, out_filename=name)
                else:
                    # no image service -> no image
                    img_path = None
            out["image"] = img_path
        except Exception as e:
            out["image"] = None
            out.setdefault("errors",[]).append(f"image_err:{e}")

        # 2) voice: nothing to synthesize yet, will be synthesized per assigned text
        out["voice_files"] = []  # will append as synths happen
        return out

    def synthesize_text(self, text: str, voice_filename: str=None) -> str:
        """
        Use TTSClient to synthesize and download local file. returns path or raises.
        """
        if not self.tts:
            raise RuntimeError("No TTS client available")
        # TTSClient.synthesize is sync wrapper
        res = self.tts.synthesize(text, filename=voice_filename)
        # res may be dict with "downloaded" or "remote_file"
        if isinstance(res, dict):
            return res.get("downloaded") or res.get("remote_file")
        return res

    def create_scene_video(self, script: str, prefer_upload: bool=False, user_images: Dict[str,str]=None, make_lipsync: bool=False, bg_override: str=None, out_name: str=None) -> Dict[str,Any]:
        """
        High level: detect characters -> split dialogue -> for each assignment:
          - ensure char image
          - synthesize audio for sentence
          - optional lipsync to produce talking clip (wav2lip/sadtalker)
          - make short clip (image+audio) -> then concatenate with transitions
        Returns dict with final video path & step details.
        """
        result = {"ok": True, "steps": {}, "errors": []}
        try:
            # 1) detect characters
            chars = []
            if self.detector:
                chars = self.detector.detect_characters(script)
            else:
                chars = [{"type":"narrator","preset":"human_cartoon_male","raw":"narrator"}]
            result["steps"]["detected"] = chars

            # 2) generate background
            bg_path = None
            if bg_override:
                bg_path = bg_override
                result["steps"]["background"] = {"ok":True, "image": bg_path, "source":"override"}
            elif self.bg:
                bg_res = self.bg.generate_background(preset_key=chars[0].get("preset"), script_text=script)
                bg_path = bg_res.get("image")
                result["steps"]["background"] = bg_res
            else:
                result["steps"]["background"] = {"ok": False, "error":"No BackgroundEngine"}

            # 3) split dialogue among characters
            assignments = self._split_dialogue_simple(script, chars)
            result["steps"]["assignments"] = assignments

            # 4) prepare character assets
            char_assets = {}
            for c in chars:
                key = c.get("preset") or c.get("type")
                user_img = None
                if user_images and key in user_images:
                    user_img = user_images[key]
                asset = self.build_character_asset(c, scene_prompt=script, image_override=user_img)
                char_assets[key] = asset
            result["steps"]["char_assets"] = char_assets

            # 5) for each assignment produce short clip
            clips_info = []
            for idx, a in enumerate(assignments):
                char = a["char"]
                text = a["text"]
                preset_key = char.get("preset") or char.get("type")
                asset = char_assets.get(preset_key, {})
                # synthesize TTS
                try:
                    voice_fname = f"voice_{preset_key}_{idx}.mp3"
                    voice_path = self.synthesize_text(text, voice_filename=voice_fname) if self.tts else None
                except Exception as e:
                    voice_path = None
                    result["errors"].append({"step":"tts","error":str(e),"assignment":a})
                # attempt lipsync if requested and lip engine available & image exists
                talking_video = None
                try:
                    if make_lipsync and self.lip and asset.get("image") and voice_path:
                        talking_video = self.lip.lipsync(asset.get("image"), voice_path, output_name=f"talk_{preset_key}_{idx}.mp4")
                except Exception as e:
                    talking_video = None
                    result["errors"].append({"step":"lipsync","error":str(e),"assignment":a})
                # if lipsync video not produced -> make simple image+audio clip
                final_clip_path = None
                if talking_video:
                    final_clip_path = talking_video
                else:
                    # use VideoService.make_simple_video to compose image+audio
                    try:
                        if self.video and asset.get("image") and voice_path:
                            vid = self.video.make_simple_video(asset.get("image"), voice_path, out_filename=f"clip_{preset_key}_{idx}.mp4", vertical=True, add_subtitles=False)
                            final_clip_path = vid
                        else:
                            # fallback: create a minimal silent mp4 of 3 sec if no audio/image
                            final_clip_path = None
                            result["errors"].append({"step":"compose","error":"No asset/image or video service to create clip","assignment":a})
                    except Exception as e:
                        final_clip_path = None
                        result["errors"].append({"step":"compose","error":str(e),"assignment":a})
                clips_info.append({"assignment":a, "voice": voice_path, "talking_video": talking_video, "final_clip": final_clip_path})
            result["steps"]["clips_info"] = clips_info

            # 6) concatenate clips (moviepy)
            if _HAS_MOVIEPY:
                try:
                    clip_objs = []
                    for info in clips_info:
                        path = info.get("final_clip")
                        if not path:
                            continue
                        # load clip as VideoFileClip (delayed import)
                        from moviepy.editor import VideoFileClip
                        vc = VideoFileClip(str(path))
                        clip_objs.append(vc)
                    if not clip_objs:
                        raise RuntimeError("No clips to concatenate")
                    final = concatenate_videoclips(clip_objs, method="compose")
                    # optionally overlay background if final size differs - here we assume clips already have bg
                    out_name = out_name or f"multichar_scene_{int(time.time())}.mp4"
                    out_path = OUT / out_name
                    final.write_videofile(str(out_path), fps=24, codec="libx264", audio_codec="aac", logger=None)
                    # close resources
                    for c in clip_objs:
                        c.close()
                    final.close()
                    result["steps"]["final_video"] = str(out_path)
                except Exception as e:
                    result["errors"].append({"step":"concat","error":str(e)})
                    result["steps"]["final_video"] = None
            else:
                result["steps"]["final_video"] = None
                result["errors"].append({"step":"moviepy_missing","error":"moviepy not installed"})
            # final
            if result["errors"]:
                result["ok"] = False
            return result

        except Exception as e:
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
