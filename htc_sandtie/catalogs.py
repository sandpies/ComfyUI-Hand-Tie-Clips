"""Clean-room JSON catalog loaders, aspect/duration metadata, and domain-compatibility helpers."""
from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
_CACHE: dict[str, object] = {}

DIAL_FILES = {
    "camera": "dials/camera.json",
    "light": "dials/lighting.json",
    "lighting": "dials/lighting.json",
    "lens": "dials/optics.json",
    "optics": "dials/optics.json",
    "fx": "dials/fx.json",
    "style": "dials/styles.json",
    "styles": "dials/styles.json",
    "colour": "dials/colour.json",
    "place": "dials/places.json",
    "places": "dials/places.json",
    "wardrobe": "dials/wardrobe.json",
    "pose": "dials/poses.json",
    "poses": "dials/poses.json",
    "character": "dials/archetypes.json",
    "archetype": "dials/archetypes.json",
    "archetypes": "dials/archetypes.json",
    "tv_show": "dials/worlds.json",
    "world": "dials/worlds.json",
    "worlds": "dials/worlds.json",
    "talkstyle": "dials/talkstyle.json",
    "accent": "dials/accent.json",
    "ambience": "dials/ambience.json",
    "music": "dials/music.json",
    "era": "dials/era.json",
    "combat": "dials/combat.json",
    "explicit": "dials/explicit.json",
}

_COMPATIBLE_GROUPS = (
    {"bedroom", "sofa_lounge", "general"},
    {"wet_shower", "general"},
    {"wet_tub", "general"},
    {"wet_pool", "general"},
    {"office_desk", "general"},
    {"car_cabin", "general"},
    {"mirror_vanity", "bedroom", "general"},
    {"gym_sport", "general"},
    {"bdsm_dom", "bedroom", "general"},
    {"gloryhole", "general"},
    {"combat_action", "general"},
)


def _load_json(rel: str):
    path = os.path.join(DATA_DIR, rel)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0.0
    hit = _CACHE.get(rel)
    if isinstance(hit, tuple) and hit[0] == mtime:
        return hit[1]
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    _CACHE[rel] = (mtime, data)
    return data


def clear_cache() -> None:
    _CACHE.clear()


def parse_multi_ids(val) -> list[str]:
    """Parse single ID, comma-separated IDs, or list into deduplicated non-empty IDs."""
    if not val:
        return []
    if isinstance(val, (list, tuple)):
        raw = [str(x or "").strip() for x in val]
    else:
        raw = [x.strip() for x in str(val).split(",")]
    out, seen = [], set()
    for x in raw:
        if not x or x.lower() == "none" or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def playbook_options() -> list[dict]:
    raw = _load_json("playbook.json")
    out = []
    for k, v in raw.items():
        title = v.get("title") or k.replace("_", " ").title()
        out.append({
            "id": k,
            "label": title,
            "group": "00 · Signature & Specialized" if k.startswith(("shibari_", "glass_", "bathtub_", "yacht_", "aftercare_", "office_")) else "Playbook Modules",
            "domain": v.get("domain") or "general",
            "aspect_best": v.get("aspect_best") or "either",
            "duration_best": v.get("duration_best") or "10-12 s",
            "title": title,
            "shooting": v.get("shooting") or "",
            "styling": v.get("styling") or "",
            "vocab": v.get("vocab") or "",
            "phrases": list(v.get("phrases") or []),
            "raw": v,
        })
    return out


def dial_options(name: str) -> list[dict]:
    key = str(name or "").strip().lower()
    if key in ("fetish", "playbook"):
        return playbook_options()
    if key == "cinema":
        return _load_json("dials/lighting.json").get("options", []) + _load_json("dials/optics.json").get("options", [])
    rel = DIAL_FILES.get(key)
    if not rel:
        return []
    return list(_load_json(rel).get("options", []))


def dial_option(name: str, oid: str) -> dict | None:
    oid = str(oid or "").strip()
    if not oid or oid == "none":
        return None
    for o in dial_options(name):
        if o.get("id") == oid:
            return o
    return None


def resolve_dial_opts(name: str, val) -> list[dict]:
    out = []
    for oid in parse_multi_ids(val):
        opt = dial_option(name, oid)
        if opt:
            out.append(opt)
    return out


def recommend_option_aspect(dial: str, opt: dict) -> dict:
    """Return {aspect_best, aspect_tip} cleanly from explicit metadata or framing semantics."""
    oid = str(opt.get("id") or "").lower()
    lbl = str(opt.get("label") or "").lower()
    rule = str(opt.get("rule") or "").lower()
    explicit_ab = str(opt.get("aspect_best") or "").strip()

    if explicit_ab in ("9:16", "16:9", "either"):
        ab = explicit_ab
    else:
        blob = f"{oid} {lbl} {rule}"
        if oid.startswith(("portrait_", "selfie_", "pov_")) or any(
            k in blob for k in ("vertical 9:16", "9:16", "vertical close", "pedestal", "elevator", "kneeling", "tilt up", "tilt down", "floor-to-face")
        ):
            ab = "9:16"
        elif oid.startswith(("ensemble_", "multi_pos_", "multi_orgy_", "multi_harem_", "combat_s1_s2_", "combat_goons_")) or opt.get("people", 0) >= 2 or any(
            k in blob for k in ("16:9", "widescreen", "horizontal", "two-shot", "side-by-side", "wide master", "pan left", "pan right", "truck left", "truck right")
        ):
            ab = "16:9"
        else:
            ab = "either"

    if ab == "9:16":
        tip = opt.get("aspect_tip") or "BEST FIT: 9:16 Portrait (vertical stacking, pedestal/tilt, or solo close framing)."
    elif ab == "16:9":
        tip = opt.get("aspect_tip") or "BEST FIT: 16:9 Landscape (widescreen two-shot, lateral travel, or side-profile depth)."
    else:
        tip = opt.get("aspect_tip") or "FLEXIBLE: Works cleanly in both 9:16 Portrait and 16:9 Landscape."
    return {"aspect_best": ab, "aspect_tip": tip}


def recommend_option_duration(dial: str, opt: dict) -> dict:
    """Return {duration_best, duration_tip} so 10-12s vs 13-15s pacing is crystal clear in UI & writer."""
    db = str(opt.get("duration_best") or "").strip()
    dt = str(opt.get("duration_tip") or "").strip()
    if not db:
        if dial == "explicit":
            oid = str(opt.get("id") or "").lower()
            if oid.startswith(("multi_pos_", "multi_orgy_", "multi_harem_")):
                db = "13-15 s"
            elif oid.startswith("cont_"):
                db = "12-15 s"
            elif oid.startswith(("playful_", "joi_", "edging_", "solo_")):
                db = "6-10 s"
            else:
                db = "10-12 s"
        elif dial in ("combat", "camera"):
            db = "8-12 s"
        else:
            db = "8-12 s"
    return {"duration_best": db, "duration_tip": dt}


def domains_compatible(dom_a: str, dom_b: str) -> bool:
    a = str(dom_a or "general").strip().lower() or "general"
    b = str(dom_b or "general").strip().lower() or "general"
    if a == b or a == "general" or b == "general":
        return True
    return any(a in grp and b in grp for grp in _COMPATIBLE_GROUPS)


def check_domain_conflicts(flavors: dict | None) -> list[dict]:
    """Detect mismatched scene domains (e.g. wet_shower place + gym_sport wardrobe + wet_pool staging)."""
    flavors = flavors or {}
    active: list[tuple[str, dict]] = []
    for k in ("place", "wardrobe", "explicit", "fetish"):
        for opt in resolve_dial_opts(k, flavors.get(k)):
            dom = str(opt.get("domain") or "general").lower()
            if dom != "general":
                active.append((k, {"id": opt["id"], "label": opt["label"], "domain": dom}))
    if len(active) < 2:
        return []
    conflicts = []
    for i in range(len(active)):
        k1, o1 = active[i]
        for j in range(i + 1, len(active)):
            k2, o2 = active[j]
            if not domains_compatible(o1["domain"], o2["domain"]):
                conflicts.append({
                    "a": (k1, o1["id"], o1["domain"], o1["label"]),
                    "b": (k2, o2["id"], o2["domain"], o2["label"]),
                })
    return conflicts


def script_presets() -> list[dict]:
    raw = _load_json("scripts.json").get("scripts", [])
    return [
        {
            "id": s["id"],
            "label": s["label"],
            "group": s.get("group") or "SandTie Showcase",
            "preview": (s.get("script") or "")[:160],
        }
        for s in raw
    ]


def load_preset_script(preset_id: str) -> str:
    pid = str(preset_id or "").strip()
    for s in _load_json("scripts.json").get("scripts", []):
        if s.get("id") == pid:
            return str(s.get("script") or "")
    return ""


def knowledge_doc() -> dict:
    return dict(_load_json("knowledge.json"))


def dance_vocab_doc() -> dict:
    return dict(_load_json("dance_vocab.json"))


def _slim_ui_opts(dial: str, opts: list[dict]) -> list[dict]:
    out = []
    for o in opts:
        asp = recommend_option_aspect(dial, o)
        dur = recommend_option_duration(dial, o) if dial in ("explicit", "combat", "camera", "pose", "fetish") else {"duration_best": "", "duration_tip": ""}
        item = {
            "id": o["id"],
            "label": o["label"],
            "group": o.get("group") or "",
            "domain": o.get("domain") or "general",
            "aspect_best": asp["aspect_best"],
            "aspect_tip": asp["aspect_tip"],
        }
        if dur["duration_best"]:
            item["duration_best"] = dur["duration_best"]
        if dur["duration_tip"]:
            item["duration_tip"] = dur["duration_tip"]
        if o.get("multi_hop_only"):
            item["multi_hop_only"] = True
        if o.get("people"):
            item["people"] = o["people"]
        out.append(item)
    return out


def _static_ui_catalog() -> dict:
    hit = _CACHE.get("__static_ui_catalog__")
    if hit is not None:
        return hit  # type: ignore[return-value]
    cat = {
        "camera": _slim_ui_opts("camera", dial_options("camera")),
        "light": _slim_ui_opts("light", dial_options("light")),
        "lens": _slim_ui_opts("lens", dial_options("lens")),
        "fx": _slim_ui_opts("fx", dial_options("fx")),
        "style": _slim_ui_opts("style", dial_options("style")),
        "colour": _slim_ui_opts("colour", dial_options("colour")),
        "place": _slim_ui_opts("place", dial_options("place")),
        "wardrobe": _slim_ui_opts("wardrobe", dial_options("wardrobe")),
        "combat": _slim_ui_opts("combat", dial_options("combat")),
        "explicit": _slim_ui_opts("explicit", dial_options("explicit")),
        "fetish": _slim_ui_opts("fetish", dial_options("fetish")),
        "pose": _slim_ui_opts("pose", dial_options("pose")),
        "character": _slim_ui_opts("character", dial_options("character")),
        "tv_show": _slim_ui_opts("tv_show", dial_options("tv_show")),
        "era": _slim_ui_opts("era", dial_options("era")),
        "talkstyle": _slim_ui_opts("talkstyle", dial_options("talkstyle")),
        "accent": _slim_ui_opts("accent", dial_options("accent")),
        "ambience": _slim_ui_opts("ambience", dial_options("ambience")),
        "music": _slim_ui_opts("music", dial_options("music")),
        "scripts": script_presets(),
        "knowledge": knowledge_doc().get("know", {}),
    }
    _CACHE["__static_ui_catalog__"] = cat
    return cat


def ui_catalog() -> dict:
    from . import refs as _refs
    cat = dict(_static_ui_catalog())
    cat["ref_bank"] = _refs.load_ref_bank()
    return cat
