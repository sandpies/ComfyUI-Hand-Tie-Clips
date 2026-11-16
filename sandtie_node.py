"""SandTiePromptRig — Dual-Mode MiniMax H3 Prompt & Conditioning Rig for ComfyUI."""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re

from comfy_api.latest import io

from . import media as _media
from . import standard as _std
from .htc_sandtie import finisher as _st_fin
from .htc_sandtie import refs as _st_refs
from .htc_sandtie import writer as _st_writer

TAG = "HandTieClips-SandTie"

WIRE_MODES = [
    "Prompt Only -> Stock H3 Node",
    "Direct H3 Conditioning (+ CLIP/VAE)",
]

H3_FORMATS = [
    "MiniMax H3 Auto (Ref2VA / T2VA)",
    "MiniMax H3 I2VA (First Frame)",
    "MiniMax H3 FL2VA (First + Last Frame)",
    "MiniMax H3 L2VA (Last Frame)",
    "Start Frame Prep (Still Image Prompt)",
    "Storyboard Beats Only",
]

_FMT_TO_CODE = {
    "MiniMax H3 Auto (Ref2VA / T2VA)": "h3_auto",
    "MiniMax H3 I2VA (First Frame)": "h3_i2va",
    "MiniMax H3 FL2VA (First + Last Frame)": "h3_fl2va",
    "MiniMax H3 L2VA (Last Frame)": "h3_l2va",
    "Start Frame Prep (Still Image Prompt)": "h3_keyframe",
    "Storyboard Beats Only": "h3_beats",
}

WRITE_MODES = [
    "LLM + Double-Knot (2-Pass)",
    "LLM 1-Pass Quick Tie",
    "Instant CPU Tie (0 VRAM)",
]

ASPECT_RATIOS = {
    "21:9 landscape": (21, 9),
    "16:9 landscape": (16, 9),
    "3:2 landscape": (3, 2),
    "4:3 landscape": (4, 3),
    "5:4 landscape": (5, 4),
    "1:1 square": (1, 1),
    "4:5 portrait": (4, 5),
    "3:4 portrait": (3, 4),
    "2:3 portrait": (2, 3),
    "9:16 portrait": (9, 16),
    "9:21 portrait": (9, 21),
}
ASPECTS = list(ASPECT_RATIOS)
DEFAULT_ASPECT = "16:9 landscape"
DURATIONS = ["5 s", "6 s", "8 s", "10 s", "12 s", "13 s", "14 s", "15 s"]
FPS = 24
CANVAS_MULTIPLE = 32
CANVAS_AREA_CAP = 768 * 1344
BASE_SHORT_EDGE = 768


def _parse_aspect_ratio(aspect: str) -> tuple[int, int]:
    raw = str(aspect or DEFAULT_ASPECT).strip()
    if raw in ASPECT_RATIOS:
        return ASPECT_RATIOS[raw]
    m = re.search(r"(\d+)\s*:\s*(\d+)", raw)
    if m:
        rw, rh = int(m.group(1)), int(m.group(2))
        if rw > 0 and rh > 0:
            return rw, rh
    if re.search(r"portrait|vertical", raw, re.I):
        return (9, 16)
    return ASPECT_RATIOS[DEFAULT_ASPECT]


def _aspect_short_label(aspect: str) -> str:
    rw, rh = _parse_aspect_ratio(aspect)
    return f"{rw}:{rh}"


def _aspect_from_dims(w: int, h: int) -> str:
    g = math.gcd(int(w), int(h)) or 1
    rw, rh = int(w) // g, int(h) // g
    target = float(w) / float(h)
    best_lbl, best_err = None, 1e9
    for lbl, (aw, ah) in ASPECT_RATIOS.items():
        err = abs((aw / float(ah)) - target)
        if err < best_err:
            best_err = err
            best_lbl = lbl
    if best_lbl and best_err <= 0.04:
        aw, ah = ASPECT_RATIOS[best_lbl]
        return f"{aw}:{ah}"
    return f"{rw}:{rh}"


def _parse_dur_seconds(label: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)", str(label or ""))
    if m:
        return max(2.0, min(20.0, float(m.group(1))))
    return 10.0


def _snap_dim(px: int) -> int:
    return max(CANVAS_MULTIPLE, int(round(int(px) / CANVAS_MULTIPLE)) * CANVAS_MULTIPLE)


def _resolve_canvas_size(aspect: str, width: int, height: int) -> tuple[int, int]:
    if int(width or 0) > 0 and int(height or 0) > 0:
        return _snap_dim(int(width)), _snap_dim(int(height))
    rw, rh = _parse_aspect_ratio(aspect)
    ratio = float(rw) / float(rh)
    short = float(BASE_SHORT_EDGE)
    w, h = (short * ratio, short) if ratio >= 1.0 else (short, short / ratio)
    if w * h > CANVAS_AREA_CAP:
        scale = math.sqrt(float(CANVAS_AREA_CAP) / (w * h))
        w, h = w * scale, h * scale
    return _snap_dim(int(round(w))), _snap_dim(int(round(h)))


def _align_frames(dur_s: float) -> int:
    n = max(5, int(round(float(dur_s) * FPS)))
    while n % 17 != 5:
        n += 1
    return n


def _split_h3_sections(block: str) -> tuple[str, str, str]:
    """Extract (storyboard_or_desc, soundscape, music) cleanly from an H3 prompt block."""
    t = str(block or "").strip()
    if not t:
        return "", "", ""
    desc = _std._field(t, "detailed_description:") or _std._field(t, "integrated_multimodal_description:") or t
    snd = _std._field(t, "overall_soundscape:") or ""
    mus = _std._field(t, "non_diegetic_music:") or ""
    return desc.strip(), snd.strip(), mus.strip()


def _parse_rig_state(raw: str) -> dict:
    try:
        doc = json.loads(str(raw or "{}") or "{}")
        return doc if isinstance(doc, dict) else {}
    except Exception:
        return {}


def _save_tensor_ref_if_needed(img_tensor, prefix: str) -> str:
    """Persist a wired IMAGE tensor to `<input>/h3_refs/` by content hash so Eye Scan can reference it."""
    if img_tensor is None:
        return ""
    try:
        import numpy as np
        from PIL import Image
        arr = img_tensor
        if hasattr(arr, "detach"):
            arr = arr[0].detach().cpu().numpy()
        arr = (np.clip(arr, 0.0, 1.0) * 255.0).astype(np.uint8)
        h = hashlib.sha1(arr.tobytes()).hexdigest()[:12]
        fname = f"sandtie_{prefix}_{h}.png"
        dest_dir = _media.refs_dir(create=True)
        dest_path = os.path.join(dest_dir, fname)
        if not os.path.isfile(dest_path):
            Image.fromarray(arr).save(dest_path, format="PNG")
        return fname
    except Exception:
        return ""


def _ordered_autogrow_items(group_dict: dict | None, prefix: str, limit: int) -> list[tuple[int, object]]:
    """Extract ordered `(slot_1based, value)` pairs from an Autogrow dict (`ref_image_1..9`, etc.)."""
    out: list[tuple[int, object]] = []
    if not isinstance(group_dict, dict):
        return out
    rows: list[tuple[int, object]] = []
    for k, v in group_dict.items():
        if v is None:
            continue
        m = re.search(r"(\d+)$", str(k))
        idx = int(m.group(1)) if m else len(rows) + 1
        rows.append((idx, v))
    rows.sort(key=lambda x: x[0])
    for idx, v in rows[:limit]:
        out.append((idx, v))
    return out


def _build_wired_ref_plan(ref_plan_json: str, wired_imgs: list[tuple[int, object]]) -> str:
    """Merge any canvas-wired `ref_image_1..9` sockets into `ref_plan_json` cleanly if not already listed."""
    raw = str(ref_plan_json or "").strip()
    try:
        doc = json.loads(raw) if raw else {}
    except Exception:
        doc = {}
    if not isinstance(doc, dict):
        doc = {}
    refs = list(doc.get("refs") or [])
    by_slot = {int(r.get("slot") or 0): r for r in refs if isinstance(r, dict)}
    changed = False
    for slot_idx, tensor in wired_imgs:
        if tensor is None:
            continue
        existing = by_slot.get(slot_idx)
        if existing and str(existing.get("file") or "").strip():
            continue
        fname = _save_tensor_ref_if_needed(tensor, f"ref{slot_idx}")
        if fname:
            refs = [r for r in refs if int(r.get("slot") or 0) != slot_idx]
            refs.append({
                "slot": slot_idx,
                "tag": f"subject{slot_idx}",
                "file": fname,
                "subject": slot_idx,
                "retention": "fully_preserved",
                "desc": "",
            })
            changed = True
    if not changed:
        return raw
    doc["refs"] = sorted(refs, key=lambda r: int(r.get("slot") or 0))
    doc.setdefault("subjects", {})
    return json.dumps(doc, separators=(",", ":"))


def _collect_conditioning_media(
    ref_plan_json: str,
    wired_imgs: list[tuple[int, object]],
    wired_vids: list[tuple[int, object]],
    wired_auds: list[tuple[int, object]],
) -> tuple[dict | None, dict | None, dict | None]:
    """Build ordered `ref_images`, `ref_videos`, `ref_audios` dicts merging Reference Bible files + canvas wires."""
    img_by_slot: dict[int, object] = {idx: t for idx, t in wired_imgs if t is not None}
    ordered_imgs: list[object] = []
    used_slots: set[int] = set()
    voice_files: list[str] = []

    try:
        doc = json.loads(str(ref_plan_json or "") or "{}")
    except Exception:
        doc = {}
    refs = sorted(
        [r for r in (doc.get("refs") or []) if isinstance(r, dict)],
        key=lambda r: int(r.get("slot") or 99),
    )

    for r in refs:
        if len(ordered_imgs) >= 9:
            break
        sl = int(r.get("slot") or 0)
        tensor = img_by_slot.get(sl) if sl >= 1 else None
        if tensor is None and str(r.get("file") or "").strip():
            fname = str(r["file"]).strip()
            if str(r.get("source") or "").strip().lower() == "refmod":
                try:
                    from . import refmod as _refmod  # noqa: PLC0415
                    vis = _refmod.load_bundle_visuals(fname, members_filter=r.get("members"))
                    if vis and vis[0].get("looks") is not None:
                        px = vis[0]["looks"][:1].float() / 255.0
                        tensor = px
                except Exception:
                    tensor = None
                if tensor is None:
                    try:
                        import folder_paths as _fp  # noqa: PLC0415
                        import numpy as _np  # noqa: PLC0415
                        from PIL import Image as _PILImage  # noqa: PLC0415
                        import io as _io  # noqa: PLC0415
                        from safetensors import safe_open as _safe_open  # noqa: PLC0415
                        import torch as _torch  # noqa: PLC0415
                        rel = fname.replace("/", os.sep) + ".safetensors"
                        for rd in ([os.path.join(_fp.models_dir, "refmods")]):
                            rp = os.path.join(rd, rel)
                            if os.path.isfile(rp):
                                with _safe_open(rp, framework="pt", device="cpu") as sf:
                                    ks = set(sf.keys())
                                    lk = next((k for k in ("looks", "looks_0", "refmod.looks") if k in ks), None)
                                    if lk:
                                        lt = sf.get_tensor(lk)
                                        if lt.ndim == 3:
                                            lt = lt.unsqueeze(0)
                                        tensor = lt[:1].float() / 255.0
                                    else:
                                        ek = next((k for k in sorted(ks) if k.startswith("enc_")), None)
                                        if ek:
                                            raw_b = sf.get_tensor(ek).numpy().tobytes()
                                            with _PILImage.open(_io.BytesIO(raw_b)) as pim:
                                                tensor = _torch.from_numpy(_np.asarray(pim.convert("RGB"), dtype=_np.float32) / 255.0).unsqueeze(0)
                                break
                    except Exception:
                        tensor = None
                if tensor is None:
                    # Same rule as a missing image: dropping the row silently would shift
                    # every later <Picture N> the compiled prompt cites.
                    raise FileNotFoundError(
                        f"{TAG}: Reference Bible RefMod '{fname}' has no readable picture "
                        "(no file in models/refmods/, or no kept looks/enc_ photo in it). "
                        "Rebuild it with kept photos, or remove it from the rail."
                    )
            else:
                tensor = _media.load_image(fname, cap_mp=float(r.get("mp") or 0.0))
                if tensor is None:
                    raise FileNotFoundError(
                        f"{TAG}: Reference Bible image '{fname}' was not found in input/h3_refs/. "
                        "Re-upload it in SandTie Studio or remove it from the rail."
                    )
        if tensor is not None:
            ordered_imgs.append(tensor)
            if sl >= 1:
                used_slots.add(sl)
        vf = str(r.get("voice") or "").strip()
        if vf and vf not in voice_files:
            voice_files.append(vf)

    for sl in sorted(img_by_slot):
        if sl in used_slots or len(ordered_imgs) >= 9:
            continue
        ordered_imgs.append(img_by_slot[sl])

    ref_images = {f"ref_image_{i + 1}": t for i, t in enumerate(ordered_imgs[:9])} or None

    ref_videos = {f"ref_video_{i + 1}": t for i, (_s, t) in enumerate(wired_vids[:3]) if t is not None} or None

    aud_items: list[dict] = []
    for _s, a in wired_auds[:3]:
        if a is not None:
            aud_items.append(a)
    for vf in voice_files:
        if len(aud_items) >= 3:
            break
        loaded = _media.load_audio(vf)
        if loaded is None:
            raise FileNotFoundError(
                f"{TAG}: Reference Bible voice audio '{vf}' was not found in input/h3_refs/. "
                "Update or clear the voice field in SandTie Studio."
            )
        aud_items.append(loaded)
    ref_audios = {f"ref_audio_{i + 1}": a for i, a in enumerate(aud_items[:3])} or None
    return ref_images, ref_videos, ref_audios


def _downstream_cond_or_latent_wired(dynprompt, unique_id) -> bool:
    """Detect whether output slot 1 (`positive`) or 2 (`latent`) is linked in the active ComfyUI prompt."""
    if dynprompt is None or not unique_id:
        return False
    try:
        orig = dynprompt.get_original_prompt() if hasattr(dynprompt, "get_original_prompt") else {}
        uid = str(unique_id)
        for node_info in (orig or {}).values():
            inputs = (node_info or {}).get("inputs") or {}
            for val in inputs.values():
                if isinstance(val, (list, tuple)) and len(val) >= 2 and str(val[0]) == uid and int(val[1]) in (1, 2):
                    return True
    except Exception:
        pass
    return False


class SandTiePromptRig(io.ComfyNode):
    """Dual-mode MiniMax H3 Prompt & Conditioning Rig (`Prompt Only` ⇄ `Direct H3 Conditioning`)."""

    @classmethod
    def define_schema(cls):
        ref_imgs_tpl = io.Autogrow.TemplateNames(
            input=io.Image.Input(
                "ref_image",
                tooltip="Canvas reference image (auto-grows up to 9; merges with Reference Bible).",
            ),
            names=[f"ref_image_{i}" for i in range(1, 10)],
            min=0,
        )
        ref_vids_tpl = io.Autogrow.TemplateNames(
            input=io.Image.Input(
                "ref_video",
                tooltip="Reference video frames at 24 fps (auto-grows up to 3).",
            ),
            names=[f"ref_video_{i}" for i in range(1, 4)],
            min=0,
        )
        ref_auds_tpl = io.Autogrow.TemplateNames(
            input=io.Audio.Input(
                "ref_audio",
                tooltip="Standalone voice or audio reference (auto-grows up to 3).",
            ),
            names=[f"ref_audio_{i}" for i in range(1, 4)],
            min=0,
        )
        return io.Schema(
            node_id="SandTiePromptRig",
            display_name="SandTie PromptRig (H3)",
            category="Hand Tie Clips",
            description=(
                "Dual-mode MiniMax H3 Prompt & Conditioning Rig. "
                "In Prompt Only mode (0 VRAM), connect `prompt` straight into MiniMaxH3ReferenceToVideo / ImageToVideo. "
                "Switch wire_mode to Direct H3 Conditioning to encode Reference Bible + canvas refs into `positive` + `latent`."
            ),
            inputs=[
                io.DynamicCombo.Input(
                    "wire_mode",
                    options=[
                        io.DynamicCombo.Option(WIRE_MODES[0], []),
                        io.DynamicCombo.Option(WIRE_MODES[1], [
                            io.Clip.Input("clip", tooltip="MiniMax H3 text encoder (Qwen3-VL) for Direct Conditioning mode."),
                            io.Vae.Input("vae", optional=True, tooltip="MiniMax H3 Video VAE (needed when encoding visual refs or keyframes)."),
                            io.Vae.Input("audio_vae", optional=True, tooltip="MiniMax H3 Audio VAE (needed when encoding voice audio references)."),
                            io.Combo.Input(
                                "ref_image_size", options=["match", "max"], default="match", socketless=True,
                                tooltip="match keeps reference aspect ratio inside H3 native caps; max scales references up to full 2048px reference resolution.",
                            ),
                            io.Int.Input("width", default=0, min=0, max=4096, step=32,
                                         tooltip="Output canvas width in pixels (0 = auto-solved from aspect ratio at H3 native 768p budget)."),
                            io.Int.Input("height", default=0, min=0, max=4096, step=32,
                                         tooltip="Output canvas height in pixels (0 = auto-solved from aspect ratio at H3 native 768p budget)."),
                        ]),
                    ],
                    tooltip="Prompt Only outputs compiled text (0 VRAM) for stock H3 nodes. Direct H3 Conditioning also encodes Reference Bible + canvas wires into positive + latent.",
                ),
                io.Combo.Input(
                    "h3_format", options=H3_FORMATS, default=H3_FORMATS[0], socketless=True,
                    tooltip="Target MiniMax H3 task structure: Ref2VA/T2VA, First Frame (I2VA), First+Last (FL2VA), Last Frame (L2VA), Start Still Prep, or Beats Only.",
                ),
                io.Autogrow.Input(
                    "ref_images", optional=True, template=ref_imgs_tpl,
                    tooltip="Optional canvas image references (auto-grows up to 9); merged cleanly with Reference Bible slots.",
                ),
                io.Autogrow.Input(
                    "ref_videos", optional=True, template=ref_vids_tpl,
                    tooltip="Optional 24 fps reference video clips (auto-grows up to 3) for style or motion guidance.",
                ),
                io.Autogrow.Input(
                    "ref_audios", optional=True, template=ref_auds_tpl,
                    tooltip="Optional voice timbre or audio references (auto-grows up to 3) in Direct Conditioning mode.",
                ),
                io.Image.Input("first_frame", optional=True, tooltip="Optional first-frame keyframe anchor (I2VA / FL2VA)."),
                io.Image.Input("last_frame", optional=True, tooltip="Optional last-frame keyframe anchor (FL2VA / L2VA)."),
                io.Combo.Input(
                    "write_mode", options=WRITE_MODES, default=WRITE_MODES[0], socketless=True,
                    tooltip="Writing engine: LLM + Double-Knot (2-pass planner + H3 compiler), LLM 1-Pass Quick Tie, or Instant CPU Tie (0 VRAM, rule-based).",
                ),
                io.Combo.Input(
                    "aspect", options=ASPECTS, default=DEFAULT_ASPECT, socketless=True,
                    tooltip="Full 11-ratio MiniMax H3 aspect suite (21:9 ultrawide through 1:1 square to 9:21 vertical).",
                ),
                io.Combo.Input(
                    "duration", options=DURATIONS, default="10 s", socketless=True,
                    tooltip="Clip length aligned to H3's 24 fps 17k+5 frame grid (determines beat count and output latent duration).",
                ),
                io.String.Input(
                    "brief", multiline=True, default="", socketless=True,
                    tooltip="Your scene idea, dialogue lines, or shot beats in plain English (editable inside SandTie Studio too).",
                ),
                io.String.Input("brief_in", optional=True, force_input=True,
                                tooltip="Optional incoming brief string override (re-ties automatically when connected)."),
                io.String.Input("rig_state", default="{}", socketless=True,
                                tooltip="Serialized SandTie Studio state JSON (compiled prompt, storyboard beats, Reference Bible, and dials)."),
            ],
            outputs=[
                io.String.Output(display_name="prompt",
                                 tooltip="Compiled MiniMax H3 prompt (connect to MiniMaxH3ReferenceToVideo / ImageToVideo prompt)."),
                io.Conditioning.Output(display_name="positive",
                                       tooltip="Native MiniMax H3 conditioning (active when wire_mode = Direct H3 Conditioning)."),
                io.Latent.Output(display_name="latent",
                                 tooltip="Empty MiniMax H3 AV latent sized to aspect & duration (active in Direct H3 Conditioning mode)."),
            ],
            hidden=[io.Hidden.dynprompt, io.Hidden.unique_id],
        )

    @classmethod
    def validate_inputs(cls, aspect=None):
        """Accept graphs saved before the 11-aspect suite. 1.0.0 stored "16:9" / "9:16",
        which core's combo check rejects now that the options read "16:9 landscape" etc.
        Naming `aspect` here skips that check for it alone; anything `_parse_aspect_ratio`
        reads as W:H (or portrait/vertical) is fine, the rest is refused readably."""
        raw = str(aspect or "").strip()
        if not raw or raw in ASPECT_RATIOS or re.search(r"\d+\s*:\s*\d+|portrait|vertical", raw, re.I):
            return True
        return f"aspect {raw!r} is not a ratio; pick one of: {', '.join(ASPECTS)}"

    @classmethod
    def fingerprint_inputs(cls, wire_mode=None, rig_state="{}", **kwargs):
        wm = wire_mode if isinstance(wire_mode, dict) else {"wire_mode": str(wire_mode or "")}
        if str(wm.get("wire_mode") or "") != WIRE_MODES[1]:
            return ""
        st = _parse_rig_state(rig_state)
        try:
            doc = json.loads(str(st.get("ref_plan_json") or "") or "{}")
        except Exception:
            return ""
        sig = []
        for r in doc.get("refs") or []:
            if not isinstance(r, dict):
                continue
            for fn, kind_f in ((r.get("file"), r.get("source") or "image"), (r.get("voice"), "image")):
                f = str(fn or "").strip()
                if not f:
                    continue
                if kind_f == "refmod":
                    p = None
                    try:
                        from . import refmod as _refmod  # noqa: PLC0415
                        p = _refmod.resolve(f)
                    except Exception:
                        try:
                            import folder_paths as _fp  # noqa: PLC0415
                            cand = os.path.join(_fp.models_dir, "refmods", f.replace("/", os.sep) + ".safetensors")
                            if os.path.isfile(cand):
                                p = cand
                        except Exception:
                            p = None
                else:
                    p = _media.resolve(f)
                if p and os.path.isfile(p):
                    st_f = os.stat(p)
                    sig.append(f"{f}:{st_f.st_mtime_ns}:{st_f.st_size}")
                else:
                    sig.append(f"{f}:missing")
        return "|".join(sig)

    @classmethod
    def execute(
        cls,
        wire_mode: dict,
        h3_format: str = H3_FORMATS[0],
        ref_images: dict | None = None,
        ref_videos: dict | None = None,
        ref_audios: dict | None = None,
        first_frame=None,
        last_frame=None,
        write_mode: str = WRITE_MODES[0],
        aspect: str = DEFAULT_ASPECT,
        duration: str = "10 s",
        brief: str = "",
        brief_in: str = "",
        rig_state: str = "{}",
    ) -> io.NodeOutput:
        wm_dict = wire_mode if isinstance(wire_mode, dict) else {"wire_mode": str(wire_mode or WIRE_MODES[0])}
        fmt_label = str(h3_format.get("h3_format") if isinstance(h3_format, dict) else (h3_format or H3_FORMATS[0]))
        fmt_code = _FMT_TO_CODE.get(fmt_label, "h3_auto")
        dur_s = _parse_dur_seconds(duration)

        state = _parse_rig_state(rig_state)
        flavors = state.get("flavors") if isinstance(state.get("flavors"), dict) else {}
        flavors = dict(flavors)
        w_in = int(wm_dict.get("width") or 0)
        h_in = int(wm_dict.get("height") or 0)
        eff_aspect = _aspect_from_dims(w_in, h_in) if (w_in > 0 and h_in > 0) else _aspect_short_label(aspect)
        flavors["aspect"] = eff_aspect
        flavors["output_format"] = fmt_code
        flavors["double_knot"] = write_mode == WRITE_MODES[0]

        wired_imgs = _ordered_autogrow_items(ref_images, "ref_image_", 9)
        wired_vids = _ordered_autogrow_items(ref_videos, "ref_video_", 3)
        wired_auds = _ordered_autogrow_items(ref_audios, "ref_audio_", 3)

        ref_plan_raw = str(state.get("ref_plan_json") or "")
        merged_ref_plan = _build_wired_ref_plan(ref_plan_raw, wired_imgs)
        start_fname = _save_tensor_ref_if_needed(first_frame, "start") if first_frame is not None else ""

        cached_prompt = str(state.get("prompt_out") or "").strip()
        active_brief = str(brief_in or "").strip() or str(brief or "").strip()

        if cached_prompt and not str(brief_in or "").strip():
            out_prompt = _st_fin.format_h3_output(cached_prompt, output_format=fmt_code, duration_s=dur_s)
        else:
            stage = "keyframe" if fmt_code == "h3_keyframe" else "cpu"
            try:
                loop = asyncio.new_event_loop()
                try:
                    res = loop.run_until_complete(
                        _st_writer.run_sandtie_write(
                            stage,
                            active_brief or "Perform the staged scene cleanly.",
                            complete_fn=None,
                            ref_plan=merged_ref_plan,
                            duration_s=dur_s,
                            start_image="1" if start_fname else None,
                            flavors=flavors,
                        )
                    )
                finally:
                    loop.close()
            except Exception:
                lab = _st_refs.sandtie_labels(merged_ref_plan)
                res = _st_writer.build_cpu_tie_block(
                    active_brief or "Perform the staged scene cleanly.",
                    lab=lab,
                    duration_s=dur_s,
                    flavors=flavors,
                )
            out_prompt = str(res.get("block") or cached_prompt or "").strip()

        is_direct = str(wm_dict.get("wire_mode") or "") == WIRE_MODES[1]
        if not is_direct:
            dynp = getattr(getattr(cls, "hidden", None), "dynprompt", None)
            uid = getattr(getattr(cls, "hidden", None), "unique_id", None)
            if _downstream_cond_or_latent_wired(dynp, uid):
                raise ValueError(
                    f"{TAG}: `positive` or `latent` is wired while wire_mode is '{WIRE_MODES[0]}'. "
                    f"Switch wire_mode to '{WIRE_MODES[1]}' and connect `clip` (or connect only `prompt`)."
                )
            try:
                from . import llm as _llm  # noqa: PLC0415
                _llm.free_for_render()
            except Exception:
                pass
            return io.NodeOutput(out_prompt, None, None)

        clip = wm_dict.get("clip")
        if clip is None:
            raise ValueError(f"{TAG}: Direct H3 Conditioning mode requires the `clip` input.")
        try:
            from . import llm as _llm  # noqa: PLC0415
            _llm.free_for_render()
        except Exception:
            pass
        vae = wm_dict.get("vae")
        audio_vae = wm_dict.get("audio_vae")
        ref_image_size = str(wm_dict.get("ref_image_size") or "match")
        w, h = _resolve_canvas_size(aspect, int(wm_dict.get("width") or 0), int(wm_dict.get("height") or 0))
        length = _align_frames(dur_s)

        from comfy_extras.nodes_minimax_h3 import (
            MiniMaxH3ImageToVideo,
            MiniMaxH3ReferenceToVideo,
            PH3ImageConditioning,
        )

        ref_images, ref_videos, ref_audios = _collect_conditioning_media(
            merged_ref_plan, wired_imgs, wired_vids, wired_auds
        )

        if fmt_code == "h3_keyframe":
            ph3_imgs = None
            if ref_images:
                ph3_imgs = {f"image_{i + 1}": t for i, t in enumerate(ref_images.values())}
            cond_out = PH3ImageConditioning.execute(
                clip=clip,
                prompt=out_prompt,
                width=w,
                height=h,
                vae=vae,
                images=ph3_imgs,
            )
            return io.NodeOutput(out_prompt, cond_out.args[0], cond_out.args[1])

        if fmt_code in ("h3_i2va", "h3_fl2va", "h3_l2va"):
            if vae is None:
                raise ValueError(
                    f"{TAG}: Direct {fmt_code.upper()} conditioning requires the Video `vae` input."
                )
            if fmt_code in ("h3_i2va", "h3_fl2va") and first_frame is None:
                raise ValueError(f"{TAG}: Direct {fmt_code.upper()} conditioning requires `first_frame`.")
            if fmt_code in ("h3_l2va", "h3_fl2va") and last_frame is None:
                raise ValueError(f"{TAG}: Direct {fmt_code.upper()} conditioning requires `last_frame`.")
            cond_out = MiniMaxH3ImageToVideo.execute(
                clip=clip,
                vae=vae,
                prompt=out_prompt,
                width=w,
                height=h,
                length=length,
                first_frame=first_frame,
                last_frame=last_frame,
            )
            return io.NodeOutput(out_prompt, cond_out.args[0], cond_out.args[1])

        cond_out = MiniMaxH3ReferenceToVideo.execute(
            clip=clip,
            prompt=out_prompt,
            width=w,
            height=h,
            length=length,
            ref_image_size=ref_image_size,
            vae=vae,
            audio_vae=audio_vae,
            ref_images=ref_images,
            ref_videos=ref_videos,
            ref_audios=ref_audios,
        )
        return io.NodeOutput(out_prompt, cond_out.args[0], cond_out.args[1])


NODE_CLASS_MAPPINGS = {
    "SandTiePromptRig": SandTiePromptRig,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SandTiePromptRig": "SandTie PromptRig (H3)",
}
