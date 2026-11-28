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


def h3_video_length_from_seconds(seconds: float, fps: int = 24) -> int:
    """Return frame count rounded up onto MiniMax H3's 24 fps 5 + 17k grid."""
    sec = max(0.0, float(seconds or 0.0))
    frames = max(5, int(round(sec * int(fps or 24))))
    return frames + (5 - frames % 17) % 17


def snap_h3_duration(seconds: float, fps: int = 24) -> tuple[int, float]:
    """Return `(frames, snapped_seconds_3dp)` on MiniMax H3's 24 fps 5 + 17k grid."""
    frames = h3_video_length_from_seconds(seconds, fps=fps)
    return frames, round(frames / float(fps or 24), 3)


def h3_length_grid(min_k: int = 4, max_k: int = 22, fps: int = 24) -> list[dict]:
    """Enumerate supported MiniMax H3 24 fps `5 + 17k` frame/second lengths."""
    rows = []
    for k in range(int(min_k), int(max_k) + 1):
        frames = 5 + 17 * k
        sec = frames / float(fps or 24)
        rows.append({
            "k": k,
            "frames": frames,
            "seconds_3dp": round(sec, 3),
            "seconds_2dp": round(sec, 2),
        })
    return rows


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


def _allocate_weighted_spans(t_start: float, t_end: float, weights: list[float], *, min_seg: float = 0.45) -> list[tuple[float, float]]:
    """Slice [t_start, t_end] cleanly into contiguous segments proportional to weights."""
    n = max(1, len(weights))
    span_len = max(min_seg, round(float(t_end) - float(t_start), 3))
    w_clean = [max(0.05, float(w)) for w in weights[:n]]
    tot = sum(w_clean) or float(n)
    out: list[tuple[float, float]] = []
    cur = round(float(t_start), 3)
    for i, w in enumerate(w_clean):
        if i == n - 1:
            nxt = round(float(t_end), 3)
        else:
            rem_min = min_seg * (n - 1 - i)
            ideal = cur + (w / tot) * span_len
            nxt = round(min(float(t_end) - rem_min, max(cur + min_seg, ideal)), 2)
        if nxt <= cur:
            nxt = round(float(t_end), 3) if i == n - 1 else round(min(float(t_end), cur + min_seg), 2)
        out.append((cur, nxt))
        cur = nxt
    return out


def _detect_music_bpm(flavors: dict) -> int:
    m_opts = _cat.resolve_dial_opts("music", flavors.get("music"))
    if not m_opts:
        return 0
    blob = " ".join(f"{o.get('label', '')} {o.get('rule', '')}" for o in m_opts)
    m = re.search(r"\b(\d{2,3})\s*BPM\b", blob, re.I)
    if not m:
        return 0
    return max(60, min(200, int(m.group(1))))


def compute_shot_topology(
    duration_s: float,
    brief: str = "",
    camera_id: str = "",
    quotes: list[str] | None = None,
    explicit_id: str = "",
    flavors: dict | None = None,
) -> dict:
    """Build Shot-Tree topology: hierarchical `[ShotNode -> MicroBeat[]]` + flat `(spans, q_map, cuts)`."""
    T = round(max(2.0, float(duration_s or 10.0)), 3)
    qs = list(quotes if quotes is not None else _dlg.extract_quotes(brief))
    flavors = flavors or {}
    cids = [x.lower() for x in parse_multi_ids(camera_id or flavors.get("camera"))]
    eids = [x.lower() for x in parse_multi_ids(explicit_id or flavors.get("explicit"))]
    cid = cids[0] if cids else ""
    eid = eids[0] if eids else ""

    max_seq_picks = max(len(cids), len(eids), 1)
    for k_dial in ("combat", "place", "wardrobe", "pose", "fetish"):
        if get_dial_mode(flavors, k_dial, "sequence") == "sequence":
            max_seq_picks = max(max_seq_picks, len(parse_multi_ids(flavors.get(k_dial))))

    is_single_continuous_ask = (
        any(e.startswith("cont_") or e in ("deepthroat_to_smile_facial", "stage_aftercare_cooldown_whisper", "stage_slow_grind_lap_tease_insertion") for e in eids)
        or any(c in ("oner", "static_close", "push_in", "slow_push", "copilot_hand_tie_calm_join") for c in cids)
        or bool(re.search(r"\b(?:one\s+(?:continuous|unbroken)\s+(?:shot|take)|single\s+(?:continuous\s+|unbroken\s+)?(?:shot|take)|zero\s+cuts|no\s+cuts)\b", brief or "", re.I))
    )
    is_cont_explicit = any(
        e.startswith("cont_") or e in ("stage_aftercare_cooldown_whisper", "stage_slow_grind_lap_tease_insertion")
        for e in eids
    )
    is_combat_scene = _dir.is_combat(brief, str(flavors.get("combat") or ""), str(flavors.get("wardrobe") or ""), str(flavors.get("fx") or ""))
    pose_opts_t = _cat.resolve_dial_opts("pose", flavors.get("pose"))
    is_dance_scene = bool(
        any(str(o.get("id") or "").startswith("dance_") or "dance" in str(o.get("group") or "").lower() for o in pose_opts_t)
        or re.search(r"(?:^|[\s_-])(?:kpop|choreo|danc(?:e|ing|er))(?:$|[\s_-])", f"{flavors.get('pose') or ''} {brief or ''}", re.I)
    )
    is_sex_scene = _dir.is_sexual(brief, explicit_id or str(flavors.get("explicit") or ""), str(flavors.get("wardrobe") or ""), fetish_id=str(flavors.get("fetish") or ""))

    def _pack_result(genre: str, shots_spec: list[dict], source: str) -> dict:
        spans_out: list[tuple[float, float]] = []
        cuts_out: list[int] = []
        for s_i, sh in enumerate(shots_spec):
            if s_i > 0:
                cuts_out.append(len(spans_out))
            for b in sh["beats"]:
                spans_out.append((b["t0"], b["t1"]))
        q_map_out: dict[int, list[str]] = {}
        if qs and spans_out:
            # Prefer non-impact, non-oral-sealed middle/lead beats when assigning single quotes
            elig = [
                idx for idx, sh in enumerate(shots_spec) for _b in sh["beats"]
            ]
            flat_meta = [b for sh in shots_spec for b in sh["beats"]]
            good_idxs = [i for i, b in enumerate(flat_meta) if b.get("audio_fg") not in ("impact", "oral_sealed")]
            if len(qs) == 1:
                if good_idxs:
                    pref = good_idxs[1] if len(good_idxs) >= 3 else good_idxs[0]
                else:
                    pref = 0 if len(spans_out) <= 2 else 1
                q_map_out[pref] = [qs[0]]
                flat_meta[pref]["audio_fg"] = "dialogue"
                flat_meta[pref]["quotes"] = [qs[0]]
            else:
                targets = good_idxs or elig
                for q_i, q in enumerate(qs):
                    t_idx = targets[min(len(targets) - 1, q_i)]
                    q_map_out.setdefault(t_idx, []).append(q)
                    flat_meta[t_idx]["audio_fg"] = "dialogue"
                    flat_meta[t_idx].setdefault("quotes", []).append(q)
        return {
            "duration_s": T,
            "genre": genre,
            "source": source,
            "shots": shots_spec,
            "spans": spans_out,
            "cuts": cuts_out,
            "q_map": q_map_out,
        }

    # 1. Jumpcut burst presets
    if cid in ("jumpcut_pose_burst", "jumpcut_z_steps") and len(cids) == 1 and not is_single_continuous_ask and T >= 5.0:
        c_step = 0.65 if cid == "jumpcut_pose_burst" else 0.70
        cs = [round(c_step * (k + 1), 2) for k in range(4)]
        mid = round(cs[-1] + (T - cs[-1]) * 0.5, 2)
        shots_jc = [
            {"shot_n": 1, "t0": 0.0, "t1": cs[0], "beats": [{"role": "jump_hit", "role_label": "Jumpcut Hit 1", "weight": cs[0], "t0": 0.0, "t1": cs[0], "audio_fg": "music_hit", "quotes": []}]},
            {"shot_n": 2, "t0": cs[0], "t1": cs[1], "beats": [{"role": "jump_hit", "role_label": "Jumpcut Hit 2", "weight": c_step, "t0": cs[0], "t1": cs[1], "audio_fg": "music_hit", "quotes": []}]},
            {"shot_n": 3, "t0": cs[1], "t1": cs[2], "beats": [{"role": "jump_hit", "role_label": "Jumpcut Hit 3", "weight": c_step, "t0": cs[1], "t1": cs[2], "audio_fg": "music_hit", "quotes": []}]},
            {"shot_n": 4, "t0": cs[2], "t1": cs[3], "beats": [{"role": "jump_hit", "role_label": "Jumpcut Hit 4", "weight": c_step, "t0": cs[2], "t1": cs[3], "audio_fg": "music_hit", "quotes": []}]},
            {"shot_n": 5, "t0": cs[3], "t1": T, "beats": [
                {"role": "groove_layer", "role_label": "Flow Continuation", "weight": mid - cs[3], "t0": cs[3], "t1": mid, "audio_fg": "foley", "quotes": []},
                {"role": "ending_hold", "role_label": "Closing Hold", "weight": T - mid, "t0": mid, "t1": T, "audio_fg": "foley", "quotes": []},
            ]},
        ]
        return _pack_result("dance" if is_dance_scene else "cinema", shots_jc, "jumpcut")

    # 2. Matchcut / Coverage / Front-to-Rear 2-cut presets
    if (cid in ("matchcut_hand_outfit", "coverage_match_on_action") or eid == "cam_cut_front_to_rear") and not eid.startswith(("stage_", "multi_pos_")) and not is_single_continuous_ask and max_seq_picks <= 1 and T >= 4.5:
        cut_t = round(T * 0.5, 2) if (eid == "cam_cut_front_to_rear" or cid == "coverage_match_on_action") else round(min(2.6, T * 0.32), 2)
        if eid == "cam_cut_front_to_rear":
            if T >= 7.0:
                s1_bs = _allocate_weighted_spans(0.0, cut_t, [0.45, 0.55], min_seg=0.8)
                s2_bs = _allocate_weighted_spans(cut_t, T, [0.42, 0.58], min_seg=0.8)
                shots_mc = [
                    {"shot_n": 1, "t0": 0.0, "t1": cut_t, "beats": [
                        {"role": "setup_contact", "role_label": "Front Setup", "weight": 0.45, "t0": s1_bs[0][0], "t1": s1_bs[0][1], "audio_fg": "foley", "quotes": []},
                        {"role": "drive_settle", "role_label": "Front Motion", "weight": 0.55, "t0": s1_bs[1][0], "t1": s1_bs[1][1], "audio_fg": "breath", "quotes": []},
                    ]},
                    {"shot_n": 2, "t0": cut_t, "t1": T, "beats": [
                        {"role": "cut_transition", "role_label": "Rear Angle Cut", "weight": 0.42, "t0": s2_bs[0][0], "t1": s2_bs[0][1], "audio_fg": "foley", "quotes": []},
                        {"role": "rhythm_peak", "role_label": "Rear Drive & Hold", "weight": 0.58, "t0": s2_bs[1][0], "t1": s2_bs[1][1], "audio_fg": "breath", "quotes": []},
                    ]},
                ]
            else:
                shots_mc = [
                    {"shot_n": 1, "t0": 0.0, "t1": cut_t, "beats": [{"role": "setup_contact", "role_label": "Front Shot", "weight": 1.0, "t0": 0.0, "t1": cut_t, "audio_fg": "foley", "quotes": []}]},
                    {"shot_n": 2, "t0": cut_t, "t1": T, "beats": [{"role": "rhythm_peak", "role_label": "Rear Cut", "weight": 1.0, "t0": cut_t, "t1": T, "audio_fg": "breath", "quotes": []}]},
                ]
        else:
            s2_bs = _allocate_weighted_spans(cut_t, T, [0.48, 0.52], min_seg=0.7)
            shots_mc = [
                {"shot_n": 1, "t0": 0.0, "t1": cut_t, "beats": [{"role": "setup_contact", "role_label": "Match Setup", "weight": 1.0, "t0": 0.0, "t1": cut_t, "audio_fg": "foley", "quotes": []}]},
                {"shot_n": 2, "t0": cut_t, "t1": T, "beats": [
                    {"role": "cut_transition", "role_label": "Action Match Follow-Through", "weight": 0.48, "t0": s2_bs[0][0], "t1": s2_bs[0][1], "audio_fg": "foley", "quotes": []},
                    {"role": "drive_settle", "role_label": "Peak & Settle", "weight": 0.52, "t0": s2_bs[1][0], "t1": s2_bs[1][1], "audio_fg": "breath", "quotes": []},
                ]},
            ]
        return _pack_result("explicit_stage" if is_sex_scene else "cinema", shots_mc, "matchcut")

    m_ask = re.search(r"\b(\d{1,2})\s+(?:different\s+|quick\s+|separate\s+|hard\s+)?(?:shots?|cuts?|angles?|positions?)\b", brief or "", re.I)
    asked_shots = int(m_ask.group(1)) if m_ask else 0

    def _rule_shot_count(rtxt: str) -> int:
        if not rtxt:
            return 0
        cleaned = re.sub(r"\([^)]*\[Shot\s+\d+\][^)]*\)", " ", str(rtxt), flags=re.I)
        nums = sorted({int(m.group(1)) for m in re.finditer(r"(?<!`)\[\s*Shot\s+(\d+)\s*\](?!`)", cleaned, re.I)})
        if len(nums) <= 1:
            nums = sorted({int(m.group(1)) for m in re.finditer(r"\[\s*Shot\s+(\d+)\s*\]", cleaned, re.I)})
        return len(nums) if len(nums) >= 2 else 0

    rule_shot_count = 0
    if not is_single_continuous_ask and asked_shots == 0:
        for dk in ("explicit", "combat", "pose"):
            dopts = _cat.resolve_dial_opts(dk, flavors.get(dk))
            if len(dopts) == 1:
                sc = _rule_shot_count(dopts[0].get("rule") or "")
                if sc >= 2:
                    rule_shot_count = sc
                    break

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

    # 3. Explicit millisecond `At MM:SS.mmm-MM:SS.mmm` rules (e.g. Uber Fights)
    viral_cut_cams = {
        "multi_angle_action_close", "multi_position_3cut_intimate", "multi_angle_orbit_arc_cut",
        "coverage_match_on_action", "table_two_shot_profile_to_single",
        "shot_reverse", "whip_pan_transition", "match_cut_motion",
        "cam_viral_dutch_90roll_wipe_cuts", "cam_beat_drop_punch_wide_combo", "cam_palm_cover_lens_reveal_snap",
        "cam_whip_pan_beat_snap_cut", "graphic_match_cut", "smash_cut_contrast",
        "cam_distant_wide_master_to_hardcut_closeup",
    }
    three_shot_cams = {
        "multi_angle_action_close", "multi_position_3cut_intimate", "multi_angle_orbit_arc_cut",
        "shot_reverse", "cam_viral_dutch_90roll_wipe_cuts", "cam_beat_drop_punch_wide_combo",
    }
    cam_seq_mode = get_dial_mode(flavors, "camera", "sequence") == "sequence"
    exp_seq_mode = get_dial_mode(flavors, "explicit", "sequence") == "sequence"
    place_ids = parse_multi_ids(flavors.get("place"))
    place_seq_n = len(place_ids) if (len(place_ids) >= 2 and get_dial_mode(flavors, "place", "sequence") == "sequence") else 0

    ms_spans: list[tuple[float, float]] = []
    ms_cuts: list[int] = []
    if asked_shots == 0:
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

    if ms_spans:
        raw_durs = [max(0.4, b - a) for a, b in ms_spans]
        scaled_spans = _allocate_weighted_spans(0.0, T, raw_durs, min_seg=0.4)
        cut_set = set(ms_cuts) if not is_single_continuous_ask else set()
        # If the ms_rule is a single unbroken sequence (0 explicit cuts) AND a multi-cut camera or multi-place sequence is active,
        # inject shot cuts cleanly along the existing ms_spans so camera cuts & BPM choreography both hold!
        if not cut_set and not is_single_continuous_ask and len(scaled_spans) >= 2:
            want_cam_shots = 0
            if place_seq_n >= 2:
                want_cam_shots = min(4, place_seq_n)
            elif len(cids) >= 2 and cam_seq_mode:
                want_cam_shots = min(4, len(cids))
            elif any(c in viral_cut_cams for c in cids):
                want_cam_shots = 3 if any(c in three_shot_cams for c in cids) else 2
            if want_cam_shots >= 2:
                k_cuts = min(want_cam_shots, len(scaled_spans))
                for s_k in range(1, k_cuts):
                    b_cut = (s_k * len(scaled_spans)) // k_cuts
                    if 0 < b_cut < len(scaled_spans):
                        cut_set.add(b_cut)
        shots_ms: list[dict] = []
        cur_beats: list[dict] = []
        shot_idx = 1
        n_ms = len(scaled_spans)
        for bi, (a, b) in enumerate(scaled_spans):
            if bi > 0 and bi in cut_set:
                shots_ms.append({"shot_n": shot_idx, "t0": cur_beats[0]["t0"], "t1": cur_beats[-1]["t1"], "beats": cur_beats})
                shot_idx += 1
                cur_beats = []
            if is_combat_scene:
                role = "open_burst" if bi == 0 else ("impact_recoil" if bi == n_ms - 1 else ("ultimate_strike" if bi == n_ms - 2 else "clash_exchange"))
                afg = "impact"
            else:
                role = "opening_setup" if bi == 0 else ("peak_settle" if bi == n_ms - 1 else "action_beat")
                afg = "foley"
            cur_beats.append({
                "role": role,
                "role_label": role.replace("_", " ").title(),
                "weight": round(b - a, 3),
                "t0": a,
                "t1": b,
                "audio_fg": afg,
                "quotes": [],
            })
        if cur_beats:
            shots_ms.append({"shot_n": shot_idx, "t0": cur_beats[0]["t0"], "t1": cur_beats[-1]["t1"], "beats": cur_beats})
        return _pack_result("combat" if is_combat_scene else ("dance" if is_dance_scene else "cinema"), shots_ms, "ms_rule")

    # 4. Multi-shot topology (`stage_*`, `multi_pos_*`, `asked_shots`, multi-cam sequences)
    if rule_shot_count == 0 and not is_single_continuous_ask and len(cids) == 1 and cids[0] in ("multi_angle_action_close", "multi_position_3cut_intimate", "multi_angle_orbit_arc_cut") and asked_shots == 0:
        rule_shot_count = 3
    multi_cut_cam = (
        (len(cids) >= 2 and cam_seq_mode)
        or any(c in viral_cut_cams for c in cids)
        or (is_multi_pos and (exp_seq_mode or len(eids) <= 1 or exp_has_cuts))
        or place_seq_n >= 2
        or asked_shots >= 2
        or rule_shot_count >= 2
    )

    if not is_single_continuous_ask and multi_cut_cam:
        if rule_shot_count >= 2 and asked_shots == 0:
            n_shots = rule_shot_count
        elif 2 <= asked_shots <= 6 and T >= asked_shots * 1.5:
            n_shots = asked_shots
        elif any(e.startswith(("multi_pos_", "stage_")) for e in eids) or exp_has_cuts:
            n_shots = max(2, min(4, len(eids) if len(eids) >= 2 else 3))
        elif place_seq_n >= 2:
            n_shots = min(4, place_seq_n)
        elif len(cids) >= 2 and cam_seq_mode:
            n_shots = min(4, len(cids))
        elif any(c in three_shot_cams for c in cids):
            n_shots = 3
        else:
            n_shots = 2

        if n_shots == 2:
            shot_weights = [0.46, 0.54]
        elif n_shots == 3:
            shot_weights = [0.30, 0.36, 0.34]
        else:
            shot_weights = [1.0 / n_shots] * n_shots
        shot_bounds = _allocate_weighted_spans(0.0, T, shot_weights, min_seg=1.0)
        shots_multi: list[dict] = []
        genre_m = "explicit_stage" if is_sex_scene else ("combat" if is_combat_scene else ("dance" if is_dance_scene else "cinema"))
        for s_idx, (st0, st1) in enumerate(shot_bounds):
            sdur = st1 - st0
            use_two_micro = (n_shots <= 3 and sdur >= 2.75 and asked_shots < 4)
            if use_two_micro:
                mb_spans = _allocate_weighted_spans(st0, st1, [0.42, 0.58], min_seg=0.85)
                r0 = "opening_setup" if s_idx == 0 else "cut_transition"
                l0 = "Shot 1 Opening Setup & Anchor" if s_idx == 0 else f"Shot {s_idx + 1} Cut Arrival & Position Shift"
                r1 = "closing_hold" if s_idx == n_shots - 1 else "rhythm_contact"
                l1 = f"Shot {s_idx + 1} Peak & Final Hold" if s_idx == n_shots - 1 else f"Shot {s_idx + 1} Primary Action & Reaction"
                afg_m = "impact" if is_combat_scene else ("breath" if is_sex_scene else "foley")
                beats_m = [
                    {"role": r0, "role_label": l0, "weight": 0.42, "t0": mb_spans[0][0], "t1": mb_spans[0][1], "audio_fg": "foley", "quotes": []},
                    {"role": r1, "role_label": l1, "weight": 0.58, "t0": mb_spans[1][0], "t1": mb_spans[1][1], "audio_fg": afg_m, "quotes": []},
                ]
            else:
                r_only = "opening_setup" if s_idx == 0 else ("closing_hold" if s_idx == n_shots - 1 else "cut_transition")
                l_only = f"Shot {s_idx + 1} Primary Beat"
                beats_m = [
                    {"role": r_only, "role_label": l_only, "weight": 1.0, "t0": st0, "t1": st1, "audio_fg": "impact" if is_combat_scene else "foley", "quotes": []},
                ]
            shots_multi.append({"shot_n": s_idx + 1, "t0": st0, "t1": st1, "beats": beats_m})
        return _pack_result(genre_m, shots_multi, "multi_shot")

    # 5. Single-Take Topologies (Continuous `cont_*`, Combat, Dance/K-Pop, Cinema/General)
    if is_cont_explicit:
        genre_s = "explicit_cont"
        if T < 6.0:
            role_specs = [
                ("anchor_shift", "Opening Anchor & Garment Shift", 0.22, "foley"),
                ("entry_drive", "Position Align & Primary Entry", 0.44, "breath"),
                ("peak_settle", "Peak Rhythm & Closing Hold", 0.34, "breath"),
            ]
        else:
            role_specs = [
                ("anchor_shift", "Opening Anchor & Garment Displacement", 0.18, "foley"),
                ("pivot_align", "Postural Pivot & Alignment", 0.27, "foley"),
                ("entry_drive", "Full Entry & Rhythmic Drive", 0.33, "breath"),
                ("peak_settle", "Peak Tension & Steady Closing Hold", 0.22, "breath"),
            ]
    elif is_combat_scene:
        genre_s = "combat"
        if T < 6.0:
            role_specs = [
                ("open_burst", "Immediate Combat Eruption", 0.24, "impact"),
                ("ultimate_strike", "Signature Ultimate Strike + Snap Zoom", 0.46, "impact"),
                ("impact_recoil", "Knockback Crash, Debris & Victor Stance", 0.30, "impact"),
            ]
        else:
            role_specs = [
                ("open_burst", "00:00.000 Opening Strike / Blitz", 0.20, "impact"),
                ("clash_exchange", "Rapid Blow-for-Blow Exchange", 0.30, "impact"),
                ("ultimate_strike", "Penultimate Ultimate Attack + Tight Zoom", 0.26, "impact"),
                ("impact_recoil", "Final Crash Recoil, Debris & Victor Hold", 0.24, "impact"),
            ]
    elif is_dance_scene:
        genre_s = "dance"
        if T < 6.0:
            role_specs = [
                ("count_hit", "Full-Body Stance & Count-1 Hit", 0.28, "music_hit"),
                ("groove_layer", "Footwork Travel & Level Drop", 0.44, "music_hit"),
                ("ending_hold", "Planted Lunge & Dime-Stop Freeze", 0.28, "music_hit"),
            ]
        else:
            role_specs = [
                ("count_hit", "Full-Body Framing & Count-1 Hit", 0.22, "music_hit"),
                ("groove_layer", "Footwork Travel & Weight Shift", 0.30, "music_hit"),
                ("choreo_turn", "Level Drop, Pivot Turn & Arm Snap", 0.28, "music_hit"),
                ("ending_hold", "Planted Stage Lunge & Dead-Stop Hold", 0.20, "music_hit"),
            ]
    else:
        genre_s = "explicit_general" if is_sex_scene else ("fetish" if flavors.get("fetish") else "cinema")
        if max_seq_picks >= 3 and T >= 6.4:
            role_specs = [
                ("anchor_open", f"Beat {k + 1} Stage", 1.0 / min(4, max_seq_picks), "breath" if is_sex_scene else "foley")
                for k in range(min(4, max_seq_picks))
            ]
        elif T < 6.4:
            role_specs = [
                ("anchor_open", "Opening Anchor & Action", 0.46, "foley"),
                ("drive_settle", "Primary Response & Settle", 0.54, "breath" if is_sex_scene else "foley"),
            ]
        elif T <= 11.4 and len(qs) < 2:
            role_specs = [
                ("anchor_open", "Opening Blocking & Anchor", 0.28, "foley"),
                ("line_or_peak", "Primary Action / Dialogue Beat", 0.38, "breath" if is_sex_scene else "foley"),
                ("reaction_settle", "Reaction & Closing Settle", 0.34, "breath" if is_sex_scene else "foley"),
            ]
        else:
            role_specs = [
                ("anchor_open", "Opening Blocking & Anchor", 0.22, "foley"),
                ("progression_action", "Escalating Gesture / Motion", 0.28, "breath" if is_sex_scene else "foley"),
                ("climax_or_turn", "Peak Turn / Emotional Focus", 0.28, "breath" if is_sex_scene else "foley"),
                ("closing_settle", "Lingering Final Beat & Hold", 0.22, "breath" if is_sex_scene else "foley"),
            ]

    weights_s = [r[2] for r in role_specs]
    if qs and len(role_specs) >= 2:
        # Nudge spoken beat(s) slightly longer so <d> lines aren't rushed
        if len(qs) == 1:
            q_target = 1 if len(role_specs) >= 3 else 0
            weights_s[q_target] += 0.06
        else:
            for qi in range(min(len(qs), len(role_specs))):
                weights_s[qi] += 0.04

    spans_s = _allocate_weighted_spans(0.0, T, weights_s, min_seg=0.8)
    # Gentle BPM bar-snapping for single-take dance clips when drift is tiny
    bpm = _detect_music_bpm(flavors) if is_dance_scene else 0
    if bpm and len(spans_s) >= 3:
        bar2 = 120.0 / float(bpm)  # half-bar (2 beats)
        snapped = list(spans_s)
        for i in range(len(snapped) - 1):
            t_cur = snapped[i][1]
            t_snap = round(round(t_cur / bar2) * bar2, 2)
            prev_t0 = snapped[i][0]
            next_t1 = snapped[i + 1][1]
            if abs(t_snap - t_cur) <= 0.40 and (t_snap - prev_t0) >= 1.0 and (next_t1 - t_snap) >= 1.0:
                snapped[i] = (prev_t0, t_snap)
                snapped[i + 1] = (t_snap, next_t1)
        spans_s = snapped

    beats_s = [
        {
            "role": r[0],
            "role_label": r[1],
            "weight": r[2],
            "t0": spans_s[idx][0],
            "t1": spans_s[idx][1],
            "audio_fg": r[3],
            "quotes": [],
        }
        for idx, r in enumerate(role_specs)
    ]
    return _pack_result(genre_s, [{"shot_n": 1, "t0": 0.0, "t1": T, "beats": beats_s}], "single_take")


def build_beat_grid(
    duration_s: float,
    brief: str = "",
    camera_id: str = "",
    quotes: list[str] | None = None,
    explicit_id: str = "",
    flavors: dict | None = None,
) -> tuple[list[tuple[float, float]], dict[int, list[str]], list[int]]:
    """Compute [(t0, t1), ...] beat spans covering 0..duration_s, quote placements, and hard-cut indices."""
    topo = compute_shot_topology(
        duration_s,
        brief=brief,
        camera_id=camera_id,
        quotes=quotes,
        explicit_id=explicit_id,
        flavors=flavors,
    )
    return topo["spans"], topo["q_map"], topo["cuts"]


def camera_trajectory_plan(
    brief: str,
    camera_id: str,
    spans: list[tuple[float, float]],
    is_pov: bool = False,
    has_bg_plate: bool = False,
    is_combat: bool = False,
    explicit_id: str = "",
) -> str:
    """Emit H3-grounded motion-primitive trajectory laws (Open-End Range, LoopForge, Zero Rig Hardware)."""
    if is_pov or not spans:
        return ""
    ts_list = [f"At {stamp(a)}-{stamp(b)}" for a, b in spans]
    n = len(ts_list)
    cids = parse_multi_ids(camera_id)
    eids = [x.lower() for x in parse_multi_ids(explicit_id)]
    cid = cids[0].lower() if cids else ""
    has_exp_stage = bool(eids)
    has_exp_cuts = any(
        e.startswith(("stage_", "multi_pos_")) and e not in ("stage_aftercare_cooldown_whisper", "stage_slow_grind_lap_tease_insertion")
        for e in eids
    )
    amp_boost = " with large amplitude across the full shot" if has_bg_plate else ""
    pace_adv = "fast and briskly" if is_combat else "smoothly"
    speed_word = "fast" if is_combat else "steady"
    mid_ts = ", ".join(ts_list[1:-1]) if n >= 3 else ts_list[-1]

    if cid == "body_contour_s_curve_pedestal_glide" and has_exp_stage and not any(e.startswith(("solo_", "undress_")) for e in eids):
        return (
            "BODY-CONTOUR FRAMING LAW: Frame tightly along the active waist, hip curve, torso, and chest contact across "
            + ", ".join(ts_list)
            + ", gliding smoothly upward along posture and expression shifts while honoring the active stage's exact opening pose."
        )

    asks_top_down = (not has_exp_cuts) and (cid in ("pedestal_down", "tilt_down", "finger_follow_macro") or bool(
        re.search(r"\b(?:from\s+(?:her|his|their|the)?\s*(?:head|face|eyes|lips)\b.*?\b(?:down\s+)?to\s+(?:her|his|their|the)?\s*(?:hips|legs|feet|heels|ankles)|top[- ]to[- ]bottom)\b", brief or "", re.I)
    ))
    if asks_top_down and n >= 3:
        return (
            "BEAT-BY-BEAT TOP-DOWN VERTICAL DESCENT LAW: "
            f"Open [Shot 1] and {ts_list[0]} in a tight eye-level close-up on face and lips (keep feet/floor out); "
            f"across {mid_ts}, tilt/pedestal smoothly downward{amp_boost} across chest, waist, and hips; "
            f"in {ts_list[-1]}, continue downward along legs to settle cleanly on footwear."
        )

    asks_bottom_up = (not has_exp_stage) and (cid in ("pedestal_up", "elevator_3stop", "tilt_up", "body_contour_s_curve_pedestal_glide", "jib_up_reveal") or bool(
        re.search(r"\b(?:from\s+(?:her|his|their|the)?\s*(?:feet|toes|boots|heels|ankles|floor)\b.*?\b(?:up\s+)?to\s+(?:her|his|their|the)?\s*(?:hips|waist|chest|face|eyes)|ankle[- ]to[- ]face|3[- ]stop\s+elevator)\b", brief or "", re.I)
    ))
    if asks_bottom_up and n >= 3:
        return (
            "BEAT-BY-BEAT 3-STOP ELEVATOR RISE LAW: "
            f"Open [Shot 1] and {ts_list[0]} low on ankles/heels (or behind a foreground edge for Jib Up), then pedestal up smoothly{amp_boost}; "
            f"pause across {' and '.join(ts_list[1:-1])} squarely on waist and swaying hips; "
            f"finish in {ts_list[-1]} rising past collarbones to lock onto face and eyes."
        )

    if cid == "low_angle_power_pedestal":
        return (
            "LOW-ANGLE POWER PEDESTAL LAW: Frame from a low-angle perspective looking gently upward across "
            + ", ".join(ts_list)
            + " so upright posture and commanding gaze dominate the composition without forcing an unrelated floor/ankle cut."
        )

    if not has_exp_cuts and cid in ("push_in", "super_dolly_in", "crash_zoom_in", "dolly_zoom_in"):
        move_name = "super push in" if cid == "super_dolly_in" else ("crash zoom in" if cid == "crash_zoom_in" else ("physical pull out while optically zooming in" if cid == "dolly_zoom_in" else "dolly push in"))
        return (
            f"OPEN-END RANGE LAW ({cid.upper()}): Open [Shot 1] and {ts_list[0]} wide/medium-wide so the lens has physical room to travel inward; "
            f"across {', '.join(ts_list[1:]) if n >= 2 else ts_list[0]}, execute a clean {move_name}{amp_boost} settling on eyes or key expression."
        )

    if not has_exp_cuts and cid in ("pull_out", "super_dolly_out", "crash_zoom_out", "aerial_pullback", "detail_to_wide", "earth_zoom"):
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
            f"TRACKING-TO-PROP HANDOFF LAW: In {ts_list[0]}, track laterally beside the moving subject; in {mid_ts}, as the subject sets a key prop down and exits clear past frame border, arrest tracking onto the stationary prop; in {ts_list[-1]}, push smoothly inward focusing sharply onto that prop."
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

    if cid == "cam_kpop_inkigayo_ronin_hand_drop" and n >= 3:
        return (
            f"K-POP HAND-MOTIVATED GIMBAL LAW: {ts_list[0]}, push tight toward outstretched fingertips; {mid_ts}, snap camera sharply downward with micro-shake on hand drop and whip laterally along pointed fingers; {ts_list[-1]}, rise smoothly to a hero wide chorus hold."
        )

    if cid == "cam_kpop_tutting_arm_window_frame" and n >= 3:
        return (
            f"K-POP ARM-WINDOW FRAME LAW: Open {ts_list[0]} looking cleanly through the foreground dancer's 90-degree forearm-and-finger box onto the partner's eyes; {mid_ts}, punch straight through the wrist window into crisp synchronized close-ups; {ts_list[-1]}, snap wide on matched fingertip locks."
        )

    if cid == "cam_kpop_through_wall_match_truck" and n >= 2:
        return (
            f"K-POP MATCH-TRUCK WIPE LAW: Track continuously horizontally across {ts_list[0]}, wipe briskly past a solid vertical wall or pillar edge on the cut beat, and emerge across {', '.join(ts_list[1:])} onto the matched dance pose under transformed lighting."
        )

    if cid == "cam_kpop_anti_drop_macro_to_crane" and n >= 3:
        return (
            f"K-POP ANTI-DROP MACRO-TO-CRANE LAW: Open {ts_list[0]} tightly on geometric finger-tutting locks beside one eye holding a crisp anti-drop freeze; across {', '.join(ts_list[1:])}, boom rapidly backward and high onto a sweeping crane wide revealing explosive footwork."
        )

    if cid == "cam_combat_kinetic_whip_zoom_ultimate" and n >= 3:
        return (
            f"COMBAT WHIP-TO-ULTIMATE ZOOM LAW: Dart fast laterally with punches ({ts_list[0]}), drop low on sweeps and tilt steeply up on mid-air clashes ({mid_ts}), snap-zoom tightly inward onto the signature ultimate attack ({ts_list[-2] if n >= 3 else ts_list[-1]}), and whip wide across crash debris ({ts_list[-1]})."
        )

    if cid in ("shot_reverse", "copilot_plate_side_180_lock", "over_the_shoulder") and n >= 2:
        return (
            "180-DEGREE EYELINE LAW: Keep the camera strictly on one side of the axis between subjects — "
            "frame <Subject 1> looking screen-right in [Shot 1] and <Subject 2> looking screen-left on reverse cuts so eyelines meet cleanly across every cut."
        )

    if cid in ("coverage_dolly_zoom_compress", "coverage_dolly_zoom_stretch", "dolly_zoom"):
        if cid == "coverage_dolly_zoom_stretch":
            return (
                "DOLLY-ZOOM STRETCH LAW: Physically dolly forward toward the subject while zooming the focal length wide simultaneously, keeping subject frame size steady as background walls stretch deep into perspective."
            )
        return (
            "DOLLY-ZOOM COMPRESS LAW: Physically dolly backward away from the subject while zooming the focal length tight simultaneously, keeping subject frame size steady as background depth swells and compresses behind them."
        )

    if cid in ("overhead", "birds_eye", "top_down", "three_quarter_top_down"):
        return (
            "TOP-DOWN COMPASS LOCK: Anchor body orientation explicitly to the frame edges (head toward top of frame, feet toward bottom of frame, left/right arm placement clear) so overhead body alignment stays consistent across every beat."
        )

    if has_bg_plate and cid and cid not in (
        "handheld", "static_close", "oner", "copilot_hand_tie_calm_join",
        "finger_follow_macro", "macro_lens", "portrait_vertical_stack",
    ):
        return f"BACKGROUND PLATE CAMERA BOOST: A standalone set plate is wired, so execute the `{cid}` motion with large amplitude across the full shot so camera travel stays crisp and unmistakable."

    return ""


def fx_trajectory_plan(fx_opt: dict | list[dict] | None, light_opt: dict | None, spans: list[tuple[float, float]], fx_timing: str = "delayed_mid") -> str:
    fx_list = [o for o in (fx_opt if isinstance(fx_opt, list) else ([fx_opt] if fx_opt else [])) if isinstance(o, dict)]
    if not fx_list or not spans or len(spans) < 2 or fx_timing == "from_start":
        return ""
    if all(
        str(o.get("id") or "").lower().startswith(("fx_ultrareal_", "fx_vhs_", "fx_anamorphic_"))
        or str(o.get("id") or "").lower() in ("fx_raindrop_on_camera_glass", "fx_golden_dust_motes_sunbeam")
        for o in fx_list
    ):
        return ""
    ts_list = [f"At {stamp(a)}-{stamp(b)}" for a, b in spans]
    mid_idx = max(1, len(ts_list) // 2)
    first_half = ts_list[:mid_idx]
    second_half = ts_list[mid_idx:]
    light_str = light_opt["rule"] if light_opt and light_opt.get("rule") else "clean physical key and rim lighting"
    fx_rules = " + ".join(str(o.get("rule") or o.get("label") or "").strip() for o in fx_list if (o.get("rule") or o.get("label")))
    return (
        "DELAYED MID-CLIP FX & LIGHTING PACING LAW: "
        f"In [Shot 1] and across {', '.join(first_half)}, render {light_str} cleanly on face, hair, and outfit so identity anchors clearly; "
        f"starting in {second_half[0]} (and continuing across {', '.join(second_half)}), unleash the visual FX: {fx_rules}"
    )
