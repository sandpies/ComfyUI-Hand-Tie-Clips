"""HTC RefMod Builder. Writes one visual RefMod into models/refmods.

The rail does not read this node's output by a wire. It reads the file,
the same way a still is a file in h3_refs. `name` is the string to put in
the row's `file` field.

Sources are named in `mod_plan` as filenames under `h3_refs`, not wired in
as IMAGE sockets. A DOM panel cannot fill a socket, and a fixed set of
sockets cannot be empty gracefully -- which is the whole reason the other
packs need a separate node to toggle their inputs on and off. Several
stills and a clip become one latent stacked along time, not a version-5
bundle: `load_visual` reads a bundle's first visual member and drops the
rest, so a bundle would silently throw away most of a character reference.

The `images` / `video` sockets still work, for graphs built before the
panel existed. A non-empty `mod_plan` outranks them.
"""
from __future__ import annotations

import torch

from . import media as _media
from . import refmod as _refmod
from comfy_api.latest import io

TAG = "HandTieClips"


def _v3_accepted(fn, kwargs):
    """The kwargs a V1 hook's signature accepts (all of them if it takes **kw)."""
    import inspect as _inspect
    params = _inspect.signature(fn).parameters
    if any(p.kind is p.VAR_KEYWORD for p in params.values()):
        return dict(kwargs)
    return {k: v for k, v in kwargs.items() if k in params}


class _HTCRefModBuilderImpl:


    # Executes on its own, the way PlagueKind's RefMod Save node does.
    # Without this the builder only runs when `name` feeds a node that is
    # itself executed, so a queue with nothing wired to it silently does
    # nothing and reads as "the build did not happen". Safe, because
    # `build=stop` returns before the VAE is touched.

    @classmethod
    def IS_CHANGED(cls, mod_plan="", build="stop", **_kw):
        # A stopped builder is inert, so it must not re-run when a source
        # file changes on disk. A started one must.
        if str(build) != "start":
            return "stopped"
        try:
            stills, clip, _voice = _refmod.parse_mod_plan(mod_plan)
        except ValueError:
            return str(mod_plan)
        names = list(stills) + ([clip["file"]] if clip else [])
        if _voice:
            names.append(_voice)
        return _media.stamp(names)

    def _isolated(self, canvas, index, count, masking):
        """`canvas` with optional subject crop + backdrop replacement."""
        if not masking:
            return canvas
        wired = masking.get("wired")
        if wired is not None:
            if wired.shape[0] == 1:
                pick = wired
            elif count == 1 and wired.shape[0] == canvas.shape[0]:
                pick = wired  # one clip, a mask per frame
            else:
                pick = wired[index:index + 1]
            m = _refmod.mask_to_canvas(pick, canvas.shape[2], canvas.shape[1],
                                       fit_mode=masking.get("fit_mode", "crop"))
        else:
            m = _refmod.refine_cutout(
                _refmod.cutout_masks(canvas, backend=masking.get("backend", "auto_rembg")),
                canvas)
        if m.shape[0] not in (1, canvas.shape[0]):
            m = m[:1]
        kept = float(m.mean())
        print(f"[{TAG}] RefMod source {index + 1}: subject covers {kept:.0%} of "
              f"the canvas", flush=True)
        if kept < 0.02:
            print(f"[{TAG}] RefMod source {index + 1}: the mask keeps almost "
                  f"nothing, so the backdrop is left as it was", flush=True)
            return canvas
        if float(masking.get("crop_margin") or 0.0) > 0.0:
            canvas, m = _refmod.crop_to_subject(canvas, m, margin=float(masking["crop_margin"]))
        return _refmod.isolate_subject(
            canvas, m, masking["retention"], mode=masking.get("bg_mode", "blur_bg"))

    def _encode_audio_member(self, audio_vae, audio_obj, voice_name, voice_win):
        if audio_vae is None:
            return None
        wav_dict = audio_obj
        if wav_dict is None and voice_name:
            v_start, v_end = voice_win
            wav_dict, _auto = _media.load_voice(voice_name, start=v_start, end=v_end)
        if wav_dict is None:
            return None
        try:
            from comfy_extras.nodes_minimax_h3 import _encode_ref_audio
            z, ref_t = _encode_ref_audio(audio_vae, wav_dict)
            return {"kind": "audio", "latent": z, "ref_audio_t": ref_t,
                    "sample_rate": int(getattr(audio_vae, "audio_sample_rate", 32000)),
                    "name": voice_name or "voice"}
        except Exception as exc:
            print(f"[{TAG}] RefMod audio encode skipped: {exc!r}", flush=True)
            return None

    def _encode_plan(self, vae, stills, clip, masking=None, fit_mode="crop",
                     separate=True, max_tokens=0):
        """Encode stills/clip either as separate v5 bundle members (native aspect) or stacked."""
        count = len(stills) + (1 if clip else 0)
        if separate:
            members = []
            shapes = []
            for i, name in enumerate(stills):
                px = _media.load_image(name)
                if px is None:
                    _refmod._fail(_refmod.source_problem(name, ("image",)) or f"mod_plan source {name} could not be read")
                sw, sh = _refmod.canvas_size(px)
                canvas = self._isolated(_refmod.to_canvas(px, sw, sh, fit_mode=fit_mode), i, count, masking)
                # Ensure 32px dimensions if crop_to_subject narrowed canvas
                cw, ch = _refmod.canvas_size(canvas)
                if (cw, ch) != (int(canvas.shape[2]), int(canvas.shape[1])):
                    canvas = _refmod.to_canvas(canvas, cw, ch, fit_mode="crop")
                z = vae.encode(canvas)
                self._check_encode(z, name)
                z = _refmod.fit_token_budget(z, max_tokens, name)
                looks = _refmod.looks_from(canvas[:1])
                members.append({
                    "kind": "image",
                    "name": name,
                    "latent": z,
                    "looks": looks,
                    "source": "image",
                    "source_shape": "x".join(str(int(n)) for n in z.shape[2:]),
                })
                shapes.append(f"{name} {int(canvas.shape[2])}x{int(canvas.shape[1])}")
            if clip:
                px = _media.load_video(clip["file"], max_frames=clip["frames"] or None,
                                       start=clip["start"], end=clip["end"])
                if px is None:
                    _refmod._fail(_refmod.source_problem(clip['file'], ("video",)) or f"mod_plan source {clip['file']} could not be read")
                px = _refmod.snap_video_frames(px)
                vw, vh = _refmod.canvas_size(px)
                canvas = self._isolated(_refmod.to_canvas(px, vw, vh, fit_mode=fit_mode), count - 1, count, masking)
                z = vae.encode(canvas)
                self._check_encode(z, clip["file"])
                z = _refmod.fit_token_budget(z, max_tokens, clip["file"])
                looks = _refmod.looks_from(canvas, clip=True)
                members.append({
                    "kind": "video",
                    "name": clip["file"],
                    "latent": z,
                    "looks": looks,
                    "source": "video",
                    "source_shape": "x".join(str(int(n)) for n in z.shape[2:]),
                })
                shapes.append(f"{clip['file']} {int(px.shape[0])}f")
            print(f"[{TAG}] RefMod v5 separate members: {', '.join(shapes)}", flush=True)
            return members

        first = _media.load_image(stills[0]) if stills else None
        if first is None:
            first = _media.load_video(clip["file"], max_frames=1,
                                      start=clip["start"], end=clip["end"])
            if first is None:
                _refmod._fail(_refmod.source_problem(clip['file'], ("video",)) or f"mod_plan source {clip['file']} could not be read")
        tw, th = _refmod.canvas_size(first)
        parts, shapes, looks = [], [], []
        for i, name in enumerate(stills):
            px = _media.load_image(name)
            if px is None:
                _refmod._fail(_refmod.source_problem(name, ("image",)) or f"mod_plan source {name} could not be read")
            canvas = self._isolated(_refmod.to_canvas(px, tw, th, fit_mode=fit_mode), i, count, masking)
            if (int(canvas.shape[2]), int(canvas.shape[1])) != (tw, th):
                canvas = _refmod.to_canvas(canvas, tw, th, fit_mode=fit_mode)
            z = vae.encode(canvas)
            self._check_encode(z, name)
            parts.append(z)
            looks.append(_refmod.looks_from(canvas[:1]))
            shapes.append(f"{name} 1f")
        if clip:
            px = _media.load_video(clip["file"], max_frames=clip["frames"] or None,
                                   start=clip["start"], end=clip["end"])
            if px is None:
                _refmod._fail(_refmod.source_problem(clip['file'], ("video",)) or f"mod_plan source {clip['file']} could not be read")
            px = _refmod.snap_video_frames(px)
            canvas = self._isolated(_refmod.to_canvas(px, tw, th, fit_mode=fit_mode), count - 1,
                                    count, masking)
            if (int(canvas.shape[2]), int(canvas.shape[1])) != (tw, th):
                canvas = _refmod.to_canvas(canvas, tw, th, fit_mode=fit_mode)
            z = vae.encode(canvas)
            self._check_encode(z, clip["file"])
            parts.append(z)
            looks.append(_refmod.looks_from(canvas, clip=True))
            shapes.append(f"{clip['file']} {int(px.shape[0])}f")
        print(f"[{TAG}] RefMod sources on a {tw}x{th} canvas ({fit_mode}): "
              f"{', '.join(shapes)}", flush=True)
        return _refmod.stack_latents(parts, "mod_plan"), torch.cat(looks, dim=0)

    def _check_encode(self, z, where):
        if z.ndim != 5:
            _refmod._fail(
                f"H3 VAE encode of {where} returned {tuple(z.shape)}, expected "
                f"[1,24,T,H,W]. Connect the H3 video VAE.")

    def build(self, vae, name, mod_plan="", images=None, video=None, max_tokens=0,
              subfolder="", save=True, build="stop", description="",
              subject_mask="off", background_retention=0.0,
              layout="separate_pictures", role="identity", default_step_curve="full",
              fit_mode="crop", background_mode="blur_bg", crop_margin=0.0,
              mask=None, audio=None, audio_vae=None, **_retired):
        # `_retired` takes `mode`, `pool`, `latent_frames` and `refine_steps`
        # from a prompt saved before training mode was removed. Pooling
        # averaged a face away; encode is the only mode that ever worked.
        description = _refmod._clean_desc_text(description)
        stem = name
        folder = (subfolder or "").strip().replace("\\", "/").strip("/")
        if folder:
            if any(p in ("", ".", "..") for p in folder.split("/")):
                raise ValueError(f"{TAG}: subfolder {subfolder!r} leaves the refmods folder")
            stem = f"{folder}/{name}"
        if str(build) != "start":
            print(f"[{TAG}] RefMod builder is stopped. {stem} was not written.",
                  flush=True)
            try:
                shown = _refmod._clean_name(stem) or str(name or "").strip()
            except ValueError:
                shown = str(name or "").strip()
            return (shown,)

        stills, clip, voice = _refmod.parse_mod_plan(mod_plan)
        if voice:
            problem = _refmod.source_problem(voice, ("audio",))
            if problem:
                _refmod._fail(problem)
        v_win = _refmod.voice_window(mod_plan) if voice else (0.0, 0.0)

        mask_mode = str(subject_mask or "off").strip().lower()
        is_auto_mask = mask_mode in ("auto", "auto_rembg", "auto_sam")
        masking, mask_meta = None, {}
        retention = float(background_retention or 0.0)
        if mask is not None or is_auto_mask:
            if mask is not None:
                wired = mask if mask.dim() == 3 else mask.unsqueeze(0)
                if stills or clip:
                    count = len(stills) + (1 if clip else 0)
                    ok = wired.shape[0] in (1, count) or (
                        count == 1 and clip and not stills)
                else:
                    count = 1
                    ok = True
                if not ok:
                    raise ValueError(
                        f"{TAG}: the mask batch has {wired.shape[0]} masks for "
                        f"{count} sources. Wire one mask for all of them, or "
                        f"one per source, stills then the clip.")
                if is_auto_mask:
                    print(f"[{TAG}] a mask is wired, so subject_mask={mask_mode} is not run", flush=True)
                masking = {"wired": wired, "retention": retention, "fit_mode": fit_mode,
                           "bg_mode": background_mode, "crop_margin": float(crop_margin or 0.0)}
                mask_meta = {"source": "wired", "fill": background_mode,
                             "background_retention": retention, "crop_margin": float(crop_margin or 0.0)}
            else:
                backend = "auto_sam" if mask_mode == "auto_sam" else "auto_rembg"
                masking = {"wired": None, "retention": retention, "backend": backend,
                           "fit_mode": fit_mode, "bg_mode": background_mode,
                           "crop_margin": float(crop_margin or 0.0)}
                mask_meta = {"source": backend, "model": _refmod.CUTOUT_MODEL,
                             "fill": background_mode, "background_retention": retention,
                             "crop_margin": float(crop_margin or 0.0)}
            if retention >= 1.0:
                print(f"[{TAG}] background_retention=1 keeps the whole "
                      f"background, so the mask changes nothing", flush=True)

        plan_used = {}
        if stills or clip or voice:
            plan_used = {"stills": list(stills)}
            if clip:
                plan_used["clip"] = dict(clip)
            if voice:
                v_start, v_end = v_win
                plan_used["voice"] = ({"file": voice, "start": v_start, "end": v_end}
                                      if v_start or v_end else voice)
            if images is not None or video is not None:
                print(f"[{TAG}] mod_plan names sources, so the images/video "
                      f"sockets are ignored", flush=True)

        audio_member = self._encode_audio_member(audio_vae, audio, voice, v_win)
        want_separate = (str(layout or "separate_pictures").strip() == "separate_pictures"
                         and (len(stills) > 1 or audio_member is not None or (stills and clip)))

        if (stills or clip) and want_separate:
            vis_members = self._encode_plan(
                vae, stills, clip, masking, fit_mode=fit_mode, separate=True, max_tokens=max_tokens)
            if audio_member is not None:
                vis_members.append(audio_member)
            if save:
                root = _refmod.register_folder()
                written = _refmod.save_v5_bundle(
                    root, stem, vis_members,
                    description=description, concept_type=role,
                    default_step_curve=default_step_curve,
                    plan=plan_used, mask=mask_meta, compact_png=True,
                )
                tok = sum(_refmod.frame_tokens(m["latent"].shape[4] * 16, m["latent"].shape[3] * 16) * m["latent"].shape[2]
                          for m in vis_members if m["kind"] != "audio")
                print(f"[{TAG}] wrote v5 RefMod bundle {written} ({len(vis_members)} member(s), "
                      f"{tok} visual tokens, role={role}, curve={default_step_curve}"
                      + (", audio latent" if audio_member else (f", voice {voice}" if voice else "")) + ")",
                      flush=True)
                return (written,)
            return (_refmod._clean_name(stem),)

        if stills or clip:
            full, looks = self._encode_plan(
                vae, stills, clip, masking, fit_mode=fit_mode, separate=False)
            source = "video" if clip else ("image" if len(stills) == 1 else "images")
        else:
            if images is None and video is None:
                raise ValueError(
                    f"{TAG}: add a still or a clip in the RefMod panel, or "
                    f"connect the images / video sockets.")
            if images is not None and video is not None:
                raise ValueError(f"{TAG}: connect images or a video, not both.")
            if video is not None:
                frames = _refmod.snap_video_frames(video)
                source = "video"
            else:
                frames = images[:1]
                source = "image"
            canvas = self._isolated(_refmod.fit_canvas(frames, fit_mode=fit_mode), 0, 1, masking)
            full = vae.encode(canvas)
            self._check_encode(full, stem)
            looks = _refmod.looks_from(canvas, clip=video is not None)

        source_shape = "x".join(str(int(n)) for n in full.shape[2:])
        latent = _refmod.fit_token_budget(full, max_tokens, name)
        kind = "image" if int(latent.shape[2]) == 1 else "video"
        tokens = (int(latent.shape[2]) * (int(latent.shape[3]) // 2)
                  * (int(latent.shape[4]) // 2))
        if audio_member is not None:
            vis_members = [{
                "kind": kind, "name": stem, "latent": latent, "looks": looks,
                "source": source, "source_shape": source_shape,
            }, audio_member]
            if save:
                root = _refmod.register_folder()
                written = _refmod.save_v5_bundle(
                    root, stem, vis_members, description=description, concept_type=role,
                    default_step_curve=default_step_curve, plan=plan_used, mask=mask_meta,
                    compact_png=True)
                print(f"[{TAG}] wrote v5 RefMod bundle {written} ({kind} + audio latent, {tokens} visual tokens)", flush=True)
                return (written,)
            return (_refmod._clean_name(stem),)

        meta = _refmod.metadata_for(
            stem, kind, latent, "encode", source, source_shape, "encode", 0,
            plan=plan_used, description=description, mask=mask_meta,
            looks=int(looks.shape[0]), concept_type=role, default_step_curve=default_step_curve)
        if save:
            root = _refmod.register_folder()
            written = _refmod.save_latent(root, stem, latent, meta, looks=looks)
            print(f"[{TAG}] wrote RefMod {written} ({kind}, {meta['latent_t']}x"
                  f"{meta['latent_h']}x{meta['latent_w']}, {tokens} tokens, "
                  f"{meta['looks']} kept for Qwen, role={role}"
                  + (f", voice {voice}" if voice else "") + ")",
                  flush=True)
            return (written,)
        print(f"[{TAG}] RefMod {stem} was not saved (save is off)", flush=True)
        return (_refmod._clean_name(stem),)


class HTCRefModBuilder(io.ComfyNode, _HTCRefModBuilderImpl):
    """V3 schema for HTCRefModBuilder; the implementation lives in _HTCRefModBuilderImpl.

    Also inherits _HTCRefModBuilderImpl so existing callers of the V1 API (HTCRefModBuilder().build(...),
    HTCRefModBuilder.<helper>) keep working; core sees only the V3 hooks below."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id='HTCRefModBuilder',
            display_name='HTC RefMod Builder',
            category="Hand Tie Clips",
            description="Retired from the node menu — use the RefMod tab inside HandTieClips. Kept for legacy workflows & Studio background builds.",
            is_output_node=True,
            is_deprecated=True,
            inputs=[
                io.Vae.Input('vae', tooltip="The H3 video VAE."),
                io.String.Input(
                    'name',
                    default="hero",
                    tooltip="File name for the RefMod under models/refmods. Pick it on a REFS row by "
                                "this name.",
                ),
                io.String.Input(
                    'mod_plan',
                    optional=True,
                    default="",
                    multiline=True,
                    tooltip="The stills, clip and voice for this RefMod, written by the panel.",
                ),
                io.Image.Input(
                    'images',
                    optional=True,
                    tooltip="Optional still to build from, instead of the panel.",
                ),
                io.Image.Input(
                    'video',
                    optional=True,
                    tooltip="Optional clip to build from, instead of the panel.",
                ),
                io.Int.Input(
                    'max_tokens',
                    optional=True,
                    default=0,
                    min=0,
                    max=1048576,
                    tooltip="Memory guard. Above this, near-duplicate frames are dropped. 0 is no "
                                "limit.",
                ),
                io.String.Input(
                    'subfolder',
                    optional=True,
                    default="",
                    tooltip="Optional folder under models/refmods.",
                ),
                io.Boolean.Input(
                    'save',
                    optional=True,
                    default=True,
                    tooltip="Write the file. Off only reports the name.",
                ),
                io.Combo.Input(
                    'build',
                    options=["stop", "start"],
                    optional=True,
                    default="stop",
                    tooltip="start builds the RefMod on this queue. stop leaves it alone, so the chain "
                                "can run without rebuilding.",
                ),
                io.String.Input(
                    'description',
                    optional=True,
                    default="",
                    tooltip="One sentence describing what the RefMod shows. Fills an empty description "
                                "on a REFS row.",
                ),
                io.Combo.Input(
                    'subject_mask',
                    options=["off", "auto_rembg", "auto_sam", "auto"],
                    optional=True,
                    default="off",
                    tooltip="auto_rembg or auto_sam cuts the subject out of each source and fills/blurs "
                                "the background before encoding. A wired mask wins.",
                ),
                io.Float.Input(
                    'background_retention',
                    optional=True,
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.05,
                    tooltip="How much background a mask keeps. 0 removes/blurs it; 1 keeps it all.",
                ),
                io.Combo.Input(
                    'layout',
                    options=["separate_pictures", "stacked_video"],
                    optional=True,
                    default="separate_pictures",
                    tooltip="separate_pictures (v5 bundle, recommended): each still keeps its own natural "
                                "aspect ratio and binds as an independent <Picture N> (never eats a <Video> slot). "
                                "stacked_video: concatenates sources onto one canvas along time.",
                ),
                io.Combo.Input(
                    'role',
                    options=list(_refmod.CONCEPT_ROLES),
                    optional=True,
                    default="identity",
                    tooltip="What this RefMod represents (identity, wardrobe, bodyshape, helper, pose_motion, background, style).",
                ),
                io.Combo.Input(
                    'default_step_curve',
                    options=list(_refmod.STEP_CURVES),
                    optional=True,
                    default="full",
                    tooltip="Default denoising curve (full, early_lock for helpers/bodyshape, late_detail, fade, mid_peak).",
                ),
                io.Combo.Input(
                    'fit_mode',
                    options=["crop", "pad", "stretch"],
                    optional=True,
                    default="crop",
                    tooltip="How mismatched ratios fit a shared video canvas (crop preserves proportions, never squishes).",
                ),
                io.Combo.Input(
                    'background_mode',
                    options=["blur_bg", "pull_push", "neutral_gray"],
                    optional=True,
                    default="blur_bg",
                    tooltip="How masked background pixels are handled: blur_bg (zero color halos), pull_push, or neutral_gray.",
                ),
                io.Float.Input(
                    'crop_margin',
                    optional=True,
                    default=0.0,
                    min=0.0,
                    max=2.5,
                    step=0.05,
                    tooltip="Optional subject-centered auto-crop margin when masking is active (e.g. 1.6x; 0 = keep full framing).",
                ),
                io.Mask.Input(
                    'mask',
                    optional=True,
                    tooltip="Optional mask of the subject, white = keep. One for all sources, or one "
                                              "per source.",
                ),
                io.Audio.Input(
                    'audio',
                    optional=True,
                    tooltip="Optional voice/sound reference to embed in a v5 bundle (needs audio_vae).",
                ),
                io.Vae.Input(
                    'audio_vae',
                    optional=True,
                    tooltip="Optional H3 Audio VAE to pre-encode the RefMod voice into a portable v5 bundle.",
                ),
            ],
            outputs=[
                io.String.Output(display_name='name'),
            ],
        )

    @classmethod
    def execute(cls, **kwargs):
        result = _HTCRefModBuilderImpl().build(**kwargs)
        if isinstance(result, dict):
            return io.NodeOutput.from_dict(result)
        return io.NodeOutput(*result) if result is not None else io.NodeOutput()

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return _HTCRefModBuilderImpl.IS_CHANGED(**_v3_accepted(_HTCRefModBuilderImpl.IS_CHANGED, kwargs))


NODE_CLASS_MAPPINGS = {"HTCRefModBuilder": HTCRefModBuilder}
NODE_DISPLAY_NAME_MAPPINGS = {"HTCRefModBuilder": "HTC RefMod Builder"}
