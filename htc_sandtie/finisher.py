"""Deterministic H3 prompt contract finisher, audio sanitizer, alignment headers, and Pass-2 checklist."""
from __future__ import annotations

import re

from .. import standard as _std
from . import beat_grid as _bg
from . import catalogs as _cat
from . import dialogue as _dlg
from . import director_cards as _dir
from . import refs as _refs

MAX_H3_CHARS = 7000

_NEG_REPLACEMENTS = (
    (re.compile(r"\bwithout\s+looking\s+up\s+from\b", re.I), "keeping their gaze locked down on"),
    (re.compile(r"\bwithout\s+looking\s+up\b", re.I), "keeping their gaze down"),
    (re.compile(r"\bwithout\s+looking\s+back\b", re.I), "keeping their gaze forward"),
    (re.compile(r"\bwithout\s+looking\s+away\b", re.I), "holding unbroken eye contact"),
    (re.compile(r"\bwithout\s+taking\s+(?:her|his|their)\s+eyes\s+off\b", re.I), "keeping their eyes locked on"),
    (re.compile(r"\bwithout\s+breaking\s+(?:her|his|their|the)?\s*(?:eye\s+contact|gaze|seal|stride|rhythm)\b", re.I), "keeping unbroken contact and rhythm"),
    (re.compile(r"\bwithout\s+blinking\b", re.I), "with an unblinking gaze"),
    (re.compile(r"\bwithout\s+pulling\s+(?:all\s+the\s+way\s+)?out\b", re.I), "staying deeply connected inside"),
    (re.compile(r"\bwithout\s+letting\s+go\b", re.I), "holding the grip tight"),
    (re.compile(r"\bwithout\s+(?:stopping|pausing)\b", re.I), "in one continuous, unbroken motion"),
    (re.compile(r"\bwithout\s+moving\s+their\s+wings\b", re.I), "gliding on outstretched wings"),
    (re.compile(r"\bwithout\s+moving\b", re.I), "holding steady in place"),
    (re.compile(r"\bwithout\s+hesitation\b", re.I), "immediately and decisively"),
    (re.compile(r"\bwithout\s+speaking\b", re.I), "with lips pressed gently shut"),
    (re.compile(r"\bwithout\s+a\s+(?:word|sound)\b", re.I), "in quiet poise"),
    (re.compile(r"\bwithout\s+any\s+[a-z]+(?:\s+[a-z]+)?\b", re.I), "cleanly"),
    (re.compile(r"\bwithout\b", re.I), "while"),
    (re.compile(r"\b(?:is|stays|remains)\s+(?:never|not)\s+(?:in\s+(?:the\s+)?(?:picture|frame|shot|view)|visible|seen|shown)\b", re.I), "stays out of frame"),
    (re.compile(r"\bnever\s+in\s+(?:the\s+)?(?:picture|frame|shot|view)\b", re.I), "out of frame"),
    (re.compile(r"\bnever\s+(?:stops?|pauses?|ceases?|ends?)\b", re.I), "continues non-stop"),
    (re.compile(r"\bnever\s+(?:turns?|looks?)\s+(?:around|back)\b", re.I), "keeps facing forward"),
    (re.compile(r"\bnever\s+pulls?\s+out\b", re.I), "stays buried deep inside"),
    (re.compile(r"\bnever\s+leaving\b", re.I), "staying locked on"),
    (re.compile(r"\bnever\s+breaking\b", re.I), "holding unbroken"),
    (re.compile(r"\bnever\s+taking\b", re.I), "keeping"),
    (re.compile(r"\bnever\b", re.I), "consistently"),
    (re.compile(r"\bno\s+phone\s+is\s+visible\b", re.I), "only the extended arm enters the corner of the frame"),
    (re.compile(r"\bno\s+phone\s+visible\b", re.I), "only the extended arm in the corner of the frame"),
    (re.compile(r"\bno\s+longer\b", re.I), "now"),
    (re.compile(r"\bno\s+other\b", re.I), "only"),
    (re.compile(r"\bno\s+sound\b", re.I), "quiet room tone"),
    (re.compile(r"\bno\s+fast\s+drums\b", re.I), "smooth beatless sustain"),
    (re.compile(r"\bno\b", re.I), "zero"),
    (re.compile(r"\b(?:does\s+not|doesn'?t|do\s+not|don'?t)\s+pull\s+out\b", re.I), "stays buried deep inside"),
    (re.compile(r"\b(?:does\s+not|doesn'?t|do\s+not|don'?t)\s+(?:turn|look)\s+(?:around|back)\b", re.I), "keeps facing forward"),
    (re.compile(r"\b(?:do\s+not|don'?t)\s+stop\b", re.I), "keep going"),
    (re.compile(r"\bdo\s+not\b|\bdon'?t\b|\bdoesn'?t\b", re.I), "keep"),
    (re.compile(r"\b(?:is\s+not|isn'?t|aren'?t)\s+(?:visible|seen|shown|in\s+frame)\b", re.I), "stays out of frame"),
    (re.compile(r"\bis\s+not\b|\bisn'?t\b|\baren'?t\b", re.I), "remains"),
    (re.compile(r"\bcan'?t\b|\bwon'?t\b", re.I), "will"),
    (re.compile(r"\bnot\s+yet\b", re.I), "poised to"),
    (re.compile(r"\bnot\s+(?:visible|seen|shown|in\s+frame)\b", re.I), "out of frame"),
    (re.compile(r"\bnot\b", re.I), "cleanly"),
    (re.compile(r"\bavoid(?:s|ing)?\b", re.I), "clear of"),
)

_TIME_PAT = r"\d{1,2}:\d{2}(?:\.\d+)?"
_BEAT_RUNIN = re.compile(rf"([.!?\"\u201d]|</d>)[ \t]+(At[ \t]+{_TIME_PAT}[ \t]*(?:[-\u2013\u2014]|to)[ \t]*{_TIME_PAT})")
_HDR_RUNIN = re.compile(r"([^\n])[ \t]+(?<!from )(?<!\()(?<!in )(?<!, )(\[\s*Shot\s+\d+\s*\])")
_CJK_OUTSIDE = re.compile(r"[ \t]*[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]+")
_META_SCAFFOLD_RX = re.compile(
    r",?\s*\bembodying\s+the\s+[^.,;\n]*?\bstaging\b"
    r"|,?\s*\bfulfilling\s+the\s+(?:continuous\s+transition|staging|playbook\s+module)\b"
    r"|,?\s*\bcompleting\s+the\s+continuous\s+entry\s+and\s+climax\s+payoff\b",
    re.I,
)


def _clean_outside_d(text: str, fn) -> str:
    parts = re.split(r"(<d>.*?</d>)", text, flags=re.S | re.I)
    for i in range(0, len(parts), 2):
        parts[i] = fn(parts[i])
    return "".join(parts)


def _clean_inside_d(text: str) -> str:
    parts = re.split(r"(<d>.*?</d>)", text, flags=re.S | re.I)
    for i in range(1, len(parts), 2):
        inner = _dlg.sanitize_gluck(parts[i])
        inner = inner.replace("\u201c", "'").replace("\u201d", "'").replace('"', "'")
        parts[i] = inner
    return "".join(parts)


def _strip_all_dialogue(text: str) -> str:
    out = str(text or "")
    out = re.sub(r"[ \t]*\(DIALOGUE\)[^\n<]*<d>.*?</d>[ \t]*\.?", "", out, flags=re.S | re.I)
    out = re.sub(r"[ \t]*\(DIALOGUE\)[^\n]*", "", out, flags=re.I)
    out = re.sub(r"[ \t]*<d>.*?</d>[ \t]*\.?", "", out, flags=re.S | re.I)
    return out


def sanitize_additive_rule(text: str) -> str:
    out = str(text or "")
    out = re.sub(r"\(\s*(?:no|not|never|without|avoid)\b[^)]{0,50}\)", "", out, flags=re.I)
    for rx, repl in _NEG_REPLACEMENTS:
        out = rx.sub(repl, out)
    out = _META_SCAFFOLD_RX.sub("", out)
    return re.sub(r"\s{2,}", " ", out).strip()


def _normalize_multishot_timeline(desc_body: str, duration_s: float) -> str:
    dur = round(max(2.0, float(duration_s or 10.0)), 3)
    text = str(desc_body or "").strip()
    if not text:
        return text

    shot_hdr_rx = re.compile(r"\[\s*Shot\s+(\d+)\s*\]", re.I)
    range_rx = re.compile(r"\bAt\s+(\d+):(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+):(\d+(?:\.\d+)?)", re.I)

    matches = list(shot_hdr_rx.finditer(text))
    if not matches:
        return text

    prefix = text[:matches[0].start()]
    chunks = [text[m.start():(matches[i + 1].start() if i + 1 < len(matches) else len(text))] for i, m in enumerate(matches)]

    if len(chunks) >= 2:
        shot_ranges = [[(int(rm.group(1)) * 60 + float(rm.group(2)), int(rm.group(3)) * 60 + float(rm.group(4))) for rm in range_rx.finditer(ch)] for ch in chunks]
        needs_rescale = False
        prev_max_end = 0.0
        for idx, r_list in enumerate(shot_ranges):
            if not r_list:
                continue
            if idx > 0 and r_list[0][0] < prev_max_end - 0.15:
                needs_rescale = True
                break
            if max(b for _, b in r_list) > dur + 0.15:
                needs_rescale = True
                break
            prev_max_end = max(prev_max_end, max(b for _, b in r_list))

        weights = [
            sum(max(0.4, b - a) for a, b in r_list) if r_list else 1.5
            for r_list in shot_ranges
        ]
        total_w = float(sum(weights)) or 1.0
        min_shot_gap = 0.55 if len(chunks) >= 6 else 0.8
        slice_bounds = [0.0]
        acc = 0.0
        for w in weights[:-1]:
            acc += w
            slice_bounds.append(round((acc / total_w) * dur, 2))
        slice_bounds.append(dur)
        for i in range(1, len(slice_bounds) - 1):
            slice_bounds[i] = max(slice_bounds[i], round(slice_bounds[i - 1] + min_shot_gap, 2))
        for i in range(len(slice_bounds) - 2, 0, -1):
            slice_bounds[i] = min(slice_bounds[i], round(slice_bounds[i + 1] - min_shot_gap, 2))

        new_chunks = []
        last_cut_t = 0.0
        for idx, ch in enumerate(chunks):
            shot_num = idx + 1
            s_a, s_b = slice_bounds[idx], slice_bounds[idx + 1]
            r_list = shot_ranges[idx]
            if needs_rescale and r_list:
                beat_durs = [max(0.3, b - a) for a, b in r_list]
                bd_tot = float(sum(beat_durs)) or 1.0
                b_bounds = [s_a]
                b_acc = 0.0
                for bd in beat_durs[:-1]:
                    b_acc += bd
                    b_bounds.append(round(s_a + (b_acc / bd_tot) * (s_b - s_a), 2))
                b_bounds.append(s_b)
                cnt = [0]

                def _rescale_range(_m, bb=b_bounds, c=cnt):
                    bi = min(c[0], len(bb) - 2)
                    c[0] += 1
                    t0 = bb[bi]
                    t1 = bb[bi + 1]
                    return f"At {_bg.stamp(t0)}-{_bg.stamp(t1)}"

                ch = range_rx.sub(_rescale_range, ch)
                first_beat_start = s_a
            else:
                first_beat_start = r_list[0][0] if r_list else s_a

            if shot_num == 1:
                ch = re.sub(
                    r"^\[\s*Shot\s+\d+\s*\][ \t]*(?:At[ \t]+\d{1,2}:\d{2}(?:\.\d+)?(?:[ \t]*[-–—][ \t]*\d{1,2}:\d{2}(?:\.\d+)?)?[,\s]*)?",
                    "[Shot 1] ",
                    ch,
                    count=1,
                    flags=re.I,
                )
            else:
                cut_t = max(round(last_cut_t + 0.4, 2), min(round(dur - 0.5, 2), round(first_beat_start, 3)))
                last_cut_t = cut_t
                m_has_at = re.match(
                    r"^\[\s*Shot\s+\d+\s*\][ \t]*At[ \t]+\d{1,2}:\d{2}(?:\.\d+)?(?:[ \t]*[-–—][ \t]*\d{1,2}:\d{2}(?:\.\d+)?)?[ \t]*,?[ \t]*",
                    ch,
                    flags=re.I,
                )
                if m_has_at:
                    ch = f"[Shot {shot_num}] At {_bg.stamp(cut_t)}, " + ch[m_has_at.end():]
                else:
                    m_hdr = re.match(r"^\[\s*Shot\s+\d+\s*\][ \t,:.-]*", ch, flags=re.I)
                    rest_ch = ch[m_hdr.end():] if m_hdr else ch
                    ch = f"[Shot {shot_num}] At {_bg.stamp(cut_t)}, " + rest_ch
            new_chunks.append(ch)
        text = prefix + "".join(new_chunks)
    else:
        text = re.sub(
            r"\[\s*Shot\s+1\s*\][ \t]*(?:At[ \t]+\d{1,2}:\d{2}(?:\.\d+)?(?:[ \t]*[-–—][ \t]*\d{1,2}:\d{2}(?:\.\d+)?)?[,\s]*)?",
            "[Shot 1] ",
            text,
            count=1,
            flags=re.I,
        )

    def _clamp(m):
        s0 = int(m.group(1)) * 60 + float(m.group(2))
        s1 = int(m.group(3)) * 60 + float(m.group(4))
        if s1 > dur:
            s1 = dur
        if s0 >= s1:
            s0 = max(0.0, round(s1 - 0.5, 3))
        return f"At {_bg.stamp(s0)}-{_bg.stamp(s1)}"

    return range_rx.sub(_clamp, text)


def clean_plan_output(raw_plan: str, duration_s: float, silent: bool = False) -> str:
    t = str(raw_plan or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not t:
        return t
    t = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", t.strip())
    m_shot1 = re.search(r"\[\s*Shot\s+1\s*\]", t, flags=re.I)
    if m_shot1:
        t = t[m_shot1.start():]
        for tail_hdr in ("overall_soundscape:", "non_diegetic_music:", "Overall Soundscape:", "Non-Diegetic Music:"):
            pos = t.find(tail_hdr)
            if pos > 0:
                t = t[:pos].rstrip()
    if silent:
        t = _strip_all_dialogue(t)
    t = _BEAT_RUNIN.sub(r"\1\n\2", t)
    t = _HDR_RUNIN.sub(r"\1\n\2", t)
    t = _META_SCAFFOLD_RX.sub("", t)
    t = _normalize_multishot_timeline(t, duration_s)
    return t.strip()


def is_pure_bgm_soundscape(
    brief: str = "",
    flavors: dict | None = None,
    *,
    sex_scene: bool | None = None,
    combat_scene: bool | None = None,
) -> bool:
    """Return True when soundscape should stay N/A so BGM plays cleanly unobstructed."""
    flavors = flavors or {}
    raw_amb_str = str(flavors.get("ambience") or "").strip().lower()
    raw_amb = _cat.parse_multi_ids(flavors.get("ambience"))
    if raw_amb_str == "none" or "amb_none_na" in raw_amb:
        return True
    explicit_amb = [
        o for o in _cat.resolve_dial_opts("ambience", flavors.get("ambience"))
        if o.get("id") not in ("none", "amb_none_na") and (o.get("rule") or o.get("world"))
    ]
    if explicit_amb:
        return False
    raw_mus_str = str(flavors.get("music") or "").strip().lower()
    raw_music = _cat.parse_multi_ids(flavors.get("music"))
    if raw_mus_str == "none" or "none" in raw_music:
        return False
    if sex_scene is None:
        sex_scene = _dir.is_sexual(brief, str(flavors.get("explicit") or ""), str(flavors.get("wardrobe") or ""), fetish_id=str(flavors.get("fetish") or ""))
    if combat_scene is None:
        combat_scene = _dir.is_combat(brief, str(flavors.get("combat") or ""), str(flavors.get("wardrobe") or ""), str(flavors.get("fx") or ""))
    if sex_scene or combat_scene:
        return False
    pose_opts_d = _cat.resolve_dial_opts("pose", flavors.get("pose"))
    has_dance = (
        any(str(o.get("id") or "").startswith("dance_") or "dance" in str(o.get("group") or "").lower() for o in pose_opts_d)
        or bool(re.search(r"(?:^|[\s_-])danc(?:e|ing|er)(?:$|[\s_-])", f"{flavors.get('pose') or ''} {brief or ''}", re.I))
    )
    wants_foley = bool(re.search(r"\b(?:foley|soundscape|footsteps?|heel\s*clicks?|surf|waves?|rain|thunder|crowd|cheers?|applause|wind\s*sound|room\s*tone)\b", brief or "", re.I))
    return has_dance and not wants_foley


def _sanitize_audio_sections(block: str, silent: bool = False) -> str:
    """Enforce H3 audio laws: replace `;` with `, ` in soundscape & music, keep music out of soundscape, and keep vocal chatter out."""
    out = block
    mus_raw = (_std._field(out, "non_diegetic_music:") or "").strip()
    mus_norm = re.sub(r"\s*;\s*", ", ", mus_raw).strip(" .") if mus_raw and mus_raw.upper() != "N/A" else ""
    for fld, next_rx in (("overall_soundscape:", r"\n+(?=non_diegetic_music:)"), ("non_diegetic_music:", r"$")):
        val = _std._field(out, fld)
        if not val:
            continue
        cleaned = re.sub(r"\s*;\s*", ", ", val.strip())
        if fld == "overall_soundscape:":
            if cleaned.strip().upper() == "N/A":
                cleaned = "N/A"
            else:
                if mus_norm and len(mus_norm) >= 12 and mus_norm.lower() in cleaned.lower():
                    cleaned = re.sub(
                        rf"{re.escape(mus_norm)}[.\s,]*(?:layered\s+over|mixed\s+with|underneath|over)?\s*",
                        "",
                        cleaned,
                        flags=re.I,
                    )
                cleaned = re.sub(
                    r"\b(?:high[- ]energy|upbeat|driving|sleek|moody|fierce|bright|bubbly|explosive|hyper[- ]?pop|industrial|viral)?\s*\d{2,3}\s*BPM\b[^.\n]*?(?:layered\s+over\b|mixed\s+with\b|synth\s+stabs?|bass\s+drops?|vocal\s+chops?|snare\s+(?:build|hits?|rolls?)|arpeggios?|four-on-the-floor\s+kick|house\s+banger|dance-pop\s+banger)[.,\s]*",
                    "",
                    cleaned,
                    flags=re.I,
                )
                # Keep soundscape free of speech/dialogue tokens so H3 doesn't hallucinate extra talking
                cleaned = re.sub(r",?\s*\b(?:spoken\s+)?(?:dialogue|voice(?:s|lines?)?|speech|talking|whispered\s+words)\b[^,.\n]*", "", cleaned, flags=re.I)
                if silent:
                    cleaned = re.sub(r",?\s*\b(?:moans?|gasps?|groans?|panting|cries|whispers?)\b[^,.\n]*", "", cleaned, flags=re.I)
                cleaned = re.sub(r",\s*,+", ", ", cleaned).strip(" ,.")
                if not cleaned or len(cleaned) < 12:
                    cleaned = "Quiet natural room tone and subtle tactile fabric movement foley"
                cleaned = cleaned[0].upper() + cleaned[1:].rstrip(".") + "."
        out = re.sub(
            rf"({re.escape(fld)}[ \t]*\r?\n)(.*?){next_rx}",
            lambda m, c=cleaned: m.group(1) + c + ("\n\n" if fld == "overall_soundscape:" else ""),
            out,
            count=1,
            flags=re.S,
        )
    return out


_EMOJI_STRIP_RX = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+\s*")
_UI_WARDROBE_LABEL_RX = re.compile(
    r"\bWearing\s+(?:NUDE(?:\s*\([^)]*\))?|FETISH(?:\s+NUDE)?|PARTIAL|TOPLESS|BOTTOMLESS)\s*[—\-–]+\s*[^:\n]+:\s*",
    re.I,
)
_UI_STATE_LABEL_RX = re.compile(
    r"`?(?:NUDE(?:\s*\([^)]*\))?|FETISH(?:\s+NUDE)?|PARTIAL|TOPLESS|BOTTOMLESS)\s*[—\-–]+\s*([^`\n]+?)`?(?=\s+state\b)",
    re.I,
)
_CUT_WITHOUT_SHOT_RX = re.compile(
    rf"(?m)^(?!(?:\[\s*Shot\s+\d+\s*\]))(At[ \t]+{_TIME_PAT}[ \t]*,[ \t]*(?:the[ \t]+)?(?:camera|shot)[ \t]+(?:cuts|switches|transitions)\b)",
    re.I,
)


def _restore_missing_shot_cut_headers(desc_body: str) -> str:
    """Restore `[Shot N]` on lines opening with `At MM:SS.mmm, camera cuts...` when `[Shot 1]` is present."""
    if not desc_body or not re.search(r"\[\s*Shot\s+1\s*\]", desc_body, flags=re.I):
        return desc_body
    existing_nums = [int(m.group(1)) for m in re.finditer(r"\[\s*Shot\s+(\d+)\s*\]", desc_body, flags=re.I)]
    next_n = [max(existing_nums, default=1) + 1]

    def _add_shot_hdr(m):
        tag = f"[Shot {next_n[0]}] "
        next_n[0] += 1
        return tag + m.group(1)

    return _CUT_WITHOUT_SHOT_RX.sub(_add_shot_hdr, desc_body)


def _replace_section_body(text: str, field: str, body: str, next_fields: tuple[str, ...]) -> str:
    """Replace the body under `field` cleanly whether separated by 1 or 2 newlines (or inline)."""
    body_clean = str(body or "").strip()
    if next_fields:
        next_alt = "|".join(re.escape(nf) for nf in next_fields)
        pat = rf"(?ms)^({re.escape(field)})[ \t]*(?:\n|$)(.*?)(?=^(?:{next_alt})[ \t]*(?:\n|$)|\Z)"
    else:
        pat = rf"(?ms)^({re.escape(field)})[ \t]*(?:\n|$)(.*)\Z"
    if re.search(pat, text):
        return re.sub(pat, lambda m: f"{m.group(1)}\n{body_clean}\n\n" if next_fields else f"{m.group(1)}\n{body_clean}", text, count=1)
    return text


def _ensure_ref2va_headers(text: str) -> str:
    """Ensure canonical 6-field Ref2VA section headers exist on their own lines."""
    t = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not t:
        return t
    if "detailed_description:" not in t and "integrated_multimodal_description:" in t:
        t = re.sub(r"(?m)^integrated_multimodal_description:", "detailed_description:", t, count=1)
    all_hdrs = (
        "subject_definitions:", "summary:", "retention_analysis:",
        "detailed_description:", "overall_soundscape:", "non_diegetic_music:",
    )
    for hdr in all_hdrs:
        t = re.sub(rf"(?mi)([^\n])[ \t]+({re.escape(hdr)})", lambda m, h=hdr: f"{m.group(1)}\n\n{h}", t)
        t = re.sub(rf"(?mi)^({re.escape(hdr)})[ \t]+([^\n]+)", lambda m, h=hdr: f"{h}\n{m.group(2).strip()}", t)
        t = re.sub(rf"(?mi)^{re.escape(hdr)}(?=[ \t]*(?:\n|$))", hdr, t)
    if "detailed_description:" not in t:
        first_body_pos = 0
        m_shot = re.search(r"(?m)^\[\s*Shot\s+1\s*\]", t)
        if m_shot:
            first_body_pos = m_shot.start()
        t = (t[:first_body_pos].rstrip() + "\n\ndetailed_description:\n" + t[first_body_pos:].lstrip()).strip()
    if "retention_analysis:" not in t:
        t = re.sub(r"(?m)^detailed_description:", "retention_analysis:\n\ndetailed_description:", t, count=1)
    if "summary:" not in t:
        t = re.sub(r"(?m)^retention_analysis:", "summary:\n\nretention_analysis:", t, count=1)
    if "subject_definitions:" not in t:
        t = "subject_definitions:\n\n" + t.lstrip()
    if "overall_soundscape:" not in t:
        t = re.sub(r"(?m)^non_diegetic_music:", "overall_soundscape:\nNatural room tone.\n\nnon_diegetic_music:", t, count=1)
        if "overall_soundscape:" not in t:
            t = t.rstrip() + "\n\noverall_soundscape:\nNatural room tone."
    if "non_diegetic_music:" not in t:
        t = t.rstrip() + "\n\nnon_diegetic_music:\nN/A"
    return t


def _ensure_t2va_headers(text: str) -> str:
    """Ensure canonical 3-field T2VA section headers exist on their own lines."""
    t = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not t:
        return t
    if "integrated_multimodal_description:" not in t and "detailed_description:" in t:
        t = re.sub(r"(?m)^detailed_description:", "integrated_multimodal_description:", t, count=1)
    all_hdrs = ("integrated_multimodal_description:", "overall_soundscape:", "non_diegetic_music:")
    for hdr in all_hdrs:
        t = re.sub(rf"(?mi)([^\n])[ \t]+({re.escape(hdr)})", lambda m, h=hdr: f"{m.group(1)}\n\n{h}", t)
        t = re.sub(rf"(?mi)^({re.escape(hdr)})[ \t]+([^\n]+)", lambda m, h=hdr: f"{h}\n{m.group(2).strip()}", t)
        t = re.sub(rf"(?mi)^{re.escape(hdr)}(?=[ \t]*(?:\n|$))", hdr, t)
    if "integrated_multimodal_description:" not in t:
        m_shot = re.search(r"(?m)^\[\s*Shot\s+1\s*\]", t)
        pos = m_shot.start() if m_shot else 0
        t = (t[:pos].rstrip() + "\n\nintegrated_multimodal_description:\n" + t[pos:].lstrip()).strip()
    if "overall_soundscape:" not in t:
        t = re.sub(r"(?m)^non_diegetic_music:", "overall_soundscape:\nNatural room tone.\n\nnon_diegetic_music:", t, count=1)
        if "overall_soundscape:" not in t:
            t = t.rstrip() + "\n\noverall_soundscape:\nNatural room tone."
    if "non_diegetic_music:" not in t:
        t = t.rstrip() + "\n\nnon_diegetic_music:\nN/A"
    return t


def finish_block(
    raw_block: str,
    *,
    mode: str,
    lab: dict,
    duration_s: float,
    silent: bool = False,
    anal_nude: bool = False,
    brief: str = "",
    flavors: dict | None = None,
) -> str:
    """Deterministic post-write cleanup so the block passes `standard.contract_errors` & H3 community laws."""
    flavors = flavors or {}
    t = str(raw_block or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not t:
        return t
    t = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", t.strip())
    t = _clean_outside_d(t, lambda s: re.sub(r"\*\*(.+?)\*\*", r"\1", s))
    t = _clean_outside_d(t, lambda s: _CJK_OUTSIDE.sub("", s))
    t = _clean_outside_d(t, lambda s: _EMOJI_STRIP_RX.sub("", s))
    t = _clean_outside_d(t, lambda s: _UI_WARDROBE_LABEL_RX.sub("", s))
    t = _clean_outside_d(t, lambda s: _UI_STATE_LABEL_RX.sub(r"\1", s))
    t = _clean_outside_d(t, lambda s: _META_SCAFFOLD_RX.sub("", s))

    fields = _std.REF2VA_FIELDS if mode == "Ref2VA" else _std.T2VA_FIELDS
    first_pos = t.find(fields[0])
    if first_pos > 0:
        t = t[first_pos:]
    if mode == "Ref2VA":
        t = _ensure_ref2va_headers(t)
    else:
        t = _ensure_t2va_headers(t)

    if silent:
        t = _strip_all_dialogue(t)
    else:
        t = re.sub(r"\n+[ \t]*(\(DIALOGUE\))", r" \1", t)

    t = _BEAT_RUNIN.sub(r"\1\n\2", t)
    t = _HDR_RUNIN.sub(r"\1\n\2", t)

    desc_field = "detailed_description:" if mode == "Ref2VA" else "integrated_multimodal_description:"
    raw_desc_body = _std._field(t, desc_field)
    if raw_desc_body:
        raw_desc_body = _restore_missing_shot_cut_headers(raw_desc_body)
        if not re.search(r"\[\s*Shot\s+1\s*\]", raw_desc_body, re.I):
            raw_desc_body = "[Shot 1] " + raw_desc_body.lstrip()
        norm_desc_body = _normalize_multishot_timeline(raw_desc_body, duration_s)
        if not bool(flavors.get("time_tied", flavors.get("fast_engine", True))) and not re.search(r"\[\s*Shot\s+[2-9]\d*\s*\]", norm_desc_body, flags=re.I):
            body_lines = [ln.strip() for ln in norm_desc_body.strip().splitlines() if ln.strip()]
            shot1_lines = []
            flow_sents = []
            for ln in body_lines:
                if re.match(r"^\[\s*Shot\s+1\s*\]", ln, flags=re.I):
                    shot1_lines.append(ln)
                else:
                    cleaned_ln = re.sub(
                        rf"^At[ \t]+{_TIME_PAT}[ \t]*(?:[-\u2013\u2014]|to)[ \t]*{_TIME_PAT}\s*,\s*",
                        "",
                        ln,
                        flags=re.I,
                    ).strip()
                    if cleaned_ln:
                        flow_sents.append(cleaned_ln[0].upper() + cleaned_ln[1:])
            if shot1_lines and flow_sents:
                norm_desc_body = "\n".join(shot1_lines) + "\n\n" + " ".join(flow_sents)
        t = _replace_section_body(t, desc_field, norm_desc_body, ("overall_soundscape:", "non_diegetic_music:"))

    # Replace @tags with proper <Picture N> / <Subject N> / <Audio N>
    tag_map = {}
    for p in lab.get("pictures") or []:
        if p.get("tag"):
            tag_map[p["tag"].lower()] = f"<Subject {p['subject']}>" if p.get("subject") is not None else p["label"]
    for a in lab.get("audios") or []:
        if a.get("tag"):
            tag_map[a["tag"].lower()] = a["label"]
    if tag_map:
        def _rep_at(m):
            k = m.group(1).lower()
            return tag_map.get(k, m.group(1))
        t = _clean_outside_d(t, lambda s: re.sub(r"(?<![\w<])@(\w+)", _rep_at, s))

    # In T2VA, replace any stray <Subject N> / <Picture N> / <Audio N> tags cleanly
    if mode == "T2VA":
        t = _clean_outside_d(t, lambda s: re.sub(r"<Subject\s+1>'s\b", "the lead's", s))
        t = _clean_outside_d(t, lambda s: re.sub(r"<Subject\s+1>", "the lead", s))
        t = _clean_outside_d(t, lambda s: re.sub(r"<Subject\s+[2-9]>'s\b", "the other person's", s))
        t = _clean_outside_d(t, lambda s: re.sub(r"<Subject\s+[2-9]>", "the other person", s))
        t = _clean_outside_d(t, lambda s: re.sub(r"\s*<(?:Picture|Audio|Video)\s+\d+>", "", s))

    # Bind bare character names in Ref2VA (and fix any nested `<Subject N> (<Subject N> Name)` artifacts)
    if mode == "Ref2VA":
        for s_n, s_meta in sorted((lab.get("subjects") or {}).items()):
            cname = str(s_meta.get("char_name") or "").strip()
            if cname and len(cname) >= 3:
                t = _clean_outside_d(
                    t,
                    lambda s, sn=s_n, cn=cname: re.sub(
                        rf"<Subject\s+{sn}>\s*\(\s*(?:<Subject\s+{sn}>\s+)?({re.escape(cn)})\s*\)",
                        rf"<Subject {sn}> \1",
                        s,
                    ),
                )
                pat_cname = re.compile(rf"(?<!<Subject {s_n}> )(?<!<Subject \d> )(?<!<Subject \d> \()\b({re.escape(cname)})\b")
                for fld in ("summary:", "detailed_description:"):
                    f_val = _std._field(t, fld)
                    if f_val and pat_cname.search(f_val):
                        f_new = _clean_outside_d(f_val, lambda s, rx=pat_cname, sn=s_n: rx.sub(rf"<Subject {sn}> \1", s))
                        next_fld = "retention_analysis:" if fld == "summary:" else "overall_soundscape:"
                        t = re.sub(
                            rf"({re.escape(fld)}[ \t]*\n)(.*?)(?=\n{re.escape(next_fld)})",
                            lambda m, fn=f_new: m.group(1) + fn.strip() + "\n\n",
                            t,
                            count=1,
                            flags=re.S,
                        )

    def _strip_neg(s: str) -> str:
        out = s
        for rx, repl in _NEG_REPLACEMENTS:
            out = rx.sub(repl, out)
        return out

    t = re.sub(r"(<d>\[[^\]]+\][^<\n]+?)(?=\.\s*$|\s*$)", r"\1</d>", t, flags=re.M)
    t = _clean_outside_d(t, _strip_neg)
    t = _clean_outside_d(t, lambda s: re.sub(r"[ \t]+([.,;!?])", r"\1", s))
    if not silent:
        t = _clean_inside_d(t)

    plan_hint = str(flavors.get("plan_hint") or "")
    if not _dir.is_anal(brief, explicit_id=str(flavors.get("explicit") or ""), plan=plan_hint):
        t = re.sub(r"[ \t]*The head of his erect penis is inside her anus\.", "", t, flags=re.I)
        t = re.sub(r"[ \t]*The anal ring is stretched tautly around the shaft and stays closed around it\.", "", t, flags=re.I)
        t = re.sub(r"[ \t]*Her pussy stays visible and stays empty[^.\n]*\.", "", t, flags=re.I)
        t = re.sub(r"[ \t]*The head stays buried\.", "", t, flags=re.I)

    def _upgrade_shaft_stroke(s: str) -> str:
        s = re.sub(
            r"\b(rapidly\s+|slowly\s+|quickly\s+)?stroking\s+((?:his|the|their|each|both)\s+(?:(?:glistening|wet|oiled|erect|throbbing|veined|lubed|exposed|thick|naked)\s+)*(?:shafts?|cocks?|penis(?:es)?|barrels?))\b(?!\s+(?:up\s+and\s+down|back\s+and\s+forth|along|from\s+(?:the\s+)?(?:base|root)))",
            r"tightly gripping and moving \1up and down along the full length of \2 from base to tip",
            s,
            flags=re.I,
        )
        s = re.sub(
            r"\b(rapidly\s+|slowly\s+|quickly\s+)?strokes\s+((?:his|the|each)\s+(?:(?:glistening|wet|oiled|erect|throbbing|veined|lubed|exposed|thick|naked)\s+)*(?:shaft|cock|penis|barrel))\b(?!\s+(?:up\s+and\s+down|back\s+and\s+forth|along|from\s+(?:the\s+)?(?:base|root)))",
            r"tightly grips and slides \1up and down along the full length of \2 from base to tip",
            s,
            flags=re.I,
        )
        return s

    t = _clean_outside_d(t, _upgrade_shaft_stroke)

    # Scrub leaked directive jargon & sexual euphemisms when explicit/NSFW is active
    exp_fin_str = str(flavors.get("explicit") or "")
    ward_fin_str = str(flavors.get("wardrobe") or "")
    fet_fin_str = str(flavors.get("fetish") or "")
    is_sex_fin = _dir.is_sexual(brief, exp_fin_str, ward_fin_str, fetish_id=fet_fin_str)
    if is_sex_fin:
        is_les_or_peg = bool(
            _dir.is_pegging_scene(brief, explicit_id=exp_fin_str, plan=plan_hint)
            or re.search(r"\b(?:lesbian|fff|cunnilingus|strap[- ]?on)\b", f"{exp_fin_str} {brief}", re.I)
        )

        def _de_euphemize_sex(s: str) -> str:
            if not is_les_or_peg:
                s = re.sub(
                    r"\b(?:her|their|the)\s+partner'?s\s+(?:(thick|hard|vertical|oiled|wet|glistening|throbbing|swollen)\s+)?(?:erect\s+)?(?:shaft|member|manhood)\b",
                    lambda m: f"his {m.group(1) + ' ' if m.group(1) else ''}erect cock",
                    s,
                    flags=re.I,
                )
                s = re.sub(r"\bher\s+partner'?s\b", "the man's", s, flags=re.I)
                s = re.sub(r"\bher\s+partner\b", "the man", s, flags=re.I)
            s = re.sub(r",?\s*\b(?:creating|maintaining)\s+(?:a\s+)?(?:smooth\s+)?(?:continuous\s+)?rhythmic\s+motion\s+along\s+the\s+(?:active|locked)\s+pose\s+axis\b", " in steady rhythmic thrusts", s, flags=re.I)
            s = re.sub(r"\balong\s+the\s+(?:active|locked)\s+pose\s+axis\b", "with steady depth", s, flags=re.I)
            s = re.sub(r"\bperforms?\s+an\s+intimate\s+adult\s+encounter\b", "has explicit sex", s, flags=re.I)
            s = re.sub(r"\ban\s+intimate\s+adult\s+encounter\b", "explicit sex", s, flags=re.I)
            s = re.sub(r"\bvivid\s+erotic\s+intensity\b", "flushed breathless pleasure", s, flags=re.I)
            return s

        t = _clean_outside_d(t, _de_euphemize_sex)

    # Strip third-person narrator self-references when POV active
    pov_mode_fin = _dir.resolve_pov_mode(brief, flavors=flavors)
    if pov_mode_fin in ("male", "female", "on"):
        def _clean_pov(s: str) -> str:
            s = re.sub(r"\b(?:first[- ]person\s+(?:male|female)\s+)?(?:POV|cameraman|viewer)'?s?\s+(?:my|mine)\b", "my", s, flags=re.I)
            s = re.sub(r"\b(?:the\s+(?:camera|viewer|cameraman|unseen\s+partner|POV\s+male))\s+holds?\s+(?:his|her|their)\s+", "my hands grip ", s, flags=re.I)
            return s
        t = _clean_outside_d(t, _clean_pov)

    # Ref2VA header synchronization
    if mode == "Ref2VA":
        has_aud = bool(lab.get("audios"))
        default_tag = "[reference generation + audio reference]" if has_aud else "[reference generation]"
        summ = (_std._field(t, "summary:") or "").strip()
        if not summ:
            sub_keys = sorted((lab.get("subjects") or {}).keys())
            sub_hint = ", ".join(f"<Subject {sn}>" for sn in sub_keys) if sub_keys else ""
            brief_clean_s = sanitize_additive_rule(brief or "").strip() or "Staged scene."
            summ = f"{default_tag} {sub_hint + ' ' if sub_hint else ''}{brief_clean_s}".strip()
        else:
            if not has_aud:
                summ = re.sub(r"\s*\+\s*audio\s+(?:reference|reuse)", "", summ, flags=re.I)
            for s_n in sorted((lab.get("subjects") or {}).keys()):
                owned = [p["label"] for p in (lab.get("pictures") or []) if p.get("subject") == s_n]
                if owned:
                    summ = re.sub(rf"(<Subject {s_n}>[^.;\n]*?\bfrom\s+)<Picture\s+\d+>", lambda m, ow=owned[0]: f"{m.group(1)}{ow}", summ, flags=re.I)
            if not re.match(r"\s*\[[^\]]+\]", summ):
                summ = default_tag + " " + summ.lstrip()
        t = _replace_section_body(t, "summary:", summ, ("retention_analysis:", "detailed_description:", "overall_soundscape:"))

        def _sort_ref_lines(lines_list: list[str]) -> list[str]:
            def _key(ln: str):
                ms = re.match(r"^\s*<Subject\s+(\d+)>", ln)
                if ms:
                    return (0, int(ms.group(1)))
                mp = re.match(r"^\s*<Picture\s+(\d+)>", ln)
                if mp:
                    return (1, int(mp.group(1)))
                ma = re.match(r"^\s*<Audio\s+(\d+)>", ln)
                if ma:
                    return (2, int(ma.group(1)))
                return (3, 0)
            return sorted([x for x in lines_list if x.strip()], key=_key)

        subj_pic_nums = {p["n"] for p in (lab.get("pictures") or []) if p.get("subject") is not None}
        desc_body_ret = _std._field(t, "detailed_description:") or ""
        shot_chunks_ret = list(re.finditer(r"\[\s*Shot\s+(\d+)\s*\]", desc_body_ret, re.I))
        shot_spans_ret = [
            (
                int(m.group(1)),
                desc_body_ret[m.start():(shot_chunks_ret[idx + 1].start() if idx + 1 < len(shot_chunks_ret) else len(desc_body_ret))],
            )
            for idx, m in enumerate(shot_chunks_ret)
        ]

        def _shots_for_subject(sn_val: int) -> str:
            hits = [f"[Shot {k}]" for k, ch in shot_spans_ret if re.search(rf"<Subject\s+{sn_val}>", ch)]
            return ", ".join(hits) if hits else "[Shot 1]"

        ret = _std._field(t, "retention_analysis:")
        if ret:
            ret_lines = []
            for rl in ret.splitlines():
                mp = re.match(r"^\s*<Picture\s+(\d+)>", rl)
                if mp and (int(mp.group(1)) in subj_pic_nums or _refs.is_studio_backdrop_text(rl)):
                    continue
                ms = re.match(r"^\s*<Subject\s+(\d+)>", rl)
                if ms:
                    if not re.search(r"\b(?:fully_preserved|partially_preserved)\b", rl):
                        continue
                    owned = [p["label"] for p in (lab.get("pictures") or []) if p.get("subject") == int(ms.group(1))]
                    if owned:
                        rl = re.sub(r"<Picture\s+\d+>", owned[0], rl)
                ret_lines.append(rl)
            ret = "\n".join(ret_lines).strip()

        ward_ids_fin = _cat.parse_multi_ids(flavors.get("wardrobe"))
        wmode_fin = _bg.get_dial_mode(flavors, "wardrobe", "sequence")
        sex_scene_fin = _dir.is_sexual(brief, str(flavors.get("explicit") or ""), str(flavors.get("wardrobe") or ""))
        missing_ret = []
        for s_n in sorted((lab.get("subjects") or {}).keys()):
            s_meta = (lab.get("subjects") or {}).get(s_n) or {}
            cname = s_meta.get("char_name") or s_meta.get("name") or ""
            cname_str = f" {cname}" if cname else ""
            s_pics = [p for p in (lab.get("pictures") or []) if p.get("subject") == s_n]
            pic_cite = f" from {', '.join(p['label'] for p in s_pics)}" if s_pics else ""
            eth_s = next((_refs.extract_ethnicity_phrase(sp.get("desc") or "", brief=brief) for sp in s_pics if _refs.extract_ethnicity_phrase(sp.get("desc") or "", brief=brief)), "")
            eth_note = f" ({eth_s})" if eth_s else ""
            all_nude_fin = bool({"nude_both_partners", "nude_all_cast_subjects_s1_s9"} & set(ward_ids_fin))
            split_assigned = bool(wmode_fin == "split" and len(ward_ids_fin) >= s_n)
            use_partial = bool((anal_nude and s_n in (1, 2)) or (ward_ids_fin and (s_n == 1 or all_nude_fin or split_assigned)) or (sex_scene_fin and s_n == 2))
            if not re.search(rf"^\s*<Subject {s_n}>[^\n]*\b(?:fully_preserved|partially_preserved)\b", ret, re.M):
                pres = (
                    f"partially_preserved -{cname_str} keeping facial bone structure{eth_note}, hair, and body identity{pic_cite} while completely nude from Frame 0"
                    if (anal_nude and s_n == 1)
                    else (
                        f"partially_preserved -{cname_str} keeping facial bone structure{eth_note}, hair, and body identity{pic_cite} with the active scene wardrobe state"
                        if use_partial
                        else f"fully_preserved -{cname_str} keeping facial bone structure{eth_note}, hair, and outfit identity{pic_cite}"
                    )
                )
                missing_ret.append(f"<Subject {s_n}> (appears in {_shots_for_subject(s_n)}): {pres}")
        for p in lab.get("pictures") or []:
            if p.get("subject") is None and not _refs.is_studio_backdrop_text(p.get("desc") or "") and not re.search(rf"^\s*<Picture {p['n']}>", ret, re.M):
                missing_ret.append(f"<Picture {p['n']}> ([Shot 1] setting): fully_preserved - {p.get('desc') or 'scene environment'}")
        snd_now_ret = (_std._field(t, "overall_soundscape:") or "").strip().upper()
        mus_now_ret = (_std._field(t, "non_diegetic_music:") or "").strip().upper()
        pure_bgm_fin = is_pure_bgm_soundscape(brief=brief, flavors=flavors) or (snd_now_ret == "N/A" and mus_now_ret not in ("", "N/A"))
        quiet_voice_fin = (silent or ("<d>" not in desc_body_ret)) and pure_bgm_fin
        def _is_voice_audio_ref(a_meta: dict) -> bool:
            if a_meta.get("subject") is not None:
                return True
            blob_a = f"{a_meta.get('file') or ''} {a_meta.get('desc') or ''}"
            return not bool(re.search(r"\b(?:bgm|music|song|track|beat|instrumental|score|soundtrack|sfx)\b", blob_a, re.I))

        if quiet_voice_fin and ret:
            for a in lab.get("audios") or []:
                if _is_voice_audio_ref(a):
                    ret = re.sub(
                        rf"(^\s*<Audio {a['n']}>\s*:\s*)full_reference\b[^\n]*",
                        r"\1timbre_reference (quiet during music-only dance)",
                        ret,
                        flags=re.M,
                    )
        for a in lab.get("audios") or []:
            if not re.search(rf"^\s*<Audio {a['n']}>", ret, re.M):
                if quiet_voice_fin and _is_voice_audio_ref(a):
                    missing_ret.append(f"<Audio {a['n']}>: timbre_reference (quiet during music-only dance)")
                else:
                    missing_ret.append(f"<Audio {a['n']}>: full_reference")
        new_ret = "\n".join(_sort_ref_lines((ret.splitlines() if ret else []) + missing_ret)).strip()
        if new_ret:
            t = _replace_section_body(t, "retention_analysis:", new_ret, ("detailed_description:", "overall_soundscape:"))
        if anal_nude or ward_ids_fin:
            t = re.sub(r"(<Subject 1>[^\n:]*:\s*)fully_preserved", r"\1partially_preserved", t, count=1)
        if anal_nude or "nude_both_partners" in ward_ids_fin or "nude_all_cast_subjects_s1_s9" in ward_ids_fin or sex_scene_fin or (len(ward_ids_fin) >= 2 and wmode_fin == "split"):
            t = re.sub(r"(<Subject 2>[^\n:]*:\s*)fully_preserved", r"\1partially_preserved", t, count=1)
        if "nude_all_cast_subjects_s1_s9" in ward_ids_fin or wmode_fin == "split":
            for s_n_idx in range(3, len(ward_ids_fin) + 1 if wmode_fin == "split" else 10):
                t = re.sub(rf"(<Subject {s_n_idx}>[^\n:]*:\s*)fully_preserved", r"\1partially_preserved", t, count=1)

        sdefs = _std._field(t, "subject_definitions:")
        if sdefs:
            sdef_lines = []
            for sl in sdefs.splitlines():
                mp = re.match(r"^\s*<Picture\s+(\d+)>\s*(?::|\()", sl)
                if mp and (int(mp.group(1)) in subj_pic_nums or _refs.is_studio_backdrop_text(sl)):
                    continue
                ms = re.match(r"^\s*<Subject\s+(\d+)>", sl)
                if ms:
                    owned = [p["label"] for p in (lab.get("pictures") or []) if p.get("subject") == int(ms.group(1))]
                    if owned:
                        sl = re.sub(r"<Picture\s+\d+>", owned[0], sl)
                    sl = _refs._STUDIO_BACKDROP_RX.sub(" ", sl)
                    sl = re.sub(r"\(\s*Anchor\s*:\s*", "(", sl, flags=re.I)
                    sl = re.sub(r"\s{2,}", " ", sl).strip()
                sdef_lines.append(sl)
            sdefs = "\n".join(sdef_lines).strip()

        missing_defs = []
        for s_n, s_meta in sorted((lab.get("subjects") or {}).items()):
            pics_for_s = [p for p in (lab.get("pictures") or []) if p.get("subject") == s_n]
            pic_labels = [p["label"] for p in pics_for_s]
            s_desc = next((str(p.get("desc") or "").strip() for p in pics_for_s if p.get("desc")), "")
            s_desc = re.sub(r"^\s*Anchor\s*:\s*", "", s_desc, flags=re.I).strip()
            eth_s = _refs.extract_ethnicity_phrase(s_desc, brief=brief)
            cname = s_meta.get("char_name") or s_meta.get("name") or ""
            cname_str = f" {cname}," if cname else ""
            has_sub_line = bool(re.search(rf"^\s*<Subject {s_n}>", sdefs, re.M))
            missing_pics = [pl for pl in pic_labels if pl not in sdefs]
            if not has_sub_line or missing_pics:
                p_join = ", ".join(pic_labels) if pic_labels else "the reference"
                who_phrase = f"the {eth_s}" if eth_s else "the person"
                desc_tail = f" ({s_desc})" if s_desc else ""
                line_def = f"<Subject {s_n}> is{cname_str} {who_phrase} in {p_join}{desc_tail}."
                if has_sub_line:
                    sdefs = re.sub(rf"^\s*<Subject {s_n}>[^\n]*$", lambda _m, ld=line_def: ld, sdefs, count=1, flags=re.M)
                else:
                    missing_defs.append(line_def)
            elif eth_s:
                m_sl = re.search(rf"^(\s*<Subject {s_n}>[^\n]*)$", sdefs, flags=re.M)
                if m_sl and not _refs._ETHNICITY_RX.search(m_sl.group(1)):
                    old_l = m_sl.group(1)
                    new_l = re.sub(
                        rf"(<Subject {s_n}>[^\n]*?\bis\s+(?:{re.escape(cname)}\s*,\s*)?)(?:the\s+|a\s+)?(?:young\s+|tall\s+)?(?:woman|man|girl|person)\b",
                        lambda m, e=eth_s: f"{m.group(1)}the {e}",
                        old_l,
                        count=1,
                        flags=re.I,
                    )
                    if new_l == old_l:
                        new_l = re.sub(rf"(<Subject {s_n}>[^\n.]*)", lambda m, e=eth_s: f"{m.group(1)}, an {e}", old_l, count=1)
                    sdefs = sdefs.replace(old_l, new_l, 1)
        for p in lab.get("pictures") or []:
            if p.get("subject") is None and not _refs.is_studio_backdrop_text(p.get("desc") or "") and p["label"] not in sdefs:
                missing_defs.append(f"{p['label']} is the scene setting ({p.get('desc') or 'the scene environment reference'}).")
        for a in lab.get("audios") or []:
            if a["label"] not in sdefs:
                missing_defs.append(f"{a['label']} is the audio reference.")
        new_defs = "\n".join(_sort_ref_lines((sdefs.splitlines() if sdefs else []) + missing_defs)).strip()
        if new_defs:
            t = _replace_section_body(t, "subject_definitions:", new_defs, ("summary:", "retention_analysis:", "detailed_description:"))

    # Scrub studio void leaks unless studio requested
    place_opts_fin = _cat.resolve_dial_opts("place", flavors.get("place"))
    place_opt_fin = place_opts_fin[0] if place_opts_fin else None
    place_id_fin = place_opt_fin["id"] if place_opt_fin else ""
    if not re.search(r"\b(?:photo\s+studio|cyclorama|studio\s+backdrop|studio\s+void)\b", f"{brief or ''} {place_id_fin}", re.I):
        p_label_clean = (place_opt_fin.get("character") or place_opt_fin.get("label") or "").split("·")[0].strip().lower() if place_opt_fin else ""
        p_rule_clean = sanitize_additive_rule(place_opt_fin.get("rule") or "") if place_opt_fin else ""
        in_place_repl = f"inside the {p_label_clean} ({p_rule_clean})" if (p_label_clean and p_rule_clean) else ("inside the room" if not p_label_clean else f"inside the {p_label_clean}")
        short_place_repl = f"in the {p_label_clean}" if p_label_clean else "in the room"
        t = re.sub(r"\bwithin\s+the\s+(?:stark\s+|minimalist\s+|high[- ]contrast\s+)*studio\s+void\s+where\s+<Picture\s+\d+>'?s\s+[^.\n]+(?:floor\s+plane|backdrop|environment)", in_place_repl, t, flags=re.I)
        t = re.sub(r"\b(?:in|within|inside)\s+the\s+(?:stark,\s+|high[- ]contrast\s+|silent\s+|minimalist\s+|dark\s+)*(?:studio\s+void|silent\s+void|dark\s+void)\b", short_place_repl, t, flags=re.I)
        t = re.sub(r"\bagainst\s+the\s+invisible\s+floor(?:\s+surface)?\b", "against the floor", t, flags=re.I)

    # Ensure Place dial appears in [Shot 1]
    if place_opt_fin and place_opt_fin.get("rule"):
        p_name_fin = (place_opt_fin.get("character") or place_opt_fin.get("label") or "").split("·")[0].strip()
        p_rule_fin = sanitize_additive_rule(place_opt_fin["rule"])
        cur_desc = _std._field(t, desc_field)
        if cur_desc:
            m_s1_line = re.search(r"(\[Shot 1\][ \t]*[^\n]+)", cur_desc)
            if m_s1_line:
                s1_line = m_s1_line.group(1)
                key_words = [w.lower() for w in re.findall(r"[A-Za-z]{4,}", f"{p_name_fin} {p_rule_fin}") if w.lower() not in ("room", "with", "from", "that", "this", "high", "small", "wall", "walls", "floor", "dark", "warm", "soft")]
                if key_words and not any(kw in cur_desc.lower() for kw in key_words[:5]):
                    light_opts_fin = _cat.resolve_dial_opts("cinema", flavors.get("light"))
                    light_opt_fin = light_opts_fin[0] if light_opts_fin else None
                    light_clause = f" under {sanitize_additive_rule(light_opt_fin['rule'])}" if (light_opt_fin and light_opt_fin.get("rule")) else ""
                    new_s1_line = re.sub(r"^(\[Shot 1\][ \t]*)", lambda m: f"{m.group(1)}Inside {p_name_fin.lower()} ({p_rule_fin}){light_clause}: ", s1_line, count=1)
                    cur_desc = cur_desc.replace(s1_line, new_s1_line, 1)
                    t = _replace_section_body(t, desc_field, cur_desc, ("overall_soundscape:", "non_diegetic_music:"))

    # Enforce ambience & music (with commas, zero semicolons!)
    amb_opts_fin = [o for o in _cat.resolve_dial_opts("ambience", flavors.get("ambience")) if o.get("id") not in ("none", "amb_none_na") and (o.get("rule") or o.get("world"))]
    if is_pure_bgm_soundscape(brief=brief, flavors=flavors):
        if "overall_soundscape:" in t:
            t = _replace_section_body(t, "overall_soundscape:", "N/A", ("non_diegetic_music:",))
    elif amb_opts_fin:
        cur_snd = (_std._field(t, "overall_soundscape:") or "").strip()
        if not cur_snd or len(cur_snd) < 20 or cur_snd.lower() in ("n/a", "room tone.", "natural room tone.", "steady room tone."):
            amb_text = ", ".join(sanitize_additive_rule((o.get("rule") or o.get("world") or "").strip()) for o in amb_opts_fin)
            if amb_text and "overall_soundscape:" in t:
                t = _replace_section_body(t, "overall_soundscape:", amb_text.rstrip(".") + ".", ("non_diegetic_music:",))

    raw_music_fin = _cat.parse_multi_ids(flavors.get("music"))
    music_opts_fin = _cat.resolve_dial_opts("music", flavors.get("music"))
    if str(flavors.get("music") or "").strip().lower() == "none" or "none" in raw_music_fin:
        t = re.sub(r"(non_diegetic_music:[ \t]*\r?\n?).*$", r"\1N/A", t, count=1, flags=re.S)
    elif len(music_opts_fin) == 1:
        m_opt = music_opts_fin[0]
        m_rule = (m_opt.get("rule") or m_opt.get("world") or "").strip() if m_opt else ""
        if m_rule:
            t = re.sub(r"(non_diegetic_music:[ \t]*\r?\n?).*$", lambda m: m.group(1) + sanitize_additive_rule(m_rule), t, count=1, flags=re.S)
    elif len(music_opts_fin) >= 2:
        m_rules = [sanitize_additive_rule((o.get("rule") or o.get("world") or "").strip()) for o in music_opts_fin if (o.get("rule") or o.get("world"))]
        if m_rules:
            t = re.sub(r"(non_diegetic_music:[ \t]*\r?\n?).*$", lambda m: m.group(1) + " ".join(m_rules), t, count=1, flags=re.S)

    t = _sanitize_audio_sections(t, silent=silent)
    return t.strip()


def format_h3_output(block: str, *, output_format: str = "h3_auto", duration_s: float = 10.0) -> str:
    """Format finished prompt block for standalone H3 node output formats (I2VA / FL2VA / L2VA / Beats / Keyframe)."""
    fmt = str(output_format or "h3_auto").strip().lower()
    t = str(block or "").strip()
    if not t:
        return t
    # Idempotently strip any prior I2VA / FL2VA / L2VA alignment header before formatting
    t = re.sub(
        r"^(?:For the target video, at 0\.00 seconds[^\n]*|How the reference pictures align[^\n]*)\s*\n+",
        "",
        t,
        flags=re.I,
    ).strip()
    if fmt == "h3_auto":
        return t
    if fmt == "h3_beats":
        desc_fld = "detailed_description:" if "detailed_description:" in t else ("integrated_multimodal_description:" if "integrated_multimodal_description:" in t else "")
        return (_std._field(t, desc_fld) or t).strip() if desc_fld else t
    if fmt == "h3_keyframe":
        desc_fld = "detailed_description:" if "detailed_description:" in t else ("integrated_multimodal_description:" if "integrated_multimodal_description:" in t else "")
        if not desc_fld:
            return t
        raw_desc = (_std._field(t, desc_fld) or "").strip()
        raw_desc = re.sub(r"\[Shot\s*\d+\]\s*(?:At\s+\d+:\d+(?:\.\d+)?[^,]*,\s*)?", "", raw_desc, flags=re.I)
        raw_desc = re.sub(r"\bAt\s+\d+:\d+(?:\.\d+)?(?:\s*-\s*\d+:\d+(?:\.\d+)?)?,?\s*", "", raw_desc, flags=re.I)
        raw_desc = re.sub(r"<d>.*?</d>", "", raw_desc, flags=re.I | re.S)
        return re.sub(r"\s+", " ", raw_desc).strip() or t
    dur = float(duration_s or 10.0)
    # Strip Ref2VA headers if targeting I2VA / FL2VA / L2VA base keyframe modes
    body = t
    if "integrated_multimodal_description:" not in body and "detailed_description:" in body:
        desc = _std._field(body, "detailed_description:")
        snd = _std._field(body, "overall_soundscape:") or "Natural room tone."
        mus = _std._field(body, "non_diegetic_music:") or "N/A"
        body = f"integrated_multimodal_description:\n{desc.strip()}\n\noverall_soundscape:\n{snd.strip()}\n\nnon_diegetic_music:\n{mus.strip()}"
    if fmt == "h3_i2va":
        hdr = "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."
        return f"{hdr}\n\n{body}"
    if fmt == "h3_fl2va":
        hdr = f"How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot 1) aligns with the {dur:.2f}-second mark of the target video."
        return f"{hdr}\n\n{body}"
    if fmt == "h3_l2va":
        hdr = f"How the reference pictures align with the target video — <Picture 1> (from [Shot 1]) aligns with the {dur:.2f}-second mark of the target video."
        return f"{hdr}\n\n{body}"
    return t


def adapt_preset_script(
    script_text: str,
    *,
    ref_plan: str = "",
    duration_s: float = 10.0,
    voice_files: tuple | list = (),
    flavors: dict | None = None,
    brief: str = "",
) -> dict:
    raw = str(script_text or "").strip()
    if not raw:
        return {"ok": False, "error": "Empty script text"}
    flavors = dict(flavors or {})
    try:
        lab = _refs.sandtie_labels(ref_plan, voice_files=voice_files)
    except Exception:
        lab = {"pictures": [], "audios": [], "videos": [], "subjects": {}}

    for p in lab.get("pictures") or []:
        if p.get("subject") is None and _refs.is_likely_person_ref(p, brief=brief, flavors=flavors):
            existing_subs = sorted((lab.get("subjects") or {}).keys())
            next_s = 1 if 1 not in existing_subs else (existing_subs[-1] + 1)
            p["subject"] = next_s
            p["retention"] = "fully_preserved"
            cname = _refs.extract_char_name_from_tag(p.get("tag") or "")
            lab.setdefault("subjects", {})[next_s] = {
                "name": cname, "char_name": cname, "box_name": "",
                "locked": "", "context": "", "pictures": [p["label"]], "audios": [],
            }
    updated_ref_plan = _refs.sync_promoted_ref_plan(ref_plan, lab)
    mode = _std.mode_for(lab)

    old_names_by_s: dict[int, set[str]] = {}
    for m_sn in re.finditer(r"<Subject\s+(\d+)>(?:\s+is)?\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", raw):
        s_i = int(m_sn.group(1))
        cand_n = m_sn.group(2).strip()
        if cand_n.lower() not in ("is", "appears", "and", "or", "with", "in", "on", "at"):
            old_names_by_s.setdefault(s_i, set()).add(cand_n)

    adapted = _ensure_ref2va_headers(raw) if mode == "Ref2VA" else raw
    wired_subs = lab.get("subjects") or {}
    wired_pics = {p["n"] for p in (lab.get("pictures") or [])}
    wired_auds = {a["n"] for a in (lab.get("audios") or [])}
    for m_au in sorted({int(x) for x in re.findall(r"<Audio\s+(\d+)>", adapted)}, reverse=True):
        if m_au not in wired_auds:
            adapted = re.sub(rf"[ \t]*\busing\s+(?:the\s+)?(?:voice\s+timbre|timbre|audio)\s+(?:from|in)\s+<Audio\s+{m_au}>", "", adapted, flags=re.I)
            adapted = re.sub(rf"(?m)^\s*<Audio\s+{m_au}>[^\n]*\n?", "", adapted)
            adapted = re.sub(rf"[ \t]*<Audio\s+{m_au}>", "", adapted)
    if mode == "Ref2VA":
        ret_raw_a = _std._field(adapted, "retention_analysis:")
        if ret_raw_a:
            kept_ret_a = []
            for rl_a in ret_raw_a.splitlines():
                ms_a = re.match(r"^\s*<Subject\s+(\d+)>", rl_a)
                if ms_a and int(ms_a.group(1)) not in wired_subs:
                    continue
                mp_a = re.search(r"<Picture\s+(\d+)>", rl_a)
                if mp_a and int(mp_a.group(1)) not in wired_pics:
                    rl_a = re.sub(r"\s*(?:from|in)\s+<Picture\s+\d+>", "", rl_a)
                kept_ret_a.append(rl_a)
            adapted = _replace_section_body(adapted, "retention_analysis:", "\n".join(kept_ret_a), ("detailed_description:", "overall_soundscape:"))
    for s_i in sorted(set(old_names_by_s.keys()) | set(wired_subs.keys())):
        s_meta = wired_subs.get(s_i) or {}
        s_cname = str(s_meta.get("char_name") or s_meta.get("name") or "").strip()
        if s_i in wired_subs:
            repl = f"<Subject {s_i}> {s_cname}" if s_cname else f"<Subject {s_i}>"
            for old_n in sorted(old_names_by_s.get(s_i, ()), key=len, reverse=True):
                adapted = re.sub(rf"<Subject\s+{s_i}>\s+{re.escape(old_n)}\b", lambda _m, r=repl: r, adapted)
                if s_cname:
                    adapted = re.sub(
                        rf"(?m)^(<Subject\s+{s_i}>[^\n]*?\b(?:fully_preserved|partially_preserved)\s*-\s*){re.escape(old_n)}\b",
                        lambda m, cn=s_cname: f"{m.group(1)}{cn}",
                        adapted,
                    )
        elif mode == "Ref2VA" and s_i >= 2:
            fallback_noun = "her rival" if _dir.is_combat(raw) else "her partner"
            for old_n in sorted(old_names_by_s.get(s_i, ()), key=len, reverse=True):
                adapted = re.sub(rf"<Subject\s+{s_i}>\s+{re.escape(old_n)}\b", fallback_noun, adapted)
            adapted = re.sub(rf"<Subject\s+{s_i}>", fallback_noun, adapted)

    if mode == "Ref2VA":
        adapted = re.sub(r"(subject_definitions:[ \t]*\n)(.*?)(?=\nsummary:)", r"\1\n", adapted, count=1, flags=re.S)

    place_opts_a = _cat.resolve_dial_opts("place", flavors.get("place"))
    place_opt_a = place_opts_a[0] if place_opts_a else None
    setting_pics_a = [p for p in (lab.get("pictures") or []) if p.get("subject") is None and not _refs.is_studio_backdrop_text(p.get("desc") or "")]
    if place_opt_a and place_opt_a.get("rule"):
        p_name_a = (place_opt_a.get("character") or place_opt_a.get("label") or "").split("·")[0].strip()
        p_rule_a = sanitize_additive_rule(place_opt_a["rule"])
        adapted = re.sub(r"in a clean minimalist dance studio with a smooth dark floor and warm studio lighting", f"inside {p_name_a} ({p_rule_a})", adapted, flags=re.I)
    elif setting_pics_a:
        sp0 = setting_pics_a[0]
        if "in a clean minimalist dance studio with a smooth dark floor and warm studio lighting" in adapted.lower():
            adapted = re.sub(r"in a clean minimalist dance studio with a smooth dark floor and warm studio lighting", f"inside {sp0['label']} ({sp0.get('desc') or 'the referenced setting'})", adapted, flags=re.I)
        elif sp0["label"] not in (_std._field(adapted, "detailed_description:") or ""):
            adapted = re.sub(
                r"(\[Shot 1\][ \t]*)",
                lambda m, sp=sp0: f"{m.group(1)}Inside {sp['label']} ({sp.get('desc') or 'the referenced setting'}), ",
                adapted,
                count=1,
            )

    style_opts_a = _cat.resolve_dial_opts("style", flavors.get("style"))
    light_opts_a = _cat.resolve_dial_opts("cinema", flavors.get("light"))
    col_opts_a = _cat.resolve_dial_opts("colour", flavors.get("colour"))
    cam_opts_a = _cat.resolve_dial_opts("camera", flavors.get("camera"))
    cur_desc_fld = "detailed_description:" if "detailed_description:" in adapted else "integrated_multimodal_description:"
    cur_desc_val = _std._field(adapted, cur_desc_fld) or ""
    has_preset_cuts = bool(re.search(r"\[\s*Shot\s+2\s*\]", cur_desc_val, re.I))
    dial_prefix_bits = []
    for lst in ((style_opts_a, light_opts_a, col_opts_a) if has_preset_cuts else (style_opts_a, cam_opts_a, light_opts_a, col_opts_a)):
        if lst and lst[0].get("rule"):
            bit_clean = sanitize_additive_rule(lst[0]["rule"]).rstrip(" .,;")
            if bit_clean:
                dial_prefix_bits.append(bit_clean)
    if dial_prefix_bits and cur_desc_val and "[Shot 1]" in cur_desc_val:
        bits2 = dial_prefix_bits[:2]
        if len(bits2) == 2 and len(bits2[1]) >= 2 and bits2[1][0].isupper() and bits2[1][1].islower() and not re.match(r"^(?:Korean|Japanese|Chinese|Tokyo|Seoul|Douyin|TikTok|Hollywood|I\b)", bits2[1]):
            bits2[1] = bits2[1][0].lower() + bits2[1][1:]
        cue_str = ", ".join(bits2)
        if cue_str and cue_str[:24].lower() not in cur_desc_val.lower():
            new_desc_val = re.sub(r"(\[Shot 1\][ \t]*)", lambda m: f"{m.group(1)}{cue_str}, ", cur_desc_val, count=1)
            adapted = _replace_section_body(adapted, cur_desc_fld, new_desc_val, ("overall_soundscape:", "non_diegetic_music:"))

    if mode == "T2VA" and "detailed_description:" in adapted and "integrated_multimodal_description:" not in adapted:
        desc_b = _std._field(adapted, "detailed_description:")
        snd_b = _std._field(adapted, "overall_soundscape:") or "Natural room tone and physical movement foley."
        mus_b = _std._field(adapted, "non_diegetic_music:") or "N/A"
        char_opts_a = _cat.resolve_dial_opts("character", flavors.get("character"))
        t2va_who = char_opts_a[0]["label"].split("—")[0].strip() if char_opts_a else "The lead"
        desc_b = re.sub(r"<Subject\s+1>(?:\s+[A-Z][a-zA-Z]+)?", t2va_who, desc_b)
        desc_b = re.sub(r"<Subject\s+2>(?:\s+[A-Z][a-zA-Z]+)?", "her partner", desc_b)
        desc_b = re.sub(r"<Subject\s+[3-9]>(?:\s+[A-Z][a-zA-Z]+)?", "the companion", desc_b)
        desc_b = re.sub(r"<(?:Picture|Subject|Audio)\s+\d+>", "", desc_b)
        adapted = f"integrated_multimodal_description:\n{desc_b.strip()}\n\noverall_soundscape:\n{snd_b.strip()}\n\nnon_diegetic_music:\n{mus_b.strip()}"

    silent_a = _dlg.should_suppress_dialogue(brief, flavors=flavors)
    finished = finish_block(adapted, mode=mode, lab=lab, duration_s=duration_s, silent=silent_a, brief=brief, flavors=flavors)

    desc_fld = "detailed_description:" if mode == "Ref2VA" else "integrated_multimodal_description:"
    desc_val = _std._field(finished, desc_fld) or ""
    plan_lines = [ln.strip() for ln in desc_val.splitlines() if re.match(r"^(?:\[Shot\s+\d+\]|At\s+\d{2}:\d{2}\.\d{3})", ln.strip())]
    summ_val = _std._field(finished, "summary:") or ""
    res = {
        "ok": True,
        "script": finished,
        "plan": "\n".join(plan_lines).strip(),
        "brief": re.sub(r"^\s*\[[^\]]+\]\s*", "", summ_val).strip(),
        "mode": mode,
    }
    if updated_ref_plan and updated_ref_plan != ref_plan:
        res["updated_ref_plan"] = updated_ref_plan
    return res


PASS2_REFINE_SYSTEM_PROMPT = """You are the Pass-2 Double-Knot Continuity Refiner for MiniMax H3 (SandTie Engine).
You receive a Pass-1 draft (`plan` storyboard or complete `block` prompt) and a concise Audit Checklist for this clip.
Your task:
1. Satisfy EVERY item in the Audit Checklist while keeping Pass 1's valid labels, timestamps, `[Shot N]` cut headers, single-thought unity, and field structure intact.
2. Lock any character sheet's racial/ethnic identity and bone structure across `subject_definitions:`, `summary:`, `retention_analysis:`, and `[Shot 1]`, writing `<Subject 1> Name` smoothly (omitting parentheses and UI emojis).
3. Enforce strict wardrobe, screen-left/right spatial axis, set, and transition continuity across EVERY beat—keep active outfits locked per assigned subject, keep displaced/removed garments in that displaced state, and bridge every movement with concrete cause-and-effect motion (`action -> contact -> secondary reaction`).
4. Write direct literal visual prose free of literary filler; in explicit/NSFW scenes name anatomy directly (`cock`, `erect penis`, `pussy`, `bare breasts`, `asshole`, `cum`) and use `his erect cock` / `the man` rather than euphemisms.
5. Keep every sentence outside `<d>...</d>` 100% affirmative (describing what IS visible and moving), keep `overall_soundscape:` and `non_diegetic_music:` free of semicolons and spoken words, and keep each beat to one clear foreground audio focus.
6. Reply with ONLY the JSON object `{ "block": "<the refined prompt block>" }` (or `{ "plan": "<the refined storyboard>" }` when Stage is `plan`)."""


def build_pass2_audit_checklist(
    brief: str,
    flavors: dict,
    lab: dict,
    *,
    is_pov: bool,
    pov_val: str,
    rear_scene: bool,
    over_shoulder: bool,
    mouth_occupied: bool,
    anal_scene: bool,
    no_dialogue: bool,
    flavor_lines: list[str],
    plan: str = "",
    prev_hop_context: str = "",
) -> list[str]:
    checks = []
    exp_p2_str = str(flavors.get("explicit") or "")
    cam_p2_str = str(flavors.get("camera") or "")
    ward_p2_str = str(flavors.get("wardrobe") or "")
    plan_hint_p2 = str(flavors.get("plan_hint") or "")
    mirror_p2 = _dir.is_mirror_scene_active(exp_p2_str, cam_p2_str)

    for s_n in sorted((lab.get("subjects") or {}).keys()):
        for sp in [p for p in (lab.get("pictures") or []) if p.get("subject") == s_n]:
            s_desc = str(sp.get("desc") or "").strip()
            eth = _refs.extract_ethnicity_phrase(s_desc, brief=brief)
            if eth:
                if s_n == 1 and rear_scene and not mirror_p2:
                    eth_r = _refs.strip_front_facial_features_for_rear(eth)
                    checks.append(f"RACIAL LOCK (<Subject {s_n}>): Name as `{eth}` in headers; in `[Shot 1]` use rear-visible `{eth_r}` only while keeping face turned forward away from the camera.")
                else:
                    checks.append(f"RACIAL LOCK (<Subject {s_n}>): Name explicitly as `{eth}` in `subject_definitions:`, `summary:`, `retention_analysis:`, and `[Shot 1]`.")
            elif s_desc:
                checks.append(f"SHEET LOCK (<Subject {s_n}>): Preserve character anchor from {sp['label']} ({s_desc[:140]}).")

    ward_opts = _cat.resolve_dial_opts("wardrobe", ward_p2_str)
    if ward_opts:
        wmode_p2 = _bg.get_dial_mode(flavors, "wardrobe", "sequence")
        if len(ward_opts) >= 2 and wmode_p2 == "split":
            subj_keys = sorted((lab.get("subjects") or {}).keys())
            pairs = []
            for idx, wo in enumerate(ward_opts):
                sn = subj_keys[idx] if idx < len(subj_keys) else (idx + 1)
                wl = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+", "", wo["label"]).strip()
                pairs.append(f"<Subject {sn}>={wl}")
            checks.append(f"SPLIT WARDROBE LOCK: Keep assigned outfits ({', '.join(pairs)}) consistent on their assigned subjects across every beat.")
        else:
            w_clean = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+", "", ward_opts[0]["label"]).strip()
            checks.append(f"WARDROBE LOCK: Keep the selected attire ({w_clean}) consistent across EVERY beat, preserving any explicit displacement state.")

    place_opts = _cat.resolve_dial_opts("place", flavors.get("place"))
    if place_opts:
        if len(place_opts) >= 2 and _bg.get_dial_mode(flavors, "place", "sequence") == "sequence":
            p_names = " -> ".join(re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+", "", po["label"]).strip() for po in place_opts)
            checks.append(f"ENVIRONMENT SEQUENCE LOCK: Transition cleanly across `{p_names}` keeping props and lighting faithful to each active room.")
        else:
            p_clean = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+", "", place_opts[0]["label"]).strip()
            checks.append(f"ENVIRONMENT DOMAIN LOCK: Keep all props and surfaces strictly faithful to {p_clean}.")

    if is_pov:
        pov_lbl = "male POV" if pov_val == "male" else ("female POV" if pov_val == "female" else "first-person POV")
        checks.append(f"POV CHECK ({pov_lbl}): Write camera perspective strictly in first-person `my`/`I` with the partner centered ahead.")
    if rear_scene and not anal_scene and not mirror_p2:
        checks.append("REAR-POSE LOCK: Keep torso, chest, shoulders, and head facing forward away from the lens throughout.")
    if over_shoulder:
        checks.append("OVER-SHOULDER LOCK: Keep hips and shoulders angled away while only the chin turns back over one shoulder.")
    if mouth_occupied:
        checks.append("ORAL SEAL LOCK: Keep lips sealed tightly around the shaft/object with hollowed cheeks during sucking beats.")
    if no_dialogue:
        is_sex_p2 = _dir.is_sexual(brief, exp_p2_str, ward_p2_str, fetish_id=str(flavors.get("fetish") or ""))
        if is_sex_p2:
            checks.append("WORDLESS AUDIO LOCK: Keep all beats free of `<d>` speech; place natural breaths, moans, and wet foley inside `overall_soundscape:`.")
        elif is_pure_bgm_soundscape(brief=brief, flavors=flavors, sex_scene=is_sex_p2):
            checks.append("SOUNDSCAPE OFF: Keep `<d>` dialogue omitted and set `overall_soundscape:` strictly to `N/A` so the music track plays unobstructed.")
        else:
            checks.append("SILENT LIPS LOCK: Keep `<d>` dialogue omitted; describe poised closed lips and tactile room foley inside `overall_soundscape:`.")
    else:
        checks.append("AUDIO DISCIPLINE: Keep `overall_soundscape:` strictly free of spoken words and semicolons, using comma-separated foley.")
        acc_opts_p2 = _cat.resolve_dial_opts("accent", flavors.get("accent"))
        tgt_lang_p2 = _dlg.detect_target_language(brief, acc_opts_p2[0] if acc_opts_p2 else None)
        if tgt_lang_p2 != "English":
            checks.append(
                f"NATIVE SCRIPT LOCK (<d>...</d>): Write EVERY spoken word inside `<d>[{tgt_lang_p2}, ...] ...</d>` strictly in authentic native {tgt_lang_p2} characters "
                f"(sample: `{_dlg.native_sample_for(tgt_lang_p2)}`), keeping all surrounding descriptions in English."
            )
    for fl in flavor_lines:
        if any(tag in fl for tag in ("LAW:", "COMBAT", "ANIME-TO-REAL-LIFE", "ORBIT", "ELEVATOR", "TOP-DOWN", "OPEN-END", "HOP-JOIN CONTINUITY", "HOP TRANSITION", "SCREEN-AXIS")):
            checks.append(fl)
    if str(prev_hop_context or "").strip() and not any("HOP" in c for c in checks):
        checks.append(f"HOP CONTINUITY CHECK: Ensure [Shot 1] smoothly continues the previous hop ending (`{str(prev_hop_context).strip()[:160]}`) with continuous posture and camera axis.")
    return checks[:12]
