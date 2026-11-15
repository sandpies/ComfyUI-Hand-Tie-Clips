"""Reference Bible (user-local storage outside git), label resolution, and ethnicity/subject helpers."""
from __future__ import annotations

import json
import os
import re
import threading

from .. import refs as _refs

HERE = os.path.dirname(os.path.abspath(__file__))
PACK_ROOT = os.path.dirname(HERE)
_LOCK = threading.Lock()


def user_data_dir() -> str:
    """User-local data directory outside the git repo (safe for ComfyUI registry & multi-user installs)."""
    base = ""
    try:
        import folder_paths  # type: ignore  # noqa: PLC0415
        if hasattr(folder_paths, "get_user_directory"):
            base = os.path.join(folder_paths.get_user_directory(), "default", "htc_sandtie")
    except Exception:
        base = ""
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".htc_sandtie")
    os.makedirs(base, exist_ok=True)
    return base


def _migrate_legacy_json(filename: str, target_path: str) -> None:
    """No-op: Reference Bible data lives in user_data_dir() only."""
    return


def ref_bank_path() -> str:
    p = os.path.join(user_data_dir(), "ref_bank.json")
    _migrate_legacy_json("ref_bank.json", p)
    return p


def thumb_cache_dir() -> str:
    d = os.path.join(user_data_dir(), "thumb_cache")
    os.makedirs(d, exist_ok=True)
    return d


def _slugify_tag(raw: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", str(raw or "").strip().lstrip("@").lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "ref"


def _human_name_from_filename(fname: str) -> str:
    stem = os.path.splitext(os.path.basename(str(fname or "")))[0]
    stem = re.sub(r"^(?:char|sub|ref|fg|img)_+", "", stem, flags=re.I)
    stem = re.sub(r"_+(?:sheet|turnaround|lookbook|face|body|portrait|ref|\d+)$", "", stem, flags=re.I)
    parts = [p.capitalize() for p in re.split(r"[_\-\s]+", stem) if p]
    return " ".join(parts[:3]) or "Reference"


_GENERIC_VOICE_STEM_TOKENS = {
    "sheet", "turnaround", "lookbook", "face", "body", "ref", "front", "back",
    "side", "view", "full", "portrait", "profile", "closeup", "three", "quarter",
    "outfit", "prop", "hero", "plate", "img", "image", "cast", "shot",
}
_EXT_STILL_FILE_RX = re.compile(
    r"_(?:front_portrait|three_quarter|full_body|side_profile|back_view|closeup_face|outfit_prop)_\d+\.(?:png|jpe?g|webp)$",
    re.I,
)


def _guess_matching_voice_file(fname: str, refs_dir_path: str) -> str:
    if not fname or not refs_dir_path or not os.path.isdir(refs_dir_path):
        return ""
    stem = os.path.splitext(os.path.basename(fname))[0].lower()
    tokens = [
        t for t in re.split(r"[_\-\s]+", stem)
        if len(t) >= 3 and not t.isdigit() and t not in _GENERIC_VOICE_STEM_TOKENS
    ]
    if not tokens:
        return ""
    lead_tok = tokens[0]
    audio_exts = (".wav", ".mp3", ".flac", ".ogg", ".m4a")
    try:
        files = sorted(os.listdir(refs_dir_path))
    except OSError:
        return ""
    for f in files:
        if not f.lower().endswith(audio_exts):
            continue
        f_low = os.path.splitext(f)[0].lower()
        if f_low == lead_tok or f_low.startswith(lead_tok + "_") or f_low.startswith(lead_tok + "-"):
            return f
    return ""


def _read_raw_ref_bank_doc() -> tuple[list[dict], set[str]]:
    path = ref_bank_path()
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        if isinstance(d, list):
            return [x for x in d if isinstance(x, dict)], set()
        if isinstance(d, dict):
            items = [x for x in (d.get("items") or []) if isinstance(x, dict)]
            deleted = {str(x).strip() for x in (d.get("deleted_files") or []) if str(x).strip()}
            return items, deleted
    except Exception:
        pass
    return [], set()


def _write_raw_ref_bank(items: list[dict], deleted_files: set[str] | None = None) -> None:
    path = ref_bank_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if deleted_files is None:
        _, deleted_files = _read_raw_ref_bank_doc()
    payload = {
        "version": 1,
        "deleted_files": sorted(deleted_files),
        "items": items,
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _unique_ref_bank_id(tag: str, used_ids: set[str]) -> str:
    base = f"rb_{_slugify_tag(tag)}"
    if base not in used_ids:
        used_ids.add(base)
        return base
    i = 2
    while f"{base}_{i}" in used_ids:
        i += 1
    cand = f"{base}_{i}"
    used_ids.add(cand)
    return cand


def _resolve_refs_dir() -> str:
    try:
        from .. import media as _media
        return _media.refs_dir()
    except Exception:
        return ""


def _load_vision_cache() -> dict:
    try:
        from . import vision_cv as _vcv
        return _vcv._load_cache()
    except Exception:
        return {}


def _refmod_module():
    try:
        from .. import refmod as _refmod  # noqa: PLC0415
        return _refmod
    except Exception:
        return None


def _clean_ref_file(raw_file: str, source: str = "image") -> str:
    raw = str(raw_file or "").strip()
    if not raw:
        return ""
    if str(source or "").strip().lower() == "refmod":
        cleaned = raw.replace("\\", "/").strip("/")
        if cleaned.lower().endswith(".safetensors"):
            cleaned = cleaned[: -len(".safetensors")]
        parts = [p for p in cleaned.split("/") if p]
        if any(p in (".", "..") for p in parts):
            return ""
        return "/".join(parts)
    return os.path.basename(raw)


def _norm_strength(val, default: float = 1.0) -> float:
    if val in (None, ""):
        return default
    try:
        return max(0.0, min(3.0, round(float(val), 4)))
    except (TypeError, ValueError):
        return default


def _norm_step_curve(val, default: str = "full") -> str:
    sc = str(val or default).strip().lower()
    return sc if sc in ("full", "early_lock", "late_detail", "fade", "mid_peak") else default


def _norm_members(val) -> list[int] | None:
    if not isinstance(val, (list, tuple)):
        return None
    out: list[int] = []
    for x in val:
        try:
            xi = int(x)
        except (TypeError, ValueError):
            continue
        if xi >= 0 and xi not in out:
            out.append(xi)
    return out or None


def _refmod_role_to_bible_role(rm_role: str) -> str:
    r = str(rm_role or "").strip().lower()
    if r == "background":
        return "place"
    if r == "helper":
        return "prop"
    return "subject"


def _deleted_key(fname: str, source: str = "image") -> str:
    return f"refmod:{fname}" if source == "refmod" else fname


def load_ref_bank() -> list[dict]:
    """Load saved Reference Bible entries, seeding vision scans and models/refmods/ RefMods."""
    with _LOCK:
        items, deleted_files = _read_raw_ref_bank_doc()
        refs_d = _resolve_refs_dir()
        rm_mod = _refmod_module()
        rm_list = []
        rm_by_name: dict[str, dict] = {}
        if rm_mod is not None:
            try:
                rm_list = list(rm_mod.listing() or [])
                rm_by_name = {str(x.get("name") or "").lower(): x for x in rm_list if isinstance(x, dict) and x.get("name")}
            except Exception:
                rm_list = []
                rm_by_name = {}

        by_key: dict[tuple[str, str], dict] = {}
        seen_ids: set[str] = set()
        cleaned_items: list[dict] = []
        changed = False

        for raw in items:
            source = "refmod" if str(raw.get("source") or "").strip().lower() == "refmod" else "image"
            fname = _clean_ref_file(raw.get("file") or "", source)
            if not fname:
                continue
            # Auto-heal legacy duplicate where a RefMod was accidentally saved with source="image"
            if source == "image" and "." not in os.path.basename(fname) and fname.lower() in rm_by_name:
                source = "refmod"
                fname = _clean_ref_file(fname, "refmod")
                changed = True
            # Auto-prune unedited RefMod Maker sheet-extractor intermediate stills when the RefMod exists
            desc_raw = str(raw.get("desc") or "").strip()
            if (
                source == "image"
                and not raw.get("user_edited")   # never prune an entry the user touched
                and _EXT_STILL_FILE_RX.search(fname)
                and desc_raw.startswith(("Using the exact ", "Isolate the exact "))
            ):
                changed = True
                continue
            tag = _slugify_tag(raw.get("tag") or _human_name_from_filename(fname.rsplit("/", 1)[-1]))
            rid = str(raw.get("id") or "").strip()
            if not rid or rid in seen_ids:
                rid = _unique_ref_bank_id(tag, seen_ids)
                changed = True
            else:
                seen_ids.add(rid)
            role = str(raw.get("role") or "subject").strip().lower()
            if role not in ("subject", "place", "prop"):
                role = "subject"
            voice = os.path.basename(str(raw.get("voice") or "").strip())
            if source == "image" and role == "subject" and not voice and refs_d:
                guessed = _guess_matching_voice_file(fname, refs_d)
                if guessed:
                    voice = guessed
                    changed = True
            base_label = fname.rsplit("/", 1)[-1]
            if base_label.lower().startswith("lora:"):
                base_label = base_label[5:]
            entry = {
                "id": rid,
                "name": str(raw.get("name") or _human_name_from_filename(base_label)).strip(),
                "char_name": str(raw.get("char_name") or "").strip(),
                "tag": tag,
                "role": role,
                "file": fname,
                "source": source,
                "voice": voice,
                "desc": str(raw.get("desc") or "").strip(),
                "locked": str(raw.get("locked") or "").strip(),
                "context": str(raw.get("context") or "").strip(),
                "user_edited": bool(raw.get("user_edited", False)),
                "mtime": int(raw.get("mtime") or 0),
            }
            if source == "refmod":
                entry["strength"] = _norm_strength(raw.get("strength"), 1.0)
                entry["step_curve"] = _norm_step_curve(raw.get("step_curve"), "full")
                mems = _norm_members(raw.get("members"))
                if mems:
                    entry["members"] = mems
                rm_info = rm_by_name.get(fname.lower())
                if rm_info:
                    if not entry["desc"] and rm_info.get("description"):
                        entry["desc"] = str(rm_info["description"]).strip()
                        changed = True
                    if not entry["voice"] and (rm_info.get("voice") or {}).get("file"):
                        entry["voice"] = os.path.basename(str(rm_info["voice"]["file"]).strip())
                        changed = True
                    if not entry["user_edited"] and rm_info.get("default_step_curve") and entry["step_curve"] == "full":
                        entry["step_curve"] = _norm_step_curve(rm_info["default_step_curve"], "full")
                    entry["refmod_format"] = str(rm_info.get("format") or "v4")
                    entry["refmod_role"] = str(rm_info.get("role") or "generic")
                    entry["refmod_tokens"] = int(rm_info.get("tokens") or 0)
                    entry["refmod_has_looks"] = bool(rm_info.get("has_looks"))
                    entry["refmod_members"] = int(rm_info.get("members_count") or 1)
                    entry["refmod_has_audio"] = bool(rm_info.get("has_audio_latent"))
            if not entry["char_name"] and role == "subject":
                entry["char_name"] = extract_char_name_from_tag(tag, entry["name"]) or entry["name"].split()[0]
            fk = (source, fname.lower())
            if fk in by_key:
                changed = True
                continue
            by_key[fk] = entry
            cleaned_items.append(entry)

        # Seed unbanked image scans from vision cache
        vcache = _load_vision_cache()
        if isinstance(vcache, dict) and vcache:
            for k, desc_val in sorted(vcache.items()):
                if not isinstance(desc_val, str) or not desc_val.strip():
                    continue
                parts = str(k).split("|")
                if len(parts) < 4 or not parts[0].startswith("refscan_"):
                    continue
                fpath, _, role_k = parts[1], parts[2], parts[3]
                fname = os.path.basename(fpath)
                if not fname or fname in deleted_files or ("image", fname.lower()) in by_key:
                    continue
                d_str = desc_val.strip()
                if is_studio_backdrop_text(d_str):
                    continue
                if refs_d and not os.path.isfile(os.path.join(refs_d, fname)):
                    continue
                role = "place" if (role_k == "place" or d_str.lower().startswith("set:")) else ("prop" if (role_k == "prop" or d_str.lower().startswith("prop:")) else "subject")
                tag = _slugify_tag(os.path.splitext(fname)[0])
                hname = _human_name_from_filename(fname)
                clean_d = clean_subject_scan_desc(d_str) if role == "subject" else re.sub(r"^(?:Set|Prop):\s*", "", d_str, flags=re.I).strip()
                if not clean_d:
                    continue
                entry = {
                    "id": _unique_ref_bank_id(tag, seen_ids),
                    "name": hname,
                    "char_name": extract_char_name_from_tag(tag, hname) if role == "subject" else "",
                    "tag": tag,
                    "role": role,
                    "file": fname,
                    "source": "image",
                    "voice": _guess_matching_voice_file(fname, refs_d) if role == "subject" and refs_d else "",
                    "desc": clean_d,
                    "locked": "",
                    "context": "",
                    "user_edited": False,
                    "mtime": int(os.path.getmtime(os.path.join(refs_d, fname))) if (refs_d and os.path.isfile(os.path.join(refs_d, fname))) else 0,
                }
                by_key[("image", fname.lower())] = entry
                cleaned_items.append(entry)
                changed = True

        # Seed unbanked RefMods from models/refmods/ (and unified RefLoRAs)
        for rm_info in rm_list:
            if not isinstance(rm_info, dict) or rm_info.get("kind") == "audio":
                continue
            rname = _clean_ref_file(rm_info.get("name") or "", "refmod")
            if not rname:
                continue
            del_tok = _deleted_key(rname, "refmod")
            if del_tok in deleted_files or ("refmod", rname.lower()) in by_key:
                continue
            role = _refmod_role_to_bible_role(rm_info.get("role") or "generic")
            base_label = rname.rsplit("/", 1)[-1]
            if base_label.lower().startswith("lora:"):
                base_label = base_label[5:]
            tag = _slugify_tag(base_label)
            hname = _human_name_from_filename(base_label)
            rm_path = rm_mod.resolve(rname) if rm_mod is not None else None
            rm_mtime = 0
            if rm_path and os.path.isfile(rm_path):
                try:
                    rm_mtime = int(os.path.getmtime(rm_path))
                except OSError:
                    rm_mtime = 0
            entry = {
                "id": _unique_ref_bank_id(f"{tag}_mod", seen_ids),
                "name": hname,
                "char_name": extract_char_name_from_tag(tag, hname) if role == "subject" else "",
                "tag": tag,
                "role": role,
                "file": rname,
                "source": "refmod",
                "voice": os.path.basename(str((rm_info.get("voice") or {}).get("file") or "").strip()),
                "desc": str(rm_info.get("description") or "").strip(),
                "locked": "",
                "context": "",
                "strength": 1.0,
                "step_curve": _norm_step_curve(rm_info.get("default_step_curve"), "full"),
                "user_edited": False,
                "mtime": rm_mtime,
                "refmod_format": str(rm_info.get("format") or "v4"),
                "refmod_role": str(rm_info.get("role") or "generic"),
                "refmod_tokens": int(rm_info.get("tokens") or 0),
                "refmod_has_looks": bool(rm_info.get("has_looks")),
                "refmod_members": int(rm_info.get("members_count") or 1),
                "refmod_has_audio": bool(rm_info.get("has_audio_latent")),
            }
            by_key[("refmod", rname.lower())] = entry
            cleaned_items.append(entry)
            changed = True

        if changed or not os.path.isfile(ref_bank_path()):
            _persist_keys = (
                "id", "name", "char_name", "tag", "role", "file", "source",
                "voice", "desc", "locked", "context", "user_edited", "mtime",
                "strength", "step_curve", "members",
            )
            disk_items = [{k: v for k, v in it.items() if k in _persist_keys} for it in cleaned_items]
            _write_raw_ref_bank(disk_items, deleted_files=deleted_files)
        cleaned_items.sort(key=lambda x: ({"subject": 0, "place": 1, "prop": 2}.get(x["role"], 9), 1 if x.get("source") == "refmod" else 0, x["name"].lower()))
        return cleaned_items


def sync_refmods_to_bank() -> list[dict]:
    """Clear RefMod dismissals and re-seed all RefMods on disk into Reference Bible."""
    with _LOCK:
        items, deleted_files = _read_raw_ref_bank_doc()
        next_deleted = {d for d in deleted_files if not d.startswith("refmod:")}
        if next_deleted != deleted_files:
            _write_raw_ref_bank(items, deleted_files=next_deleted)
    return load_ref_bank()


def find_ref_bank_entry(file_name: str = "", tag: str = "", bank: list[dict] | None = None, source: str = "") -> dict | None:
    items = bank if bank is not None else load_ref_bank()
    src_want = str(source or "").strip().lower()
    f_raw = str(file_name or "").strip()
    f_clean_rm = _clean_ref_file(f_raw, "refmod").lower()
    f_clean_img = os.path.basename(f_raw).lower()
    t_clean = str(tag or "").lstrip("@").strip().lower()
    if f_raw:
        if src_want:
            target_f = f_clean_rm if src_want == "refmod" else f_clean_img
            for it in items:
                it_src = str(it.get("source") or "image").lower()
                if it_src == src_want and _clean_ref_file(it.get("file") or "", it_src).lower() == target_f:
                    return it
        for it in items:
            it_src = str(it.get("source") or "image").lower()
            it_f = _clean_ref_file(it.get("file") or "", it_src).lower()
            if it_f == (f_clean_rm if it_src == "refmod" else f_clean_img):
                return it
    if t_clean:
        for it in items:
            if str(it.get("tag") or "").lower() == t_clean:
                return it
    return None


def upsert_ref_bank_item(item: dict, *, user_edited: bool = True) -> dict:
    source = "refmod" if str(item.get("source") or "").strip().lower() == "refmod" else "image"
    fname = _clean_ref_file(item.get("file") or "", source)
    if not fname:
        raise ValueError("Reference Bible item requires a file name.")
    with _LOCK:
        items, deleted_files = _read_raw_ref_bank_doc()
        deleted_files.discard(fname)
        deleted_files.discard(_deleted_key(fname, source))
        rid = str(item.get("id") or "").strip()
        used_ids = {str(x.get("id") or "") for x in items if x.get("id")}
        existing_idx = next(
            (
                i for i, x in enumerate(items)
                if (rid and x.get("id") == rid)
                or (
                    str(x.get("source") or "image").lower() == source
                    and _clean_ref_file(x.get("file") or "", source).lower() == fname.lower()
                )
            ),
            None,
        )
        old = items[existing_idx] if existing_idx is not None else {}
        base_label = fname.rsplit("/", 1)[-1]
        if base_label.lower().startswith("lora:"):
            base_label = base_label[5:]
        tag = _slugify_tag(item.get("tag") or old.get("tag") or _human_name_from_filename(base_label))
        if not rid:
            rid = old.get("id") or _unique_ref_bank_id(tag, used_ids)
        role = str(item.get("role") or old.get("role") or "subject").strip().lower()
        if role not in ("subject", "place", "prop"):
            role = "subject"
        name = str(item.get("name") or old.get("name") or _human_name_from_filename(base_label)).strip()
        char_name = str(item.get("char_name") if item.get("char_name") is not None else (old.get("char_name") or "")).strip()
        if role == "subject" and not char_name:
            char_name = extract_char_name_from_tag(tag, name) or name.split()[0]
        entry = {
            "id": rid,
            "name": name,
            "char_name": char_name if role == "subject" else "",
            "tag": tag,
            "role": role,
            "file": fname,
            "source": source,
            "voice": os.path.basename(str(item.get("voice") if item.get("voice") is not None else (old.get("voice") or "")).strip()),
            "desc": str(item.get("desc") if item.get("desc") is not None else (old.get("desc") or "")).strip(),
            "locked": str(item.get("locked") if item.get("locked") is not None else (old.get("locked") or "")).strip(),
            "context": str(item.get("context") if item.get("context") is not None else (old.get("context") or "")).strip(),
            "user_edited": bool(user_edited or old.get("user_edited")),
            "mtime": int(item.get("mtime") or old.get("mtime") or 0),
        }
        if source == "refmod":
            entry["strength"] = _norm_strength(item.get("strength") if "strength" in item else old.get("strength"), 1.0)
            entry["step_curve"] = _norm_step_curve(item.get("step_curve") if "step_curve" in item else old.get("step_curve"), "full")
            mems = _norm_members(item.get("members") if "members" in item else old.get("members"))
            if mems:
                entry["members"] = mems
        if existing_idx is not None:
            items[existing_idx] = entry
        else:
            items.append(entry)
        _write_raw_ref_bank(items, deleted_files=deleted_files)
        return entry


def delete_ref_bank_item(item_id: str, file_name: str = "", source: str = "") -> bool:
    iid = str(item_id or "").strip()
    src_want = str(source or "").strip().lower()
    fn_clean = _clean_ref_file(file_name or "", src_want or "image").lower()
    with _LOCK:
        items, deleted_files = _read_raw_ref_bank_doc()
        kept = []
        removed = False
        for it in items:
            it_src = str(it.get("source") or "image").lower()
            it_fn = _clean_ref_file(it.get("file") or "", it_src).lower()
            match_id = bool(iid and it.get("id") == iid)
            match_fn = bool(fn_clean and it_fn == fn_clean and (not src_want or it_src == src_want))
            if match_id or match_fn:
                removed = True
                if it.get("file"):
                    deleted_files.add(_deleted_key(_clean_ref_file(it["file"], it_src), it_src))
                continue
            kept.append(it)
        if removed:
            _write_raw_ref_bank(kept, deleted_files=deleted_files)
        return removed


def import_rail_to_ref_bank(ref_plan_text: str, voice_files: tuple | list = ()) -> list[dict]:
    plan = _refs.parse_ref_plan(ref_plan_text) if str(ref_plan_text or "").strip() else {"refs": [], "subjects": {}}
    subs = plan.get("subjects") or {}
    mvf = [str(v or "").strip() for v in (voice_files or ()) if str(v or "").strip()]
    for r in plan.get("refs") or []:
        source = "refmod" if str(r.get("source") or "").strip().lower() == "refmod" else "image"
        fname = _clean_ref_file(r.get("file") or "", source)
        if not fname:
            continue
        sn = r.get("subject")
        s_meta = subs.get(sn) if sn is not None else None
        ret = str(r.get("retention") or "").strip().lower()
        role = "subject" if sn is not None else ("prop" if ret == "prop" else ("place" if str(r.get("desc") or "").lower().startswith(("set:", "place:", "room:")) else "subject"))
        voice = os.path.basename(str(r.get("voice") or "").strip())
        if not voice and sn == 1 and mvf:
            voice = os.path.basename(mvf[0])
        elif not voice and sn == 2 and len(mvf) >= 2:
            voice = os.path.basename(mvf[1])
        base_label = fname.rsplit("/", 1)[-1]
        if base_label.lower().startswith("lora:"):
            base_label = base_label[5:]
        payload = {
            "file": fname,
            "source": source,
            "tag": r.get("tag") or "",
            "role": role,
            "name": (s_meta or {}).get("name") or _human_name_from_filename(base_label),
            "char_name": (s_meta or {}).get("name") or extract_char_name_from_tag(r.get("tag") or ""),
            "voice": voice or None,
            "desc": r.get("desc") or None,
            "locked": (s_meta or {}).get("locked") or None,
            "context": (s_meta or {}).get("context") or None,
        }
        if source == "refmod":
            payload["strength"] = r.get("strength", 1.0)
            payload["step_curve"] = r.get("step_curve") or "full"
            if r.get("members"):
                payload["members"] = r["members"]
        upsert_ref_bank_item(payload, user_edited=True)
    return load_ref_bank()


# ── Ethnicity, Backdrop Scrubbing & Subject Labels ──────────────────────────

_ETHNICITY_RX = re.compile(
    r"\b((?:(?:East\s+Asian|Southeast\s+Asian|South\s+Asian|Asian|Japanese|Korean|Chinese|Taiwanese|Vietnamese|Thai|Filipina|Filipino|Indonesian|"
    r"African[- ]American|Afro[- ]Caribbean|Ebony|Latina|Latino|Hispanic|Afro[- ]Latina|"
    r"Middle\s+Eastern|Persian|Arab|North\s+African|Indian|Desi|Native\s+American|Indigenous|Polynesian|Pacific\s+Islander|"
    r"Caucasian|European|Nordic|Scandinavian|Slavic|Mediterranean|Mixed[- ]race|Biracial)"
    r"(?:\s+(?:woman|man|girl|boy|person|model|cosplayer|character|beauty|figure|lady|guy|male|female))?|"
    r"(?:Black|White)\s+(?:woman|man|girl|boy|person|model|cosplayer|character|beauty|figure|lady|guy|male|female))"
    r"(?:\s+with\s+[^,.;]{3,75})?)",
    re.I,
)

_PERSON_FILENAME_RX = re.compile(
    r"(?:sheet|turnaround|lookbook|studio|char(?:acter)?|cosplay|girl|woman|lady|man|guy|male|female|model|portrait|face|body|nude|bikini|swimsuit|dress|egirl|wren|mara|elias|qwen)",
    re.I,
)

_ROOM_FILENAME_RX = re.compile(
    r"\b(?:room|street|kitchen|bedroom|hall|office|forest|beach|set|bg|background|penthouse|cell|corridor|landscape|alley|bar|club|hotel|onsen|shower)\b",
    re.I,
)

_STUDIO_BACKDROP_RX = re.compile(
    r"(?:(?:This|The)\s+(?:minimalist\s+)?indoor\s+studio(?:\s+set)?\s+features[^.]*\.\s*|"
    r"(?:Bright,\s+even|Soft,\s+diffused|Warm,\s+directional)\s+(?:overhead\s+)?lighting\s+(?:illuminates|casts|highlights)[^.]*\.\s*|"
    r"The\s+floor\s+remains\s+invisible[^.]*\.\s*|"
    r"The\s+(?:space|clean\s+lines)[^.]*(?:uncluttered|portraiture|professional\s+setting)[^.]*\.\s*|"
    r"A\s+seamless\s+(?:matte\s+)?(?:black|grey|gray|charcoal|white|dark)\s+(?:cyclorama|studio\s+backdrop|backdrop)[^.]*\.\s*|"
    r"\s*(?:against|in|on|standing\s+against|posed\s+against|within)\s+a\s+(?:plain\s+|seamless\s+|matte\s+|solid\s+|monochromatic\s+|stark\s+|high[- ]contrast\s+)*(?:black|dark\s+grey|dark\s+gray|charcoal(?:\s+grey|\s+gray)?|grey|gray|white|dark|neutral|studio)\s+(?:studio\s+)?(?:backdrop|background|cyclorama|void|wall|environment)[^,.;]*)",
    re.I,
)

_BRIEF_BG_META_RX = re.compile(
    r"(?:[,;.\s]*\b(?:and\s+)?(?:please\s+)?(?:do\s+not|don'?t|never|avoid)\s+(?:mention\w*|includ\w*|describ\w*|us\w*|pull\w*|focus\w*\s+on)\s+(?:the\s+|any\s+)?(?:studio\s+|black\s+|grey\s+|gray\s+|dark\s+)?(?:background|backdrop)s?(?:\s+(?:from|in|of|on)\s+(?:the\s+)?(?:reference|character|ref)?\s*(?:sheets?|images?|pictures?|cards?|photos?))?[,.!\s]*|"
    r"[,;.\s]*\b(?:and\s+)?(?:please\s+)?ignore\s+(?:the\s+|any\s+)?(?:studio\s+|black\s+|grey\s+|gray\s+|dark\s+)?(?:background|backdrop)s?(?:\s+(?:from|in|of|on)\s+(?:the\s+)?(?:reference|character|ref)?\s*(?:sheets?|images?|pictures?|cards?|photos?))?[,.!\s]*|"
    r"[,;.\s]*\b(?:without|no)\s+(?:the\s+|any\s+)?(?:reference\s+sheet\s+|studio\s+)?(?:background|backdrop)s?(?:\s+(?:from|in|of|on)\s+(?:the\s+)?(?:reference|character|ref)?\s*(?:sheets?|images?|pictures?|cards?|photos?))?[,.!\s]*)",
    re.I,
)

_GENERIC_TAG_RX = re.compile(
    r"^(?:ref|pic|picture|img|image|sub|subj|subject|char|character|person|woman|man|girl|guy|face|body|sheet|look|outfit|plate|scene|place|set|bg|prop)(?:_?\d+)?$",
    re.I,
)


def clean_user_brief(brief: str) -> str:
    t = str(brief or "").strip()
    if not t:
        return t
    t = _BRIEF_BG_META_RX.sub(" ", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" ,;")
    return t or str(brief or "").strip()


def extract_ethnicity_phrase(text: str, brief: str = "") -> str:
    for src in (text or "", brief or ""):
        if not src:
            continue
        m_anc = re.search(r"Anchor:\s*([^.;]+)", src, re.I)
        if m_anc:
            anc_body = m_anc.group(1).strip()
            m_eth = _ETHNICITY_RX.search(anc_body)
            if m_eth:
                tail = anc_body[m_eth.start():]
                m_split = re.search(
                    r",\s*(?=(?:with\s+|featuring\s+|sporting\s+)?(?:vibrant|bright|dyed|long|short|medium|shoulder[- ]length|waist[- ]length|chin[- ]length|"
                    r"jet[- ]black|black|dark\s+brown|light\s+brown|brown|blonde|platinum|golden|red|crimson|ginger|orange|copper|"
                    r"pink|pastel|purple|violet|blue|cyan|green|silver|white|grey|gray|two[- ]tone|straight|wavy|curly|braided|"
                    r"twin[- ]?tails?|pigtails?|ponytail|bun|bob|bangs|fringe|wearing|gold|silver|black\s+choker|glasses|tattoos?)\b)",
                    tail,
                    re.I,
                )
                phrase = tail[:m_split.start()] if m_split else m_eth.group(1)
                return phrase.strip(" ,;.")
        m_eth = _ETHNICITY_RX.search(src)
        if m_eth:
            raw = m_eth.group(1).strip(" ,;.")
            if not re.search(r"\b(?:woman|man|girl|boy|person|model|cosplayer|lady|guy|male|female)\b", raw, re.I):
                raw = f"{raw} woman" if not re.search(r"\b(?:he|him|his|man|male)\b", brief or "", re.I) else f"{raw} person"
            return raw
    return ""


def strip_front_facial_features_for_rear(eth_phrase: str) -> str:
    s = str(eth_phrase or "").strip()
    if not s:
        return s
    s = re.sub(r",?\s*\b(?:and\s+)?(?:dark|almond|bright|large|expressive|narrow|deep[- ]set|soft)?\s*(?:almond\s+)?eyes\b", "", s, flags=re.I)
    s = re.sub(r",?\s*\b(?:and\s+)?(?:soft\s+|sharp\s+|delicate\s+|defined\s+)?(?:East\s+Asian|Southeast\s+Asian|South\s+Asian|Asian|Caucasian|Latina|Black)?\s*facial\s+features\b", "", s, flags=re.I)
    s = re.sub(r",?\s*\b(?:with|and)\s*$", "", s.strip(" ,;"), flags=re.I)
    return re.sub(r"\s{2,}", " ", s).strip(" ,;")


def is_studio_backdrop_text(desc: str) -> bool:
    t = str(desc or "").strip()
    if not t or t.lower().startswith("anchor:"):
        return False
    return bool(
        re.search(
            r"\b(?:indoor\s+studio(?:\s+set)?|seamless\s+(?:matte\s+)?(?:black|charcoal|grey|gray|white)\s+(?:backdrop|walls)|"
            r"monochromatic\s+backdrop|dark\s+void|invisible\s+floor|floating\s+effect|focused\s+portraiture|"
            r"focusing\s+entirely\s+on\s+the\s+subject'?s\s+attire)\b",
            t,
            re.I,
        )
    )


def clean_subject_scan_desc(desc: str) -> str:
    t = str(desc or "").strip()
    if not t:
        return t
    if re.fullmatch(r"(?:character\s+)?(?:reference\s+)?sheet|turnaround\s+sheet|character\s+reference", t, flags=re.I):
        return ""
    if is_studio_backdrop_text(t):
        return ""
    if t.lower().startswith(("set:", "prop:")):
        t = re.sub(r"^(?:set|prop):\s*", "", t, flags=re.I).strip()
    cleaned = _STUDIO_BACKDROP_RX.sub(" ", t)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return "" if is_studio_backdrop_text(cleaned) else (cleaned or t)


def extract_char_name_from_tag(tag: str, box_name: str = "") -> str:
    raw = str(tag or "").strip().lstrip("@")
    raw = re.sub(r"^(?:fg|ep\d+|ch|char|sub|ref)_+", "", raw, flags=re.I)
    raw = re.sub(r"_+(?:sheet|dress|casual|suit|gown|nude|face|body|look|ref|\d+).*$", "", raw, flags=re.I)
    raw = raw.replace("_", " ").strip()
    if raw and not _GENERIC_TAG_RX.match(raw) and re.fullmatch(r"[A-Za-z]{2,18}", raw):
        return raw.capitalize()
    bn = str(box_name or "").strip()
    if bn and re.fullmatch(r"[A-Z][a-z]{1,18}(?:\s+[A-Z][a-z]{1,18})?", bn) and not re.search(r"\b(?:the|woman|man|girl|boy|person)\b", bn, re.I):
        return bn
    return ""


def _row_voice(r: dict) -> str:
    v = str(r.get("voice") or "").strip()
    if v:
        return v
    if r.get("source") == "refmod" and str(r.get("file") or "").strip():
        rm_mod = _refmod_module()
        if rm_mod is not None:
            try:
                return str((rm_mod.stored_voice(r["file"]) or {}).get("file") or "").strip()
            except Exception:
                return ""
    return ""


def is_likely_person_ref(p: dict, scanned: str = "", brief: str = "", flavors: dict | None = None) -> bool:
    ret = str(p.get("explicit_retention") or p.get("retention") or "").strip().lower()
    if ret == "prop":
        return False
    desc = str(scanned or p.get("desc") or "").strip()
    d_low = desc.lower()
    if d_low.startswith(("set:", "place:", "room:", "background:", "environment:", "prop:", "object:")):
        return False
    if d_low.startswith("anchor:") or _ETHNICITY_RX.search(desc):
        return True
    if re.search(r"\b(?:woman|man|girl|boy|person|model|cosplayer|portrait|wearing|hair|skin)\b", d_low) and not re.search(r"^(?:a|the)\s+(?:room|street|bedroom|hall|alley|beach|forest|office|interior)\b", d_low):
        return True
    tag = str(p.get("tag") or "").lower()
    fn = str(p.get("file") or "").lower()
    if _ROOM_FILENAME_RX.search(tag) or _ROOM_FILENAME_RX.search(fn):
        return False
    if _PERSON_FILENAME_RX.search(tag) or _PERSON_FILENAME_RX.search(fn):
        return True
    if not desc and extract_char_name_from_tag(tag):
        return True
    if is_studio_backdrop_text(desc) and not (flavors or {}).get("place"):
        return True
    return False


def sandtie_labels(ref_plan_text: str, voice_files: tuple | list = ()) -> dict:
    """Resolve hop-1 reference labels (<Picture N>, <Subject N>, <Audio N>) enriched with Reference Bible entries."""
    text = str(ref_plan_text or "").strip()
    media_vf = [str(v or "").strip() for v in (voice_files or ()) if str(v or "").strip()]
    if not text and not media_vf:
        return {"pictures": [], "subjects": {}, "videos": [], "audios": []}
    plan = _refs.parse_ref_plan(text) if text else {"refs": [], "subjects": {}}
    rows = plan["refs"]
    wired = {r["slot"] for r in rows if str(r.get("file") or "").strip()}
    active = _refs.active_refs(rows, 0, wired)
    pics = [r for r in active if r.get("kind") != "video"]
    vids = [r for r in active if r.get("kind") == "video"]
    ords = _refs.ordinals(pics)
    bank = load_ref_bank()
    sub_meta_map = plan.get("subjects") or {}

    out = []
    for r in pics:
        sn = r.get("subject")
        s_meta = (sub_meta_map.get(sn) or {}) if sn is not None else {}
        bank_hit = find_ref_bank_entry(file_name=r.get("file") or "", tag=r.get("tag") or "", bank=bank, source=r.get("source") or "")
        raw_desc = str(r.get("desc") or "").strip()
        if not raw_desc and bank_hit and bank_hit.get("desc"):
            raw_desc = str(bank_hit["desc"]).strip()
        box_parts = [str(s_meta.get(k) or "").strip() for k in ("locked", "context") if str(s_meta.get(k) or "").strip()]
        box_prose = "; ".join(box_parts)
        if sn is None:
            desc_clean = re.sub(r"^(?:Set|Prop):\s*", "", raw_desc, flags=re.I).strip() if raw_desc else ""
        else:
            desc_clean = clean_subject_scan_desc(raw_desc)
            if not desc_clean and box_prose:
                desc_clean = box_prose
            elif desc_clean and box_prose and box_prose.lower() not in desc_clean.lower():
                desc_clean = f"{desc_clean} ({box_prose})"
        out.append({
            "label": f"<Picture {ords[r['tag']]}>",
            "n": ords[r["tag"]],
            "tag": r["tag"],
            "file": r.get("file") or "",
            "source": r.get("source", "image"),
            "members": r.get("members"),
            "desc": desc_clean,
            "raw_desc": raw_desc,
            "box_prose": box_prose,
            "subject": sn,
            "retention": str(r.get("retention") or "").strip() or ("fully_preserved" if sn is not None else "reference"),
            "explicit_retention": str(r.get("retention") or "").strip(),
            "bank_id": (bank_hit or {}).get("id") or "",
        })

    audios = []
    for vf in media_vf:
        n = len(audios) + 1
        audios.append({"label": f"<Audio {n}>", "n": n, "tag": "", "file": vf, "desc": "", "subject": None, "picture": None})
    for r in rows:
        if r.get("shots") is not None and 1 not in r["shots"]:
            continue
        vf = _row_voice(r)
        if not vf:
            bank_hit = find_ref_bank_entry(file_name=r.get("file") or "", tag=r.get("tag") or "", bank=bank, source=r.get("source") or "")
            vf = str((bank_hit or {}).get("voice") or "").strip()
        if not vf:
            continue
        n = len(audios) + 1
        pic_lbl = f"<Picture {ords[r['tag']]}>" if r["tag"] in ords else None
        audios.append({
            "label": f"<Audio {n}>",
            "n": n,
            "tag": r["tag"],
            "file": vf,
            "desc": clean_subject_scan_desc(r.get("desc") or "") if r.get("subject") is not None else (r.get("desc") or ""),
            "subject": r.get("subject"),
            "picture": pic_lbl,
        })

    subs: dict[int, dict] = {}
    for p in out:
        s = p["subject"]
        if s is None:
            continue
        meta = sub_meta_map.get(s) or {}
        bank_hit = find_ref_bank_entry(file_name=p.get("file") or "", tag=p.get("tag") or "", bank=bank, source=p.get("source") or "")
        box_name = str(meta.get("name") or "").strip()
        bank_cname = str((bank_hit or {}).get("char_name") or "").strip()
        char_name = bank_cname or extract_char_name_from_tag(p.get("tag") or "", box_name) or box_name
        subs.setdefault(s, {
            "name": box_name or char_name,
            "char_name": char_name,
            "box_name": box_name,
            "locked": str(meta.get("locked") or "").strip(),
            "context": str(meta.get("context") or "").strip(),
            "pictures": [],
            "audios": [],
        })
        subs[s]["pictures"].append(p["label"])

    for a in audios:
        s = a["subject"]
        if s is None:
            continue
        meta = sub_meta_map.get(s) or {}
        box_name = str(meta.get("name") or "").strip()
        char_name = extract_char_name_from_tag(a.get("tag") or "", box_name) or box_name
        subs.setdefault(s, {
            "name": box_name or char_name,
            "char_name": char_name,
            "box_name": box_name,
            "locked": str(meta.get("locked") or "").strip(),
            "context": str(meta.get("context") or "").strip(),
            "pictures": [],
            "audios": [],
        })
        subs[s]["audios"].append(a["label"])

    return {"pictures": out, "subjects": dict(sorted(subs.items())), "videos": [r["tag"] for r in vids], "audios": audios}


# Compatibility alias
personal_labels = sandtie_labels


def sync_promoted_ref_plan(ref_plan_text: str, lab: dict) -> str:
    raw = str(ref_plan_text or "").strip()
    if not raw:
        return raw
    try:
        doc = json.loads(raw)
    except Exception:
        return raw
    if not isinstance(doc, dict) or not isinstance(doc.get("refs"), list):
        return raw
    by_tag = {str(p.get("tag") or "").lower(): p for p in (lab.get("pictures") or []) if p.get("tag")}
    changed = False
    for r in doc["refs"]:
        t = str(r.get("tag") or "").lstrip("@").strip().lower()
        p = by_tag.get(t)
        if not p:
            continue
        if p.get("subject") is not None and r.get("subject") != p["subject"]:
            r["subject"] = p["subject"]
            changed = True
        if p.get("desc") and not str(r.get("desc") or "").strip():
            r["desc"] = p["desc"]
            changed = True
        if p.get("subject") is not None and not str(r.get("retention") or "").strip():
            r["retention"] = "fully_preserved"
            changed = True
    if not changed:
        return raw
    return json.dumps(doc, separators=(",", ":"))


def label_lines(lab: dict) -> list[str]:
    lines = []
    for n, s in (lab.get("subjects") or {}).items():
        cname = s.get("char_name") or s.get("name") or ""
        nm = f" {cname}" if cname else ""
        where = list(s.get("pictures") or []) + [f"voice {a}" for a in (s.get("audios") or [])]
        lines.append(f"<Subject {n}>{nm}: in {', '.join(where)}")
    for p in lab.get("pictures") or []:
        who = f", <Subject {p['subject']}>" if p.get("subject") is not None else ""
        desc = f": {p['desc']}" if p.get("desc") else ""
        lines.append(f"{p['label']} = @{p['tag']}{who}{desc}")
    for a in lab.get("audios") or []:
        src = f"@{a['tag']} ({a['file']})" if a.get("tag") else (a.get("file") or "voice")
        if a.get("subject") is not None:
            role = f", voice for <Subject {a['subject']}>"
        elif a.get("picture"):
            role = f", paired with {a['picture']}"
        else:
            role = ""
        desc = f": {a['desc']}" if a.get("desc") and not a.get("picture") else ""
        lines.append(f"{a['label']} = {src}{role}{desc}")
    return lines
