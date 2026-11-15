"""OpenCV 30-FPS Optical Flow + Jump-Cut Detector + 2.5 MP Reference Vision (User-Local Cache)."""
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
        "CRITICAL RULE: Focus 100% on the person/character. COMPLETELY IGNORE any black, dark grey, charcoal, white, or plain studio background, backdrop, void, floor, walls, or studio lighting — do NOT mention any background or studio environment! "
        "Write two sentences about the person ONLY (check all panels and zoomed inset crops if this is a reference sheet): "
        "Sentence 1 must start with \"Anchor: \" followed immediately by their exact racial/ethnic descent, facial bone structure, eye shape, and skin tone "
        "(e.g. 'East Asian woman with fair porcelain skin, soft East Asian facial features, and dark almond eyes', 'Southeast Asian woman with warm golden-tan skin and Southeast Asian facial features', "
        "'South Asian woman', 'Black woman with deep rich brown skin', 'Latina woman', 'Middle Eastern woman', 'Caucasian woman' — "
        "determine racial/ethnic descent strictly from facial bone structure and features in the face/inset panels, even when they wear dyed bright red, ginger-orange, blonde, pastel, or cosplay hair), "
        "followed by their exact hair colour, length, and style (plus facial hair if any), "
        "any worn jewellery, choker, hair clip, headband, glasses, or claw nails, and any visible tattoos, text tattoos, "
        "body markings, piercings, or horns including those shown in close-up inset panels. "
        "Sentence 2 must start with \"Wearing \" and state their exact garment construction and layers head-to-toe: "
        "specify whether it is a one-piece (bodysuit, swimsuit, leotard, dress) or two-piece (crop top, sports bra, "
        "shorts, bikini), any layered inner/outer pieces, and exact strap/closure details (spaghetti straps, wide tank "
        "straps, halter neck tie, button placket, waist band, socks, footwear). "
        "Never mention age, body weight, background, studio backdrop, or lighting, and never use negative words (no, not, never, without). "
        "Under 65 words total. Answer with the two sentences only."
    ),
    "auto": (
        "CRITICAL RULE: If this image contains ANY person, character, model, face, or body (including a portrait, lookbook photo, or multi-panel character reference/turnaround sheet on a black, dark grey, charcoal, or white background), focus 100% on the PERSON and COMPLETELY IGNORE the background, studio backdrop, walls, floor, void, and studio lighting! "
        "When a person is present, write two sentences about the person ONLY: "
        "Sentence 1 must start with \"Anchor: \" followed immediately by their exact racial/ethnic descent, facial bone structure, eye shape, and skin tone "
        "(judge ethnicity strictly from facial bone structure and features, even when they have dyed red, ginger-orange, blonde, silver, or cosplay hair), "
        "then their exact hair colour, length, and style, plus any jewellery, choker, headband, glasses, nails, tattoos, or body markings across all inset panels. "
        "Sentence 2 must start with \"Wearing \" and state their exact garment construction and layers head-to-toe (never mention the background or studio lighting). "
        "ONLY if the image contains ZERO people and shows an actual architectural room, street, landscape, or film set, start with \"Set: \" and describe the indoor/outdoor setting, surfaces, materials, colours, key objects, and lighting in under 45 words. "
        "ONLY if it shows a standalone object or wearable prop alone with zero people, start with \"Prop: \" and describe its shape, material, colour, and texture in one sentence. "
        "Never use negative words (no, not, never, without)."
    ),
    "place": (
        "Describe this place as a film set: whether indoors or outdoors, surfaces and materials, colours, key objects "
        "and furniture, and the light and time of day. Focus strictly on the environment and architecture, and never use negative words (no, not, "
        "never, without, empty). One concise paragraph under 45 words."
    ),
    "prop": (
        "Describe only this object or wearable prop: exact shape, material, colour, surface texture, and details. "
        "Focus strictly on the object itself, and never use negative words (no, not, never, without). "
        "One short sentence under 30 words."
    ),
    "frame": (
        "This picture is the opening frame of a video. Open with the medium and style (e.g. live-action cinematic, "
        "2D anime, 3D render), then state each person's exact racial/ethnic descent, facial features, and skin tone alongside their hair colour "
        "(e.g. 'an East Asian woman with fair porcelain skin and vibrant red hair'), what they are wearing, their exact posture and hand placement, "
        "the room/place, the lighting, and the camera framing. Never mention age or body weight, and "
        "never use negative words (no, not, never, without). One paragraph under 65 words."
    ),
}

VIDEO_EXTRACTOR_SYSTEM = """You are the SandTie Choreography & Camera Vision Extractor for MiniMax H3.
You are given Shot-by-Shot Storyboard Contact Strips of a reference video clip.
- Each image (`IMAGE 1 — SHOT 1`, `IMAGE 2 — SHOT 2`, ...) is a 3-frame horizontal strip (`START | MIDDLE | END`) for that exact shot or beat window.
%(cuts_note)s

CRITICAL EXTRACTION LAWS:
1. Always refer to the main person as `<Subject 1>` (and `<Subject 2>` if a second person is present).
2. Inside `shot1` and `beats`, keep the person's hair color, face identity, and skin tone out (put the garment description ONLY in `"outfit"`).
3. Translate motion speeds into natural kinematic prose (avoid numeric Hz values); describe skeletal joint movement first followed by `'with a natural, soft jiggle'` during active bounces or shimmies.
4. In `shot1`, lock Frame 0 (`0.00s`): state the camera framing/angle, `<Subject 1>`'s exact screen-direction body orientation (`facing straight forward toward the lens`, `standing in side profile facing toward the right edge of the frame with her head turned to look into the lens`, `three-quarter front view`), and exact starting left/right arm and hand placement.
5. For EVERY item in `"beats"`, keep the exact `[Shot N] At MM:SS.mmm...` and `At MM:SS.mmm-MM:SS.mmm...` timestamps from the Mandatory Beat Skeleton below, and describe:
   (a) body orientation & lean, (b) exact left & right arm/wrist/finger gesture, (c) hip/torso/leg movement, and (d) head tilt, gaze, and facial expression.
6. POSITIVE PHRASING ONLY: Keep words strictly positive (zero negative terms anywhere).

Reply with ONLY a valid JSON object matching this exact shape (without markdown fences):
{
  "name": "Short descriptive title (4-7 words)",
  "outfit": "Wearing ...",
  "room": "The exact setting and lighting visible in the frames",
  "summary": "1-2 sentence summary of <Subject 1> performing the sequence.",
  "shot1": "The [Shot 1] opening camera framing, setting, and t=0.0s body orientation + arm/hand pose sentence (excluding the '[Shot 1]' prefix).",
  "beats": [
%(beats_skeleton)s
  ],
  "music": "Upbeat 120 BPM studio track with a clean bassline and crisp percussion."
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


def _clean_desc(text: str, cap: int = 420, strip_studio: bool = False) -> str:
    t = re.sub(r"[*#_`>]+", "", text or "")
    t = re.sub(r"^(?:based on|here is|here's|sure|certainly|in this (?:image|picture|frame))[^:.]*[:.]\s*", "", t, flags=re.I)
    t = " ".join(t.split()).strip()
    if strip_studio or t.lower().startswith("anchor:"):
        t = _STUDIO_SCAN_SENT_RX.sub(" ", t)
    t = re.sub(r"\b(?:with\s+)?no\s+(?:visible\s+)?(?:tattoos?|markings?|jewell?ery|accessories)\b[,.]?", "", t, flags=re.I)
    t = re.sub(r"\bwithout\s+any\s+[^,.;]+", "", t, flags=re.I)
    t = " ".join(t.split()).strip()
    if len(t) > cap:
        cut = t[:cap].rsplit(". ", 1)[0]
        t = cut + ("." if not cut.endswith(".") else "")
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


async def scan_reference_file(path: str, role: str, complete_fn) -> str:
    if not path or not os.path.isfile(path):
        return ""
    role = role if role in ROLE_PROMPTS else "subject"
    mtime = int(os.path.getmtime(path))
    cache = _load_cache()
    key = f"refscan_v4|{os.path.abspath(path)}|{mtime}|{role}"
    hit = cache.get(key)
    if not (isinstance(hit, str) and hit.strip()):
        v3_hit = cache.get(f"refscan_v3|{os.path.abspath(path)}|{mtime}|{role}")
        if not v3_hit and role == "auto":
            v3_hit = cache.get(f"refscan_v3|{os.path.abspath(path)}|{mtime}|subject")
        if isinstance(v3_hit, str) and v3_hit.strip() and not is_studio_backdrop_scan(v3_hit):
            hit = v3_hit
    if isinstance(hit, str) and hit.strip() and not is_studio_backdrop_scan(hit):
        return _clean_desc(hit, 480, strip_studio=(role in ("subject", "auto")))
    try:
        data_url = encode_image_mp(path, mp=2.5 if role in ("subject", "auto", "frame") else 1.2)
        msgs = [{
            "role": "user",
            "content": [
                {"type": "text", "text": ROLE_PROMPTS[role]},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }]
        raw = await complete_fn(msgs, schema=None, temperature=0.2, max_tokens=240)
        cleaned = _clean_desc(raw, 480, strip_studio=(role in ("subject", "auto")))
        if role == "auto" and is_studio_backdrop_scan(cleaned):
            msgs_subj = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": ROLE_PROMPTS["subject"]},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }]
            raw_subj = await complete_fn(msgs_subj, schema=None, temperature=0.2, max_tokens=240)
            cleaned = _clean_desc(raw_subj, 480, strip_studio=True)
        if cleaned and not is_studio_backdrop_scan(cleaned):
            _save_cache(key, cleaned)
        return cleaned
    except Exception as exc:
        print(f"[HandTieClips-SandTie] vision scan skipped ({os.path.basename(path)}): {exc}", flush=True)
        return ""


def _fmt_mmss(t_sec: float) -> str:
    m_i = int(max(0.0, t_sec) // 60)
    s_r = max(0.0, t_sec) - m_i * 60
    return f"{m_i:02d}:{s_r:06.3f}"


def build_opencv_video_strips(video_path: str, in_sec: float = 0.0, out_sec: float = 0.0, max_seconds: float = 15.0):
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    cap = cv2.VideoCapture(video_path)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    n_frames = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    w = max(1, int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
    h = max(1, int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    total_dur = n_frames / fps

    t0 = max(0.0, min(float(in_sec or 0.0), max(0.0, total_dur - 0.5)))
    t1 = float(out_sec or 0.0)
    t1 = min(total_dur, t0 + max_seconds) if t1 <= t0 + 0.3 else min(total_dur, t0 + max_seconds, t1)
    raw_dur = max(1.0, round(t1 - t0, 2))

    start_f = max(0, int(round(t0 * fps)))
    end_f = min(n_frames, int(round(t1 * fps)))
    if start_f > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)

    prev_small = None
    prev_gray = None
    all_diffs = [0.0]
    frame_flows = []
    last_active_t = raw_dur

    for idx in range(end_f - start_f):
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        t_s = round(idx / fps, 3)
        small = cv2.resize(frame, (72, 128)).astype(np.float32)
        gray = cv2.cvtColor(small.astype(np.uint8), cv2.COLOR_BGR2GRAY)
        if prev_small is not None:
            diff = float(np.mean(np.abs(small - prev_small)))
            all_diffs.append(diff)
            mean_bright = float(np.mean(small))
            flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 2, 11, 2, 5, 1.1, 0)
            fx, fy = flow[..., 0], flow[..., 1]
            frame_motion = float(np.percentile(np.hypot(fx, fy), 90))
            if t_s > 4.5 and mean_bright < 52.0 and frame_motion < 0.25:
                last_active_t = round(max(2.5, t_s - 0.1), 1)
                break
            bg_mask = np.zeros_like(fx, dtype=bool)
            bg_mask[:, :10] = True
            bg_mask[:, -10:] = True
            cam_vx = float(np.median(fx[bg_mask]))
            cam_vy = float(np.median(fy[bg_mask]))
            rel_fx = fx - cam_vx
            rel_fy = fy - cam_vy
            ch_fx, ch_fy = rel_fx[32:64, 16:56], rel_fy[32:64, 16:56]
            hp_fx, hp_fy = rel_fx[64:100, 16:56], rel_fy[64:100, 16:56]
            frame_flows.append((
                t_s, cam_vx, cam_vy,
                float(np.mean(ch_fx)), float(np.percentile(np.hypot(ch_fx, ch_fy), 85)),
                float(np.mean(hp_fx)), float(np.percentile(np.hypot(hp_fx, hp_fy), 85)),
            ))
        prev_small = small
        prev_gray = gray

    dur = max(2.0, min(max_seconds, round(last_active_t, 2)))
    active_max_f = min(len(all_diffs), int(round(dur * fps)))

    cut_times = []
    for f_i in range(1, active_max_f):
        t_s = round(f_i / fps, 3)
        if t_s < 0.25 or t_s > dur - 0.25:
            continue
        d = all_diffs[f_i]
        win = [all_diffs[j] for j in range(max(1, f_i - 4), min(active_max_f, f_i + 5)) if j != f_i]
        loc_med = float(np.median(win)) if win else 1.0
        if d > 19.0 and (d / max(1.0, loc_med)) > 1.55:
            if not cut_times or (t_s - cut_times[-1]) >= 0.38:
                cut_times.append(round(t_s, 2))

    has_cuts = len(cut_times) > 0
    if has_cuts:
        bounds = [0.0] + cut_times + [dur]
        segments = [(i + 1, round(bounds[i], 3), round(bounds[i + 1], 3)) for i in range(len(bounds) - 1)]
    else:
        n_segs = max(3, min(6, int(round(dur / 2.2))))
        bounds = [round(i * dur / n_segs, 3) for i in range(n_segs + 1)]
        segments = [(i + 1, bounds[i], bounds[i + 1]) for i in range(n_segs)]

    telemetry_lines, skeleton_items, seg_short_badge = [], [], {}
    for seg_id, t_a, t_b in segments:
        seg_len = max(0.1, t_b - t_a)
        seg_rows = [r for r in frame_flows if (t_a + 0.045) < r[0] < (t_b - 0.035)] or [r for r in frame_flows if t_a <= r[0] <= t_b]
        if seg_rows:
            cam_vx = float(np.mean([r[1] for r in seg_rows]))
            cam_vy = float(np.mean([r[2] for r in seg_rows]))
            ch_e = float(np.mean([r[4] for r in seg_rows]))
            hp_e = float(np.mean([r[6] for r in seg_rows]))
            ch_vxs = [r[3] for r in seg_rows if abs(r[3]) > 0.16]
            hp_vxs = [r[5] for r in seg_rows if abs(r[5]) > 0.16]
            ch_hz = (sum(1 for a, b in zip(ch_vxs, ch_vxs[1:]) if a * b < 0) / 2.0) / seg_len if len(ch_vxs) > 1 else 0.0
            hp_hz = (sum(1 for a, b in zip(hp_vxs, hp_vxs[1:]) if a * b < 0) / 2.0) / seg_len if len(hp_vxs) > 1 else 0.0
        else:
            cam_vx = cam_vy = ch_e = hp_e = ch_hz = hp_hz = 0.0

        max_e = max(ch_e, hp_e)
        peak_hz = max(ch_hz, hp_hz)
        if cam_vy > 0.45:
            cam_desc = "CAMERA TILTING/PEDESTALING UPWARD"
        elif cam_vy < -0.45:
            cam_desc = "CAMERA TILTING/PEDESTALING DOWNWARD"
        elif abs(cam_vx) > 0.55:
            cam_desc = "CAMERA PANNING/TRUCKING SIDEWAYS"
        else:
            cam_desc = "STATIC TRIPOD"

        if max_e >= 2.3 or (seg_len >= 1.0 and peak_hz >= 2.8):
            e_desc, e_tag = "FAST ENERGETIC BOUNCE / SHIMMY", "energetic bounce and hip shimmy"
        elif seg_len >= 1.0 and (max_e >= 0.78 or peak_hz >= 1.2):
            e_desc, e_tag = "CONTINUOUS RHYTHMIC VERTICAL BOUNCE & SIDE-TO-SIDE HIP SWAY", "continuous rhythmic vertical knee-bounce and side-to-side hip sway"
        else:
            e_desc, e_tag = "POSED MICRO-CUT HOLD WITH SUBTLE HIP/POSTURE SWAY", "posed stance with subtle hip sway"

        seg_short_badge[seg_id] = f"{cam_desc} | {e_desc}"
        lbl_kind = f"SHOT {seg_id}" if has_cuts else f"BEAT {seg_id}"
        cut_prefix = f" [HARD JUMP-CUT AT {t_a:.2f}s]" if (has_cuts and seg_id > 1) else ""
        telemetry_lines.append(
            f"  • IMAGE {seg_id} -> {lbl_kind} ({_fmt_mmss(t_a)}–{_fmt_mmss(t_b)}, dur={seg_len:.2f}s){cut_prefix}: "
            f"[{cam_desc}] | [{e_desc}] — Inspect the 3 frames (START | MIDDLE | END) of IMAGE {seg_id} and describe "
            f"<Subject 1>'s exact screen-direction body orientation, left & right hand/finger pose, {e_tag}, and facial expression!"
        )
        if has_cuts and seg_id > 1:
            skeleton_items.append(f'    "[Shot {seg_id}] At {_fmt_mmss(t_a)}, the camera cuts to a hard jump-cut in the exact same spot with <Subject 1> <describe {lbl_kind} body orientation and starting hand/arm position>."')
        skeleton_items.append(f'    "At {_fmt_mmss(t_a)}-{_fmt_mmss(t_b)}, <Subject 1> <describe {lbl_kind} exact left/right hand gesture, {e_tag}, and eye contact / facial expression>."')

    try:
        font_big = ImageFont.truetype("arialbd.ttf", 22)
        font_sub = ImageFont.truetype("arialbd.ttf", 17)
    except Exception:
        font_big = font_sub = None

    cols, thumb_w = 3, 260
    thumb_h = max(140, int(thumb_w * h / max(1, w)))
    row_banner_h, frame_hdr_h = 36, 26
    strip_h = thumb_h + row_banner_h + frame_hdr_h + 2
    shot_palette = [(25, 55, 115), (155, 25, 50), (20, 100, 75), (135, 70, 15), (80, 35, 125), (20, 95, 120), (125, 30, 90), (55, 95, 30)]

    strips, strip_headers = [], []
    stage_names = ["START", "MIDDLE", "END"]
    for seg_id, t_a, t_b in segments[:10]:
        seg_len = max(0.15, t_b - t_a)
        pad = min(0.06, seg_len * 0.14)
        t_start = t_a + pad
        t_end = max(t_start, t_b - pad)
        canvas = Image.new("RGB", (cols * thumb_w, strip_h), (14, 14, 18))
        draw = ImageDraw.Draw(canvas)
        hdr_col = shot_palette[(seg_id - 1) % len(shot_palette)]
        kind_prefix = f"SHOT {seg_id}" if has_cuts else f"BEAT {seg_id}"
        cut_str = f" [JUMP-CUT AT {t_a:.2f}s]" if (has_cuts and seg_id > 1) else " [OPENING SHOT]"
        draw.rectangle([0, 0, cols * thumb_w, row_banner_h], fill=hdr_col)
        draw.text((10, 6), f"{kind_prefix} ({_fmt_mmss(t_a)} - {_fmt_mmss(t_b)}){cut_str}", fill=(255, 250, 120), font=font_big)

        for c_i in range(cols):
            t_sec = round(t_start + (c_i / float(cols - 1)) * (t_end - t_start), 2)
            f_no = min(n_frames - 1, max(0, int(round((t0 + t_sec) * fps))))
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_no)
            ok, frame = cap.read()
            if ok and frame is not None:
                im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                x0 = c_i * thumb_w
                fy0 = row_banner_h + 1
                draw.rectangle([x0, fy0, x0 + thumb_w - 2, fy0 + frame_hdr_h], fill=(24, 24, 32))
                draw.text((x0 + 8, fy0 + 3), f"{kind_prefix} {stage_names[c_i]} ({t_sec:.2f}s)", fill=(180, 255, 195), font=font_sub)
                canvas.paste(im, (x0, fy0 + frame_hdr_h + 1))
        strips.append(canvas)
        strip_headers.append(f"IMAGE {seg_id} — {kind_prefix} ({_fmt_mmss(t_a)} to {_fmt_mmss(t_b)}){cut_str} | {seg_short_badge.get(seg_id, '')}")
    cap.release()
    return strips, dur, cut_times, "\n".join(telemetry_lines), ",\n".join(skeleton_items), strip_headers


VIDEO_EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "outfit", "room", "summary", "shot1", "beats", "music"],
    "properties": {
        "name": {"type": "string"},
        "outfit": {"type": "string"},
        "room": {"type": "string"},
        "summary": {"type": "string"},
        "shot1": {"type": "string"},
        "beats": {"type": "array", "items": {"type": "string"}},
        "music": {"type": "string"},
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


def _parse_lenient_json_obj(raw: str) -> dict | None:
    txt = str(raw or "").strip()
    if not txt:
        return None
    # Strip <think>...</think> blocks if any
    txt = re.sub(r"<think>[\s\S]*?</think>", "", txt, flags=re.I).strip()

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


async def extract_video_to_plan(video_path: str, complete_fn, in_sec: float = 0.0, out_sec: float = 0.0, max_seconds: float = 15.0) -> dict:
    if not video_path or not os.path.isfile(video_path):
        raise ValueError(f"Video file not found: {video_path}")
    mtime = int(os.path.getmtime(video_path))
    cache_key = f"vidextract|{os.path.abspath(video_path)}|{mtime}|{in_sec:.2f}|{out_sec:.2f}|{max_seconds:.1f}"
    cached = _load_cache().get(cache_key)
    if isinstance(cached, dict) and cached.get("beats"):
        return cached

    import asyncio
    strips, dur, cut_times, telemetry_str, beats_skeleton_str, strip_headers = await asyncio.get_running_loop().run_in_executor(
        None, build_opencv_video_strips, video_path, in_sec, out_sec, max_seconds
    )
    if cut_times:
        cuts_str = ", ".join(f"{ct:.2f}s" for ct in cut_times)
        cuts_note = (
            f"OPENCV DETECTED {len(cut_times)} HARD JUMP-CUTS AT: {cuts_str} "
            f"(dividing the {dur:.2f}s clip into {len(cut_times) + 1} shots).\n"
            f"Output all {len(cut_times) + 1} shots in order using the exact `[Shot N] At MM:SS.mmm...` and "
            f"`At MM:SS.mmm-MM:SS.mmm...` timestamps in the Mandatory Beat Skeleton!\n\n"
            f"30-FPS OPTICAL FLOW TELEMETRY:\n{telemetry_str}"
        )
    else:
        cuts_note = (
            f"Continuous single-take clip ({dur:.2f}s). Describe each `BEAT N` strip using the exact "
            f"`At MM:SS.mmm-MM:SS.mmm` timestamps below.\n\n30-FPS OPTICAL FLOW TELEMETRY:\n{telemetry_str}"
        )

    prompt_txt = VIDEO_EXTRACTOR_SYSTEM % {"cuts_note": cuts_note, "beats_skeleton": beats_skeleton_str}
    content = []
    for idx, st_im in enumerate(strips):
        hdr = strip_headers[idx] if idx < len(strip_headers) else f"IMAGE {idx + 1}"
        content.append({"type": "text", "text": f"=== {hdr} ==="})
        content.append({"type": "image_url", "image_url": {"url": encode_pil_mp(st_im, mp=1.0)}})
    content.append({"type": "text", "text": prompt_txt})

    user_msg = {"role": "user", "content": content}
    raw = await complete_fn([user_msg], schema=VIDEO_EXTRACT_SCHEMA, temperature=0.25, max_tokens=2200)
    from .. import planner as _pl
    obj = _pl._parse_obj(raw)
    if not isinstance(obj, dict):
        obj = _parse_lenient_json_obj(raw)
    if not isinstance(obj, dict):
        # Single fast JSON-repair turn reusing the cached multimodal KV prefix
        repair_msgs = [
            user_msg,
            {"role": "assistant", "content": str(raw or "")},
            {"role": "user", "content": "Your previous reply had invalid JSON syntax (such as a missing comma or unescaped quote). Return ONLY the fixed valid JSON object matching the exact schema, with no extra prose."},
        ]
        try:
            raw2 = await complete_fn(repair_msgs, schema=VIDEO_EXTRACT_SCHEMA, temperature=0.1, max_tokens=2200)
            obj = _pl._parse_obj(raw2) or _parse_lenient_json_obj(raw2)
            if isinstance(obj, dict):
                raw = raw2
        except Exception:
            pass
    if not isinstance(obj, dict):
        snippet = re.sub(r"\s+", " ", str(raw or "")).strip()[:180]
        raise ValueError(f"Vision model did not return a JSON object for the video extraction. ({snippet or 'empty reply'})")
    res = {
        "ok": True,
        "name": str(obj.get("name") or os.path.splitext(os.path.basename(video_path))[0]),
        "duration_s": dur,
        "cuts": cut_times,
        "telemetry": telemetry_str,
        "outfit": str(obj.get("outfit") or ""),
        "room": str(obj.get("room") or ""),
        "summary": str(obj.get("summary") or ""),
        "shot1": str(obj.get("shot1") or ""),
        "beats": [str(b).strip() for b in (obj.get("beats") or []) if str(b).strip()],
        "music": str(obj.get("music") or ""),
    }
    if res["beats"]:
        _save_cache(cache_key, res)
    return res
