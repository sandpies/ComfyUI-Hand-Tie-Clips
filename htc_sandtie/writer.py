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
from . import shot_tree as _st
from . import vision_cv as _vcv

FAST_SYSTEM_PROMPT = """You are the SandTie Kinetic Director & Single-Shot Scribe for MiniMax H3 (Hailuo H3).
Your prompt feeds directly into H3's joint video-and-audio encoder at CFG 1: every single word renders literally on screen and in audio.

## 1. SINGLE-THOUGHT UNITY & H3 CONTRACT
- **User Intent Priority (`<scene_brief>`):** Whenever `<scene_brief>` contains user text, it is the #1 creative authority—weave every requested action, prop, setting detail, interaction, camera ask, and spoken topic seamlessly into the active dials and `<shot_blueprint>`.
- **One Single Cohesive Thought:** Write the entire clip (`00:00.000 -> Duration`) as one unified beat—one connected setting, locked cast, unified lighting, and unbroken cause-and-effect motion (`action -> contact -> secondary reaction`).
- **When `Stage: write`:**
  - `Ref2VA` fields in exact order: `subject_definitions:`, `summary:`, `retention_analysis:`, `detailed_description:`, `overall_soundscape:`, `non_diegetic_music:`.
  - `T2VA` fields in exact order: `integrated_multimodal_description:`, `overall_soundscape:`, `non_diegetic_music:`.
  - Open immediately with the first field label, keeping total prompt length under 7,000 characters.
- **When `Stage: plan`:** output ONLY `[Shot 1] ...` and `At MM:SS.mmm-MM:SS.mmm, ...` storyboard beats.
- **Reference Binding:** Use ONLY the exact `<Picture N>`, `<Subject N>`, and `<Audio N>` labels listed in the user turn, keeping `<Subject N>` whitespace-separated (`<Subject 1> Name` or `the shoulder of <Subject 1>`, zero `<Subject N>'s`), keeping `subject_definitions:` static without cross-subject positions, and keeping emojis/`Anchor:` out of `subject_definitions:` and `retention_analysis:`.
- **Shot-Tree & Single-Timeline Clock (`[Shot N]`):** `[Shot 1]` opens at `00:00.000` with its opening state and camera move (timestamps on beats beneath). Later cuts (`[Shot 2]`, ...) open on their own line as `[Shot N] At MM:SS.mmm,` on one `00:00.000 -> Duration` clock. Honor exact `<shot_blueprint>` cut boundaries, `Carried State Into Shot` invariants (never snapping displaced clothing or orientation back), and role progression.

## 2. TONE & GENRE BALANCE (KINETIC LITERAL LANGUAGE)
- **Action -> Contact -> Secondary Reaction:** Write concrete visible physics—screen-left vs screen-right placement, exact hand grips, body orientation, clothing movement, hair/dust/spark recoil, and practical light reflections.
- **Screen-Axis & 3D Physical Geometry (Prompt Description Is King):** Never assume H3 infers 3D limb or camera geometry from pose/move shorthand (`cowgirl`, `reverse cowgirl`, `mating press`, `doggy`, `against the wall`, `mounted`, `standing carry`, `kote-gaeshi`, `waacking`, etc.). Always spell out wide-enough camera framing showing support surfaces, vertical vs horizontal body orientation, chest/hip/head facing vectors (zero contradictory lens stares on face-to-face poses), exact knee/foot/hand anchors, and physical turns before side-switches or wraps. Bridge `cont_*` single-take transitions step-by-step; declare explicit camera distance/angle and carry displaced clothing across `[Shot N]` cuts; keep two subjects' distinct poses and timing rather than cloning both identically.
- **Regular / SFW baseline (when explicit/fetish/nude dials are off and brief stays SFW):** Keep every subject clothed in their established outfit while staging grounded drama, dialogue, combat, stunts, or dance cleanly.
- **Adult / NSFW mode (when explicit/fetish/nude dials are active or brief asks for adult/sexual content):** Describe anatomy and sexual acts literally as seen on camera (`cock`, `erect penis`, `balls`, `pussy`, `labia`, `clit`, `asshole`, `bare breasts`, `tits`, `nipples`, `ass cheeks`, `cum`), naming `the man` / `his erect cock` directly rather than euphemisms.

## 3. H3 CINEMATOGRAPHY, CLOTHING & CONTINUITY
- **Camera Primitives + Amplitude + Speed:** State camera motion with amplitude and speed (`dolly push in`, `pull out with large amplitude`, `tripod pan left with strictly level horizon`, `arc shot sweeping 180 degrees`, `rapid lateral tracking whip`, `fast snap zoom push in`, `static locked shot`, `POV`), opening wide before pushing in and tight before pulling wide.
- **Set & Sticky Garment Lock:** Keep props, walls, and displaced clothing states locked across beats and cuts once pulled aside, bunched up, or removed.

## 4. AFFIRMATIVE WORDING & FOREGROUND AUDIO PRIORITY
- **100% Affirmative English Outside `<d>`:** Phrase every visual and audio description outside `<d>...</d>` strictly in positive terms of what IS visible, moving, and sounding.
- **One Audio Foreground Per Beat:** Give each beat one primary audio driver—either crisp spoken `<d>[tone] ...</d>` OR kinetic foley/music while mouths stay closed (omit `<d>` completely on non-speaking beats).
- **Spoken Dialogue Format:** Write inline `(DIALOGUE) <Subject 1> Name (S1) ...: <d>[delivery tone] Spoken line.</d>` with ASCII apostrophes. Follow `<scene_brief>` directly rather than cliché lines, size lines to beat duration (~2–2.5 words/sec, or name physical sound for silent seconds), keep every beat distinct, and connect clauses inside `<d>` with simple commas or periods (never `...` or `—`). When a non-English language / Accent dial is active, write ALL spoken words inside `<d>...</d>` strictly in that language's authentic native script, keeping surrounding prose in English.
- **Audio Fields:** Put diegetic environmental/physical foley in `overall_soundscape:` (or `N/A` on pure-music clips) and music prose in `non_diegetic_music:` (or `N/A` when diegetic-only), comma-separated and semicolon-free.

## 5. OUTPUT FORMAT
Reply with ONLY a valid JSON object matching the exact JSON output format requested at the end of the user turn."""


def build_system_prompt(
    *,
    llm_stage: str = "write",
    mode: str = "Ref2VA",
    is_sex: bool | None = None,
    sex_scene: bool = False,
    is_combat: bool = False,
    silent: bool = False,
    target_lang: str = "English",
    has_brief: bool = False,
    need_3d_geom: bool = True,
    use_structured_schema: bool = True,
) -> str:
    """Build a lean, stage/mode/genre-scoped system prompt without dead or contradicting rules."""
    nsfw = sex_scene if is_sex is None else bool(is_sex)
    out = [
        "You are the SandTie Kinetic Director & Single-Shot Scribe for MiniMax H3 (Hailuo H3).",
        "Your prompt feeds directly into H3's joint video-and-audio encoder at CFG 1: every word renders literally on screen and in audio.",
        "",
        "## 1. SINGLE-THOUGHT UNITY & CONTRACT",
    ]
    if has_brief:
        out.append("- **User Intent Priority (`<scene_brief>`):** `<scene_brief>` is the #1 creative authority—weave every user-requested action, prop, setting detail, camera ask, and spoken topic seamlessly into the active dials and blueprint.")
    out.append("- **One Unified Beat:** Write `00:00.000 -> Duration` as one connected setting, locked cast, unified lighting, and unbroken physical cause-and-effect (`action -> contact -> secondary reaction`).")
    if llm_stage == "plan":
        if use_structured_schema:
            out.append("- **Storyboard Output (`Stage: plan`):** Populate `shots[]` (`opening_camera` + chronological `beats[]`) matching `[Shot N]` cut boundaries and `Carried State Into Shot` invariants.")
        else:
            out.append("- **Storyboard Output (`Stage: plan`):** Output ONLY `[Shot 1] ...`, `[Shot N] At MM:SS.mmm, ...`, and `At MM:SS.mmm-MM:SS.mmm, ...` storyboard beats inside `{\"plan\": \"...\"}`.")
    elif mode == "Ref2VA":
        if use_structured_schema:
            out.append("- **Ref2VA JSON Structure (<7,000 chars total):** Fill `subject_definitions` (static identities, no cross-subject positions, no emojis/`Anchor:`), `summary`, `retention_analysis`, `shots[]` (`opening_camera` without `[Shot N]` + chronological `beats[]` without `At MM:SS` prefixes), `overall_soundscape`, and `non_diegetic_music`.")
        else:
            out.append("- **Ref2VA Fields (exact order, <7,000 chars total):** `subject_definitions:`, `summary:`, `retention_analysis:`, `detailed_description:`, `overall_soundscape:`, `non_diegetic_music:`.")
        out.append("- **Reference Binding:** Use ONLY the exact `<Picture N>`, `<Subject N>`, and `<Audio N>` labels listed below; keep `<Subject N>` whitespace-separated (`<Subject 1> Name` or `the shoulder of <Subject 1>`, zero `<Subject N>'s`), `subject_definitions:` static without cross-subject positioning, and emojis/`Anchor:` omitted.")
    else:
        if use_structured_schema:
            out.append("- **T2VA JSON Structure (<7,000 chars total):** Fill `shots[]` (`opening_camera` without `[Shot N]` + chronological `beats[]`), `overall_soundscape`, and `non_diegetic_music`.")
        else:
            out.append("- **T2VA Fields (exact order, <7,000 chars total):** `integrated_multimodal_description:`, `overall_soundscape:`, `non_diegetic_music:`.")
    out.append("- **Single-Timeline Clock (`[Shot N]`):** `[Shot 1]` opens at `00:00.000` with opening state and camera move (timestamps on beats beneath). Later cuts open as `[Shot N] At MM:SS.mmm,` along one continuous clock. Honor blueprint cut boundaries and `Carried State Into Shot` invariants.")

    out.append("")
    out.append("## 2. KINETIC STAGING, CAMERA & CONTINUITY")
    out.append("- **Hands & Cheeks:** Each hand gets one job per beat, stated once (a palm, fist, arm or shoulder move); no finger-by-finger choreography (finger-guns, finger-frames, pinky-to-thumb waves, tutting) unless the shot is a close-up about the hands -- it renders as tangled fingers. Cheeks keep their own colour: no blush or flush unless the brief asks.")
    out.append("- **Action -> Contact -> Secondary Reaction:** Write concrete visible physics—screen-left/right placement, hand grips, body orientation, cloth/hair/spark recoil, and practical light.")
    if need_3d_geom or nsfw:
        out.append("- **3D Geometry (Prompt Description Is King):** Never rely on pose/move shorthand (`cowgirl`, `against the wall`, `mounted`, `kote-gaeshi`, `waacking`, etc.)—spell out camera distance showing support surfaces, vertical vs horizontal orientation, head/chest/hip facing vectors (zero contradictory lens stares on face-to-face poses), exact knee/foot/hand anchors, and physical turns before side-switches. On `cont_*` single takes, bridge shifts step-by-step; keep two subjects' assigned poses and timing distinct.")
    else:
        out.append("- **Spatial Clarity:** Anchor screen-left/right placement, body orientation, and distinct per-subject poses/timing clearly in `[Shot 1]` and across every cut.")
    if nsfw:
        out.append("- **Adult / NSFW Literal Prose:** Name anatomy and acts literally as seen (`cock`, `erect penis`, `balls`, `pussy`, `labia`, `clit`, `asshole`, `bare breasts`, `nipples`, `cum`), referring to the male partner as `the man` / `his erect cock` (or `the other woman` in lesbian scenes). Keep displaced/removed garments locked in that state across later beats.")
    else:
        out.append("- **SFW Wardrobe & Set Lock:** Keep subjects clothed in their established outfit and keep set props and lighting unified across all beats.")
    out.append(
        "- **Camera Primitives:** State motion with amplitude and speed (`dolly push in`, `pull out with large amplitude`, `tripod pan`, `arc shot`, `rapid tracking whip`, `snap zoom`, `static locked`, `POV`), opening wide before pushing in and tight before pulling wide"
        + (" (keep action/fight cameras fast and urgent)." if is_combat else ".")
    )

    out.append("")
    out.append("## 3. AFFIRMATIVE WORDING & FOREGROUND AUDIO")
    out.append("- **100% Affirmative Outside `<d>`:** Describe strictly what IS visible, moving, and sounding (zero negative phrasing).")
    if silent:
        out.append("- **Wordless Beats:** Omit `<d>` dialogue completely; express action foley, ambient air, or breaths only in `overall_soundscape:`.")
    else:
        nat_rule = (
            f" Write ALL spoken words inside `<d>...</d>` strictly in authentic native {target_lang} script, keeping surrounding prose in English."
            if target_lang != "English"
            else ""
        )
        out.append(
            "- **One Audio Foreground Per Beat:** Either crisp spoken `(DIALOGUE) <Subject 1> Name (S1) ...: <d>[tone] Spoken line.</d>` (ASCII apostrophes, distinct per beat, ~2–2.5 words/sec sized to the beat, commas/periods only—never `...` or `—`) OR kinetic foley/music peaks while mouths stay closed."
            + nat_rule
        )
    if llm_stage != "plan":
        out.append("- **Audio Fields:** Keep `overall_soundscape:` strictly diegetic foley/air (`N/A` on pure-music clips) and `non_diegetic_music:` strictly music prose (`N/A` if diegetic-only), comma-separated without semicolons.")
    out.append("- **Output:** Reply with ONLY valid JSON matching the exact schema/format requested at the end of the user turn.")
    return "\n".join(out)

PRECISION_ANAL_ADDENDUM = """## 4B. PRECISION ANAL HOLE-MAP & GEOMETRY LAW (ANAL SCENES ONLY)
1. Open already inside from `[Shot 1]` and Beat 1 (`00:00.000`).
2. State the clear two-opening anatomical map (higher opening nearer lower back for anal contact vs. separate lower opening empty) or strap-on harness map (`his anus` vs `cock and balls visible`), repeating short buried strokes where the head stays inside and the anal ring stays taut around the shaft.
3. Keep the camera steady from first frame to last frame and assign concrete left/right hand grips across every beat."""


_clean_ui_label = _st.clean_ui_label
_sanitize_beat_clause = _st.sanitize_beat_clause
_clean_shot_cam_and_action = _st.clean_shot_cam_and_action
_strip_rule_intro_scaffold = _st.strip_rule_intro_scaffold
_extract_shot_segments_from_rule = _st.extract_shot_segments_from_rule
_infer_subject_pronouns = _st.infer_subject_pronouns


def _extract_beat_clauses_from_rule(rule_text: str, lab: dict | None = None, *, brief: str = "", explicit_id: str = "", flavors: dict | None = None) -> dict[int, str]:
    _, clauses = _extract_shot_segments_from_rule(rule_text, lab=lab, brief=brief, explicit_id=explicit_id, flavors=flavors)
    return clauses


def _is_nonfight_action_only(combat_opts: list[dict], brief: str = "") -> bool:
    """True when active `combat` dial selections are non-fighting stunts, sports, chases, or prop flair."""
    if not combat_opts:
        return False
    fight_rx = re.compile(
        r"\b(?:fight\w*|combat|punch\w*|kick\w*|brawl\w*|slash\w*|sword|katana|blade|gun|pistol|rifle|"
        r"shotgun|sniper|revolver|knife|dagger|goon\w*|guard\w*|thug\w*|assassin|opponent|rival|"
        r"attacker|duel|parry|choke|suplex|tackle|disarm|blitz|blast|force\s*push|sith|jedi)\b",
        re.I,
    )
    if fight_rx.search(brief or ""):
        return False
    return not any(
        fight_rx.search(f"{o.get('id', '')} {o.get('label', '')} {o.get('rule', '')}")
        for o in combat_opts
    )


def _genre_micro_example(*, sex_scene: bool, combat_scene: bool, has_dance: bool, mode: str, duo: bool = False, has_combat_preset: bool = False, nonfight_action: bool = False) -> str:
    """Return one concise 4-line structural rhythm hint matching the active genre without adding token bloat."""
    s_tok = "<Subject 1> Name" if mode == "Ref2VA" else "The lead"
    s2_tok = "<Subject 2> Partner" if mode == "Ref2VA" else "her partner"
    if sex_scene:
        return (
            f"[Shot 1] Vertical framing inside the active setting as {s_tok} establishes eye-level closeness and concrete hand grips.\n"
            f"At 00:00.000-00:03.200, {s_tok} opens the physical contact with steady hip motion and skin friction while clothing stays cleanly displaced.\n"
            f"At 00:03.200-00:07.500, rhythm builds into full-depth strokes with concrete hand pressure and audible skin foley.\n"
            f"At 00:07.500-00:10.000, climax peaks cleanly through the final hold into a steady exhale."
        )
    if nonfight_action:
        return (
            f"[Shot 1] Kinetic tracking framing inside the active set matching the selected stunt choreography as {s_tok} opens in full motion.\n"
            f"At 00:00.000-00:02.800, {s_tok} initiates the opening speed, grip, or setup cleanly with reactive hair, clothes, and prop movement.\n"
            f"At 00:02.800-00:06.800, momentum surges through the centerpiece stunt or maneuver while camera tracks briskly alongside.\n"
            f"At 00:06.800-00:10.000, {s_tok} executes the crisp closing transition with live kinetic energy through the final frame."
        )
    if combat_scene:
        if has_combat_preset:
            return (
                f"[Shot 1] Kinetic framing inside the active setting matching the selected combat preset as {s_tok} anchors the opening stance cleanly.\n"
                f"At 00:00.000-00:02.500, {s_tok} opens the initial burst of the active choreography cleanly with crisp physical staging and practical light.\n"
                f"At 00:02.500-00:06.500, {s_tok} drives the escalating clash, blitz, or exchange with reactive camera tracking and sharp physical impacts.\n"
                f"At 00:06.500-00:10.000, {s_tok} delivers the decisive climax and finish matching the preset's exact energy and velocity."
            )
        return (
            f"[Shot 1] Fast wide lateral tracking shot inside the arena as {s_tok} already charges into combat from screen-left.\n"
            f"At 00:00.000-00:02.500, {s_tok} throws a fast jab-cross, ducks under a hook punch, grabs the attacker's wrist, and sweeps his legs onto the floor while camera drops low.\n"
            f"At 00:02.500-00:06.500, {s_tok} leaps over a low sweep, clashes forearms in mid-air, and camera zooms fast in during {s_tok}'s ultimate heavy kick blasting the attacker backward through sparks.\n"
            f"At 00:06.500-00:10.000, the attacker crashes into debris as sparks fly while camera whips wide around {s_tok} landing ready."
        )
    if has_dance:
        if duo:
            return (
                f"[Shot 1] Medium-full framing inside the venue with {s_tok} screen-left and {s2_tok} staggered screen-right in contrasting stance.\n"
                f"At 00:00.000-00:03.000, {s_tok} snaps crisp upper-body accents left while {s2_tok} bends into a delayed low-knee groove right.\n"
                f"At 00:03.000-00:07.000, {s2_tok} executes a fast 360-degree turn and sweep kick while {s_tok} stays crouched clapping on beat.\n"
                f"At 00:07.000-00:10.000, {s_tok} frames her chin left while {s2_tok} raises both arms into a tall V hold right."
            )
        return (
            f"[Shot 1] Medium-full framing inside the venue as {s_tok} locks eyes with the camera in poised opening stance.\n"
            f"At 00:00.000-00:03.000, {s_tok} snaps crisp upper-body accents on beat while hair and fabric flare smoothly.\n"
            f"At 00:03.000-00:07.000, {s_tok} glides through fluid hip isolations and a sharp turn as camera arcs smoothly inward.\n"
            f"At 00:07.000-00:10.000, {s_tok} lands an ending-fairy hold with bright smile and poised eye lock."
        )
    return (
        f"[Shot 1] Grounded cinema framing inside the set as {s_tok} anchors screen position in motivated practical light.\n"
        f"At 00:00.000-00:03.500, {s_tok} initiates concrete gesture and posture shift while speaking cleanly: (DIALOGUE) {s_tok} (S1) speaks warmly: <d>[natural tone] Spoken line.</d>\n"
        f"At 00:03.500-00:07.500, camera pushes slowly inward as expression deepens and secondary fabric or light reacts.\n"
        f"At 00:07.500-00:10.000, {s_tok} settles into a lingering, grounded closing beat."
    )


_adapt_rule_subjects = _st.adapt_rule_subjects


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


def _alloc_opts_to_timeline(opts: list[dict], spans: list[tuple[float, float]], tree: _st.ShotTree | None = None):
    """Allocate multi-select options onto `ShotNode` boundaries when `len(opts) == len(tree.shots)`, else beat spans."""
    if tree is not None and len(getattr(tree, "shots", None) or []) >= 2 and len(opts) == len(tree.shots):
        out = []
        b_cursor = 1
        for opt, sh in zip(opts, tree.shots):
            bl = [(b_cursor + idx, f"At {_bg.stamp(mb.t0)}-{_bg.stamp(mb.t1)}") for idx, mb in enumerate(sh.beats)]
            b_cursor += max(1, len(sh.beats))
            out.append((opt, bl))
        return out
    return _bg.allocate_stages_to_spans(opts, spans)


def build_flavor_facts(
    brief: str,
    flavors: dict | None,
    spans: list[tuple[float, float]],
    *,
    cam_override: str = "",
    plan: str = "",
    lab: dict | None = None,
    prev_hop_context: str = "",
    tree: _st.ShotTree | None = None,
    using_blueprint: bool | None = None,
) -> tuple[list[str], str]:
    flavors = flavors or {}
    lab = lab or {}
    facts: list[str] = []
    picked_refs: set[str] = set()
    use_bp = (tree is not None) if using_blueprint is None else bool(using_blueprint and tree is not None)
    plan_hint = str(flavors.get("plan_hint") or "")
    no_dialogue = _dlg.should_suppress_dialogue(brief, flavors=flavors, plan=plan)
    prelim_exp_id = str(flavors.get("explicit") or "").strip()
    prelim_cam_id = str(flavors.get("camera") or "").strip()
    prelim_pose_id = str(flavors.get("pose") or "").strip()
    rear_prelim = _dir.is_rear_facing(brief, prelim_exp_id, plan=plan, plan_hint=plan_hint, camera_id=prelim_cam_id, pose_id=prelim_pose_id)
    mirror_prelim = _dir.is_mirror_scene_active(prelim_exp_id, prelim_cam_id)

    # 1. Character racial/ethnic, style & distinctive facial anchor locks
    _ward_opts_id = _cat.resolve_dial_opts("wardrobe", flavors.get("wardrobe"))
    _ward_snip = _fin.sanitize_additive_rule(_ward_opts_id[0].get("rule") or "") if _ward_opts_id else ""
    for s_n in sorted((lab.get("subjects") or {}).keys()):
        s_meta = (lab.get("subjects") or {}).get(s_n) or {}
        cname = s_meta.get("char_name") or s_meta.get("name") or ""
        cname_str = f" {cname}" if cname else ""
        for sp in [p for p in (lab.get("pictures") or []) if p.get("subject") == s_n]:
            s_desc = str(sp.get("desc") or "").strip()
            s_desc_id = s_desc.replace(_ward_snip, "").strip() if (_ward_snip and _ward_snip in s_desc) else s_desc
            eth = _refs.extract_ethnicity_phrase(s_desc_id, brief=brief)
            full_anchor = _refs.extract_identity_anchor_summary(s_desc_id, brief=brief, cap=180)
            if eth:
                if s_n == 1 and rear_prelim and not mirror_prelim:
                    eth_r = _refs.strip_front_facial_features_for_rear(eth)
                    rear_anchor = _refs.strip_front_facial_features_for_rear(full_anchor) if full_anchor else eth_r
                    extra_rear = f" (rear hair/build/style: `{rear_anchor}`)" if (rear_anchor and rear_anchor.lower() != eth_r.lower()) else ""
                    poss_p, _, _ = _infer_subject_pronouns(s_n, lab=lab, brief=brief, flavors=flavors)
                    facts.append(
                        f"CHARACTER IDENTITY LOCK (<Subject {s_n}>{cname_str} in {sp['label']}): "
                        f"Name as `{eth}` in `subject_definitions:`, `summary:`, `retention_analysis:`{extra_rear}; in `[Shot 1]` (rear view) write `{eth_r}` only, keeping {poss_p} face away from camera."
                    )
                else:
                    extra_anchor = f" — keep style/face/marks/build/hair (`{full_anchor}`)" if (full_anchor and full_anchor.lower() != eth.lower()) else ""
                    facts.append(
                        f"CHARACTER IDENTITY LOCK (<Subject {s_n}>{cname_str} in {sp['label']}): "
                        f"Identify as `{eth}` in `subject_definitions:`, `summary:`, `retention_analysis:`, and `[Shot 1]`{extra_anchor}."
                    )
                break
            elif s_desc_id:
                facts.append(
                    f"CHARACTER SHEET LOCK (<Subject {s_n}>{cname_str} in {sp['label']}): "
                    f"Preserve style and anchor from {sp['label']} ({(full_anchor or s_desc_id)[:180]}) in `subject_definitions:` and `retention_analysis:`."
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
                    f"Stage inside {sp['label']} and define it in `subject_definitions:`, `retention_analysis:`, and `[Shot 1]`."
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
    amb_opts = [o for o in _cat.resolve_dial_opts("ambience", flavors.get("ambience")) if o.get("id") not in ("none", "amb_none_na")]
    music_opts = _cat.resolve_dial_opts("music", flavors.get("music"))

    # Domain conflict & strict wardrobe/set lock (prevents shower+tennis+pool+foam bugs!)
    dom_conflicts = _cat.check_domain_conflicts(flavors)
    if dom_conflicts or ward_opts or place_opt:
        if place_opt and dom_conflicts:
            facts.append(
                f"STRICT ENVIRONMENT PRIORITY LOCK: Anchor walls, flooring, and props strictly to {place_opt['label']} (`domain={place_opt.get('domain', 'general')}`), discarding incompatible props from conflicting domains."
            )
        if ward_opts:
            wmode_lock = _bg.get_dial_mode(flavors, "wardrobe", "sequence")
            if len(ward_opts) >= 2 and wmode_lock == "split":
                subj_keys = sorted((lab.get("subjects") or {}).keys())
                pairs = []
                for idx, o in enumerate(ward_opts):
                    sn = subj_keys[idx] if idx < len(subj_keys) else (idx + 1)
                    s_meta = (lab.get("subjects") or {}).get(sn) or {}
                    cname = s_meta.get("char_name") or s_meta.get("name") or ""
                    s_lbl = f"<Subject {sn}> {cname}".strip()
                    w_rule = _fin.sanitize_additive_rule(o.get("rule") or _clean_ui_label(o["label"]))
                    pairs.append(f"{s_lbl}: {_clean_ui_label(o['label'])} ({w_rule})")
                facts.append(
                    f"WARDROBE LOCK (PER-SUBJECT SPLIT): Keep {', '.join(pairs)} consistent on their assigned subjects across `[Shot 1]` and every cut unless an explicit undress/displacement beat moves it aside."
                )
            elif len(ward_opts) >= 2 and wmode_lock == "sequence":
                alloc = _alloc_opts_to_timeline(ward_opts, spans, tree)
                facts.append(
                    "WARDROBE PROGRESSION (1->2): " + " -> ".join(
                        f"{_clean_ui_label(o['label'])} ({', '.join(ts for _, ts in bl)}): {_fin.sanitize_additive_rule(o.get('rule') or _clean_ui_label(o['label']))}"
                        for o, bl in alloc
                    )
                )
            else:
                w_desc = ", ".join(_clean_ui_label(o["label"]) for o in ward_opts)
                has_pic_spliced = bool(_ward_snip and any(_ward_snip in str(p.get("desc") or "") for p in (lab.get("pictures") or [])))
                w_rules = "" if has_pic_spliced else " | ".join(_fin.sanitize_additive_rule(o.get("rule") or "") for o in ward_opts if o.get("rule"))
                w_tail = f" ({w_rules})" if w_rules else ""
                facts.append(
                    f"WARDROBE LOCK: Keep `{w_desc}`{w_tail} consistent across `[Shot 1]` and every cut unless an explicit undress/displacement beat moves it aside."
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
    prelim_combat = _dir.is_combat(brief, str(flavors.get("combat") or ""), ward_id, str(flavors.get("fx") or ""))
    exp_ids_list = [x.lower() for x in _cat.parse_multi_ids(exp_id)]
    exp_is_cont_single = any(
        e.startswith("cont_") or e in ("stage_aftercare_cooldown_whisper", "stage_slow_grind_lap_tease_insertion")
        for e in exp_ids_list
    )
    exp_has_cuts = len(exp_opts) >= 2 or any(re.search(r"\[\s*Shot\s+2\s*\]", str(o.get("rule") or ""), re.I) for o in exp_opts)
    traj_law = _bg.camera_trajectory_plan(brief, cam_override or cam_id, spans, is_pov=is_pov, has_bg_plate=(has_bg_plate and not bool(place_opt)), is_combat=prelim_combat, explicit_id=exp_id)
    bp_label = "the approved plan" if str(plan or "").strip() else "the Shot-Tree blueprint"
    if len(cam_opts) == 1 and cam_opt and cam_opt.get("rule"):
        c_rule_s = _fin.sanitize_additive_rule(cam_opt["rule"])
        if exp_is_cont_single and re.search(r"\[\s*Shot\s+2\s*\]|\b(?:three-shot|two-shot\s+.*cut|hard[- ]cut|smash\s+cut)\b", c_rule_s, re.I):
            facts.append(
                f"SINGLE-TAKE CAMERA PRIORITY ({cam_opt['label']}): Keep ONE unbroken continuous camera take matching PRIMARY STAGING across every timestamp beat without cutting."
            )
        elif exp_has_cuts:
            facts.append(
                f"CAMERA FRAMING SUPPORT ({_clean_ui_label(cam_opt['label'])}): Honor PRIMARY STAGING and {bp_label}'s exact shot count, per-shot angles, positions, and active room."
            )
        elif not use_bp:
            facts.append(f"CAMERA MOVEMENT ({_clean_ui_label(cam_opt['label'])}): {c_rule_s}")
    elif len(cam_opts) >= 2:
        cmode = _bg.get_dial_mode(flavors, "camera", "sequence")
        if cmode == "blend":
            facts.append("CAMERA FUSION: " + " + ".join(f"{o['label']} ({_fin.sanitize_additive_rule(o.get('rule',''))})" for o in cam_opts))
        else:
            alloc = _alloc_opts_to_timeline(cam_opts, spans, tree)
            facts.append("MULTI-CAMERA PROGRESSION: " + " -> ".join(f"Shot {i+1} ({o['label']} at {', '.join(ts for _, ts in bl)}): {_fin.sanitize_additive_rule(o.get('rule',''))}" for i, (o, bl) in enumerate(alloc)))
    if traj_law:
        facts.append(traj_law)

    # Lighting, Optics, FX, Style, Colour, Era, World, Place, Character
    if light_opts:
        facts.append("LIGHTING: " + " + ".join(_fin.sanitize_additive_rule(o.get("rule") or o["label"]) for o in light_opts))
    if lens_opts:
        facts.append("OPTICS & FRAMING: " + " + ".join(_fin.sanitize_additive_rule(o.get("rule") or o["label"]) for o in lens_opts))
    if style_opts:
        if len(style_opts) >= 2 and _bg.get_dial_mode(flavors, "style", "sequence") == "sequence":
            alloc = _alloc_opts_to_timeline(style_opts, spans, tree)
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

    if len(place_opts) >= 2 and _bg.get_dial_mode(flavors, "place", "sequence") == "sequence":
        alloc_pl = _alloc_opts_to_timeline(place_opts, spans, tree)
        facts.append("SCENE PROGRESSION (1->2): " + " -> ".join(f"{_clean_ui_label(o['label'])} ({', '.join(ts for _, ts in bl)}): {_fin.sanitize_additive_rule(o.get('rule',''))}" for o, bl in alloc_pl))
    elif place_opt and place_opt.get("rule"):
        facts.append(f"SCENE SETTING ({_clean_ui_label(place_opt['label'])}): {_fin.sanitize_additive_rule(place_opt['rule'])}")
    if char_opts and not (lab.get("pictures")):
        facts.append("CAST ARCHETYPES: " + " | ".join(f"{_clean_ui_label(o['label'])} ({_fin.sanitize_additive_rule(o.get('rule',''))})" for o in char_opts))

    # Poses & Cinema Knowledge (only condense to Shot-Tree pointer when blueprint is active AND not overridden by explicit/combat)
    if pose_opts:
        if use_bp and not exp_opts and not combat_opts:
            p_lbls = " -> ".join(_clean_ui_label(o["label"]) for o in pose_opts)
            facts.append(f"POSE CHOREOGRAPHY ({p_lbls}): Follow {bp_label}'s micro-beat blocking.")
        elif len(pose_opts) >= 2 and _bg.get_dial_mode(flavors, "pose", "sequence") == "sequence":
            alloc = _alloc_opts_to_timeline(pose_opts, spans, tree)
            facts.append("POSE CHOREOGRAPHY SEQUENCE: " + " -> ".join(f"{_clean_ui_label(o['label'])} ({', '.join(ts for _, ts in bl)}): {_fin.sanitize_additive_rule(o.get('rule',''))}" for o, bl in alloc))
        else:
            facts.append("ANCHOR POSE: " + " + ".join(_fin.sanitize_additive_rule(o.get("rule") or _clean_ui_label(o["label"])) for o in pose_opts))

    cam_ids_parsed = _cat.parse_multi_ids(cam_id)
    has_multi_shot = len(cam_ids_parsed) >= 2 or any(
        c in (
            "shot_reverse", "multi_angle_action_close", "whip_pan_transition", "match_cut_motion",
            "graphic_match_cut", "smash_cut_contrast", "cam_viral_dutch_90roll_wipe_cuts",
            "cam_beat_drop_punch_wide_combo", "cam_palm_cover_lens_reveal_snap", "cam_whip_pan_beat_snap_cut",
            "cam_distant_wide_master_to_hardcut_closeup",
        )
        for c in cam_ids_parsed
    )
    for tok, _ref, kopt in _dir.knowledge_terms_in_brief(brief, picked_refs=picked_refs, is_multi_shot=has_multi_shot):
        facts.append(f"TERM DEFINITION ('{tok}' -> {_clean_ui_label(kopt['label'])}): {_fin.sanitize_additive_rule(kopt['rule'])}")

    # Ambience, Sound Mode, Music, Speech, Accent
    sm_w = _fin.resolve_sound_mode(brief=brief, flavors=flavors)
    pure_bgm_w = _fin.is_pure_bgm_soundscape(brief=brief, flavors=flavors)
    if pure_bgm_w:
        facts.append("SOUND MODE — PURE BGM (`overall_soundscape: N/A`): Omit footsteps, heel clicks, heavy breathing, cloth rustle, and impact foley cues from `detailed_description:` and set `overall_soundscape:` strictly to `N/A` so music plays unobstructed.")
    elif sm_w == "quiet_air":
        facts.append("SOUND MODE — QUIET AIR: Keep `overall_soundscape:` strictly soft, narrowband indoor room air and gentle stillness; omit loud footsteps, impacts, crunch, or heavy breath cues.")
        if amb_opts:
            facts.append("AMBIENCE FOLEY (softened, zero semicolons): " + ", ".join(_fin.scrub_foley_cues_in_description(_fin.sanitize_additive_rule(o.get("rule") or ""), mode="quiet_air") for o in amb_opts if o.get("rule")))
    elif sm_w == "foley":
        facts.append("SOUND MODE — FOLEY ON: Include crisp diegetic physical foley (footfalls, fabric motion, contact impacts, spatial acoustics) inside `overall_soundscape:` even when music is active.")
        if amb_opts:
            facts.append("AMBIENCE FOLEY (zero semicolons): " + ", ".join(_fin.sanitize_additive_rule(o.get("rule") or "") for o in amb_opts if o.get("rule")))
    elif amb_opts:
        facts.append("AMBIENCE FOLEY (zero semicolons): " + ", ".join(_fin.sanitize_additive_rule(o.get("rule") or "") for o in amb_opts if o.get("rule")))
    raw_music = _cat.parse_multi_ids(flavors.get("music"))
    if "none" in raw_music:
        facts.append("MUSIC: N/A (diegetic room audio only)")
    elif music_opts:
        facts.append("NON-DIEGETIC MUSIC (put ONLY in `non_diegetic_music:`, keep strictly separate from `overall_soundscape:`): " + ", ".join(_fin.sanitize_additive_rule(o.get("rule") or "") for o in music_opts if o.get("rule")))

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
        if (
            life_val == "natural"
            and motion_val == "natural"
            and energy_val == "steady"
            and expr_val == "natural"
        ):
            facts.append("PERFORMANCE BASELINE: Natural blinking/breathing, grounded movement speed, steady focus, and readable facial reactions.")
        else:
            facts.append(_dir.LIFE_RULES.get(life_val, _dir.LIFE_RULES["natural"]))
            facts.append(_dir.MOTION_RULES_GEN.get(motion_val, _dir.MOTION_RULES_GEN["natural"]))
            if no_dialogue and energy_val in ("charged", "peak", "large"):
                e_rule = (
                    "INTENSITY (charged): Spirited emotional urgency, athletic drive, and sharp physical momentum."
                    if energy_val == "charged"
                    else "INTENSITY (peak): Full dramatic intensity, sharp contrast, and commanding physical commitment."
                )
                facts.append(e_rule)
            else:
                facts.append(_dir.ENERGY_RULES_GEN.get(energy_val, _dir.ENERGY_RULES_GEN["steady"]))
            facts.append(_dir.EXPRESSION_RULES_GEN.get(expr_val, _dir.EXPRESSION_RULES_GEN["natural"]))
    if expr_read and expr_read != "auto" and (not sex_scene or not rear_scene or mirror_scene) and not mouth_occupied:
        er_rule = _dir.EXPRESSION_FLAVOR_RULES.get(expr_read)
        if er_rule:
            facts.append(er_rule)

    if is_pov:
        pov_lbl = "Male first-person POV" if pov_val == "male" else ("Female first-person POV" if pov_val == "female" else "First-person POV")
        facts.append(f"FIRST-PERSON POV CAMERA ({pov_lbl}): Write strictly from `my` / `I` eye-level perspective looking at the partner; keep my own head/face out of frame.")

    has_user_brief = bool(str(brief or "").strip())
    if has_user_brief:
        facts.append(
            "USER INTENT PRIORITY: Prioritize `<scene_brief>` above preset boilerplate—weave every requested action, prop, setting detail, camera ask, and spoken topic seamlessly."
        )
    # Explicit & Playbook stagings
    brief_fuse_note = " while integrating `<scene_brief>` as top priority" if has_user_brief else ""
    if exp_opts:
        if use_bp:
            e_lbls = " -> ".join(_clean_ui_label(o["label"]) for o in exp_opts)
            facts.append(f"PRIMARY STAGING ({e_lbls}): Follow {bp_label}'s cut count, camera angles, carried clothing/orientation, and physical contact{brief_fuse_note}.")
        elif len(exp_opts) >= 2:
            alloc = _alloc_opts_to_timeline(exp_opts, spans, tree)
            facts.append("MULTI-STAGE STAGING: " + " -> ".join(f"{_clean_ui_label(o['label'])} ({', '.join(ts for _, ts in bl)}): {_adapt_rule_subjects(_fin.sanitize_additive_rule(o.get('rule','')), lab, brief=brief, explicit_id=o['id'])}" for o, bl in alloc))
        else:
            facts.append(f"PRIMARY STAGING ({_clean_ui_label(exp_opt['label'])}): {_adapt_rule_subjects(_fin.sanitize_additive_rule(exp_opt.get('rule', '')), lab, brief=brief, explicit_id=exp_opt['id'])}")
        if exp_is_cont_single:
            facts.append(
                "CONTINUOUS POSITION TRANSITION LAW: Keep ONE unbroken shot (zero cuts) and bridge every posture or garment change step-by-step across beats while maintaining exact screen-left/right placement and surface contact."
            )
        elif (exp_has_cuts or any(e.startswith(("stage_", "multi_pos_")) for e in exp_ids_list)) and not use_bp:
            facts.append(
                "MULTI-SHOT POSITIONAL & ANGLE FIDELITY LAW: Follow PRIMARY STAGING's exact shot count; every `[Shot N]` cut MUST open with explicit camera distance/angle, screen-left/right placement, sticky displaced clothing, and concrete hand grips."
            )
        if anal_scene:
            facts.append(PRECISION_ANAL_ADDENDUM)

    if fetish_opts:
        for fb in fetish_opts:
            fdir = _dir.format_playbook_directive(fb, has_camera_or_explicit=bool(exp_opt or cam_opt or is_pov or rear_scene), has_subject_or_wardrobe=bool(ward_opt or lab.get("pictures")), has_brief=has_user_brief)
            facts.append(_dir.strip_d_examples(fdir) if (no_dialogue or talk_opt or acc_opt or energy_val in ("hush", "calm")) else fdir)
    elif sex_scene and not exp_opts:
        for fb in _dir.playbook_matches(brief, exp_id):
            fdir = _dir.format_playbook_directive(fb, has_camera_or_explicit=bool(cam_opt or is_pov or rear_scene), has_subject_or_wardrobe=bool(ward_opt or lab.get("pictures")), has_brief=has_user_brief)
            facts.append(_dir.strip_d_examples(fdir) if no_dialogue else fdir)

    d_dir = _dir.dance_vocab_directive(brief, pose_id=pose_id)
    if d_dir:
        facts.append(d_dir)
    is_dance_active = bool(
        d_dir
        or any(str(o.get("id") or "").startswith("dance_") or "dance" in str(o.get("group") or "").lower() for o in pose_opts)
    )
    if is_dance_active:
        facts.append(
            "COMPOUND MULTI-LAYER GROOVE (ZERO STIFF SINGLE-PART MOTION): Never animate just one isolated limb or joint — layer simultaneous footwork or bouncy hops, hip-and-pelvis drive, alternating shoulder-and-torso snaps, active arm/elbow rhythm, and hair inertia on every beat so dancers stay fluid and alive."
        )
    if is_dance_active and music_opts:
        m_bpm_hit = re.search(r"\b(\d{2,3})\s*BPM\b", " ".join(f"{o.get('label','')} {o.get('rule','')}" for o in music_opts), re.I)
        if m_bpm_hit:
            bpm_n = max(60, min(200, int(m_bpm_hit.group(1))))
            spb = round(60.0 / bpm_n, 2)
            bar4 = round(spb * 4.0, 2)
            facts.append(
                f"BEAT-GRID CHOREOGRAPHY SYNC ({bpm_n} BPM -> {spb:.2f}s/beat, {bar4:.2f}s/4-beat bar): "
                f"Time crisp kinetic hits, shoulder pops, reverse steps, drops, and freezes directly onto the {spb:.2f}s kick-and-snare grid with sharp micro-holds on counts rather than muddy continuous drift."
            )

    if combat_opts:
        if use_bp and not exp_opts:
            c_lbls = " -> ".join(_clean_ui_label(o["label"]) for o in combat_opts)
            facts.append(f"COMBAT CHOREOGRAPHY ({c_lbls}): Follow {bp_label}'s combat beat timing, spatial axis, and contact sequence{brief_fuse_note}.")
        elif len(combat_opts) >= 2:
            alloc = _alloc_opts_to_timeline(combat_opts, spans, tree)
            facts.append("COMBAT PROGRESSION: " + " -> ".join(f"{_clean_ui_label(o['label'])} ({', '.join(ts for _, ts in bl)}): {_fin.sanitize_additive_rule(o.get('rule',''))}" for o, bl in alloc))
        else:
            facts.append(f"COMBAT CHOREOGRAPHY ({_clean_ui_label(combat_opts[0]['label'])}): {_fin.sanitize_additive_rule(combat_opts[0].get('rule',''))}")

    nonfight_action = _is_nonfight_action_only(combat_opts, brief=brief)
    if bool(flavors.get("kinetic_grip", True)) and not sex_scene:
        if combat_scene and not nonfight_action:
            facts.append("KINETIC FLOW (COMBAT): Keep constant forward kinetic energy and sharp timing across every beat—follow the active preset's pacing without awkward static stalls or slow jogging.")
        elif nonfight_action:
            facts.append("KINETIC FLOW (ACTION STUNT): Maintain brisk athletic momentum, crisp prop handling, and continuous camera flow across every second.")
        elif motion_val in ("freeze", "slow"):
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
    if combat_scene and not nonfight_action:
        facts.append("COMBAT PHYSICS: Write concrete strike-to-dodge-to-impact-to-recoil mechanics with physically lit sparks, dust, shell casings, or elemental/force shockwaves.")
        if combat_opts:
            combat_blob = " ".join(f"{o.get('id', '')} {o.get('label', '')} {o.get('rule', '')}" for o in combat_opts)
            beat1_blob = re.split(r"(?:At\s+00:0[2-9]|\bin\s+Beat\s+2\b)", combat_blob, maxsplit=1, flags=re.I)[0]
            is_speed_blitz = bool(re.search(r"\b(?:speedster|lightning|flash[- ]?step|sandevistan|thunder\s*breathing|thunder\s*clap|blitz)\b", combat_blob, re.I))
            is_solo_charge_opener = bool(
                re.search(r"\b(?:coiled|iaido|scope|hand-seal|breath|raises\s+both\s+palms|sits\s+slouched)\b", beat1_blob, re.I)
                and not re.search(r"\b(?:rushes?|lunges?|strikes?|punches?|kicks?|shoots?|slices?|ducks?|parries?)\b", beat1_blob, re.I)
            )
            facts.append(
                "COMBAT PRESET FIDELITY LAW: Follow the active COMBAT CHOREOGRAPHY framing, camera axis, opponent count, and beat sequence strictly in crisp simple Subject-Verb-Object prose (`X punches -> Y ducks -> Y kicks X into steel`) rather than substituting unrelated moves or lateral framing."
            )
            if is_speed_blitz:
                facts.append(
                    "SPEEDSTER CONTINUOUS-VELOCITY LAW: When the opening beat is a solo charge-up, omit opponents completely from that opening beat (mention only the hero charging alone in tight foreground framing), then reveal opponents downrange on the next beat as the hero bursts at lightspeed past them; carry full supersonic speed and crackling lightning/afterimage trails ALL THE WAY through the penultimate/final finisher into a dynamic sliding skid rather than stopping early, jogging normally, or standing motionless."
                )
            elif is_solo_charge_opener:
                facts.append(
                    "COMBAT DYNAMIC CAMERA & PENULTIMATE ULTIMATE LAW: Hold coiled tension tightly in Beat 1, whip fast into relentless blow-for-blow clash across mid-beats with snappy tracking, low-angle sweeps, and upward tilts, drive a fast snap-zoom onto the signature ultimate attack strictly inside the next-to-last beat, and resolve cleanly on knockback crash, settling sparks/debris, and victor recovery in the final beat."
                )
            else:
                facts.append(
                    "COMBAT EARLY-START & PENULTIMATE ULTIMATE LAW: Erupt straight into fast blow-for-blow combat at 00:00.000 using urgent tracking, low crouching sweeps, upward jump-kick tilts, and whip pans, locking a tight push-in zoom onto the signature ultimate finisher strictly inside the next-to-last beat so the final beat cleanly finishes with crash recoil, settling debris, and victor readiness."
                )
        else:
            facts.append(
                "COMBAT EARLY-START & SIMPLE BLOW-FOR-BLOW LAW: Open intense fighting straight from 00:00.000 in crisp simple Subject-Verb-Object grammar (`X punches -> Y ducks -> Y kicks X into wall -> sparks fly`), packing maximum fast action into every beat while keeping every subject interacting continuously with opponents and surroundings."
            )
            facts.append(
                "COMBAT DYNAMIC CAMERA & PENULTIMATE ULTIMATE LAW: Drive fast, energetic fighting camera motion across jump kicks, crouching sweeps, mid-air clashes, and force blasts, executing a tight push-in zoom during the ultimate attack strictly inside the next-to-last beat; dedicate the final beat solely to knockback crash, settling debris, and victor recovery so the ultimate attack completes fully before the clip ends (keep every camera and body move fast and urgent, free of slow or soft pacing)."
            )

    if len((lab.get("subjects") or {}).keys()) >= 2 or (combat_scene and any(re.search(r"<Subject\s+2>|S1\s*(?:vs|\+)\s*S2", str(o.get("label") or "") + " " + str(o.get("rule") or ""), re.I) for o in combat_opts)):
        facts.append("SCREEN-AXIS GEOMETRY: Anchor each subject's screen-left / screen-right placement and eyeline direction in [Shot 1] and keep orientation consistent across cuts unless an orbit or cross-over moves them.")
        if pose_opts or combat_opts:
            facts.append("DUET ASYMMETRY & ROLE SPLIT: Preserve each subject's exact assigned screen depth, limb pose, solo vs crouched support role, and staggered timing rather than making both subjects perform identical mirrored gestures.")

    _geom_blob = " ".join([
        brief or "",
        " ".join(f"{o.get('id','')} {o.get('rule','')}" for o in (exp_opts + combat_opts + pose_opts)),
    ])
    if sex_scene or re.search(
        r"\b(?:cowgirl|mating press|doggy|spitroast|missionary|prone[- ]bone|facesit|straddl\w*|mounted|against (?:the )?wall|wall[- ]pin|lifted|carry|kote-gaeshi|harai-goshi|pak-sao|chi-sao|hurricanrana|waacking|gancho|ocho|contrapposto|tutting)\b",
        _geom_blob,
        re.I,
    ):
        facts.append(
            "3D GEOMETRY EXPANSION LAW: Spell out literal camera distance/angle showing support surfaces, vertical vs horizontal placement, exact facing vectors, knee/foot/hand anchors, and explicit turns before side-switches—never rely on shorthand move names."
        )

    s1_poss, _, _ = _infer_subject_pronouns(1, lab=lab, brief=brief, flavors=flavors)
    mixed_orient = _dir.has_mixed_front_and_rear_beats(brief, explicit_id=exp_id, plan=plan, plan_hint=plan_hint)
    mixed_oral = _dir.has_mixed_oral_beats(brief, explicit_id=exp_id, plan=plan, plan_hint=plan_hint)
    if sex_scene:
        facts.append("LITERAL ANATOMY LAW: Name anatomy and acts literally (`cock`, `erect penis`, `balls`, `pussy`, `labia`, `clit`, `asshole`, `bare breasts`, `nipples`, `cum`; `the man` / `his erect cock`)—never euphemisms.")
        if rear_scene and not anal_scene and not mirror_scene and not mixed_orient:
            facts.append("REAR-FACING LOCK: Keep torso, chest, shoulders, and head facing forward away from the camera across every beat.")
        elif mixed_orient:
            facts.append("TRANSITION ORIENTATION LOCK: Keep faces visible in front/oral/cowgirl beats; face away ONLY during rear-entry or reverse-cowgirl beats (preserving mirror reflections if active).")
        if over_shoulder:
            facts.append(f"OVER-SHOULDER LOCK: Keep hips and shoulders angled away while only {s1_poss} chin turns back over one shoulder.")
        if (solo_bj_oral or mouth_occupied) and not mixed_oral:
            facts.append("ORAL SEAL LAW: Keep lips sealed tightly around his cock during sucking beats, opening to pant only after pulling clear.")
        elif mixed_oral:
            facts.append("BEAT-SCOPED ORAL SEAL LAW: Keep lips sealed tightly in an O-ring with hollowed cheeks ONLY during sucking beats, opening naturally on kissing/riding beats.")
        if pegging_scene:
            facts.append("PEGGING LOCK: Keep her leather strap-on harness buckled snugly at hips and his cock and balls visible outside the anal contact.")

    if not no_dialogue:
        tm_mode = str(flavors.get("talk_mode") or "auto").strip().lower()
        has_quotes = bool(_dlg.extract_quotes(brief))
        has_speech_req = bool(re.search(r"\b(?:say\w*|speak\w*|talk\w*|whisper\w*|tell\w*|ask\w*|taunt\w*|mock\w*|teas\w*|flirt\w*|argu\w*|complain\w*|confess\w*|beg\w*|plead\w*|greet\w*|mutter\w*|murmur\w*|answer\w*|repl\w*|shout\w*|yell\w*|explain\w*|narrat\w*|sing\w*|banter\w*|joi|dirty\s*talk|dialogue|monologue)\b", brief or "", re.I))
        exp_has_dlg = (not has_user_brief) and any("<d>" in str(o.get("rule") or "") for o in exp_opts)
        fet_has_dlg = (not has_user_brief) and any(bool(fb.get("phrases")) for fb in fetish_opts)
        if has_quotes or talk_opt or acc_opt or fet_has_dlg or tm_mode == "talk_all" or has_speech_req or exp_has_dlg:
            if has_user_brief and not has_quotes:
                tone_hint_b = f" in {talk_opt['label']} delivery" if talk_opt else ""
                lang_hint_b = f" ({target_lang})" if target_lang != "English" else ""
                facts.append(
                    f"DIALOGUE INTENT FROM BRIEF: Write fresh, natural spoken `<d>...</d>` lines{tone_hint_b}{lang_hint_b} driven directly by `<scene_brief>`'s intent, emotion, and topic—never copy canned preset lines or generic filler."
                )
            else:
                cues = _dlg.pick_beat_dialogue_cues(brief=brief, talk_opt=talk_opt, acc_opt=acc_opt, playbook_entries=fetish_opts, n_beats=len(spans), is_sexual_scene=sex_scene)
                facts.append("SUGGESTED BEAT DIALOGUE ARC (adapt freely to voice & brief — keep fresh and natural): " + " | ".join(f"Beat {i+1}: `{c}`" for i, c in enumerate(cues)))
            if combat_scene or music_opts or amb_opts:
                facts.append("AUDIO FOREGROUND PRIORITY: Give spoken `<d>` beats clear vocal foreground while ducking heavy foley and music beneath, saving loud impacts and music peaks for wordless action beats.")
        else:
            facts.append("DIALOGUE CHOICE: Keep non-verbal, physical, or oral beats wordless with breathing/moans/wet foley in `overall_soundscape:`; add `<d>[tone] ...</d>` speech ONLY if the brief calls for spoken words.")
    else:
        if _fin.is_pure_bgm_soundscape(brief=brief, flavors=flavors, sex_scene=sex_scene, combat_scene=combat_scene):
            facts.append("SOUNDSCAPE OFF (PURE MUSIC PRIORITY): Characters perform with expressive posture and closed lips while `overall_soundscape:` stays `N/A` so environmental surf, footsteps, and foley stay off and `non_diegetic_music:` plays at full clarity.")
        elif sex_scene:
            facts.append("WORDLESS PERFORMANCE (ZERO SPOKEN <d> LINES): Keep all beats free of spoken words; describe natural breaths, moans, and wet oral or skin contact sounds in `overall_soundscape:` (zero spoken dialogue there).")
        elif _fin.resolve_sound_mode(brief=brief, flavors=flavors) == "quiet_air":
            facts.append("QUIET AIR PERFORMANCE: Characters perform with poised closed lips while `overall_soundscape:` carries only soft, narrowband indoor room air and gentle stillness.")
        else:
            facts.append("SILENT PERFORMANCE: Characters perform with expressive posture and closed lips while narrowband acoustic room tone and tactile foley fill `overall_soundscape:` (zero voices/speech there).")

    return [f for f in facts if f], cam_id


_split_long_single_clause = _st._split_long_single_clause


def _topo_from_spans_and_cuts(
    spans: list[tuple[float, float]],
    q_map: dict[int, list[str]],
    cuts: list[int],
    *,
    brief: str = "",
    flavors: dict | None = None,
) -> dict:
    flavors = flavors or {}
    dur = float(spans[-1][1]) if spans else 10.0
    auto_topo = _bg.compute_shot_topology(
        dur, brief=brief,
        camera_id=str(flavors.get("camera") or ""),
        explicit_id=str(flavors.get("explicit") or ""),
        flavors=flavors,
    )
    if (
        len(auto_topo["spans"]) == len(spans)
        and auto_topo["cuts"] == list(cuts or [])
        and all(abs(a[0] - b[0]) < 0.02 and abs(a[1] - b[1]) < 0.02 for a, b in zip(auto_topo["spans"], spans))
    ):
        if q_map:
            auto_topo["q_map"] = dict(q_map)
            flat_b = [b for sh in auto_topo["shots"] for b in sh["beats"]]
            for bi, qlist in q_map.items():
                if 0 <= bi < len(flat_b) and qlist:
                    flat_b[bi]["quotes"] = list(qlist)
                    flat_b[bi]["audio_fg"] = "dialogue"
        return auto_topo

    cut_set = set(int(c) for c in (cuts or []))
    shots_spec: list[dict] = []
    cur_beats: list[dict] = []
    shot_n = 1
    for i, (t0, t1) in enumerate(spans or [(0.0, dur)]):
        if i > 0 and i in cut_set and cur_beats:
            shots_spec.append({"shot_n": shot_n, "t0": cur_beats[0]["t0"], "t1": cur_beats[-1]["t1"], "beats": cur_beats})
            shot_n += 1
            cur_beats = []
        qs = list((q_map or {}).get(i) or [])
        cur_beats.append({
            "role": "opening_setup" if i == 0 else ("closing_hold" if i == len(spans) - 1 else "action_beat"),
            "role_label": f"Beat {i + 1}",
            "weight": max(0.1, float(t1) - float(t0)),
            "t0": float(t0),
            "t1": float(t1),
            "audio_fg": "dialogue" if qs else "foley",
            "quotes": qs,
        })
    if cur_beats:
        shots_spec.append({"shot_n": shot_n, "t0": cur_beats[0]["t0"], "t1": cur_beats[-1]["t1"], "beats": cur_beats})
    return {
        "duration_s": dur,
        "genre": auto_topo["genre"],
        "source": "multi_shot" if len(shots_spec) >= 2 else auto_topo["source"],
        "shots": shots_spec,
        "spans": list(spans),
        "cuts": list(cuts or []),
        "q_map": dict(q_map or {}),
    }


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
    tree: _st.ShotTree | None = None,
) -> str:
    flavors = flavors or {}
    if tree is None:
        topo = None if (extracted_video and extracted_video.get("beats") and not str(plan or "").strip()) else _topo_from_spans_and_cuts(
            spans, q_map, cuts, brief=brief, flavors=flavors,
        )
        dur = float(spans[-1][1]) if spans else 10.0
        tree = _st.build_shot_tree(
            dur, lab, brief=brief, flavors=flavors, extracted_video=extracted_video, plan=plan, topo=topo,
        )
    return _st.render_skeleton_prose(tree, lab, brief=brief, flavors=flavors)


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
    wmode_kf = _bg.get_dial_mode(flavors, "wardrobe", "sequence")
    if ward and wmode_kf == "split" and len(ward) >= 2 and len(lab.get("subjects") or {}) >= 2:
        subj_keys = sorted((lab.get("subjects") or {}).keys())
        for idx, o in enumerate(ward):
            if idx < len(subj_keys) and o.get("rule"):
                sn = subj_keys[idx]
                meta = lab["subjects"][sn]
                cname = meta.get("char_name") or meta.get("name") or f"Subject {sn}"
                parts.append(f"{cname} wearing {_fin.sanitize_additive_rule(o['rule'])}")
    elif ward and ward[0].get("rule"):
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
    tree: _st.ShotTree | None = None,
) -> dict:
    """Instant 0-LLM / 0-VRAM assembled H3 block built deterministically from active dials + wired refs."""
    flavors = flavors or {}
    mode = _std.mode_for(lab)
    if tree is None:
        topo = _bg.compute_shot_topology(
            duration_s, brief=brief, camera_id=str(flavors.get("camera") or ""),
            explicit_id=str(flavors.get("explicit") or ""), flavors=flavors,
        )
        tree = _st.build_shot_tree(
            duration_s, lab, brief=brief, flavors=flavors, extracted_video=extracted_video, topo=topo,
        )
    spans = tree.flat_spans()
    q_map = tree.q_map
    cuts = tree.flat_cuts()
    skel = build_skeleton_text(spans, q_map, cuts, lab, brief=brief, flavors=flavors, extracted_video=extracted_video, tree=tree)
    amb_opts = [o for o in _cat.resolve_dial_opts("ambience", flavors.get("ambience")) if o.get("id") not in ("none", "amb_none_na")]
    music_opts = _cat.resolve_dial_opts("music", flavors.get("music"))
    raw_music = _cat.parse_multi_ids(flavors.get("music"))
    sm_cpu = _fin.resolve_sound_mode(brief=brief, flavors=flavors)
    if _fin.is_pure_bgm_soundscape(brief=brief, flavors=flavors):
        snd = "N/A"
    elif sm_cpu == "quiet_air":
        if amb_opts:
            amb_q = ", ".join(_fin.scrub_foley_cues_in_description(_fin.sanitize_additive_rule(o.get("rule") or ""), mode="quiet_air") for o in amb_opts if o.get("rule"))
            snd = "Soft, narrowband quiet room air, " + amb_q if amb_q else "Soft, narrowband quiet indoor room air and gentle stillness."
        else:
            snd = "Soft, narrowband quiet indoor room air and gentle stillness."
    elif sm_cpu == "foley":
        snd = ", ".join(_fin.sanitize_additive_rule(o.get("rule") or "") for o in amb_opts if o.get("rule")) or "Crisp physical movement foley, natural footfalls, fabric motion, and spatial room acoustics."
    else:
        snd = ", ".join(_fin.sanitize_additive_rule(o.get("rule") or "") for o in amb_opts if o.get("rule")) or "Natural quiet room tone and tactile contact foley."
    mus = "N/A" if (str(flavors.get("music") or "").strip().lower() == "none" or "none" in raw_music or not music_opts) else (", ".join(_fin.sanitize_additive_rule(o.get("rule") or "") for o in music_opts if o.get("rule")) or "N/A")

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


DIALOGUE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["block"],
    "properties": {
        "block": {
            "type": "string",
            "description": "Complete updated H3 prompt block with refreshed `<d>[tone] ...</d>` spoken lines and unchanged visual staging, timestamps, labels, and audio sections.",
        }
    },
}

BLOCK_WRAP_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["block"],
    "properties": {
        "block": {
            "type": "string",
            "description": "Audited, polished H3 prompt block with all checklist fixes applied.",
        }
    },
}

PLAN_WRAP_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["plan"],
    "properties": {
        "plan": {
            "type": "string",
            "description": "Storyboard beats (`[Shot N] ...` and `At MM:SS.mmm-MM:SS.mmm, ...`) with updated native `<d>...</d>` dialogue.",
        }
    },
}


def _parse_json_obj(raw: str) -> dict | None:
    obj = _vcv.parse_lenient_json_obj(raw)
    if isinstance(obj, dict):
        return obj
    try:
        obj2 = _pl._parse_obj(str(raw or ""))
        return obj2 if isinstance(obj2, dict) else None
    except Exception:
        return None


def _extract_json_field(raw: str, key: str) -> str:
    txt = str(raw or "").strip()
    obj = _parse_json_obj(txt)
    if isinstance(obj, dict):
        return str(obj.get(key) or "").strip()
    m = re.search(rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"\\])*)"', txt, re.S)
    if m:
        try:
            return json.loads(f'"{m.group(1)}"')
        except Exception:
            return m.group(1).replace("\\n", "\n").replace('\\"', '"')
    return txt


def _ref_label_choices(lab: dict) -> list[str]:
    choices: list[str] = []
    for sn in sorted((lab.get("subjects") or {}).keys()):
        choices.append(f"<Subject {sn}>")
    for p in lab.get("pictures") or []:
        if p.get("subject") is None and not _refs.is_studio_backdrop_text(p.get("desc") or ""):
            choices.append(p["label"])
    for a in lab.get("audios") or []:
        choices.append(a["label"])
    return list(dict.fromkeys(choices))


def build_stage_schema(
    llm_stage: str,
    *,
    tree: _st.ShotTree,
    mode: str,
    lab: dict,
    brief: str = "",
    flavors: dict | None = None,
    silent: bool = False,
    target_lang: str = "English",
    time_tied: bool = True,
    plan: str = "",
) -> dict:
    """Build an OpenAI-strict JSON schema dynamically from `ShotTree`, `lab`, and active audio/speech dials."""
    flavors = flavors or {}
    plan_txt = str(plan or "").strip()
    plan_shot_count = len(re.findall(r"(?m)^\s*\[\s*Shot\s+\d+\s*\]", plan_txt)) if plan_txt else 0
    expected_shots = max(1, plan_shot_count if (llm_stage == "write" and plan_shot_count >= 1) else len(tree.shots))
    beat_counts = [max(1, len(sh.beats)) for sh in tree.shots] if tree.shots else [3]
    uniform_beats = (not plan_txt) and len(set(beat_counts)) == 1
    min_b = beat_counts[0] if uniform_beats else 1
    max_b = beat_counts[0] if uniform_beats else max(6, max(beat_counts) + 2)

    if silent:
        dlg_prop: dict = {
            "type": "string",
            "enum": [""],
            "description": "Empty string only (dialogue is suppressed).",
        }
    elif target_lang != "English":
        ex_nat = _dlg.native_sample_for(target_lang)
        ex_hint = f" e.g. '<d>[{target_lang}, soft] {ex_nat}</d>'" if ex_nat else ""
        dlg_prop = {
            "type": "string",
            "description": (
                f"Optional `<d>[{target_lang}, tone] ...</d>` spoken line written STRICTLY in native {target_lang} characters{ex_hint} "
                f"(zero English/romanized words inside `<d>`); empty string `\"\"` on wordless action beats."
            ),
        }
    else:
        dlg_prop = {
            "type": "string",
            "description": "Optional `<d>[delivery tone] Spoken line.</d>` with ASCII apostrophes on speaking beats ONLY; empty string `\"\"` on non-speaking or oral-sealed beats.",
        }

    beat_props: dict = {
        "action": {
            "type": "string",
            "description": "Affirmative physical action -> contact -> reaction (`<Subject 1> Name`, zero `<Subject N>'s`, zero spoken words).",
        },
        "spoken_dialogue": dlg_prop,
    }
    beat_req = ["action", "spoken_dialogue"]
    if plan_txt and llm_stage == "write":
        beat_props = {
            "t0": {"type": "string", "description": "Beat start `MM:SS.mmm`."},
            "t1": {"type": "string", "description": "Beat end `MM:SS.mmm`."},
            **beat_props,
        }
        beat_req = ["t0", "t1", "action", "spoken_dialogue"]

    shots_prop = {
        "type": "array",
        "minItems": expected_shots,
        "maxItems": expected_shots,
        "description": (
            f"Exactly {expected_shots} shot(s)"
            + (" matching `[Shot 1]`..`[Shot N]`." if expected_shots > 1 else " (one unbroken take, 0 cuts).")
        ),
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["shot_n", "opening_camera", "beats"],
            "properties": {
                "shot_n": {"type": "integer", "description": "1-based shot index."},
                "opening_camera": {
                    "type": "string",
                    "description": "Opening framing, distance/angle, move/lock, set/light, & displaced garments (omit `[Shot N]` / `At MM:SS`).",
                },
                "beats": {
                    "type": "array",
                    "minItems": min_b,
                    "maxItems": max_b,
                    "description": "Chronological beats." if (time_tied or expected_shots > 1) else "Sequential beats.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": beat_req,
                        "properties": beat_props,
                    },
                },
            },
        },
    }

    if llm_stage == "plan":
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["shots"],
            "properties": {"shots": shots_prop},
        }

    sm_sch = _fin.resolve_sound_mode(brief=brief, flavors=flavors)
    pure_bgm_sch = _fin.is_pure_bgm_soundscape(brief=brief, flavors=flavors)
    if pure_bgm_sch:
        soundscape_prop: dict = {
            "type": "string",
            "enum": ["N/A"],
            "description": "Literally 'N/A'.",
        }
    elif sm_sch == "quiet_air":
        soundscape_prop = {
            "type": "string",
            "description": "Comma-separated soft narrowband indoor room air (no semicolons/impacts/voices).",
        }
    else:
        soundscape_prop = {
            "type": "string",
            "description": "Comma-separated diegetic foley only (no semicolons, music, or speech).",
        }

    raw_music_sch = _cat.parse_multi_ids(flavors.get("music"))
    if str(flavors.get("music") or "").strip().lower() == "none" or "none" in raw_music_sch:
        music_prop: dict = {
            "type": "string",
            "enum": ["N/A"],
            "description": "Literally 'N/A'.",
        }
    else:
        music_prop = {
            "type": "string",
            "description": "Comma-separated music prose matching Music dial, or 'N/A' (no semicolons).",
        }

    if mode == "Ref2VA":
        ref_choices = _ref_label_choices(lab)
        ref_field: dict = (
            {"type": "string", "enum": ref_choices, "description": "Wired ref label."}
            if ref_choices
            else {"type": "string", "description": "Wired ref label (`<Subject N>`, `<Picture N>`, `<Audio N>`)."}
        )
        return {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "subject_definitions",
                "summary",
                "retention_analysis",
                "shots",
                "overall_soundscape",
                "non_diegetic_music",
            ],
            "properties": {
                "subject_definitions": {
                    "type": "string",
                    "description": "Static `<Subject N>`, scene `<Picture N>`, & `<Audio N>` definitions (one per line, no cross-subject positions/emojis).",
                },
                "summary": {
                    "type": "string",
                    "description": "One concise `[reference generation ...]` sentence using `<Subject N>` / `<Picture N>`.",
                },
                "retention_analysis": {
                    "type": "array",
                    "minItems": max(1, len(ref_choices)) if ref_choices else 1,
                    "description": "One entry per wired ref.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["ref", "state", "note"],
                        "properties": {
                            "ref": ref_field,
                            "state": {
                                "type": "string",
                                "enum": ["fully_preserved", "partially_preserved", "timbre_reference"],
                                "description": "Retention level.",
                            },
                            "note": {"type": "string", "description": "Identity, hair, & outfit state (no emojis)."},
                        },
                    },
                },
                "shots": shots_prop,
                "overall_soundscape": soundscape_prop,
                "non_diegetic_music": music_prop,
            },
        }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["shots", "overall_soundscape", "non_diegetic_music"],
        "properties": {
            "shots": shots_prop,
            "overall_soundscape": soundscape_prop,
            "non_diegetic_music": music_prop,
        },
    }


def _format_structured_dialogue(
    raw_dlg: str,
    *,
    lab: dict,
    silent: bool,
    target_lang: str,
    flavors: dict | None = None,
) -> str:
    d_txt = str(raw_dlg or "").strip()
    if silent or not d_txt:
        return ""
    subs = sorted((lab.get("subjects") or {}).keys())
    if subs:
        sn = subs[0]
        s_meta = (lab.get("subjects") or {}).get(sn) or {}
        cname = s_meta.get("char_name") or s_meta.get("name") or ""
        speaker = f"<Subject {sn}> {cname}".strip() if cname else f"<Subject {sn}>"
    else:
        speaker = "The lead character"
    audios = lab.get("audios") or []
    au_ref = f" using {audios[0]['label']}" if audios else ""

    if "(DIALOGUE)" in d_txt and "<d>" in d_txt.lower():
        return " " + d_txt
    if "<d>" in d_txt.lower():
        return f" (DIALOGUE) {speaker} (S1) speaks{au_ref}: {d_txt}"
    flavors = flavors or {}
    talk_opts = _cat.resolve_dial_opts("talkstyle", flavors.get("talkstyle"))
    tone_tag = _clean_ui_label(talk_opts[0]["label"]).split("(")[0].strip().lower() if talk_opts else "natural tone"
    return f" (DIALOGUE) {speaker} (S1) speaks{au_ref}: <d>[{target_lang}, {tone_tag}] {d_txt}</d>"


def _coerce_shots_list(shots_val) -> list:
    if isinstance(shots_val, list):
        return shots_val
    if isinstance(shots_val, dict):
        def _shot_sort_key(kv):
            k = str(kv[0])
            m = re.search(r"(\d+)", k)
            return (0, int(m.group(1)), k) if m else (1, 0, k)
        return [v for _, v in sorted(shots_val.items(), key=_shot_sort_key)]
    return []


def _format_string_shot(raw_shot: str, s_idx: int, t0_s: float) -> str:
    txt = str(raw_shot or "").strip()
    if not txt:
        return ""
    # Strip any accidental leading [Shot N] header so we normalize cleanly
    txt_no_hdr = re.sub(r"^\[\s*Shot\s+\d+\s*\]\s*", "", txt, flags=re.I).strip()
    if s_idx == 0:
        txt_no_hdr = re.sub(r"^At\s+00:00(?:\.000)?\s*,\s*", "", txt_no_hdr, flags=re.I).strip()
        return f"[Shot 1] {txt_no_hdr}"
    if re.match(r"^At\s+\d+:\d+(?:\.\d+)?\b", txt_no_hdr, re.I):
        return f"[Shot {s_idx + 1}] {txt_no_hdr}"
    m_ts = re.search(r"\bAt\s+(\d+:\d+(?:\.\d+)?)\b", txt_no_hdr, re.I)
    use_ts = m_ts.group(1) if m_ts else _bg.stamp(t0_s)
    return f"[Shot {s_idx + 1}] At {use_ts}, {txt_no_hdr}"


def _render_structured_shots(
    shots_raw,
    *,
    tree: _st.ShotTree,
    lab: dict,
    duration_s: float,
    silent: bool,
    target_lang: str,
    flavors: dict | None,
    time_tied: bool,
) -> str:
    lines: list[str] = []
    shots_seq = _coerce_shots_list(shots_raw)
    shots_clean = [sh for sh in shots_seq if isinstance(sh, dict) or (isinstance(sh, str) and sh.strip())]
    if not shots_clean:
        return ""

    # Compute shot boundaries if counts differ from ShotTree
    n_s = len(shots_clean)
    if n_s == len(tree.shots):
        shot_windows = [(sh.t0, sh.t1, sh.beats) for sh in tree.shots]
    else:
        raw_sp = _bg._allocate_weighted_spans(0.0, float(duration_s or 10.0), [1.0] * n_s)
        shot_windows = [(a, b, []) for a, b in raw_sp]

    for s_idx, sh_obj in enumerate(shots_clean):
        t0_s, t1_s, tree_beats = shot_windows[s_idx]
        if isinstance(sh_obj, str):
            norm_sh = _format_string_shot(sh_obj, s_idx, t0_s)
            if norm_sh:
                lines.append(norm_sh)
            continue

        cam = str(sh_obj.get("opening_camera") or sh_obj.get("camera") or "").strip()
        cam = re.sub(r"^\[\s*Shot\s+\d+\s*\](?:\s*At\s+\d+:\d+(?:\.\d+)?\s*,?)?\s*", "", cam, flags=re.I).strip() or "framed cleanly inside the scene"
        beats_raw = [b for b in (sh_obj.get("beats") or []) if isinstance(b, dict) and str(b.get("action") or "").strip()]
        shot_t0_str = _bg.stamp(t0_s)
        if s_idx > 0 and beats_raw:
            b0_t0 = str(beats_raw[0].get("t0") or "").strip()
            if re.fullmatch(r"\d+:\d+(?:\.\d+)?", b0_t0):
                shot_t0_str = b0_t0
        if s_idx == 0:
            lines.append(f"[Shot 1] {cam}")
        else:
            lines.append(f"[Shot {s_idx + 1}] At {shot_t0_str}, {cam}")

        if not beats_raw:
            raw_body = str(sh_obj.get("body") or sh_obj.get("description") or sh_obj.get("text") or "").strip()
            if raw_body:
                lines.append(raw_body)
            continue

        if not time_tied and n_s == 1:
            prose_parts = []
            for b_obj in beats_raw:
                act = str(b_obj.get("action") or "").strip().rstrip(".")
                dlg = _format_structured_dialogue(b_obj.get("spoken_dialogue") or "", lab=lab, silent=silent, target_lang=target_lang, flavors=flavors)
                if act:
                    prose_parts.append(f"{act}.{dlg}")
            if prose_parts:
                lines.append("")
                lines.append(" ".join(prose_parts))
            continue

        if len(beats_raw) == len(tree_beats):
            b_spans = [(mb.t0, mb.t1) for mb in tree_beats]
        else:
            b_spans = _bg._allocate_weighted_spans(t0_s, t1_s, [1.0] * len(beats_raw))

        for b_i, b_obj in enumerate(beats_raw):
            bt0_raw = str(b_obj.get("t0") or "").strip()
            bt1_raw = str(b_obj.get("t1") or "").strip()
            if re.fullmatch(r"\d+:\d+(?:\.\d+)?", bt0_raw) and re.fullmatch(r"\d+:\d+(?:\.\d+)?", bt1_raw):
                ts_a, ts_b = bt0_raw, bt1_raw
            else:
                ts_a, ts_b = _bg.stamp(b_spans[b_i][0]), _bg.stamp(b_spans[b_i][1])
            act = str(b_obj.get("action") or "").strip()
            act = re.sub(r"^At\s+\d+:\d+(?:\.\d+)?(?:\s*[-–—]\s*\d+:\d+(?:\.\d+)?)?\s*,\s*", "", act, flags=re.I).strip().rstrip(".")
            dlg = _format_structured_dialogue(b_obj.get("spoken_dialogue") or "", lab=lab, silent=silent, target_lang=target_lang, flavors=flavors)
            if act:
                lines.append(f"At {ts_a}-{ts_b}, {act}.{dlg}")

    return "\n".join(lines).strip()


def assemble_structured_or_text(
    raw_out: str,
    *,
    llm_stage: str,
    mode: str,
    lab: dict,
    tree: _st.ShotTree,
    duration_s: float,
    silent: bool,
    target_lang: str,
    flavors: dict | None = None,
    time_tied: bool = True,
) -> str:
    """Assemble decomposed structured schema JSON (`shots` + sections) or extract legacy `block` / `plan`."""
    obj = _parse_json_obj(raw_out)
    if isinstance(obj, dict):
        desc_body = ""
        if obj.get("shots"):
            desc_body = _render_structured_shots(
                obj["shots"],
                tree=tree,
                lab=lab,
                duration_s=duration_s,
                silent=silent,
                target_lang=target_lang,
                flavors=flavors,
                time_tied=time_tied,
            )
        elif any(re.fullmatch(r"shot_?\d+", str(k), re.I) for k in obj.keys()):
            shot_dict = {k: v for k, v in obj.items() if re.fullmatch(r"shot_?\d+", str(k), re.I)}
            desc_body = _render_structured_shots(
                shot_dict,
                tree=tree,
                lab=lab,
                duration_s=duration_s,
                silent=silent,
                target_lang=target_lang,
                flavors=flavors,
                time_tied=time_tied,
            )
        elif llm_stage != "plan":
            raw_desc = obj.get("detailed_description") or obj.get("integrated_multimodal_description")
            if isinstance(raw_desc, str) and raw_desc.strip():
                desc_body = raw_desc.strip()

        if desc_body:
            if llm_stage == "plan":
                return desc_body
            snd = str(obj.get("overall_soundscape") or "Natural quiet room tone.").strip()
            mus = str(obj.get("non_diegetic_music") or "N/A").strip()
            if mode == "Ref2VA":
                sdefs = str(obj.get("subject_definitions") or "").strip()
                summ = str(obj.get("summary") or "").strip()
                ret_raw = obj.get("retention_analysis")
                if isinstance(ret_raw, list):
                    ret_lines = []
                    for item in ret_raw:
                        if not isinstance(item, dict) or not item.get("ref"):
                            continue
                        r_lbl = str(item["ref"]).strip()
                        r_st = str(item.get("state") or "fully_preserved").strip()
                        r_nt = str(item.get("note") or "").strip()
                        ret_lines.append(f"{r_lbl}: {r_st}" + (f" - {r_nt}" if r_nt else ""))
                    ret = "\n".join(ret_lines).strip()
                else:
                    ret = str(ret_raw or "").strip()
                return (
                    f"subject_definitions:\n{sdefs}\n\n"
                    f"summary:\n{summ}\n\n"
                    f"retention_analysis:\n{ret}\n\n"
                    f"detailed_description:\n{desc_body}\n\n"
                    f"overall_soundscape:\n{snd}\n\n"
                    f"non_diegetic_music:\n{mus}"
                )
            return (
                f"integrated_multimodal_description:\n{desc_body}\n\n"
                f"overall_soundscape:\n{snd}\n\n"
                f"non_diegetic_music:\n{mus}"
            )
        fallback_key = "plan" if llm_stage == "plan" else "block"
        if obj.get(fallback_key):
            return str(obj[fallback_key]).strip()
    return _extract_json_field(raw_out, "plan" if llm_stage == "plan" else "block")


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
    structured_schema: bool | None = None,
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

    if stage not in ("skeleton", "cpu") and eye_scan and complete_fn is not None and (resolve_file_fn or any(p.get("source") == "refmod" for p in (lab.get("pictures") or []))):
        from . import vision_cv as _vcv
        rm_mod = _refs._refmod_module()
        for p in lab.get("pictures") or []:
            if not p.get("file"):
                continue
            exp_ret = str(p.get("explicit_retention") or "").strip().lower()
            raw_d = str(p.get("raw_desc") or "").strip().lower()
            role = "subject" if p.get("subject") is not None else ("prop" if exp_ret == "prop" or raw_d.startswith("prop:") else ("place" if raw_d.startswith(("set:", "place:", "room:")) and not flavors.get("place") else ("subject" if _refs.is_likely_person_ref(p, brief=brief, flavors=flavors) else "auto")))
            scanned = ""
            if p.get("source") == "refmod":
                if rm_mod is not None and (not p.get("desc") or _refs.is_studio_backdrop_text(p.get("desc") or "")):
                    rm_path = rm_mod.resolve(p["file"])
                    if rm_path:
                        rm_urls = rm_mod.vision_data_urls(p["file"], max_images=4, max_side=1024)
                        if rm_urls:
                            rm_meta = rm_mod.read_meta(rm_path) or {}
                            rm_role_meta = str(rm_meta.get("role") or "").strip().lower()
                            rm_role = _vcv.canonical_caption_role(rm_role_meta if rm_role_meta in ("wardrobe", "style", "bodyshape", "pose_motion", "background", "helper") else role)
                            rm_mtime = int(os.path.getmtime(rm_path)) if os.path.isfile(rm_path) else 0
                            rm_ck = f"refscan_v6|refmod:{_refs._clean_ref_file(p['file'], 'refmod')}|{rm_mtime}|{rm_role}"
                            scanned = await _vcv.scan_reference_urls(rm_urls, rm_role, complete_fn, cache_key=rm_ck)
            elif resolve_file_fn:
                fpath = resolve_file_fn(p["file"])
                if fpath:
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
    if ward_opts_init and lab.get("subjects"):
        w_ids_init = _cat.parse_multi_ids(flavors.get("wardrobe"))
        wmode_init = _bg.get_dial_mode(flavors, "wardrobe", "sequence")
        all_nude = bool({"nude_both_partners", "nude_all_cast_subjects_s1_s9"} & set(w_ids_init))
        subj_keys = sorted((lab.get("subjects") or {}).keys())
        for idx, s_n in enumerate(subj_keys):
            chosen_w = None
            if wmode_init == "split" and len(ward_opts_init) >= 2:
                if idx < len(ward_opts_init):
                    chosen_w = ward_opts_init[idx]
            elif s_n == 1 or all_nude:
                chosen_w = ward_opt
            if chosen_w:
                w_rule_clean = _fin.sanitize_additive_rule(chosen_w.get("rule") or _clean_ui_label(chosen_w.get("label") or ""))
                for p in lab.get("pictures") or []:
                    if p.get("subject") == s_n and w_rule_clean:
                        base_d = str(p.get("desc") or "")
                        anc = base_d.split("Wearing ")[0].strip() if "Wearing " in base_d else base_d
                        p["desc"] = f"{anc} {w_rule_clean}".strip() if anc else w_rule_clean

    topo = _bg.compute_shot_topology(
        duration_s, brief=brief, camera_id=str(flavors.get("camera") or ""),
        explicit_id=str(flavors.get("explicit") or ""), flavors=flavors,
    )
    tree = _st.build_shot_tree(
        duration_s, lab, brief=brief, flavors=flavors, extracted_video=extracted_video, plan=plan, topo=topo,
    )
    spans = tree.flat_spans()
    q_map = tree.q_map
    cuts = tree.flat_cuts()
    skel = build_skeleton_text(spans, q_map, cuts, lab, brief=brief, flavors=flavors, extracted_video=extracted_video, plan=plan, tree=tree)
    dur_adv = _bg.duration_advisory(duration_s, flavors=flavors)
    dom_conflicts = _cat.check_domain_conflicts(flavors)

    if stage == "skeleton":
        return {"ok": True, "stage": "skeleton", "mode": mode, "skeleton": skel, "plan": skel, "errors": [], "warnings": [], "duration_advisory": dur_adv, "domain_conflicts": dom_conflicts}

    if stage == "keyframe" or out_fmt == "h3_keyframe":
        kf = build_keyframe_prep_prompt(brief, flavors, lab=lab)
        return {"ok": True, "stage": "keyframe", "mode": mode, "block": kf, "plan": skel, "skeleton": skel, "errors": [], "warnings": [], "duration_advisory": dur_adv}

    if stage == "cpu" or complete_fn is None:
        res_cpu = build_cpu_tie_block(brief, lab=lab, duration_s=duration_s, flavors=flavors, extracted_video=extracted_video, tree=tree)
        res_cpu["duration_advisory"] = dur_adv
        res_cpu["domain_conflicts"] = dom_conflicts
        if updated_ref_plan != ref_plan:
            res_cpu["updated_ref_plan"] = updated_ref_plan
        return res_cpu

    use_structured_schema = True if structured_schema is None else bool(structured_schema)

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
        brief_hint_d = f"User Intent (follow closely for topic, tone, and meaning): {brief}\n" if str(brief or "").strip() else ""
        dlg_prompt = (
            "Rewrite ONLY the spoken `<d>[...] ...</d>` lines inside the prompt block below so they feel fresh, character-specific, distinct from beat to beat, and free of clichés, "
            "keeping EVERY physical action, pose, hand role, timestamp, camera instruction, and label unchanged. "
            "Size each line to its timestamp beat's seconds (~2 words per second so H3 never loops short lines), and connect clauses inside `<d>` with simple commas and periods (never `...` or `—`).\n"
            + brief_hint_d
            + (f"Speech register: {talk_opts[0]['label']} ({talk_opts[0].get('words','')})\n" if talk_opts else "")
            + lang_hint_d
            + f"\nReturn JSON `{{\"block\": \"...\"}}`.\n\n{cur_blk}"
        )
        raw_d = await complete_fn(
            [{"role": "system", "content": "You refresh spoken dialogue inside MiniMax H3 prompts without altering visual staging."}, {"role": "user", "content": dlg_prompt}],
            schema=(DIALOGUE_SCHEMA if use_structured_schema else None),
            temperature=0.95,
            max_tokens=2400,
        )
        raw_d_blk = _extract_json_field(raw_d, "block")
        new_blk = _fin.finish_block(raw_d_blk, mode=mode, lab=lab, duration_s=duration_s, silent=False, brief=brief, flavors=flavors) if len(raw_d_blk.strip()) >= 20 else ""
        errs_d = _std.contract_errors(new_blk, mode=mode, lab=lab, duration_s=duration_s) if new_blk else ["Empty dialogue rewrite returned."]
        return {"ok": bool(new_blk) and len(errs_d) == 0, "stage": "dialogue", "mode": mode, "block": new_blk, "plan": new_blk, "errors": errs_d}

    # Build user turn for `plan`, `write`, or `fast`
    llm_stage = "write" if stage == "fast" else stage
    silent = _dlg.should_suppress_dialogue(brief, flavors=flavors, plan=plan)
    acc_opts_rw = _cat.resolve_dial_opts("accent", flavors.get("accent"))
    target_lang_rw = _dlg.detect_target_language(brief, acc_opts_rw[0] if acc_opts_rw else None)
    time_tied = bool(flavors.get("time_tied", flavors.get("fast_engine", True)))
    has_extracted = bool(extracted_video and extracted_video.get("beats"))
    using_extracted_skel = bool(has_extracted and not str(plan or "").strip())
    using_blueprint = bool(time_tied and not using_extracted_skel and not (llm_stage == "write" and plan))
    flavor_lines, resolved_cam = build_flavor_facts(
        brief, flavors, spans, plan=plan, lab=lab, prev_hop_context=prev_hop_context, tree=tree, using_blueprint=using_blueprint,
    )

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
    has_top_brief = bool(str(brief or "").strip())
    if has_top_brief:
        lines.append("User Intent (TOP PRIORITY — weave every action, prop, setting detail, camera ask, and dialogue topic into dials & blueprint):")
        lines.append(_pl.fence(brief, "scene_brief"))
    lines.append("Active SandTie Directives & Continuity Laws:")
    lines += ["- " + fl for fl in flavor_lines]
    if has_extracted:
        if extracted_video.get("cuts") and not str(flavors.get("camera") or "").strip():
            lines.append("- EXTRACTED CUT & CAMERA LOCK: Preserve every `[Shot N]` hard cut boundary, transition type, camera move/roll/zoom, crop scale, and subject visibility from the extracted choreography verbatim rather than smoothing cuts into one take.")
        if extracted_video.get("cast"):
            lines.append(f"- Extracted Source Cast Layout: {extracted_video['cast']}")
        if (extracted_video.get("made_of") or extracted_video.get("style")) and not _cat.resolve_dial_opts("style", flavors.get("style")):
            style_hint = " — ".join(p for p in (extracted_video.get("made_of"), extracted_video.get("style")) if p)
            lines.append(f"- Extracted Visual Medium / Style Hint (when no style dial overrides): {style_hint}")
        if extracted_video.get("music") and not _cat.resolve_dial_opts("music", flavors.get("music")):
            lines.append(f"- Extracted Clip Music Hint (use in `non_diegetic_music:` if suitable): {extracted_video['music']}")
        if extracted_video.get("room") and not _cat.resolve_dial_opts("place", flavors.get("place")) and not any(p.get("subject") is None and not _refs.is_studio_backdrop_text(p.get("desc") or "") for p in (lab.get("pictures") or [])) and not brief:
            lines.append(f"- Extracted Setting Baseline (when no place dial/plate overrides): {extracted_video['room']}")
    is_sex_rw = _dir.is_sexual(brief, str(flavors.get("explicit") or ""), str(flavors.get("wardrobe") or ""), fetish_id=str(flavors.get("fetish") or ""))
    is_combat_rw = _dir.is_combat(brief, str(flavors.get("combat") or ""), str(flavors.get("wardrobe") or ""), str(flavors.get("fx") or ""))
    combat_opts_rw = _cat.resolve_dial_opts("combat", flavors.get("combat"))
    pose_opts_rw = _cat.resolve_dial_opts("pose", flavors.get("pose"))
    is_nonfight_rw = _is_nonfight_action_only(combat_opts_rw, brief=brief)
    is_dance_rw = bool(
        any(str(o.get("id") or "").startswith("dance_") or "dance" in str(o.get("group") or "").lower() for o in pose_opts_rw)
        or re.search(r"(?:^|[\s_-])(?:kpop|choreo|danc(?:e|ing|er))(?:$|[\s_-])", f"{flavors.get('pose') or ''} {brief or ''}", re.I)
    )
    is_duo_rw = len((lab.get("subjects") or {}).keys()) >= 2
    if using_extracted_skel:
        lines.append("Extracted Reference Video Choreography (preserve EVERY `[Shot N]` cut boundary, camera framing/roll/zoom, visible subject slot, and chronological motion faithfully while binding wired cast, wardrobe, and place):")
        lines.append(_pl.fence(skel, "extracted_choreography"))
    elif llm_stage == "write" and plan:
        inv_txt = _st.render_state_invariants(tree, plan=plan)
        if inv_txt:
            lines.append("Carried State Invariants (keep these wardrobe/orientation states consistent across cuts):")
            lines.append(_pl.fence(inv_txt, "state_ledger_invariants"))
    elif time_tied:
        blueprint_txt = _st.render_llm_blueprint(tree, lab, brief=brief, flavors=flavors, include_brief=(not has_top_brief))
        lines.append("Shot-Tree & State-Ledger Blueprint (honor exact `[Shot N]` cuts, carried outfit/orientation states, and action-weighted micro-beat clocks while writing vivid kinetic prose):")
        lines.append(_pl.fence(blueprint_txt, "shot_blueprint"))
    else:
        lines.append("Single-Thought Rhythm Example (structure guide only — fill with your active brief, cast, and dials):")
        lines.append(_pl.fence(_genre_micro_example(sex_scene=is_sex_rw, combat_scene=is_combat_rw, has_dance=is_dance_rw, mode=mode, duo=is_duo_rw, has_combat_preset=bool(combat_opts_rw), nonfight_action=is_nonfight_rw), "rhythm_example"))
        inv_txt = _st.render_state_invariants(tree)
        if inv_txt:
            lines.append("Carried State Invariants (honor cut count, cast axes, and active outfit states without forcing rigid timestamps):")
            lines.append(_pl.fence(inv_txt, "state_ledger_invariants"))
    if not has_top_brief:
        eff_brief = (str(extracted_video.get("summary") or "").strip() if has_extracted else "") or "Perform the staged scene cleanly."
        lines.append("Scene Brief:")
        lines.append(_pl.fence(eff_brief, "scene_brief"))
    if llm_stage == "write" and plan:
        lines.append("Approved Storyboard (expand cleanly into full H3 prompt):")
        lines.append(_pl.fence(plan, "approved_plan"))

    if use_structured_schema:
        stage_schema = build_stage_schema(
            llm_stage,
            tree=tree,
            mode=mode,
            lab=lab,
            brief=brief,
            flavors=flavors,
            silent=silent,
            target_lang=target_lang_rw,
            time_tied=time_tied,
            plan=plan,
        )
        if llm_stage == "plan":
            shape_hint = '{"shots": [{"shot_n": 1, "opening_camera": "...", "beats": [{"action": "...", "spoken_dialogue": ""}]}]}'
        elif mode == "Ref2VA":
            shape_hint = (
                '{"subject_definitions": "...", "summary": "...", '
                '"retention_analysis": [{"ref": "<Subject 1>", "state": "fully_preserved", "note": "..."}], '
                '"shots": [{"shot_n": 1, "opening_camera": "...", "beats": [{"action": "...", "spoken_dialogue": ""}]}], '
                '"overall_soundscape": "...", "non_diegetic_music": "..."}'
            )
        else:
            shape_hint = (
                '{"shots": [{"shot_n": 1, "opening_camera": "...", "beats": [{"action": "...", "spoken_dialogue": ""}]}], '
                '"overall_soundscape": "...", "non_diegetic_music": "..."}'
            )
        lines.append(f"Return ONLY valid JSON matching this schema shape: {shape_hint}")
    else:
        stage_schema = None
        if llm_stage == "plan":
            lines.append(
                'Return ONLY valid JSON: {"plan": "<clean storyboard lines starting with [Shot 1] ... and At MM:SS.mmm-MM:SS.mmm, ...>"}'
            )
        elif mode == "Ref2VA":
            lines.append(
                'Return ONLY valid JSON: {"block": "<complete H3 Ref2VA prompt starting directly with subject_definitions: and ending with overall_soundscape: and non_diegetic_music:>"}'
            )
        else:
            lines.append(
                'Return ONLY valid JSON: {"block": "<complete H3 T2VA prompt starting directly with integrated_multimodal_description: and ending with overall_soundscape: and non_diegetic_music:>"}'
            )

    user_content: object = "\n".join(lines)
    if images or start_image:
        pic_by_tag = {str(p.get("tag") or "").lstrip("@"): p for p in (lab.get("pictures") or []) if p.get("tag")}
        parts: list[dict] = [{"type": "text", "text": str(user_content)}]
        for im in images or []:
            if isinstance(im, dict) and im.get("data_url"):
                im_tag = str(im.get("tag") or "").lstrip("@")
                p_meta = pic_by_tag.get(im_tag)
                if p_meta:
                    who_lbl = f" (<Subject {p_meta['subject']}>)" if p_meta.get("subject") is not None else ""
                    cap = f"{p_meta['label']} (@{im_tag}){who_lbl}:"
                elif im.get("caption"):
                    cap = str(im["caption"]).strip()
                elif im_tag:
                    cap = f"@{im_tag}:"
                else:
                    cap = ""
                if cap:
                    parts.append({"type": "text", "text": cap})
                parts.append({"type": "image_url", "image_url": {"url": im["data_url"]}})
        if start_image:
            parts.append({"type": "text", "text": "Start image (Frame 0, no @tag):"})
            parts.append({"type": "image_url", "image_url": {"url": start_image}})
        user_content = parts

    sys_prompt_rw = build_system_prompt(
        llm_stage=llm_stage,
        mode=mode,
        is_sex=is_sex_rw,
        is_combat=is_combat_rw,
        has_brief=has_top_brief,
        need_3d_geom=any("3D GEOMETRY EXPANSION LAW" in fl for fl in flavor_lines),
        use_structured_schema=use_structured_schema,
        target_lang=target_lang_rw,
        silent=silent,
    )
    raw_out = await complete_fn(
        [
            {"role": "system", "content": sys_prompt_rw},
            {"role": "user", "content": user_content},
        ],
        schema=stage_schema,
        temperature=0.85,
        max_tokens=2800,
    )

    if llm_stage == "plan":
        raw_plan = assemble_structured_or_text(
            raw_out,
            llm_stage="plan",
            mode=mode,
            lab=lab,
            tree=tree,
            duration_s=duration_s,
            silent=silent,
            target_lang=target_lang_rw,
            flavors=flavors,
            time_tied=time_tied,
        )
        cleaned_plan = _fin.clean_plan_output(raw_plan, duration_s=duration_s, silent=silent)
        if cleaned_plan and not silent and target_lang_rw != "English" and _dlg.language_script_missing(cleaned_plan, target_lang_rw):
            try:
                fix_plan_msg = (
                    f"Language is set to {target_lang_rw}, yet `<d>...</d>` dialogue in your storyboard used English/romanization. "
                    f"Translate EVERY spoken line inside `<d>[{target_lang_rw}, ...] ...</d>` into natural native {target_lang_rw} script/characters "
                    f"(sample: `{_dlg.native_sample_for(target_lang_rw)}`), keeping timestamps and action descriptions intact.\n"
                    f"Return JSON `{{\"plan\": \"...\"}}`.\n\n{cleaned_plan}"
                )
                raw_p_fix = await complete_fn(
                    [
                        {"role": "system", "content": "You translate spoken `<d>...</d>` lines inside MiniMax H3 storyboards into native script without altering visual staging."},
                        {"role": "user", "content": fix_plan_msg},
                    ],
                    schema=(PLAN_WRAP_SCHEMA if use_structured_schema else None),
                    temperature=0.45,
                    max_tokens=2400,
                )
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

    raw_blk = assemble_structured_or_text(
        raw_out,
        llm_stage="write",
        mode=mode,
        lab=lab,
        tree=tree,
        duration_s=duration_s,
        silent=silent,
        target_lang=target_lang_rw,
        flavors=flavors,
        time_tied=time_tied,
    )
    blk = _fin.finish_block(raw_blk, mode=mode, lab=lab, duration_s=duration_s, silent=silent, brief=brief, flavors=flavors)

    # Optional Pass-2 Double-Knot refinement (also triggers automatically on contract defects or non-English <d> script repair!)
    double_knot = bool(flavors.get("double_knot", flavors.get("pass2_refine", True)))
    need_lang_repair = bool(blk and not silent and target_lang_rw != "English" and _dlg.language_script_missing(blk, target_lang_rw))
    pass1_errs = _std.contract_errors(blk, mode=mode, lab=lab, duration_s=duration_s) if blk else []
    if (double_knot or need_lang_repair or pass1_errs) and blk:
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
            prev_hop_context=prev_hop_context, tree=tree,
        )
        if pass1_errs:
            checklist = [f"CONTRACT REPAIR: Fix `{pe}` cleanly in Pass 2." for pe in pass1_errs[:4]] + checklist
        if checklist:
            p2_user = "Audit Checklist:\n" + "\n".join(f"- {c}" for c in checklist) + "\n\nPass-1 Draft:\n" + blk
            try:
                raw_p2 = await complete_fn(
                    [
                        {"role": "system", "content": _fin.PASS2_REFINE_SYSTEM_PROMPT},
                        {"role": "user", "content": p2_user},
                    ],
                    schema=(BLOCK_WRAP_SCHEMA if use_structured_schema else None),
                    temperature=0.45,
                    max_tokens=2800,
                )
                refined = assemble_structured_or_text(
                    raw_p2,
                    llm_stage="write",
                    mode=mode,
                    lab=lab,
                    tree=tree,
                    duration_s=duration_s,
                    silent=silent,
                    target_lang=target_lang_rw,
                    flavors=flavors,
                    time_tied=time_tied,
                )
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
    if time_tied:
        out_plan = "\n".join(ln.strip() for ln in desc_val.splitlines() if re.match(r"^(?:\[Shot\s+\d+\]|At\s+\d{2}:\d{2}\.\d{3})", ln.strip())).strip() or skel
    else:
        out_plan = desc_val.strip() or skel
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
