"""OpenCV Dual-Evidence Cut Detector + FPS-Invariant Optical Flow + Reference Vision (User-Local Cache)."""
from __future__ import annotations

import base64
import io
import json
import os
import re
import threading

from . import refs as _refs

_LOCK = threading.Lock()


def _cache_file() -> str:
    p = os.path.join(_refs.user_data_dir(), "vision_cache.json")
    _refs._migrate_legacy_json("vision_cache.json", p)
    return p


ROLE_PROMPTS = {
    "subject": (
        "CRITICAL RULE: Focus 100% on the person/character. Completely disregard any black, dark grey, charcoal, white, or plain studio background, backdrop, void, floor, walls, or studio lighting — mention zero background or studio environment! "
        "Reply with EXACTLY TWO sentences (never three or more, and NEVER use pronouns she, he, her, his, they, their): "
        "Sentence 1 MUST be ONE single comma-separated noun-phrase sentence starting with \"Anchor: \" giving: "
        "1) visual medium/style (e.g. photorealistic live-action, 2D cel-shaded anime, digital illustration, 3D CGI render, vintage film photo); "
        "2) racial/ethnic profile and gender (e.g. East Asian woman, Southeast Asian man, South Asian woman, Black woman, Latina woman, Middle Eastern man, Caucasian woman, Mixed-race woman — judge strictly from facial bone structure even under dyed or cosplay hair); "
        "3) actual skin tone/undertone plus any visible freckles, beauty marks/moles with exact placement, dimples, scars, or clearly applied makeup (lipstick, eyeliner, eyeshadow) -- never natural cheek colour, blush or flush; "
        "4) actual face shape and bone structure (jawline, chin, cheekbones, nose bridge/tip, lip fullness/shape); "
        "5) ACTUAL observed eye geometry and iris color (check close-up insets — never default to 'almond' or 'dark': state round, hooded, monolid, deep double-lid, upturned, wide-set, exact iris tint e.g. pale lavender-grey/amber/hazel/espresso, eyeliner/lashes, and brow thickness/arch); "
        "6) honest body build and silhouette from full-body views (never default to 'slim' or 'petite' when curvy — explicitly note curvy hourglass, full/modest bust, narrow waist, wide/narrow hips, athletic muscular, lean, or petite frame); "
        "7) exact hair color/roots, length (chin, shoulder, mid-back, waist), bangs/sidelocks, parting, texture, facial hair, plus any worn glasses shape, jewelry, choker, headwear, nails, tattoos, piercings, or horns. "
        "Sentence 2 MUST ALWAYS be present whenever clothing, swimwear, or footwear is visible: start with \"Wearing \" (or \"Unclothed\" when bare) and list head-to-toe garment construction, inner/outer layers, cut-outs, ties/straps/closures, fabrics, colors, hosiery, and footwear/bare feet. "
        "Never guess numeric age or body weight, never list absent items (never write 'no jewelry', 'no tattoos', etc.), never use negative words (no, not, never, without, none, lacking), and stay under 110 words total."
    ),
    "auto": (
        "CRITICAL RULE: If this image contains ANY person, character, model, face, or body (including a portrait, lookbook photo, or multi-panel character reference/turnaround sheet on a black, dark grey, charcoal, or white background), focus 100% on the PERSON and completely disregard the background, studio backdrop, walls, floor, void, and studio lighting! "
        "When a person is present, reply with EXACTLY TWO sentences (never use pronouns she, he, her, his, they, their): "
        "Sentence 1 MUST be ONE single comma-separated noun-phrase sentence starting with \"Anchor: \" giving visual medium/style, racial/ethnic profile and gender (judged from facial bone structure even under dyed/cosplay hair), "
        "actual skin tone/undertone and marks/makeup, face/jaw/nose/lip geometry, ACTUAL eye geometry/lid type/iris color and brow shape (never default to 'almond' or 'dark'), "
        "honest full-body silhouette/build (explicitly noting bust, waist, hips, muscularity, or slender frame rather than defaulting to 'slim'/'petite'), exact hair color/length/bangs/sidelocks/texture, plus glasses, jewelry, nails, tattoos, or horns. "
        "Sentence 2 MUST ALWAYS start with \"Wearing \" (or \"Unclothed\" when bare) and list head-to-toe garments, layers, cut-outs, straps/ties, fabrics, colors, and footwear/bare feet (mention zero background or studio lighting). "
        "ONLY if the image contains ZERO people and shows an actual architectural room, street, landscape, or film set, start with \"Set: \" and describe the rendering style, indoor/outdoor spatial layout (foreground/midground/background), surfaces, materials, key objects, lighting direction/color temperature, and plate camera height/angle in under 65 words. "
        "ONLY if it shows a standalone object or wearable prop alone with zero people, start with \"Prop: \" and describe its visual style, silhouette, material/finish, colors, and surface details in under 40 words. "
        "Never list absent items and never use negative words (no, not, never, without, none, lacking)."
    ),
    "place": (
        "Describe this place as a film set: visual medium/style if stylized, indoor/outdoor setting, foreground/midground/background layout, "
        "surfaces and materials, colors, key furniture and props, lighting direction/color temperature/time of day, and plate camera angle/height. "
        "Focus strictly on the environment and architecture, and never use negative words (no, not, never, without, empty). "
        "One concrete paragraph under 65 words."
    ),
    "prop": (
        "Describe only this object or wearable prop: visual style/medium if stylized, exact silhouette, material/finish, colors, "
        "markings or engravings, and surface wear/details. Focus strictly on the object itself, and never use negative words (no, not, never, without). "
        "One crisp sentence under 40 words."
    ),
    "wardrobe": (
        "CRITICAL RULE: Describe ONLY the garments, accessories, and footwear visible (completely disregard the wearer's face/identity and any studio background, backdrop, or lighting). "
        "Open with rendering style if non-photorealistic (e.g. 2D anime or 3D CGI), then start with \"Wearing \" and state exact garment silhouette/fit, "
        "inner and outer layers, fabric drape/sheen/knit/pattern, colors, necklines, straps, closures, hosiery, and footwear in under 60 words. "
        "Never mention age, studio backdrop, or negative words (no, not, never, without)."
    ),
    "style": (
        "Describe ONLY the visual style of this reference: exact rendering medium (photorealistic 35mm, glossy editorial digital, 2D cel-shaded anime, painterly illustration, 3D CGI render), "
        "linework or grain/lens texture, color palette and grading curve, contrast, and signature lighting aesthetic in under 50 words. "
        "Never use negative words (no, not, never, without)."
    ),
    "bodyshape": (
        "CRITICAL RULE: Describe ONLY the body build, proportions, and visual style (disregarding studio backdrop, walls, lighting, and specific face/garment identity). "
        "State rendering style, stature/frame proportions honestly (curvy hourglass, full/modest bust, narrow waist, wide/narrow hips, athletic muscular, lean, or slender — never default to 'slim'/'petite' when curvy), shoulder-to-waist-to-hip silhouette, and skin tone/undertone in under 50 words. "
        "Never guess numeric age/weight or use negative words (no, not, never, without)."
    ),
    "pose_motion": (
        "Describe ONLY the physical pose, stance, weight distribution, spine/hip tilt, arm/hand placement, head angle/gaze, and implied motion across frames in under 45 words. "
        "Disregard the subject's identity, garments, and background, and never use negative words (no, not, never, without)."
    ),
    "frame": (
        "This picture is the opening frame of a video. Open with the exact visual medium and rendering style (e.g. live-action cinematic, "
        "2D cel-shaded anime, 3D CGI render), then state each person's racial/ethnic profile, gender, actual skin tone/marks, and specific facial/eye/brow geometry and build alongside their exact hair color/style "
        "(observing true eye and face shape rather than generic defaults), what they are wearing, their exact posture, screen position, and hand placement, "
        "the room/place, the lighting direction/color, and the camera framing. Never guess numeric age or body weight, and "
        "never use negative words (no, not, never, without). One concrete paragraph under 85 words."
    ),
}


def canonical_caption_role(role: str) -> str:
    r = str(role or "subject").strip().lower()
    if r == "background":
        return "place"
    if r == "helper":
        return "prop"
    if r in ("identity", "generic", ""):
        return "subject"
    return r if r in ROLE_PROMPTS else "subject"


def build_caption_prompt(role: str, n_images: int = 1) -> str:
    key = role if role in ROLE_PROMPTS else canonical_caption_role(role)
    base = ROLE_PROMPTS[key]
    if int(n_images or 1) >= 2:
        if key == "subject":
            base += (
                " Multiple look frames from the same subject asset are attached: capture the shared rendering style, racial/ethnic profile, gender, "
                "specific eye/facial traits, skin marks, build, and hair consistent across all frames, and state clothing only where outfits match across frames."
            )
        else:
            base += " Multiple frames from the same asset are attached: synthesize the consistent traits shared across all frames."
    return base


def caption_max_tokens(role: str) -> int:
    key = role if role in ROLE_PROMPTS else canonical_caption_role(role)
    return 440 if key in ("subject", "auto", "frame") else 280

MADE_OF_LABELS = (
    "live_action", "ai_video", "cg_3d", "anim_2d", "code_render",
    "screen_capture", "still_motion", "static_hold", "stop_motion",
    "film_footage", "avatar",
)

VIDEO_EXTRACTOR_SYSTEM = """You are the SandTie Choreography & Camera Vision Extractor for MiniMax H3.
You are given chronological Shot-by-Shot Storyboard Contact Strips of a reference video clip.
- Each image (`IMAGE 1 — ...`, `IMAGE 2 — ...`, ...) shows sequential numbered frames (`#1`, `#2`, `#3`, ...) with exact timestamps in seconds across that shot or sub-beat window.
%(cuts_note)s

CRITICAL EXTRACTION LAWS:
1. MULTI-SUBJECT CONSISTENT CASTING: Scan all images first to see how many distinct people appear anywhere in the clip. Assign `<Subject 1>` (primary lead), `<Subject 2>` (second performer, if any), and `<Subject 3>` (if three+) consistently by persistent role/wardrobe/appearance across EVERY strip. Even when `<Subject 2>` appears alone in a cut, keep labeling them `<Subject 2>`! Whenever 2+ subjects appear together, state exact screen-left / screen-right / front-back positions and any staggered or asymmetric timing rather than merging both into identical copies.
2. TRACE CHRONOLOGICAL FRAME PROGRESSION: Inside every strip, read frames `#1 -> #2 -> #3 -> ...` in order and describe how the action EVOLVES from start to end (weight shifts, steps, pivots/turns, airborne hops, high kicks, crouches/squats, elbow/wrist/finger trajectories, partner entrances/exits). Note peak moments cleanly without collapsing an evolving sequence into a static pose.
3. VISUAL HONESTY & CROP FRAMING: Describe ONLY body parts, faces, and subjects directly visible in that strip. On an isolated detail/limb insert (e.g. forearm and hand against sky) or a tight bust-up/waist-up shot, state the exact framing scale (`extreme close-up of forearm`, `tight bust-up`) and describe ONLY visible parts — never invent off-screen legs, hips, or hidden faces.
4. CHECK HORIZON & CAMERA ROLL FIRST: Inspect sky/water/horizon, walls, and floor lines before describing body posture. When the horizon or room lines sit tilted or vertical (`Dutch tilt` or `90-degree sideways camera roll`), state the camera roll explicitly while describing the subject's true posture relative to gravity (standing upright in a sideways-rolled frame, rather than falsely claiming they lie flat).
5. SEPARATE APPEARANCE FROM CHOREOGRAPHY: Keep hair color, skin tone, ethnicity, and clothing descriptions inside `"cast"` and `"outfit"` ONLY (never inside `"shot1"` or `"beats"`, except brief physical garment/prop handling if touched during a move).
6. KINETIC PROSE & STRICTLY POSITIVE WORDING: Translate motion speeds into natural kinematic prose (never emit Hz numbers or negative words like no/not/never/without anywhere). Describe skeletal joint action cleanly, adding `'with a natural, soft jiggle'` only during visible active bounces or shimmies.
7. CLASSIFY MEDIUM & LOCK SHOT 1 / TIMESTAMPS:
   - Set `"made_of"` to the single best-fitting production medium (`live_action`, `ai_video`, `cg_3d`, `anim_2d`, `code_render`, `screen_capture`, `still_motion`, `static_hold`, `stop_motion`, `film_footage`, or `avatar`), and put rendering medium/palette/lighting into `"style"`.
   - In `"shot1"`, write a clean plain sentence (WITHOUT any `[Shot 1]` prefix) locking `0.00s`: camera scale/angle/horizon, visible `<Subject N>` placement, body orientation (`facing straight forward`, `three-quarter front view`, `side profile facing screen-right`), and starting left/right arm + hand placement.
   - In `"beats"`, emit the exact `[Shot N] At MM:SS.mmm, ...` and `At MM:SS.mmm-MM:SS.mmm, ...` timestamps from the Mandatory Beat Skeleton below.

Reply with ONLY a valid JSON object matching this exact shape (without markdown fences):
{
  "name": "Short descriptive title (4-7 words)",
  "made_of": "live_action",
  "style": "Rendering medium, lens/texture, palette, and lighting aesthetic in 1 concise sentence.",
  "cast": "<Subject 1>: brief visual role/hair anchor; <Subject 2>: brief visual role/hair anchor (or 'Solo <Subject 1>')",
  "outfit": "Wearing ...",
  "room": "The exact setting and lighting visible in the frames",
  "summary": "1-2 sentence overview of the cast performing the choreography and camera cuts.",
  "shot1": "Opening camera framing, horizon/angle, visible subject(s), and t=0.0s screen-left/right posture + left/right hand placement sentence (NO '[Shot 1]' prefix).",
  "beats": [
%(beats_skeleton)s
  ],
  "music": "Upbeat 120 BPM track with crisp percussion and clean bassline."
}"""

STRIP_PASS1_SYSTEM = """You are a frame-accurate video breakdown analyst. Inspect ONLY the attached storyboard strip(s) in chronological order (`#1 -> #2 -> #3 -> ...`).
Describe strictly what is visible and moving across those frames using 100% positive phrasing (no negative words like no/not/never/without).
Reply with ONLY a valid JSON object:
{
  "made_of": "one of: live_action, ai_video, cg_3d, anim_2d, code_render, screen_capture, still_motion, static_hold, stop_motion, film_footage, avatar",
  "style": "visual rendering medium, palette, and lighting",
  "cast_notes": "distinct people visible (appearance/hair/position, e.g. person A in red, person B in black)",
  "outfit_notes": "visible garments and footwear",
  "room_notes": "visible setting and lighting",
  "segments": [
    {
      "label": "exact IMAGE / SHOT / BEAT header",
      "shot_size": "extreme_close_up / close_up / medium / wide / extreme_wide / top_down / pov",
      "camera_move": "camera scale, horizon roll, and movement",
      "action": "chronological #1->#N progression of visible subjects, posture, limb/hand paths, and gaze"
    }
  ]
}"""


def _load_cache() -> dict:
    try:
        with open(_cache_file(), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_cache(key: str, val) -> None:
    path = _cache_file()
    with _LOCK:
        c = _load_cache()
        c[key] = val
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(c, fh, indent=0)
        os.replace(tmp, path)


def encode_image_mp(path: str, mp: float = 2.5) -> str:
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = min(1.0, (mp * 1e6 / float(max(1, w * h))) ** 0.5)
        if scale < 1.0:
            im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def encode_pil_mp(im, mp: float = 1.0) -> str:
    from PIL import Image
    im = im.convert("RGB")
    w, h = im.size
    scale = min(1.0, (mp * 1e6 / float(max(1, w * h))) ** 0.5)
    if scale < 1.0:
        im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


_STUDIO_SCAN_SENT_RX = re.compile(
    r"(?:(?:This|The)\s+(?:minimalist\s+)?indoor\s+studio(?:\s+set)?\s+features[^.]*\.\s*|"
    r"(?:Bright,\s+even|Soft,\s+diffused|Warm,\s+directional)\s+(?:overhead\s+)?lighting\s+(?:illuminates|casts|highlights)[^.]*\.\s*|"
    r"The\s+floor\s+remains\s+invisible[^.]*\.\s*|"
    r"The\s+(?:space|clean\s+lines)[^.]*(?:uncluttered|portraiture|professional\s+setting)[^.]*\.\s*|"
    r"A\s+seamless\s+(?:matte\s+)?(?:black|grey|gray|charcoal|white|dark)\s+(?:cyclorama|studio\s+backdrop|backdrop)[^.]*\.\s*|"
    r"\s*(?:against|in|on|standing\s+against|posed\s+against)\s+a\s+(?:plain\s+|seamless\s+|matte\s+|solid\s+|monochromatic\s+)*(?:black|dark\s+grey|dark\s+gray|charcoal(?:\s+grey|\s+gray)?|grey|gray|white|dark|neutral)\s+(?:studio\s+)?(?:backdrop|background|cyclorama|void|wall)[^,.;]*)",
    re.I,
)

_SHEET_LEAK_SUBS = (
    (re.compile(r"\b(?:shown|visible)\s+(?:in|across|on)\s+(?:all\s+)?(?:the\s+)?(?:(?:close-up|zoomed)\s+)?(?:inset\s+panels?|contact\s+sheets?|(?:motion\s+)?sequence\s+sheets?|storyboard(?:\s+(?:sequence|frames?))?|comic\s+strip)\b", re.I), ""),
    (re.compile(r"\b(?:in|across|from|on|inside)\s+(?:all\s+)?(?:the\s+)?(?:close-up|zoomed)\s+inset\s+panels?\b", re.I), "in close-up"),
    (re.compile(r"\b(?:in|across|from|on|inside)\s+(?:all\s+)?(?:the\s+)?inset\s+panels?\b", re.I), ""),
    (re.compile(r"\b(?:in|from|on|at)\s+(?:frame|panel|tile)\s*#\s*\d+\b", re.I), ""),
    (re.compile(r"\b(?:storyboard(?:\s+(?:sequence|video|sheet|frames?))?|comic\s+strip|manga\s+page|stitched\s+images?|contact\s+sheets?|(?:motion\s+)?sequence\s+sheets?|speech\s+bubbles?|speech\s+balloons?|panel\s+borders?|gutters?|split[- ]screen\s+grid|grid\s+cells?|inset\s+panels?)\b", re.I), ""),
    (re.compile(r"\{[^{}\n]{2,60}\}"), ""),
)


def scrub_sheet_leaks(text: str, strip: bool = True) -> str:
    """Strip VLM contact-sheet, storyboard-panel, and template-placeholder leakage cleanly."""
    t = str(text or "")
    if not t:
        return t
    for rx, repl in _SHEET_LEAK_SUBS:
        t = rx.sub(repl, t)
    t = re.sub(r"[ \t]+([,.;!?])", r"\1", t)
    t = re.sub(r",[ \t]*,+", ",", t)
    t = re.sub(r"\([ \t]*\)", "", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip() if strip else t


def _clean_desc(text: str, cap: int = 860, strip_studio: bool = False) -> str:
    t = re.sub(r"[*#_`>]+", "", text or "")
    t = re.sub(r"^(?:based on|here is|here's|sure|certainly|in this (?:image|picture|frame))[^:.]*[:.]\s*", "", t, flags=re.I)
    t = " ".join(t.split()).strip()
    if strip_studio or t.lower().startswith("anchor:"):
        t = _STUDIO_SCAN_SENT_RX.sub(" ", t)
    t = scrub_sheet_leaks(t)
    # Strip negative-absence clauses ("and no visible jewelry or piercings", "with no tattoos", "without any accessories", "lacking markings")
    for _ in range(3):
        t_next = re.sub(
            r"(?:,\s*(?:and\s+|with\s+)?|\s+(?:and|with)\s+)?\b(?:no|without|lacking|free\s+of|devoid\s+of)\s+(?:visible\s+|any\s+)?[^,.;!?\n]+",
            "",
            t,
            flags=re.I,
        )
        t_next = re.sub(
            r"(?:,\s*(?:and\s+)?|\s+and\s+)?\b(?:not|never)\s+(?:wearing|showing|having|featuring)\s+[^,.;!?\n]+",
            "",
            t_next,
            flags=re.I,
        )
        if t_next == t:
            break
        t = t_next
    t = re.sub(r",\s*,+", ",", t)
    t = re.sub(r"(?:,\s*|\s+(?:and|with)\s*)([.;!?]|$)", r"\1", t, flags=re.I)
    t = re.sub(r"\.\s*\.", ".", t)
    t = " ".join(t.split()).strip()
    if len(t) > cap:
        cut = t[:cap].rsplit(". ", 1)[0]
        if len(cut) < max(80, cap // 3) or "Wearing " in t[len(cut):cap]:
            cut = t[:cap].rsplit(", ", 1)[0]
        t = cut.rstrip(" ,;") + ("." if not cut.rstrip(" ,;").endswith(".") else "")
    return t


def is_studio_backdrop_scan(text: str) -> bool:
    t = str(text or "").strip()
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


async def scan_reference_urls(urls: list[str], role: str, complete_fn, *, cache_key: str = "") -> str:
    clean_urls = [str(u).strip() for u in (urls or []) if str(u or "").strip()]
    if not clean_urls:
        return ""
    rkey = role if role in ROLE_PROMPTS else canonical_caption_role(role)
    strip_studio = rkey in ("subject", "auto", "wardrobe", "bodyshape")
    if cache_key:
        cache = _load_cache()
        hit = cache.get(cache_key)
        if isinstance(hit, str) and hit.strip() and not (strip_studio and is_studio_backdrop_scan(hit)):
            return _clean_desc(hit, 860, strip_studio=strip_studio)
    content = [{"type": "text", "text": build_caption_prompt(rkey, n_images=len(clean_urls))}]
    for u in clean_urls:
        content.append({"type": "image_url", "image_url": {"url": u}})
    max_tok = caption_max_tokens(rkey)
    raw = await complete_fn([{"role": "user", "content": content}], schema=None, temperature=0.35, max_tokens=max_tok)
    cleaned = _clean_desc(raw, 860, strip_studio=strip_studio)
    if rkey == "auto" and is_studio_backdrop_scan(cleaned):
        content_subj = [{"type": "text", "text": build_caption_prompt("subject", n_images=len(clean_urls))}]
        for u in clean_urls:
            content_subj.append({"type": "image_url", "image_url": {"url": u}})
        raw_subj = await complete_fn([{"role": "user", "content": content_subj}], schema=None, temperature=0.35, max_tokens=440)
        cleaned = _clean_desc(raw_subj, 860, strip_studio=True)
    if cache_key and cleaned and not (strip_studio and is_studio_backdrop_scan(cleaned)):
        _save_cache(cache_key, cleaned)
    return cleaned


async def scan_reference_file(path: str, role: str, complete_fn) -> str:
    if not path or not os.path.isfile(path):
        return ""
    rkey = role if role in ROLE_PROMPTS else canonical_caption_role(role)
    strip_studio = rkey in ("subject", "auto", "wardrobe", "bodyshape")
    mtime = int(os.path.getmtime(path))
    cache = _load_cache()
    key = f"refscan_v6|{os.path.abspath(path)}|{mtime}|{rkey}"
    hit = cache.get(key)
    if isinstance(hit, str) and hit.strip() and not (strip_studio and is_studio_backdrop_scan(hit)):
        return _clean_desc(hit, 860, strip_studio=strip_studio)
    try:
        data_url = encode_image_mp(path, mp=2.5 if rkey in ("subject", "auto", "frame") else 1.5)
        return await scan_reference_urls([data_url], rkey, complete_fn, cache_key=key)
    except Exception as exc:
        print(f"[HandTieClips-SandTie] vision scan skipped ({os.path.basename(path)}): {exc}", flush=True)
        return ""


def _fmt_mmss(t_sec: float) -> str:
    m_i = int(max(0.0, t_sec) // 60)
    s_r = max(0.0, t_sec) - m_i * 60
    return f"{m_i:02d}:{s_r:06.3f}"


def _summarize_flow_rows(rows: list) -> tuple[str, str, list[float]]:
    import math
    import numpy as np
    if not rows:
        return "LOCKED / STATIC CAMERA", "LOW SUBJECT MOTION / HELD POSE", []
    mid_idx = max(1, len(rows) // 2)
    halves = [rows, rows[:mid_idx], rows[mid_idx:]] if len(rows) >= 4 else [rows]
    best_tx = max((float(np.mean([r[1] for r in h])) for h in halves if h), key=abs)
    best_ty = max((float(np.mean([r[2] for r in h])) for h in halves if h), key=abs)
    best_div = max((float(np.mean([r[3] for r in h])) for h in halves if h), key=abs)
    best_roll = max((float(np.mean([r[4] for r in h])) for h in halves if h), key=abs)

    cam_bits = []
    if best_div >= 0.09:
        cam_bits.append("PUSH-IN / ZOOM IN")
    elif best_div <= -0.09:
        cam_bits.append("PULL-OUT / ZOOM OUT")
    if best_tx <= -0.08:
        cam_bits.append("PAN/TRUCK RIGHT")
    elif best_tx >= 0.08:
        cam_bits.append("PAN/TRUCK LEFT")
    if best_ty >= 0.07:
        cam_bits.append("TILT/RISE UP")
    elif best_ty <= -0.07:
        cam_bits.append("TILT/DROP DOWN")
    if abs(best_roll) >= 10.0:
        cam_bits.append(f"ROLL/SPIN ({best_roll:+.0f} deg/s)")

    jitter = 0.0
    speed_mean = 0.0
    if len(rows) >= 3:
        dtx = np.diff([r[1] for r in rows])
        dty = np.diff([r[2] for r in rows])
        jitter = float(np.mean(np.hypot(dtx, dty)))
        speed_mean = float(np.mean([math.hypot(r[1], r[2]) for r in rows]))
    is_handheld = jitter >= 0.065 and (jitter >= 0.55 * speed_mean or jitter >= 0.11)
    if is_handheld:
        cam_desc = f"HANDHELD ({' + '.join(cam_bits)})" if cam_bits else "HANDHELD CAMERA"
    else:
        cam_desc = " + ".join(cam_bits) if cam_bits else "LOCKED / STATIC CAMERA"

    fg_mean = float(np.mean([r[6] for r in rows]))
    fg_peak_row = max(rows, key=lambda r: r[6])
    peak_ts = [round(r[0], 2) for r in sorted(rows, key=lambda x: x[6], reverse=True)[:2]]
    if fg_mean >= 0.28 or fg_peak_row[6] >= 0.42:
        e_desc = f"HIGH-ENERGY ACTION (peak ~{fg_peak_row[0]:.2f}s)"
    elif fg_mean >= 0.14 or fg_peak_row[6] >= 0.22:
        e_desc = f"ACTIVE CHOREOGRAPHY (peak ~{fg_peak_row[0]:.2f}s)"
    elif fg_mean >= 0.075 or fg_peak_row[6] >= 0.12:
        e_desc = f"MODERATE MOTION (peak ~{fg_peak_row[0]:.2f}s)"
    elif fg_mean < 0.025 and fg_peak_row[6] < 0.045:
        if cam_bits:
            e_desc = "STILL IMAGE PAN/ZOOM (0% subject motion)"
        elif not is_handheld:
            e_desc = "STATIC HOLD / FROZEN FRAME (0% motion)"
        else:
            e_desc = "MINIMAL MOTION / HELD POSE"
    else:
        e_desc = "MINIMAL MOTION / HELD POSE"
    return cam_desc, e_desc, peak_ts


def _scan_video_cv(video_path: str, in_sec: float = 0.0, out_sec: float = 0.0,
                   max_seconds: float = 15.0, min_dur: float = 1.5):
    """Dual-evidence hard-cut + fade/flash/dissolve detector & ~15 Hz IRLS affine flow scanner."""
    import math
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(video_path)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    n_frames = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    w = max(1, int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
    h = max(1, int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    total_dur = n_frames / fps

    t0 = max(0.0, min(float(in_sec or 0.0), max(0.0, total_dur - 0.25)))
    t1 = float(out_sec or 0.0)
    t1 = min(total_dur, t0 + max_seconds) if t1 <= t0 + 0.15 else min(total_dur, t0 + max_seconds, t1)
    raw_dur = max(0.25, round(t1 - t0, 2))

    start_f = max(0, int(round(t0 * fps)))
    end_f = min(n_frames, int(round(t1 * fps)))
    if start_f > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)

    scale_an = 128.0 / float(max(w, h))
    fw = max(32, int(round(w * scale_an / 2.0) * 2))
    fh = max(32, int(round(h * scale_an / 2.0) * 2))
    diag_an = math.hypot(fw, fh)

    frame_thumbs: list = []
    all_diffs: list[float] = [0.0]
    all_hists: list = []
    all_lumas: list[float] = []
    prev_small = None
    last_active_t = raw_dur
    dark_streak = 0
    dark_thresh = max(3, int(round(0.35 * fps)))

    for idx in range(max(1, end_f - start_f)):
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        t_s = round(idx / fps, 3)
        thumb_u8 = cv2.resize(frame, (fw, fh), interpolation=cv2.INTER_AREA)
        small = thumb_u8.astype(np.float32)
        bright = float(np.mean(small))
        all_lumas.append(bright / 255.0)
        hsv = cv2.cvtColor(thumb_u8, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [16, 8, 8], [0, 180, 0, 256, 0, 256])
        cv2.normalize(hist, hist, 1.0, 0.0, cv2.NORM_L1)
        all_hists.append(hist)
        if prev_small is not None:
            diff = float(np.mean(np.abs(small - prev_small)))
            all_diffs.append(diff)
            if t_s > 4.5 and bright < 30.0 and diff < 1.2:
                dark_streak += 1
                if dark_streak >= dark_thresh:
                    last_active_t = round(max(2.5, t_s - dark_streak / fps), 2)
                    break
            else:
                dark_streak = 0
        frame_thumbs.append(thumb_u8)
        prev_small = small

    cap.release()
    if not frame_thumbs:
        return {
            "fps": fps, "n_frames": n_frames, "w": w, "h": h, "total_dur": total_dur,
            "t0": t0, "start_f": start_f, "dur": 0.0, "cut_times": [], "cuts_meta": [], "frame_flows": [],
        }

    actual_span = max(0.1, round(len(frame_thumbs) / fps, 2))
    dur = max(min(min_dur, actual_span), min(max_seconds, round(last_active_t, 2)))
    active_max_f = min(len(all_diffs), len(frame_thumbs), max(1, int(round(dur * fps))))

    luma_arr = np.asarray(all_lumas[:active_max_f], dtype=np.float32)
    sm_luma = np.convolve(luma_arr, np.ones(5, dtype=np.float32) / 5.0, mode="same") if luma_arr.size >= 5 else luma_arr

    cut_cands: list[tuple[float, float, str]] = []
    for f_i in range(1, max(1, active_max_f - 1)):
        t_s = round(f_i / fps, 3)
        if t_s < 0.25 or t_s > dur - 0.25:
            continue
        d = all_diffs[f_i]
        win = [all_diffs[j] for j in range(max(1, f_i - 5), min(active_max_f, f_i + 6)) if abs(j - f_i) >= 2]
        loc_med = float(np.median(win)) if win else 1.0
        ratio = d / max(1.0, loc_med)
        if d > 15.0 and ratio > 1.48:
            im_a = frame_thumbs[max(0, f_i - 2)]
            im_b = frame_thumbs[min(len(frame_thumbs) - 1, f_i + 1)]
            ha = cv2.calcHist([cv2.cvtColor(im_a, cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256])
            hb = cv2.calcHist([cv2.cvtColor(im_b, cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256])
            cv2.normalize(ha, ha, 1.0, 0.0, cv2.NORM_L1)
            cv2.normalize(hb, hb, 1.0, 0.0, cv2.NORM_L1)
            bhat = float(cv2.compareHist(ha, hb, cv2.HISTCMP_BHATTACHARYYA))
            ga = cv2.resize(cv2.cvtColor(im_a, cv2.COLOR_BGR2GRAY), (16, 16)).astype(np.float32)
            gb = cv2.resize(cv2.cvtColor(im_b, cv2.COLOR_BGR2GRAY), (16, 16)).astype(np.float32)
            corr16 = float(np.corrcoef(ga.ravel(), gb.ravel())[0, 1]) if (ga.std() > 1.0 and gb.std() > 1.0) else 1.0
            is_cut = (d > 15.5 and ratio > 1.48 and (bhat >= 0.19 or corr16 < 0.42)) or (d > 26.0 and ratio >= 2.60)
            if is_cut:
                score = (d / 20.0) + bhat * 2.2 + max(0.0, 0.5 - corr16)
                lo0, hi0 = max(0, f_i - 3), min(len(sm_luma), f_i + 4)
                c_type = "cut"
                if lo0 < hi0:
                    if float(sm_luma[lo0:hi0].min()) < 0.07:
                        c_type = "fade"
                    elif float(sm_luma[lo0:hi0].max()) > 0.92 and bhat < 0.55:
                        c_type = "flash"
                if cut_cands and (t_s - cut_cands[-1][0]) < 0.36:
                    if (t_s - cut_cands[-1][0]) < 0.18 and score > cut_cands[-1][1]:
                        cut_cands[-1] = (round(t_s, 2), score, c_type)
                else:
                    cut_cands.append((round(t_s, 2), score, c_type))

    # Smoothed FPS-invariant (~0.20s stride) dissolve / crossfade plateau detector
    if active_max_f >= 10:
        stride = max(2, int(round(0.20 * fps)))
        cut_f_set = {int(round(ct * fps)) for ct, _, _ in cut_cands}
        bhat_stride = np.zeros(active_max_f, dtype=np.float32)
        for f_i in range(stride, active_max_f):
            if any((f_i - stride) < cf <= f_i for cf in cut_f_set):
                continue
            bhat_stride[f_i] = float(cv2.compareHist(all_hists[f_i - stride], all_hists[f_i], cv2.HISTCMP_BHATTACHARYYA))
        b_valid = bhat_stride[stride:]
        med_b = float(np.median(b_valid)) if b_valid.size >= 3 else 0.0
        t_lo = max(0.26, min(0.55, med_b + 0.22))
        plateau = np.convolve(bhat_stride, np.ones(5, dtype=np.float32) / 5.0, mode="same")
        in_block, block_start = False, 0
        min_dissolve_frames = max(5, int(round(0.20 * fps)))
        for f_i in range(stride, active_max_f - 1):
            if plateau[f_i] > t_lo and not in_block:
                in_block, block_start = True, f_i
            elif plateau[f_i] <= t_lo and in_block:
                in_block = False
                if (f_i - block_start) >= min_dissolve_frames:
                    # Center the transition inside the dissolve (accounting for the lookback stride)
                    t_mid = round(max(0.25, (((block_start + f_i) // 2) - stride // 2) / fps), 2)
                    ta_b, tb_b = (block_start - stride) / fps - 0.35, f_i / fps + 0.35
                    if 0.25 <= t_mid <= dur - 0.25 and not any(ta_b <= ct <= tb_b for ct, _, _ in cut_cands):
                        pk = float(np.max(plateau[block_start:f_i]))
                        lo_l = max(0, block_start - stride - 2)
                        hi_l = min(len(sm_luma), f_i + 2)
                        if lo_l < hi_l and float(sm_luma[lo_l:hi_l].min()) < 0.07:
                            cut_cands.append((t_mid, pk, "fade"))
                        else:
                            cut_cands.append((t_mid, pk, "dissolve"))
        if in_block and (active_max_f - 1 - block_start) >= min_dissolve_frames:
            t_mid = round(max(0.25, (((block_start + active_max_f) // 2) - stride // 2) / fps), 2)
            ta_b = (block_start - stride) / fps - 0.35
            if 0.25 <= t_mid <= dur - 0.25 and not any(ct >= ta_b for ct, _, _ in cut_cands):
                cut_cands.append((t_mid, float(np.max(plateau[block_start:active_max_f])), "dissolve"))

    cut_cands.sort(key=lambda x: x[0])
    dedup_cands: list[tuple[float, float, str]] = []
    for ct, sc, typ in cut_cands:
        if dedup_cands and (ct - dedup_cands[-1][0]) < 0.36:
            if sc > dedup_cands[-1][1]:
                dedup_cands[-1] = (ct, sc, typ)
        else:
            dedup_cands.append((ct, sc, typ))

    cut_times = [ct for ct, _, _ in dedup_cands]
    cuts_meta = [{"t": ct, "type": typ, "score": round(sc, 3)} for ct, sc, typ in dedup_cands]
    flow_step = max(1, int(round(fps / 15.0)))
    yy_g, xx_g = np.mgrid[0:fh, 0:fw]
    nx_g = (xx_g + 0.5) / float(fw) - 0.5
    ny_g = (yy_g + 0.5) / float(fh) - 0.5
    bmask = (np.abs(nx_g) > 0.30) | (np.abs(ny_g) > 0.30)
    cut_frames_set = {int(round(ct * fps)) for ct in cut_times}

    frame_flows = []  # (t_s, tx, ty, div, roll_deg_s, fg_p95, fg_p98)
    prev_f_idx = None
    prev_gray = None
    for f_i in range(0, active_max_f, flow_step):
        gray = cv2.cvtColor(frame_thumbs[f_i], cv2.COLOR_BGR2GRAY)
        if prev_gray is not None and prev_f_idx is not None:
            crossed_cut = any(prev_f_idx < cf <= f_i + 1 for cf in cut_frames_set)
            if not crossed_cut:
                dt_pair = (f_i - prev_f_idx) / fps
                flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 13, 3, 5, 1.1, 0)
                fx = flow[..., 0] / (fw * dt_pair)
                fy = flow[..., 1] / (fh * dt_pair)
                A1 = np.column_stack([np.ones(int(bmask.sum())), nx_g[bmask], ny_g[bmask]])
                px, _, _, _ = np.linalg.lstsq(A1, fx[bmask], rcond=None)
                py, _, _, _ = np.linalg.lstsq(A1, fy[bmask], rcond=None)
                res0 = np.hypot((fx - (px[0] + px[1] * nx_g + px[2] * ny_g)) * fw, (fy - (py[0] + py[1] * nx_g + py[2] * ny_g)) * fh)
                bg2 = res0 < max(0.35, float(np.percentile(res0, 65)))
                if int(bg2.sum()) >= 48:
                    A2 = np.column_stack([np.ones(int(bg2.sum())), nx_g[bg2], ny_g[bg2]])
                    px, _, _, _ = np.linalg.lstsq(A2, fx[bg2], rcond=None)
                    py, _, _, _ = np.linalg.lstsq(A2, fy[bg2], rcond=None)
                pred_x = px[0] + px[1] * nx_g + px[2] * ny_g
                pred_y = py[0] + py[1] * nx_g + py[2] * ny_g
                res_diag_s = np.hypot((fx - pred_x) * fw, (fy - pred_y) * fh) / diag_an
                tx_v, ty_v = float(px[0]), float(py[0])
                div_v = 0.5 * (float(px[1]) + float(py[2]))
                roll_deg_s = math.degrees(0.5 * (float(py[1]) * fh / float(fw) - float(px[2]) * fw / float(fh)))
                frame_flows.append((
                    round(f_i / fps, 3), tx_v, ty_v, div_v, roll_deg_s,
                    float(np.percentile(res_diag_s, 95)), float(np.percentile(res_diag_s, 98)),
                ))
        prev_f_idx = f_i
        prev_gray = gray

    return {
        "fps": fps, "n_frames": n_frames, "w": w, "h": h, "total_dur": total_dur,
        "t0": t0, "start_f": start_f, "dur": dur, "cut_times": cut_times,
        "cuts_meta": cuts_meta, "frame_flows": frame_flows,
    }


def _grab_exact_frames_rgb(video_path: str, frame_indices: list[int]) -> dict[int, object]:
    """Decode exact 0-based frame indices sequentially via grab/retrieve (zero B-frame seek drift)."""
    import cv2
    from PIL import Image

    need = sorted({max(0, int(i)) for i in frame_indices})
    if not need:
        return {}
    max_idx = need[-1]
    need_set = set(need)
    out = {}
    cap = cv2.VideoCapture(video_path)
    try:
        start_at = need[0]
        if start_at > 24:
            # Back off ~24 frames before first target to avoid H264/HEVC keyframe land drift while staying fast
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, start_at - 24))
            cur = int(cap.get(cv2.CAP_PROP_POS_FRAMES) or 0)
        else:
            cur = 0
        while cur <= max_idx:
            ok = cap.grab()
            if not ok:
                break
            if cur in need_set:
                ok_r, fr = cap.retrieve()
                if ok_r and fr is not None:
                    out[cur] = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
            cur += 1
    finally:
        cap.release()
    return out


def _cut_label(c_type: str) -> tuple[str, str, str]:
    t = str(c_type or "cut").lower()
    if t == "fade":
        return "FADE", "fade in to", "fade"
    if t == "dissolve":
        return "DISSOLVE", "dissolve to", "dissolve"
    if t == "flash":
        return "FLASH CUT", "flash cut to", "flash"
    return "HARD CUT", "hard cut to", "cut"


def build_swap_vision_bundle(video_path: str, start: float = 0.0, end: float = 0.0, max_seconds: float = 15.0) -> dict:
    """Build SWAP-optimized OpenCV vision package: 1 crisp anchor IN frame + 1-2 timestamped sequence strips + telemetry."""
    from PIL import Image, ImageDraw, ImageFont

    scan = _scan_video_cv(video_path, in_sec=start, out_sec=end, max_seconds=max_seconds, min_dur=0.4)
    fps, n_frames = scan["fps"], scan["n_frames"]
    w, h, t0, dur = scan["w"], scan["h"], scan["t0"], scan["dur"]
    cut_times, frame_flows = scan["cut_times"], scan["frame_flows"]
    cuts_meta = scan.get("cuts_meta") or [{"t": ct, "type": "cut"} for ct in cut_times]
    cut_type_by_seg = {i + 2: str(m.get("type") or "cut") for i, m in enumerate(cuts_meta)}
    has_cuts = len(cut_times) > 0

    bounds = [0.0] + cut_times + [dur] if has_cuts else [0.0, dur]
    segments = [(i + 1, round(bounds[i], 3), round(bounds[i + 1], 3)) for i in range(len(bounds) - 1)]

    # Budget 6..16 timestamped samples across the trimmed window, hitting every cut/shot + motion peaks
    target_total = 6 if dur <= 4.8 else (8 if dur <= 7.5 else (12 if dur <= 12.2 else 16))
    if has_cuts and len(segments) * 2 > target_total:
        target_total = min(16, max(target_total, len(segments)))

    # Allocate samples per segment proportionally, >=2 when slots allow, >=1 always
    seg_counts = {}
    for sid, ta, tb in segments:
        seg_counts[sid] = 1
    rem = max(0, target_total - len(segments))
    if rem > 0:
        weights = [(sid, max(0.15, tb - ta)) for sid, ta, tb in segments]
        tot_w = sum(wt for _, wt in weights) or 1.0
        for sid, wt in weights:
            add = int(round(rem * wt / tot_w))
            seg_counts[sid] += add
        while sum(seg_counts.values()) > target_total:
            cands = [(seg_counts[s], s) for s in seg_counts if seg_counts[s] > 1]
            if not cands:
                break
            cands.sort(reverse=True)
            seg_counts[cands[0][1]] -= 1
        while sum(seg_counts.values()) < target_total and segments:
            longest = max(segments, key=lambda x: (x[2] - x[1]) / float(seg_counts[x[0]]))
            seg_counts[longest[0]] += 1

    samples = []  # (t_rel, seg_id, cut_lbl_or_empty, f_idx)
    seg_telem_lines = []
    for sid, ta, tb in segments:
        seg_len = max(0.1, tb - ta)
        win_rows = [r for r in frame_flows if (ta + 0.03) < r[0] < (tb - 0.02)] or [r for r in frame_flows if ta <= r[0] <= tb]
        cam_desc, e_desc, peak_ts = _summarize_flow_rows(win_rows)
        c_lbl, _, _ = _cut_label(cut_type_by_seg.get(sid, "cut"))
        cut_tag = f" [{c_lbl} AT {ta:.2f}s]" if (has_cuts and sid > 1) else ""
        lbl = f"Shot {sid}" if has_cuts else "Clip"
        seg_telem_lines.append(f"  - {lbl} ({ta:.2f}s–{tb:.2f}s){cut_tag}: camera [{cam_desc}] | action [{e_desc}]")

        n_here = seg_counts[sid]
        pad = min(0.055, seg_len * 0.12)
        t_a = ta + (0.04 if (has_cuts and sid > 1) else 0.0)
        t_b = max(t_a, tb - pad)
        ts_here = []
        if n_here == 1:
            # Prefer a clear interior frame (~40% into the shot, biased away from cut-out whip blurs)
            t_pick = t_a + 0.4 * max(0.0, t_b - t_a)
            mid_rows = [r for r in win_rows if (t_a + 0.15 * seg_len) <= r[0] <= (t_b - 0.15 * seg_len)]
            if mid_rows:
                t_pick = max(mid_rows, key=lambda r: r[6])[0]
            ts_here.append(round(t_pick, 2))
        else:
            dt_slot = (t_b - t_a) / float(n_here - 1)
            for k in range(n_here):
                tu = t_a + k * dt_slot
                if 0 < k < (n_here - 1) and win_rows:
                    cands = [r for r in win_rows if max(t_a + 0.02, tu - 0.25 * dt_slot) <= r[0] <= min(t_b - 0.02, tu + 0.25 * dt_slot)]
                    if cands:
                        best_r = max(cands, key=lambda r: r[6])
                        center_r = min(cands, key=lambda r: abs(r[0] - tu))
                        if best_r[6] >= 1.18 * max(0.05, center_r[6]):
                            tu = best_r[0]
                if ts_here and tu <= ts_here[-1] + 0.04:
                    tu = min(t_b, ts_here[-1] + 0.05)
                ts_here.append(round(tu, 2))
        for j, tr in enumerate(ts_here):
            f_no = min(n_frames - 1, max(0, int(round((t0 + tr) * fps))))
            samples.append((tr, sid, (c_lbl if (has_cuts and sid > 1 and j == 0) else ""), f_no))

    anchor_f = min(n_frames - 1, max(0, int(round(t0 * fps))))
    need_frames = [anchor_f] + [s[3] for s in samples]
    decoded = _grab_exact_frames_rgb(video_path, need_frames)
    anchor_im = decoded.get(anchor_f)
    anchor_url = encode_pil_mp(anchor_im, mp=0.65) if anchor_im is not None else None

    try:
        font_big = ImageFont.truetype("arialbd.ttf", 19)
        font_sub = ImageFont.truetype("arialbd.ttf", 15)
    except Exception:
        font_big = font_sub = None

    # Pack samples into 1 or 2 crisp contact grids (max 8 per sheet: 2x3 or 2x4)
    chunks = [samples[:8], samples[8:]] if len(samples) > 8 else [samples]
    strip_urls, strip_labels = [], []
    shot_palette = [(28, 60, 125), (155, 32, 54), (24, 102, 78), (138, 72, 20), (84, 38, 128), (24, 96, 122)]

    for s_idx, chunk in enumerate(chunks, 1):
        if not chunk:
            continue
        n_c = len(chunk)
        cols = 4 if n_c >= 7 else (3 if n_c >= 5 else n_c)
        rows_g = (n_c + cols - 1) // cols
        thumb_w = (320 if cols <= 3 else 270) if w >= h else (260 if cols <= 3 else 220)
        thumb_h = max(110, int(round(thumb_w * h / float(max(1, w)))))
        hdr_h, cell_hdr_h = 32, 22
        cell_h = cell_hdr_h + thumb_h + 2
        canvas = Image.new("RGB", (cols * thumb_w, hdr_h + rows_g * cell_h), (14, 14, 18))
        draw = ImageDraw.Draw(canvas)
        ta_c, tb_c = chunk[0][0], chunk[-1][0]
        draw.rectangle([0, 0, cols * thumb_w, hdr_h], fill=(28, 56, 110))
        draw.text((10, 6), f"SEQUENCE {s_idx}/{len(chunks)} ({ta_c:.2f}s -> {tb_c:.2f}s of {dur:.2f}s)", fill=(255, 250, 130), font=font_big)
        for idx_c, (tr, sid, cut_tag_lbl, f_no) in enumerate(chunk):
            im = decoded.get(f_no)
            if im is None:
                continue
            im_r = im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            r_i, c_i = idx_c // cols, idx_c % cols
            x0, y0 = c_i * thumb_w, hdr_h + 1 + r_i * cell_h
            bar_col = shot_palette[(sid - 1) % len(shot_palette)] if has_cuts else (26, 28, 38)
            tag = f" [{cut_tag_lbl}]" if cut_tag_lbl else (" [IN]" if (s_idx == 1 and idx_c == 0) else (" [OUT]" if (s_idx == len(chunks) and idx_c == n_c - 1) else ""))
            draw.rectangle([x0, y0, x0 + thumb_w - 2, y0 + cell_hdr_h], fill=bar_col)
            draw.text((x0 + 6, y0 + 2), f"{tr:.2f}s{tag}", fill=(205, 255, 210), font=font_sub)
            canvas.paste(im_r, (x0, y0 + cell_hdr_h + 1))
        strip_urls.append(encode_pil_mp(canvas, mp=1.25))
        strip_labels.append(
            f"Clip motion sequence sheet {s_idx} of {len(chunks)} ({ta_c:.2f}s to {tb_c:.2f}s in time order, "
            f"{len(chunk)} timestamped frames). Read left-to-right, top-to-bottom to trace camera path and movement."
        )

    global_cam, global_e, _ = _summarize_flow_rows(frame_flows)
    cuts_str = ", ".join(f"{m['t']:.2f}s ({m['type']})" for m in cuts_meta)
    cuts_desc = (f"{len(cut_times)} transition(s) at {cuts_str}"
                 if has_cuts else "continuous single shot (0 hard cuts)")
    telem_hdr = f"[CLIP TIMELINE & CAMERA MOTION]\nWindow: {dur:.2f}s | {cuts_desc} | Overall camera: [{global_cam}] | Energy: [{global_e}]"
    telemetry = telem_hdr + ("\n" + "\n".join(seg_telem_lines) if len(seg_telem_lines) > 1 else "")
    return {
        "anchor_url": anchor_url,
        "strip_urls": strip_urls,
        "strip_labels": strip_labels,
        "telemetry": telemetry,
        "duration_s": dur,
        "cut_times": cut_times,
        "cuts_meta": cuts_meta,
    }


def _build_strips_bundle(video_path: str, in_sec: float = 0.0, out_sec: float = 0.0, max_seconds: float = 15.0) -> dict:
    from PIL import Image, ImageDraw, ImageFont

    scan = _scan_video_cv(video_path, in_sec=in_sec, out_sec=out_sec, max_seconds=max_seconds, min_dur=1.5)
    fps, n_frames = scan["fps"], scan["n_frames"]
    w, h, t0, dur = scan["w"], scan["h"], scan["t0"], scan["dur"]
    cut_times, frame_flows = scan["cut_times"], scan["frame_flows"]
    cuts_meta = scan.get("cuts_meta") or [{"t": ct, "type": "cut"} for ct in cut_times]
    cut_type_by_seg = {i + 2: str(m.get("type") or "cut") for i, m in enumerate(cuts_meta)}
    has_cuts = len(cut_times) > 0

    if dur <= 0.0 or n_frames <= 0:
        return {
            "strips": [], "dur": 0.0, "cut_times": [], "cuts_meta": [],
            "telemetry_str": "", "beats_skeleton_str": "", "strip_headers": [], "strip_meta": [],
        }

    if has_cuts:
        bounds = [0.0] + cut_times + [dur]
        segments = [(i + 1, round(bounds[i], 3), round(bounds[i + 1], 3)) for i in range(len(bounds) - 1)]
    else:
        segments = [(1, 0.0, dur)]

    shot_parts: dict[int, int] = {}
    for seg_id, t_a, t_b in segments:
        seg_len = max(0.1, t_b - t_a)
        if not has_cuts:
            shot_parts[seg_id] = max(3, min(8, int(round(seg_len / 2.2))))
        elif seg_len > 3.65:
            shot_parts[seg_id] = max(2, min(5, int(round(seg_len / 2.2))))
        else:
            shot_parts[seg_id] = 1

    max_strips = 14 if len(segments) <= 14 else min(16, len(segments))
    while sum(shot_parts.values()) > max_strips:
        splittable = [
            (shot_parts[sid], (tb - ta) / float(shot_parts[sid]), sid)
            for sid, ta, tb in segments if shot_parts[sid] > 1
        ]
        if not splittable:
            break
        splittable.sort(reverse=True)
        shot_parts[splittable[0][2]] -= 1

    strip_specs = []
    for seg_id, t_a, t_b in segments:
        if len(strip_specs) >= max_strips:
            break
        n_parts = shot_parts[seg_id]
        seg_len = max(0.1, t_b - t_a)
        for p_i in range(n_parts):
            w_a = round(t_a + (p_i / float(n_parts)) * seg_len, 3)
            w_b = round(t_a + ((p_i + 1) / float(n_parts)) * seg_len, 3)
            w_len = max(0.1, w_b - w_a)
            if n_parts == 1 and has_cuts:
                n_f = 3 if w_len <= 1.35 else (4 if w_len <= 2.35 else 6)
            else:
                n_f = 3 if w_len <= 1.35 else 4
            strip_specs.append((len(strip_specs) + 1, seg_id, p_i + 1, n_parts, w_a, w_b, n_f, p_i == 0))

    # Pre-plan exact timestamps & frame indices across ALL strips so we decode in one sequential pass (zero B-frame seek drift)
    strip_plans = []
    all_need_frames: list[int] = []
    for img_id, seg_id, part_i, part_tot, w_a, w_b, n_f, is_shot_start in strip_specs:
        w_len = max(0.15, w_b - w_a)
        win_rows = [r for r in frame_flows if (w_a + 0.035) < r[0] < (w_b - 0.025)] or [r for r in frame_flows if w_a <= r[0] <= w_b]
        cam_desc, e_desc, peak_ts = _summarize_flow_rows(win_rows)

        pad = min(0.055, w_len * 0.12)
        t_start = w_a + pad
        t_end = max(t_start, w_b - pad)
        sample_ts = []
        slot_dt = (t_end - t_start) / float(max(1, n_f - 1))
        for c_i in range(n_f):
            t_u = t_start + c_i * slot_dt
            if 0 < c_i < (n_f - 1) and win_rows:
                lo_t = max(t_start + 0.03, t_u - 0.25 * slot_dt)
                hi_t = min(t_end - 0.03, t_u + 0.25 * slot_dt)
                cand_rows = [r for r in win_rows if lo_t <= r[0] <= hi_t]
                if cand_rows:
                    best_r = max(cand_rows, key=lambda r: r[6])
                    center_r = min(cand_rows, key=lambda r: abs(r[0] - t_u))
                    if best_r[6] >= 1.18 * max(0.05, center_r[6]):
                        t_u = best_r[0]
            if sample_ts and t_u <= sample_ts[-1] + 0.04:
                t_u = min(t_end, sample_ts[-1] + 0.05)
            sample_ts.append(round(t_u, 2))
        frame_nos = [min(n_frames - 1, max(0, int(round((t0 + ts) * fps)))) for ts in sample_ts]
        all_need_frames.extend(frame_nos)
        strip_plans.append((img_id, seg_id, part_i, part_tot, w_a, w_b, n_f, is_shot_start, w_len, cam_desc, e_desc, peak_ts, sample_ts, frame_nos))

    decoded_frames = _grab_exact_frames_rgb(video_path, all_need_frames)

    try:
        font_big = ImageFont.truetype("arialbd.ttf", 20)
        font_sub = ImageFont.truetype("arialbd.ttf", 16)
    except Exception:
        font_big = font_sub = None

    shot_palette = [(25, 55, 115), (155, 25, 50), (20, 100, 75), (135, 70, 15), (80, 35, 125), (20, 95, 120), (125, 30, 90), (55, 95, 30)]
    strips, strip_headers, telemetry_lines, skeleton_items, strip_meta = [], [], [], [], []

    for img_id, seg_id, part_i, part_tot, w_a, w_b, n_f, is_shot_start, w_len, cam_desc, e_desc, peak_ts, sample_ts, frame_nos in strip_plans:
        part_lbl = f"SHOT {seg_id}" if has_cuts else f"BEAT {img_id}"
        if has_cuts and part_tot > 1:
            part_lbl = f"SHOT {seg_id} (Part {part_i}/{part_tot})"
        c_lbl, c_verb, c_raw = _cut_label(cut_type_by_seg.get(seg_id, "cut"))
        cut_prefix = f" [{c_lbl} AT {w_a:.2f}s]" if (has_cuts and seg_id > 1 and is_shot_start) else ""

        cols = 3 if n_f == 6 else n_f
        rows_g = 2 if n_f == 6 else 1
        thumb_w = (340 if cols <= 3 else 300) if w >= h else (280 if cols <= 3 else 240)
        thumb_h = max(120, int(round(thumb_w * h / float(max(1, w)))))
        row_banner_h, frame_hdr_h = 34, 24
        cell_h = frame_hdr_h + thumb_h + 2
        canvas = Image.new("RGB", (cols * thumb_w, row_banner_h + rows_g * cell_h), (14, 14, 18))
        draw = ImageDraw.Draw(canvas)
        hdr_col = shot_palette[(seg_id - 1) % len(shot_palette)]
        cut_str = f" [{c_lbl}]" if (has_cuts and seg_id > 1 and is_shot_start) else (" [OPENING SHOT]" if img_id == 1 else " [CONTINUATION]")
        draw.rectangle([0, 0, cols * thumb_w, row_banner_h], fill=hdr_col)
        draw.text((10, 6), f"{part_lbl} ({_fmt_mmss(w_a)} - {_fmt_mmss(w_b)}){cut_str}", fill=(255, 250, 120), font=font_big)

        for c_i, (t_sec, f_no) in enumerate(zip(sample_ts, frame_nos)):
            im_src = decoded_frames.get(f_no)
            if im_src is not None:
                im = im_src.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                r_idx = c_i // cols
                c_col = c_i % cols
                x0 = c_col * thumb_w
                fy0 = row_banner_h + 1 + r_idx * cell_h
                tag_pos = "START" if c_i == 0 else ("END" if c_i == n_f - 1 else "")
                lbl_f = f"#{c_i + 1} {tag_pos} ({t_sec:.2f}s)".replace("  ", " ")
                draw.rectangle([x0, fy0, x0 + thumb_w - 2, fy0 + frame_hdr_h], fill=(24, 24, 32))
                draw.text((x0 + 8, fy0 + 3), lbl_f, fill=(180, 255, 195), font=font_sub)
                canvas.paste(im, (x0, fy0 + frame_hdr_h + 1))

        strips.append(canvas)
        hdr_line = f"IMAGE {img_id} — {part_lbl} ({_fmt_mmss(w_a)} to {_fmt_mmss(w_b)}){cut_str} | {cam_desc} | {e_desc}"
        strip_headers.append(hdr_line)
        peak_note = f" | Peak action near {', '.join(f'{pt:.2f}s' for pt in peak_ts)}" if peak_ts else ""
        tel_line = (
            f"  • IMAGE {img_id} -> {part_lbl} ({_fmt_mmss(w_a)}–{_fmt_mmss(w_b)}, dur={w_len:.2f}s, {n_f} frames #1..#{n_f}){cut_prefix}: "
            f"[{cam_desc}] | [{e_desc}{peak_note}] — Inspect frames #1..#{n_f} in order and report exact visible framing/horizon, "
            f"who is in shot (`<Subject 1>`, `<Subject 2>`, or detail insert), and chronological step/pose/hand transitions."
        )
        telemetry_lines.append(tel_line)
        strip_meta.append({
            "img_id": img_id, "seg_id": seg_id, "part_lbl": part_lbl, "w_a": w_a, "w_b": w_b,
            "cam_desc": cam_desc, "e_desc": e_desc, "transition": c_raw if (has_cuts and seg_id > 1 and is_shot_start) else "",
            "header": hdr_line, "telemetry": tel_line,
        })

        if has_cuts and seg_id > 1 and is_shot_start:
            skeleton_items.append(
                f'    "[Shot {seg_id}] At {_fmt_mmss(w_a)}, {c_verb} <state camera scale/angle/horizon roll, which `<Subject N>` (or body detail) appears, screen-left/right placement, and starting pose>."'
            )
        if n_f == 6:
            w_mid = round(0.5 * (w_a + w_b), 3)
            skeleton_items.append(
                f'    "At {_fmt_mmss(w_a)}-{_fmt_mmss(w_mid)}, <trace {part_lbl} first half (frames #1-#3): camera move, visible subject(s), body turns/steps, left/right arm & hand transitions, and gaze>."'
            )
            skeleton_items.append(
                f'    "At {_fmt_mmss(w_mid)}-{_fmt_mmss(w_b)}, <trace {part_lbl} second half (frames #4-#6): any newly visible subject or formation change, footwork, left/right hand poses, and expression>."'
            )
        else:
            skeleton_items.append(
                f'    "At {_fmt_mmss(w_a)}-{_fmt_mmss(w_b)}, <trace {part_lbl} across frames #1-#{n_f}: camera movement, visible subject(s) & staggered/asymmetric actions, footwork/kicks/crouches/pivots, left/right hand shapes, and gaze>."'
            )

    return {
        "strips": strips,
        "dur": dur,
        "cut_times": cut_times,
        "cuts_meta": cuts_meta,
        "telemetry_str": "\n".join(telemetry_lines),
        "beats_skeleton_str": ",\n".join(skeleton_items),
        "strip_headers": strip_headers,
        "strip_meta": strip_meta,
    }


def build_opencv_video_strips(video_path: str, in_sec: float = 0.0, out_sec: float = 0.0, max_seconds: float = 15.0):
    b = _build_strips_bundle(video_path, in_sec=in_sec, out_sec=out_sec, max_seconds=max_seconds)
    return b["strips"], b["dur"], b["cut_times"], b["telemetry_str"], b["beats_skeleton_str"], b["strip_headers"]


VIDEO_EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "cast", "outfit", "room", "summary", "shot1", "beats", "music"],
    "properties": {
        "name": {"type": "string"},
        "made_of": {"type": "string"},
        "style": {"type": "string"},
        "cast": {"type": "string"},
        "outfit": {"type": "string"},
        "room": {"type": "string"},
        "summary": {"type": "string"},
        "shot1": {"type": "string"},
        "beats": {"type": "array", "items": {"type": "string"}},
        "music": {"type": "string"},
    },
}

STRIP_PASS1_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["made_of", "style", "cast_notes", "outfit_notes", "room_notes", "segments"],
    "properties": {
        "made_of": {"type": "string"},
        "style": {"type": "string"},
        "cast_notes": {"type": "string"},
        "outfit_notes": {"type": "string"},
        "room_notes": {"type": "string"},
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "shot_size", "camera_move", "action"],
                "properties": {
                    "label": {"type": "string"},
                    "shot_size": {"type": "string"},
                    "camera_move": {"type": "string"},
                    "action": {"type": "string"},
                },
            },
        },
    },
}


def _repair_json_text(cand: str) -> str:
    s = str(cand or "").strip()
    # Replace curly double quotes inside strings with apostrophes so they don't break JSON delimiters
    s = s.replace("\u201c", "'").replace("\u201d", "'")
    # Insert missing commas between JSON fields/items across newlines (e.g. "room": "..."\n  "summary": "...")
    s = re.sub(r'([\]}"0-9]|true|false|null)[ \t]*\r?\n([ \t]*")', r"\1,\n\2", s)
    # Remove trailing commas before closing } or ]
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    # Escape raw control newlines inside string literals
    out_chars: list[str] = []
    in_str = False
    esc = False
    for ch in s:
        if esc:
            out_chars.append(ch)
            esc = False
            continue
        if ch == "\\":
            out_chars.append(ch)
            esc = True
            continue
        if ch == '"':
            out_chars.append(ch)
            in_str = not in_str
            continue
        if in_str and ch == "\n":
            out_chars.append("\\n")
            continue
        if in_str and ch == "\r":
            continue
        out_chars.append(ch)
    return "".join(out_chars)


def parse_lenient_json_obj(raw: str) -> dict | None:
    txt = str(raw or "").strip()
    if not txt:
        return None
    # Strip <think>...</think> blocks, plus orphaned closing </think> prefix if opening tag was omitted
    txt = re.sub(r"<think>[\s\S]*?</think>", "", txt, flags=re.I).strip()
    m_think_end = re.search(r"</think>", txt, flags=re.I)
    if m_think_end:
        txt = txt[m_think_end.end():].strip()

    candidates = [txt]
    for blk in re.findall(r"```(?:json)?\s*([\s\S]*?)```", txt, flags=re.I):
        if blk.strip():
            candidates.append(blk.strip())
    a, b = txt.find("{"), txt.rfind("}")
    if 0 <= a < b:
        candidates.append(txt[a:b + 1])

    dec = json.JSONDecoder()
    for c in candidates:
        for attempt in (c, _repair_json_text(c)):
            try:
                obj = json.loads(attempt)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
            idx = attempt.find("{")
            if idx >= 0:
                try:
                    obj, _ = dec.raw_decode(attempt[idx:])
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    pass
    return None


_parse_lenient_json_obj = parse_lenient_json_obj


def _clean_extracted_shot1(text: str) -> str:
    s = scrub_sheet_leaks(str(text or "").strip())
    s = re.sub(r"^(?:The\s+)?\[\s*Shot\s+1\s*\](?:\s*At\s+\d+:\d+(?:\.\d+)?\s*,?)?\s*[,:\-]*\s*", "", s, flags=re.I).strip()
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return s


def _normalize_made_of(raw_val: str, telemetry_str: str = "") -> str:
    v = re.sub(r"[^a-z0-9_]+", "_", str(raw_val or "").strip().lower()).strip("_")
    aliases = {
        "live": "live_action", "real": "live_action", "photoreal": "live_action", "photorealistic": "live_action",
        "ai": "ai_video", "aigc": "ai_video", "3d": "cg_3d", "cgi": "cg_3d", "cg": "cg_3d",
        "2d": "anim_2d", "anime": "anim_2d", "animation": "anim_2d", "cartoon": "anim_2d",
        "motion_graphics": "code_render", "ken_burns": "still_motion", "still": "static_hold",
        "talking_head": "avatar", "film": "film_footage",
    }
    v = aliases.get(v, v)
    if v in MADE_OF_LABELS:
        return v
    low_t = str(telemetry_str or "").lower()
    if "still image pan/zoom" in low_t:
        return "still_motion"
    if "static hold / frozen frame" in low_t:
        return "static_hold"
    return "live_action" if v == "" else v


def render_extracted_video_md(res: dict) -> str:
    """Render a compact VIDEO.md-style reverse-engineering report for an extracted clip."""
    if not isinstance(res, dict):
        return ""
    dur = float(res.get("duration_s") or 0.0)
    cuts = res.get("transitions") or [{"t": c, "type": "cut"} for c in (res.get("cuts") or [])]
    made_of = res.get("made_of") or "live_action"
    trans_str = ", ".join(f"{c.get('type', 'cut')}@{float(c.get('t', 0)):.2f}s" for c in cuts) or "continuous"
    lines = [
        "---",
        f"name: {res.get('name') or 'Extracted Clip'}",
        f"duration: {dur:.2f}s",
        f"made_of: {made_of}",
        f"transitions: {len(cuts)} ({trans_str})",
        "---",
        "",
    ]
    if res.get("style"):
        lines.append(f"- **Style:** {res['style']}")
    if res.get("cast"):
        lines.append(f"- **Cast:** {res['cast']}")
    if res.get("outfit"):
        lines.append(f"- **Outfit:** {res['outfit']}")
    if res.get("room"):
        lines.append(f"- **Setting:** {res['room']}")
    if res.get("summary"):
        lines.append(f"- **Summary:** {res['summary']}")
    if res.get("shot1") or res.get("beats"):
        lines.append("")
        lines.append("## Beats")
        if res.get("shot1"):
            lines.append(f"- `[Shot 1]` {res['shot1']}")
        for b in res.get("beats") or []:
            lines.append(f"- {b}")
    return "\n".join(lines)


def _scrub_extracted_result(res: dict) -> dict:
    out = dict(res)
    for k in ("cast", "outfit", "room", "summary", "music", "style"):
        if k in out and isinstance(out[k], str):
            out[k] = scrub_sheet_leaks(out[k])
    out["made_of"] = _normalize_made_of(out.get("made_of") or "", out.get("telemetry") or "")
    out["shot1"] = _clean_extracted_shot1(out.get("shot1") or "")
    out["beats"] = [scrub_sheet_leaks(str(b).strip()) for b in (out.get("beats") or []) if scrub_sheet_leaks(str(b).strip())]
    out["video_md"] = render_extracted_video_md(out)
    return out


async def _extract_json_with_repair(complete_fn, user_msg: dict, schema: dict, *, max_tokens: int = 3600) -> tuple[dict | None, str]:
    from .. import planner as _pl
    raw = await complete_fn([user_msg], schema=schema, temperature=0.2, max_tokens=max_tokens)
    obj = _pl._parse_obj(raw)
    if not isinstance(obj, dict):
        obj = _parse_lenient_json_obj(raw)
    if not isinstance(obj, dict):
        repair_msgs = [
            user_msg,
            {"role": "assistant", "content": str(raw or "")},
            {"role": "user", "content": "Your previous reply had invalid JSON syntax (such as a missing comma or unescaped quote). Return ONLY the fixed valid JSON object matching the exact schema, with no extra prose."},
        ]
        try:
            raw2 = await complete_fn(repair_msgs, schema=schema, temperature=0.1, max_tokens=max_tokens)
            obj = _pl._parse_obj(raw2) or _parse_lenient_json_obj(raw2)
            if isinstance(obj, dict):
                raw = raw2
        except Exception:
            pass
    return (obj if isinstance(obj, dict) else None), str(raw or "")


async def _extract_two_pass(complete_fn, strips, strip_headers, strip_meta, prompt_txt: str) -> dict | None:
    """Per-batch visual breakdown -> text synthesis (bounds vision tokens for 16k servers & long multi-cut clips)."""
    batch_size = 3
    notes = []
    for start_i in range(0, len(strips), batch_size):
        b_strips = strips[start_i:start_i + batch_size]
        b_hdrs = strip_headers[start_i:start_i + batch_size]
        b_meta = strip_meta[start_i:start_i + batch_size]
        content = []
        for idx, st_im in enumerate(b_strips):
            hdr = b_hdrs[idx] if idx < len(b_hdrs) else f"IMAGE {start_i + idx + 1}"
            content.append({"type": "text", "text": f"=== {hdr} ==="})
            content.append({"type": "image_url", "image_url": {"url": encode_pil_mp(st_im, mp=1.15)}})
        tel_block = "\n".join(m.get("telemetry") or "" for m in b_meta if m.get("telemetry"))
        content.append({"type": "text", "text": f"{STRIP_PASS1_SYSTEM}\n\nTELEMETRY FOR THESE STRIPS:\n{tel_block}"})
        obj_p1, _ = await _extract_json_with_repair(complete_fn, {"role": "user", "content": content}, STRIP_PASS1_SCHEMA, max_tokens=1800)
        if isinstance(obj_p1, dict):
            notes.append(obj_p1)

    if not notes:
        return None
    obs_lines = []
    for bi, n in enumerate(notes, 1):
        obs_lines.append(
            f"[Chunk {bi}] made_of={n.get('made_of', '')} | style={n.get('style', '')} | "
            f"cast={n.get('cast_notes', '')} | outfit={n.get('outfit_notes', '')} | room={n.get('room_notes', '')}"
        )
        for seg in n.get("segments") or []:
            obs_lines.append(
                f"  - {seg.get('label', '')}: shot_size={seg.get('shot_size', '')}; "
                f"camera={seg.get('camera_move', '')}; action={seg.get('action', '')}"
            )
    synth_msg = {
        "role": "user",
        "content": (
            "Chronological Per-Strip Visual Observations (from inspecting every storyboard strip in order):\n"
            + "\n".join(obs_lines)
            + "\n\nSynthesize these into one unified cast/outfit/room/choreography JSON matching all laws below:\n\n"
            + prompt_txt
        ),
    }
    obj_p2, _ = await _extract_json_with_repair(complete_fn, synth_msg, VIDEO_EXTRACT_SCHEMA, max_tokens=3600)
    return obj_p2


async def extract_video_to_plan(
    video_path: str,
    complete_fn,
    in_sec: float = 0.0,
    out_sec: float = 0.0,
    max_seconds: float = 15.0,
    two_pass: str | bool = "auto",
) -> dict:
    if not video_path or not os.path.isfile(video_path):
        raise ValueError(f"Video file not found: {video_path}")
    mtime = int(os.path.getmtime(video_path))
    cache_key = f"vidextract_v3|{os.path.abspath(video_path)}|{mtime}|{in_sec:.2f}|{out_sec:.2f}|{max_seconds:.1f}"
    cached = _load_cache().get(cache_key)
    if isinstance(cached, dict) and cached.get("beats"):
        return _scrub_extracted_result(cached)

    import asyncio
    bundle = await asyncio.get_running_loop().run_in_executor(
        None, _build_strips_bundle, video_path, in_sec, out_sec, max_seconds
    )
    strips = bundle["strips"]
    dur = bundle["dur"]
    cut_times = bundle["cut_times"]
    cuts_meta = bundle["cuts_meta"]
    telemetry_str = bundle["telemetry_str"]
    beats_skeleton_str = bundle["beats_skeleton_str"]
    strip_headers = bundle["strip_headers"]
    strip_meta = bundle["strip_meta"]

    if not strips:
        raise ValueError(f"Could not decode frames from video: {video_path}")

    if cut_times:
        cuts_str = ", ".join(f"{m['t']:.2f}s ({m['type']})" for m in cuts_meta)
        cuts_note = (
            f"OPENCV DETECTED {len(cut_times)} SHOT TRANSITION(S) AT: {cuts_str} "
            f"(dividing the {dur:.2f}s clip into {len(cut_times) + 1} shots).\n"
            f"Output all {len(cut_times) + 1} shots in order using the exact `[Shot N] At MM:SS.mmm, ...` and "
            f"`At MM:SS.mmm-MM:SS.mmm, ...` timestamps in the Mandatory Beat Skeleton!\n\n"
            f"OPTICAL FLOW & CAMERA TELEMETRY:\n{telemetry_str}"
        )
    else:
        cuts_note = (
            f"Continuous single-take clip ({dur:.2f}s, zero hard cuts). Describe each chronological `BEAT` strip using the exact "
            f"`At MM:SS.mmm-MM:SS.mmm` timestamps below.\n\nOPTICAL FLOW & CAMERA TELEMETRY:\n{telemetry_str}"
        )

    prompt_txt = VIDEO_EXTRACTOR_SYSTEM % {"cuts_note": cuts_note, "beats_skeleton": beats_skeleton_str}
    use_two_pass = (two_pass is True) or (two_pass == "auto" and len(strips) > 6)
    obj = None
    raw = ""

    if not use_two_pass:
        content = []
        for idx, st_im in enumerate(strips):
            hdr = strip_headers[idx] if idx < len(strip_headers) else f"IMAGE {idx + 1}"
            content.append({"type": "text", "text": f"=== {hdr} ==="})
            content.append({"type": "image_url", "image_url": {"url": encode_pil_mp(st_im, mp=1.35)}})
        content.append({"type": "text", "text": prompt_txt})
        user_msg = {"role": "user", "content": content}
        try:
            obj, raw = await _extract_json_with_repair(complete_fn, user_msg, VIDEO_EXTRACT_SCHEMA, max_tokens=3600)
        except Exception as exc:
            msg_low = str(exc).lower()
            if two_pass == "auto" and ("context" in msg_low or "token" in msg_low):
                use_two_pass = True
            else:
                raise

    if use_two_pass and not isinstance(obj, dict):
        obj = await _extract_two_pass(complete_fn, strips, strip_headers, strip_meta, prompt_txt)

    if not isinstance(obj, dict):
        snippet = re.sub(r"\s+", " ", str(raw or "")).strip()[:180]
        raise ValueError(f"Vision model did not return a JSON object for the video extraction. ({snippet or 'empty reply'})")
    res = _scrub_extracted_result({
        "ok": True,
        "name": str(obj.get("name") or os.path.splitext(os.path.basename(video_path))[0]),
        "made_of": str(obj.get("made_of") or ""),
        "style": str(obj.get("style") or ""),
        "cast": str(obj.get("cast") or ""),
        "duration_s": dur,
        "cuts": cut_times,
        "transitions": cuts_meta,
        "telemetry": telemetry_str,
        "outfit": str(obj.get("outfit") or ""),
        "room": str(obj.get("room") or ""),
        "summary": str(obj.get("summary") or ""),
        "shot1": _clean_extracted_shot1(obj.get("shot1") or ""),
        "beats": [str(b).strip() for b in (obj.get("beats") or []) if str(b).strip()],
        "music": str(obj.get("music") or ""),
        "two_pass": bool(use_two_pass),
    })
    if res["beats"]:
        _save_cache(cache_key, res)
    return res
