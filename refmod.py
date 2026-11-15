"""Read and write MiniMax H3 RefMods, and turn one into a DiT reference block.

The file format is Luisa's (ComfyUI-MiniMaxH3Mod, format version 4 standalone,
version 5 bundle read-only). This module does not import that pack. A file
written here is a file her loader can open, and a file she wrote is a file
the rail can read.

The stored tensor is the VAE latent. Decoding it and encoding it again is a
different reference: the pooled latent would be gone. Callers hand the DiT
`visual_block()`, and show Qwen the pictures the builder encoded when the
file keeps them (`looks`), or a decode of the latent when it does not.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import threading

import torch
import torch.nn.functional as F

TAG = "HandTieClips"
META_KEY = "refmod_meta"
AUDIO_META_KEY = "audio_refmod_meta"
REFLORA_META_KEYS = ("h3_refmod_meta", "minimax_h3_refmod_meta")
FORMAT_VERSION = 4
BUNDLE_VERSION = 5
# The pictures the builder encoded, uint8 [N,H,W,3] beside `latent`. Luisa's
# loader reads `latent` by key and her bundle writer carries unknown tensors
# through, so the extra key does not cost the file its portability.
LOOKS_KEY = "looks"
SKIP_DIRS = {".git", "__pycache__", "graph_presets"}

CONCEPT_ROLES = (
    "generic",
    "identity",
    "wardrobe",
    "bodyshape",
    "helper",
    "pose_motion",
    "background",
    "style",
)
STEP_CURVES = ("full", "early_lock", "late_detail", "fade", "mid_peak")
MAX_COPIES = 3
MAX_STRENGTH = 3.0


def _fail(msg):
    raise ValueError(f"{TAG}: {msg}")

def source_problem(name, kinds=("image", "video")):
    """Why a mod_plan source cannot be used, as a sentence, or None.

    None means nothing is detectably wrong -- present, and a kind this slot
    takes. It does NOT mean a loader will succeed, so a caller that already
    watched one fail supplies its own `or "... could not be read"`. Having
    this return that sentence unconditionally made a perfectly good voice
    fail the build.

    A loader returning None means absent, wrong kind, or unreadable, and
    reporting all three as "not in h3_refs" sent someone looking for a file
    that was sitting right there. A RefMod is visual, so an audio pick is
    the likely mistake and gets told where a voice actually goes.
    """
    try:  # the offline checkers import this module without its package
        from . import media as _media
    except ImportError:
        import media as _media

    if not str(name or "").strip():
        return None
    if _media.resolve(name) is None:
        return f"{name} is not in h3_refs"
    kind = _media.kind_of(name)
    if kind not in kinds:
        if kind == "audio":
            return (f"{name} is a sound file. A RefMod's pictures are "
                    f"encoded; its voice goes in the voice slot.")
        want = " or ".join("picture" if k == "image" else k for k in kinds)
        return f"{name} is a {kind or 'unknown'} file, not a {want}"
    return None


def _ext_kind(name):
    """'image' | 'video' | 'audio' | None. `media.kind_of`, reached without
    importing it, so the parser stays free of the loaders."""
    try:
        from . import media as _media
    except ImportError:
        import media as _media
    return _media.kind_of(name)


def parse_mod_plan(text):
    """`(stills, clip, voice)` from the builder's `mod_plan` widget.

    `stills` is a list of reference filenames in the order they will occupy
    latent frames. `clip` is `{"file", "start", "end", "frames"}` or None.
    An empty widget is `([], None, "")`, which leaves the wired inputs in
    charge.

    `voice` is a sound file in h3_refs, and is the one field here that is
    not encoded into the latent -- a RefMod holds pictures. It is recorded
    so a reference row citing this mod inherits the voice instead of the
    author having to name it twice, which is what makes the file a
    character rather than a face. It may be written as `{"file", "start",
    "end"}` to trim it; `voice_window` reads that window, and this returns
    the name alone so every caller that only needs the file is unchanged.

    A still may be written as a bare string or as `{"file": ...}`; the panel
    writes the object form, a hand-typed plan is allowed either.
    """
    if isinstance(text, (dict, list)):
        data = text
    else:
        raw = (text or "").strip()
        if not raw:
            return [], None, ""
        try:
            data = json.loads(raw)
        except ValueError as exc:
            _fail(f"mod_plan is not valid JSON: {exc}")
    if isinstance(data, list):
        data = {"stills": data}
    if not isinstance(data, dict):
        _fail("mod_plan must be a JSON object or a list of stills")

    def _name(entry, where):
        if isinstance(entry, str):
            name = entry
        elif isinstance(entry, dict):
            name = entry.get("file") or entry.get("name") or ""
        else:
            _fail(f"{where} must be a filename or an object with file")
        name = str(name).strip()
        if not name:
            _fail(f"{where} has no file")
        if "\\" in name or "/" in name or name in (".", ".."):
            _fail(f"{where}: {name!r} must be a plain filename in h3_refs")
        return name

    stills_raw = data.get("stills") or []
    if not isinstance(stills_raw, list):
        _fail("mod_plan stills must be a list")
    stills, seen = [], set()
    for i, entry in enumerate(stills_raw):
        name = _name(entry, f"mod_plan still {i + 1}")
        if name in seen:
            _fail(f"mod_plan lists {name} twice. Each still is one latent frame.")
        seen.add(name)
        stills.append(name)

    clip_raw = data.get("clip")
    clip = None
    if clip_raw not in (None, "", {}, []):
        if isinstance(clip_raw, str):
            clip_raw = {"file": clip_raw}
        if not isinstance(clip_raw, dict):
            _fail("mod_plan clip must be a filename or an object")
        clip = {
            "file": _name(clip_raw, "mod_plan clip"),
            "start": max(0.0, float(clip_raw.get("start") or 0.0)),
            "end": max(0.0, float(clip_raw.get("end") or 0.0)),
            "frames": max(0, int(clip_raw.get("frames") or 0)),
        }
        if clip["end"] and clip["end"] <= clip["start"]:
            _fail(f"mod_plan clip window ends at {clip['end']}s, which is not "
                  f"after its {clip['start']}s start")
        if _ext_kind(clip["file"]) == "audio":
            _fail(f"mod_plan clip {clip['file']} is a sound file. A voice goes "
                  f"in the RefMod's voice slot, not in the clip slot.")

    voice = data.get("voice") or ""
    if voice not in (None, "", {}, []):
        voice = _name(voice, "mod_plan voice")
        if _ext_kind(voice) != "audio":
            _fail(f"mod_plan voice {voice} is not a sound file")
        voice_window(data)  # a reversed window fails here, before any encode
    else:
        voice = ""
    return stills, clip, voice


def tensor_digest(t):
    """Same bytes as store.tensor_digest. Kept here so a file read does not
    import the hop store."""
    a = t.detach().cpu().contiguous().numpy()
    h = hashlib.sha256()
    h.update(str(a.shape).encode())
    h.update(str(a.dtype).encode())
    h.update(a.tobytes())
    return h.hexdigest()[:16]


def register_folder():
    """Make `models/refmods` a folder_paths root. Safe to call more than once."""
    import folder_paths

    base = os.path.join(folder_paths.models_dir, "refmods")
    os.makedirs(base, exist_ok=True)
    try:
        known = [os.path.normcase(os.path.normpath(p))
                 for p in folder_paths.get_folder_paths("refmods")]
    except Exception:
        known = []
    if os.path.normcase(os.path.normpath(base)) not in known:
        folder_paths.add_model_folder_path("refmods", base)
    return base


def roots():
    """Every directory a RefMod may live in, the registered root first."""
    import folder_paths

    try:
        found = list(folder_paths.get_folder_paths("refmods"))
    except Exception:
        found = []
    base = os.path.join(folder_paths.models_dir, "refmods")
    if not found:
        found = [base]
    elif os.path.normcase(os.path.normpath(base)) not in {
            os.path.normcase(os.path.normpath(p)) for p in found}:
        found.insert(0, base)
    return found


def _lora_roots():
    """Registered LoRA folders for unified RefLoRA discovery."""
    import folder_paths

    try:
        return list(folder_paths.get_folder_paths("loras"))
    except Exception:
        base = os.path.join(folder_paths.models_dir, "loras")
        return [base] if os.path.isdir(base) else []


def _clean_name(name):
    """A relative safetensors stem. `..` and an absolute path are refused."""
    raw = str(name or "").strip().replace("\\", "/")
    prefix = ""
    if raw.lower().startswith("lora:"):
        prefix = "lora:"
        raw = raw[5:]
    if raw.lower().endswith(".safetensors"):
        raw = raw[: -len(".safetensors")]
    raw = raw.strip("/")
    if not raw:
        return ""
    parts = raw.split("/")
    if any(p in ("", ".", "..") for p in parts):
        _fail(f"refmod name {name!r} is not a file under the refmods folder")
    return prefix + "/".join(parts)


def resolve(name):
    """Absolute `.safetensors` path for a refmod (or `lora:` RefLoRA) name, or None."""
    stem = _clean_name(name)
    if not stem:
        return None
    is_lora = stem.lower().startswith("lora:")
    inner = stem[5:] if is_lora else stem
    rel = inner.replace("/", os.sep) + ".safetensors"
    search_roots = _lora_roots() if is_lora else roots()
    for root in search_roots:
        base = os.path.normpath(root)
        full = os.path.normpath(os.path.join(base, rel))
        if full != base and not full.startswith(base + os.sep):
            continue
        if os.path.isfile(full):
            return full
    return None


def _clean_desc_text(text):
    s = str(text or "").strip()
    # Clean legacy widget-migration artifact ("0") or empty sentinels.
    if s in ("0", "none", "None", "null"):
        return ""
    return s


def _member_tokens(member):
    if not isinstance(member, dict):
        return 0
    if member.get("kind") == "audio":
        t = int(member.get("ref_audio_t") or member.get("latent_t") or 0)
        return 2 * t
    t = int(member.get("latent_t") or 1)
    h = int(member.get("latent_h") or 0)
    w = int(member.get("latent_w") or 0)
    return max(0, t * (h // 2) * (w // 2))


_HEADER_CACHE = {}
_HEADER_CACHE_LOCK = threading.Lock()
_HEADER_CACHE_MAX = 512


def _stat_sig(path):
    try:
        st = os.stat(path)
        return (os.path.normcase(os.path.normpath(path)), int(st.st_mtime_ns), int(st.st_size))
    except OSError:
        return None


def _invalidate_header_cache(path=None):
    with _HEADER_CACHE_LOCK:
        if path is None:
            _HEADER_CACHE.clear()
            return
        norm = os.path.normcase(os.path.normpath(path))
        for k in [k for k in _HEADER_CACHE if k[0] == norm]:
            _HEADER_CACHE.pop(k, None)


def _scan_safetensors_header(path):
    """Single safe_open inspection returning (is_reflora, meta, has_looks_key, has_audio_key)."""
    sig = _stat_sig(path)
    if sig is None:
        return (False, None, False, False)
    with _HEADER_CACHE_LOCK:
        hit = _HEADER_CACHE.get(sig)
    if hit is not None:
        return hit

    from safetensors import safe_open
    is_reflora = False
    meta = None
    has_looks_key = False
    has_audio_key = False
    try:
        with safe_open(path, framework="pt") as handle:
            hdr_meta = handle.metadata() or {}
            keys = list(handle.keys())
            key_set = set(keys)
            is_reflora = any(
                k == "refmod.latent" or k == "refmod.samples" or k.startswith("refmod.ref_")
                for k in key_set
            )
            has_looks_key = any(
                k == LOOKS_KEY or k.startswith("looks_") or k.startswith("enc_")
                or k.startswith("refmod.looks")
                for k in key_set
            )
            has_audio_key = any("audio_latent" in k for k in key_set)
            raw = hdr_meta.get(META_KEY) or hdr_meta.get(AUDIO_META_KEY)
            if raw:
                parsed = json.loads(raw)
                meta = parsed if isinstance(parsed, dict) else None
            else:
                for rk in REFLORA_META_KEYS:
                    if hdr_meta.get(rk):
                        parsed = json.loads(hdr_meta[rk])
                        if isinstance(parsed, dict):
                            data = dict(parsed)
                            data["_reflora"] = True
                            if "kind" not in data:
                                if "refmod.latent" in key_set:
                                    shape = handle.get_slice("refmod.latent").get_shape()
                                    data["kind"] = "video" if (len(shape) >= 3 and shape[2] > 1) else "image"
                                    if len(shape) == 5:
                                        data.setdefault("latent_t", int(shape[2]))
                                        data.setdefault("latent_h", int(shape[3]))
                                        data.setdefault("latent_w", int(shape[4]))
                                else:
                                    data["kind"] = "image"
                            meta = data
                        break
                if meta is None and "refmod.latent" in key_set:
                    shape = handle.get_slice("refmod.latent").get_shape()
                    meta = {
                        "name": os.path.splitext(os.path.basename(path))[0],
                        "kind": "video" if (len(shape) >= 3 and shape[2] > 1) else "image",
                        "latent_t": int(shape[2]) if len(shape) == 5 else 1,
                        "latent_h": int(shape[3]) if len(shape) == 5 else 0,
                        "latent_w": int(shape[4]) if len(shape) == 5 else 0,
                        "_reflora": True,
                        "_format_version": 4,
                    }
    except Exception:
        return (False, None, False, False)

    res = (is_reflora, meta, has_looks_key, has_audio_key)
    with _HEADER_CACHE_LOCK:
        if len(_HEADER_CACHE) >= _HEADER_CACHE_MAX:
            _HEADER_CACHE.clear()
        _HEADER_CACHE[sig] = res
    return res


def _meta_summary(meta, full=None, _scanned=None):
    kind = str((meta or {}).get("kind") or "refmod")
    role = str((meta or {}).get("concept_type") or (meta or {}).get("role") or "generic").strip()
    if role not in CONCEPT_ROLES:
        role = "generic"
    step_curve = str((meta or {}).get("default_step_curve") or "full").strip()
    if step_curve not in STEP_CURVES:
        step_curve = "full"
    ver = int((meta or {}).get("_format_version") or 4)
    fmt = "reflora" if (meta or {}).get("_reflora") else (f"v{ver}" if ver >= 4 else "v4")
    has_audio_latent = False
    members_count = 1
    tokens = 0
    has_looks = bool(int((meta or {}).get("looks") or 0))
    if kind == "bundle":
        mem = [m for m in ((meta or {}).get("members") or []) if isinstance(m, dict)]
        members_count = len(mem)
        vis_mem = [m for m in mem if m.get("kind") in ("image", "video")]
        has_audio_latent = any(m.get("kind") == "audio" for m in mem)
        tokens = sum(_member_tokens(m) for m in vis_mem)
        if any(int(m.get("looks") or 0) > 0 for m in vis_mem):
            has_looks = True
    elif kind == "audio":
        has_audio_latent = True
        tokens = _member_tokens(meta)
    else:
        tokens = _member_tokens(meta)
    if full and not has_looks:
        sc = _scanned if _scanned is not None else _scan_safetensors_header(full)
        has_looks = bool(sc[2])
        if not has_audio_latent:
            has_audio_latent = bool(sc[3])
    return {
        "kind": kind,
        "role": role,
        "default_step_curve": step_curve,
        "format": fmt,
        "tokens": tokens,
        "members_count": members_count,
        "has_audio_latent": has_audio_latent,
        "has_looks": has_looks,
    }


def listing():
    """`[{name, kind, role, tokens, ...}]` for the editor. `name` has no extension."""
    rows = []
    seen = set()
    for root in roots():
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for filename in filenames:
                if not filename.endswith(".safetensors"):
                    continue
                full = os.path.join(dirpath, filename)
                rel = os.path.relpath(full, root).replace("\\", "/")
                stem = rel[: -len(".safetensors")]
                if stem in seen:
                    continue
                seen.add(stem)
                try:
                    mtime = os.path.getmtime(full)
                except OSError:
                    continue
                sc = _scan_safetensors_header(full)
                meta = sc[1]
                info = _meta_summary(meta, full=full, _scanned=sc)
                rows.append((mtime, stem, info, description_of(meta),
                             _listed_voice(meta)))
    # Also surface unified RefLoRAs from models/loras/ that actually embed `refmod.*` latents.
    for root in _lora_roots():
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for filename in filenames:
                if not filename.endswith(".safetensors"):
                    continue
                full = os.path.join(dirpath, filename)
                sc = _scan_safetensors_header(full)
                if not sc[0]:
                    continue
                rel = os.path.relpath(full, root).replace("\\", "/")
                stem = "lora:" + rel[: -len(".safetensors")]
                if stem in seen:
                    continue
                seen.add(stem)
                try:
                    mtime = os.path.getmtime(full)
                except OSError:
                    continue
                meta = sc[1]
                info = _meta_summary(meta, full=full, _scanned=sc)
                rows.append((mtime, stem, info, description_of(meta),
                             _listed_voice(meta)))
    rows.sort(reverse=True)
    # `voice` is what a row citing this mod inherits, so the rail can show
    # and trim the recording that will actually ride.
    return [{
        "name": n,
        "kind": info["kind"],
        "role": info["role"],
        "default_step_curve": info["default_step_curve"],
        "format": info["format"],
        "tokens": info["tokens"],
        "members_count": info["members_count"],
        "has_audio_latent": info["has_audio_latent"],
        "has_looks": info["has_looks"],
        "description": d,
        "voice": v,
    } for _m, n, info, d, v in rows]


def _listed_voice(meta):
    """The header's voice as `{"file", "start", "end"}`, or None."""
    plan = (meta or {}).get("mod_plan") if isinstance(meta, dict) else None
    if not isinstance(plan, dict):
        return None
    try:
        _stills, _clip, voice = parse_mod_plan(plan)
        start, end = voice_window(plan)
    except ValueError:
        return None
    if not voice:
        return None
    return {"file": voice, "start": start, "end": end}


def description_of(meta):
    """The caption a RefMod carries in its header, or "".

    Luisa's layout has had a `description` field all along; this pack wrote it
    empty until the builder grew one, and other builders fill it. The editor
    offers it as the row's `desc` -- it is never read on the render path, so a
    caption the person has not accepted reaches no prompt. A bundle's own
    field wins, then the member `load_visual` would pick.
    """
    if not isinstance(meta, dict):
        return ""
    text = _clean_desc_text(meta.get("description"))
    if text or meta.get("kind") != "bundle":
        return text
    for member in meta.get("members") or []:
        if isinstance(member, dict) and member.get("kind") in ("image", "video"):
            cand = _clean_desc_text(member.get("description"))
            if cand:
                return cand
    return ""


def stamp(names):
    """`name:mtime` for IS_CHANGED. A missing file stays a stable token."""
    bits = []
    for name in names:
        if not name:
            continue
        path = resolve(name)
        try:
            bits.append(f"{name}:{os.path.getmtime(path)}" if path else f"{name}:missing")
        except OSError:
            bits.append(f"{name}:missing")
    return "|".join(bits)


def _is_reflora_file(path):
    """Fast header check for unified LoRA + RefMod `.safetensors` containers."""
    return bool(_scan_safetensors_header(path)[0])


def read_meta(path):
    """Header JSON, or None. Supports v4/v5 `refmod_meta`, `audio_refmod_meta`, and RefLoRA metadata."""
    meta = _scan_safetensors_header(path)[1]
    return dict(meta) if isinstance(meta, dict) else None


def voice_window(plan):
    """`(start, end)` seconds of the mod_plan's voice. `(0, 0)` is the whole file.

    Same sentinel as `media.clip_window`: an end of 0 is the end of the file.
    Only the object form of `voice` carries a window.
    """
    if not isinstance(plan, dict):
        try:
            plan = json.loads(plan) if str(plan or "").strip() else {}
        except ValueError:
            return 0.0, 0.0
    entry = plan.get("voice") if isinstance(plan, dict) else None
    if not isinstance(entry, dict):
        return 0.0, 0.0
    try:
        start = max(0.0, float(entry.get("start") or 0.0))
        end = max(0.0, float(entry.get("end") or 0.0))
    except (TypeError, ValueError):
        _fail("mod_plan voice window must be numbers of seconds")
    if end and end <= start:
        _fail(f"mod_plan voice window ends at {end:g}s, which is not after "
              f"its {start:g}s start")
    return start, end


def stored_plan(name):
    """The `mod_plan` a saved RefMod was built from, or `{}`.

    Empty for a mod built through the sockets, for one written before this
    field existed, or for a file that is not a RefMod at all -- all three
    mean the same thing to a caller: nothing to reload.
    """
    path = resolve(name)
    if path is None:
        return {}
    meta = read_meta(path) or {}
    plan = meta.get("mod_plan")
    if not isinstance(plan, dict):
        return {}
    try:
        stills, clip, voice = parse_mod_plan(plan)
    except ValueError:
        # A header that no longer parses is not worth failing a panel over.
        return {}
    if not (stills or clip or voice):
        return {}
    out = {"stills": stills, "clip": clip, "voice": voice}
    if voice:
        try:
            start, end = voice_window(plan)
        except ValueError:
            start, end = 0.0, 0.0
        if start or end:
            out["voice_start"], out["voice_end"] = start, end
    return out


def stored_voice(name):
    """`{"file", "start", "end"}` for the voice a saved RefMod names, or `{}`.

    A reference row that cites the mod and leaves its own voice empty
    inherits this, window and all, so the character is assembled once in the
    builder and the rail only has to point at it.
    """
    plan = stored_plan(name)
    if not plan.get("voice"):
        return {}
    return {"file": str(plan["voice"]),
            "start": float(plan.get("voice_start") or 0.0),
            "end": float(plan.get("voice_end") or 0.0)}


def _load_tensor(path, key):
    from safetensors.torch import load_file

    # Clone releases the file mapping so Windows can overwrite the file later.
    return load_file(path, device="cpu")[key].clone()


def _load_looks(path, key=LOOKS_KEY):
    """The kept pictures (`[N,H,W,3]` uint8), or None when absent."""
    from safetensors import safe_open

    try:
        with safe_open(path, framework="pt", device="cpu") as handle:
            keys = set(handle.keys())
            if key not in keys:
                return None
            looks = handle.get_tensor(key).clone()
    except Exception:
        return None
    if looks.ndim == 3 and looks.shape[-1] == 3:
        looks = looks.unsqueeze(0)
    if looks.ndim != 4 or looks.shape[-1] != 3 or looks.shape[0] < 1:
        print(f"[{TAG}] {os.path.basename(path)}: {key} tensor is "
              f"{tuple(looks.shape)}, not [N,H,W,3]. Showing Qwen a decode.",
              flush=True)
        return None
    return looks


def _load_enc_jpegs(path, member_indices=None):
    """Decode Fantastic/H3RefModPicker `enc_N` JPEG byte tensors if present."""
    from safetensors import safe_open

    try:
        with safe_open(path, framework="pt", device="cpu") as handle:
            keys = [k for k in handle.keys() if k.startswith("enc_")]
            if not keys:
                return None
            keys.sort(key=lambda s: int(s.split("_", 1)[1]) if s.split("_", 1)[1].isdigit() else 9999)
            if member_indices is not None:
                want = {f"enc_{i}" for i in member_indices}
                # Strict: a member without its own enc_N has none. Falling back to
                # every enc_ key showed Qwen the other members' photos as this one.
                keys = [k for k in keys if k in want]
                if not keys:
                    return None
            from PIL import Image  # noqa: PLC0415
            import io  # noqa: PLC0415
            import numpy as np  # noqa: PLC0415
            frames = []
            for k in keys:
                raw = handle.get_tensor(k).numpy().tobytes()
                with Image.open(io.BytesIO(raw)) as im:
                    arr = np.array(im.convert("RGB"), dtype=np.uint8, copy=True)
                frames.append(torch.from_numpy(arr))
            if not frames:
                return None
            # Only stack if dimensions match; otherwise return list or first frame.
            h0, w0 = frames[0].shape[:2]
            if all(f.shape[:2] == (h0, w0) for f in frames):
                return torch.stack(frames, dim=0)
            return frames[0].unsqueeze(0)
    except Exception:
        return None


def _as_visual(meta, latent, where):
    kind = str(meta.get("kind") or "")
    if kind not in ("image", "video"):
        _fail(f"{where} is a '{kind or 'unknown'}' RefMod. This pass reads "
              f"image and video mods.")
    if latent.ndim != 5 or latent.shape[0] != 1 or latent.shape[1] != 24:
        _fail(f"{where} latent must be [1,24,T,H,W], got {tuple(latent.shape)}")
    _b, _c, t, h, w = latent.shape
    if t < 1 or h < 2 or w < 2 or h % 2 or w % 2:
        _fail(f"{where} latent grid {t}x{h}x{w} is not a usable visual ref")
    if kind == "image":
        latent = latent[:, :, :1]
        t = 1
    latent = latent.contiguous()
    return {
        "kind": "image" if t == 1 else "video",
        "latent": latent,
        "latent_t": int(t),
        "latent_h": int(h),
        "latent_w": int(w),
        "name": str(meta.get("name") or where),
        "mode": str(meta.get("mode") or ""),
        "role": str(meta.get("concept_type") or meta.get("role") or "generic"),
        "default_step_curve": str(meta.get("default_step_curve") or "full"),
        "digest": tensor_digest(latent),
        "tokens": int(t) * (int(h) // 2) * (int(w) // 2),
    }


def _first_tensor(*cands):
    for t in cands:
        if t is not None:
            return t
    return None


def _extract_looks_from_handle(handle, keys, key=LOOKS_KEY):
    if key not in keys:
        return None
    looks = handle.get_tensor(key).clone()
    if looks.ndim == 3 and looks.shape[-1] == 3:
        looks = looks.unsqueeze(0)
    if looks.ndim != 4 or looks.shape[-1] != 3 or looks.shape[0] < 1:
        return None
    return looks


def _extract_enc_jpegs_from_handle(handle, keys, member_indices=None):
    enc_keys = [k for k in keys if k.startswith("enc_")]
    if not enc_keys:
        return None
    enc_keys.sort(key=lambda s: int(s.split("_", 1)[1]) if s.split("_", 1)[1].isdigit() else 9999)
    if member_indices is not None:
        want = {f"enc_{i}" for i in member_indices}
        # Strict, as in _load_enc_jpegs: never another member's photos.
        enc_keys = [k for k in enc_keys if k in want]
        if not enc_keys:
            return None
    try:
        from PIL import Image  # noqa: PLC0415
        import io  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415
        frames = []
        for k in enc_keys:
            raw = handle.get_tensor(k).numpy().tobytes()
            with Image.open(io.BytesIO(raw)) as im:
                arr = np.array(im.convert("RGB"), dtype=np.uint8, copy=True)
            frames.append(torch.from_numpy(arr))
        if not frames:
            return None
        h0, w0 = frames[0].shape[:2]
        if all(f.shape[:2] == (h0, w0) for f in frames):
            return torch.stack(frames, dim=0)
        return frames[0].unsqueeze(0)
    except Exception:
        return None


def load_bundle_visuals(name, members_filter=None):
    """All visual blocks inside `name` (v4 standalone, v5 bundle, or RefLoRA).

    Returns a list of visual dicts. `members_filter` (optional list of 0-based
    indices) restricts a v5 bundle to only those visual members without rebuilding.
    """
    path = resolve(name)
    if path is None:
        return []
    meta = read_meta(path)
    if not isinstance(meta, dict):
        _fail(f"{name} has no {META_KEY} header. It is not a RefMod.")

    from safetensors import safe_open

    # RefLoRA container (`refmod.latent` / `refmod.samples` / `refmod.ref_*`)
    if meta.get("_reflora"):
        out = []
        with safe_open(path, framework="pt", device="cpu") as fh:
            keys = set(fh.keys())
            if "refmod.latent" in keys:
                lat = fh.get_tensor("refmod.latent").clone()
                item = _as_visual(meta, lat, name)
                looks = _first_tensor(
                    _extract_looks_from_handle(fh, keys, "refmod.looks"),
                    _extract_looks_from_handle(fh, keys, LOOKS_KEY),
                )
                item["looks"] = looks
                item["looks_digest"] = tensor_digest(looks) if looks is not None else None
                item["member_index"] = 0
                out.append(item)
            else:
                ref_keys = sorted(
                    [k for k in keys if k.startswith("refmod.ref_")],
                    key=lambda s: int(s.split("_")[-1]) if s.split("_")[-1].isdigit() else 9999,
                )
                for idx, rk in enumerate(ref_keys):
                    lat = fh.get_tensor(rk).clone()
                    if lat.ndim != 5 or lat.shape[1] != 24:
                        continue
                    k_meta = {"name": f"{name}#{idx}", "kind": "video" if lat.shape[2] > 1 else "image"}
                    item = _as_visual(k_meta, lat, name)
                    looks = _extract_looks_from_handle(fh, keys, f"refmod.looks_{idx}")
                    item["looks"] = looks
                    item["looks_digest"] = tensor_digest(looks) if looks is not None else None
                    item["member_index"] = idx
                    out.append(item)
        if not out:
            _fail(f"{name} RefLoRA has no MiniMax-H3 [1,24,T,H,W] visual latent.")
        return out

    if meta.get("kind") == "bundle":
        members = meta.get("members") or []
        if not isinstance(members, list):
            _fail(f"{name} bundle has no members list")
        wanted = None
        if members_filter:
            wanted = {int(x) for x in members_filter}
        out = []
        vis_indices = [i for i, m in enumerate(members) if isinstance(m, dict) and m.get("kind") in ("image", "video")]
        if not vis_indices:
            _fail(f"{name} has no visual member. Audio RefMods are not applied "
                  f"by this node.")
        with safe_open(path, framework="pt", device="cpu") as fh:
            keys = set(fh.keys())
            for i in vis_indices:
                if wanted is not None and i not in wanted:
                    continue
                member = members[i]
                latent = fh.get_tensor(f"ref_{i}").clone()
                loaded = _as_visual(member, latent, name)
                looks = _first_tensor(
                    _extract_looks_from_handle(fh, keys, f"looks_{i}"),
                    _extract_looks_from_handle(fh, keys, LOOKS_KEY) if len(vis_indices) == 1 else None,
                    # one visual member: its photos may be stored unnumbered-to-it
                    _extract_enc_jpegs_from_handle(fh, keys, [i] if len(vis_indices) > 1 else None),
                )
                loaded["looks"] = looks
                loaded["looks_digest"] = tensor_digest(looks) if looks is not None else None
                loaded["member_index"] = i
                if member.get("yaw") is not None:
                    loaded["yaw"] = float(member["yaw"])
                if loaded.get("role") == "generic" and meta.get("concept_type"):
                    loaded["role"] = str(meta.get("concept_type"))
                if loaded.get("default_step_curve") == "full" and meta.get("default_step_curve"):
                    loaded["default_step_curve"] = str(meta.get("default_step_curve"))
                out.append(loaded)
        if not out and wanted is not None:
            _fail(f"{name}: selected member indices {sorted(wanted)} matched no visual member.")
        return out

    if meta.get("kind") == "audio":
        _fail(f"{name} is an audio-only RefMod. Visual references require an image or video RefMod.")
    with safe_open(path, framework="pt", device="cpu") as fh:
        keys = set(fh.keys())
        latent = fh.get_tensor("latent").clone()
        loaded = _as_visual(meta, latent, name)
        looks = _first_tensor(
            _extract_looks_from_handle(fh, keys, LOOKS_KEY),
            _extract_enc_jpegs_from_handle(fh, keys),
        )
    loaded["looks"] = looks
    loaded["looks_digest"] = tensor_digest(looks) if looks is not None else None
    loaded["member_index"] = 0
    return [loaded]


def load_visual(name):
    """The first visual latent behind `name`, or None when the file is absent."""
    items = load_bundle_visuals(name)
    if not items:
        return None
    if len(items) > 1:
        print(f"[{TAG}] {name}: loaded primary visual member ({len(items)} total in bundle)", flush=True)
    return items[0]


def load_audio_latent(name):
    """Pre-encoded `[1,32,2,T]` audio latent inside `name`, or None."""
    path = resolve(name)
    if path is None:
        return None
    meta = read_meta(path)
    if not isinstance(meta, dict):
        return None
    from safetensors import safe_open
    try:
        with safe_open(path, framework="pt", device="cpu") as fh:
            keys = set(fh.keys())
            tensor = None
            src_name = ""
            sr = int(meta.get("sample_rate") or 32000)
            if meta.get("_reflora") and "refmod.audio_latent" in keys:
                tensor = fh.get_tensor("refmod.audio_latent").clone()
            elif meta.get("kind") == "bundle":
                for i, member in enumerate(meta.get("members") or []):
                    if isinstance(member, dict) and member.get("kind") == "audio" and f"ref_{i}" in keys:
                        tensor = fh.get_tensor(f"ref_{i}").clone()
                        sr = int(member.get("sample_rate") or sr)
                        src_name = os.path.basename(str(member.get("name") or "").strip())
                        break
            elif meta.get("kind") == "audio" and "latent" in keys:
                tensor = fh.get_tensor("latent").clone()
            if tensor is None or tensor.ndim != 4 or tensor.shape[1] != 32 or tensor.shape[2] != 2:
                return None
            return {
                "audio_latent": tensor.contiguous(),
                "ref_audio_t": int(tensor.shape[-1]),
                "sample_rate": sr,
                "digest": tensor_digest(tensor),
                "name": src_name,
            }
    except Exception:
        return None


def _blur_latent(z, factor=8):
    """Luisa's weakening target: a spatial/temporal low-pass, not noise and not zero."""
    if z.dim() == 4:
        b, c, stereo, t = z.shape
        if t <= 1:
            return z
        flat = z.reshape(b * c * stereo, 1, t).float()
        down = F.adaptive_avg_pool1d(flat, max(1, t // factor))
        return F.interpolate(down, size=t, mode="linear", align_corners=False).reshape_as(z).to(dtype=z.dtype)
    if z.dim() != 5:
        _fail(f"cannot blur a RefMod latent of shape {tuple(z.shape)}")
    t, h, w = z.shape[2], z.shape[3], z.shape[4]
    down = F.adaptive_avg_pool3d(z.float(), (t, max(1, h // factor), max(1, w // factor)))
    up = F.interpolate(down, size=(t, h, w), mode="trilinear", align_corners=False)
    return up.to(dtype=z.dtype)


def refine_cutout(mask, frames, low=0.1, pocket=0.005):
    """A matting model's soft mask, made solid inside and clean at the edge.

    The two halves of a cutout fail differently, so they are treated apart.

    Inside, a matting model is unsure as well as at the edge -- on a
    character sheet the robes came back as grey patches, and every grey
    pixel is subject half-lost. So the question is turned round: backdrop
    is what is confidently empty (`< low`) AND touches the frame's border
    or is a pocket larger than `pocket` of it. Everything else, shrunk
    back from its outline, is a core held at full weight.

    At the edge, the model's own soft alpha is kept -- that is what it is
    good at -- except that on a plain sheet an edge pixel the colour of
    the sheet is let go. That removes the white rim a cutout leaves round
    a figure, the thin panel dividers a sheet grid is drawn with, and the
    wedges of sheet caught between hair and shoulder. What the model was
    sure of inside the figure is never keyed, so a white collar stays.
    """
    import numpy as np  # noqa: PLC0415
    from scipy import ndimage  # noqa: PLC0415

    out = []
    for raw_t, px_t in zip(mask, frames):
        raw = raw_t.float().cpu().numpy()
        px = px_t[..., :3].float().cpu().numpy()
        labels, count = ndimage.label(raw < low)
        if count:
            edge = np.unique(np.concatenate(
                [labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
            sizes = np.bincount(labels.ravel(), minlength=count + 1)
            backdrop_ids = set(int(i) for i in edge if i) | set(
                int(i) for i in np.nonzero(sizes >= pocket * raw.size)[0] if i)
            backdrop = np.isin(labels, sorted(backdrop_ids))
        else:
            backdrop = np.zeros_like(raw, dtype=bool)
        inset = max(1, round(min(raw.shape) / 100))
        core = ndimage.binary_erosion(~backdrop, iterations=inset)
        m = np.maximum(raw, core.astype(np.float32))

        sure = backdrop & (raw < 0.02)
        if sure.sum() > 0.01 * raw.size:
            sheet = np.median(px[sure], axis=0)
            spread = float(np.abs(px[sure] - sheet).mean())
            if spread < 0.06:  # a plain sheet, not a photographed room
                near = np.abs(px - sheet).max(axis=-1)
                key = np.clip((near - 0.04) / 0.12, 0.0, 1.0)
                m = np.where(core & (raw >= 0.9), m, m * key)
        out.append(torch.from_numpy(m.astype(np.float32)))
    return torch.stack(out)


def pull_push_fill(frames, mask):
    """Every pixel coloured from the subject nearest it, smoothly.

    The standard pull-push hole fill: pool colour-times-weight and weight
    down to one pixel, then walk back up, keeping a level's own colour in
    proportion to how much subject it holds and taking the coarser guess
    for the rest. The backdrop ends up a soft extension of the subject's
    own edge colours -- no structure of its own, and none of its tone.
    """
    c = frames[..., :3].float().movedim(-1, 1)          # [T, 3, H, W]
    w = mask.float().to(c.device).unsqueeze(1)          # [T, 1, H, W]
    colours, weights = [c * w], [w]
    while max(colours[-1].shape[-2:]) > 1:
        colours.append(F.avg_pool2d(colours[-1], 2, ceil_mode=True))
        weights.append(F.avg_pool2d(weights[-1], 2, ceil_mode=True))
    fill = colours[-1] / weights[-1].clamp_min(1e-6)
    for cl, wl in zip(reversed(colours[:-1]), reversed(weights[:-1])):
        coarse = F.interpolate(fill, size=cl.shape[-2:], mode="bilinear",
                               align_corners=False)
        own = cl / wl.clamp_min(1e-6)
        fill = wl * own + (1.0 - wl) * coarse
    return fill.movedim(1, -1).clamp(0.0, 1.0)


def _blur_bg_pixels(px, mask):
    """Smooth heavy spatial blur of background pixels (Fantastic-style) for zero edge halos."""
    c = px[..., :3].float().movedim(-1, 1)  # [T, 3, H, W]
    _, _, h, w = c.shape
    scale = max(8, round(min(h, w) / 24))
    bh, bw = max(2, h // scale), max(2, w // scale)
    down = F.adaptive_avg_pool2d(c, (bh, bw))
    blurred = F.interpolate(down, size=(h, w), mode="bicubic", align_corners=False).movedim(1, -1).clamp(0.0, 1.0)
    # Softly expand mask perimeter so hairline edges don't glow against dark backgrounds
    m_dil = F.max_pool2d(mask.float().to(c.device).unsqueeze(1), kernel_size=7, stride=1, padding=3).squeeze(1)
    edge_soft = F.avg_pool2d(m_dil.unsqueeze(1), kernel_size=9, stride=1, padding=4).squeeze(1)
    return blurred, edge_soft


def isolate_subject(frames, mask, retention=0.0, mode="pull_push"):
    """`[T,H,W,C]` canvas frames with the backdrop replaced, before encode.

    `mode`:
      * `pull_push` (default legacy): edge-color pull-push fill
      * `blur_bg`: blurred background (keeps natural lighting balance with zero pull-push color streaks)
      * `neutral_gray`: 50% studio neutral backdrop
    """
    m = mask.float().to(frames.device)
    if m.shape[0] == 1 and frames.shape[0] > 1:
        m = m.expand(frames.shape[0], -1, -1)
    if tuple(m.shape) != tuple(frames.shape[:3]):
        _fail(f"subject mask {tuple(m.shape)} does not cover frames "
              f"{tuple(frames.shape[:3])}")
    r = min(1.0, max(0.0, float(retention)))
    if r >= 1.0 or float(m.amax()) <= 0.0:
        return frames
    px = frames[..., :3].float()
    bg_mode = str(mode or "pull_push").strip().lower()
    if bg_mode == "blur_bg":
        bg, soft_m = _blur_bg_pixels(px, m)
        keep = (r + (1.0 - r) * torch.maximum(m, soft_m * 0.65)).unsqueeze(-1)
    elif bg_mode == "neutral_gray":
        bg = torch.full_like(px, 0.5)
        keep = (r + (1.0 - r) * m).unsqueeze(-1)
    else:
        bg = pull_push_fill(px, m)
        keep = (r + (1.0 - r) * m).unsqueeze(-1)
    out = keep * px + (1.0 - keep) * bg
    return out.to(frames.dtype)


def crop_to_subject(frames, mask, margin=1.6):
    """Subject-centered bounding-box crop with margin (1.4-2.0x), rounded to 32px grid."""
    import numpy as np  # noqa: PLC0415

    m_f = mask.float().to(frames.device)
    if m_f.shape[0] == 1 and frames.shape[0] > 1:
        m_f = m_f.expand(frames.shape[0], -1, -1)
    union = (m_f > 0.25).any(dim=0).cpu().numpy()
    ys, xs = np.nonzero(union)
    if len(ys) < 16:
        return frames, mask
    h, w = int(frames.shape[1]), int(frames.shape[2])
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    bw = max(64, x1 - x0)
    bh = max(64, y1 - y0)
    marg = max(1.1, float(margin or 1.6))
    cw = min(w, max(64, int(round(bw * marg / 32.0)) * 32))
    ch = min(h, max(64, int(round(bh * marg / 32.0)) * 32))
    if cw >= w and ch >= h:
        return frames, mask
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    lx = max(0, min(w - cw, cx - cw // 2))
    ty = max(0, min(h - ch, cy - ch // 2))
    return frames[:, ty:ty + ch, lx:lx + cw], mask[:, ty:ty + ch, lx:lx + cw]


def mask_to_canvas(mask, tw, th, fit_mode="crop"):
    """`[T,H,W]` MASK fit onto the canvas the way `to_canvas` fits pixels."""
    import comfy.utils

    if mask.dim() == 2:
        mask = mask.unsqueeze(0)
    if mask.dim() != 3:
        _fail(f"a subject mask must be [T,H,W], got {tuple(mask.shape)}")
    crop = "center" if fit_mode == "crop" else "disabled"
    m = comfy.utils.common_upscale(mask.float().unsqueeze(1), int(tw), int(th),
                                   "bilinear", crop)
    return m.squeeze(1).clamp(0.0, 1.0)


CUTOUT_MODEL = "isnet-general-use"
_cutout_session = None
_sam_predictor = None
_sam_path_loaded = ""


def _find_sam_checkpoint():
    import folder_paths

    cands = []
    try:
        for p in folder_paths.get_folder_paths("sams"):
            cands.append(p)
    except Exception:
        pass
    cands.append(os.path.join(folder_paths.models_dir, "sams"))
    for root in cands:
        if not os.path.isdir(root):
            continue
        for fn in sorted(os.listdir(root)):
            if fn.lower().endswith((".pth", ".pt", ".safetensors")):
                return os.path.join(root, fn)
    return ""


def _cutout_sam(frames):
    """Subject mask via ComfyUI's installed SAM (`models/sams/`)."""
    global _sam_predictor, _sam_path_loaded
    import numpy as np  # noqa: PLC0415
    from segment_anything import SamPredictor, sam_model_registry  # noqa: PLC0415

    ckpt = _find_sam_checkpoint()
    if not ckpt:
        raise FileNotFoundError("No SAM checkpoint in models/sams/")
    if _sam_predictor is None or _sam_path_loaded != ckpt:
        low = os.path.basename(ckpt).lower()
        arch = "vit_h" if "vit_h" in low else ("vit_l" if "vit_l" in low else "vit_b")
        sam = sam_model_registry[arch](checkpoint=ckpt)
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        sam.to(device=dev)
        _sam_predictor = SamPredictor(sam)
        _sam_path_loaded = ckpt

    out = []
    for frame in frames:
        rgb = (frame[..., :3].float().clamp(0, 1) * 255).round().byte().cpu().numpy()
        h, w = rgb.shape[:2]
        _sam_predictor.set_image(rgb)
        # Foreground center + upper-center points + central box prompt
        pts = np.array([[w * 0.5, h * 0.45], [w * 0.5, h * 0.25], [w * 0.5, h * 0.70]])
        lbls = np.array([1, 1, 1])
        box = np.array([w * 0.08, h * 0.04, w * 0.92, h * 0.96])
        masks, scores, _ = _sam_predictor.predict(
            point_coords=pts, point_labels=lbls, box=box, multimask_output=True)
        best = int(np.argmax(scores))
        out.append(torch.from_numpy(masks[best].astype(np.float32)))
    return torch.stack(out)


def cutout_masks(frames, backend="auto_rembg"):
    """`[T,H,W]` subject masks for `[T,H,W,C]` canvas frames.

    `backend`: `"auto_rembg"` (default, uses `rembg`) or `"auto_sam"`
    (uses SAM from `models/sams/`, falling back to `rembg` if unavailable).
    """
    if str(backend or "").strip().lower() == "auto_sam":
        try:
            return _cutout_sam(frames)
        except Exception as exc:
            print(f"[{TAG}] SAM cutout unavailable ({exc}); falling back to rembg", flush=True)

    global _cutout_session
    try:
        from rembg import new_session, remove  # noqa: PLC0415
    except ImportError:
        _fail("subject_mask=auto needs rembg (pip install rembg), or wire a "
              "MASK into the builder's mask socket")
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    if _cutout_session is None:
        _cutout_session = new_session(CUTOUT_MODEL)
    out = []
    for frame in frames:
        px = (frame[..., :3].float().clamp(0, 1) * 255).round().byte().cpu().numpy()
        m = remove(Image.fromarray(px), session=_cutout_session, only_mask=True)
        out.append(torch.from_numpy(np.asarray(m.convert("L"), dtype=np.float32) / 255.0))
    return torch.stack(out)


def step_curve_value(curve_name, progress):
    """Strength in [0, 1] at denoising `progress` (0 = noisy start, 1 = clean end)."""
    import math

    c = str(curve_name or "full").strip().lower()
    x = min(1.0, max(0.0, float(progress)))
    if c == "early_lock":
        # Strong composition/anatomy anchor for first ~45%, smooth floor 0.15 late.
        e = 0.5 * (1.0 + math.cos(math.pi * min(1.0, x / 0.72)))
        return 0.15 + 0.85 * e
    if c == "late_detail":
        # Gentle early framing (0.25), ramps to 1.0 in the detail half.
        e = 0.5 * (1.0 - math.cos(math.pi * max(0.0, min(1.0, (x - 0.15) / 0.65))))
        return 0.25 + 0.75 * e
    if c == "fade":
        return max(0.0, 1.0 - x)
    if c == "mid_peak":
        return 0.25 + 0.75 * (1.0 - abs(2.0 * x - 1.0))
    return 1.0


def apply_strength(latent, strength):
    """`w * latent + (1-w) * blur`. `>= 1` returns the same tensor."""
    w = float(strength)
    if w >= 1.0:
        return latent
    if w <= 0.0:
        return None
    return w * latent + (1.0 - w) * _blur_latent(latent)


def visual_block(loaded, strength, step_curve="full"):
    """Single `minimax_refs` block for this mod, or None when strength drops it."""
    latent = apply_strength(loaded["latent"], min(1.0, float(strength)))
    if latent is None:
        return None
    block = {
        "kind": loaded["kind"],
        "latent_h": int(latent.shape[3]),
        "latent_w": int(latent.shape[4]),
        "latent": latent,
        "refmod": True,
    }
    sc = str(step_curve or loaded.get("default_step_curve") or "full").strip().lower()
    if sc != "full" and sc in STEP_CURVES:
        block["step_curve"] = sc
    if loaded["kind"] == "video":
        block["latent_t"] = int(latent.shape[2])
        block["ref_audio_t"] = 0
        block["audio_latent"] = None
    return block


def visual_blocks(loaded, strength, step_curve="full"):
    """One or more `minimax_refs` blocks. `strength > 1.0` stacks copies + residual blur."""
    import math

    w = min(MAX_STRENGTH, max(0.0, float(strength)))
    if w <= 0.0:
        return []
    if w <= 1.0:
        b = visual_block(loaded, w, step_curve=step_curve)
        return [b] if b is not None else []
    n_full = min(MAX_COPIES, int(math.floor(w)))
    rem = round(w - n_full, 4)
    out = []
    for _ in range(n_full):
        b = visual_block(loaded, 1.0, step_curve=step_curve)
        if b is not None:
            out.append(b)
    if rem >= 0.05 and len(out) < MAX_COPIES:
        b = visual_block(loaded, rem, step_curve=step_curve)
        if b is not None:
            out.append(b)
    return out


def audio_block(loaded_audio, strength=1.0, step_curve="full"):
    """`minimax_refs` standalone audio block from pre-encoded `[1,32,2,T]` latent."""
    if not loaded_audio or loaded_audio.get("audio_latent") is None:
        return None
    z = apply_strength(loaded_audio["audio_latent"], min(1.0, float(strength)))
    if z is None:
        return None
    block = {
        "kind": "audio",
        "ref_audio_t": int(z.shape[-1]),
        "audio_latent": z,
        "refmod": True,
    }
    sc = str(step_curve or "full").strip().lower()
    if sc != "full" and sc in STEP_CURVES:
        block["step_curve"] = sc
    return block


_STEP_CURVE_SEQ = 0


def attach_step_curve_wrapper(model):
    """Attach per-RefMod denoising step-curve mixing (zero cost when no block carries `step_curve`)."""
    global _STEP_CURVE_SEQ
    if model is None or not hasattr(model, "add_wrapper_with_key"):
        return model
    from contextvars import ContextVar
    import comfy.patcher_extension as _pe

    _STEP_CURVE_SEQ += 1
    key = f"htc_refmod_step_curve_{_STEP_CURVE_SEQ}"
    start_var = ContextVar(key, default=1000.0)
    blur_cache = {}

    def _cached_blur(z):
        ck = (id(z), z.device, z.dtype)
        hit = blur_cache.get(ck)
        if hit is not None:
            return hit
        if len(blur_cache) > 64:
            blur_cache.clear()
        b = _blur_latent(z)
        blur_cache[ck] = b
        return b

    def _schedule(executor, noise, latent_image, sampler, sigmas, *args, **kwargs):
        blur_cache.clear()
        try:
            sampling = executor.class_obj.model_patcher.get_model_object("model_sampling")
            start = float(sampling.timestep(sigmas[0]))
        except Exception:
            start = 1000.0
        tok = start_var.set(start)
        try:
            return executor(noise, latent_image, sampler, sigmas, *args, **kwargs)
        finally:
            start_var.reset(tok)
            blur_cache.clear()

    def _wrapper(executor, x, timestep, context, transformer_options={}, **kwargs):
        payload = kwargs.get("minimax_payload")
        refs = (payload or {}).get("refs") or []
        if not payload or not any(isinstance(r, dict) and r.get("step_curve") for r in refs):
            return executor(x, timestep, context, transformer_options=transformer_options, **kwargs)
        start = start_var.get()
        sigma = min(1.0, max(0.0, float(timestep.flatten()[0]) / max(start, 1e-8)))
        prog = 1.0 - sigma
        mixed = dict(payload)
        kfs = payload.get("keyframes") or []
        for field, latent_key in (("cond_video_latents", "latent"),
                                  ("cond_audio_latents", "audio_latent")):
            cond = payload.get(field)
            if not cond:
                continue
            out = list(cond)
            idx = sum(1 for k in kfs if k.get(latent_key) is not None)
            changed = False
            for r in refs:
                if r.get(latent_key) is None:
                    continue
                if idx >= len(out):
                    break
                sc = r.get("step_curve")
                if sc and sc != "full":
                    w = step_curve_value(sc, prog)
                    if w < 0.999:
                        z = out[idx]
                        out[idx] = (w * z + (1.0 - w) * _cached_blur(z)).to(dtype=z.dtype)
                        changed = True
                idx += 1
            if changed:
                mixed[field] = out
        return executor(x, timestep, context, transformer_options=transformer_options,
                        **dict(kwargs, minimax_payload=mixed))

    out = model.clone()
    out.add_wrapper_with_key(_pe.WrappersMP.OUTER_SAMPLE, key, _schedule)
    out.add_wrapper_with_key(_pe.WrappersMP.DIFFUSION_MODEL, key, _wrapper)
    return out


_VFADE_SEQ = 0


def _cosine_fade_strength(prog: float, fade_start: float = 0.55, end_strength: float = 0.20) -> float:
    p = min(1.0, max(0.0, float(prog)))
    fs = min(0.99, max(0.0, float(fade_start)))
    es = min(1.0, max(0.0, float(end_strength)))
    if p <= fs:
        return 1.0
    u = (p - fs) / max(1e-6, 1.0 - fs)
    return es + (1.0 - es) * 0.5 * (1.0 + math.cos(math.pi * u))


def _ref_video_v_spans(payload, context, video_x, audio_x, scale: float):
    """Exact `(start, stop, v_scale)` spans of `video`/`video_audio` ref blocks in `PackedLayout`."""
    if not payload or float(scale) >= 0.9999:
        return ()
    refs = payload.get("refs") or ()
    has_vid = any(isinstance(r, dict) and r.get("kind") in ("video", "video_audio")
                  and not r.get("_keep_full_v") for r in refs)
    if not has_vid:
        return ()
    try:
        from comfy.ldm.minimax.model import PackedLayout  # noqa: PLC0415
    except Exception:
        return ()
    text_len = int(context.shape[1]) if hasattr(context, "shape") and context.ndim >= 2 else 0
    lt, lh, lw = int(video_x.shape[2]), int(video_x.shape[3]), int(video_x.shape[4])
    at = int(audio_x.shape[-1]) if audio_x is not None else 0
    layout = payload.get("layout")
    if layout is None or getattr(layout, "signature", None) != (text_len, lt, lh, lw, at):
        layout = PackedLayout(text_len, lt, lh, lw, at,
                              keyframes=payload.get("keyframes"), refs=refs)
    ref_img_segs = [(int(a), int(b)) for a, b, kind in getattr(layout, "segments", ()) if kind == "ref_img"]
    spans = []
    ri = 0
    for blk in refs:
        if not isinstance(blk, dict):
            continue
        knd = blk.get("kind")
        if knd in ("image", "video", "video_audio"):
            if ri >= len(ref_img_segs):
                break
            if knd in ("video", "video_audio") and not blk.get("_keep_full_v"):
                a, b = ref_img_segs[ri]
                spans.append((a, b, float(scale)))
            ri += 1
    return tuple(spans)


def attach_ref_video_fade_wrapper(model, fade_start=0.55, end_strength=0.20):
    """Half-cosine fade on native `<Video N>` reference block attention `V` slices.

    Preserves `<Picture N>` stills, `<Audio N>`, keyframes, and target streams,
    and works inside both dense attention AND `HTCSparseAttention` (`ck.sol_attn_chunked`).
    """
    global _VFADE_SEQ
    if model is None or not hasattr(model, "add_wrapper_with_key"):
        return model
    from contextvars import ContextVar  # noqa: PLC0415
    import comfy.patcher_extension as _pe  # noqa: PLC0415
    from comfy.ldm.modules.attention import AttentionTensorContainer, optimized_attention  # noqa: PLC0415

    _VFADE_SEQ += 1
    key = f"htc_ref_video_fade_{_VFADE_SEQ}"
    start_var = ContextVar(key, default=1000.0)
    fs = float(fade_start)
    es = float(end_strength)

    def _schedule(executor, noise, latent_image, sampler, sigmas, *args, **kwargs):
        try:
            sampling = executor.class_obj.model_patcher.get_model_object("model_sampling")
            start = float(sampling.timestep(sigmas[0]))
        except Exception:
            start = 1000.0
        tok = start_var.set(start)
        try:
            return executor(noise, latent_image, sampler, sigmas, *args, **kwargs)
        finally:
            start_var.reset(tok)

    def _scale_dense_v(v, spans, *, skip_reshape: bool):
        seq_len = int(v.shape[2] if skip_reshape else v.shape[1])
        out = None
        for a, b, s in spans:
            if float(s) >= 0.9999:
                continue
            lo = max(0, int(a))
            hi = min(seq_len, int(b))
            if hi <= lo:
                continue
            if out is None:
                out = v.clone()
            if skip_reshape:
                out[:, :, lo:hi, :].mul_(float(s))
            else:
                out[:, lo:hi, :].mul_(float(s))
        return out if out is not None else v

    def _wrapper(executor, x, timestep, context, transformer_options={}, **kwargs):
        payload = kwargs.get("minimax_payload")
        start = start_var.get()
        sigma = min(1.0, max(0.0, float(timestep.flatten()[0]) / max(start, 1e-8)))
        prog = 1.0 - sigma
        v_strength = _cosine_fade_strength(prog, fade_start=fs, end_strength=es)
        vx = x[0] if isinstance(x, (list, tuple)) else x
        ax = x[1] if isinstance(x, (list, tuple)) and len(x) > 1 else None
        spans = _ref_video_v_spans(payload, context, vx, ax, v_strength)
        if not spans:
            return executor(x, timestep, context, transformer_options=transformer_options, **kwargs)
        to = dict(transformer_options or {})
        to["_htc_ref_video_v_spans"] = spans
        prev_ov = to.get("optimized_attention_override")

        def _fade_override(func, q, k, v, heads, mask=None, attn_precision=None,
                           skip_reshape=False, skip_output_reshape=False, **akw):
            inner_to = dict(akw.get("transformer_options") or to)
            cur_spans = inner_to.get("_htc_ref_video_v_spans")
            if cur_spans and not inner_to.get("_htc_v_spans_applied"):
                inner_to["_htc_v_spans_applied"] = True
                if isinstance(v, AttentionTensorContainer):
                    vt = _scale_dense_v(v.take(), cur_spans, skip_reshape=skip_reshape)
                    v = AttentionTensorContainer(vt)
                else:
                    v = _scale_dense_v(v, cur_spans, skip_reshape=skip_reshape)
                akw["transformer_options"] = inner_to
            call_fn = prev_ov if prev_ov is not None else (func or optimized_attention)
            if prev_ov is not None:
                if isinstance(q, AttentionTensorContainer) and hasattr(prev_ov, "container_function"):
                    return prev_ov.container_function(
                        q, k, v, heads, mask=mask, attn_precision=attn_precision,
                        skip_reshape=skip_reshape, skip_output_reshape=skip_output_reshape, **akw)
                if isinstance(q, AttentionTensorContainer):
                    return prev_ov(
                        func or optimized_attention, q.take(), k.take(),
                        (v.take() if isinstance(v, AttentionTensorContainer) else v),
                        heads, mask=mask, attn_precision=attn_precision,
                        skip_reshape=skip_reshape, skip_output_reshape=skip_output_reshape, **akw)
                return prev_ov(
                    func or optimized_attention, q, k, v, heads, mask=mask,
                    attn_precision=attn_precision, skip_reshape=skip_reshape,
                    skip_output_reshape=skip_output_reshape, **akw)
            return call_fn(
                q, k, v, heads, mask=mask, attn_precision=attn_precision,
                skip_reshape=skip_reshape, skip_output_reshape=skip_output_reshape, **akw)

        _fade_override.container_function = lambda q, k, v, heads, **akw: _fade_override(None, q, k, v, heads, **akw)
        to["optimized_attention_override"] = _fade_override
        return executor(x, timestep, context, transformer_options=to, **kwargs)

    out = model.clone()
    out.add_wrapper_with_key(_pe.WrappersMP.OUTER_SAMPLE, key, _schedule)
    out.add_wrapper_with_key(_pe.WrappersMP.DIFFUSION_MODEL, key, _wrapper)
    return out


def qwen_stride():
    """Frames between the samples core shows Qwen of a reference video.

    Core's `FPS // 2`: a reference clip reaches the text encoder at 2 fps.
    Read from core so a change there moves this with it.
    """
    try:
        from comfy_extras.nodes_minimax_h3 import FPS
    except Exception:
        FPS = 24
    return max(1, int(FPS) // 2)


def looks_from(canvas, clip=False):
    """The pictures to keep for Qwen from one encoded source, as uint8.

    A still keeps itself. A clip keeps the frames core would sample for Qwen
    anyway, so a mod does not carry a whole clip's pixels to show two a
    second of it.
    """
    frames = canvas[::qwen_stride()] if clip else canvas
    return (frames[..., :3].float().clamp(0, 1) * 255.0).round().to(torch.uint8).cpu()


def hold_looks(looks):
    """Lay the kept pictures out as a reference clip Qwen sees one each of.

    Core snaps a reference video down to 17k+5 frames and samples it every
    `qwen_stride()` frames, so each picture is held for one stride and the
    last is held until the snapped length still reaches it. The last picture
    may be sampled twice; no earlier one is skipped.
    """
    stride = qwen_stride()
    n = int(looks.shape[0])
    need = max(5, stride * (n - 1) + 1)
    length = 5
    while length < need:
        length += 17
    idx = torch.clamp(torch.arange(length) // stride, max=n - 1)
    return looks[idx]


def presentation_pixels(vae, latent, cap_mp=0.0, looks=None, kind="image"):
    """IMAGE pixels for the text encoder.

    With `looks`, the pictures the builder encoded: sharp, one Qwen frame per
    picture. Without them, a decode of the stored latent -- the only view a
    mod written elsewhere, or before looks existed, can give. A decode of a
    stacked multi-still latent is also a clip the VAE invents between the
    stills, which is not what anybody photographed.

    Image mods come back `[1,H,W,C]`. Video mods come back `[T,H,W,C]`.
    `cap_mp` shrinks this view only. The latent handed to the DiT is the
    stored one.
    """
    try:
        from . import media as _media
    except ImportError:
        import media as _media

    if looks is not None:
        view = looks[:1] if kind == "image" else hold_looks(looks)
        return _cap(view.float() / 255.0, cap_mp, _media)
    pixels = vae.decode(latent)
    if pixels.ndim == 5 and pixels.shape[0] == 1 and pixels.shape[1] == 1:
        pixels = pixels[:, 0]
    elif pixels.ndim == 5 and pixels.shape[0] == 1:
        pixels = pixels[0]
    elif pixels.ndim == 5:
        pixels = pixels.reshape(-1, pixels.shape[-3], pixels.shape[-2], pixels.shape[-1])
    if pixels.ndim != 4 or pixels.shape[-1] != 3:
        _fail(f"VAE decode of a RefMod came back as {tuple(pixels.shape)}, "
              f"which is not an image batch")
    return _cap(pixels, cap_mp, _media)


def _cap(pixels, cap_mp, _media):
    h, w = int(pixels.shape[1]), int(pixels.shape[2])
    tw, th = _media._mp_cap_size(w, h, cap_mp)
    if (tw, th) != (w, h):
        samples = pixels.movedim(-1, 1).float()
        samples = F.interpolate(samples, size=(th, tw), mode="bicubic", align_corners=False)
        pixels = samples.movedim(1, -1).clamp_(0, 1)
    return pixels


def splice_blocks(cond, hop_images, hop_videos, image_ids, video_ids,
                  hop_audios=None, audio_ids=None):
    """Replace the blocks `ReferenceToVideo` just encoded for RefMod slots.

    `image_ids` / `video_ids` / `audio_ids` map `id(tensor)` to a RefMod block.
    Picture order is `hop_images`, then `hop_videos`, then `hop_audios`, which is
    the exact order Core builds `minimax_refs`.
    """
    import node_helpers

    images = list((hop_images or {}).values())
    videos = list((hop_videos or {}).values())
    audios = list((hop_audios or {}).values())
    # The maps are built once per run. A later hop that does not cite the
    # mod has no pixel of ours, and ReferenceToVideo then emits no
    # minimax_refs. That hop is finished. Splicing it was the hop-2 crash.
    has_img = any(id(t) in (image_ids or {}) for t in images)
    has_vid = any(id(t) in (video_ids or {}) for t in videos)
    has_aud = any(id(a) in (audio_ids or {}) for a in audios)
    if not (has_img or has_vid or has_aud):
        return cond
    blocks = None
    for entry in cond or []:
        meta = entry[1] if len(entry) > 1 else None
        if isinstance(meta, dict) and meta.get("minimax_refs"):
            blocks = meta["minimax_refs"]
            break
    if not blocks:
        _fail("This hop cites a RefMod but the conditioning has no "
              "minimax_refs. The video VAE has to be connected.")
    blocks = [dict(b) for b in blocks]

    def _prepare(index, block_or_list, expected):
        if index >= len(blocks):
            _fail(f"RefMod block {index} is past the {len(blocks)} reference "
                  f"blocks the encoder built")
        got = blocks[index].get("kind")
        if expected == "image" and got != "image":
            _fail(f"reference block {index} is '{got}', not the image a RefMod "
                  f"still has to replace")
        if expected == "video" and got not in ("video", "video_audio"):
            _fail(f"reference block {index} is '{got}', not the video a RefMod "
                  f"clip has to replace")
        if expected == "audio" and got != "audio":
            _fail(f"reference block {index} is '{got}', not the audio slot a "
                  f"RefMod audio latent has to replace")
        items = list(block_or_list) if isinstance(block_or_list, (list, tuple)) else [block_or_list]
        out_list = []
        for copy_i, blk in enumerate(items):
            placed = dict(blk)
            if expected == "audio":
                old_a = blocks[index].get("audio_latent")
                if torch.is_tensor(old_a) and torch.is_tensor(placed.get("audio_latent")):
                    placed["audio_latent"] = placed["audio_latent"].to(
                        device=old_a.device, dtype=old_a.dtype)
            else:
                old = blocks[index].get("latent")
                if torch.is_tensor(old) and torch.is_tensor(placed.get("latent")):
                    placed["latent"] = placed["latent"].to(device=old.device, dtype=old.dtype)
                # Carry encoded audio across on the first copy when a video clip carries sound.
                if got == "video_audio" and copy_i == 0:
                    placed["kind"] = "video_audio"
                    placed["ref_audio_t"] = blocks[index].get("ref_audio_t", 0)
                    placed["audio_latent"] = blocks[index].get("audio_latent")
            out_list.append(placed)
        return out_list

    replacements = {}
    for i, tensor in enumerate(images):
        blk = (image_ids or {}).get(id(tensor))
        if blk is not None:
            replacements[i] = _prepare(i, blk, "image")
    n_img = len(images)
    for j, tensor in enumerate(videos):
        blk = (video_ids or {}).get(id(tensor))
        if blk is not None:
            replacements[n_img + j] = _prepare(n_img + j, blk, "video")
    n_vis = n_img + len(videos)
    for k, aud in enumerate(audios):
        blk = (audio_ids or {}).get(id(aud))
        if blk is not None:
            replacements[n_vis + k] = _prepare(n_vis + k, blk, "audio")

    new_blocks = []
    for idx, orig in enumerate(blocks):
        if idx in replacements:
            new_blocks.extend(replacements[idx])
        else:
            new_blocks.append(orig)
    return node_helpers.conditioning_set_values(cond, {"minimax_refs": new_blocks})


# -- builder math ----------------------------------------------------------

def fit_token_budget(latent, budget, label):
    """Drop near-duplicate frames, then resample time, until tokens fit."""
    budget = int(budget or 0)
    if budget <= 0:
        return latent
    h, w = int(latent.shape[3]), int(latent.shape[4])
    per = (h // 2) * (w // 2)
    t = int(latent.shape[2])
    if per > budget:
        _fail(f"{label}: one frame costs {per} tokens, above the {budget} budget. "
              f"Lower the pool size.")
    if per * t <= budget:
        return latent
    flat = latent[0].float()
    kept = [0]
    prev = flat[:, 0]
    for i in range(1, t):
        cur = flat[:, i]
        denom = (cur.abs().mean() + prev.abs().mean()) / 2 + 1e-6
        if (cur - prev).abs().mean() / denom >= 0.02:
            kept.append(i)
            prev = cur
    if len(kept) < t:
        latent = latent[:, :, kept]
        t = int(latent.shape[2])
    if per * t > budget:
        fit_t = max(1, budget // per)
        idx = torch.linspace(0, t - 1, fit_t).round().long()
        latent = latent[:, :, idx]
    return latent


def metadata_for(name, kind, latent, mode, source, source_shape, pool, steps,
                 plan=None, description="", mask=None, looks=0,
                 concept_type="generic", default_step_curve="full"):
    t, h, w = (int(latent.shape[2]), int(latent.shape[3]), int(latent.shape[4]))
    role = str(concept_type or "generic").strip()
    if role not in CONCEPT_ROLES:
        role = "generic"
    sc = str(default_step_curve or "full").strip()
    if sc not in STEP_CURVES:
        sc = "full"
    return {
        "name": name,
        "kind": kind,
        "latent_h": h,
        "latent_w": w,
        "latent_t": t,
        "mode": mode,
        "source": source,
        "source_shape": source_shape,
        "pool": pool,
        "optimize_steps": int(steps or 0),
        "tags": [],
        "description": _clean_desc_text(description),
        "concept_type": role,
        "default_step_curve": sc,
        "mod_plan": plan if isinstance(plan, dict) else {},
        "subject_mask": mask if isinstance(mask, dict) else {},
        "looks": int(looks or 0),
        "_format_version": FORMAT_VERSION,
        "sample_rate": 32000,
    }


def save_latent(directory, name, latent, meta, looks=None):
    """Atomic write (v4 standalone). Returns the stem the rail stores in `file`."""
    from safetensors.torch import save_file

    stem = _clean_name(name)
    if not stem:
        _fail("refmod name is empty")
    directory = os.path.normpath(directory)
    dest = os.path.join(directory, stem.replace("/", os.sep) + ".safetensors")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".refmod-", suffix=".tmp",
                                     dir=os.path.dirname(dest) or ".")
    os.close(fd)
    try:
        tensors = {"latent": latent.detach().cpu().contiguous()}
        if looks is not None:
            tensors[LOOKS_KEY] = looks.to(torch.uint8).cpu().contiguous()
        save_file(tensors, temporary, metadata={META_KEY: json.dumps(meta)})
        os.replace(temporary, dest)
        _invalidate_header_cache(dest)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return stem


def encode_png_bytes_tensor(pixels_hwc) -> torch.Tensor:
    """Lossless 8-bit PNG byte tensor `[N]` (`uint8`) for compact v5 RefMod storage."""
    import io  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    arr = pixels_hwc
    if torch.is_tensor(arr):
        if arr.ndim == 4:
            arr = arr[0]
        arr = arr[..., :3].detach().cpu()
        if arr.dtype != torch.uint8:
            arr = (arr.float().clamp(0.0, 1.0) * 255.0).round().to(torch.uint8)
        arr = arr.numpy()
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG", optimize=True)
    return torch.frombuffer(bytearray(buf.getvalue()), dtype=torch.uint8).clone()


def infer_yaw_from_label(text: str) -> float | None:
    """Best-effort camera azimuth `yaw` in `(-180, 180]` from angle/pose words."""
    s = str(text or "").lower()
    if not s:
        return None
    if re.search(r"(?:^|[\W_])(?:back|rear|behind)(?:$|[\W_])", s):
        return 180.0
    if re.search(r"(?:^|[\W_])(?:left[_\s-]*profile|left[_\s-]*side)(?:$|[\W_])", s):
        return -90.0
    if re.search(r"(?:^|[\W_])(?:right[_\s-]*profile|right[_\s-]*side)(?:$|[\W_])", s):
        return 90.0
    if re.search(r"(?:^|[\W_])(?:three[_\s-]*quarter[_\s-]*left|3/4[_\s-]*left)(?:$|[\W_])", s):
        return -45.0
    if re.search(r"(?:^|[\W_])(?:three[_\s-]*quarter[_\s-]*right|3/4[_\s-]*right|three[_\s-]*quarter|3/4)(?:$|[\W_])", s):
        return 45.0
    if re.search(r"(?:^|[\W_])(?:front|frontal|headshot|portrait|closeup|straight)(?:$|[\W_])", s):
        return 0.0
    return None


def infer_shot_yaw(text: str) -> float | None:
    """Explicit camera-azimuth angle from shot beat/prose (avoids narrative false positives)."""
    s = str(text or "").lower()
    if not s:
        return None
    if re.search(r"\b(?:back view|rear view|from behind|over[- ]the[- ]shoulder)\b", s):
        return 180.0
    if re.search(r"\b(?:left[- ]profile|left side view|side profile left)\b", s):
        return -90.0
    if re.search(r"\b(?:right[- ]profile|right side view|side profile right)\b", s):
        return 90.0
    if re.search(r"\b(?:three[- ]quarter left|3/4 left)\b", s):
        return -45.0
    if re.search(r"\b(?:three[- ]quarter right|3/4 right)\b", s):
        return 45.0
    if re.search(r"\b(?:front view|frontal view|facing camera|straight[- ]on view)\b", s):
        return 0.0
    return None


def select_members_by_yaw(members, target_yaw: float = 0.0, max_views: int = 2):
    """Select the `max_views` nearest visual member indices by circular yaw distance."""
    vis = [(i, m) for i, m in enumerate(members or []) if isinstance(m, dict) and m.get("kind") != "audio"]
    if len(vis) <= max(1, int(max_views)):
        return [i for i, _m in vis]
    yaws = []
    for i, m in vis:
        y = m.get("yaw")
        if y is None:
            y = infer_yaw_from_label(m.get("name") or "")
        if y is None:
            return [i for i, _m in vis]
        yaws.append((i, float(y)))
    tgt = float(target_yaw)
    ranked = sorted(yaws, key=lambda item: abs(((item[1] - tgt + 180.0) % 360.0) - 180.0))
    return sorted(i for i, _y in ranked[:max(1, int(max_views))])


def save_v5_bundle(directory, name, members_specs, *, description="",
                   concept_type="identity", default_step_curve="full",
                   plan=None, mask=None, compact_png=False):
    """Atomic v5 bundle write (`ref_0..ref_N` + `looks_0..looks_N` + optional audio).

    Compatible with ComfyUI-MiniMaxH3Mod v0.2.6 `load_bundle` AND HTC multi-member
    `load_bundle_visuals` / `load_audio_latent`.
    """
    from safetensors.torch import save_file

    stem = _clean_name(name)
    if not stem:
        _fail("refmod name is empty")
    if not members_specs:
        _fail("v5 bundle needs at least one member")
    role = str(concept_type or "identity").strip()
    if role not in CONCEPT_ROLES:
        role = "generic"
    sc = str(default_step_curve or "full").strip()
    if sc not in STEP_CURVES:
        sc = "full"

    tensors = {}
    members_meta = []
    for i, spec in enumerate(members_specs):
        lat = spec["latent"].detach().cpu().clone().contiguous()
        tensors[f"ref_{i}"] = lat
        kind = str(spec["kind"])
        if kind == "audio":
            members_meta.append({
                "name": str(spec.get("name") or f"{stem}_voice"),
                "kind": "audio",
                "ref_audio_t": int(lat.shape[-1]),
                "sample_rate": int(spec.get("sample_rate") or 32000),
                "description": _clean_desc_text(spec.get("description") or description),
                "concept_type": role,
                "_format_version": FORMAT_VERSION,
            })
        else:
            looks = spec.get("looks")
            n_looks = 0
            if looks is not None:
                lk = looks.to(torch.uint8).cpu().contiguous()
                if compact_png and int(lk.shape[0]) == 1 and kind == "image":
                    tensors[f"enc_{i}"] = encode_png_bytes_tensor(lk[0])
                else:
                    tensors[f"looks_{i}"] = lk
                    if len(members_specs) == 1:
                        tensors[LOOKS_KEY] = lk
                n_looks = int(lk.shape[0])
            t, h, w = int(lat.shape[2]), int(lat.shape[3]), int(lat.shape[4])
            yaw_val = spec.get("yaw")
            if yaw_val is None:
                yaw_val = infer_yaw_from_label(spec.get("name") or "")
            m_entry = {
                "name": str(spec.get("name") or f"{stem}_{i}"),
                "kind": kind,
                "latent_h": h,
                "latent_w": w,
                "latent_t": t,
                "mode": str(spec.get("mode") or "encode"),
                "source": str(spec.get("source") or kind),
                "source_shape": str(spec.get("source_shape") or f"{t}x{h}x{w}"),
                "pool": str(spec.get("pool") or "encode"),
                "optimize_steps": 0,
                "tags": [],
                "description": _clean_desc_text(spec.get("description") or description),
                "concept_type": role,
                "default_step_curve": sc,
                "looks": n_looks,
                "_format_version": FORMAT_VERSION,
                "sample_rate": 32000,
            }
            if yaw_val is not None:
                m_entry["yaw"] = float(yaw_val)
            members_meta.append(m_entry)

    bundle_meta = {
        "_format_version": BUNDLE_VERSION,
        "kind": "bundle",
        "name": stem,
        "description": _clean_desc_text(description),
        "concept_type": role,
        "default_step_curve": sc,
        "mod_plan": plan if isinstance(plan, dict) else {},
        "subject_mask": mask if isinstance(mask, dict) else {},
        "members": members_meta,
    }
    directory = os.path.normpath(directory)
    dest = os.path.join(directory, stem.replace("/", os.sep) + ".safetensors")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".refmod-", suffix=".tmp",
                                     dir=os.path.dirname(dest) or ".")
    os.close(fd)
    try:
        save_file(tensors, temporary, metadata={META_KEY: json.dumps(bundle_meta)})
        os.replace(temporary, dest)
        _invalidate_header_cache(dest)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return stem


def update_meta(name, patch):
    """Header-only RefMod metadata edit (no VAE re-encode). Returns updated meta."""
    from safetensors import safe_open
    from safetensors.torch import save_file

    path = resolve(name)
    if path is None:
        _fail(f"refmod {name!r} not found")
    with safe_open(path, framework="pt", device="cpu") as fh:
        raw_hdr = dict(fh.metadata() or {})
        tensors = {k: fh.get_tensor(k).clone() for k in fh.keys()}
    # Write back under the key the header was read from. A RefLoRA keeps its
    # meta under h3_refmod_meta / minimax_h3_refmod_meta (or none at all); adding a
    # bare `refmod_meta` would win the next read and drop its kind and shape.
    meta_key = next((k for k in (META_KEY, AUDIO_META_KEY) + REFLORA_META_KEYS
                     if raw_hdr.get(k)), None)
    if meta_key is None:
        if not _is_reflora_file(path):
            _fail(f"{name} has no {META_KEY} header. It is not a RefMod.")
        meta_key = REFLORA_META_KEYS[0]
        meta = {k: v for k, v in (read_meta(path) or {}).items() if k != "_reflora"}
    else:
        meta = json.loads(raw_hdr[meta_key])
    if not isinstance(meta, dict):
        meta = {}
    if "description" in patch:
        meta["description"] = _clean_desc_text(patch["description"])
    if "concept_type" in patch or "role" in patch:
        r = str(patch.get("concept_type") or patch.get("role") or "generic").strip()
        if r in CONCEPT_ROLES:
            meta["concept_type"] = r
    if "default_step_curve" in patch:
        sc = str(patch["default_step_curve"] or "full").strip()
        if sc in STEP_CURVES:
            meta["default_step_curve"] = sc
    if "voice" in patch:
        mp = dict(meta.get("mod_plan") or {})
        v = str(patch.get("voice") or "").strip()
        vs = float(patch.get("voice_start") or 0.0)
        ve = float(patch.get("voice_end") or 0.0)
        if v:
            mp["voice"] = {"file": v, "start": vs, "end": ve} if (vs or ve) else v
        else:
            mp.pop("voice", None)
        meta["mod_plan"] = mp
    if meta.get("kind") == "bundle":
        for m in meta.get("members") or []:
            if isinstance(m, dict):
                if "description" in patch:
                    m["description"] = meta["description"]
                if "concept_type" in meta:
                    m["concept_type"] = meta["concept_type"]
                if "default_step_curve" in meta:
                    m["default_step_curve"] = meta["default_step_curve"]

    raw_hdr[meta_key] = json.dumps(meta)
    fd, temporary = tempfile.mkstemp(prefix=".refmod-", suffix=".tmp",
                                     dir=os.path.dirname(path) or ".")
    os.close(fd)
    try:
        save_file(tensors, temporary, metadata=raw_hdr)
        os.replace(temporary, path)
        _invalidate_header_cache(path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return meta


def remove_member(name, member_idx):
    """Remove member `member_idx` from a v5 bundle without re-encoding."""
    from safetensors import safe_open
    from safetensors.torch import save_file

    path = resolve(name)
    if path is None:
        _fail(f"refmod {name!r} not found")
    with safe_open(path, framework="pt", device="cpu") as fh:
        raw_hdr = dict(fh.metadata() or {})
        meta = json.loads(raw_hdr.get(META_KEY) or "{}")
        if meta.get("kind") != "bundle":
            _fail(f"{name} is not a multi-member bundle")
        members = list(meta.get("members") or [])
        idx = int(member_idx)
        if idx < 0 or idx >= len(members):
            _fail(f"member index {idx} out of range (0..{len(members) - 1})")
        if len(members) <= 1:
            _fail("cannot remove the last remaining member from a bundle")
        old_tensors = {k: fh.get_tensor(k).clone() for k in fh.keys()}

    # Per-member tensors are renumbered with their member: latent, kept photos
    # (`looks_N`) and compact PNG photos (`enc_N`). Anything else rides through.
    per_member = re.compile(r"^(ref|looks|enc)_(\d+)$")
    new_members = []
    new_tensors = {k: v for k, v in old_tensors.items() if not per_member.match(k)}
    ni = 0
    for oi, m in enumerate(members):
        if oi == idx:
            continue
        new_members.append(m)
        for pre in ("ref", "looks", "enc"):
            if f"{pre}_{oi}" in old_tensors:
                new_tensors[f"{pre}_{ni}"] = old_tensors[f"{pre}_{oi}"]
        ni += 1
    meta["members"] = new_members
    raw_hdr[META_KEY] = json.dumps(meta)
    fd, temporary = tempfile.mkstemp(prefix=".refmod-", suffix=".tmp",
                                     dir=os.path.dirname(path) or ".")
    os.close(fd)
    try:
        save_file(new_tensors, temporary, metadata=raw_hdr)
        os.replace(temporary, path)
        _invalidate_header_cache(path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return meta


def inspect_refmod(name):
    """Rich header+member inspection for UI without heavy decoding."""
    path = resolve(name)
    if path is None:
        return None
    meta = read_meta(path)
    if not isinstance(meta, dict):
        return None
    summary = _meta_summary(meta, full=path)
    voice = _listed_voice(meta)
    members_out = []
    if meta.get("kind") == "bundle":
        for i, m in enumerate(meta.get("members") or []):
            if not isinstance(m, dict):
                continue
            members_out.append({
                "index": i,
                "name": str(m.get("name") or f"member_{i}"),
                "kind": str(m.get("kind") or "image"),
                "tokens": _member_tokens(m),
                "shape": [int(m.get("latent_t") or 1), int(m.get("latent_h") or 0), int(m.get("latent_w") or 0)],
                "has_looks": bool(int(m.get("looks") or 0)) or summary["has_looks"],
            })
    else:
        members_out.append({
            "index": 0,
            "name": str(meta.get("name") or name),
            "kind": summary["kind"],
            "tokens": summary["tokens"],
            "shape": [int(meta.get("latent_t") or 1), int(meta.get("latent_h") or 0), int(meta.get("latent_w") or 0)],
            "has_looks": summary["has_looks"],
        })
    return {
        "name": _clean_name(name),
        "description": description_of(meta),
        "voice": voice,
        "mod_plan": stored_plan(name),
        "subject_mask": meta.get("subject_mask") or {},
        "members": members_out,
        **summary,
    }


def thumb_bytes(name, member_idx=0, width=192):
    """Return JPEG bytes for a RefMod thumbnail from `looks`/`enc_` (no VAE decode)."""
    import io  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    path = resolve(name)
    if path is None:
        return None
    meta = read_meta(path) or {}
    idx = max(0, int(member_idx or 0))
    w = max(48, min(384, int(width or 192)))
    try:
        st = os.stat(path)
        sig = f"{path}|{int(st.st_mtime)}|{st.st_size}|{idx}|{w}"
    except OSError:
        sig = f"{path}|{idx}|{w}"
    hkey = hashlib.sha1(sig.encode("utf-8", "ignore")).hexdigest()[:24]
    try:
        import folder_paths
        cdir = os.path.join(folder_paths.get_temp_directory(), "h3_refmod_thumbs")
    except Exception:
        cdir = os.path.join(tempfile.gettempdir(), "h3_refmod_thumbs")
    os.makedirs(cdir, exist_ok=True)
    cached = os.path.join(cdir, f"{hkey}.jpg")
    if os.path.isfile(cached) and os.path.getsize(cached) > 0:
        with open(cached, "rb") as fh:
            return fh.read()

    looks = None
    if meta.get("_reflora"):
        looks = _first_tensor(
            _load_looks(path, f"refmod.looks_{idx}"),
            _load_looks(path, "refmod.looks"),
            _load_looks(path, LOOKS_KEY),
        )
    elif meta.get("kind") == "bundle":
        looks = _first_tensor(
            _load_looks(path, f"looks_{idx}"),
            _load_looks(path, LOOKS_KEY) if idx == 0 else None,
            _load_enc_jpegs(path, [idx]),
        )
    else:
        looks = _first_tensor(_load_looks(path, LOOKS_KEY), _load_enc_jpegs(path))

    if looks is None:
        return None
    frame_idx = min(idx, int(looks.shape[0]) - 1) if meta.get("kind") != "bundle" else 0
    arr = looks[frame_idx].detach().cpu().numpy()
    im = Image.fromarray(arr.astype(np.uint8))
    im.thumbnail((w, w), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=84, optimize=True)
    data = buf.getvalue()
    try:
        tmp = cached + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, cached)
    except OSError:
        pass
    return data


def vision_data_urls(name, member_indices=None, max_images=4, max_side=1024):
    """JPEG data-URLs (`data:image/jpeg;base64,...`) from a RefMod's stored `looks`."""
    import base64  # noqa: PLC0415
    import io  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    path = resolve(name)
    if path is None:
        return []
    meta = read_meta(path) or {}
    cap_n = max(1, int(max_images or 4))
    side = max(256, min(2048, int(max_side or 1024)))
    urls = []

    def _arr_to_url(arr):
        im = Image.fromarray(arr.astype(np.uint8))
        if im.mode != "RGB":
            im = im.convert("RGB")
        if max(im.size) > side:
            im.thumbnail((side, side), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=88)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    if meta.get("kind") == "bundle":
        members = [m for m in (meta.get("members") or []) if isinstance(m, dict)]
        vis_indices = [i for i, m in enumerate(members) if m.get("kind") in ("image", "video")]
        if member_indices:
            wanted = [i for i in member_indices if i in vis_indices]
            if wanted:
                vis_indices = wanted
        for idx in vis_indices[:cap_n]:
            lk = _first_tensor(
                _load_looks(path, f"looks_{idx}"),
                _load_looks(path, LOOKS_KEY) if idx == 0 else None,
                _load_enc_jpegs(path, [idx]),
            )
            if lk is not None and int(lk.shape[0]) > 0:
                urls.append(_arr_to_url(lk[0].detach().cpu().numpy()))
    else:
        if meta.get("_reflora"):
            lk = _first_tensor(
                _load_looks(path, "refmod.looks_0"),
                _load_looks(path, "refmod.looks"),
                _load_looks(path, LOOKS_KEY),
            )
        else:
            lk = _first_tensor(_load_looks(path, LOOKS_KEY), _load_enc_jpegs(path))
        if lk is not None and int(lk.shape[0]) > 0:
            n_f = int(lk.shape[0])
            picks = [0] if (cap_n == 1 or n_f == 1) else sorted({round(j * (n_f - 1) / max(1, min(cap_n, n_f) - 1)) for j in range(min(cap_n, n_f))})
            for fi in picks:
                urls.append(_arr_to_url(lk[fi].detach().cpu().numpy()))

    if not urls:
        plan = stored_plan(name) or {}
        stills = [s for s in (plan.get("stills") or []) if isinstance(s, str) and s.strip()]
        if stills:
            try:
                from . import media as _media
            except ImportError:
                import media as _media
            for s in stills[:cap_n]:
                u = _media.vision_data_url(s, max_side=side)
                if u:
                    urls.append(u)
    return urls


def vision_data_url(name, member_idx=0, max_side=1024):
    """Single JPEG data-URL from a RefMod's stored `looks` (or None)."""
    idx = None if member_idx is None else [max(0, int(member_idx or 0))]
    urls = vision_data_urls(name, member_indices=idx, max_images=1, max_side=max_side)
    return urls[0] if urls else None


def preview_mask_png(image_name, subject_mask="auto_rembg", background_retention=0.0,
                     background_mode="blur_bg", crop_margin=0.0, max_side=512):
    """Render side-by-side / isolated PNG preview bytes for `image_name` in `h3_refs/`."""
    import io  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    try:
        from . import media as _media
    except ImportError:
        import media as _media

    px = _media.load_image(image_name)
    if px is None:
        _fail(f"{image_name} could not be loaded from h3_refs")
    tw, th = canvas_size(px, short=min(512, int(max_side or 512)))
    canvas = to_canvas(px, tw, th, fit_mode="crop")
    mode = str(subject_mask or "off").strip().lower()
    if mode in ("auto", "auto_rembg", "auto_sam"):
        backend = "auto_sam" if mode == "auto_sam" else "auto_rembg"
        m = refine_cutout(cutout_masks(canvas, backend=backend), canvas)
        if float(crop_margin or 0.0) > 0.0:
            canvas, m = crop_to_subject(canvas, m, margin=float(crop_margin))
        out = isolate_subject(canvas, m, retention=float(background_retention or 0.0),
                              mode=background_mode)
    else:
        out = canvas
    arr = (out[0, ..., :3].float().clamp(0, 1) * 255.0).round().byte().cpu().numpy()
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def canvas_for_hw(h, w, short=1024):
    """The `(tw, th)` a source of this size lands on. Never upscales.

    Split out from `canvas_size` so the panel's estimate can ask about a
    file's dimensions without decoding it, and get the same answer the
    build will.
    """
    h, w = int(h), int(w)
    if h < 1 or w < 1:
        _fail(f"a source cannot be {w}x{h}")
    scale = 1.0 if min(h, w) <= short else short / float(min(h, w))
    tw = max(32, int(round(w * scale) / 32) * 32)
    th = max(32, int(round(h * scale) / 32) * 32)
    tw = min(tw, max(32, w // 32 * 32))
    th = min(th, max(32, h // 32 * 32))
    return tw, th


def canvas_size(frames, short=1024):
    """The `(tw, th)` `fit_canvas` would pick for `[T,H,W,C]`."""
    if frames.ndim != 4 or frames.shape[-1] < 3:
        _fail(f"builder frames must be [T,H,W,C], got {tuple(frames.shape)}")
    return canvas_for_hw(int(frames.shape[1]), int(frames.shape[2]), short)


def frame_tokens(tw, th, factor=16):
    """DiT tokens one latent frame of this canvas costs.

    The H3 VAE is 16x spatial and the DiT patchifies 2x2, so a 1024x1280
    canvas is an 80x64 latent and 1280 tokens -- which is what a real
    built mod measures.
    """
    return max(1, (int(th) // factor // 2) * (int(tw) // factor // 2))


def to_canvas(frames, tw, th, fit_mode="crop"):
    """Resize `[T,H,W,C]` onto an exact canvas.

    `fit_mode`:
      * `crop` (default): aspect-preserving center cover-crop (never stretches!).
      * `pad`: aspect-preserving fit inside `(tw, th)` padded with edge neutral.
      * `stretch`: legacy resize (`disabled` crop).
    """
    import comfy.utils

    if frames.ndim != 4 or frames.shape[-1] < 3:
        _fail(f"builder frames must be [T,H,W,C], got {tuple(frames.shape)}")
    tw, th = int(tw), int(th)
    fh, fw = int(frames.shape[1]), int(frames.shape[2])
    mode = str(fit_mode or "crop").strip().lower()
    samples = frames[..., :3].movedim(-1, 1)
    if mode == "pad" and (fw * th != fh * tw):
        scale = min(tw / float(fw), th / float(fh))
        rw = max(1, min(tw, int(round(fw * scale))))
        rh = max(1, min(th, int(round(fh * scale))))
        scaled = comfy.utils.common_upscale(samples, rw, rh, "lanczos", "disabled")
        pad_l = (tw - rw) // 2
        pad_r = tw - rw - pad_l
        pad_t = (th - rh) // 2
        pad_b = th - rh - pad_t
        padded = F.pad(scaled, (pad_l, pad_r, pad_t, pad_b), mode="constant", value=0.5)
        return padded.movedim(1, -1)
    crop_arg = "disabled" if mode == "stretch" else "center"
    samples = comfy.utils.common_upscale(samples, tw, th, "lanczos", crop_arg)
    return samples.movedim(1, -1)


def fit_canvas(frames, short=1024, fit_mode="crop"):
    """Resize `[T,H,W,C]` onto the 32px grid, short edge at most `short`.

    Never upscales. A still and a clip share this so the VAE sees the same
    class of canvas the reference pipeline does.
    """
    tw, th = canvas_size(frames, short)
    return to_canvas(frames, tw, th, fit_mode=fit_mode)


def stack_latents(parts, label):
    """Concatenate `[1,24,T,H,W]` encodes along time into one visual mod.

    This is how several stills and a clip become a single RefMod rather
    than a version-5 bundle: `load_visual` reads one latent, and `_as_visual`
    already calls anything with `T > 1` a video mod. A bundle would hand the
    rail its first member and drop the rest.
    """
    parts = [p for p in parts if p is not None]
    if not parts:
        _fail(f"{label}: nothing to encode")
    head = parts[0]
    for i, p in enumerate(parts[1:], start=1):
        if p.shape[3:] != head.shape[3:]:
            _fail(f"{label}: source {i} encoded to {tuple(p.shape[2:])}, which "
                  f"does not stack onto {tuple(head.shape[2:])}. Sources must "
                  f"share a canvas.")
    if len(parts) == 1:
        return parts[0]
    return torch.cat([p.to(dtype=head.dtype, device=head.device) for p in parts], dim=2)


def snap_video_frames(frames):
    """Core's reference-video length: at least 5, and `n % 17 == 5`."""
    n = int(frames.shape[0])
    if n < 5:
        _fail(f"a video RefMod needs at least 5 frames (got {n})")
    while n % 17 != 5:
        n -= 1
    if n < 5:
        _fail(f"a video RefMod needs at least 5 frames after the 17k+5 snap "
              f"(started at {int(frames.shape[0])})")
    return frames[:n]
