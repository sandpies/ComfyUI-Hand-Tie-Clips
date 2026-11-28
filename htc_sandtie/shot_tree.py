"""Shot-Tree, StateLedger, and Dual Renderer (H3 Prose + LLM Blueprint) for SandTie."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from . import beat_grid as _bg
from . import catalogs as _cat
from . import dialogue as _dlg
from . import director_cards as _dir
from . import finisher as _fin


@dataclass
class MicroBeat:
    t0: float
    t1: float
    role: str
    role_label: str
    weight: float = 1.0
    action: str = ""
    audio_fg: str = "foley"
    quotes: list[str] = field(default_factory=list)
    state_delta: dict[str, str] = field(default_factory=dict)
    state_after: dict[str, str] = field(default_factory=dict)
    dialogue_text: str = ""
    is_canned_cue: bool = False


@dataclass
class ShotNode:
    shot_n: int
    t0: float
    t1: float
    camera: str = ""
    place: str = ""
    axis_lock: str = ""
    carried_state: dict[str, str] = field(default_factory=dict)
    beats: list[MicroBeat] = field(default_factory=list)


@dataclass
class ShotTree:
    duration_s: float
    genre: str
    source: str
    pov: str = "off"
    canvas_aspect: str = ""
    initial_state: dict[str, Any] = field(default_factory=dict)
    shots: list[ShotNode] = field(default_factory=list)
    q_map: dict[int, list[str]] = field(default_factory=dict)
    header_s1: str = ""
    cam_s1: str = ""
    is_extracted: bool = False
    brief: str = ""

    def flat_spans(self) -> list[tuple[float, float]]:
        return [(b.t0, b.t1) for sh in self.shots for b in sh.beats]

    def flat_cuts(self) -> list[int]:
        cuts: list[int] = []
        idx = 0
        for s_i, sh in enumerate(self.shots):
            if s_i > 0:
                cuts.append(idx)
            idx += len(sh.beats)
        return cuts

    def flat_beats(self) -> list[tuple[ShotNode, MicroBeat]]:
        return [(sh, b) for sh in self.shots for b in sh.beats]

    def shot_count(self) -> int:
        return len(self.shots)


_PARTICIPLE_TO_FINITE = {
    "bracing": "braces", "kneeling": "kneels", "straddling": "straddles", "standing": "stands",
    "leaning": "leans", "lying": "lies", "pressing": "presses", "bouncing": "bounces",
    "gripping": "grips", "sliding": "slides", "pulling": "pulls", "wrapping": "wraps",
    "looking": "looks", "lowering": "lowers", "climbing": "climbs", "arching": "arches",
    "holding": "holds", "rocking": "rocks", "grinding": "grinds", "riding": "rides",
    "driving": "drives", "sucking": "sucks", "stroking": "strokes", "kissing": "kisses",
    "facing": "faces", "sitting": "sits", "hovering": "hovers", "resting": "rests",
    "crawling": "crawls", "balancing": "balances", "bending": "bends",
    "seated": "sits", "perched": "perches", "pinned": "stays pinned", "draped": "drapes",
    "hiking": "hikes", "lifting": "lifts", "tugging": "tugs", "pushing": "pushes",
    "tilting": "tilts", "turning": "turns", "pivoting": "pivots",
    "thrusting": "thrusts", "spreading": "spreads", "grasping": "grasps", "clasping": "clasps",
    "reaching": "reaches", "rubbing": "rubs", "gliding": "glides",
    "guiding": "guides", "sinking": "sinks", "dropping": "drops", "whipping": "whips",
    "striking": "strikes", "blocking": "blocks", "parrying": "parries", "ducking": "ducks",
    "leaping": "leaps", "firing": "fires", "reloading": "reloads", "spinning": "spins",
    "snapping": "snaps", "flaring": "flares", "smiling": "smiles", "panting": "pants",
    "taking": "takes", "wrapping": "wraps", "stroking": "strokes", "opening": "opens",
    "parting": "parts", "revealing": "reveals", "exposing": "exposes", "ejecting": "ejects",
    "landing": "lands", "staring": "stares", "clenching": "clenches", "raising": "raises",
    "sweeping": "sweeps", "stepping": "steps", "locking": "locks", "keeping": "keeps",
    "establishing": "braces", "bringing": "brings", "cocking": "cocks",
}

_GARMENT_SHIFT_RX = re.compile(
    r"(?:"
    r"(?:pull(?:s|ing)?|tug(?:s|ging)?|hook(?:s|ing)?|slid(?:e|es|ing)|push(?:es|ing)?|hik(?:e|es|ing)|bunch(?:es|ing)?|lift(?:s|ing)?|drop(?:s|ping)?|lower(?:s|ing)?|unbutton(?:s|ing)?|unzip(?:s|ping)?|peel(?:s|ing)?|strip(?:s|ping)?|remov(?:e|es|ing)|shed(?:s|ding)?|part(?:s|ing)?|slip(?:s|ping)?)"
    r"\s+(?:her|his|their|the)?\s*"
    r"(?:(?:[a-z]+\s+){0,3}?(?:dress|skirt|hem(?:line)?|top|shirt|blouse|sweater|cardigan|jacket|coat|bra|strap|panties|thong|underwear|lingerie|bodysuit|bikini(?:\s+bottoms?|\s+top)?|shorts|jeans|pants|trousers|zipper|fly|robe|kimono|towel|leggings|stockings))"
    r"(?:\s+(?:aside|up|high|down|off|open|smoothly|tautly|to\s+(?:the\s+)?(?:waist|hips?|knees?|ankles?|side)|(?:high\s+)?above\s+(?:her|the)\s+(?:waist|hips?|bare\s+breasts?|breasts?)|(?:high\s+)?over\s+(?:her|the)\s+(?:bare\s+)?breasts?|off\s+(?:her\s+)?shoulders?|toward\s+the\s+camera))*"
    r"|"
    r"(?:dress|skirt|hem(?:line)?|top|shirt|blouse|sweater|bra|panties|thong|bikini(?:\s+bottoms?)?|shorts|jeans|robe|towel)"
    r"\s+(?:is\s+|stays\s+|kept\s+)?"
    r"(?:bunched|lifted|hiked|pulled\s+aside|tucked\s+up|pushed\s+(?:up|down|aside)|unbuttoned|unzipped|lowered|dropped|removed|off\s+one\s+shoulder)"
    r"(?:\s+(?:high\s+)?(?:at|above|around|to|over)\s+(?:her|his|the)\s+(?:waist|hips?|ribs?|knees?|ankles?|bare\s+breasts?))*"
    r")",
    re.I,
)

_GARMENT_KEY_RX = re.compile(
    r"\b(dress|skirt|hem|top|shirt|blouse|sweater|bra|panties|thong|underwear|lingerie|bodysuit|bikini|shorts|jeans|pants|robe|kimono|towel|leggings)\b",
    re.I,
)

_REAR_BEAT_RX = re.compile(
    r"\b(?:from\s+behind|rear\s+three[- ]quarter|rear\s+3/4|low\s+rear|"
    r"facing\s+(?:forward\s+(?:toward\s+(?:his|her)\s+feet\s+)?)?away(?:\s+from\s+(?:the\s+)?(?:lens|camera))?|"
    r"bare\s+back(?:\s+and\s+(?:rounded\s+)?(?:glutes|ass(?:\s+cheeks)?))?\s+(?:facing|toward)\s+(?:the\s+)?(?:lens|camera)|"
    r"all\s+fours|doggy(?:-style)?|reverse\s+cowgirl|bent\s+(?:forward\s+)?over|"
    r"bare\s+back\s+and\s+(?:rounded\s+)?glutes\s+toward|back\s+arched\s+toward)\b",
    re.I,
)

_FRONT_BEAT_RX = re.compile(
    r"\b(?:facing\s+each\s+other|face[- ]to[- ]face|facing\s+(?:forward(?!\s+(?:toward\s+(?:his|her)\s+feet\s+)?away\s+from)|camera)|"
    r"missionary|upright\s+cowgirl|straddling\s+chest[- ]to[- ]chest|kneel(?:s|ing)?\s+(?:upward\s+)?between\s+(?:his|her|both)|looks?\s+up\s+at|lock(?:s|ing)?\s+lips)\b",
    re.I,
)

_MIRROR_BEAT_RX = re.compile(r"\b(?:mirror(?!-bright|-like|-finish|-gloss|-shine)|two-plane|reflection)\b", re.I)

_ORAL_ACTIVE_RX = re.compile(
    r"\b(?:suck(?:s|ing)?|lips\s+sealed|seal(?:s|ing)(?:\s+\w+){0,2}\s+lips|takes?\s+(?:his\s+)?(?:erect\s+)?cock\s+into\s+(?:her\s+)?mouth|deepthroat(?:s|ing)?|bobs?\s+(?:her\s+)?head|glides?\s+(?:her\s+)?lips\s+up\s+and\s+down|wraps?\s+(?:her\s+)?lips\s+around)\b",
    re.I,
)

_ORAL_FREE_RX = re.compile(
    r"\b(?:pulls?\s+(?:clear|back|off)|pops?\s+(?:her\s+)?lips\s+free|parted\s+lips|thick\s+white\s+ropes|ropes?\s+arc|onto\s+her\s+(?:bare\s+)?(?:face|chest|breasts|tongue|lips)|facial|finishes?\s+on|kiss(?:es|ing)?|smiles?|speaks?|pants?\s+openly|drops?\s+onto|straddles?|rides?)\b",
    re.I,
)

_HANDJOB_RX = re.compile(
    r"\b(?:handjob|wraps?\s+(?:her\s+)?(?:manicured\s+|oiled\s+)?fingers\s+around|strokes?\s+(?:swiftly\s+|slowly\s+|briskly\s+)?(?:base-to-tip|his\s+(?:hard\s+|erect\s+)?(?:cock|shaft))|two-hand\s+stroke|pumps?\s+his\s+(?:hard\s+|erect\s+)?(?:cock|shaft))\b",
    re.I,
)

_INTERCOURSE_RX = re.compile(
    r"\b(?:thrusts?|pounding|drives?\s+(?:his\s+|her\s+|deep)|sinks?\s+(?:all\s+the\s+way|down|onto|into)|penetration|creampie|doggy|missionary|cowgirl|mating\s+press|spitroast|inside\s+her\s+(?:wet\s+)?(?:pussy|vagina|anus)|into\s+her\s+(?:wet\s+)?(?:pussy|vagina|anus)|bounces?\s+(?:her\s+)?(?:bare\s+)?(?:hips|glutes))\b",
    re.I,
)

_SOLO_ACT_RX = re.compile(
    r"\b(?:masturbat|dildo|vibrator|wand|clit|rubs?\s+her\s+own|fingers?\s+her\s+(?:wet\s+)?pussy|zipper\s+(?:slowly\s+|smoothly\s+)?downward|pours?\s+a\s+glistening\s+stream)\b",
    re.I,
)

_CUMSHOT_RX = re.compile(
    r"\b(?:ropes?\s+(?:of\s+)?(?:cum|semen)|thick\s+(?:glossy\s+)?white\s+ropes|eruption\s+onto|facial\s+cumshot|pearlescent\s+semen|drips?\s+from\s+her|ejaculat\w+)\b",
    re.I,
)

_PROP_SURFACE_RX = re.compile(
    r"\b(marble\s+(?:kitchen\s+)?island|kitchen\s+(?:counter|island)|shower\s+(?:glass|wall|door)|vanity\s+counter|glass\s+wall|velvet\s+sofa|leather\s+sofa|sofa|couch|bed|mattress|executive\s+desk|desk|balcony\s+railing|railing|car\s+hood|hood|hot\s+tub|tub|pool\s+edge|bar\s+counter)\b",
    re.I,
)


def clean_ui_label(label: str) -> str:
    """Strip UI emojis and all-caps menu category prefixes from dial labels."""
    s = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+", "", str(label or "")).strip()
    s = re.sub(
        r"^(?:NUDE(?:\s*\([^)]*\))?|FETISH(?:\s+NUDE)?|PARTIAL|TOPLESS|BOTTOMLESS)\s*[—\-–:]+\s*",
        "",
        s,
        flags=re.I,
    )
    return re.sub(r"\s{2,}", " ", s).strip()


def sanitize_beat_clause(text: str) -> str:
    return _fin.sanitize_additive_rule(_dir.strip_d_examples(text or ""))


def infer_subject_pronouns(s_n: int, lab: dict | None = None, brief: str = "", flavors: dict | None = None) -> tuple[str, str, str]:
    """Infer `(possessive, object, subject)` pronouns (`her/her/she` vs `his/him/he`)."""
    lab = lab or {}
    flavors = flavors or {}
    pics = [p for p in (lab.get("pictures") or []) if p.get("subject") == s_n]
    desc = " ".join(str(p.get("desc") or "") for p in pics)
    char_opts = _cat.resolve_dial_opts("character", flavors.get("character"))
    exp_opts = _cat.resolve_dial_opts("explicit", flavors.get("explicit"))
    sub_meta = (lab.get("subjects") or {}).get(s_n) or {}
    cname = str(sub_meta.get("char_name") or sub_meta.get("name") or "")
    c_rule = ""
    if char_opts:
        idx = min(len(char_opts) - 1, max(0, s_n - 1))
        c_rule = str(char_opts[idx].get("rule") or char_opts[idx].get("label") or "")
    blob = f"{cname} {desc} {c_rule}".lower()
    m_score = len(re.findall(r"\b(?:man|male|boy|guy|gentleman|husband|boyfriend|actor|knight|samurai|soldier|fighter|hero|he|his|him|beard|stubble|short\s+cropped\s+hair)\b", blob))
    f_score = len(re.findall(r"\b(?:woman|female|girl|lady|wife|girlfriend|actress|idol|heroine|she|her|hers|skirt|dress|lingerie|bikini|bra|bust|breasts|cleavage|heels)\b", blob))
    if s_n == 1 and m_score > f_score:
        return ("his", "him", "he")
    if s_n == 1 and f_score > m_score:
        return ("her", "her", "she")
    if s_n == 1 and re.search(r"\b(?:the\s+man|a\s+man|young\s+man|male\s+lead|guy)\b", brief or "", re.I) and not re.search(r"\b(?:woman|girl|female|she|her)\b", brief or "", re.I):
        return ("his", "him", "he")
    if s_n == 2:
        exp_blob = " ".join(f"{o.get('id','')} {o.get('label','')} {o.get('rule','')}" for o in exp_opts).lower()
        if f_score > m_score or re.search(r"\b(?:lesbian|fff|two\s+women|other\s+woman)\b", f"{brief} {exp_blob}".lower()):
            return ("her", "her", "she")
        if m_score > f_score or _dir.is_sexual(brief, str(flavors.get("explicit") or ""), str(flavors.get("wardrobe") or ""), fetish_id=str(flavors.get("fetish") or "")):
            return ("his", "him", "he")
        return ("their", "them", "they")
    if m_score > f_score:
        return ("his", "him", "he")
    if f_score > m_score:
        return ("her", "her", "she")
    return ("her", "her", "she") if s_n == 1 else ("his", "him", "he")


def adapt_rule_subjects(rule_text: str, lab: dict | None = None, *, brief: str = "", explicit_id: str = "", flavors: dict | None = None) -> str:
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
    comb_s = f"{explicit_id} {brief} {out}".lower()
    is_sex_s = bool(explicit_id or _dir.is_sexual(brief, explicit_id=explicit_id))
    if 1 not in sub_meta:
        s1_noun = "the woman" if (is_sex_s and not re.search(r"\b(?:male\s+lead|gay)\b", comb_s)) else "the lead"
        out = re.sub(r"<Subject\s+1>'s\b", f"{s1_noun}'s", out)
        out = re.sub(r"<Subject\s+1>", s1_noun, out)
    if 2 not in sub_meta:
        is_les = bool(re.search(r"\b(?:lesbian|scissoring|tribadism|cunnilingus|two women|other woman|fff)\b", comb_s))
        if is_les:
            out = re.sub(r"<Subject\s+2>'s\b", "the other woman's", out)
            out = re.sub(r"<Subject\s+2>", "the other woman", out)
        elif is_sex_s:
            out = re.sub(
                r"<Subject\s+2>'s\s+(?:(thick|hard|vertical|oiled|glistening|throbbing|swollen)\s+)?(?:erect\s+)?shaft\b",
                lambda m: f"his {m.group(1) + ' ' if m.group(1) else ''}erect cock",
                out,
                flags=re.I,
            )
            out = re.sub(r"<Subject\s+2>'s\b", "the man's", out)
            out = re.sub(r"<Subject\s+2>", "the man", out)
        else:
            is_combat_s = _dir.is_combat(brief, out)
            is_tag_team_s = bool(re.search(r"\b(?:tag[- ]?team|back[- ]?to[- ]?back|squad|ally|assist)\b", comb_s))
            is_dance_s = bool(re.search(r"\b(?:dance|duet|choreograph|vogue|shimmy|backspin|hook\s*kick|cheek-heart|two-step|hip|squat)\b", comb_s))
            s1_poss, _, _ = infer_subject_pronouns(1, lab=lab, brief=brief, flavors=flavors)
            s2_noun = (f"{s1_poss} ally" if is_tag_team_s else f"{s1_poss} rival") if is_combat_s else (f"{s1_poss} dance partner" if is_dance_s else "the other person")
            out = re.sub(r"<Subject\s+2>'s\b", f"{s2_noun}'s", out)
            out = re.sub(r"<Subject\s+2>", s2_noun, out)
    if re.search(r"<Subject\s+N>", out):
        extra_keys = [sn for sn in sorted(sub_meta.keys()) if sn >= 3]
        s2_lbl_e = f"<Subject 2> {sub_meta[2].get('char_name') or sub_meta[2].get('name') or ''}".strip() if 2 in sub_meta else ""
        s1_lbl_e = f"<Subject 1> {sub_meta[1].get('char_name') or sub_meta[1].get('name') or ''}".strip() if 1 in sub_meta else "the lead"
        if extra_keys:
            extra_list = ", ".join(
                f"<Subject {sn}> {sub_meta[sn].get('char_name') or sub_meta[sn].get('name') or ''}".strip()
                for sn in extra_keys
            )
            full_s1_n = ", ".join([x for x in (s1_lbl_e, s2_lbl_e, extra_list) if x])
            full_s2_n = ", ".join([x for x in (s2_lbl_e, extra_list) if x])
            out = re.sub(r"<Subject\s+1>(?:\s+[A-Za-z][A-Za-z'\-]+)?\s*(?:\.\.|through)\s*<Subject\s+N>", full_s1_n, out)
            out = re.sub(r"<Subject\s+2>(?:\s+[A-Za-z][A-Za-z'\-]+)?\s*(?:\.\.|through)\s*<Subject\s+N>", full_s2_n, out)
            out = re.sub(r"<Subject\s+3>(?:\s+[A-Za-z][A-Za-z'\-]+)?\s*(?:\.\.|through)\s*<Subject\s+N>", extra_list, out)
            out = re.sub(r"<Subject\s+N>", extra_list.split(", ")[-1], out)
        else:
            is_cbt_n = _dir.is_combat(brief, out)
            is_dnc_n = bool(re.search(r"\b(?:dance|choreo|idol|v-formation|canon|diamond|runway|catwalk|club)\b", comb_s))
            grp_tail = "allied squad mates" if is_cbt_n else ("the flanking dancers" if is_dnc_n else "the surrounding companions")
            two_s = f"{s1_lbl_e} and {s2_lbl_e}" if s2_lbl_e else s1_lbl_e
            out = re.sub(r"All\s+cast\s+subjects\s*\(\s*<Subject\s+1>(?:\s+[A-Za-z][A-Za-z'\-]+)?\s+through\s+<Subject\s+N>\s*\)", two_s, out, flags=re.I)
            out = re.sub(r"<Subject\s+1>(?:\s+[A-Za-z][A-Za-z'\-]+)?\s*(?:\.\.|through)\s*<Subject\s+N>", f"{two_s} and {grp_tail}" if s2_lbl_e else f"{s1_lbl_e} and {grp_tail}", out)
            out = re.sub(r"<Subject\s+2>(?:\s+[A-Za-z][A-Za-z'\-]+)?\s*(?:\.\.|through)\s*<Subject\s+N>", f"{s2_lbl_e} and {grp_tail}" if s2_lbl_e else grp_tail, out)
            out = re.sub(r"<Subject\s+3>(?:\s+[A-Za-z][A-Za-z'\-]+)?\s*(?:\.\.|through)\s*<Subject\s+N>", grp_tail, out)
            out = re.sub(r"<Subject\s+N>", grp_tail, out)
    for sn_extra in range(3, 10):
        if sn_extra not in sub_meta and re.search(rf"<Subject\s+{sn_extra}>", out):
            extra_noun = "the second woman" if re.search(r"\b(?:ffm|lesbian|fff)\b", comb_s) else "the other companion"
            out = re.sub(rf"<Subject\s+{sn_extra}>'s\b", f"{extra_noun}'s", out)
            out = re.sub(rf"<Subject\s+{sn_extra}>", extra_noun, out)
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


def strip_rule_intro_scaffold(txt: str) -> tuple[str, str]:
    """Strip 'Structure across 3 ...:' / 'Stage a ...:' / 'Frame a ...' intro wrapper, returning `(intro_cam_cue, body)`."""
    s = str(txt or "").strip()
    intro_cam = ""
    s = re.sub(r"\([^)]*\[\s*Shot\s+\d+\s*\][^)]*\)", "", s, flags=re.I)
    # Strip meta-instruction sentences before `In Beat 1` / `Across the beats` (e.g. "keep her shoulders ... Write the rear hole map ... In Beat 1, ...")
    s = re.sub(
        r"(?:^|\.\s*)(?:keep\s+(?:her|his|their)\s+shoulders\s+level[^.]{0,220}\.\s*(?:Write\s+the\s+rear\s+hole\s+map[^:]{0,140}:\s*[^.]{0,420}\.\s*)?|Write\s+the\s+rear\s+hole\s+map[^:]{0,140}:\s*[^.]{0,420}\.\s*)(?=(?:In\s+Beat\s+1\b|One\s+hand\s+is\s+already\b|Across\s+the\s+beats\b))",
        "",
        s,
        flags=re.I,
    ).strip()

    m_wrap = re.match(
        r"^(?:(?:Structure|Stage|Hold|Frame|Show|Choreograph|Deliver|Capture)\s+(?:the\s+clip\s+)?(?:across|as|one|a|an|the|this)\b"
        r"|One\s+(?:unbroken|continuous|unhurried)\b"
        r"|(?:a|an|classic|high-contrast)\s+(?:three-shot|two-shot|match-on-action|dynamic\s+multi-angle|table\s+dialogue|two-shot\s+graphic|two-shot\s+smash)\b"
        r"|connect\s+two\s+contrasting\s+locations\b"
        r"|join\s+two\s+locations\b)"
        r"([^:\n]{0,280}):\s*\.?\s*(.+)$",
        s,
        flags=re.I | re.S,
    )
    if m_wrap:
        wrap_txt = m_wrap.group(1).strip()
        body_txt = m_wrap.group(2).strip()
        m_cam_in_wrap = re.search(
            r"(?:in|from)\s+(?:a|an)?\s*([^,:\n]{6,110}?(?:shot|close-?up|angle|view|portrait|framing|take))\b",
            wrap_txt,
            flags=re.I,
        )
        if m_cam_in_wrap:
            intro_cam = m_cam_in_wrap.group(1).strip(" .,")
        else:
            cleaned_w = re.sub(r"`?\[\s*Shot\s+\d+\s*\]`?", "", wrap_txt, flags=re.I)
            cleaned_w = re.sub(r"^(?:ONE\s+)?(?:unbroken|continuous|unhurried|\d+\s+crisp|\d+\s+distinct)?\s*(?:continuous\s+)?", "", cleaned_w, flags=re.I).strip(" .,-`")
            if re.search(r"\b(?:shot|close-?up|angle|view|portrait|framing)\b", cleaned_w, re.I) and 6 <= len(cleaned_w) <= 110:
                if not re.search(r"\b(?:multi-angle|multi-position|orbiting|table\s+dialogue|graphic\s+match|smash\s+cut)\b", cleaned_w, re.I):
                    intro_cam = cleaned_w
        # Strip trailing meta-instructions between ":" and "In Beat 1" / "One hand is" / "Across the beats"
        if re.match(r"^(?:keep\s+|write\s+the\s+rear\s+hole\s+map\b)", body_txt, re.I):
            body_txt = re.sub(r"^.*?(?=(?:In\s+Beat\s+1\b|One\s+hand\s+is\s+already\b|Across\s+the\s+beats\b))", "", body_txt, count=1, flags=re.I | re.S).strip()
        return intro_cam, body_txt

    # Handle standalone sentence opener: "Frame a <camera/angle sentence>. In Beat 1 / In [Shot 1] / <Subject>..."
    m_frame_sent = re.match(
        r"^Frame\s+(?:a|an)\s+([^.!?\n]{8,220}?)[.!?]\s+(?=(?:In\s+(?:Beat\s+1|\[\s*Shot\s+1\s*\])|<Subject|She\b|He\b|They\b|Both\b|The\b))(.+)$",
        s,
        flags=re.I | re.S,
    )
    if m_frame_sent:
        cand = m_frame_sent.group(1).strip(" .,")
        rest = m_frame_sent.group(2).strip()
        cand_clean = re.sub(r"\s*\([^)]*\)\s*", " ", cand).strip()
        if re.search(r"\b(?:shot|angle|close-?up|medium|wide|pov|view|portrait|framing)\b", cand_clean, re.I):
            intro_cam = cand_clean[:120].strip(" .,")
        return intro_cam, rest

    # Handle "Frame a <camera/angle> looking [up/down] at/across/from ... <Subject N> <participle...>"
    m_frame_part = re.match(
        r"^Frame\s+(?:a|an)\s+([^,;\n]{8,180}?(?:shot|angle|close-?up|pov|view|perspective|framing)[^,;\n]{0,80}?)\s+(?:looking\s+(?:up|down)\s+(?:from\s+[^,;\n]{2,40}\s+)?(?:at|across)|at|across)\s+(<Subject\s+\d+>(?:\s+[A-Z][a-zA-Z'\-]+)?)\s+([a-z]+(?:ing|ed))\b(.+)$",
        s,
        flags=re.I | re.S,
    )
    if m_frame_part:
        cam_p = m_frame_part.group(1).strip(" .,")
        subj_p = m_frame_part.group(2).strip()
        verb_ing = m_frame_part.group(3).lower()
        rest_p = m_frame_part.group(4)
        fin_v = _PARTICIPLE_TO_FINITE.get(verb_ing, "sits perched" if verb_ing == "perched" else ("reclines" if verb_ing == "reclined" else verb_ing))
        return cam_p[:120], f"{subj_p} {fin_v}{rest_p}"

    return intro_cam, s


def clean_shot_cam_and_action(raw_clause: str, s_idx: int) -> tuple[str, str]:
    """Split a `[Shot N]` chunk cleanly into `(camera_framing_cue, grammatical_action_clause)`."""
    c = str(raw_clause or "").strip(" .;,`-\n")
    if not c:
        return "", ""
    cam_cue = ""
    act = c

    # 0. Explicit `<framing cue>: <action clause>` (e.g. "Frame a three-quarter side medium shot keeping ... in clear view: he lies...")
    m_colon = re.match(
        r"^(?:frame\s+(?:a|an)\s+|frames?\s+|opens?\s+(?:in|with|on)\s+(?:a|an)?\s*)?([^:\n]{6,180}):\s*(.+)$",
        c,
        flags=re.I | re.S,
    )
    if m_colon:
        left_cam = m_colon.group(1).strip(" ,.-")
        right_act = m_colon.group(2).strip(" .;,-")
        if (
            re.search(r"\b(?:shot|angle|close-?up|medium|wide|profile|rear|3/4|three-quarter|look-?down|look-?up|mirror|two-plane|portrait|eye-level|over-?shoulder|framing|view|dolly|tracking|overhead)\b", left_cam, re.I)
            and not re.match(r"^(?:<Subject\s+\d+>|she|he|they|both)\b", left_cam, re.I)
            and len(right_act.split()) >= 4
        ):
            return left_cam, right_act

    # 0b. Leading "in a <framing>, <Subject...>" (common in ms_rule dance shots)
    m_in_lead = re.match(
        r"^(?:in|from)\s+((?:a|an)\s+[^.;\n]{4,140}?(?:shot|angle|close-?up|frame|view|perspective|framing)(?:[^,\n]{0,90})?),\s*(?=(?:<Subject|both\b|she\b|he\b|they\b|all\b|an?\s+isolated|the\b))(.+)$",
        c,
        flags=re.I | re.S,
    )
    if m_in_lead:
        return m_in_lead.group(1).strip(" .,"), m_in_lead.group(2).strip(" .;,-")

    # Strip accidental subject prefix before cut verb (e.g. "<Subject 1> hard-cutting onto...")
    c_scan = re.sub(
        r"^<Subject\s+\d+>(?:\s+[A-Z][a-zA-Z'\-]+)?\s+(?=(?:(?:hard|quick|smash|clean)[- ]+)?cutting\b|(?:hard|quick|smash)[- ]?cuts?\b)",
        "",
        c,
        flags=re.I,
    )

    # Pattern A: "(opens|cuts|cutting|...) <framing/angle> (as|where|establishing|showing|revealing|framing|bringing|, <Subject...>) <action>"
    m_split = re.match(
        r"^(?:(?:instant\s+)?(?:hard|quick|smash|clean)?[- ]*cut(?:s|ting)?(?:\s+(?:cleanly|smoothly|tight(?:ly)?|wide|back|far\s+back|low|high|straight))?"
        r"|opens?(?:\s+(?:tightly|closely|wide|briskly|cleanly))?"
        r"|frames?"
        r"|holds?(?:\s+steady)?"
        r"|switches?(?:\s+(?:cleanly|smoothly))?"
        r"|punches?(?:\s+(?:in(?:to)?|out))?"
        r"|looks\s+(?:steeply\s+)?(?:down|up))\b"
        r"([^.;\n]{0,190}?)"
        r"(?:\s+(?:as|where|establishing|revealing|showing|framing|bringing)\s+|,\s*(?=(?:<Subject|nude\s+<Subject|bare[- ]chested\s+<Subject|both\b|she\b|he\b|the\b|her\b|his\b|their\b|an?\s+isolated\b|bracing\b)))"
        r"(.+)$",
        c_scan,
        flags=re.I | re.S,
    )
    if m_split:
        lead_raw = m_split.group(0)[:m_split.start(2)]
        lead_cam = re.sub(
            r"^(?:(?:instant\s+)?(?:hard|quick|smash|clean)?[- ]*cut(?:s|ting)?\s*(?:(?:cleanly|smoothly)\s+)?(?:to|into|onto)?|opens?\s*(?:inside|in|as|beside|on|onto|with)?|frames?|holds?\s*(?:in|steady)?|switches?\s*(?:to|into)?|punches?\s*(?:into|in|out)?)\s*",
            "",
            lead_raw,
            flags=re.I,
        ).strip(" ,:-")
        if re.match(r"^(?:looks\s+(?:steeply\s+)?(?:down|up))\b", c_scan, re.I):
            lead_cam = re.sub(r"^(?:looks)", "looking", lead_raw, flags=re.I).strip(" ,:-")
        m_kw = re.search(r"\s+(as|where|establishing|revealing|showing|framing|bringing)$", lead_cam, re.I)
        kw_split = m_kw.group(1).lower() if m_kw else ""
        lead_cam = re.sub(r"\s+(?:as|where|establishing|revealing|showing|framing|bringing)$", "", lead_cam, flags=re.I).strip(" ,:-")
        cam_cue = re.sub(r"^(?:to|into|onto)\s+", "", lead_cam, flags=re.I).strip()
        if re.match(r"^in\s+", cam_cue, re.I) and not re.match(r"^inside\b", cam_cue, re.I):
            cam_cue = re.sub(r"^in\s+", "", cam_cue, flags=re.I).strip()
        if cam_cue.lower() in ("low", "tight", "close", "wide", "high"):
            cam_cue = f"{cam_cue} angle"
        act = m_split.group(2).strip(" ,;.-")
        if kw_split == "framing" and re.match(r"^(?:ONLY\s+)?<Subject\s+\d+>[^,]{0,60}\bcentered\b", act, re.I):
            act = re.sub(r"^(?:ONLY\s+)?(<Subject\s+\d+>(?:\s+[A-Z][a-zA-Z'\-]+)?)\s+centered\b", r"\1 is centered", act, count=1, flags=re.I)
        elif kw_split == "bringing" and re.match(r"^<Subject\s+\d+>.*\btogether\b", act, re.I):
            act = re.sub(r"^(.+?)\s+together\b", r"\1 step close together", act, count=1, flags=re.I)
        if s_idx > 0 and re.match(r"^(?:(?:hard|quick|smash|clean)[- ]+)?(?:cutting|cuts?|smash[- ]?cuts?|punch)", c_scan, re.I):
            prep = "onto" if re.search(r"\bonto\b", lead_raw, re.I) else ("into" if re.search(r"\binto\b", lead_raw, re.I) else "to")
            if re.match(r"^smash", c_scan, re.I):
                cam_cue = f"smash-cuts {prep} {cam_cue}".strip()
            elif re.match(r"^hard", c_scan, re.I):
                cam_cue = f"hard-cuts {prep} {cam_cue}".strip()
            elif re.match(r"^quick", c_scan, re.I):
                cam_cue = f"quick-cuts {prep} {cam_cue}".strip()
    else:
        # Pattern B: "frame(s) a <framing> with/as <Subject...>" or "cut(s) to/inside a <framing> of/with <Subject...>"
        m_cam_only = re.match(
            r"^(?:frame\s+(?:a|an)\s+|frames?\s+|cuts?\s+(?:cleanly\s+|smoothly\s+)?(?:to|into|onto|inside|in)\s+(?:a|an)?\s*|opens?\s+(?:inside|in|with|on)\s+(?:a|an)?\s*)"
            r"([^,;.\n]{4,160}?)"
            r"(?=\s+with\s+(?:<Subject|both\b|the\b|nude\b|bare\b|her\b|his\b)|(?<!\blegs)(?<!\blap)(?<!\bfront)(?<!\bhips)(?<!\bwaist)(?<!\bchest)(?<!\bside)(?<!\bback)\s+of\s+(?:<Subject|both\b)|,\s*(?=(?:<Subject|both\b|she\b|he\b|the\b|her\b|his\b|their\b|nude\b|bare\b|bracing\b))|[;.]|$)"
            r"(.*)$",
            c_scan,
            flags=re.I | re.S,
        )
        if m_cam_only and m_cam_only.group(2).strip():
            cand_cam = m_cam_only.group(1).strip(" ,:-")
            rest_a = re.sub(r"^(?:with|of|,)\s+", "", m_cam_only.group(2).strip(), flags=re.I).strip()
            if re.search(r"\b(?:shot|angle|close-?up|medium|wide|profile|mirror|pov|view|portrait|framing|pedestal|cut|orbit|arc|push|pull|booth|elevator|window)\b", cand_cam, re.I):
                cam_cue = cand_cam
                act = rest_a
        elif re.match(r"^(?:frame|frames)\s+(?:a|an)\s+[^.!?\n]{4,150}$", c_scan, re.I) and not re.search(r"<Subject|\b(?:she|he|they)\s+(?:stands|sits|kneels|lies|pulls|pushes|drives)\b", c_scan, re.I):
            cam_cue = re.sub(r"^(?:frame|frames)\s+(?:a|an)\s+", "", c_scan, flags=re.I).strip(" .")
            act = ""
        elif re.match(r"^(?:frames?|opens?|cuts?\s+to|switches?\s+to)\s+(?=<Subject|nude|both|the\b)", c_scan, re.I):
            act = re.sub(r"^(?:frames?|opens?\s+with|opens?\s+on|cuts?\s+to|switches?\s+to)\s+", "", c_scan, flags=re.I).strip()

    if act:
        def _fix_participle(m):
            subj_part = m.group(1)
            verb_part = m.group(2).lower()
            repl = _PARTICIPLE_TO_FINITE.get(verb_part, verb_part)
            return f"{subj_part} {repl}"
        act = re.sub(
            r"^((?:(?:nude|bare[- ]shouldered|bare[- ]chested|flushed)\s+)?<Subject\s+\d+>(?:\s+[A-Z][a-zA-Z]+)?(?:\s*,\s*[^,]{3,80},)?)\s+"
            r"(bracing|kneeling|straddling|standing|leaning|lying|pressing|bouncing|gripping|sliding|pulling|wrapping|looking|lowering|climbing|arching|holding|rocking|grinding|riding|driving|sucking|stroking|kissing|facing|sitting|hovering|resting|crawling|balancing|bending|seated|perched|pinned|draped)\b",
            _fix_participle,
            act,
            count=1,
        )
        # Fix "<Subject N> [Name] on all fours" (missing verb after stripping "establishing")
        act = re.sub(
            r"^((?:nude\s+)?<Subject\s+\d+>(?:\s+[A-Z][a-zA-Z]+)?)\s+(?!braces|kneels|stands|lies|sits|leans|crouches|perches)(on\s+all\s+fours|flat\s+on\s+(?:her|his)\s+back|astride\s+his\s+lap|at\s+the\s+brink)\b",
            r"\1 braces \2",
            act,
            count=1,
            flags=re.I,
        )
        act = re.sub(r"\b(braces|kneels|stands|lies|sits)\s+\1\b", r"\1", act, flags=re.I)
        if re.match(r"^(?:low|tight|close|wide)\s+as\s+", act, re.I):
            m_la = re.match(r"^(low|tight|close|wide)\s+as\s+(.+)$", act, re.I | re.S)
            if m_la:
                if not cam_cue:
                    cam_cue = f"{m_la.group(1).lower()} close-up"
                act = m_la.group(2).strip()
    return cam_cue.strip(" .,"), act.strip(" .,;")


def extract_shot_segments_from_rule(
    rule_text: str,
    lab: dict | None = None,
    *,
    brief: str = "",
    explicit_id: str = "",
    flavors: dict | None = None,
) -> tuple[dict[int, str], dict[int, str]]:
    """Extract `(shot_cams_by_idx, clauses_by_idx)` cleanly for `[Shot N]`, `At MM:SS`, `Beat N`, or prose rules."""
    txt = adapt_rule_subjects(rule_text, lab, brief=brief, explicit_id=explicit_id, flavors=flavors)
    txt = sanitize_beat_clause(txt)
    cams: dict[int, str] = {}
    out: dict[int, str] = {}
    if not txt:
        return cams, out

    intro_cam, body = strip_rule_intro_scaffold(txt)
    if intro_cam:
        cams[0] = intro_cam

    # 1. Explicit millisecond `At MM:SS.mmm-MM:SS.mmm` segments (Uber Fights & viral dance cuts)
    ms_matches = list(re.finditer(r"\bAt\s+\d+:\d+(?:\.\d+)?\s*[-–—]\s*\d+:\d+(?:\.\d+)?\s*,?\s*", body, flags=re.I))
    if len(ms_matches) >= 2:
        prev_pos = 0
        cur_shot_idx = 0
        for b_idx, m_at in enumerate(ms_matches):
            seg_before = body[prev_pos:m_at.start()]
            m_sh_num = list(re.finditer(r"\[\s*Shot\s+(\d+)\s*\]", seg_before, re.I))
            if m_sh_num:
                cur_shot_idx = max(0, int(m_sh_num[-1].group(1)) - 1)
            end_c = ms_matches[b_idx + 1].start() if b_idx + 1 < len(ms_matches) else len(body)
            raw_seg = body[m_at.end():end_c]
            # Strip trailing `[Shot N]` belonging to the NEXT timestamp
            raw_seg = re.sub(r"\[\s*Shot\s+\d+\s*\]\s*$", "", raw_seg.strip(), flags=re.I).strip(" .;,-")
            raw_seg = re.sub(r"\[\s*Shot\s+\d+\s*\](?:\s*,?\s*At\s+\d+:\d+(?:\.\d+)?\s*,?)?", "", raw_seg, flags=re.I).strip(" .;,-")
            if raw_seg:
                c_cam, c_act = clean_shot_cam_and_action(raw_seg, cur_shot_idx)
                if c_cam and cur_shot_idx not in cams:
                    cams[cur_shot_idx] = c_cam
                out[b_idx] = c_act or raw_seg
            prev_pos = m_at.end()
        if out:
            return cams, out

    # 2. Multi-shot `[Shot 1] ... [Shot 2] ...` rules (only return early when Shot 2+ exists!)
    shot_parts = re.split(
        r"(?:\(\d+\)\s*)?(?:In\s+)?`?\[\s*Shot\s+([1-6])\s*\]`?(?:\s*,?\s*At\s+MM:SS\.mmm\s*,?\s*)?",
        body,
        flags=re.I,
    )
    has_shot2_plus = len(shot_parts) >= 5 and any(int(shot_parts[i]) >= 2 for i in range(1, len(shot_parts), 2))
    if has_shot2_plus:
        for i in range(1, len(shot_parts), 2):
            s_idx = int(shot_parts[i]) - 1
            raw_chunk = shot_parts[i + 1].strip(" .;,`-\n")
            c_cam, c_act = clean_shot_cam_and_action(raw_chunk, s_idx)
            if c_cam:
                cams[s_idx] = c_cam
            if c_act:
                out[s_idx] = c_act
        if out or cams:
            return cams, out

    # Strip single-shot `[Shot 1]` / `In [Shot 1],` wrappers before Beat N / sentence splitting
    body = re.sub(r"(?:^|[.;]\s*)(?:In\s+)?`?\[\s*Shot\s+1\s*\]`?[,:\s]*", lambda m: ". " if m.group(0).lstrip().startswith(".") else "", body, flags=re.I).strip(" .;,`-\n")

    # 3. Single-shot `Beat 1 ... Beat 2 ... Beat 3 ...` rules
    parts = re.split(r"(?:[.;,\s]*\b(?:in|at)\s+)?\bBeat\s+([1-6])\b[:\-\s—]*", body, flags=re.I)
    if len(parts) >= 3:
        lead_txt = parts[0].strip(" .;,`-\n")
        lead_cam, lead_act = clean_shot_cam_and_action(lead_txt, 0)
        if lead_cam and 0 not in cams:
            cams[0] = lead_cam
        for i in range(1, len(parts), 2):
            b_idx = int(parts[i]) - 1
            clause = parts[i + 1].strip(" .;,-")
            if clause:
                out[b_idx] = clause
        # Prepend non-camera opening context cleanly onto Beat 0 if distinct from Beat 0 (never prepend meta-imperatives)
        is_meta_lead = bool(re.match(r"^(?:stage|frame|keep|maintain|ensure|write|repeat|deliver|choreograph|capture|show|structure)\b", lead_act or "", re.I))
        if lead_act and not is_meta_lead and 0 in out and lead_act.lower()[:24] not in out[0].lower():
            if len(lead_act.split()) >= 5:
                b0_cap = out[0][0].upper() + out[0][1:] if (out[0] and out[0][0].islower()) else out[0]
                out[0] = f"{lead_act.rstrip('.')}. {b0_cap}"
        elif lead_act and not is_meta_lead and 0 not in out:
            out[0] = lead_act
        return cams, out

    # 4. Multi-cut camera prose without `[Shot N]` tags (e.g. `cam_viral_dutch_90roll_wipe_cuts`)
    cut_clauses = [p.strip(" .;,-") for p in re.split(r",\s+(?:and\s+)?(?=(?:hard[- ]cut|smash\s+(?:far\s+)?out|smash[- ]cut|quick[- ]cut|cut\s+(?:cleanly|smoothly))\b)", body, flags=re.I) if p.strip(" .;,-")]
    if len(cut_clauses) >= 2 and re.search(r"\b(?:hard[- ]cut|smash\s+far\s+out|smash[- ]cut)\b", body, re.I):
        for s_i, cc_raw in enumerate(cut_clauses):
            c_cam, c_act = clean_shot_cam_and_action(cc_raw, s_i)
            cams[s_i] = c_cam or cc_raw
            if c_act and c_act != cc_raw:
                out[s_i] = c_act
        return cams, out

    # 5. Single-shot prose
    lead_cam_s, body_act = clean_shot_cam_and_action(body, 0)
    if lead_cam_s and 0 not in cams:
        cams[0] = lead_cam_s
    text_for_sents = body_act or body
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text_for_sents) if s.strip()]
    if len(sents) == 1 and ";" in text_for_sents:
        semi_parts = [p.strip(" .;,-") for p in text_for_sents.split(";") if p.strip(" .;,-")]
        if len(semi_parts) >= 2:
            sents = semi_parts
    if len(sents) >= 3:
        out[0] = " ".join(sents[:max(1, len(sents) // 3)])
        out[1] = " ".join(sents[max(1, len(sents) // 3):max(2, (2 * len(sents)) // 3)])
        out[2] = " ".join(sents[max(2, (2 * len(sents)) // 3):])
    elif len(sents) == 2:
        out[0], out[1] = sents[0], sents[1]
    elif sents:
        out[0] = sents[0]
    return cams, out


def _lc_lead(txt_s: str) -> str:
    s_t = str(txt_s or "").strip()
    if len(s_t) >= 2 and s_t[0].isupper() and s_t[1].islower() and not re.match(r"^(?:Korean|Japanese|Chinese|Tokyo|Seoul|Douyin|TikTok|Hollywood|I\b)", s_t):
        return s_t[0].lower() + s_t[1:]
    return s_t


def _make_polish_fn(lab: dict, *, brief: str = "", flavors: dict | None = None):
    subs = sorted((lab.get("subjects") or {}).keys())
    sub_meta = lab.get("subjects") or {}

    def _sub_lbl(sn: int) -> str:
        m = sub_meta.get(sn) or {}
        cn = m.get("char_name") or m.get("name") or ""
        return f"<Subject {sn}> {cn}".strip() if cn else f"<Subject {sn}>"

    primary_speaker = _sub_lbl(subs[0]) if subs else "The lead character"
    partner_lbl = _sub_lbl(subs[1]) if len(subs) >= 2 else "the partner"
    s1_pron = infer_subject_pronouns(1, lab=lab, brief=brief, flavors=flavors)
    s2_pron = infer_subject_pronouns(2, lab=lab, brief=brief, flavors=flavors) if len(subs) >= 2 else ("his", "him", "he")

    def _polish_clause(raw_c: str) -> str:
        cl = str(raw_c or "").strip(" .;")
        if not cl:
            return cl
        if re.match(r"^she\b", cl) and len(subs) >= 1 and s1_pron[2] == "she" and (len(subs) == 1 or s2_pron[2] == "he"):
            cl = re.sub(r"^she\b", primary_speaker, cl, count=1)
        elif re.match(r"^he\b", cl) and len(subs) >= 2 and s2_pron[2] == "he" and s1_pron[2] == "she":
            cl = re.sub(r"^he\b", partner_lbl, cl, count=1)
        elif re.match(r"^he\b", cl) and len(subs) == 1 and s1_pron[2] == "he":
            cl = re.sub(r"^he\b", primary_speaker, cl, count=1)
        elif re.match(r"^(?:she|he|they)\b", cl):
            cl = cl[0].upper() + cl[1:]
        if cl and cl[0].islower():
            if "<Subject" not in cl and not re.match(
                r"^(?:the|a|an|her|his|their|she|he|they|it|we|you|my|our|under|inside|in|at|on|beside|behind|against|through|from|frame|camera|keeping|bracing|sliding|lifting|lowering|pivoting|turning|both|each|all|one|while|as|with|once|between|around|across|bare|wet|thick|heavy|bright|warm|cool|soft|deep|quick|rapid|slow|steady|low|tight|close|wide|I)\b",
                cl,
                re.I,
            ):
                cl = _conjugate_leading_participle(cl, primary_speaker)
                if cl and cl[0].islower() and not cl.startswith("<Subject"):
                    cl = f"{primary_speaker} {cl}"
            elif cl[0].islower():
                cl = cl[0].upper() + cl[1:]
        return cl

    return _polish_clause


def _infer_active_subject_for_tail(first_half: str, tail: str, lab: dict, brief: str = "", flavors: dict | None = None) -> str:
    """Infer who performs an elliptical `'and <participle/verb>'` tail cleanly."""
    subs = sorted((lab.get("subjects") or {}).keys())
    sub_meta = lab.get("subjects") or {}

    def _sub_lbl(sn: int) -> str:
        m = sub_meta.get(sn) or {}
        cn = m.get("char_name") or m.get("name") or ""
        return f"<Subject {sn}> {cn}".strip() if cn else f"<Subject {sn}>"

    s1 = _sub_lbl(subs[0]) if subs else "the woman"
    s2 = _sub_lbl(subs[1]) if len(subs) >= 2 else "the man"
    s1_pron = infer_subject_pronouns(1, lab=lab, brief=brief, flavors=flavors)
    s2_pron = infer_subject_pronouns(2, lab=lab, brief=brief, flavors=flavors) if len(subs) >= 2 else ("his", "him", "he")
    t_low = (tail or "").lower()

    # 1. Strong anatomical/possessive cues inside `tail` itself
    if s1_pron[0] == "her" and re.search(r"\bher\s+(?:parted\s+|wet\s+|bare\s+|arched\s+|own\s+)*(?:labia|pussy|clit|hips|breasts|tits|glutes|head|lips|knees|thighs)\b", t_low):
        if not re.search(r"\b(?:driv(?:e|es|ing)|thrust(?:s|ing)?|grips?\s+behind|gripping\s+behind|pulls?\s+her\s+bare\s+hips|pulling\s+her\s+bare\s+hips|slides?\s+his|sliding\s+his|into\s+her\s+(?:wet\s+)?(?:pussy|vagina|ass|anus)|from\s+behind)\b", t_low):
            return s1
    if len(subs) >= 2 and s2_pron[0] == "his" and re.search(
        r"\b(?:drives?\s+his|thrusts?\s+his|his\s+(?:erect\s+)?cock|his\s+hands|grips?\s+behind\s+her|pulls?\s+her\s+bare\s+hips|"
        r"erupts?\s+in\s+(?:thick|glossy|white)|firing\s+(?:thick|glossy|white)|aimed\s+at\s+her|pulls?\s+his\s+(?:glistening|erect))\b",
        t_low,
    ):
        if not re.search(r"\bonto\s+his\s+(?:erect\s+)?cock\b|\bover\s+his\s+(?:erect\s+)?cock\b", t_low):
            return s2

    # 2. Scan grammatical clause starts in `first_half` (ignore prepositional objects like "lap of <Subject 2> Ken")
    fh = first_half or ""
    clauses = re.split(r"(?:,\s*(?:while|as|then)\s+|\s+(?:while|as)\s+|;\s*)", fh, flags=re.I)
    for cl in reversed(clauses):
        cl_s = cl.strip()
        if not cl_s:
            continue
        for sn in subs:
            lbl = _sub_lbl(sn)
            if re.match(rf"^(?:nude\s+|bare[- ]\w+\s+)?{re.escape(lbl)}\b", cl_s, re.I):
                return lbl
        m_other = re.match(r"^(?:the\s+other\s+companion|the\s+second\s+woman|the\s+other\s+woman|the\s+man|the\s+woman|(?:her|his|their)\s+(?:ally|rival|dance\s+partner|partner))\b", cl_s, re.I)
        if m_other:
            return m_other.group(0).lower()
        if re.match(r"^she\b", cl_s, re.I):
            return s1
        if re.match(r"^he\b", cl_s, re.I) and len(subs) >= 2:
            return s2
        if re.match(r"^both\b", cl_s, re.I):
            return "both"
    return s1


def _conjugate_leading_participle(tail: str, subject_lbl: str, is_plural: bool = False) -> str:
    s = tail.strip(" .;,-")
    m = re.match(r"^([a-z]+ing)\b(.*)$", s, re.I | re.S)
    if m:
        fin = _PARTICIPLE_TO_FINITE.get(m.group(1).lower())
        if fin:
            if is_plural and fin.endswith("s"):
                fin = fin[:-1]
            rest = re.sub(
                r"\band\s+(driving|gripping|pulling|bouncing|grinding|thrusting|sliding|lowering|arch(?:ing)|rocking)\b",
                lambda mx: "and " + (_PARTICIPLE_TO_FINITE[mx.group(1).lower()][:-1] if (is_plural and _PARTICIPLE_TO_FINITE[mx.group(1).lower()].endswith("s")) else _PARTICIPLE_TO_FINITE[mx.group(1).lower()]),
                m.group(2),
                count=1,
                flags=re.I,
            )
            return f"{subject_lbl} {fin}{rest}"
    m_v = re.match(r"^(drives|thrusts|bounces|grinds|slides|lifts|grips|lowers|swings|pulls|drops|kicks|fires|spins|holds|leans|arches|kisses|sucks|rides|rocks|plants|launches|settles|pivots|turns|steps|presses|wraps|reaches|glides|aligns|sinks|opens|closes)\b(.*)$", s, re.I | re.S)
    if m_v:
        return f"{subject_lbl} {m_v.group(1).lower()}{m_v.group(2)}"
    return s


def split_clause_for_two_microbeats(
    clause: str,
    lab: dict,
    *,
    brief: str = "",
    flavors: dict | None = None,
) -> tuple[str, str] | None:
    """Split a rich single-shot/single-beat clause into two grammatical subject-verb micro-beats if warranted."""
    c = str(clause or "").strip(" .;")
    if len(c.split()) < 13:
        return None

    # 1. Multiple sentences
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", c) if s.strip()]
    if len(sents) >= 2:
        mid = len(sents) // 2
        p1, p2 = " ".join(sents[:mid]).rstrip("."), " ".join(sents[mid:]).rstrip(".")
        if len(p1.split()) >= 4 and len(p2.split()) >= 4:
            return p1, p2

    # 2. Semicolons
    if ";" in c:
        semi = [p.strip(" .;") for p in c.split(";") if p.strip(" .;")]
        if len(semi) >= 2:
            mid = len(semi) // 2
            p1, p2 = "; ".join(semi[:mid]), "; ".join(semi[mid:])
            if len(p1.split()) >= 4 and len(p2.split()) >= 4:
                return p1, p2

    # 3. Clean middle grammatical hinges
    n_len = len(c)
    lo, hi = int(n_len * 0.22), int(n_len * 0.80)
    hinge_patterns = [
        r",\s+followed\s+by\s+",
        r",\s+(?:and\s+)?then\s+",
        r"\s+before\s+(?=(?:<Subject\s+\d+>|she\b|he\b|they\b|both\b|the\s+(?:man|woman|lead|other)\b|launching\b|lowering\b|driving\b|sinking\b|snapping\b|dropping\b|pivoting\b|rising\b|turning\b|settling\b|tracing\b|wrapping\b|tucking\b))",
        r",\s*while\s+(?=(?:<Subject\s+\d+>|she\b|he\b|they\b|both\b|the\s+(?:man|woman|lead|other)\b|her\b|his\b|pearlescent\b|thick\b|steam\b|water\b|sparks\b|gliding\b|rolling\b|swaying\b|keeping\b))",
        r"\s+while\s+(?=(?:<Subject\s+\d+>|the\s+(?:man|woman)\b|her\s+partner\b|she\b|he\b|gliding\b|rolling\b|swaying\b|tracing\b|keeping\b|holding\b|popping\b|bouncing\b|stepping\b|spinning\b))",
        r",\s+as\s+(?=(?:<Subject\s+\d+>|both\b|she\b|he\b|they\b|the\s+(?:man|woman)\b|her\b|his\b))",
        r",\s+and\s+(?=(?:<Subject\s+\d+>|she\b|he\b|they\b|both\b|the\s+(?:man|woman|lead)\b|launches\b|lowers\b|drives\b|thrusts\b|bounces\b|grinds\b|glides\b|aligns\b|sinks\b|plants\b|pivots\b|straddles\b|wraps\b|strokes\b|pulls\b|slides\b|erupts\b|snaps\b|fires\b|drops\b|holds\b|arches\b|rises\b|looks\b|rolls\b|sweeps\b|traces\b|rocks\b|sways\b|tucks\b|tilts\b|settles\b|freezes\b|smiles\b|winks\b|locks\b|steps\b|turns\b|pops\b|driving\b|gripping\b|pulling\b|sliding\b|bouncing\b|grinding\b))",
        r"\s+and\s+(?=(?:<Subject\s+\d+>|she\b|he\b|they\b|both\b|launches\b|lowers\b|drives\b|thrusts\b|bounces\b|grinds\b|glides\b|aligns\b|sinks\b|plants\b|pivots\b|straddles\b|wraps\b|strokes\b|pulls\b|slides\b|erupts\b|snaps\b|fires\b|drops\b|holds\b|arches\b|rises\b|looks\b|rolls\b|sweeps\b|traces\b|rocks\b|sways\b|tucks\b|tilts\b|settles\b|freezes\b|smiles\b|winks\b|locks\b|steps\b|turns\b|pops\b|driving\b|gripping\b|pulling\b|sliding\b|bouncing\b|grinding\b))",
        r",\s+(?=(?:rolls|sweeps|traces|rocks|sways|tucks|tilts|settles|freezes|smiles|winks|locks|steps|turns|pops|gripping|driving|thrusting|hiking|lifting|pulling|sliding|lowering|bouncing|grinding|riding|kissing|sucking|taking|wrapping|stroking|opening|parting|revealing|exposing|raising|arching|pressing|holding|staring|smiling|sweeping|stepping|locking|firing|moving|slamming|leaping|spinning|rolling|tracing|tilting|dipping|gliding)\b)",
    ]
    best_hit: tuple[int, int, int] | None = None
    mid_target = n_len // 2
    for rx in hinge_patterns:
        for m in re.finditer(rx, c, flags=re.I):
            if lo <= m.start() <= hi:
                dist = abs(m.start() - mid_target)
                if best_hit is None or dist < best_hit[0]:
                    best_hit = (dist, m.start(), m.end())
        if best_hit is not None:
            break

    if best_hit is None:
        return None

    _, s_idx, e_idx = best_hit
    head = c[:s_idx].strip(" .;,")
    tail = c[e_idx:].strip(" .;,")
    if len(head.split()) < 5 or len(tail.split()) < 4:
        return None

    if re.match(r"^a\s+", tail, re.I) and "revealing" in tail.lower():
        tail = re.sub(r"\brevealing\b", "reveals", tail, count=1, flags=re.I)
        tail = tail[0].upper() + tail[1:]
    else:
        # Ensure tail starts cleanly as an independent finite sentence
        has_explicit_subj = bool(re.match(
            r"^(?:<Subject\s+\d+>|she\b|he\b|they\b|both\b|the\s+(?:man|woman|lead|other)\b|her\b|his\b|their\b|with\b|keeping\b|my\b|I\b)",
            tail,
            flags=re.I,
        ))
        if not has_explicit_subj:
            subj_lbl = _infer_active_subject_for_tail(head, tail, lab, brief=brief, flavors=flavors)
            is_pl = subj_lbl.lower() in ("they", "both")
            tail = _conjugate_leading_participle(tail, subj_lbl, is_plural=is_pl)

    return head, tail


def _split_long_single_clause(
    clause_txt: str,
    n_beats: int,
    lab: dict | None = None,
    *,
    brief: str = "",
    flavors: dict | None = None,
) -> dict[int, str]:
    c = str(clause_txt or "").strip(" .;")
    if not c or n_beats < 2:
        return {0: c} if c else {}
    parts = [p.strip(" .;,") for p in re.split(r";\s+|\s*,\s+(?=while\b|as\b|then\b|and\s+(?:then\b|his\b|her\b|she\b|he\b|my\b|both\b))", c, flags=re.I) if p.strip(" .;,")]
    if len(parts) < n_beats and lab is not None and len(c.split()) >= 16:
        pair1 = split_clause_for_two_microbeats(c, lab, brief=brief, flavors=flavors)
        if pair1:
            parts = [pair1[0], pair1[1]]
            if n_beats >= 3:
                expanded: list[str] = []
                for seg in parts:
                    if len(expanded) + (2 if len(parts) == 2 else 1) <= n_beats + 1:
                        sub_p = split_clause_for_two_microbeats(seg, lab, brief=brief, flavors=flavors)
                        if sub_p:
                            expanded.extend(sub_p)
                            continue
                    expanded.append(seg)
                parts = expanded
    if len(parts) >= 2:
        out: dict[int, str] = {}
        if len(parts) >= n_beats:
            per = len(parts) // n_beats
            idx = 0
            for b in range(n_beats):
                take = (len(parts) - idx) if b == n_beats - 1 else max(1, per)
                out[b] = ", ".join(parts[idx:idx + take])
                idx += take
        else:
            for b, p in enumerate(parts):
                out[b] = p
        return out
    return {0: c}


def _extract_state_delta(text: str, state: dict[str, Any], *, is_sex: bool, is_mirror: bool = False) -> dict[str, str]:
    """Infer concrete physical state deltas from a beat or shot clause."""
    t = str(text or "")
    deltas: dict[str, str] = {}
    if not t:
        return deltas

    # 1. Garment displacement detection (when not fully nude already)
    if state.get("outfit_base") != "nude":
        m_g = _GARMENT_SHIFT_RX.search(t)
        if m_g:
            raw_shift = re.sub(r"\s{2,}", " ", m_g.group(0).strip(" .,;"))
            low = raw_shift.lower()
            canon = ""
            if "aside" in low:
                km = _GARMENT_KEY_RX.search(low)
                g_w = km.group(1).lower() if km else "underwear"
                canon = f"{g_w} pulled aside"
            elif re.search(r"\b(?:bunch(?:es|ing|ed)?|hik(?:e|es|ing|ed)|lift(?:s|ing|ed)?|tuck(?:s|ing|ed)?\s+up|push(?:es|ing|ed)?\s+(?:up|high))\b", low):
                km = _GARMENT_KEY_RX.search(low)
                g_w = km.group(1).lower() if km else "hem"
                canon = f"{g_w} bunched high around waist" if g_w in ("dress", "skirt", "hem", "hemline") else f"{g_w} pushed up above bare breasts"
            elif re.search(r"\b(?:unbutton|unzip)\w*\b", low):
                km = _GARMENT_KEY_RX.search(low)
                g_w = km.group(1).lower() if km else "front"
                canon = f"{g_w} left open"
            elif re.search(r"\b(?:peel|strip|remov|toss|drop|lower|push(?:es|ing|ed)?\s+down|off\b)\w*", low):
                km = _GARMENT_KEY_RX.search(low)
                g_w = km.group(1).lower() if km else "garment"
                if re.search(r"\b(?:peel|strip|remov|toss)\w*\b|off\s+(?:one\s+shoulder|her\s+shoulders?)", low):
                    canon = f"{g_w} removed"
                else:
                    canon = f"{g_w} lowered off hips"
            if canon:
                prev = str(state.get("outfit_displaced") or "")
                g_tok = (_GARMENT_KEY_RX.search(canon).group(1).lower() if _GARMENT_KEY_RX.search(canon) else "")
                if not prev:
                    state["outfit_displaced"] = canon
                    deltas["outfit"] = canon
                elif g_tok and g_tok not in prev.lower():
                    combined = f"{prev}; {canon}"
                    parts = [p.strip() for p in combined.split(";") if p.strip()][-2:]
                    state["outfit_displaced"] = "; ".join(parts)
                    deltas["outfit"] = state["outfit_displaced"]

    # 2. Orientation (front vs rear vs mirror)
    if is_sex:
        has_mir = is_mirror or bool(_MIRROR_BEAT_RX.search(t))
        if _REAR_BEAT_RX.search(t):
            new_or = "rear-facing with mirror reflection" if has_mir else "rear-facing (face/chest forward away from lens)"
            if state.get("orientation") != new_or:
                state["orientation"] = new_or
                deltas["orientation"] = new_or
        elif _FRONT_BEAT_RX.search(t):
            new_or = "front-facing"
            if state.get("orientation") != new_or:
                state["orientation"] = new_or
                deltas["orientation"] = new_or

    # 3. Oral & active sexual act_mode state
    if is_sex:
        if _ORAL_ACTIVE_RX.search(t):
            if state.get("oral") != "lips sealed on shaft":
                state["oral"] = "lips sealed on shaft"
                deltas["oral"] = "lips sealed on shaft"
            state["act_mode"] = "oral"
        elif _ORAL_FREE_RX.search(t):
            if state.get("oral") == "lips sealed on shaft":
                state["oral"] = "mouth free"
                deltas["oral"] = "mouth free"
        if _CUMSHOT_RX.search(t):
            state["act_mode"] = "cumshot_climax"
        elif re.search(r"\b(?:internal\s+creampie|creampie\s+finish|semen\s+welling|holds?\s+(?:deep|flush)\s+inside\s+her\s+in\s+.*climax)\b", t, re.I):
            state["act_mode"] = "internal_creampie"
        elif _INTERCOURSE_RX.search(t):
            state["act_mode"] = "intercourse"
        elif _HANDJOB_RX.search(t):
            state["act_mode"] = "handjob"
        elif _SOLO_ACT_RX.search(t) and state.get("act_mode") not in ("intercourse", "oral"):
            state["act_mode"] = "solo"

    # 4. Furniture / contact surface
    m_prop = _PROP_SURFACE_RX.search(t)
    if m_prop:
        surf = m_prop.group(1).lower()
        if state.get("surface") != surf:
            state["surface"] = surf
            deltas["surface"] = surf

    return deltas


def _format_brief_beat(brief: str, *, lab: dict, flavors: dict | None = None, strip_quotes: bool = False) -> str:
    """Turn a freeform `brief` into grammatical Subject-tagged prose without `Name: She` double subjects."""
    b = str(brief or "").strip()
    if not b:
        return ""
    if strip_quotes:
        b = re.sub(r'[:,\s]*["“][^"”]{1,220}["”]', "", b)
    b = _fin.sanitize_additive_rule(re.sub(r"[\"“”]", "", b)).strip(" .,:;")
    if not b:
        return ""
    subs = sorted((lab.get("subjects") or {}).keys())
    sub_meta = lab.get("subjects") or {}

    def _sub_lbl(sn: int) -> str:
        m = sub_meta.get(sn) or {}
        cn = m.get("char_name") or m.get("name") or ""
        return f"<Subject {sn}> {cn}".strip() if cn else f"<Subject {sn}>"

    primary = _sub_lbl(subs[0]) if subs else "The lead character"
    s1_who = " and ".join(_sub_lbl(sn) for sn in subs) if subs else "The lead character"
    s1_pron = infer_subject_pronouns(1, lab=lab, brief=brief, flavors=flavors)
    # Replace bare partner name with <Subject N> Name if it appears cleanly as a whole word
    for sn in subs:
        m = sub_meta.get(sn) or {}
        cn = str(m.get("char_name") or m.get("name") or "").strip()
        if cn and re.search(rf"(?<!> )\b{re.escape(cn)}\b", b):
            b = re.sub(rf"(?<!<Subject {sn}> )\b{re.escape(cn)}\b", _sub_lbl(sn), b)

    if re.match(r"^(?:she|he)\b", b, re.I):
        b = re.sub(r"^(?:she|he)\b", primary if re.match(r"^" + s1_pron[2] + r"\b", b, re.I) or len(subs) == 1 else _sub_lbl(subs[1] if len(subs) >= 2 else 1), b, count=1, flags=re.I)
    elif re.match(r"^they\b", b, re.I) and len(subs) >= 2:
        b = re.sub(r"^they\b", s1_who, b, count=1, flags=re.I)
    elif subs and "<Subject" not in b and not re.match(r"^(?:the|a|an|in|on|at|under|inside|while|as|with)\b", b, re.I):
        b = f"{s1_who}: {b}"
    return b


def _build_state_aware_beat_text(
    shot: ShotNode,
    beat: MicroBeat,
    *,
    tree: ShotTree,
    lab: dict,
    brief: str,
    flavors: dict,
    exp_opts: list[dict],
    combat_opts: list[dict],
    pose_opts: list[dict],
    fetish_opts: list[dict],
    cam_shot_cams: dict[int, str],
    cam_shot_clauses: dict[int, str],
    b_idx: int = 0,
) -> str:
    """StateLedger-grounded action builder when a micro-beat has no preset clause directly assigned."""
    subs = sorted((lab.get("subjects") or {}).keys())
    sub_meta = lab.get("subjects") or {}

    def _sub_lbl(sn: int) -> str:
        m = sub_meta.get(sn) or {}
        cn = m.get("char_name") or m.get("name") or ""
        return f"<Subject {sn}> {cn}".strip() if cn else f"<Subject {sn}>"

    s1_who = " and ".join(_sub_lbl(sn) for sn in subs) if subs else "The lead character"
    primary_speaker = _sub_lbl(subs[0]) if subs else "The lead character"
    partner_lbl = _sub_lbl(subs[1]) if len(subs) >= 2 else "the partner"
    s1_poss, _, _ = infer_subject_pronouns(1, lab=lab, brief=brief, flavors=flavors)
    motion_val = _dir.normalize_perf_level("motion", flavors.get("motion"), fallback=str(flavors.get("energy") or "natural"))
    expr_read = str(flavors.get("expr_read") or "auto").strip().lower()
    pov_val = tree.pov
    is_pov = pov_val in ("male", "female", "on")

    disp = str(beat.state_after.get("outfit_displaced") or shot.carried_state.get("outfit_displaced") or "").strip()
    orient = str(beat.state_after.get("orientation") or shot.carried_state.get("orientation") or "front-facing")
    oral = str(beat.state_after.get("oral") or shot.carried_state.get("oral") or "mouth free")
    act_mode = str(beat.state_after.get("act_mode") or shot.carried_state.get("act_mode") or "")
    surf = str(beat.state_after.get("surface") or shot.carried_state.get("surface") or "")
    surf_phrase = f" against the {surf}" if surf else ""
    carry_tail = f" with {disp} kept clear" if disp else ""

    # 1. Explicit Sexual Scenes (StateLedger-aware, role-specific)
    if tree.genre.startswith("explicit") or exp_opts:
        e_blob = " ".join(f"{o.get('id','')} {o.get('label','')} {o.get('rule','')}" for o in exp_opts)
        s0_act_fin = (shot.beats[0].action if shot.beats else "")
        shot_ctx = f"{shot.camera} {shot.place} {s0_act_fin}"
        has_ropes = bool(re.search(r"\b(?:rope|shibari|harness|cuff|leash|collar)\b", shot_ctx if len(shot.beats) else e_blob, re.I)) or bool(re.search(r"\b(?:rope|shibari|harness|cuff|leash|collar)\b", e_blob, re.I))
        has_water = bool(re.search(r"\b(?:shower|water|steam|tub|pool|foam)\b", shot_ctx if shot.shot_n > 1 else e_blob, re.I))
        cam_ids_m = _cat.parse_multi_ids(flavors.get("camera"))
        has_mirror = ("mirror" in orient) or bool(_MIRROR_BEAT_RX.search(shot_ctx)) or any("mirror" in c for c in cam_ids_m)
        prop_tail = (
            " as taut ropes press cleanly into bare skin" if has_ropes
            else (" while warm spray and glistening droplets track bare skin" if has_water
                  else (" while their mirror reflection tracks their motion cleanly" if has_mirror else ""))
        )
        is_rear_now = orient.startswith("rear")
        if is_pov:
            if beat.role in ("anchor_shift", "opening_setup", "setup_contact", "cut_transition"):
                return (
                    f"I steady both hands at the frame edges{surf_phrase}{carry_tail} as {primary_speaker} shifts into clear close-range alignment"
                    + (" facing away" if is_rear_now else " holding eye contact")
                )
            if beat.role in ("peak_settle", "closing_hold", "drive_settle"):
                return (
                    f"My grip tightens steadily around {s1_poss} waist{carry_tail} as breathing peaks and muscles tense into a steady closing hold{prop_tail}"
                )
            return (
                f"I maintain close eye-level perspective gripping {primary_speaker}{carry_tail} while driving rhythmic full-depth motion"
                + (" as her spine arches forward" if is_rear_now else " as her chest rises and falls")
                + prop_tail
            )

        if oral == "lips sealed on shaft":
            has_third = len(subs) >= 3 or bool(re.search(r"\b(?:companion|second\s+man|spitroast|mmf)\b", s0_act_fin + " " + e_blob, re.I))
            if has_third and is_rear_now:
                return (
                    f"{primary_speaker} keeps {s1_poss} lips sealed around the glistening cock of {partner_lbl} while taking steady deep rear thrusts{surf_phrase}{carry_tail}"
                    + prop_tail
                )
            if has_third:
                return (
                    f"{primary_speaker} keeps {s1_poss} lips sealed in a tight O-ring gliding along the glistening cock of {partner_lbl} while working the second shaft briskly with one hand{carry_tail}"
                    + prop_tail
                )
            return (
                f"{primary_speaker} keeps {s1_poss} lips sealed in a tight O-ring gliding along the glistening cock of {partner_lbl}{carry_tail} as {partner_lbl} cradles the back of {s1_poss} head"
                + prop_tail
            )

        pace_w = "briskly" if motion_val in ("brisk", "max") else "steadily"
        is_facial_climax = bool(re.search(r"\b(?:thick\s+white\s+ropes|ropes?\s+arc|onto\s+her\s+(?:bare\s+)?(?:face|chest|breasts|tongue|lips)|facial\b|pearl\s+necklace)\b", s0_act_fin + " " + e_blob, re.I))
        if beat.role in ("peak_settle", "closing_hold") and is_facial_climax:
            return (
                f"{primary_speaker} tilts {s1_poss} chin up with flushed skin, parted glossy lips, and glistening warm cum across {s1_poss} chest while catching {s1_poss} breath into a steady closing hold"
            )

        if act_mode == "internal_creampie" or (beat.role in ("peak_settle", "closing_hold") and re.search(r"\b(?:creampie|semen\s+welling|draw-back|ejaculat\w+|cum\s+ropes)\b", s0_act_fin, re.I)):
            return (
                f"{s1_who} rest close together in post-climax release{surf_phrase}{carry_tail} as breathing slows and warm flushed skin settles cleanly through the closing frame"
                + prop_tail
            )

        if act_mode == "cumshot_climax":
            return (
                f"Thick glossy white ropes of cum coat {s1_poss} flushed skin cleanly{surf_phrase}{carry_tail} as muscles tremble and breathing slows into steady climax release"
                + prop_tail
            )

        if act_mode == "handjob":
            return (
                f"{primary_speaker} strokes {partner_lbl}'s hard cock briskly base-to-tip{surf_phrase}{carry_tail} with thumb gliding across the glistening tip while keeping tight eye contact"
                + prop_tail
            )

        if act_mode == "solo":
            return (
                f"{primary_speaker} traces both hands slowly across {s1_poss} bare skin{surf_phrase}{carry_tail} with parted glossy lips and steady breath{prop_tail}"
            )

        if beat.role in ("anchor_shift", "opening_setup"):
            return f"{primary_speaker} and {partner_lbl} anchor position{surf_phrase}{carry_tail} with firm hand placement and warm breath"
        if beat.role in ("pivot_align", "cut_transition", "setup_contact"):
            dir_note = "angled forward away from the lens" if is_rear_now else "squarely aligned"
            return f"{primary_speaker} shifts weight{surf_phrase} ({dir_note}){carry_tail} as {partner_lbl} grips {s1_poss} hips firmly to align contact"
        if beat.role in ("peak_settle", "closing_hold"):
            if len(subs) < 2 and not is_pov:
                return (
                    f"{primary_speaker} holds teasing, confident eye contact{surf_phrase}{carry_tail} with a slow smirk and relaxed shoulder poise through the closing frame{prop_tail}"
                )
            return (
                f"{s1_who} reach peak muscular tension and flush{carry_tail}{surf_phrase}, slowing {pace_w} into a tightly pressed closing hold with parted lips and steady breath{prop_tail}"
            )
        if len(subs) < 2 and not is_pov:
            return (
                f"{primary_speaker} sustains poised, unhurried teasing posture and expressive gaze{surf_phrase}{carry_tail}{prop_tail}"
            )
        return (
            f"{partner_lbl} and {primary_speaker} drive {pace_w} through full-depth rhythmic strokes{surf_phrase}{carry_tail} with firm waist grips and reactive flesh recoil{prop_tail}"
        )

    # 2. Fetish / Playbook
    if fetish_opts:
        f0 = fetish_opts[0]
        f_vocab = _fin.sanitize_additive_rule(f0.get("vocab") or "")
        f_shoot = _fin.sanitize_additive_rule(f0.get("shooting") or "")
        if beat.role in ("anchor_open", "anchor_shift", "opening_setup"):
            return f"{s1_who} settle into the staged framing ({f_shoot or clean_ui_label(f0.get('title',''))}){carry_tail}" + (f" with {f_vocab}" if f_vocab else "")
        if beat.role in ("closing_settle", "peak_settle", "closing_hold"):
            return f"{s1_who} hold close skin-to-skin warmth{carry_tail} with soft gaze and unhurried breathing into the final frame"
        return f"{s1_who} deepen the tactile closeness{carry_tail} with lingering hand pressure and hushed breathing" + (f", highlighting {f_vocab}" if f_vocab else "")

    # 3. Combat / Action
    if tree.genre == "combat" or combat_opts:
        if beat.role == "open_burst":
            return f"{s1_who} erupt straight from 00:00.000 into rapid strikes, parries, and low footwork evades"
        if beat.role == "ultimate_strike":
            return f"{primary_speaker} winds through a tight snap-zoomed ultimate strike aimed straight at {partner_lbl} as air distortion and sparks flare"
        if beat.role == "impact_recoil":
            return f"Heavy knockback impact blasts debris and bright sparks across the floor while {primary_speaker} lands into a crisp ready guard"
        return f"{s1_who} trade rapid blow-for-blow combos, crouched pivots, and reactive prop impacts across the space"

    # 4. Dance / K-Pop (ONLY when genre == "dance"; static pose_* presets stay in Cinema/Poise!)
    if tree.genre == "dance":
        is_ens = any("s1_s9" in str(p.get("id") or "") for p in pose_opts) or len(subs) >= 3
        is_duet_dance = len(subs) >= 2 and (any(int(p.get("people") or 1) >= 2 or "duet" in str(p.get("id") or "").lower() for p in pose_opts) or not pose_opts)
        if is_ens:
            if beat.role == "count_hit":
                return f"{primary_speaker} pops center-front on count 1 while {partner_lbl} and cast hit staggered sharp lines behind"
            if beat.role == "ending_hold":
                return "All subjects lock cleanly into unified formation with bright eye contact as hair and stage fabric settle"
            return f"As camera tracks across depth, {s1_who} snap contrasting shoulder-and-torso accents, footwork hops, and crisp fingertip lines"
        if beat.role == "count_hit":
            return f"{primary_speaker} hits the opening count-1 shoulder snap sharply on beat with fluid hip tilt and crisp hand framing"
        if beat.role == "choreo_turn":
            return f"{primary_speaker} whips through a crisp 180-degree pivot, arm-frame accent, and rhythmic footwork step as hair and hem flare"
        if beat.role == "ending_hold":
            if is_duet_dance:
                return f"{s1_who} lock into a poised duet ending-fairy pose with relaxed shoulder poise, bright smiles, and direct camera eye lock"
            return f"{primary_speaker} freezes into a poised ending-fairy silhouette with relaxed shoulder poise, bright smile, and direct camera eye lock"
        return f"{primary_speaker} layers fluid shoulder isolations, waist grooves, and alternating hand accents continuously on beat"

    # 5. Cinema / Dialogue
    tone_desc = expr_read if expr_read != "auto" else "grounded"
    cam_act = ""
    if shot.shot_n == 1 and b_idx > 0:
        cam_c = cam_shot_clauses.get(b_idx) or cam_shot_cams.get(b_idx) or ""
        if cam_c and not re.match(r"^(?:cuts?\s|hard[- ]?cut|smash[- ]?cut)", cam_c, re.I):
            cam_act = _lc_lead(cam_c.rstrip("."))

    brief_clean = _format_brief_beat(brief, lab=lab, flavors=flavors, strip_quotes=bool(tree.q_map))
    brief_is_speech = bool(re.search(r"\b(?:whispers?|says?|asks?|speaks?|murmurs?|replies?|calls?\s+out)\b", brief_clean, re.I))
    if b_idx == 0 and brief_clean and not (brief_is_speech and 1 in (tree.q_map or {})):
        return brief_clean
    if b_idx in (tree.q_map or {}) and brief_clean and brief_is_speech:
        return brief_clean
    if beat.role in ("anchor_open", "opening_setup"):
        return f"{s1_who} anchor screen position in motivated practical light with {tone_desc} posture and clear eyeline"
    if beat.role in ("cut_transition", "progression_action", "line_or_peak"):
        if len(subs) >= 2:
            lead = f"{cam_act} while " if cam_act else ""
            return f"{lead}{primary_speaker} shifts weight toward {partner_lbl} with natural hand gesture and {tone_desc} expression"
        return (f"{cam_act} as " if cam_act else "") + f"{primary_speaker} adjusts posture with deliberate hand movement and {tone_desc} gaze"
    if beat.role in ("closing_settle", "reaction_settle", "drive_settle", "closing_hold"):
        return (f"{cam_act} as " if cam_act else "") + f"{primary_speaker} holds a lingering {tone_desc} gaze and natural breath through the closing frame"
    return f"{primary_speaker} sustains steady natural motion and {tone_desc} presence"


def build_shot_tree(
    duration_s: float,
    lab: dict,
    *,
    brief: str = "",
    flavors: dict | None = None,
    extracted_video: dict | None = None,
    plan: str = "",
    topo: dict | None = None,
) -> ShotTree:
    """Build a complete Shot-Tree + StateLedger for `duration_s` and active SandTie dials."""
    flavors = dict(flavors or {})
    subs = sorted((lab.get("subjects") or {}).keys())
    sub_meta = lab.get("subjects") or {}

    def _sub_lbl(sn: int) -> str:
        m = sub_meta.get(sn) or {}
        cn = m.get("char_name") or m.get("name") or ""
        return f"<Subject {sn}> {cn}".strip() if cn else f"<Subject {sn}>"

    s1_who = " and ".join(_sub_lbl(sn) for sn in subs) if subs else "The lead character"

    # Fast path for freshly extracted video choreography (never drop user-extracted timings/cuts)
    if extracted_video and extracted_video.get("beats") and not str(plan or "").strip():
        s1_raw = str(extracted_video.get("shot1") or "...").strip()
        s1_clean = re.sub(
            r"^(?:The\s+)?\[\s*Shot\s+1\s*\](?:\s*At\s+\d+:\d+(?:\.\d+)?\s*,?)?\s*[,:\-]*\s*",
            "",
            s1_raw,
            flags=re.I,
        ).strip() or "..."
        header_s1 = f"[Shot 1] {s1_clean}"
        ext_shots: list[ShotNode] = [ShotNode(shot_n=1, t0=0.0, t1=float(duration_s or 10.0), camera=s1_clean)]
        for raw_ln in extracted_video["beats"]:
            ln = str(raw_ln or "").strip()
            if not ln:
                continue
            m_sh = re.match(r"^\[\s*Shot\s+(\d+)\s*\](?:\s*At\s+(\d+:\d+(?:\.\d+)?)\s*,?)?\s*(.*)$", ln, re.I)
            if m_sh:
                sn = int(m_sh.group(1))
                rest = m_sh.group(3).strip()
                if sn == 1:
                    if rest:
                        header_s1 = f"[Shot 1] {rest}"
                        ext_shots[0].camera = rest
                else:
                    ext_shots.append(ShotNode(shot_n=sn, t0=0.0, t1=float(duration_s or 10.0), camera=rest))
                continue
            m_at = re.match(r"^At\s+(\d+):(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+):(\d+(?:\.\d+)?)\s*,\s*(.+)$", ln, re.I)
            if m_at:
                t0_e = int(m_at.group(1)) * 60 + float(m_at.group(2))
                t1_e = int(m_at.group(3)) * 60 + float(m_at.group(4))
                act_e = m_at.group(5).strip()
                cur_sh = ext_shots[-1]
                if not cur_sh.beats:
                    cur_sh.t0 = t0_e
                cur_sh.t1 = t1_e
                cur_sh.beats.append(MicroBeat(
                    t0=t0_e, t1=t1_e, role="extracted_beat", role_label=f"Extracted Beat {len(cur_sh.beats) + 1}",
                    weight=max(0.2, t1_e - t0_e), action=act_e,
                ))
        return ShotTree(
            duration_s=float(duration_s or 10.0),
            genre="extracted",
            source="extracted",
            shots=ext_shots,
            header_s1=header_s1,
            is_extracted=True,
        )

    if topo is None:
        topo = _bg.compute_shot_topology(
            duration_s,
            brief=brief,
            camera_id=str(flavors.get("camera") or ""),
            explicit_id=str(flavors.get("explicit") or ""),
            flavors=flavors,
        )

    place_opts = _cat.resolve_dial_opts("place", flavors.get("place"))
    light_opts = _cat.resolve_dial_opts("light", flavors.get("light"))
    lens_opts = _cat.resolve_dial_opts("lens", flavors.get("lens"))
    cam_opts = _cat.resolve_dial_opts("camera", flavors.get("camera"))
    style_opts = _cat.resolve_dial_opts("style", flavors.get("style"))
    col_opts = _cat.resolve_dial_opts("colour", flavors.get("colour"))
    era_opts = _cat.resolve_dial_opts("era", flavors.get("era"))
    tv_opts = _cat.resolve_dial_opts("tv_show", flavors.get("tv_show"))
    fx_opts = _cat.resolve_dial_opts("fx", flavors.get("fx"))
    exp_opts = _cat.resolve_dial_opts("explicit", flavors.get("explicit"))
    combat_opts = _cat.resolve_dial_opts("combat", flavors.get("combat"))
    pose_opts = _cat.resolve_dial_opts("pose", flavors.get("pose"))
    fetish_opts = _cat.resolve_dial_opts("fetish", flavors.get("fetish"))
    ward_opts = _cat.resolve_dial_opts("wardrobe", flavors.get("wardrobe"))
    talk_opts = _cat.resolve_dial_opts("talkstyle", flavors.get("talkstyle"))
    acc_opts = _cat.resolve_dial_opts("accent", flavors.get("accent"))

    pov_val = _dir.resolve_pov_mode(brief, flavors=flavors, plan=plan)
    is_pov = pov_val in ("male", "female", "on")
    is_sex = _dir.is_sexual(brief, str(flavors.get("explicit") or ""), str(flavors.get("wardrobe") or ""), fetish_id=str(flavors.get("fetish") or ""))
    rear_scene = _dir.is_rear_facing(brief, str(flavors.get("explicit") or ""), plan=plan, camera_id=str(flavors.get("camera") or ""), pose_id=str(flavors.get("pose") or ""))
    mirror_scene = _dir.is_mirror_scene_active(
        str(flavors.get("explicit") or ""),
        str(flavors.get("camera") or ""),
        place_id=str(flavors.get("place") or ""),
        lens_id=str(flavors.get("lens") or ""),
        brief=brief,
    )
    mixed_orient = _dir.has_mixed_front_and_rear_beats(brief, explicit_id=str(flavors.get("explicit") or ""), plan=plan)
    spans = topo["spans"]
    n_shots = len(topo["shots"])

    # Extract raw rule clauses & per-shot cameras
    def _segments_for_dial(opts: list[dict], *, is_explicit: bool = False, is_camera_dial: bool = False) -> tuple[dict[int, str], dict[int, str]]:
        if not opts:
            return {}, {}
        if len(opts) == 1:
            sc_m, cl_m = extract_shot_segments_from_rule(
                opts[0].get("rule") or "", lab=lab, brief=brief, explicit_id=opts[0]["id"] if is_explicit else "", flavors=flavors,
            )
            if (not is_camera_dial) and n_shots >= 2 and topo["source"] != "ms_rule" and len(cl_m) == 1 and 0 in cl_m:
                split_sh = _split_long_single_clause(cl_m[0], n_shots, lab=lab, brief=brief, flavors=flavors)
                if len(split_sh) >= 2:
                    cl_m = split_sh
            return sc_m, cl_m
        cams_m: dict[int, str] = {}
        mapped: dict[int, str] = {}
        if n_shots >= 2 and topo["source"] != "ms_rule":
            # Map picked presets cleanly across Shot indices (0 .. n_shots - 1), never raw beat indices!
            if len(opts) == n_shots:
                for s_idx, opt in enumerate(opts):
                    sub_cams, sub = extract_shot_segments_from_rule(
                        opt.get("rule") or "", lab=lab, brief=brief, explicit_id=opt["id"] if is_explicit else "", flavors=flavors,
                    )
                    if sub_cams.get(0):
                        cams_m[s_idx] = sub_cams[0]
                    clause_txt = sub.get(0) or sanitize_beat_clause(adapt_rule_subjects(opt.get("rule") or "", lab, brief=brief, explicit_id=opt["id"] if is_explicit else "", flavors=flavors))
                    if clause_txt:
                        mapped[s_idx] = clause_txt
            else:
                shot_buckets = _bg.allocate_stages_to_spans(opts, [(sh_s["t0"], sh_s["t1"]) for sh_s in topo["shots"]])
                for opt, s_list in shot_buckets:
                    sub_cams, sub = extract_shot_segments_from_rule(
                        opt.get("rule") or "", lab=lab, brief=brief, explicit_id=opt["id"] if is_explicit else "", flavors=flavors,
                    )
                    base_c = sub.get(0) or sanitize_beat_clause(adapt_rule_subjects(opt.get("rule") or "", lab, brief=brief, explicit_id=opt["id"] if is_explicit else "", flavors=flavors))
                    if (not is_camera_dial) and len(s_list) >= 2 and len(sub) < len(s_list) and base_c:
                        exp_sub = _split_long_single_clause(base_c, len(s_list), lab=lab, brief=brief, flavors=flavors)
                        if len(exp_sub) >= 2:
                            sub = exp_sub
                    for k_idx, (sh_num, _) in enumerate(s_list):
                        s_i = sh_num - 1
                        cam_txt = sub_cams.get(k_idx) or sub_cams.get(0)
                        if cam_txt:
                            cams_m[s_i] = cam_txt
                        clause_txt = sub.get(k_idx) if k_idx in sub else (base_c if k_idx == 0 else "")
                        if clause_txt:
                            mapped[s_i] = clause_txt
            return cams_m, mapped

        alloc = _bg.allocate_stages_to_spans(opts, spans)
        for opt, b_list in alloc:
            sub_cams, sub = extract_shot_segments_from_rule(
                opt.get("rule") or "", lab=lab, brief=brief, explicit_id=opt["id"] if is_explicit else "", flavors=flavors,
            )
            base_c = sub.get(0) or sanitize_beat_clause(adapt_rule_subjects(opt.get("rule") or "", lab, brief=brief, explicit_id=opt["id"] if is_explicit else "", flavors=flavors))
            if (not is_camera_dial) and len(b_list) >= 2 and len(sub) < len(b_list) and base_c:
                exp_sub = _split_long_single_clause(base_c, len(b_list), lab=lab, brief=brief, flavors=flavors)
                if len(exp_sub) >= 2:
                    sub = exp_sub
            for k_idx, (b_num, _) in enumerate(b_list):
                b_i = b_num - 1
                cam_txt = sub_cams.get(k_idx) or sub_cams.get(0)
                if cam_txt:
                    cams_m[b_i] = cam_txt
                clause_txt = sub.get(k_idx) if k_idx in sub else (base_c if k_idx == 0 else "")
                if clause_txt:
                    mapped[b_i] = clause_txt
        return cams_m, mapped

    exp_cams, exp_clauses = _segments_for_dial(exp_opts, is_explicit=True)
    cb_cams, cb_clauses = _segments_for_dial(combat_opts)
    pose_cams, pose_clauses = _segments_for_dial(pose_opts)
    cam_shot_cams, cam_shot_clauses = ({}, {}) if is_pov else _segments_for_dial(cam_opts, is_camera_dial=True)

    # Expand 1-sentence rules in single-take scenes
    if n_shots == 1 and len(exp_clauses) == 1 and 0 in exp_clauses and len(spans) >= 2:
        split_e = _split_long_single_clause(exp_clauses[0], len(spans), lab=lab, brief=brief, flavors=flavors)
        if len(split_e) >= 2:
            exp_clauses = split_e
    if n_shots == 1 and len(pose_clauses) == 1 and 0 in pose_clauses and len(spans) >= 2:
        split_p = _split_long_single_clause(pose_clauses[0], len(spans), lab=lab, brief=brief, flavors=flavors)
        if len(split_p) >= 2:
            pose_clauses = split_p

    # Initial StateLedger
    w_ids = _cat.parse_multi_ids(flavors.get("wardrobe"))
    wmode_st = _bg.get_dial_mode(flavors, "wardrobe", "sequence")
    all_nude = bool({"nude_both_partners", "nude_all_cast_subjects_s1_s9"} & set(w_ids)) or (len(ward_opts) == 1 and str(ward_opts[0].get("id") or "").startswith("nude_"))
    if all_nude:
        w_base = "nude"
    elif wmode_st == "split" and len(ward_opts) >= 2:
        w_base = "; ".join(
            f"{_sub_lbl(subs[idx] if idx < len(subs) else idx + 1)}={clean_ui_label(o.get('label') or '')}"
            for idx, o in enumerate(ward_opts)
        )
    else:
        w_base = ", ".join(clean_ui_label(o.get("label") or "") for o in ward_opts) if ward_opts else ""
    axis_str = f"{_sub_lbl(subs[0])} screen-left, {_sub_lbl(subs[1])} screen-right" if len(subs) >= 2 else (f"{_sub_lbl(subs[0])} center-frame" if subs else "lead center-frame")
    init_orient = "rear-facing (face/chest turned away)" if (is_sex and rear_scene and not mirror_scene and not mixed_orient) else ("rear-facing with mirror reflection" if (is_sex and rear_scene and mirror_scene and not mixed_orient) else "front-facing")

    ledger: dict[str, Any] = {
        "outfit_base": w_base,
        "outfit_displaced": "",
        "orientation": init_orient,
        "oral": "mouth free",
        "act_mode": "",
        "axis": axis_str,
        "surface": "",
        "cast_n": len(subs),
    }

    def _cam_profile(txt: str) -> tuple[str, str, str, str, str, str]:
        tl = str(txt or "").lower()
        elev = "low" if re.search(r"\b(?:low[- ]angle|worm.?s[- ]eye|floor[- ]level|near shin|looking (?:steeply )?upward)\b", tl) else ("high" if re.search(r"\b(?:high[- ]angle|elevated angle|bird.?s[- ]eye|overhead|top[- ]down|looking (?:cleanly )?down(?:ward)?)\b", tl) else "")
        size = "close" if re.search(r"\b(?:extreme close[- ]up|ecu|close[- ]up|tight frame|macro)\b", tl) else ("wide" if re.search(r"\b(?:wide shot|full[- ]body|full shot|establishing wide|long shot)\b", tl) else "")
        orient = "rear" if re.search(r"\b(?:from behind|behind-the-back|rear angle|rear view|over-the-shoulder|from the rear)\b", tl) else ("front" if re.search(r"\b(?:facing camera|front-facing|frontal|direct eye contact)\b", tl) else "")
        motion = "static" if re.search(r"\b(?:static\s+locked|locked[- ]off|tripod\s+locked|motionless\s+camera)\b", tl) else ("moving" if re.search(r"\b(?:orbit|tracking|dolly|crane|whip[- ]?pan|handheld|steadi?cam|pedestal)\b", tl) else "")
        roll = "tilted" if re.search(r"\b(?:dutch\s+angle|canted|tilted\s+horizon|barrel\s+roll)\b", tl) else ("level" if re.search(r"\b(?:strictly\s+level\s+horizon|level\s+horizon)\b", tl) else "")
        persp = "pov" if re.search(r"\b(?:first[- ]person\s+pov|\bpov\b)\b", tl) else ("third" if re.search(r"\b(?:over[- ]the[- ]shoulder|third[- ]person|side[- ]profile)\b", tl) else "")
        return elev, size, orient, motion, roll, persp

    def _cam_conflicts(a: str, b: str) -> bool:
        pa = _cam_profile(a)
        pb = _cam_profile(b)
        return any(va and vb and va != vb for va, vb in zip(pa, pb))

    # Build [Shot 1] header metadata
    canvas_asp = _bg.detect_canvas_aspect(brief=brief, node_aspect=str(flavors.get("aspect") or ""), camera_id=",".join(o["id"] for o in cam_opts))
    canvas_bkt = _bg.aspect_bucket(canvas_asp)
    s1_parts: list[str] = []
    s1_cam_parts: list[str] = []
    if canvas_bkt == "9:16":
        s1_parts.append(f"Vertical {canvas_asp} framing")
        s1_cam_parts.append(f"Vertical {canvas_asp} framing")
    elif canvas_bkt == "1:1":
        s1_parts.append("Square 1:1 framing")
        s1_cam_parts.append("Square 1:1 framing")
    elif canvas_bkt == "16:9":
        s1_parts.append(f"Wide {canvas_asp} framing")
        s1_cam_parts.append(f"Wide {canvas_asp} framing")
    if style_opts:
        st_str = _fin.sanitize_additive_rule(style_opts[0].get("rule") or style_opts[0]["label"])
        s1_parts.append(st_str)
        s1_cam_parts.append(st_str)
    style_xfer_st = _dir.resolve_style_transfer(brief=brief, flavors=flavors, lab=lab)
    if style_xfer_st:
        s1_parts.append(f"rendered in {style_xfer_st['label']} with {style_xfer_st['cues']}")
    if era_opts:
        s1_parts.append(_lc_lead(_fin.sanitize_additive_rule(era_opts[0].get("rule") or era_opts[0]["label"])))
    if tv_opts:
        s1_parts.append(_lc_lead(_fin.sanitize_additive_rule(tv_opts[0].get("world") or tv_opts[0]["label"])))
    fx_timing_st = str(flavors.get("fx_timing") or "delayed_mid").strip().lower()
    if fx_opts and (
        fx_timing_st == "from_start"
        or len(spans) < 2
        or all(
            str(o.get("id") or "").lower().startswith(("fx_ultrareal_", "fx_vhs_", "fx_anamorphic_"))
            or str(o.get("id") or "").lower() in ("fx_raindrop_on_camera_glass", "fx_golden_dust_motes_sunbeam")
            for o in fx_opts
        )
    ):
        fx_s1 = ", ".join(_lc_lead(_fin.sanitize_additive_rule(o.get("rule") or o["label"])) for o in fx_opts if (o.get("rule") or o.get("label")))
        if fx_s1:
            s1_parts.append(fx_s1)

    exp_is_cont = topo["genre"] == "explicit_cont"
    shot1_cam_txt = exp_cams.get(0) or cb_cams.get(0) or pose_cams.get(0) or ""
    cam0_preview = ""
    if cam_opts and not is_pov:
        cam0_preview = cam_shot_cams.get(0) or cam_shot_clauses.get(0) or _fin.sanitize_additive_rule(cam_opts[0].get("rule") or cam_opts[0]["label"])
    arb_cam_ref = shot1_cam_txt or cam0_preview

    for lens_o in lens_opts:
        lens_str = _fin.sanitize_additive_rule(lens_o.get("rule") or lens_o["label"])
        if lens_str and not (arb_cam_ref and _cam_conflicts(lens_str, arb_cam_ref)):
            s1_parts.append(lens_str)
            s1_cam_parts.append(lens_str)
    if place_opts:
        s1_parts.append("inside " + _lc_lead(_fin.sanitize_additive_rule(place_opts[0].get("rule") or place_opts[0]["label"])))
    if light_opts:
        s1_parts.append("lit by " + _lc_lead(_fin.sanitize_additive_rule(light_opts[0].get("rule") or light_opts[0]["label"])))
    if col_opts:
        s1_parts.append(_lc_lead(_fin.sanitize_additive_rule(col_opts[0].get("rule") or col_opts[0]["label"])))

    if is_pov:
        pov_cam_tag = "first-person male POV perspective" if pov_val == "male" else ("first-person female POV perspective" if pov_val == "female" else "first-person POV perspective")
        cam_tail_s1 = pov_cam_tag if not shot1_cam_txt else _lc_lead(shot1_cam_txt)
        s1_parts.append(cam_tail_s1)
        s1_cam_parts.append(cam_tail_s1)
    else:
        if shot1_cam_txt:
            s1_parts.append(_lc_lead(shot1_cam_txt))
            s1_cam_parts.append(_lc_lead(shot1_cam_txt))
        elif cam_opts:
            c0_raw = _fin.sanitize_additive_rule(cam_opts[0].get("rule") or cam_opts[0]["label"])
            has_multi_in_cam = bool(cam_shot_cams.get(1) or re.search(r"\[\s*Shot\s+2\s*\]", c0_raw, re.I))
            if exp_is_cont and has_multi_in_cam:
                c0_pick = cam_shot_cams.get(0) or cam_shot_clauses.get(0) or "continuous smooth tracking framing"
                c0_pick_lc = _lc_lead(re.sub(r"\b(?:three-shot|two-shot|cut(?:ting|s)?)\b", "continuous", c0_pick, flags=re.I))
                s1_parts.append(c0_pick_lc)
                s1_cam_parts.append(c0_pick_lc)
            elif has_multi_in_cam:
                c0_pick = cam_shot_cams.get(0) or cam_shot_clauses.get(0) or c0_raw.split("[Shot 2]")[0]
                c0_pick = re.sub(r"^.*?\[\s*Shot\s+1\s*\]\s*", "", c0_pick, flags=re.I).strip(" .;,:")
                if c0_pick:
                    s1_parts.append(_lc_lead(c0_pick))
                    s1_cam_parts.append(_lc_lead(c0_pick))
            else:
                s1_parts.append(_lc_lead(c0_raw))
                s1_cam_parts.append(_lc_lead(c0_raw))
        if shot1_cam_txt and cam_opts and not cam_shot_cams.get(1) and not re.search(r"\[\s*Shot\s+2\s*\]", cam_opts[0].get("rule") or "", re.I):
            c_id0 = cam_opts[0]["id"]
            if c_id0 not in ("portrait_vertical_stack", "landscape_widescreen_blocking", "multi_position_3cut_intimate", "cam_viral_dutch_90roll_wipe_cuts"):
                c0_extra = _fin.sanitize_additive_rule(cam_opts[0].get("rule") or "")
                if c0_extra and len(c0_extra) < 260 and not (exp_is_cont and "cut" in c0_extra.lower()) and not _cam_conflicts(c0_extra, shot1_cam_txt):
                    if c_id0 == "body_contour_s_curve_pedestal_glide" and exp_opts and not any(str(o.get("id") or "").startswith(("solo_", "undress_")) for o in exp_opts):
                        glide_s = "smooth body-contouring camera glide following hips and torso"
                        s1_parts.append(glide_s)
                        s1_cam_parts.append(glide_s)
                    else:
                        s1_parts.append(_lc_lead(c0_extra))
                        s1_cam_parts.append(_lc_lead(c0_extra))

    clean_s1 = [p.strip().rstrip(".") for p in s1_parts if p and p.strip().rstrip(".")]
    clean_cam_s1 = [p.strip().rstrip(".") for p in s1_cam_parts if p and p.strip().rstrip(".")]
    header_s1 = "[Shot 1] " + (", ".join(clean_s1) or f"{s1_who} inside the scene") + "."
    cam_s1 = (", ".join(clean_cam_s1) or f"{s1_who} framed inside the scene") + "."

    # Distribute active rule clauses cleanly onto ShotNode -> MicroBeat[]
    polish_fn = _make_polish_fn(lab, brief=brief, flavors=flavors)
    brief_clean = _format_brief_beat(brief, lab=lab, flavors=flavors, strip_quotes=bool(topo["q_map"]))
    brief_is_speech = bool(re.search(r"\b(?:whispers?|says?|asks?|speaks?|murmurs?|replies?|calls?\s+out)\b", brief_clean, re.I))

    # Prepare single-take clause expansion if 3-clause rule meets 4-beat topology
    single_clauses: dict[int, str] = {}
    if n_shots == 1:
        n_b0 = len(topo["shots"][0]["beats"])
        src_map = exp_clauses or cb_clauses or pose_clauses
        if topo["source"] == "ms_rule":
            single_clauses = dict(src_map)
        elif src_map:
            if len(src_map) == n_b0 and all(i in src_map for i in range(n_b0)):
                single_clauses = dict(src_map)
            else:
                ordered = [src_map[k] for k in sorted(src_map.keys()) if src_map.get(k)]
                if len(ordered) == 1 and cb_clauses and pose_clauses and not exp_clauses:
                    ordered = [f"{pose_clauses[0].rstrip('.')} before {cb_clauses[0]}"]
                if len(ordered) == n_b0:
                    single_clauses = {i: ordered[i] for i in range(n_b0)}
                elif len(ordered) == 3 and n_b0 == 4:
                    split_done = False
                    for try_i in (1, 0, 2):
                        pair = split_clause_for_two_microbeats(ordered[try_i], lab, brief=brief, flavors=flavors)
                        if pair:
                            if try_i == 0:
                                single_clauses = {0: pair[0], 1: pair[1], 2: ordered[1], 3: ordered[2]}
                            elif try_i == 1:
                                single_clauses = {0: ordered[0], 1: pair[0], 2: pair[1], 3: ordered[2]}
                            else:
                                single_clauses = {0: ordered[0], 1: ordered[1], 2: pair[0], 3: pair[1]}
                            split_done = True
                            break
                    if not split_done:
                        single_clauses = {0: ordered[0], 1: ordered[1], 2: ordered[2]}
                elif len(ordered) > n_b0:
                    for i in range(n_b0):
                        single_clauses[i] = ordered[i] if i < n_b0 - 1 else "; ".join(ordered[n_b0 - 1:])
                else:
                    # Place clauses at non-overlapping sparse indices so adjacent beats never duplicate verbatim
                    for idx_k, c in enumerate(ordered):
                        if idx_k not in single_clauses:
                            single_clauses[idx_k] = c

    shot_nodes: list[ShotNode] = []
    flat_beat_global = 0
    for s_idx, sh_spec in enumerate(topo["shots"]):
        carried = {
            "outfit_base": str(ledger["outfit_base"]),
            "outfit_displaced": str(ledger["outfit_displaced"]),
            "orientation": str(ledger["orientation"]),
            "oral": str(ledger["oral"]),
            "act_mode": str(ledger.get("act_mode") or ""),
            "axis": str(ledger["axis"]),
            "surface": str(ledger["surface"]),
        }
        # Resolve per-shot camera cut string for Shot 2+
        cam_str = shot1_cam_txt if s_idx == 0 else ""
        pl_str = clean_ui_label(place_opts[0]["label"]) if place_opts else ""
        if s_idx > 0:
            if len(place_opts) >= 2 and _bg.get_dial_mode(flavors, "place", "sequence") == "sequence":
                pl_idx = min(len(place_opts) - 1, s_idx)
                pl_str = _fin.sanitize_additive_rule(place_opts[pl_idx].get("rule") or "")
            exp_cut_cam = exp_cams.get(s_idx) or cb_cams.get(s_idx) or pose_cams.get(s_idx) or ""
            cam_cut_cam = cam_shot_cams.get(s_idx) or cam_shot_clauses.get(s_idx) or ""
            _CAM_VERB_RE = r"^(?:cuts?\s|hard[- ]?cut|quick[- ]?cut|smash[- ]?cut|camera\s|snaps?\s|fires?\s|whips?\s|punches?\s|glides?\s|tracks?\s|zooms?\s|tilts?\s|drops?\s|rises?\s|pulls?\s|pushes?\s|orbits?\s|arcs?\s)"
            if exp_cut_cam:
                ec = _lc_lead(exp_cut_cam.rstrip("."))
                ec = re.sub(r"^(?:cleanly\s+to\s+)+", "", ec, flags=re.I).strip()
                cam_str = (ec if ec.lower().startswith("camera") else f"camera {ec}") if re.match(r"^(?:instant\s+hard\s+cut|hard[- ]?cut|quick[- ]?cut|smash[- ]?cut|cuts?\s|snaps?\s|fires?\s|whips?\s|punches?\s|camera\s)", ec, re.I) else f"camera cuts cleanly to {ec}"
            elif cam_cut_cam:
                cc = _lc_lead(cam_cut_cam.rstrip("."))
                cc = re.sub(r"^(?:cleanly\s+to\s+)+", "", cc, flags=re.I).strip()
                cam_str = (cc if cc.lower().startswith("camera") else f"camera {cc}") if re.match(_CAM_VERB_RE, cc, re.I) else f"camera cuts cleanly to {cc}"
            else:
                hint_sc = (exp_clauses.get(s_idx) or pose_clauses.get(s_idx) or cb_clauses.get(s_idx) or "").lower()
                if re.search(r"\b(?:jawline|eyes|lips|cheek|closeup|close-up|wink|smile|gaze|brow|peace sign)\b", hint_sc):
                    cam_str = "camera cuts cleanly to a tight medium close-up capturing upper-body detail and facial expression"
                elif re.search(r"\b(?:knee-lunge|squat|drop|floor|heels|kick|footwork)\b", hint_sc):
                    cam_str = "camera cuts cleanly to a three-quarter medium-full shot framing the stance drop and full motion"
                elif re.search(r"\b(?:rear|doggy|all fours|reverse|glutes|ass)\b", hint_sc):
                    cam_str = "camera cuts cleanly to a three-quarter rear medium angle framing hips, spine arch, and physical contact"
                else:
                    cam_str = f"camera cuts cleanly to a contrasting angle framing Shot {s_idx + 1} contact and expression"

        # Resolve clause(s) for this shot's 1 or 2 MicroBeats
        n_mb = len(sh_spec["beats"])
        shot_beat_clauses: dict[int, str] = {}
        if n_shots >= 2:
            if topo["source"] == "ms_rule":
                for mb_i in range(n_mb):
                    g_i = flat_beat_global + mb_i
                    c_ms = exp_clauses.get(g_i) or cb_clauses.get(g_i) or pose_clauses.get(g_i) or ""
                    if c_ms:
                        shot_beat_clauses[mb_i] = c_ms
            else:
                raw_sc = exp_clauses.get(s_idx) or cb_clauses.get(s_idx) or pose_clauses.get(s_idx) or ""
                if not raw_sc and s_idx == 0 and cb_clauses.get(0) and pose_clauses.get(0):
                    raw_sc = f"{pose_clauses[0].rstrip('.')} before {cb_clauses[0]}"
                if raw_sc:
                    # Extract leading cut-verb override when embedded in multi-shot rule
                    if s_idx > 0:
                        m_cut_lead = re.match(
                            r"^(?:((?:(?:hard|quick|smash|clean)[- ]+)?cutting(?:\s+(?:cleanly|tight|wide|in|out|to|onto))?)|(punching\s+(?:in(?:to)?|out))|(smash\s+cut(?:ting)?(?:\s+(?:wide|far|out|to|into))?))\b([^,\n]{2,160}),\s*(.+)$",
                            raw_sc,
                            flags=re.I | re.S,
                        )
                        if m_cut_lead:
                            verb_raw = (m_cut_lead.group(1) or m_cut_lead.group(2) or m_cut_lead.group(3) or "").lower()
                            tail_cam = m_cut_lead.group(4).strip()
                            rest_act = m_cut_lead.group(5).strip()
                            if verb_raw.startswith("punch"):
                                v_fin = "punches" + verb_raw[len("punching"):]
                            elif "smash" in verb_raw:
                                v_fin = re.sub(r"^(?:smash[- ]+cut(?:ting)?)", "smash-cuts", verb_raw)
                            elif "quick" in verb_raw:
                                v_fin = re.sub(r"^(?:quick[- ]+cutting)", "quick-cuts", verb_raw)
                            elif "hard" in verb_raw:
                                v_fin = re.sub(r"^(?:hard[- ]+cutting)", "hard-cuts", verb_raw)
                            else:
                                v_fin = re.sub(r"^(?:clean[- ]+)?cutting", "cuts", verb_raw)
                            cam_str = f"camera {v_fin} {tail_cam}".strip()
                            raw_sc = rest_act
                    if n_mb == 1:
                        shot_beat_clauses[0] = raw_sc
                    else:
                        pair = split_clause_for_two_microbeats(raw_sc, lab, brief=brief, flavors=flavors)
                        if pair:
                            shot_beat_clauses[0], shot_beat_clauses[1] = pair
                        else:
                            shot_beat_clauses[0] = raw_sc
                elif s_idx == 0 and brief_clean and not (brief_is_speech and 1 in (topo["q_map"] or {})):
                    shot_beat_clauses[0] = brief_clean
        else:
            for mb_i in range(n_mb):
                if single_clauses.get(mb_i):
                    shot_beat_clauses[mb_i] = single_clauses[mb_i]
                elif mb_i == 0 and brief_clean and not (brief_is_speech and 1 in (topo["q_map"] or {})):
                    shot_beat_clauses[0] = brief_clean

        # Weave user intent (`brief_clean`) into Shot 1 Beat 1 when dials are active so user text never vanishes
        if s_idx == 0 and brief_clean and not (brief_is_speech and 1 in (topo["q_map"] or {})):
            b0_cur = shot_beat_clauses.get(0, "")
            if not b0_cur:
                shot_beat_clauses[0] = brief_clean
            elif brief_clean[:24].lower() not in b0_cur.lower():
                shot_beat_clauses[0] = f"{brief_clean.rstrip('.')}; {_lc_lead(b0_cur)}"

        sh_node = ShotNode(
            shot_n=sh_spec["shot_n"],
            t0=sh_spec["t0"],
            t1=sh_spec["t1"],
            camera=cam_str,
            place=pl_str,
            axis_lock=str(ledger["axis"]),
            carried_state=carried,
        )

        # Update orientation from camera string on Shot 2+ so Carried State Into Shot reflects the cut angle
        if s_idx > 0 and cam_str:
            _cam_deltas = _extract_state_delta(cam_str, ledger, is_sex=is_sex, is_mirror=mirror_scene)
            if "orientation" in _cam_deltas:
                sh_node.carried_state["orientation"] = str(ledger["orientation"])

        for mb_i, b_spec in enumerate(sh_spec["beats"]):
            mb = MicroBeat(
                t0=b_spec["t0"],
                t1=b_spec["t1"],
                role=b_spec["role"],
                role_label=b_spec["role_label"],
                weight=b_spec["weight"],
                audio_fg=b_spec["audio_fg"],
                quotes=list(b_spec.get("quotes") or []),
            )
            raw_act = shot_beat_clauses.get(mb_i, "")
            if raw_act:
                mb.action = polish_fn(raw_act)
                mb.state_delta = _extract_state_delta(mb.action, ledger, is_sex=is_sex, is_mirror=mirror_scene)
                mb.state_after = {k: str(v) for k, v in ledger.items()}
            else:
                mb.state_after = {k: str(v) for k, v in ledger.items()}
                mb.action = polish_fn(_build_state_aware_beat_text(
                    sh_node, mb,
                    tree=ShotTree(duration_s=topo["duration_s"], genre=topo["genre"], source=topo["source"], pov=pov_val, canvas_aspect=canvas_asp, q_map=topo["q_map"]),
                    lab=lab, brief=brief, flavors=flavors,
                    exp_opts=exp_opts, combat_opts=combat_opts, pose_opts=pose_opts, fetish_opts=fetish_opts,
                    cam_shot_cams=cam_shot_cams, cam_shot_clauses=cam_shot_clauses,
                    b_idx=flat_beat_global,
                ))
                mb.state_delta = _extract_state_delta(mb.action, ledger, is_sex=is_sex, is_mirror=mirror_scene)
                mb.state_after = {k: str(v) for k, v in ledger.items()}

            # Tag oral-sealed audio focus so automatic dialogue never collides with sucking beats
            if ledger.get("oral") == "lips sealed on shaft" and not mb.quotes:
                mb.audio_fg = "oral_sealed"

            sh_node.beats.append(mb)
            flat_beat_global += 1

        shot_nodes.append(sh_node)

    # Attach dialogue cues cleanly (one speaking focus per beat / shot, never on oral_sealed or pure impact unless explicit quote)
    no_dlg = _dlg.should_suppress_dialogue(brief, flavors=flavors, plan=plan)
    tm = str(flavors.get("talk_mode") or "auto").strip().lower()
    has_speech_ask = bool(re.search(r"\b(?:say\w*|speak\w*|talk\w*|whisper\w*|tell\w*|ask\w*|taunt\w*|mock\w*|teas\w*|flirt\w*|argu\w*|complain\w*|confess\w*|beg\w*|plead\w*|greet\w*|mutter\w*|murmur\w*|answer\w*|repl\w*|shout\w*|yell\w*|explain\w*|narrat\w*|sing\w*|banter\w*|dialogue|monologue)\b", brief or "", re.I))
    has_user_brief = bool(str(brief or "").strip())
    # Do not let a preset's sample <d> force canned dialogue when user typed a non-speaking brief
    exp_has_dlg = (not has_user_brief) and any("<d>" in str(o.get("rule") or "") for o in exp_opts)
    audios = lab.get("audios") or []
    primary_speaker = _sub_lbl(subs[0]) if subs else "The lead character"

    all_beats = [(sh, mb) for sh in shot_nodes for mb in sh.beats]
    n_total_b = len(all_beats)
    cues = _dlg.pick_beat_dialogue_cues(
        brief=brief,
        talk_opt=talk_opts[0] if talk_opts else None,
        acc_opt=acc_opts[0] if acc_opts else None,
        playbook_entries=fetish_opts,
        n_beats=max(1, n_total_b),
        is_sexual_scene=is_sex,
    )
    want_any_dlg = (not no_dlg) and (bool(topo["q_map"]) or tm == "talk_all" or bool(talk_opts) or bool(acc_opts) or has_speech_ask or exp_has_dlg)
    if want_any_dlg and all_beats:
        tgt_lang = _dlg.detect_target_language(brief, acc_opts[0] if acc_opts else None)
        acc_tag = tgt_lang if tgt_lang != "English" else ((acc_opts[0].get("accent") or acc_opts[0].get("lang") or "English") if acc_opts else "English")
        tone_tag = clean_ui_label(talk_opts[0]["label"]).split("(")[0].strip().lower() if talk_opts else "natural tone"
        au_ref = f" using {audios[0]['label']}" if audios else ""

        # Choose which beats speak without flooding 6-beat timelines
        shot_spoke: set[int] = set()
        for g_i, (sh, mb) in enumerate(all_beats):
            explicit_qs = topo["q_map"].get(g_i) or mb.quotes
            if explicit_qs:
                mb.dialogue_text = f" (DIALOGUE) {primary_speaker} (S1) speaks{au_ref}: <d>[{acc_tag}, {tone_tag}] {explicit_qs[0]}</d>"
                mb.is_canned_cue = False
                mb.audio_fg = "dialogue"
                shot_spoke.add(sh.shot_n)
                continue
            if mb.audio_fg in ("oral_sealed", "impact"):
                continue
            if tm == "talk_all":
                # 1 speaking beat per shot so foley/breath breathe between lines
                if len(shot_nodes) >= 2 and sh.shot_n in shot_spoke:
                    continue
                mb.dialogue_text = f" (DIALOGUE) {primary_speaker} (S1) speaks{au_ref}: <d>[{acc_tag}, {tone_tag}] {cues[g_i]}</d>"
                mb.is_canned_cue = True
                mb.audio_fg = "dialogue"
                shot_spoke.add(sh.shot_n)
            elif bool(talk_opts) or bool(acc_opts) or has_speech_ask or exp_has_dlg:
                # Non-talk_all auto speech: place cleanly on opening/mid beat per shot (max 1 per shot)
                if sh.shot_n in shot_spoke:
                    continue
                if len(sh.beats) >= 2 and g_i == 0 and len(shot_nodes) == 1 and sh.beats[1].audio_fg not in ("oral_sealed", "impact"):
                    continue
                mb.dialogue_text = f" (DIALOGUE) {primary_speaker} (S1) speaks{au_ref}: <d>[{acc_tag}, {tone_tag}] {cues[g_i]}</d>"
                mb.is_canned_cue = True
                mb.audio_fg = "dialogue"
                shot_spoke.add(sh.shot_n)

    sm_tree = _fin.resolve_sound_mode(brief=brief, flavors=flavors)
    pure_bgm_tree = _fin.is_pure_bgm_soundscape(brief=brief, flavors=flavors, sex_scene=is_sex)
    if pure_bgm_tree or sm_tree == "quiet_air":
        scrub_m = "pure_bgm" if pure_bgm_tree else "quiet_air"
        for _sh, _mb in all_beats:
            if _mb.action:
                _mb.action = _fin.scrub_foley_cues_in_description(_mb.action, mode=scrub_m)
            if not _mb.dialogue_text and _mb.audio_fg not in ("oral_sealed",):
                _mb.audio_fg = "music" if pure_bgm_tree else "quiet_air"

    return ShotTree(
        duration_s=topo["duration_s"],
        genre=topo["genre"],
        source=topo["source"],
        pov=pov_val,
        canvas_aspect=canvas_asp,
        initial_state={
            "cast": [(_sub_lbl(sn), infer_subject_pronouns(sn, lab=lab, brief=brief, flavors=flavors)[2]) for sn in subs],
            "wardrobe": w_base,
            "axis": axis_str,
            "place": clean_ui_label(place_opts[0]["label"]) if place_opts else "",
        },
        shots=shot_nodes,
        q_map=topo["q_map"],
        header_s1=header_s1,
        cam_s1=cam_s1,
        is_extracted=False,
        brief=str(brief or "").strip(),
    )


def _garment_already_cited(text: str, disp: str) -> bool:
    if not disp or not text:
        return True
    keys = {k.lower() for k in _GARMENT_KEY_RX.findall(disp)}
    if not keys:
        return True
    t_low = text.lower()
    return any(k in t_low for k in keys)


def render_skeleton_prose(
    tree: ShotTree,
    lab: dict,
    *,
    brief: str = "",
    flavors: dict | None = None,
) -> str:
    """Compile a `ShotTree` into clean H3 `[Shot N]` + `At MM:SS.mmm-MM:SS.mmm,` prose (CPU Tie / Skeleton)."""
    flavors = flavors or {}
    if tree.is_extracted:
        lines = [tree.header_s1]
        for sh in tree.shots:
            if sh.shot_n > 1 and sh.beats:
                lines.append(f"[Shot {sh.shot_n}] At {_bg.stamp(sh.beats[0].t0)}, {sh.camera}")
            for mb in sh.beats:
                lines.append(f"At {_bg.stamp(mb.t0)}-{_bg.stamp(mb.t1)}, {mb.action}")
        return "\n".join(lines)

    place_opts = _cat.resolve_dial_opts("place", flavors.get("place"))
    seq_place = len(place_opts) >= 2 and _bg.get_dial_mode(flavors, "place", "sequence") == "sequence"
    fx_opts_r = _cat.resolve_dial_opts("fx", flavors.get("fx"))
    fx_timing_r = str(flavors.get("fx_timing") or "delayed_mid").strip().lower()
    delayed_fx_txt = ""
    total_beats_r = sum(len(sh.beats) for sh in tree.shots)
    if fx_opts_r and fx_timing_r != "from_start" and total_beats_r >= 2 and not all(
        str(o.get("id") or "").lower().startswith(("fx_ultrareal_", "fx_vhs_", "fx_anamorphic_"))
        or str(o.get("id") or "").lower() in ("fx_raindrop_on_camera_glass", "fx_golden_dust_motes_sunbeam")
        for o in fx_opts_r
    ):
        delayed_fx_txt = ", ".join(_lc_lead(_fin.sanitize_additive_rule(o.get("rule") or o["label"])) for o in fx_opts_r if (o.get("rule") or o.get("label")))
    mid_beat_global = max(1, total_beats_r // 2)

    expr_val_r = _dir.normalize_perf_level("expression", flavors.get("expression"), fallback="natural")
    life_val_r = _dir.normalize_perf_level("life", flavors.get("life"), fallback="natural")
    _EXPR_CPU_MAP = {
        "stoic": "holding calm deadpan facial restraint",
        "subtle": "showing subtle eye and brow micro-reads",
        "vivid": "with vivid expressive facial acting",
        "theatrical": "with bold heightened theatrical expression",
    }
    _LIFE_CPU_MAP = {
        "lock": "with quiet steady breathing and poised stillness",
        "subtle": "as subtle room air and breath stir gently",
        "alive": "with active swaying hair, fabric motion, and lively prop details",
        "hyper": "amid kinetic swirling hair, reactive fabric, and layered background movement",
    }
    perf_tail_b0 = ", ".join(p for p in (_EXPR_CPU_MAP.get(expr_val_r, ""), _LIFE_CPU_MAP.get(life_val_r, "")) if p)

    lines = [tree.header_s1]
    global_bi = 0

    for s_idx, sh in enumerate(tree.shots):
        if s_idx > 0:
            cam_line = sh.camera or "camera cuts cleanly to a contrasting close-medium angle focused on hands, posture, and expression"
            pl_note = f" inside {sh.place}" if (seq_place and sh.place and sh.place.lower() not in cam_line.lower()) else ""
            # Carry displaced garment state automatically across [Shot N] boundaries
            disp = str(sh.carried_state.get("outfit_displaced") or "").strip()
            first_act = sh.beats[0].action if sh.beats else ""
            carry_note = ""
            if disp and not _garment_already_cited(f"{cam_line} {first_act}", disp):
                carry_note = f", keeping {disp} in place"
            lines.append(f"[Shot {sh.shot_n}] At {_bg.stamp(sh.t0)}, {cam_line}{pl_note}{carry_note}.")

        for mb_i, mb in enumerate(sh.beats):
            act = (mb.action or "").rstrip(".")
            if s_idx == 0 and mb_i > 0:
                prev_disp = str(sh.beats[mb_i - 1].state_after.get("outfit_displaced") or "")
                if prev_disp and not mb.state_delta.get("outfit") and not _garment_already_cited(act, prev_disp) and mb.role in ("pivot_align", "entry_drive"):
                    if "removed" in prev_disp or "left open" in prev_disp:
                        act = f"{act} with {prev_disp}"
                    else:
                        act = f"{act} with {prev_disp} still held clear"
            if global_bi == 0 and perf_tail_b0 and perf_tail_b0.lower() not in act.lower():
                act = f"{act}, {perf_tail_b0}"
            if delayed_fx_txt and global_bi == mid_beat_global and delayed_fx_txt[:24].lower() not in act.lower():
                act = f"{act}, unleashing {delayed_fx_txt}"
            lines.append(f"At {_bg.stamp(mb.t0)}-{_bg.stamp(mb.t1)}, {act}.{mb.dialogue_text}")
            global_bi += 1

    return "\n".join(lines)


def render_llm_blueprint(
    tree: ShotTree,
    lab: dict,
    *,
    brief: str = "",
    flavors: dict | None = None,
    include_brief: bool = True,
) -> str:
    """Compile a structured, state-aware Shot-Tree Blueprint for `Quick Tie` & `Plan` LLM calls."""
    if tree.is_extracted:
        return render_skeleton_prose(tree, lab, brief=brief, flavors=flavors)

    lines: list[str] = []
    n_s = len(tree.shots)
    n_b = sum(len(sh.beats) for sh in tree.shots)
    topo_desc = f"{n_s} shot{'s' if n_s != 1 else ''} ({'0 cuts — one unbroken continuous take' if n_s == 1 else f'{n_s - 1} hard cut(s)'}), {n_b} micro-beats"
    sm_bp = _fin.resolve_sound_mode(brief=brief, flavors=flavors)
    sound_tag = f" | Sound: {sm_bp}" if sm_bp != "auto" else (" | Sound: pure_bgm (auto)" if _fin.is_pure_bgm_soundscape(brief=brief, flavors=flavors) else "")
    lines.append(f"Topology: {topo_desc} | Genre: {tree.genre} | Duration: {tree.duration_s:.2f}s" + (f" | Aspect: {tree.canvas_aspect}" if tree.canvas_aspect else "") + sound_tag)
    use_brief = str(brief or getattr(tree, "brief", "") or "").strip()
    if use_brief and include_brief:
        lines.append(f"User Intent (TOP PRIORITY — weave every detail & dialogue topic into beats below): {use_brief}")
    init = tree.initial_state or {}
    if init.get("axis"):
        lines.append(f"Initial Axis: {init['axis']}" + (f" | Base Wardrobe: {init['wardrobe']}" if init.get("wardrobe") else "") + (f" | Place: {init['place']}" if init.get("place") else ""))

    for sh in tree.shots:
        hdr = f"[Shot {sh.shot_n}]" if sh.shot_n == 1 else f"[Shot {sh.shot_n}] At {_bg.stamp(sh.t0)}"
        cam_txt = (tree.cam_s1 or tree.header_s1[8:].strip()) if sh.shot_n == 1 else (sh.camera or "contrasting camera angle")
        lines.append(f"{hdr} ({_bg.stamp(sh.t0)}->{_bg.stamp(sh.t1)}) | Camera: {cam_txt}")
        cs = sh.carried_state or {}
        first_d = sh.beats[0].state_delta if sh.beats else {}
        eff_orient = first_d.get("orientation") or cs.get("orientation")
        eff_oral = first_d.get("oral") or cs.get("oral")
        carry_bits: list[str] = []
        if cs.get("outfit_displaced"):
            carry_bits.append(f"CARRIED DISPLACED OUTFIT={cs['outfit_displaced']}")
        elif cs.get("outfit_base"):
            carry_bits.append(f"outfit={cs['outfit_base']}")
        if eff_orient:
            carry_bits.append(f"orientation={eff_orient}")
        if cs.get("surface"):
            carry_bits.append(f"surface={cs['surface']}")
        if eff_oral and eff_oral != "mouth free":
            carry_bits.append(f"oral={eff_oral}")
        if carry_bits:
            lines.append("  Carried State Into Shot: " + " | ".join(carry_bits))
        for mb in sh.beats:
            delta_s = f" | delta={'; '.join(f'{k}:{v}' for k, v in mb.state_delta.items())}" if mb.state_delta else ""
            beat_dur = max(0.5, mb.t1 - mb.t0)
            w_lo = max(3, int(round(beat_dur * 1.6)))
            w_hi = max(w_lo + 2, int(round(beat_dur * 2.5)))
            if mb.dialogue_text and mb.is_canned_cue and use_brief:
                m_tag = re.search(r"<d>\s*(\[[^\]]+\])", mb.dialogue_text, re.I)
                tag_ex = m_tag.group(1) if m_tag else "[English, natural tone]"
                dlg_s = f" | spoken_cue=AUTHOR FRESH <d>{tag_ex} ...</d> FROM <scene_brief> (~{w_lo}-{w_hi} spoken words for {beat_dur:.1f}s, distinct, commas/periods only)"
            elif mb.dialogue_text:
                dlg_s = f" | spoken_cue={mb.dialogue_text.strip()} (~{w_lo}-{w_hi} words for {beat_dur:.1f}s)"
            else:
                dlg_s = ""
            lines.append(f"  - At {_bg.stamp(mb.t0)}-{_bg.stamp(mb.t1)} [{mb.role_label} | audio={mb.audio_fg}{delta_s}]: {mb.action}{dlg_s}")

    return "\n".join(lines)


def render_state_invariants(tree: ShotTree, plan: str = "") -> str:
    """Compact continuity invariant ledger passed alongside user-edited `approved_plan` in `Write`."""
    if tree.is_extracted or not tree.shots:
        return ""
    rows: list[str] = []
    init = tree.initial_state or {}
    if init.get("axis"):
        rows.append(f"Axis: {init['axis']}")
    plan_txt = str(plan or "").strip()
    if plan_txt:
        # Derive per-shot carried invariants directly from user's edited plan so edited cuts/outfits stay respected
        sh_rx = re.compile(r"\[\s*Shot\s+(\d+)\s*\]", re.I)
        matches = list(sh_rx.finditer(plan_txt))
        if matches:
            st_ledger: dict[str, Any] = {
                "outfit_base": str(init.get("outfit_base") or init.get("wardrobe") or ""),
                "outfit_displaced": "",
                "orientation": "",
            }
            for idx_m, m in enumerate(matches):
                sn = int(m.group(1))
                chunk = plan_txt[m.start():(matches[idx_m + 1].start() if idx_m + 1 < len(matches) else len(plan_txt))]
                carried_disp = st_ledger.get("outfit_displaced") or ""
                _extract_state_delta(chunk, st_ledger, is_sex=tree.genre.startswith("explicit"), is_mirror=bool(_MIRROR_BEAT_RX.search(chunk)))
                parts = []
                if carried_disp:
                    parts.append(f"keep displaced outfit ({carried_disp})")
                elif st_ledger.get("outfit_base"):
                    parts.append(f"outfit={st_ledger['outfit_base']}")
                if st_ledger.get("orientation"):
                    parts.append(f"orientation={st_ledger['orientation']}")
                if parts:
                    rows.append(f"Shot {sn}: " + ", ".join(parts))
            return "\n".join(rows)

    for sh in tree.shots:
        cs = sh.carried_state or {}
        first_d = sh.beats[0].state_delta if sh.beats else {}
        eff_orient = first_d.get("orientation") or cs.get("orientation")
        parts = []
        if cs.get("outfit_displaced"):
            parts.append(f"keep displaced outfit ({cs['outfit_displaced']})")
        elif cs.get("outfit_base"):
            parts.append(f"outfit={cs['outfit_base']}")
        if eff_orient:
            parts.append(f"orientation={eff_orient}")
        if parts:
            rows.append(f"Shot {sh.shot_n}: " + ", ".join(parts))
    return "\n".join(rows)
