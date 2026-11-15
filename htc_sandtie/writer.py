"""SandTie Scribe — Clean-Room MiniMax H3 Prompt Engine (`Ref2VA`, `T2VA`, `I2VA`/`FL2VA`/`L2VA`, `Start-Frame Prep`, `CPU Tie`)."""
from __future__ import annotations

import json
import re

from .. import planner as _pl
from .. import standard as _std
from . import beat_grid as _bg
from . import catalogs as _cat
from . import dialogue as _dlg
from . import director_cards as _dir
from . import finisher as _fin
from . import refs as _refs

FAST_SYSTEM_PROMPT = """You are the SandTie Kinetic Director & Single-Shot Scribe for MiniMax H3 (Hailuo H3).
Your prompt goes straight to the H3 video-and-audio encoder running at CFG 1 with zero negative branch: every word is rendered literally.

## 1. H3 STRUCTURE & REFERENCE BINDING
- When `Stage: write`:
  - `Ref2VA` fields in exact order: `subject_definitions:`, `summary:`, `retention_analysis:`, `detailed_description:`, `overall_soundscape:`, `non_diegetic_music:`.
  - `T2VA` fields in exact order: `integrated_multimodal_description:`, `overall_soundscape:`, `non_diegetic_music:`.
  - Start immediately with the first field label, keeping total prompt length under 7,000 characters.
- When `Stage: plan`: output ONLY `[Shot 1] ...` and `At MM:SS.mmm-MM:SS.mmm, ...` storyboard beats.
- **Subject & Picture Binding:** Use ONLY the exact `<Picture N>`, `<Subject N>`, and `<Audio N>` labels listed in the user turn (zero `@tags`), writing `<Subject 1> Name` (no parentheses around `Name`) across headers and `[Shot 1]`. Never include UI emojis (`🔥`) or dial menu titles in `subject_definitions:` or `retention_analysis:`.
- **Single-Timeline Law (`[Shot N]`):** `[Shot 1]` opens at `00:00.000` with NO timestamp on its header; every later cut (`[Shot 2]`, `[Shot 3]`, ...) MUST open on its own line with `[Shot N] At MM:SS.mmm,` along one continuous `00:00.000 -> Duration` clock.

## 2. TONE & GENRE BALANCE (SFW & ADULT PARITY, DIRECT LITERAL WORDING)
- **Plain Visual Words (Zero Literary Bloat):** Write concrete visible framing, body orientation, hand grips, clothing state, camera move, lighting, and sound in crisp direct English. Write concrete physical motion rather than vague atmospheric or abstract phrasing.
- **Regular / SFW baseline (when explicit/fetish/nude dials are inactive and the brief does not ask for adult content):** Keep every subject clothed in their established outfit and stage grounded story, dialogue, action, combat, or dance beats without drifting into nudity or sexual content.
- **Adult / NSFW mode (when explicit/fetish/nude dials are active or the brief asks for adult/sexual content):** Describe anatomy and sexual acts literally as seen on camera: `cock`, `erect penis`, `balls`, `pussy`, `labia`, `clit`, `asshole`, `bare breasts`, `tits`, `nipples`, `ass cheeks`, `cum`. Always use exact literal anatomical terms (`his erect cock`, `the man`, `her pussy`, `her bare breasts`) instead of euphemisms (`partner's shaft`, `her partner`, `adult encounter`, `member`, `down there`). If no `<Subject 2>` is defined, name the man directly (`the man`, `his hard cock`, `his hands on her waist` — or `the other woman` in lesbian scenes) and state clearly who is behind/above/kneeling and what enters what.

## 3. H3 CINEMATOGRAPHY & CONTINUITY
- **12 Motion Primitives + Amplitude + Speed:** Write camera moves with amplitude and speed (`dolly push in with moderate amplitude at slow speed`, `pull out with large amplitude at steady speed`, `tripod pan left with strictly level horizon`, `arc shot sweeping 180 degrees`, `tracking shot gliding beside`, `pedestal up smoothly`, `static locked shot`, `POV`).
- **Open-End Range Law:** Open wide before pushing/zooming inward; open tight on eyes or prop before pulling out / ascending wide.
- **Set & Sticky Clothing Lock:** Keep location, props, and clothing states unified across beats and cuts; once a dress, skirt, top, or underwear is bunched up, pulled aside, or off, keep it that way in every later shot. Omit rig hardware names and meta labels (`embodying the ... staging`).

## 4. POSITIVE PHRASING & AUDIO DISCIPLINE
- **100% Additive English Outside `<d>`:** Keep every word positive outside `<d>...</d>` (zero negations like `no`, `not`, `never`, `without`, `avoid`, `don't`, `isn't`, `can't`, `won't`).
- **Spoken Dialogue Format:** When speech is requested or appropriate, write inline `(DIALOGUE) <Subject 1> Name (S1) ...: <d>[delivery tone] Spoken line.</d>` with straight ASCII apostrophes. When a non-English language / Accent dial is active (`Japanese`, `Korean`, `Mandarin`, `Spanish`, `French`, `Russian`, `Portuguese`, `Italian`), write ALL spoken words inside `<d>...</d>` strictly in that language's native script (e.g. 日本語かな/漢字 for Japanese, 한국어 for Korean, 中文 for Mandarin, Русский for Russian — never English or romanization inside `<d>...</d>`), while keeping descriptions outside `<d>...</d>` in English. Keep purely physical, silent, or oral-contact beats free of spoken `<d>` words, putting breaths, moans, gasps, and wet foley inside `overall_soundscape:`.
- **Audio Fields (`overall_soundscape:` & `non_diegetic_music:`):** Keep zero semicolons `;` (use `, ` or `. `), keep `overall_soundscape:` free of spoken dialogue/words, and set `non_diegetic_music:` to `N/A` when diegetic-only or name genre/instruments/BPM cleanly.

## 5. OUTPUT FORMAT
Reply with ONLY a valid JSON object matching:
`{"plan": "..."}` when `Stage: plan`, OR `{"block": "..."}` when `Stage: write`."""

PRECISION_ANAL_ADDENDUM = """## 4B. PRECISION ANAL HOLE-MAP & GEOMETRY LAW (ANAL SCENES ONLY)
1. Open already inside from `[Shot 1]` and Beat 1 (`00:00.000`).
2. State the clear two-opening anatomical map (higher opening nearer lower back for anal contact vs. separate lower opening empty) or strap-on harness map (`his anus` vs `cock and balls visible`), repeating short buried strokes where the head stays inside and the anal ring stays taut around the shaft.
3. Keep the camera steady from first frame to last frame and assign concrete left/right hand grips across every beat."""


def _clean_ui_label(label: str) -> str:
    """Strip UI emojis and all-caps menu category prefixes from dial labels."""
    s = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+", "", str(label or "")).strip()
    s = re.sub(
        r"^(?:NUDE(?:\s*\([^)]*\))?|FETISH(?:\s+NUDE)?|PARTIAL|TOPLESS|BOTTOMLESS)\s*[—\-–:]+\s*",
        "",
        s,
        flags=re.I,
    )
    return re.sub(r"\s{2,}", " ", s).strip()


def _sanitize_beat_clause(text: str) -> str:
    return _fin.sanitize_additive_rule(_dir.strip_d_examples(text or ""))


def _extract_beat_clauses_from_rule(rule_text: str, lab: dict | None = None, *, brief: str = "", explicit_id: str = "") -> dict[int, str]:
    txt = _adapt_rule_subjects(rule_text, lab, brief=brief, explicit_id=explicit_id)
    txt = _sanitize_beat_clause(txt)
    out: dict[int, str] = {}
    if not txt:
        return out
    shot_parts = re.split(
        r"(?:\(\d+\)\s*)?(?:In\s+)?`?\[\s*Shot\s+([1-6])\s*\]`?(?:\s*,?\s*At\s+MM:SS\.mmm\s*,?\s*)?",
        txt,
        flags=re.I,
    )
    if len(shot_parts) >= 5:
        for i in range(1, len(shot_parts), 2):
            s_idx = int(shot_parts[i]) - 1
            clause = shot_parts[i + 1].strip(" .;,`-\n")
            m_lead = re.match(r"^(opens|cuts(?:\s+(?:cleanly|smoothly))?(?:\s+(?:into|onto|to))?|switches(?:\s+(?:to|into))?)\s+(.*)$", clause, flags=re.I)
            if m_lead:
                rest = m_lead.group(2).strip(" .;,`-")
                if re.match(r"^(?:the|a|an|under|inside|in|at|on|beside|behind|against|through|from)\b", rest, re.I):
                    clause = f"{'Camera opens' if s_idx == 0 else 'Camera frames'} {rest}"
                else:
                    clause = rest
            if clause:
                out[s_idx] = clause
        if out:
            return out
    parts = re.split(r"\bBeat\s+([1-6])\b[:\-\s—]*", txt, flags=re.I)
    if len(parts) >= 3:
        for i in range(1, len(parts), 2):
            b_idx = int(parts[i]) - 1
            clause = parts[i + 1].strip(" .;,-")
            if clause:
                out[b_idx] = clause
        return out
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", txt) if s.strip()]
    if len(sents) >= 3:
        out[0] = " ".join(sents[:max(1, len(sents) // 3)])
        out[1] = " ".join(sents[max(1, len(sents) // 3):max(2, (2 * len(sents)) // 3)])
        out[2] = " ".join(sents[max(2, (2 * len(sents)) // 3):])
    elif len(sents) == 2:
        out[0], out[1], out[2] = sents[0], sents[1], sents[1]
    elif sents:
        out[0] = sents[0]
    return out


def _adapt_rule_subjects(rule_text: str, lab: dict | None = None, *, brief: str = "", explicit_id: str = "") -> str:
    if not rule_text:
        return ""
    lab = lab or {}
    sub_meta = lab.get("subjects") or {}
    out = str(rule_text)
    for sn in sorted(sub_meta.keys()):
        m = sub_meta.get(sn) or {}
        cname = str(m.get("char_name") or m.get("name") or "").strip()
        if cname:
            out = re.sub(rf"<Subject\s+{sn}>(?!(?:\s+{re.escape(cname)})\b)", f"<Subject {sn}> {cname}", out)
    if 2 not in sub_meta:
        comb = f"{explicit_id} {brief} {out}".lower()
        is_les = bool(re.search(r"\b(?:lesbian|scissoring|tribadism|cunnilingus|two women|other woman|fff)\b", comb))
        is_sex = bool(explicit_id or _dir.is_sexual(brief, explicit_id=explicit_id))
        if is_les:
            out = re.sub(r"<Subject\s+2>'s\b", "the other woman's", out)
            out = re.sub(r"<Subject\s+2>", "the other woman", out)
        elif is_sex:
            out = re.sub(r"<Subject\s+2>'s\s+(?:(thick|hard|vertical|oiled|glistening|throbbing|swollen)\s+)?(?:erect\s+)?shaft\b", lambda m: f"his {m.group(1) + ' ' if m.group(1) else ''}erect cock", out, flags=re.I)
            out = re.sub(r"<Subject\s+2>'s\b", "the man's", out)
            out = re.sub(r"<Subject\s+2>", "the man", out)
        else:
            out = re.sub(r"<Subject\s+2>'s\b", "the other person's", out)
            out = re.sub(r"<Subject\s+2>", "the other person", out)
    # Replace euphemistic "her partner's shaft" / "her partner" in explicit text when heterosexual male anatomy is implied
    if _dir.is_sexual(brief, explicit_id=explicit_id) and not re.search(r"\b(?:lesbian|fff|strap[- ]?on)\b", f"{explicit_id} {out}", re.I):
        out = re.sub(
            r"\b(?:her|their|the)\s+partner'?s\s+(?:(thick|hard|vertical|oiled|glistening|throbbing|swollen)\s+)?(?:erect\s+)?(?:shaft|cock|penis|member)\b",
            lambda m: f"his {m.group(1) + ' ' if m.group(1) else ''}erect cock",
            out,
            flags=re.I,
        )
        out = re.sub(r"\bher\s+partner'?s\b", "the man's", out, flags=re.I)
        out = re.sub(r"\bher\s+partner\b", "the man", out, flags=re.I)
    return out


def parse_prev_hop_continuity(prev_hop_context: str) -> dict:
    """Parse `Hop N (sN, join=..., camera=..., framing=..., pace=..., tail=...): beat`."""
    raw = str(prev_hop_context or "").strip()
    if not raw:
        return {}
    m_hdr = re.match(r"^(Hop\s+\d+\s*\([^)]*\))\s*:\s*(.*)$", raw, flags=re.S | re.I)
    meta_str = m_hdr.group(1) if m_hdr else ""
    beat_txt = (m_hdr.group(2) if m_hdr else raw).strip()
    out = {"raw": raw, "beat": beat_txt, "join": "", "camera": "", "framing": "", "pace": "", "tail": ""}
    for key in ("join", "camera", "framing", "pace", "tail"):
        km = re.search(rf"\b{key}=([^\s,)]+)", meta_str, re.I)
        if km:
            out[key] = km.group(1).strip().lower()
    return out


def build_flavor_facts(
    brief: str,
    flavors: dict | None,
    spans: list[tuple[float, float]],
    *,
    cam_override: str = "",
    plan: str = "",
    lab: dict | None = None,
    prev_hop_context: str = "",
) -> tuple[list[str], str]:
    flavors = flavors or {}
    lab = lab or {}
    facts: list[str] = []
    picked_refs: set[str] = set()
    plan_hint = str(flavors.get("plan_hint") or "")
    no_dialogue = _dlg.should_suppress_dialogue(brief, flavors=flavors, plan=plan)
    prelim_exp_id = str(flavors.get("explicit") or "").strip()
    prelim_cam_id = str(flavors.get("camera") or "").strip()
    prelim_pose_id = str(flavors.get("pose") or "").strip()
    rear_prelim = _dir.is_rear_facing(brief, prelim_exp_id, plan=plan, plan_hint=plan_hint, camera_id=prelim_cam_id, pose_id=prelim_pose_id)
    mirror_prelim = _dir.is_mirror_scene_active(prelim_exp_id, prelim_cam_id)

    # 1. Character racial/ethnic & facial anchor locks
    for s_n in sorted((lab.get("subjects") or {}).keys()):
        s_meta = (lab.get("subjects") or {}).get(s_n) or {}
        cname = s_meta.get("char_name") or s_meta.get("name") or ""
        cname_str = f" {cname}" if cname else ""
        for sp in [p for p in (lab.get("pictures") or []) if p.get("subject") == s_n]:
            s_desc = str(sp.get("desc") or "").strip()
            eth = _refs.extract_ethnicity_phrase(s_desc, brief=brief)
            if eth:
                if s_n == 1 and rear_prelim and not mirror_prelim:
                    eth_r = _refs.strip_front_facial_features_for_rear(eth)
                    facts.append(
                        f"CHARACTER IDENTITY LOCK (<Subject {s_n}>{cname_str} in {sp['label']}): "
                        f"Identify as `{eth}` in `subject_definitions:`, `summary:`, `retention_analysis:`, and in `[Shot 1]` (rear view) write `{eth_r}` only, keeping her face turned forward away from the camera."
                    )
                else:
                    facts.append(
                        f"CHARACTER IDENTITY LOCK (<Subject {s_n}>{cname_str} in {sp['label']}): "
                        f"Explicitly identify <Subject {s_n}>{cname_str} as `{eth}` in `subject_definitions:`, `summary:`, `retention_analysis:`, and `[Shot 1]`."
                    )
                break
            elif s_desc:
                facts.append(
                    f"CHARACTER SHEET LOCK (<Subject {s_n}>{cname_str} in {sp['label']}): "
                    f"Include the anchor and garment/features from {sp['label']} ({s_desc[:180]}) in `subject_definitions:` and `retention_analysis:`."
                )
                break

    place_opts = _cat.resolve_dial_opts("place", flavors.get("place"))
    place_opt = place_opts[0] if place_opts else None
    place_id = place_opt["id"] if place_opt else ""

    has_bg_plate = False
    for sp in lab.get("pictures") or []:
        if sp.get("subject") is None and not _refs.is_studio_backdrop_text(sp.get("desc") or ""):
            has_bg_plate = True
            if not place_opt:
                facts.append(
                    f"SCENE PLATE LOCK ({sp['label']} = @{sp.get('tag') or 'setting'}): "
                    f"Stage inside {sp['label']} ({sp.get('desc') or 'referenced environment'}). Define {sp['label']} in `subject_definitions:`, `retention_analysis:`, and `[Shot 1]`."
                )

    pov_val = _dir.resolve_pov_mode(brief, flavors=flavors, plan=plan)
    is_pov = pov_val in ("male", "female", "on")

    cam_opts = [] if is_pov else _cat.resolve_dial_opts("camera", flavors.get("camera"))
    cam_opt = cam_opts[0] if cam_opts else None
    cam_id = ",".join(o["id"] for o in cam_opts) if cam_opts else ""
    for o in cam_opts:
        picked_refs.add(f"camera:{o['id']}")

    light_opts = _cat.resolve_dial_opts("light", flavors.get("light"))
    light_opt = light_opts[0] if light_opts else None
    for o in light_opts:
        picked_refs.add(f"cinema:{o['id']}")

    lens_opts = _cat.resolve_dial_opts("lens", flavors.get("lens"))
    lens_opt = lens_opts[0] if lens_opts else None
    for o in lens_opts:
        picked_refs.add(f"cinema:{o['id']}")

    fx_opts = _cat.resolve_dial_opts("fx", flavors.get("fx"))
    fx_opt = fx_opts[0] if fx_opts else None
    for o in fx_opts:
        picked_refs.add(f"fx:{o['id']}")

    style_opts = _cat.resolve_dial_opts("style", flavors.get("style"))
    col_opts = _cat.resolve_dial_opts("colour", flavors.get("colour"))
    ward_opts = _cat.resolve_dial_opts("wardrobe", flavors.get("wardrobe"))
    ward_opt = ward_opts[0] if ward_opts else None
    ward_id = ",".join(o["id"] for o in ward_opts) if ward_opts else ""
    era_opts = _cat.resolve_dial_opts("era", flavors.get("era"))
    tv_opts = _cat.resolve_dial_opts("tv_show", flavors.get("tv_show"))
    char_opts = _cat.resolve_dial_opts("character", flavors.get("character"))
    pose_opts = _cat.resolve_dial_opts("pose", flavors.get("pose"))
    pose_id = ",".join(o["id"] for o in pose_opts) if pose_opts else ""
    combat_opts = _cat.resolve_dial_opts("combat", flavors.get("combat"))
    exp_opts = _cat.resolve_dial_opts("explicit", flavors.get("explicit"))
    exp_opt = exp_opts[0] if exp_opts else None
    exp_id = ",".join(o["id"] for o in exp_opts) if exp_opts else ""
    fetish_opts = _cat.resolve_dial_opts("fetish", flavors.get("fetish"))
    talk_opts = _cat.resolve_dial_opts("talkstyle", flavors.get("talkstyle"))
    talk_opt = talk_opts[0] if talk_opts else None
    acc_opts = _cat.resolve_dial_opts("accent", flavors.get("accent"))
    acc_opt = acc_opts[0] if acc_opts else None
    amb_opts = _cat.resolve_dial_opts("ambience", flavors.get("ambience"))
    music_opts = _cat.resolve_dial_opts("music", flavors.get("music"))

    # Domain conflict & strict wardrobe/set lock (prevents shower+tennis+pool+foam bugs!)
    dom_conflicts = _cat.check_domain_conflicts(flavors)
    if dom_conflicts or ward_opts or place_opt:
        if place_opt and dom_conflicts:
            facts.append(
                f"STRICT ENVIRONMENT PRIORITY LOCK: Anchor all walls, flooring, and props strictly to {place_opt['label']} (`domain={place_opt.get('domain', 'general')}`) — discard incompatible props (like pool sunbeds inside showers) if another preset mentions them."
            )
        if ward_opts:
            w_desc = ", ".join(_clean_ui_label(o["label"]) for o in ward_opts)
            facts.append(
                f"WARDROBE LOCK: Keep `{w_desc}` consistent across `[Shot 1]` and every cut (`At MM:SS.mmm`) unless an explicit undress/displacement beat moves it aside."
            )

    # Aspect lock
    canvas_asp = _bg.detect_canvas_aspect(brief=brief, node_aspect=str(flavors.get("aspect") or ""), camera_id=cam_id, plan=plan, plan_hint=plan_hint)
    canvas_bkt = _bg.aspect_bucket(canvas_asp)
    if canvas_bkt == "9:16":
        facts.append(f"ASPECT {canvas_asp} VERTICAL: Frame vertical portrait compositions suited to {canvas_asp} framing (never quote technical aspect-fill jargon inside retention_analysis).")
    elif canvas_bkt == "1:1":
        facts.append("ASPECT 1:1 SQUARE: Frame balanced centered 1:1 square compositions with clean headroom and side symmetry.")
    elif canvas_bkt == "16:9":
        facts.append(f"ASPECT {canvas_asp} WIDESCREEN: Frame horizontal {canvas_asp} compositions with depth layers and lateral travel.")

    # Camera + trajectory
    traj_law = _bg.camera_trajectory_plan(brief, cam_override or cam_id, spans, is_pov=is_pov, has_bg_plate=has_bg_plate)
    if len(cam_opts) == 1 and cam_opt and cam_opt.get("rule"):
        facts.append(f"CAMERA MOVEMENT ({cam_opt['label']}): {_fin.sanitize_additive_rule(cam_opt['rule'])}")
    elif len(cam_opts) >= 2:
        cmode = _bg.get_dial_mode(flavors, "camera", "sequence")
        if cmode == "blend":
            facts.append("CAMERA FUSION: " + " + ".join(f"{o['label']} ({_fin.sanitize_additive_rule(o.get('rule',''))})" for o in cam_opts))
        else:
            alloc = _bg.allocate_stages_to_spans(cam_opts, spans)
            facts.append("MULTI-CAMERA PROGRESSION: " + " -> ".join(f"Shot {i+1} ({o['label']} at {', '.join(ts for _, ts in bl)}): {_fin.sanitize_additive_rule(o.get('rule',''))}" for i, (o, bl) in enumerate(alloc)))
    if traj_law:
        facts.append(traj_law)

    # Lighting, Optics, FX, Style, Colour, Era, World, Place, Character, Wardrobe
    if light_opts:
        facts.append("LIGHTING: " + " + ".join(_fin.sanitize_additive_rule(o.get("rule") or o["label"]) for o in light_opts))
    if lens_opts:
        facts.append("OPTICS & FRAMING: " + " + ".join(_fin.sanitize_additive_rule(o.get("rule") or o["label"]) for o in lens_opts))
    if style_opts:
        if len(style_opts) >= 2 and _bg.get_dial_mode(flavors, "style", "sequence") == "sequence":
            alloc = _bg.allocate_stages_to_spans(style_opts, spans)
            facts.append("MULTI-STYLE SEQUENCE: " + " -> ".join(f"{o['label']} ({', '.join(ts for _, ts in bl)}): {_fin.sanitize_additive_rule(o.get('rule',''))}" for o, bl in alloc))
        else:
            facts.append("VISUAL STYLE: " + " + ".join(_fin.sanitize_additive_rule(o.get("rule") or o["label"]) for o in style_opts))
    if col_opts:
        facts.append("COLOUR GRADE: " + " + ".join(_fin.sanitize_additive_rule(o.get("rule") or o["label"]) for o in col_opts))
    if era_opts:
        facts.append("ERA / PERIOD: " + " + ".join(_fin.sanitize_additive_rule(o.get("rule") or o["label"]) for o in era_opts))
    if tv_opts:
        facts.append("TONAL WORLD: " + " + ".join(_fin.sanitize_additive_rule(o.get("world") or o["label"]) for o in tv_opts))

    fx_timing = str(flavors.get("fx_timing") or "delayed_mid")
    if fx_opts:
        fx_traj = _bg.fx_trajectory_plan(fx_opt, light_opt, spans, fx_timing=fx_timing)
        if fx_traj:
            facts.append(fx_traj)
        else:
            facts.append("VISUAL FX: " + " + ".join(f"{o['label']} ({_fin.sanitize_additive_rule(o.get('rule',''))})" for o in fx_opts))

    if place_opt and place_opt.get("rule"):
        facts.append(f"SCENE SETTING ({_clean_ui_label(place_opt['label'])}): {_fin.sanitize_additive_rule(place_opt['rule'])}")
    if char_opts and not (lab.get("pictures")):
        facts.append("CAST ARCHETYPES: " + " | ".join(f"{_clean_ui_label(o['label'])} ({_fin.sanitize_additive_rule(o.get('rule',''))})" for o in char_opts))
    if ward_opts:
        facts.append("WARDROBE: " + " | ".join(_fin.sanitize_additive_rule(o.get('rule') or _clean_ui_label(o['label'])) for o in ward_opts))

    # Poses & Cinema Knowledge
    if pose_opts:
        if len(pose_opts) >= 2 and _bg.get_dial_mode(flavors, "pose", "sequence") == "sequence":
            alloc = _bg.allocate_stages_to_spans(pose_opts, spans)
            facts.append("POSE CHOREOGRAPHY SEQUENCE: " + " -> ".join(f"{_clean_ui_label(o['label'])} ({', '.join(ts for _, ts in bl)}): {_fin.sanitize_additive_rule(o.get('rule',''))}" for o, bl in alloc))
        else:
            facts.append("ANCHOR POSE: " + " + ".join(_fin.sanitize_additive_rule(o.get("rule") or _clean_ui_label(o["label"])) for o in pose_opts))

    has_multi_shot = any(c in ("shot_reverse", "multi_angle_action_close", "whip_pan_transition") for c in _cat.parse_multi_ids(cam_id))
    for tok, _ref, kopt in _dir.knowledge_terms_in_brief(brief, picked_refs=picked_refs, is_multi_shot=has_multi_shot):
        facts.append(f"TERM DEFINITION ('{tok}' -> {_clean_ui_label(kopt['label'])}): {_fin.sanitize_additive_rule(kopt['rule'])}")

    # Ambience, Music, Speech, Accent
    if amb_opts:
        facts.append("AMBIENCE FOLEY (zero semicolons): " + ", ".join(_fin.sanitize_additive_rule(o.get("rule") or "") for o in amb_opts if o.get("rule")))
    raw_music = _cat.parse_multi_ids(flavors.get("music"))
    if "none" in raw_music:
        facts.append("MUSIC: N/A (diegetic room audio only)")
    elif music_opts:
        facts.append("NON-DIEGETIC MUSIC (zero semicolons): " + ", ".join(_fin.sanitize_additive_rule(o.get("rule") or "") for o in music_opts if o.get("rule")))

    target_lang = _dlg.detect_target_language(brief, acc_opt)
    if talk_opt and not no_dialogue:
        facts.append(f"SPEECH DELIVERY ({talk_opt['label']}): {talk_opt.get('words', '')}")
    if target_lang != "English" and not no_dialogue:
        native_ex = _dlg.native_sample_for(target_lang)
        acc_desc = (acc_opt.get("words") or acc_opt.get("accent") or target_lang) if acc_opt else target_lang
        facts.append(
            f"NATIVE LANGUAGE SCRIPT LAW ({target_lang}): ALL spoken words inside `<d>[{target_lang}, tone] ...</d>` MUST be written strictly in authentic native {target_lang} script/characters"
            + (f" (e.g. `{native_ex}`)" if native_ex else "")
            + f" ({acc_desc}) — keep zero English or romanized words inside `<d>...</d>`, while keeping all descriptions outside `<d>...</d>` in English."
        )
    elif acc_opt and not no_dialogue:
        facts.append(f"ACCENT / LANGUAGE ({acc_opt['label']}): Speak in `{acc_opt.get('accent') or acc_opt.get('lang')}` inside `<d>[{acc_opt.get('accent') or acc_opt['lang']} ...] ...</d>`.")

    # Life, Energy, Expression, POV
    sex_scene = _dir.is_sexual(brief, exp_id, ward_id, fetish_id=str(flavors.get("fetish") or ""))
    combat_scene = _dir.is_combat(brief, str(flavors.get("combat") or ""), ward_id, str(flavors.get("fx") or ""))
    anal_scene = _dir.is_anal(brief, explicit_id=exp_id, plan=plan, plan_hint=plan_hint)
    pegging_scene = _dir.is_pegging_scene(brief, explicit_id=exp_id, plan=plan, plan_hint=plan_hint)
    rear_scene = _dir.is_rear_facing(brief, exp_id, plan=plan, plan_hint=plan_hint, camera_id=cam_id, pose_id=pose_id)
    mirror_scene = _dir.is_mirror_scene_active(exp_id, cam_id)
    over_shoulder = _dir.is_over_shoulder(brief, explicit_id=exp_id, camera_id=cam_id, plan=plan, plan_hint=plan_hint, pose_id=pose_id)
    mouth_occupied = _dir.is_mouth_occupied(brief, explicit_id=exp_id, plan=plan, plan_hint=plan_hint)
    solo_bj_oral = _dir.uses_solo_blowjob_template(brief, explicit_id=exp_id, plan=plan, plan_hint=plan_hint)
    prog_setup = _dir.is_progressive_or_casual_setup(brief, explicit_id=exp_id, plan=plan, plan_hint=plan_hint)

    motion_val = _dir.normalize_perf_level("motion", flavors.get("motion"), fallback=str(flavors.get("energy") or "natural"))
    energy_val = _dir.normalize_perf_level("energy", flavors.get("energy"), fallback="steady")
    expr_val = _dir.normalize_perf_level("expression", flavors.get("expression"), fallback="natural")
    expr_read = str(flavors.get("expr_read") or "auto").strip().lower()
    life_val = _dir.normalize_perf_level("life", flavors.get("life"), fallback="natural")

    if sex_scene:
        facts.append(_dir.LIFE_RULES_POSE_LOCKED.get(life_val, _dir.LIFE_RULES_POSE_LOCKED["natural"]))
        facts.append(_dir.MOTION_RULES_SEX.get(motion_val, _dir.MOTION_RULES_SEX["natural"]))
        facts.append(_dir.ENERGY_RULES_SEX.get(energy_val, _dir.ENERGY_RULES_SEX["steady"]))
        if rear_scene and not mirror_scene:
            facts.append(_dir.EXPRESSION_RULES_REAR.get(expr_val, _dir.EXPRESSION_RULES_REAR["natural"]))
        elif mouth_occupied:
            facts.append(_dir.EXPRESSION_RULES_SEX_ORAL.get(expr_val, _dir.EXPRESSION_RULES_SEX_ORAL["natural"]))
        elif prog_setup:
            facts.append(_dir.EXPRESSION_RULES_SEX_PROGRESSIVE.get(expr_val, _dir.EXPRESSION_RULES_SEX_PROGRESSIVE["natural"]))
        else:
            facts.append(_dir.EXPRESSION_RULES_SEX.get(expr_val, _dir.EXPRESSION_RULES_SEX["natural"]))
    else:
        facts.append(_dir.LIFE_RULES.get(life_val, _dir.LIFE_RULES["natural"]))
        facts.append(_dir.MOTION_RULES_GEN.get(motion_val, _dir.MOTION_RULES_GEN["natural"]))
        facts.append(_dir.ENERGY_RULES_GEN.get(energy_val, _dir.ENERGY_RULES_GEN["steady"]))
        facts.append(_dir.EXPRESSION_RULES_GEN.get(expr_val, _dir.EXPRESSION_RULES_GEN["natural"]))
    if expr_read and expr_read != "auto" and (not sex_scene or not rear_scene or mirror_scene) and not mouth_occupied:
        er_rule = _dir.EXPRESSION_FLAVOR_RULES.get(expr_read)
        if er_rule:
            facts.append(er_rule)

    if is_pov:
        pov_lbl = "Male first-person POV" if pov_val == "male" else ("Female first-person POV" if pov_val == "female" else "First-person POV")
        facts.append(f"FIRST-PERSON POV CAMERA ({pov_lbl}): Write strictly from `my` / `I` eye-level perspective looking at the partner; keep my own head/face out of frame.")

    # Explicit & Playbook stagings
    if exp_opts:
        if len(exp_opts) >= 2:
            alloc = _bg.allocate_stages_to_spans(exp_opts, spans)
            facts.append("MULTI-STAGE STAGING: " + " -> ".join(f"{_clean_ui_label(o['label'])} ({', '.join(ts for _, ts in bl)}): {_adapt_rule_subjects(_fin.sanitize_additive_rule(o.get('rule','')), lab, brief=brief, explicit_id=o['id'])}" for o, bl in alloc))
        else:
            facts.append(f"PRIMARY STAGING ({_clean_ui_label(exp_opt['label'])}): {_adapt_rule_subjects(_fin.sanitize_additive_rule(exp_opt.get('rule', '')), lab, brief=brief, explicit_id=exp_opt['id'])}")
        if anal_scene:
            facts.append(PRECISION_ANAL_ADDENDUM)

    if fetish_opts:
        for fb in fetish_opts:
            fdir = _dir.format_playbook_directive(fb, has_camera_or_explicit=bool(exp_opt or cam_opt or is_pov or rear_scene), has_subject_or_wardrobe=bool(ward_opt or lab.get("pictures")))
            facts.append(_dir.strip_d_examples(fdir) if (no_dialogue or talk_opt or acc_opt or energy_val in ("hush", "calm")) else fdir)
    elif sex_scene and not exp_opts:
        for fb in _dir.playbook_matches(brief, exp_id):
            fdir = _dir.format_playbook_directive(fb, has_camera_or_explicit=bool(cam_opt or is_pov or rear_scene), has_subject_or_wardrobe=bool(ward_opt or lab.get("pictures")))
            facts.append(_dir.strip_d_examples(fdir) if no_dialogue else fdir)

    d_dir = _dir.dance_vocab_directive(brief, pose_id=pose_id)
    if d_dir:
        facts.append(d_dir)

    if combat_opts:
        if len(combat_opts) >= 2:
            alloc = _bg.allocate_stages_to_spans(combat_opts, spans)
            facts.append("COMBAT PROGRESSION: " + " -> ".join(f"{_clean_ui_label(o['label'])} ({', '.join(ts for _, ts in bl)}): {_fin.sanitize_additive_rule(o.get('rule',''))}" for o, bl in alloc))
        else:
            facts.append(f"COMBAT CHOREOGRAPHY ({_clean_ui_label(combat_opts[0]['label'])}): {_fin.sanitize_additive_rule(combat_opts[0].get('rule',''))}")

    if bool(flavors.get("kinetic_grip", True)) and not sex_scene:
        if motion_val in ("freeze", "slow"):
            facts.append("GROUNDED POISE (Kinetic Flow yielded to calm Motion): Keep posture anchored and breathing natural without unnecessary hand fidgeting, bridging smoothly into the next beat.")
        else:
            facts.append("KINETIC FLOW: Ground active beats with concrete weight transfer, clear hand placement, and smooth momentum carry-through between timestamps.")

    hop_ctx = parse_prev_hop_continuity(prev_hop_context)
    if hop_ctx:
        join_m = hop_ctx.get("join") or "continuous"
        if join_m in ("continuous", "match_cut"):
            facts.append(
                f"HOP-JOIN CONTINUITY (`join={join_m}` — follow ONLY when subjects/setting match the brief & active dials, never import unrelated props): "
                "Open [Shot 1] seamlessly from the previous hop's closing posture, hand placement, gaze, lighting, and framing"
                + (f" ({hop_ctx['framing']})" if hop_ctx.get("framing") else "")
                + (f" — closing state: `{hop_ctx['beat'][:220]}`" if hop_ctx.get("beat") else "")
                + "."
            )
        else:
            facts.append(
                f"HOP TRANSITION (`join={join_m}`): Open [Shot 1] with preserved wardrobe and lighting continuity into the fresh angle"
                + (f" (previous hop tail: `{hop_ctx['beat'][:180]}`)" if hop_ctx.get("beat") else "")
                + "."
            )
    if combat_scene:
        facts.append("COMBAT PHYSICS: Write concrete strike-to-impact-to-recoil mechanics with physically lit sparks, dust, shell casings, or elemental VFX reflections.")

    if sex_scene:
        facts.append("LITERAL ANATOMY LAW: Write concrete physical thrusts, grips, and skin contact in plain English using exact anatomy (`cock`, `erect penis`, `balls`, `pussy`, `labia`, `clit`, `asshole`, `bare breasts`, `nipples`, `cum`) — refer to the male partner directly as `the man` / `his erect cock`, never `partner's shaft` or euphemisms.")
        if rear_scene and not anal_scene and not mirror_scene:
            facts.append("REAR-FACING LOCK: Keep torso, chest, shoulders, and head facing forward away from the camera across every beat.")
        if over_shoulder:
            facts.append("OVER-SHOULDER LOCK: Keep hips and shoulders angled away while only her chin turns back over one shoulder.")
        if solo_bj_oral or mouth_occupied:
            facts.append("ORAL SEAL LAW: Keep lips sealed tightly around his cock during sucking beats, opening to pant only after pulling clear.")
        if pegging_scene:
            facts.append("PEGGING LOCK: Keep her leather strap-on harness buckled snugly at hips and his cock and balls visible outside the anal contact.")

    if not no_dialogue:
        tm_mode = str(flavors.get("talk_mode") or "auto").strip().lower()
        has_quotes = bool(_dlg.extract_quotes(brief))
        has_speech_req = bool(re.search(r"\b(?:say\w*|speak\w*|talk\w*|whisper\w*|tell\w*|ask\w*|dialogue|monologue|banter|confess\w*|joi|dirty\s*talk)\b", brief or "", re.I))
        exp_has_dlg = any("<d>" in str(o.get("rule") or "") for o in exp_opts)
        if has_quotes or talk_opt or acc_opt or fetish_opts or tm_mode == "talk_all" or has_speech_req or exp_has_dlg:
            cues = _dlg.pick_beat_dialogue_cues(brief=brief, talk_opt=talk_opt, acc_opt=acc_opt, playbook_entries=fetish_opts, n_beats=len(spans), is_sexual_scene=sex_scene)
            facts.append("SUGGESTED BEAT DIALOGUE ARC (adapt freely to voice & brief — avoid repetitive clichés): " + " | ".join(f"Beat {i+1}: `{c}`" for i, c in enumerate(cues)))
        else:
            facts.append("DIALOGUE CHOICE: Keep non-verbal, physical, or oral beats wordless with breathing/moans/wet foley in `overall_soundscape:`; add `<d>[tone] ...</d>` speech ONLY if the brief calls for spoken words.")
    else:
        if sex_scene:
            facts.append("WORDLESS PERFORMANCE (ZERO SPOKEN <d> LINES): Keep all beats free of spoken words; describe natural breaths, moans, and wet oral or skin contact sounds in `overall_soundscape:` (zero spoken dialogue there).")
        else:
            facts.append("SILENT PERFORMANCE: Characters perform with expressive posture and closed lips while narrowband acoustic room tone and tactile foley fill `overall_soundscape:` (zero voices/speech there).")

    return [f for f in facts if f], cam_id


def build_skeleton_text(
    spans: list[tuple[float, float]],
    q_map: dict[int, list[str]],
    cuts: list[int],
    lab: dict,
    *,
    brief: str = "",
    flavors: dict | None = None,
    extracted_video: dict | None = None,
    plan: str = "",
) -> str:
    flavors = flavors or {}
    if extracted_video and extracted_video.get("beats"):
        return "\n".join([f"[Shot 1] {extracted_video.get('shot1') or '...'}"] + [str(b) for b in extracted_video["beats"]])

    subs = sorted((lab.get("subjects") or {}).keys())
    sub_meta = lab.get("subjects") or {}
    audios = lab.get("audios") or []

    def _sub_lbl(sn: int) -> str:
        m = sub_meta.get(sn) or {}
        cn = m.get("char_name") or m.get("name") or ""
        return f"<Subject {sn}> {cn}".strip() if cn else f"<Subject {sn}>"

    s1_who = " and ".join(_sub_lbl(sn) for sn in subs) if subs else "The lead character"
    primary_speaker = _sub_lbl(subs[0]) if subs else "The lead character"

    place_opts = _cat.resolve_dial_opts("place", flavors.get("place"))
    light_opts = _cat.resolve_dial_opts("light", flavors.get("light"))
    lens_opts = _cat.resolve_dial_opts("lens", flavors.get("lens"))
    cam_opts = _cat.resolve_dial_opts("camera", flavors.get("camera"))
    style_opts = _cat.resolve_dial_opts("style", flavors.get("style"))
    col_opts = _cat.resolve_dial_opts("colour", flavors.get("colour"))
    exp_opts = _cat.resolve_dial_opts("explicit", flavors.get("explicit"))
    combat_opts = _cat.resolve_dial_opts("combat", flavors.get("combat"))
    pose_opts = _cat.resolve_dial_opts("pose", flavors.get("pose"))
    talk_opts = _cat.resolve_dial_opts("talkstyle", flavors.get("talkstyle"))
    acc_opts = _cat.resolve_dial_opts("accent", flavors.get("accent"))

    s1_parts = []
    canvas_asp = _bg.detect_canvas_aspect(brief=brief, node_aspect=str(flavors.get("aspect") or ""), camera_id=",".join(o["id"] for o in cam_opts))
    canvas_bkt = _bg.aspect_bucket(canvas_asp)
    if canvas_bkt == "9:16":
        s1_parts.append(f"Vertical {canvas_asp} framing")
    elif canvas_bkt == "1:1":
        s1_parts.append("Square 1:1 framing")
    elif canvas_bkt == "16:9":
        s1_parts.append(f"Wide {canvas_asp} framing")
    if style_opts:
        s1_parts.append(_fin.sanitize_additive_rule(style_opts[0].get("rule") or style_opts[0]["label"]))
    if lens_opts:
        s1_parts.append(_fin.sanitize_additive_rule(lens_opts[0].get("rule") or lens_opts[0]["label"]))
    if place_opts:
        s1_parts.append("inside " + _fin.sanitize_additive_rule(place_opts[0].get("rule") or place_opts[0]["label"]))
    if light_opts:
        s1_parts.append("lit by " + _fin.sanitize_additive_rule(light_opts[0].get("rule") or light_opts[0]["label"]))
    if col_opts:
        s1_parts.append(_fin.sanitize_additive_rule(col_opts[0].get("rule") or col_opts[0]["label"]))
    if cam_opts:
        s1_parts.append(_fin.sanitize_additive_rule(cam_opts[0].get("rule") or cam_opts[0]["label"]))
    clean_s1 = [p.strip().rstrip(".") for p in s1_parts if p and p.strip().rstrip(".")]
    header_s1 = "[Shot 1] " + (", ".join(clean_s1) or f"{s1_who} inside the scene") + "."

    is_sex = _dir.is_sexual(brief, str(flavors.get("explicit") or ""), str(flavors.get("wardrobe") or ""))
    no_dlg = _dlg.should_suppress_dialogue(brief, flavors=flavors, plan=plan)
    tm = str(flavors.get("talk_mode") or "auto").strip().lower()
    has_speech_ask = bool(re.search(r"\b(?:say\w*|speak\w*|talk\w*|whisper\w*|tell\w*|ask\w*|dialogue|monologue)\b", brief or "", re.I))
    cues = _dlg.pick_beat_dialogue_cues(
        brief=brief,
        talk_opt=talk_opts[0] if talk_opts else None,
        acc_opt=acc_opts[0] if acc_opts else None,
        n_beats=len(spans),
        is_sexual_scene=is_sex,
    )

    exp_clauses = _extract_beat_clauses_from_rule(exp_opts[0].get("rule") or "", lab=lab, brief=brief, explicit_id=exp_opts[0]["id"]) if exp_opts else {}
    cb_clauses = _extract_beat_clauses_from_rule(combat_opts[0].get("rule") or "", lab=lab, brief=brief) if combat_opts else {}
    pose_clauses = _extract_beat_clauses_from_rule(pose_opts[0].get("rule") or "", lab=lab, brief=brief) if pose_opts else {}
    brief_clean = _fin.sanitize_additive_rule(re.sub(r"[\"“”]", "", brief or "")).strip().rstrip(".")

    lines = [header_s1]
    shot_counter = 1
    exp_has_dlg = any("<d>" in str(o.get("rule") or "") for o in exp_opts)
    for i, (t0, t1) in enumerate(spans):
        if i > 0 and i in cuts:
            shot_counter += 1
            lines.append(f"[Shot {shot_counter}] At {_bg.stamp(t0)}, camera cuts smoothly onto the next angle.")
        if exp_clauses.get(i) or cb_clauses.get(i) or pose_clauses.get(i):
            clause = exp_clauses.get(i) or cb_clauses.get(i) or pose_clauses.get(i)
            if clause and clause[0].islower() and "<Subject" not in clause and not re.match(
                r"^(?:the|a|an|her|his|their|under|inside|in|at|on|beside|behind|against|through|from|frame|camera)\b",
                clause,
                re.I,
            ):
                clause = f"{s1_who} {clause}"
        elif i == 0 and brief_clean:
            if subs and "<Subject" not in brief_clean:
                clause = f"{s1_who}: {brief_clean}"
            else:
                clause = brief_clean
        elif i == 0:
            clause = f"{s1_who} opens the staged movement with clear posture and gaze"
        elif i < len(spans) - 1:
            clause = f"{s1_who} carries the action forward smoothly with clear weight shift and gesture"
        else:
            clause = f"{s1_who} completes the motion cleanly and settles into a steady closing hold"

        dlg_tail = ""
        want_beat_dlg = (not no_dlg) and (bool(q_map.get(i)) or tm == "talk_all" or bool(talk_opts) or bool(acc_opts) or has_speech_ask or exp_has_dlg)
        if want_beat_dlg:
            q_line = (q_map.get(i) or [cues[i]])[0]
            tgt_lang = _dlg.detect_target_language(brief, acc_opts[0] if acc_opts else None)
            acc_tag = tgt_lang if tgt_lang != "English" else ((acc_opts[0].get("accent") or acc_opts[0].get("lang") or "English") if acc_opts else "English")
            tone_tag = talk_opts[0]["label"].split("(")[0].strip().lower() if talk_opts else "natural tone"
            au_ref = f" using {audios[0]['label']}" if audios else ""
            dlg_tail = f" (DIALOGUE) {primary_speaker} (S1) speaks{au_ref}: <d>[{acc_tag}, {tone_tag}] {q_line}</d>"
        lines.append(f"At {_bg.stamp(t0)}-{_bg.stamp(t1)}, {clause.rstrip('.')}.{dlg_tail}")
    return "\n".join(lines)


def build_keyframe_prep_prompt(brief: str, flavors: dict | None, lab: dict | None = None) -> str:
    """Build a crisp Start-Frame Prep still-image prompt (T2I/I2I) aligned with active SandTie dials & refs."""
    flavors = flavors or {}
    lab = lab or {}
    parts = []
    asp = _bg.detect_canvas_aspect(brief=brief, node_aspect=str(flavors.get("aspect") or ""))
    asp_bkt = _bg.aspect_bucket(asp)
    if asp_bkt == "9:16":
        parts.append(f"Vertical {asp} cinematic frame")
    elif asp_bkt == "1:1":
        parts.append("Square 1:1 cinematic frame")
    elif asp_bkt == "16:9":
        parts.append(f"Widescreen {asp} cinematic still")
    for key in ("style", "lens", "colour", "light", "place"):
        opts = _cat.resolve_dial_opts(key, flavors.get(key))
        if opts and opts[0].get("rule"):
            parts.append(_fin.sanitize_additive_rule(opts[0]["rule"]))
    for s_n in sorted((lab.get("subjects") or {}).keys()):
        meta = lab["subjects"][s_n]
        pics = [p for p in (lab.get("pictures") or []) if p.get("subject") == s_n]
        desc = next((p.get("desc") for p in pics if p.get("desc")), "")
        cname = meta.get("char_name") or meta.get("name") or f"Subject {s_n}"
        if desc:
            parts.append(f"{cname}: {_fin.sanitize_additive_rule(desc)}")
    ward = _cat.resolve_dial_opts("wardrobe", flavors.get("wardrobe"))
    if ward and ward[0].get("rule"):
        parts.append("wearing " + _fin.sanitize_additive_rule(ward[0]["rule"]))
    pose = _cat.resolve_dial_opts("pose", flavors.get("pose"))
    if pose and pose[0].get("rule"):
        parts.append(_fin.sanitize_additive_rule(pose[0]["rule"]))
    if brief:
        parts.append(_fin.sanitize_additive_rule(brief))
    return ". ".join(p.rstrip(".") for p in parts if p) + "."


def build_cpu_tie_block(
    brief: str,
    *,
    lab: dict,
    duration_s: float,
    flavors: dict | None = None,
    extracted_video: dict | None = None,
) -> dict:
    """Instant 0-LLM / 0-VRAM assembled H3 block built deterministically from active dials + wired refs."""
    flavors = flavors or {}
    mode = _std.mode_for(lab)
    spans, q_map, cuts = _bg.build_beat_grid(
        duration_s, brief=brief, camera_id=str(flavors.get("camera") or ""),
        explicit_id=str(flavors.get("explicit") or ""), flavors=flavors,
    )
    skel = build_skeleton_text(spans, q_map, cuts, lab, brief=brief, flavors=flavors, extracted_video=extracted_video)
    amb_opts = _cat.resolve_dial_opts("ambience", flavors.get("ambience"))
    music_opts = _cat.resolve_dial_opts("music", flavors.get("music"))
    raw_music = _cat.parse_multi_ids(flavors.get("music"))
    snd = ", ".join(_fin.sanitize_additive_rule(o.get("rule") or "") for o in amb_opts if o.get("rule")) or "Natural quiet room tone and tactile contact foley."
    mus = "N/A" if ("none" in raw_music or not music_opts) else (", ".join(_fin.sanitize_additive_rule(o.get("rule") or "") for o in music_opts if o.get("rule")) or "N/A")

    if mode == "Ref2VA":
        has_aud = bool(lab.get("audios"))
        tag = "[reference generation + audio reference]" if has_aud else "[reference generation]"
        sub_labels = [f"<Subject {sn}>" for sn in sorted((lab.get("subjects") or {}).keys())]
        summ = f"{tag} {' and '.join(sub_labels) or 'Subject'} performs the brief ({_fin.sanitize_additive_rule(brief or 'scene action')})."
        raw_blk = f"subject_definitions:\n\n\nsummary:\n{summ}\n\nretention_analysis:\n\n\ndetailed_description:\n{skel}\n\noverall_soundscape:\n{snd}\n\nnon_diegetic_music:\n{mus}"
    else:
        raw_blk = f"integrated_multimodal_description:\n{skel}\n\noverall_soundscape:\n{snd}\n\nnon_diegetic_music:\n{mus}"

    silent = _dlg.should_suppress_dialogue(brief, flavors=flavors)
    blk = _fin.finish_block(raw_blk, mode=mode, lab=lab, duration_s=duration_s, silent=silent, brief=brief, flavors=flavors)
    out_fmt = str(flavors.get("output_format") or "h3_auto")
    formatted = _fin.format_h3_output(blk, output_format=out_fmt, duration_s=duration_s)
    errs = _std.contract_errors(blk, mode=mode, lab=lab, duration_s=duration_s) if out_fmt == "h3_auto" else []
    return {"ok": True, "stage": "cpu", "mode": mode, "block": formatted, "plan": skel, "skeleton": skel, "errors": errs, "warnings": []}


def _extract_json_field(raw: str, key: str) -> str:
    txt = str(raw or "").strip()
    try:
        obj = _pl._parse_obj(txt)
        if isinstance(obj, dict) and obj.get(key):
            return str(obj[key]).strip()
    except Exception:
        pass
    m = re.search(rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"\\])*)"', txt, re.S)
    if m:
        try:
            return json.loads(f'"{m.group(1)}"')
        except Exception:
            return m.group(1).replace("\\n", "\n").replace('\\"', '"')
    return txt


async def run_sandtie_write(
    stage: str,
    brief: str,
    *,
    complete_fn,
    ref_plan: str = "",
    duration_s: float = 10.0,
    images: list | None = None,
    start_image: str | None = None,
    start_image_path: str = "",
    plan: str = "",
    voice_files: tuple | list = (),
    flavors: dict | None = None,
    extracted_video: dict | None = None,
    prev_hop_context: str = "",
    resolve_file_fn=None,
) -> dict:
    flavors = dict(flavors or {})
    brief = _refs.clean_user_brief(brief)
    try:
        lab = _refs.sandtie_labels(ref_plan, voice_files=voice_files)
    except Exception as exc:
        return {"ok": False, "stage": stage, "errors": [f"ref_plan parse failed: {exc}"]}

    mode = _std.mode_for(lab)
    out_fmt = str(flavors.get("output_format") or "h3_auto")
    eye_scan = bool(flavors.get("eye_scan", flavors.get("vision_scan", True)))
    ward_opts_init = _cat.resolve_dial_opts("wardrobe", flavors.get("wardrobe"))
    ward_opt = ward_opts_init[0] if ward_opts_init else None
    char_opts_init = _cat.resolve_dial_opts("character", flavors.get("character"))

    if stage not in ("skeleton", "cpu") and eye_scan and resolve_file_fn and complete_fn is not None:
        from . import vision_cv as _vcv
        for p in lab.get("pictures") or []:
            if p.get("file"):
                fpath = resolve_file_fn(p["file"])
                if fpath:
                    exp_ret = str(p.get("explicit_retention") or "").strip().lower()
                    raw_d = str(p.get("raw_desc") or "").strip().lower()
                    role = "subject" if p.get("subject") is not None else ("prop" if exp_ret == "prop" or raw_d.startswith("prop:") else ("place" if raw_d.startswith(("set:", "place:", "room:")) and not flavors.get("place") else ("subject" if _refs.is_likely_person_ref(p, brief=brief, flavors=flavors) else "auto")))
                    scanned = await _vcv.scan_reference_file(fpath, role, complete_fn)
                    if scanned:
                        if p.get("subject") is None and _refs.is_likely_person_ref(p, scanned, brief=brief, flavors=flavors):
                            ex = sorted((lab.get("subjects") or {}).keys())
                            ns = 1 if 1 not in ex else (ex[-1] + 1)
                            p["subject"] = ns
                            p["retention"] = "fully_preserved"
                            cn = _refs.extract_char_name_from_tag(p.get("tag") or "")
                            lab.setdefault("subjects", {})[ns] = {"name": cn, "char_name": cn, "box_name": "", "locked": "", "context": "", "pictures": [p["label"]], "audios": []}
                        cleaned = _refs.clean_subject_scan_desc(scanned) if p.get("subject") is not None else re.sub(r"^(?:Set|Prop):\s*", "", scanned, flags=re.I).strip()
                        if cleaned and (not p.get("desc") or _refs.is_studio_backdrop_text(p.get("desc") or "")):
                            p["desc"] = cleaned
                        if p.get("file") and p.get("source", "image") != "refmod":
                            try:
                                _refs.upsert_ref_bank_item({
                                    "file": p["file"],
                                    "source": p.get("source") or "image",
                                    "tag": p.get("tag") or "",
                                    "role": "subject" if p.get("subject") is not None else ("prop" if role == "prop" else "place"),
                                    "desc": p.get("desc") or cleaned,
                                }, user_edited=False)
                            except Exception:
                                pass

    updated_ref_plan = _refs.sync_promoted_ref_plan(ref_plan, lab)
    mode = _std.mode_for(lab)

    # Apply wardrobe override onto Subject descriptions (clean natural prose, zero UI emoji/labels!)
    if ward_opt and lab.get("subjects"):
        w_rule_clean = _fin.sanitize_additive_rule(ward_opt.get("rule") or _clean_ui_label(ward_opt.get("label") or ""))
        for s_n, s_meta in (lab.get("subjects") or {}).items():
            if s_n == 1 or "nude_both_partners" in _cat.parse_multi_ids(flavors.get("wardrobe")):
                for p in lab.get("pictures") or []:
                    if p.get("subject") == s_n and w_rule_clean:
                        base_d = str(p.get("desc") or "")
                        anc = base_d.split("Wearing ")[0].strip() if "Wearing " in base_d else base_d
                        p["desc"] = f"{anc} {w_rule_clean}".strip() if anc else w_rule_clean

    spans, q_map, cuts = _bg.build_beat_grid(
        duration_s, brief=brief, camera_id=str(flavors.get("camera") or ""),
        explicit_id=str(flavors.get("explicit") or ""), flavors=flavors,
    )
    skel = build_skeleton_text(spans, q_map, cuts, lab, brief=brief, flavors=flavors, extracted_video=extracted_video, plan=plan)
    dur_adv = _bg.duration_advisory(duration_s, flavors=flavors)
    dom_conflicts = _cat.check_domain_conflicts(flavors)

    if stage == "skeleton":
        return {"ok": True, "stage": "skeleton", "mode": mode, "skeleton": skel, "plan": skel, "errors": [], "warnings": [], "duration_advisory": dur_adv, "domain_conflicts": dom_conflicts}

    if stage == "keyframe" or out_fmt == "h3_keyframe":
        kf = build_keyframe_prep_prompt(brief, flavors, lab=lab)
        return {"ok": True, "stage": "keyframe", "mode": mode, "block": kf, "plan": skel, "skeleton": skel, "errors": [], "warnings": [], "duration_advisory": dur_adv}

    if stage == "cpu" or complete_fn is None:
        res_cpu = build_cpu_tie_block(brief, lab=lab, duration_s=duration_s, flavors=flavors, extracted_video=extracted_video)
        res_cpu["duration_advisory"] = dur_adv
        res_cpu["domain_conflicts"] = dom_conflicts
        if updated_ref_plan != ref_plan:
            res_cpu["updated_ref_plan"] = updated_ref_plan
        return res_cpu

    if stage == "dialogue":
        cur_blk = str(flavors.get("current_block") or plan or "").strip()
        if not cur_blk:
            return {"ok": False, "stage": "dialogue", "errors": ["No existing prompt block to refresh dialogue inside."]}
        talk_opts = _cat.resolve_dial_opts("talkstyle", flavors.get("talkstyle"))
        acc_opts = _cat.resolve_dial_opts("accent", flavors.get("accent"))
        tgt_lang_d = _dlg.detect_target_language(brief, acc_opts[0] if acc_opts else None)
        lang_hint_d = (
            f"Target Language ({tgt_lang_d}): Write ALL spoken words inside `<d>[{tgt_lang_d}, ...] ...</d>` strictly in authentic native {tgt_lang_d} script/characters (never English or romanized romaji; sample: `{_dlg.native_sample_for(tgt_lang_d)}`).\n"
            if tgt_lang_d != "English"
            else (f"Accent/Language: {acc_opts[0].get('accent') or acc_opts[0].get('lang')}\n" if acc_opts else "")
        )
        dlg_prompt = (
            "Rewrite ONLY the spoken `<d>[...] ...</d>` lines inside the prompt block below so they feel fresh, character-specific, and free of clichés, "
            "keeping EVERY physical action, pose, hand role, timestamp, camera instruction, and label unchanged.\n"
            + (f"Speech register: {talk_opts[0]['label']} ({talk_opts[0].get('words','')})\n" if talk_opts else "")
            + lang_hint_d
            + f"\nReturn JSON `{{\"block\": \"...\"}}`.\n\n{cur_blk}"
        )
        raw_d = await complete_fn([{"role": "system", "content": "You refresh spoken dialogue inside MiniMax H3 prompts without altering visual staging."}, {"role": "user", "content": dlg_prompt}], temperature=0.95, max_tokens=2400)
        new_blk = _fin.finish_block(_extract_json_field(raw_d, "block"), mode=mode, lab=lab, duration_s=duration_s, silent=False, brief=brief, flavors=flavors)
        return {"ok": True, "stage": "dialogue", "mode": mode, "block": new_blk, "plan": new_blk, "errors": _std.contract_errors(new_blk, mode=mode, lab=lab, duration_s=duration_s)}

    # Build user turn for `plan`, `write`, or `fast`
    llm_stage = "write" if stage == "fast" else stage
    flavor_lines, resolved_cam = build_flavor_facts(brief, flavors, spans, plan=plan, lab=lab, prev_hop_context=prev_hop_context)
    time_tied = bool(flavors.get("time_tied", flavors.get("fast_engine", True)))

    lines = [
        f"Stage: {llm_stage}.",
        f"Mode: {mode}{' + start image' if start_image else ''}.",
        f"Duration: {float(duration_s):.2f} seconds.",
    ]
    if mode == "Ref2VA":
        lines.append("Labels handed to the H3 model (use ONLY these):")
        lines += ["- " + ln for ln in _refs.label_lines(lab)]
    else:
        lines.append("No reference labels (T2VA).")
    if start_image:
        lines.append("Start frame attached as last image: describe [Shot 1] cleanly from it without a label.")
    if str(prev_hop_context or "").strip():
        lines.append("Previous hop context (continue cleanly at [Shot 1] start):")
        lines.append(_pl.fence(prev_hop_context, "previous_hop_end"))
    lines.append("Active SandTie Directives & Continuity Laws:")
    lines += ["- " + fl for fl in flavor_lines]
    if time_tied:
        lines.append("Time-Tied Continuity Flow (preserve timestamps cleanly as smooth momentum bridges without pausing action between beats):")
        lines.append(_pl.fence(skel, "beat_skeleton"))
    lines.append("Scene Brief:")
    lines.append(_pl.fence(brief or "Perform the staged scene cleanly.", "scene_brief"))
    if llm_stage == "write" and plan:
        lines.append("Approved Storyboard (expand cleanly into full H3 prompt):")
        lines.append(_pl.fence(plan, "approved_plan"))

    user_content: object = "\n".join(lines)
    if images or start_image:
        parts: list[dict] = [{"type": "text", "text": str(user_content)}]
        for im in images or []:
            if isinstance(im, dict) and im.get("data_url"):
                parts.append({"type": "image_url", "image_url": {"url": im["data_url"]}})
        if start_image:
            parts.append({"type": "image_url", "image_url": {"url": start_image}})
        user_content = parts

    raw_out = await complete_fn([
        {"role": "system", "content": FAST_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ], temperature=0.85, max_tokens=2800)

    silent = _dlg.should_suppress_dialogue(brief, flavors=flavors, plan=plan)
    acc_opts_rw = _cat.resolve_dial_opts("accent", flavors.get("accent"))
    target_lang_rw = _dlg.detect_target_language(brief, acc_opts_rw[0] if acc_opts_rw else None)
    if llm_stage == "plan":
        cleaned_plan = _fin.clean_plan_output(_extract_json_field(raw_out, "plan"), duration_s=duration_s, silent=silent)
        if cleaned_plan and not silent and target_lang_rw != "English" and _dlg.language_script_missing(cleaned_plan, target_lang_rw):
            try:
                fix_plan_msg = (
                    f"Language is set to {target_lang_rw}, yet `<d>...</d>` dialogue in your storyboard used English/romanization. "
                    f"Translate EVERY spoken line inside `<d>[{target_lang_rw}, ...] ...</d>` into natural native {target_lang_rw} script/characters "
                    f"(sample: `{_dlg.native_sample_for(target_lang_rw)}`), keeping timestamps and action descriptions intact.\n"
                    f"Return JSON `{{\"plan\": \"...\"}}`.\n\n{cleaned_plan}"
                )
                raw_p_fix = await complete_fn([
                    {"role": "system", "content": FAST_SYSTEM_PROMPT},
                    {"role": "user", "content": fix_plan_msg},
                ], temperature=0.45, max_tokens=2400)
                cand_plan = _fin.clean_plan_output(_extract_json_field(raw_p_fix, "plan"), duration_s=duration_s, silent=silent)
                if cand_plan and not _dlg.language_script_missing(cand_plan, target_lang_rw):
                    cleaned_plan = cand_plan
            except Exception:
                pass
        return {
            "ok": bool(cleaned_plan), "stage": "plan", "mode": mode,
            "plan": cleaned_plan, "skeleton": skel, "errors": [] if cleaned_plan else ["Empty storyboard returned."],
            "warnings": [], "duration_advisory": dur_adv, "domain_conflicts": dom_conflicts,
            **({"updated_ref_plan": updated_ref_plan} if updated_ref_plan != ref_plan else {}),
        }

    raw_blk = _extract_json_field(raw_out, "block")
    blk = _fin.finish_block(raw_blk, mode=mode, lab=lab, duration_s=duration_s, silent=silent, brief=brief, flavors=flavors)

    # Optional Pass-2 Double-Knot refinement (also triggers automatically when non-English <d> script needs repair!)
    double_knot = bool(flavors.get("double_knot", flavors.get("pass2_refine", True)))
    need_lang_repair = bool(blk and not silent and target_lang_rw != "English" and _dlg.language_script_missing(blk, target_lang_rw))
    if (double_knot or need_lang_repair) and blk:
        anal_sc = _dir.is_anal(brief, explicit_id=str(flavors.get("explicit") or ""), plan=plan)
        rear_sc = _dir.is_rear_facing(brief, str(flavors.get("explicit") or ""), plan=plan, camera_id=resolved_cam)
        os_sc = _dir.is_over_shoulder(brief, explicit_id=str(flavors.get("explicit") or ""), camera_id=resolved_cam, plan=plan)
        mo_sc = _dir.is_mouth_occupied(brief, explicit_id=str(flavors.get("explicit") or ""), plan=plan)
        pov_v = _dir.resolve_pov_mode(brief, flavors=flavors, plan=plan)
        checklist = _fin.build_pass2_audit_checklist(
            brief, flavors, lab,
            is_pov=pov_v in ("male", "female", "on"), pov_val=pov_v,
            rear_scene=rear_sc, over_shoulder=os_sc, mouth_occupied=mo_sc,
            anal_scene=anal_sc, no_dialogue=silent, flavor_lines=flavor_lines, plan=plan,
            prev_hop_context=prev_hop_context,
        )
        if checklist:
            p2_user = "Audit Checklist:\n" + "\n".join(f"- {c}" for c in checklist) + "\n\nPass-1 Draft:\n" + blk
            try:
                raw_p2 = await complete_fn([
                    {"role": "system", "content": _fin.PASS2_REFINE_SYSTEM_PROMPT},
                    {"role": "user", "content": p2_user},
                ], temperature=0.45, max_tokens=2800)
                refined = _extract_json_field(raw_p2, "block")
                if refined and len(refined) > 80:
                    blk = _fin.finish_block(refined, mode=mode, lab=lab, duration_s=duration_s, silent=silent, brief=brief, flavors=flavors)
            except Exception:
                pass

    errs = _std.contract_errors(blk, mode=mode, lab=lab, duration_s=duration_s)
    warnings: list[str] = []
    if len(blk) > _fin.MAX_H3_CHARS:
        warnings.append(f"Prompt is {len(blk)} chars (above H3's 7,000-char limit) — consider tightening beats.")
    if dur_adv:
        warnings.append(dur_adv["reason"])
    if dom_conflicts:
        a_lbl = dom_conflicts[0]["a"][3]
        b_lbl = dom_conflicts[0]["b"][3]
        warnings.append(f"Domain mismatch smoothed: {a_lbl} ({dom_conflicts[0]['a'][2]}) vs {b_lbl} ({dom_conflicts[0]['b'][2]}).")

    desc_fld = "detailed_description:" if mode == "Ref2VA" else "integrated_multimodal_description:"
    desc_val = _std._field(blk, desc_fld) or ""
    out_plan = "\n".join(ln.strip() for ln in desc_val.splitlines() if re.match(r"^(?:\[Shot\s+\d+\]|At\s+\d{2}:\d{2}\.\d{3})", ln.strip())).strip() or skel
    formatted = _fin.format_h3_output(blk, output_format=out_fmt, duration_s=duration_s)

    return {
        "ok": len(errs) == 0,
        "stage": stage,
        "mode": mode,
        "block": formatted,
        "plan": out_plan,
        "skeleton": skel,
        "errors": errs,
        "warnings": warnings,
        "duration_advisory": dur_adv,
        "domain_conflicts": dom_conflicts,
        **({"updated_ref_plan": updated_ref_plan} if updated_ref_plan != ref_plan else {}),
    }
