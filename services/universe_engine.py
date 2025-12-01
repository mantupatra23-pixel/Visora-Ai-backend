# services/universe_engine.py
from pathlib import Path
import time
import traceback

# try import existing engines
try:
    from services.preset_engine import PresetEngine
except Exception:
    PresetEngine = None

try:
    from services.background_engine import BackgroundEngine
except Exception:
    BackgroundEngine = None

try:
    from services.character3d_engine import Character3DEngine
except Exception:
    Character3DEngine = None

try:
    from services.auto_engine import AutoEngine
except Exception:
    AutoEngine = None

# Optional image service (for direct SD character generation)
try:
    from services.image_engine import ImageService
except Exception:
    ImageService = None

OUT = Path("static/outputs")
OUT.mkdir(parents=True, exist_ok=True)

class UniverseEngine:
    def __init__(self):
        self.preset = PresetEngine() if PresetEngine else None
        self.bg = BackgroundEngine() if BackgroundEngine else None
        self.c3d = Character3DEngine() if Character3DEngine else None
        self.auto = AutoEngine() if AutoEngine else None
        self.img = ImageService() if ImageService else None

    def _choose_preset(self, script_text: str, preferred: str | None = None):
        # if preferred provided and exists -> use it
        if preferred and self.preset:
            p = self.preset.get_preset(preferred)
            if p:
                return preferred, p
        # heuristics: find keyword matches in presets
        if self.preset:
            # simple heuristic: look for keywords inside script
            low = (script_text or "").lower()
            mapping = {
                "tiger": ["tiger","sher","शेर","animal","wild"],
                "monkey_3d": ["monkey","bandar","monkey","funny"],
                "anime_boy": ["boy","anime","hero","young"],
                "anime_girl": ["girl","anime","she","her"],
                "human_cartoon": ["man","woman","person","host","presenter"]
            }
            for key, keywords in mapping.items():
                for kw in keywords:
                    if kw in low:
                        return key, self.preset.get_preset(key)
            # fallback: pick a random or first preset
            lst = list(self.preset.list_presets())
            if lst:
                return lst[0]["key"], self.preset.get_preset(lst[0]["key"])
        return None, None

    def create_universe_asset(self,
                              script_text: str,
                              preferred_preset: str | None = None,
                              prefer_upload: bool = False,
                              user_image_path: str | None = None,
                              extra_prompt: str | None = None,
                              make_3d: bool = True,
                              want_video: bool = True,
                              voice_filename: str | None = None,
                              image_filename: str | None = None,
                              video_filename: str | None = None):
        """
        High level orchestrator:
         - Choose preset (or use preferred)
         - Generate background prompt & image
         - If prefer_upload and user_image_path provided -> use that as source
           else auto-generate a character image using preset (via ImageService or PresetEngine prompt)
         - If make_3d and character3d_engine available -> generate 3D mesh/video
         - If want_video -> call AutoEngine to stitch final video (text -> tts -> image -> video)
        Returns dict with detailed steps and file paths.
        """
        res = {"ok": True, "steps": {}, "errors": []}
        try:
            # 1) choose preset
            preset_key, preset_meta = self._choose_preset(script_text, preferred_preset)
            res["steps"]["preset_selected"] = {"key": preset_key, "meta": preset_meta}

            # 2) background
            bg_info = None
            if self.bg:
                try:
                    bg_info = self.bg.generate_background(preset_key, script_text, explicit_mood=None, out_name=None)
                    res["steps"]["background"] = bg_info
                except Exception as e:
                    res["steps"]["background"] = {"ok": False, "error": str(e)}
                    res["errors"].append({"step":"background","error":str(e)})
            else:
                res["steps"]["background"] = {"ok": False, "error": "No BackgroundEngine"}

            # 3) character image: user upload preferred?
            char_img = None
            if prefer_upload and user_image_path:
                # use uploaded image file (assume user saved it to static/outputs and provided path)
                char_img = user_image_path
                res["steps"]["character_image"] = {"ok": True, "source": "user_upload", "path": char_img}
            else:
                # auto-generate character image:
                # If ImageService available -> use preset prompt via PresetEngine or direct prompt
                if self.preset:
                    try:
                        # prepare prompt meta (not running Zero123 here, but creating prompt)
                        meta = self.preset.prepare_prompt_only(preset_key, extra=extra_prompt)
                        prompt = meta.get("prompt")
                        # call ImageService if present
                        if self.img:
                            img_name = image_filename or f"char_{int(time.time())}.png"
                            img_path = self.img.generate(prompt=prompt, out_filename=img_name)
                            char_img = img_path
                            res["steps"]["character_image"] = {"ok": True, "source":"image_service", "path": img_path, "prompt": prompt}
                        else:
                            # fallback: save prompt meta file for manual run
                            res["steps"]["character_image"] = {"ok": False, "error":"No ImageService to generate image", "prompt": prompt}
                    except Exception as e:
                        res["steps"]["character_image"] = {"ok": False, "error": str(e)}
                        res["errors"].append({"step":"character_image","error":str(e)})
                else:
                    res["steps"]["character_image"] = {"ok": False, "error":"No PresetEngine available"}

            # 4) If make_3d -> call character3d_engine (prefer multi-view pipeline)
            mesh_path = None
            if make_3d and self.c3d:
                try:
                    if char_img:
                        # run full pipeline (Zero123 -> TripoSR)
                        mesh_path = self.c3d.generate_character(char_img)
                        res["steps"]["character_3d"] = {"ok": True, "mesh": mesh_path}
                    else:
                        res["steps"]["character_3d"] = {"ok": False, "error":"No character image available for 3D"}
                except Exception as e:
                    res["steps"]["character_3d"] = {"ok": False, "error": str(e)}
                    res["errors"].append({"step":"character_3d","error":str(e)})
            else:
                res["steps"]["character_3d"] = {"ok": False, "skipped": True if not make_3d else "No C3D engine"}

            # 5) Final video via AutoEngine (optional)
            final_video = None
            if want_video and self.auto:
                try:
                    # pass preferred files to auto engine: it expects prompt, and will call image/tts/video chains
                    # we prefer to give generated character image + bg + voice filename override
                    # create composite prompt: include preset info and script
                    composite_prompt = script_text
                    # call auto.create_pipeline - it will try to use internal engines
                    out = self.auto.create_pipeline(
                        prompt=composite_prompt,
                        mode_text="local",
                        want_image=True,
                        want_audio=True,
                        want_video=True,
                        voice_filename=voice_filename,
                        image_filename=image_filename or (char_img and Path(char_img).name),
                        video_filename=video_filename,
                        vertical=True,
                        add_subtitles=True
                    )
                    final_video = out.get("video")
                    res["steps"]["auto_pipeline"] = out
                except Exception as e:
                    res["steps"]["auto_pipeline"] = {"ok": False, "error": str(e)}
                    res["errors"].append({"step":"auto_pipeline","error":str(e)})
            else:
                res["steps"]["auto_pipeline"] = {"ok": False, "skipped": True}

            # attach quick summary
            res["summary"] = {"preset": preset_key, "character_image": char_img, "background": bg_info.get("image") if bg_info else None, "mesh": mesh_path, "final_video": final_video}
            if res["errors"]:
                res["ok"] = False
            return res

        except Exception as e:
            traceback.print_exc()
            return {"ok": False, "error": str(e)}
