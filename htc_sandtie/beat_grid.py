"""Beat timing grids, aspect resolution, and H3/LoopForge camera & FX trajectory laws."""
from __future__ import annotations

import re

from . import catalogs as _cat
from . import dialogue as _dlg
from . import director_cards as _dir

parse_multi_ids = _cat.parse_multi_ids


def get_dial_mode(flavors: dict | None, key: str, default: str = "sequence") -> str:
    dm = (flavors or {}).get("dial_modes")
    if isinstance(dm, dict):
        v = str(dm.get(key) or "").strip().lower()
        if v in ("sequence", "blend", "split"):
            return v
    return default


def allocate_stages_to_spans(opts: list[dict], spans: list[tuple[float, float]]) -> list[tuple[dict, list[tuple[int, str]]]]:
    if not opts or not spans:
        return []
    k = len(opts)
    m = len(spans)
    out = []
    if k <= m:
        base, rem = divmod(m, k)
        cur = 0
        for idx, opt in enumerate(opts):
            take = base + (1 if idx < rem else 0)
            b_list = [(j + 1, f"At {stamp(spans[j][0])}-{stamp(spans[j][1])}") for j in range(cur, cur + take)]
            out.append((opt, b_list))
            cur += take
    else:
        for idx, opt in enumerate(opts):
            j = min(m - 1, idx * m // k)
            out.append((opt, [(j + 1, f"At {stamp(spans[j][0])}-{stamp(spans[j][1])}")]))
    return out


def stamp(sec: float) -> str:
    s = max(0.0, float(sec or 0.0))
    m = int(s // 60)
    r = s - m * 60
    return f"{m:02d}:{r:06.3f}"


def aspect_bucket(aspect: str = "") -> str:
    s = str(aspect or "").strip()
    m = re.search(r"(\d+)\s*:\s*(\d+)", s)
    if m:
        rw, rh = int(m.group(1)), int(m.group(2))
        if rw > 0 and rh > 0:
            if rh > rw:
                return "9:16"
            if rw > rh:
                return "16:9"
            return "1:1"
    if re.search(r"\b(?:vertical|portrait)\b", s, re.I):
        return "9:16"
    if re.search(r"\b(?:horizontal|landscape|widescreen)\b", s, re.I):
        return "16:9"
    if re.search(r"\bsquare\b", s, re.I):
        return "1:1"
    return ""


def detect_canvas_aspect(brief: str = "", node_aspect: str = "", camera_id: str = "", plan: str = "", plan_hint: str = "") -> str:
    na = str(node_aspect or "").strip()
    m = re.search(r"(\d+)\s*:\s*(\d+)", na)
    if m:
        rw, rh = int(m.group(1)), int(m.group(2))
        if rw > 0 and rh > 0:
            return f"{rw}:{rh}"
    if re.search(r"\b(?:vertical|portrait)\b", na, re.I):
        return "9:16"
    if re.search(r"\b(?:horizontal|landscape|widescreen)\b", na, re.I):
        return "16:9"
    if re.search(r"\bsquare\b", na, re.I):
        return "1:1"
    combined = f"{brief or ''}\n{plan or ''}\n{plan_hint or ''}"
    m2 = re.search(r"\b(21:9|16:9|3:2|4:3|5:4|1:1|4:5|3:4|2:3|9:16|9:21)\b", combined)
    if m2:
        return m2.group(1)
    if re.search(r"\b(?:vertical|portrait)\b", combined, re.I):
        return "9:16"
    if re.search(r"\b(?:horizontal|landscape|widescreen)\b", combined, re.I):
        return "16:9"
    if camera_id in ("portrait_vertical_stack", "selfie_arm", "selfie_high_overhead", "selfie_shoulder", "elevator_3stop", "yoyo_tilt", "pedestal_up", "pedestal_down", "tilt_up", "tilt_down"):
        return "9:16"
    return ""


def duration_advisory(duration_s: float, flavors: dict | None = None) -> dict | None:
    """Advise when selected staging/combat/camera presets need 13-15 s vs the active duration."""
    flavors = flavors or {}
    d_sec = float(duration_s or 10.0)
    recommended: list[tuple[str, str, str]] = []
    for k in ("explicit", "combat", "camera", "pose"):
        for opt in _cat.resolve_dial_opts(k, flavors.get(k)):
            dur = _cat.recommend_option_duration(k, opt)
            db = dur.get("duration_best") or ""
            m = re.match(r"(\d+)\s*-\s*(\d+)", db)
            if m:
                lo = float(m.group(1))
                if d_sec + 0.35 < lo:
                    recommended.append((k, opt["label"], db))
    if not recommended:
        return None
    top_k, top_lbl, top_db = recommended[0]
    return {
        "best_length": top_db,
        "reason": f"'{top_lbl}' ({top_k}) lands smoothest at {top_db}; current clip is {d_sec:.1f} s.",
        "items": recommended,
    }


def build_beat_grid(
    duration_s: float,
    brief: str = "",
    camera_id: str = "",
    quotes: list[str] | None = None,
    explicit_id: str = "",
    flavors: dict | None = None,
) -> tuple[list[tuple[float, float]], dict[int, list[str]], list[int]]:
    """Compute [(t0, t1), ...] beat spans covering 0..duration_s, quote placements, and hard-cut indices."""
    T = round(max(2.0, float(duration_s or 10.0)), 3)
    qs = list(quotes if quotes is not None else _dlg.extract_quotes(brief))
    flavors = flavors or {}
    cids = [x.lower() for x in parse_multi_ids(camera_id or flavors.get("camera"))]
    eids = [x.lower() for x in parse_multi_ids(explicit_id or flavors.get("explicit"))]
    cid = cids[0] if cids else ""
    eid = eids[0] if eids else ""

    max_seq_picks = max(len(cids), len(eids), 1)
    for k_dial in ("style", "combat", "place", "wardrobe", "character", "pose", "fetish", "era", "tv_show", "light", "colour", "lens", "fx", "talkstyle", "accent", "ambience", "music"):
        if get_dial_mode(flavors, k_dial, "sequence") == "sequence":
            max_seq_picks = max(max_seq_picks, len(parse_multi_ids(flavors.get(k_dial))))

    if cid == "jumpcut_pose_burst" and len(cids) == 1 and T >= 5.0:
        c1, c2, c3, c4 = 0.65, 1.30, 1.95, 2.60
        mid = round(2.60 + (T - 2.60) * 0.5, 2)
        spans = [(0.0, c1), (c1, c2), (c2, c3), (c3, c4), (c4, mid), (mid, T)]
        return spans, ({len(spans) - 1: qs} if qs else {}), [1, 2, 3, 4]

    if cid == "jumpcut_z_steps" and len(cids) == 1 and T >= 5.0:
        c1, c2, c3, c4 = 0.70, 1.40, 2.10, 2.80
        mid = round(2.80 + (T - 2.80) * 0.5, 2)
        spans = [(0.0, c1), (c1, c2), (c2, c3), (c3, c4), (c4, mid), (mid, T)]
        return spans, ({len(spans) - 1: qs} if qs else {}), [1, 2, 3, 4]

    if (cid in ("matchcut_hand_outfit", "coverage_match_on_action") or eid == "cam_cut_front_to_rear") and max_seq_picks <= 1 and T >= 4.5:
        cut_t = round(T * 0.5, 2) if eid == "cam_cut_front_to_rear" or cid == "coverage_match_on_action" else round(min(2.6, T * 0.32), 2)
        mid_t = round(cut_t + (T - cut_t) * 0.5, 2)
        spans = [(0.0, cut_t), (cut_t, T)] if eid == "cam_cut_front_to_rear" else [(0.0, cut_t), (cut_t, mid_t), (mid_t, T)]
        return spans, ({1: qs} if qs else {}), [1]

    m_ask = re.search(r"\b(\d{1,2})\s+(?:different\s+|quick\s+|separate\s+|hard\s+)?(?:shots?|cuts?|angles?|positions?)\b", brief or "", re.I)
    asked_shots = int(m_ask.group(1)) if m_ask else 0

    is_single_continuous_ask = (
        any(e.startswith("cont_") or e == "deepthroat_to_smile_facial" for e in eids)
        or any(c in ("oner", "static_close", "push_in", "slow_push", "copilot_hand_tie_calm_join") for c in cids)
        or bool(re.search(r"\b(?:one\s+(?:continuous|unbroken)\s+(?:shot|take)|single\s+(?:continuous\s+|unbroken\s+)?(?:shot|take)|zero\s+cuts|no\s+cuts)\b", brief or "", re.I))
    )
    non_climax_eids = [e for e in eids if not e.startswith("climax_")]
    has_rear_pick = any(e in _dir.REAR_EXPLICIT_IDS for e in non_climax_eids)
    has_front_pick = any(e not in _dir.REAR_EXPLICIT_IDS for e in non_climax_eids)
    has_multi_pos_picks = (
        not is_single_continuous_ask
        and len(non_climax_eids) >= 2
        and (has_rear_pick or has_front_pick)
        and (has_rear_pick != has_front_pick or len(non_climax_eids) >= 2)
    )
    exp_has_cuts = any(re.search(r"\[\s*Shot\s+2\s*\]", str(o.get("rule") or ""), re.I) for o in _cat.resolve_dial_opts("explicit", explicit_id))
    is_multi_pos = (
        any(e.startswith("multi_pos_") for e in eids)
        or exp_has_cuts
        or has_multi_pos_picks
        or _dir.is_multi_position_scene(brief, explicit_id=explicit_id)
    )

    # Check if an active single rule carries explicit millisecond `At MM:SS.mmm-MM:SS.mmm` spans
    ms_spans: list[tuple[float, float]] = []
    ms_cuts: list[int] = []
    if max_seq_picks <= 1 and asked_shots == 0:
        for dk in ("explicit", "combat", "pose"):
            opts = _cat.resolve_dial_opts(dk, flavors.get(dk))
            if len(opts) == 1:
                rtxt = str(opts[0].get("rule") or "")
                matches_ms = list(re.finditer(r"\bAt\s+(\d+):(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+):(\d+(?:\.\d+)?)", rtxt, re.I))
                if len(matches_ms) >= 2:
                    ms_spans = [
                        (int(m.group(1)) * 60 + float(m.group(2)), int(m.group(3)) * 60 + float(m.group(4)))
                        for m in matches_ms
                    ]
                    prev_pos = 0
                    for idx_m, m in enumerate(matches_ms):
                        seg_before = rtxt[prev_pos:m.start()]
                        if idx_m > 0 and re.search(r"\[\s*Shot\s+[2-9]\d*\s*\]", seg_before, re.I):
                            ms_cuts.append(idx_m)
                        prev_pos = m.end()
                    break

    # Check if brief / preset naturally expects hard cuts
    viral_cut_cams = {
        "multi_angle_action_close", "shot_reverse", "whip_pan_transition", "match_cut_motion",
        "cam_viral_dutch_90roll_wipe_cuts", "cam_beat_drop_punch_wide_combo", "cam_palm_cover_lens_reveal_snap",
        "cam_whip_pan_beat_snap_cut", "graphic_match_cut", "smash_cut_contrast",
        "cam_distant_wide_master_to_hardcut_closeup",
    }
    multi_cut_cam = (
        len(cids) >= 2
        or any(c in viral_cut_cams for c in cids)
        or is_multi_pos
        or asked_shots >= 2
    )

    if ms_spans:
        raw_durs = [max(0.4, b - a) for a, b in ms_spans]
        tot = sum(raw_durs) or 1.0
        spans = []
        cur = 0.0
        for i, d_seg in enumerate(raw_durs):
            nxt = T if i == len(raw_durs) - 1 else round(min(T - 0.4 * (len(raw_durs) - 1 - i), cur + (d_seg / tot) * T), 3)
            if nxt <= cur:
                nxt = round(min(T, cur + 0.4), 3)
            spans.append((cur, nxt))
            cur = nxt
    else:
        if T < 6.4:
            n_beats = 2 if max_seq_picks <= 2 else min(3, max_seq_picks)
        elif T <= 11.4:
            # 10-11s sweet spot: 3 cohesive beats (slightly shorter Beat 1 so Beat 2-3 never rush!)
            n_beats = max(3, min(4, max_seq_picks if max_seq_picks <= 4 else 3))
        else:
            n_beats = max(3, min(4, max_seq_picks if max_seq_picks <= 4 else 4))

        if asked_shots >= 2 and asked_shots <= 6 and T >= asked_shots * 2.0:
            n_beats = asked_shots

        # Weighted spans for 10-12s continuous vs climax pacing (fixes rushed Beat 2-3 transitions)
        if n_beats == 3 and 8.5 <= T <= 11.4 and not multi_cut_cam:
            t1 = round(T * 0.28, 2)
            t2 = round(T * 0.66, 2)
            spans = [(0.0, t1), (t1, t2), (t2, T)]
        elif n_beats == 2:
            t1 = round(T * 0.45, 2)
            spans = [(0.0, t1), (t1, T)]
        else:
            step = T / n_beats
            spans = []
            cur = 0.0
            for i in range(n_beats):
                nxt = T if i == n_beats - 1 else round((i + 1) * step, 2)
                spans.append((cur, nxt))
                cur = nxt

    cuts: list[int] = []
    if not is_single_continuous_ask and (multi_cut_cam or ms_cuts):
        if ms_cuts:
            cuts = ms_cuts
        elif (any(e.startswith("multi_pos_") for e in eids) or exp_has_cuts) and len(spans) >= 2:
            cuts = list(range(1, len(spans)))
        elif len(cids) >= 2 and get_dial_mode(flavors, "camera", "sequence") == "sequence":
            alloc = allocate_stages_to_spans([{"id": x} for x in cids], spans)
            cuts = [b_list[0][0] - 1 for _, b_list in alloc[1:] if b_list and b_list[0][0] > 1]
        elif asked_shots >= 2:
            cuts = list(range(1, len(spans)))
        elif any(c in ("multi_angle_action_close", "shot_reverse", "cam_viral_dutch_90roll_wipe_cuts", "cam_beat_drop_punch_wide_combo", "cam_palm_cover_lens_reveal_snap") for c in cids) and len(spans) >= 2:
            cuts = list(range(1, len(spans)))
        elif any(c in ("graphic_match_cut", "smash_cut_contrast", "cam_whip_pan_beat_snap_cut", "whip_pan_transition", "match_cut_motion", "cam_distant_wide_master_to_hardcut_closeup") for c in cids) and len(spans) >= 2:
            cuts = [1 if len(spans) == 2 else (len(spans) - 1 if any(c == "cam_distant_wide_master_to_hardcut_closeup" for c in cids) else (len(spans) // 2))]

    q_map: dict[int, list[str]] = {}
    if qs:
        if len(qs) == 1:
            q_map[0 if len(spans) <= 2 else 1] = [qs[0]]
        else:
            for idx, q in enumerate(qs):
                b = min(len(spans) - 1, idx)
                q_map.setdefault(b, []).append(q)
    return spans, q_map, cuts


def camera_trajectory_plan(
    brief: str,
    camera_id: str,
    spans: list[tuple[float, float]],
    is_pov: bool = False,
    has_bg_plate: bool = False,
    is_combat: bool = False,
) -> str:
    """Emit H3-grounded motion-primitive trajectory laws (Open-End Range, LoopForge, Zero Rig Hardware)."""
    if is_pov or not spans:
        return ""
    ts_list = [f"At {stamp(a)}-{stamp(b)}" for a, b in spans]
    n = len(ts_list)
    cids = parse_multi_ids(camera_id)
    cid = cids[0].lower() if cids else ""
    amp_boost = " with large amplitude across the full shot" if has_bg_plate else ""
    pace_adv = "fast and briskly" if is_combat else "smoothly"
    speed_word = "fast" if is_combat else "steady"

    asks_top_down = cid in ("pedestal_down", "tilt_down", "finger_follow_macro") or bool(
        re.search(r"\b(?:from\s+(?:her|his|their|the)?\s*(?:head|face|eyes|lips)\b.*?\b(?:down\s+)?to\s+(?:her|his|their|the)?\s*(?:hips|legs|feet|heels|ankles)|top[- ]to[- ]bottom)\b", brief or "", re.I)
    )
    if asks_top_down and n >= 3:
        return (
            "BEAT-BY-BEAT TOP-DOWN VERTICAL DESCENT LAW: "
            f"Open [Shot 1] and {ts_list[0]} in a tight eye-level close-up on face and lips (keep feet/floor out); "
            f"across {ts_list[1]}, tilt/pedestal smoothly downward{amp_boost} across chest, waist, and hips; "
            f"in {ts_list[-1]}, continue downward along legs to settle cleanly on footwear."
        )

    asks_bottom_up = cid in ("pedestal_up", "elevator_3stop", "tilt_up", "low_angle_power_pedestal", "body_contour_s_curve_pedestal_glide", "jib_up_reveal") or bool(
        re.search(r"\b(?:from\s+(?:her|his|their|the)?\s*(?:feet|toes|boots|heels|ankles|floor)\b.*?\b(?:up\s+)?to\s+(?:her|his|their|the)?\s*(?:hips|waist|chest|face|eyes)|ankle[- ]to[- ]face|3[- ]stop\s+elevator)\b", brief or "", re.I)
    )
    if asks_bottom_up and n >= 3:
        return (
            "BEAT-BY-BEAT 3-STOP ELEVATOR RISE LAW: "
            f"Open [Shot 1] and {ts_list[0]} low on ankles/heels (or behind a foreground edge for Jib Up), then pedestal up smoothly{amp_boost}; "
            f"pause across {' and '.join(ts_list[1:-1])} squarely on waist and swaying hips; "
            f"finish in {ts_list[-1]} rising past collarbones to lock onto face and eyes."
        )

    if cid in ("push_in", "super_dolly_in", "crash_zoom_in", "dolly_zoom_in"):
        move_name = "super push in" if cid == "super_dolly_in" else ("crash zoom in" if cid == "crash_zoom_in" else ("physical pull out while optically zooming in" if cid == "dolly_zoom_in" else "dolly push in"))
        return (
            f"OPEN-END RANGE LAW ({cid.upper()}): Open [Shot 1] and {ts_list[0]} wide/medium-wide so the lens has physical room to travel inward; "
            f"across {', '.join(ts_list[1:]) if n >= 2 else ts_list[0]}, execute a clean {move_name}{amp_boost} settling on eyes or key expression."
        )

    if cid in ("pull_out", "super_dolly_out", "crash_zoom_out", "aerial_pullback", "detail_to_wide", "earth_zoom"):
        return (
            f"OPEN-END REVEAL LAW ({cid.upper()}): Open [Shot 1] and {ts_list[0]} tight on a close face, eye, or tactile detail; "
            f"across {', '.join(ts_list[1:]) if n >= 2 else ts_list[0]}, continuously pull out / pedestal up with large amplitude at {speed_word} speed until the full architecture/skyline opens wide."
        )

    if cid in ("selfie_arm", "selfie_high_overhead") or bool(re.search(r"\b(?:selfie|arm'?s[- ]length\s+camera)\b", brief or "", re.I)):
        corner = "upper corner looking steeply down" if cid == "selfie_high_overhead" else "bottom corner at arm's length"
        return (
            f"SELFIE ARM-LOCK LAW: Across [Shot 1] and {', '.join(ts_list)}, keep one extended arm reaching toward the {corner} while the subject stays centered and background walls swing cleanly behind them (keep phone bezels unmentioned)."
        )

    if cid in ("orbit_360", "orbit_180_front_to_rear", "orbit_180_rear_to_front", "arc_left", "arc_right", "spiral_3axis", "overhead_swing"):
        return (
            f"3D ARC / ORBIT PARALLAX LAW: Across {', '.join(ts_list)}, keep the subject's feet grounded facing one clear direction while the camera arcs {pace_adv} around them{amp_boost} and background walls/lights rotate cleanly in 3D parallax."
        )

    if cid == "snorricam":
        return (
            f"TORSO-LOCKED PERSPECTIVE LAW: In [Shot 1] and across {', '.join(ts_list)}, lock the camera frame rigidly to chest height so head and shoulders remain dead-center while hallway walls, ceiling, and lights tilt and whip behind them (describe purely visual motion — never name mechanical chest bars or rigs)."
        )

    if cid in ("pan_left", "pan_right"):
        p_dir = "left" if cid == "pan_left" else "right"
        return (
            f"STATIONARY TRIPOD PAN HORIZON LAW: Across {', '.join(ts_list)}, keep the tripod base planted stationary and pan purely horizontally {p_dir}{amp_boost} with a strictly level horizon."
        )

    if cid == "pullback_rise":
        return (
            f"PULLBACK & CRANE RISE HORIZON LAW: Across {', '.join(ts_list)}, pull out physically while pedestaling upward{amp_boost}, tilting gently down to center the subject with a strictly level horizon."
        )

    if cid == "key_handoff" and n >= 3:
        return (
            f"TRACKING-TO-PROP HANDOFF LAW: In {ts_list[0]}, track laterally beside the moving subject; in {ts_list[1]}, as the subject sets a key prop down and exits clear past frame border, arrest tracking onto the stationary prop; in {ts_list[-1]}, push smoothly inward focusing sharply onto that prop."
        )

    if cid == "walk_past_camera" and n >= 2:
        return (
            f"WALK-PAST LENS TRANSITION LAW: Keep the framing anchored in {ts_list[0]} as the subject approaches straight toward the lens; in {ts_list[1]}, let their shoulder brush close past the foreground edge while panning smoothly to follow their exit into depth."
        )

    if cid == "barrel_roll" and n >= 3:
        return (
            f"360-DEGREE AXIAL BARREL ROLL LAW: Across {ts_list[0]}, roll clockwise through 45° diagonal tilt; in {ts_list[len(ts_list) // 2]}, pass full 180° inverted orientation; in {ts_list[-1]}, settle upright level on the subject's eyes."
        )

    if cid == "floor_step_over" and n >= 2:
        return (
            f"FLOOR WORM'S-EYE STEP-OVER LAW: Open [Shot 1] looking steeply up from floor height; in {ts_list[0]}, the subject steps cleanly over/past the lens border; across {', '.join(ts_list[1:])}, frame upward across hovering silhouette and gaze."
        )

    if cid == "mirror_reveal" and n >= 2:
        return (
            f"MIRROR PAN-OFF REVEAL LAW: Open {ts_list[0]} framed inside a clear mirror reflection; across {', '.join(ts_list[1:])}, pan smoothly off the mirror frame directly onto the live person inside the room."
        )

    if has_bg_plate and cid:
        return f"BACKGROUND PLATE CAMERA BOOST: A standalone set plate is wired, so execute the `{cid}` motion with large amplitude across {', '.join(ts_list)} so camera travel stays crisp and unmistakable."

    return ""


def fx_trajectory_plan(fx_opt: dict | None, light_opt: dict | None, spans: list[tuple[float, float]], fx_timing: str = "delayed_mid") -> str:
    if not fx_opt or not spans or len(spans) < 2 or fx_timing == "from_start":
        return ""
    ts_list = [f"At {stamp(a)}-{stamp(b)}" for a, b in spans]
    mid_idx = max(1, len(ts_list) // 2)
    first_half = ts_list[:mid_idx]
    second_half = ts_list[mid_idx:]
    light_str = light_opt["rule"] if light_opt and light_opt.get("rule") else "clean physical key and rim lighting"
    return (
        "DELAYED MID-CLIP FX & LIGHTING PACING LAW: "
        f"In [Shot 1] and across {', '.join(first_half)}, render {light_str} cleanly on face, hair, and outfit so identity anchors clearly; "
        f"starting in {second_half[0]} (and continuing across {', '.join(second_half)}), unleash the visual FX: {fx_opt['rule']}"
    )
