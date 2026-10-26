"""Check a music-video plan: the node's own validator, then the MV rules learned on renders.

    python check_plan.py shot_plan.json ref_plan.json
    python check_plan.py shot_plan.json ref_plan.json --pin-mech motion_context --no-mv

Part 1 is `planner.validate` from the pack -- the same checks the node runs, so an
error here is a plan the node will reject. It needs ComfyUI's Python (it imports
the node). If that import fails, part 1 is skipped and the script says so; do not
call a plan valid when part 1 did not run.

Part 2 is this skill's lints. Each one is a failure seen on a real render:

  opens-on-place   the first sentence names a place plate before any person:
                   the hop's first frame becomes the empty plate. Safe only when
                   the opening verb is an action ON something in the plate (a car
                   door opens, a vault door swings open) that brings the people in.
  dialogue         a <d> line under master audio: the song drives the mouths.
  restart          anchor=restart without join=hard_cut, or without refs.
  tag-prefix       one tag is the start of another (@vault / @vault_dial): the
                   place lint and the reader confuse them.
  pronoun          "they/them" in a beat that names one person: plural pronouns
                   have rendered two people from one reference.
  vague-camera     a camera placed on/at something with no facing direction
                   ("fixed on the dashboard" rendered as a dashcam facing out).
  song-words       a song-structure word in a beat ("sings the hook", "the second
                   verse", "the last line"): the video model never hears the song's
                   sections, so the words mean nothing. Describe the delivery.
  barrier          bars/gate/glass/railing in a beat with no side named: people
                   warp through barriers whose sides were never fixed.
  pin-face         the hop before a continuation does not end on a face toward
                   the camera: the continuation rebuilds identity from that ending.
  two-subjects-one-mouth  (review) every beat with two or more people should give
                   the non-rapper an action; listed for a human/model read.
  outfit           two subjects whose clothing shares most of its words: alike
                   clothes merge two people into one in a shared frame.
  back-view        a walk or run "away from the camera" with no "back to the
                   camera": it can render as a face to the lens moving backward.
  prop-words       the same long description in two or more hops with no tag: a
                   prop held by words alone is redrawn in every appearance.
  beside-tag       a close "from beside @b" with no "alone in the frame": @b gets
                   drawn into the shot.
  pull-in          a close shot whose eyeline names someone off the frame, with no
                   "alone in the frame": that person can be drawn into the close.
  no-eye-target    a face toward the camera with nothing named for the eyes: it
                   looks into the lens.
  absence          "silent", "in silence", "without a sound": naming an absence
                   adds it. Write the mouth and the sound that is there.
  solo-window      a timed window in a shot with several people that gives only one
                   of them an action: the frame waits while one person moves.
  frozen           "nobody moves", "holds still": only mouths need control; a frozen
                   frame plays like a slideshow.
  phone            a phone at someone's ear in a shot with no line: the model
                   gives the call a voice.
  offscreen-action a tagged person off the frame given an action ("@b running off
                   ..., off the frame"): they are drawn doing it, small in the
                   distance. Off the frame a person is only the eyes' target.
  empty-spot       "the empty seat / hand / table": naming the spot draws it, and a
                   prop whose picture rides the hop comes back on it.
  exit-side        someone leaves the frame to one side and a later shot of the hop
                   places them off the frame on the other.
  move-time        a timed window too short for its movements: two or more people
                   each travelling in under 6 s, or one person moving twice in under
                   4 s. Squeezed movements are skipped or the people doubled.

With --map scene_map.json (written before the beats, see references/directing.md):

  goal-behind      a scene whose goal lies in the far distance of its plate has a
                   run or walk toward the camera: the plate puts the goal behind
                   the traveller, so she seems to run away from it (and the reverse
                   for a goal behind the camera).
  sides            a shot puts someone on the side of the frame the map gives to
                   someone else for that plate's view.
  prop-picture     a prop in two or more hops with no picture, or its picture's
                   row missing from a hop it is in.
  cast-missing     someone in the scene's cast has no row on a continuation hop of it.
  prop-holder      the map says who holds a prop on a hop, and that person is not
                   in the hop's beat.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _htc  # noqa: E402

FACE = re.compile(r"\b(camera|lens|face|faces|grin\w*|smil\w*|look\w* (in|at|into))\b", re.I)
CAM_PLACE = re.compile(r"\bcamera\b[^.]{0,40}\b(fixed|mounted|placed|set|sits?|rests?)\b[^.]{0,30}\b(on|at|in)\b", re.I)
TRAVEL = re.compile(r"\b(?:runs?|running|walks?|walking|rush(?:es)?|sprints?|charges?|dash(?:es)?|hurr(?:y|ies)|strides?)\b"
                    r"[^.]{0,80}\btoward(?:s)? (?:the camera|@\w+)", re.I)
TRAVEL_END = re.compile(r"\b(?:stops?|halts?|comes to a stop|past the (?:lens|camera)|out of (?:the )?frame|"
                         r"camera (?:\w+ly )?(?:backs|tracks back(?:ward)?|pulls back|retreats)\b[^.]{0,30}\bahead of)\b", re.I)
SOUND = re.compile(r"\b(?:sound\w*|hum\w*|wind|rain\w*|drum\w*|tick\w*|siren\w*|beep\w*|footsteps|traffic|"
                   r"chim\w*|roar\w*|hiss\w*|clank\w*|clang\w*|creak\w*|buzz\w*|echo\w*|click\w*|wail\w*|"
                   r"rustl\w*|splash\w*|patter\w*|crackl\w*|rumbl\w*|whir\w*|thump\w*|"
                   r"knock\w*|bang\w*|slam\w*|squeak\w*|whisper\w*|puls\w*|throb\w*|bass|chord|score|"
                   r"piano|strings?|drone)\b", re.I)
CAM_DIR = re.compile(r"\b(facing|faces|looking|looks|pointed|pointing|aimed|turned)\b", re.I)
DIALOGUE = re.compile(r"<d>", re.I)
# changes of state that each take seconds; a run or walk that carries on is not counted
STATE_MOVE = re.compile(r"\b(walks? (?:round|around|across|over to|up to)|crosses|climbs?|climbing|"
                    r"opens? (?:the |a |his |her )?(?:[\w']+ )?door|gets? (?:in|into|out)|"
                    r"sits? down|stands? up|slides? (?:back )?(?:in|out)|steps? (?:out of|into))\b", re.I)
BARRIER = re.compile(r"\b(bars|gate|gates|glass (?:walls?|panes?|doors?|partition)|window|railings?|fence|grille|cage)\b", re.I)
BARRIER_SIDE = re.compile(r"\b(side|stays? fixed)\b", re.I)
SONG_WORDS = re.compile(r"\b(hooks?|chorus(?:es)?|verses?|pre-?hooks?|refrain|intro|outro|"
                        r"(?:first|last|next|final|opening) (?:line|bar|lines|bars)|line for line)\b", re.I)
PRONOUN = re.compile(r"\b(they|them|themselves)\b", re.I)
PERSON_WORDS = re.compile(r"\b(man|men|woman|women|girls?|boys?|guys?|crew|band|duo|pair|friends|couple|"
                          r"dancers?|singers?|rappers?|both|the (?:two|three|four))\b", re.I)


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


QUOTE = re.compile(r"(?:^|(?<=[\s,]))'[A-Z][^']{2,}'")
AWAY = re.compile(r"\b(?:runs?|running|walks?|walking|sprints?|hurr(?:y|ies)|strides?|dash(?:es)?)\b[^.]{0,60}"
                  r"\baway from the camera\b", re.I)
BACK = re.compile(r"\b(?:back|backs) (?:is |are )?(?:turned )?to the camera\b|\bseen from behind\b", re.I)
TOWARD_CAM = re.compile(r"\b(?:runs?|running|walks?|walking|sprints?|hurr(?:y|ies)|strides?|dash(?:es)?)\b"
                        r"[^.]{0,60}\btoward(?:s)? the camera\b", re.I)
PHONE_EAR = re.compile(r"\bphone\b[^.]{0,80}\bear\b|\bear\b[^.]{0,40}\bphone\b", re.I)
STOP = {"a", "an", "the", "and", "with", "of", "on", "in", "her", "his", "their", "over", "under", "wearing",
        "small", "long", "short", "thin", "thick", "black", "white"}


NOT_PROP = {"frame", "camera", "lens", "gaze", "eyes", "look", "looks", "looking", "hop", "shot", "cut", "lips",
            "face", "faces", "voice", "track", "score", "bass", "throbbing", "humming", "hums", "side", "end",
            "aisle", "behind", "wall", "floor"}


def clothing(context):
    """Content words of what a subject wears (the text after 'wearing')."""
    m = re.search(r"\bwearing\b(.*)", context or "", re.I | re.S)
    words = re.findall(r"[a-z]+", (m.group(1) if m else "").lower())
    return {w for w in words if w not in STOP and len(w) > 2}


def same_base(tag, name):
    """@quiet_a and @a are the same person as map name 'a'."""
    t, n = tag.lower(), name.lower()
    return t == n or t.endswith("_" + n) or n.endswith("_" + t)


def tags_in(text, tags):
    """Tags present in text, matched whole (so @vault does not hit @vault_dial)."""
    out = []
    for t in tags:
        for mt in re.finditer(r"@" + re.escape(t) + r"(?![A-Za-z0-9_])", text, re.I):
            out.append((mt.start(), t))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shot_plan")
    ap.add_argument("ref_plan")
    ap.add_argument("--pin-mech", default="motion_context")
    ap.add_argument("--no-mv", action="store_true", help="not a music video (allows <d>)")
    ap.add_argument("--refs-dir", help="folder holding the reference files (default <ComfyUI>/input/h3_refs)")
    ap.add_argument("--map", help="scene_map.json written before the beats (references/directing.md)")
    ap.add_argument("--htc")
    a = ap.parse_args()

    shot_text = Path(a.shot_plan).read_text(encoding="utf-8")
    ref_text = Path(a.ref_plan).read_text(encoding="utf-8")
    shots = json.loads(shot_text).get("shots") or []
    refs = json.loads(ref_text)
    pack = _htc.find_pack(a.htc)
    mv = not a.no_mv

    print("== part 1: the node's validator")
    ran = False
    try:
        planner = _htc.import_package_module(pack, "planner")
        rdir = Path(a.refs_dir) if a.refs_dir else _htc.refs_dir(pack)
        known = set(os.listdir(rdir)) if rdir.is_dir() else None
        errs, warns = planner.validate(shot_text, ref_text, hops=len(shots), known_files=known,
                                       pin_mech=a.pin_mech, mv=mv)
        ran = True
        print(f"errors {len(errs)}")
        for e in errs:
            print("  E", e)
        print(f"warnings {len(warns)}")
        for w in warns:
            print("  W", w)
        if known is None:
            print("  note: reference folder not found, file names were not checked")
    except Exception as exc:  # noqa: BLE001
        print(f"SKIPPED: could not import the node's validator ({type(exc).__name__}: {exc}).")
        print("  Run this script with ComfyUI's own Python. Until part 1 runs, the plan is unchecked.")

    print("\n== part 2: music-video lints")
    all_refs = refs.get("refs") or []
    people = [r["tag"] for r in all_refs if r.get("subject")]
    places = [r["tag"] for r in all_refs if not r.get("subject")]
    plates = [r["tag"] for r in all_refs if not r.get("subject") and r.get("retention") == "reference"]
    tags = [r["tag"] for r in all_refs]
    lint = []

    for x in tags:
        for y in tags:
            if x != y and y.startswith(x):
                lint.append(f"tag-prefix: @{x} is the start of @{y}. Rename one (e.g. @{y} -> @{y.split('_')[-1]}).")

    for i, s in enumerate(shots, 1):
        beat = s.get("beat") or ""
        d = s.get("directives") or {}
        sents = sentences(beat)
        first = sents[0] if sents else ""
        ft = tags_in(first, tags)
        names = [str((v or {}).get("name") or "").lower() for v in (refs.get("subjects") or {}).values()]
        pos_place = ft[0][0] if ft and ft[0][1] in places else None
        pw = PERSON_WORDS.search(first)
        person_first = pos_place is not None and (
            (pw is not None and pw.start() < pos_place)
            or any(n and 0 <= first.lower().find(n) < pos_place for n in names))
        if pos_place is not None and not person_first:
            lint.append(f"shot {i}: opens-on-place: the first sentence names @{ft[0][1]} before any person "
                        f"(\"{first[:70]}...\"). Lead with a person acting, place inside that line -- unless the "
                        f"first verb opens/moves something in the plate that brings the people in.")
        elif not ft and places and any(t in places for _, t in tags_in(beat, tags)):
            if not tags_in(first, people):
                lint.append(f"shot {i}: opens-on-place: the first sentence has no person in it "
                            f"(\"{first[:70]}...\"). The hop may open on the plate.")
        if mv and DIALOGUE.search(beat):
            lint.append(f"shot {i}: dialogue: a <d> line under master audio. The song drives the mouth; "
                        f"say who raps/sings instead.")
        sw = sorted({m.group(0).lower() for m in SONG_WORDS.finditer(beat)})
        if mv and sw:
            lint.append(f"shot {i}: song-words: {', '.join(sw)}. The video model does not know the song's "
                        f"sections; describe what the mouth and body do (raps fast, sings long notes, "
                        f"takes turns rapping).")
        if BARRIER.search(beat) and not BARRIER_SIDE.search(beat):
            lint.append(f"shot {i}: barrier: \"{BARRIER.search(beat).group(0)}\" with no side named. Say where it sits "
                        f"in frame, which side the camera and each person are on, that it stays fixed; hands on it, "
                        f"never through it.")
        if s.get("anchor") == "restart":
            if d.get("join") != "hard_cut":
                lint.append(f"shot {i}: restart: anchor=restart is a cut; set join=hard_cut.")
            if not s.get("refs"):
                lint.append(f"shot {i}: restart: no refs on the shot; it needs its own refs (or a start image).")
        named_people = {t for _, t in tags_in(beat, people)}
        # a spoken line may say "they" about other people; only the narration counts
        narration = re.sub(r"(?:^|(?<=[\s,]))'[A-Z][^']{2,}'", " ", beat)
        if len(named_people) == 1 and PRONOUN.search(narration):
            lint.append(f"shot {i}: pronoun: \"they/them\" in a one-person beat; use the tag or he/she.")
        if CAM_PLACE.search(beat) and not CAM_DIR.search(beat):
            lint.append(f"shot {i}: vague-camera: the camera is placed somewhere with no direction. Say where "
                        f"it is, which way it faces and whose faces fill the frame.")
        set_dirs = [k for k in ("camera", "framing") if str(d.get(k) or "").strip()]
        if set_dirs:
            lint.append(f"shot {i}: camera-dropdown: {', '.join(set_dirs)} set on the node. Leave them empty and "
                        f"write the move in the beat (rule 6); `hold` adds \"holds its position throughout\".")
        # "the camera arcs / slowly rises / holds"; "toward the camera" is not a camera line.
        if not re.search(r"\bcamera\s+(?:\w+ly\s+)?\w+s\b", beat, re.I):
            lint.append(f"shot {i}: no-camera: the beat never says what the camera does. Write one move "
                        f"(or a deliberate hold) from what the moment is about (references/camera.md).")
        segs = re.split(r"\[Shot\s+\d+\]", beat, flags=re.I)
        if len(segs) > 2:  # a multi-shot beat: segs[0] is the text before [Shot 1]
            for k, seg in enumerate(segs[1:], 1):
                if not tags_in(seg, people):
                    lint.append(f"shot {i}: shot-people: [Shot {k}] names no person. Every cut re-places "
                                f"everyone in frame (who, where, doing what), even someone who sits still.")
            # a hop with lines: a shot showing two or more people with no mouth state invites babble
            if not mv and re.search(r"(?:^|[\s,])'[A-Z][^']{2,}'", beat):
                for k, seg in enumerate(segs[1:], 1):
                    # a face inside a photo or on a screen has no mouth to keep shut
                    if (len({t for _, t in tags_in(seg, people)}) >= 2
                            and not re.search(r"\b(?:lips?|mouths?|jaw|says|laugh\w*)\b", seg, re.I)
                            and not re.search(r"\b(?:photo\w*|polaroid|screens?|monitors?)\b", seg, re.I)):
                        lint.append(f"shot {i}: mouth: [Shot {k}] shows several people in a hop with lines and gives "
                                    f"none of them a mouth state. Add \"lips pressed shut\" for each face.")
            m2 = re.search(r"\[Shot\s+2\]\s*At\s+00:(\d\d)\.(\d+)", beat, re.I)
            cont = i > 1 and s.get("anchor") != "restart"
            if cont and m2 and float(m2.group(1) + "." + m2.group(2)) < 2.0:
                lint.append(f"shot {i}: early-cut: a continuation cuts at {m2.group(1)}.{m2.group(2)} s. "
                            f"[Shot 1] continues the pin; no cut in its first 2 s.")
        # A run or walk toward the camera or a person with no end mark keeps going, past everyone.
        for k, seg in enumerate(segs[1:] if len(segs) > 2 else [beat], 1):
            if TRAVEL.search(seg) and not TRAVEL_END.search(seg):
                where = f"[Shot {k}]" if len(segs) > 2 else "the beat"
                lint.append(f"shot {i}: no-stop: {where} sends someone running or walking toward the camera or a "
                            f"person with no end mark. Say where they stop (\"stops an arm's length in front of "
                            f"@b, facing her\") or that they leave past the lens.")
        if not mv and re.search(r"\b(?:into|at|toward|to) the lens\b|\b(?:into|at) the camera\b", beat, re.I):
            lint.append(f"shot {i}: lens-address: a character looks or speaks into the lens. In a scene the face "
                        f"turns toward the camera but the eyes stay on the other person (camera.md, Eyelines).")
        for q in re.finditer(r"(?:^|[\s,])'[A-Z][^']{2,}'", beat):
            odd = sorted({c for c in q.group(0) if ord(c) > 127 and c.isalpha()})
            if odd:
                lint.append(f"shot {i}: accent: the line {q.group(0).strip()[:40]!r} has {''.join(odd)}. "
                            f"Accented letters inside a quote get garbled; spell it in plain English.")
                break
        quotes = list(re.finditer(r"(?:^|[\s,])'[A-Z][^']{2,}'", beat))
        tail_txt = beat[quotes[-1].end():] if quotes else ""
        # only when the last line is in the hop's last shot (a later shot moves on to other action)
        if not mv and quotes and not re.search(r"\[Shot\s+\d+\]", tail_txt, re.I) and not SOUND.search(tail_txt):
            lint.append(f"shot {i}: after-line: nothing after the hop's last line names a sound. Close the "
                        f"mouth and name one (\"...presses her lips shut, the wind humming\"), or the model "
                        f"adds a few words of babble after the line.")
        if not mv and re.search(r"(?:^|[\s,])'[A-Z][^']{2,}'", beat) and not re.search(r"\beyes (?:stay |fixed |locked )?on @", beat, re.I):
            lint.append(f"shot {i}: eyeline: a line is spoken with no eyeline. Give the speaker's eyes a target "
                        f"and a direction (\"his eyes on @b just left of the lens\"), or he talks to the audience.")
        nxt = shots[i] if i < len(shots) else None
        if nxt is not None and nxt.get("anchor") != "restart" and (nxt.get("directives") or {}).get("join") != "hard_cut":
            last = sents[-1] if sents else ""
            if not FACE.search(last):
                lint.append(f"shot {i}: pin-face: shot {i + 1} continues from this ending, but the last sentence "
                            f"(\"{last[:70]}\") puts no face toward the camera.")

    # --- text lints that need no map ---
    subj = refs.get("subjects") or {}
    keys = list(subj)
    for x in range(len(keys)):
        for y in range(x + 1, len(keys)):
            a_, b_ = clothing(subj[keys[x]].get("context")), clothing(subj[keys[y]].get("context"))
            if a_ and b_ and len(a_ & b_) / min(len(a_), len(b_)) >= 0.6:
                lint.append(f"outfit: subjects {keys[x]} and {keys[y]} wear nearly the same clothes "
                            f"({', '.join(sorted(a_ & b_))}). Alike outfits merge two people into one in a shared "
                            f"frame; change one outfit (and its sheet) before rendering.")
    for i, s in enumerate(shots, 1):
        beat = s.get("beat") or ""
        segs = re.split(r"\[Shot\s+\d+\]", beat, flags=re.I)
        exits = {}   # tag -> (side it left the frame by, shot)
        # prop pictures on this hop: refs with no subject that are not plates
        hop_props = [r.get("tag") for r in (refs.get("refs") or [])
                     if "subject" not in r and r.get("retention") == "fully_preserved"
                     and i in (r.get("shots") or [])]
        for k, seg in enumerate(segs[1:] if len(segs) > 2 else [beat], 1):
            where = f"[Shot {k}]" if len(segs) > 2 else "the beat"
            # someone off the frame given an action is drawn doing it, small in the distance
            oa = re.search(r"(@\w+)[^.;@]{0,30}?\b(run\w*|walk\w*|rac\w*|sprint\w*|flee\w*|climb\w*|driv\w*)\b"
                           r"[^.;@]{0,60}?\boff (?:the )?frame", seg, re.I)
            if oa:
                lint.append(f"shot {i}: offscreen-action: {where} gives {oa.group(1)}, off the frame, an action "
                            f"(\"{oa.group(2)}\"): the person is drawn doing it, often small in the distance. Off "
                            f"the frame, name a person only as the eyes' target; their action is a sound.")
            # "the empty seat" draws the seat, and with a prop's picture on the hop, the prop on it
            em = re.search(r"\bempty (seat|bench|chair|table|hands?|palm|shelf|desk|hook|tray|case|box|pocket|"
                           r"spot|place)\b", QUOTE.sub(" ", seg), re.I)
            if em and hop_props:
                lint.append(f"shot {i}: empty-spot: {where} shows \"{em.group(0)}\" on a hop that carries the "
                            f"picture of @{', @'.join(hop_props)}. Naming the spot draws it, and the prop comes "
                            f"back on it. Show the prop leave on screen, then frame away from the spot.")
            # one person leaves by one side and is then looked for, or travels, on the other;
            # the exit belongs to the last person tagged before it in the shot
            for em_ in re.finditer(r"\bout of (?:the )?frame to the (left|right)", seg, re.I):
                before = re.findall(r"@\w+", seg[:em_.start()])
                if before:
                    exits[before[-1]] = (em_.group(1).lower(), k)
            # movements play in real time: too many in a short window get squeezed or doubled
            for wm in re.finditer(r"\bAt (\d\d):(\d\d\.\d+)-(\d\d):(\d\d\.\d+),(.*?)(?=\bAt \d\d:\d\d\.\d+|$)",
                                  seg, re.I | re.S):
                dur = (int(wm.group(3)) * 60 + float(wm.group(4))) - (int(wm.group(1)) * 60 + float(wm.group(2)))
                text = QUOTE.sub(" ", wm.group(5))
                moves = {}
                for mv in STATE_MOVE.finditer(text):
                    who = re.findall(r"@\w+", text[:mv.start()])
                    if who:
                        moves[who[-1]] = moves.get(who[-1], 0) + 1
                busy = [t for t, n in moves.items() if n >= 2]
                if (len(moves) >= 2 and dur < 6.0) or (busy and dur < 4.0):
                    lint.append(f"shot {i}: move-time: {where} gives {dur:.1f} s to "
                                f"{sum(moves.values())} movement(s) by {', '.join(moves)}. Movements play in real "
                                f"time (a door and getting in ~3 s, round a car 4-5 s); squeezed, they are skipped "
                                f"or the people doubled. One travel movement per person per window, or more time.")
            for tm in re.finditer(r"(@\w+)[^.;@]{0,40}?\boff (?:the )?frame to the (left|right)", seg, re.I):
                was = exits.get(tm.group(1))
                if was and was[1] < k and was[0] != tm.group(2).lower():
                    lint.append(f"shot {i}: exit-side: {tm.group(1)} leaves the frame to the {was[0]} in "
                                f"[Shot {was[1]}] but is placed off the frame to the {tm.group(2).lower()} in "
                                f"{where}. Keep the side someone left by.")
            if AWAY.search(seg) and not BACK.search(seg):
                lint.append(f"shot {i}: back-view: {where} has a walk or run away from the camera with no \"back to "
                            f"the camera\". Say it, or it can render as a face to the lens moving backward.")
            if (re.search(r"\bfrom beside @\w+", seg, re.I)
                    and not re.search(r"\balone in the frame\b|\bnobody else\b", seg, re.I)):
                lint.append(f"shot {i}: beside-tag: {where} places the camera \"from beside\" a tagged person: "
                            f"that person can be drawn into the frame. Add \"alone in the frame ... nobody else is "
                            f"in the frame\", or place the camera by the room.")
            # a close shot whose eyeline names someone off the frame can pull that person in, head at
            # the edge of the close, when they stand near (side by side at a railing)
            elif (re.search(r"\b(?:medium close|close)(?:-up| shot| view)\b", seg, re.I)
                    and re.search(r"@\w+[^.;]{0,40}?\boff (?:the )?frame", seg, re.I)
                    and not re.search(r"\balone in the frame\b|\bnobody else\b", seg, re.I)):
                lint.append(f"shot {i}: pull-in: {where} is a close shot naming a tagged person off the frame: "
                            f"that person can be drawn into the close. Add \"alone in the frame ... nobody else is "
                            f"in the frame\".")
            # a face turned to the camera with nothing to look at looks into the lens
            # ("his back to the camera" turns the face away, so it does not count)
            if (re.search(r"\b(?:facing|toward|towards|to) (?:the )?camera\b",
                          re.sub(r"\bbacks? to (?:the )?camera\b", "", seg, flags=re.I), re.I)
                    and not re.search(r"\b(?:eyes|gaze|looks?|looking|glanc\w*|watch\w*|stares?|staring)\b", seg, re.I)):
                lint.append(f"shot {i}: no-eye-target: {where} turns a face to the camera but gives the eyes "
                            f"nothing to look at; a face with no target looks into the lens. Name what each face "
                            f"looks at, off the lens.")
            # naming an absence adds the thing: "silent" and "without a sound" invite a voice
            narr = QUOTE.sub(" ", seg)
            ab = re.search(r"\b(silent(?:ly)?|silence|without (?:a )?(?:sound|word)|no sound|soundless(?:ly)?|"
                           r"says nothing|stops talking|in the quiet)\b", narr, re.I)
            if ab:
                lint.append(f"shot {i}: absence: {where} says \"{ab.group(0)}\". Naming an absence adds the "
                            f"thing; write the mouth state and the sound that is there instead.")
            # an ensemble, not a soloist: a timed window in a shot with several people that gives
            # only one of them anything to do plays one action while the frame waits
            # people in frame only: a tag named as an eyeline target off the frame, or as the camera's
            # place ("from beside @b"), is not in the shot
            in_shot = {t for pos, t in tags_in(seg, people)
                       if not re.search(r"off (?:the )?frame", seg[pos:pos + 70], re.I)
                       and not re.search(r"from beside\s*$", seg[max(0, pos - 15):pos], re.I)}
            if len(in_shot) >= 2 and not re.search(r"\balone in the frame\b", seg, re.I):
                for wm in re.finditer(r"\bAt \d\d:\d\d\.\d+-\d\d:\d\d\.\d+,(.*?)(?=\bAt \d\d:\d\d\.\d+|$)", seg,
                                      re.I | re.S):
                    win = QUOTE.sub(" ", wm.group(1))
                    who = {t for _, t in tags_in(win, people)}
                    if len(who) <= 1 and not re.search(r"\b(all|both|together|everyone|the (?:two|three|four|twins|pair)|"
                                                        r"they|each)\b", win, re.I):
                        lint.append(f"shot {i}: solo-window: {where} has {len(in_shot)} people but the window "
                                    f"\"{wm.group(0)[:40].strip()}...\" gives only one of them an action. Say what "
                                    f"everyone in frame does at once, and what the place does.")
                        break
            # control the mouths, never the bodies: a frozen frame plays like a slideshow
            fz = re.search(r"\bnobody moves\b|\b(?:both|all|the (?:two|three|four)) (?:of them )?hold still\b|"
                           r"\b(?:holds?|stays?|stand|stands|sit|sits) (?:perfectly )?still\b", narr, re.I)
            if fz:
                lint.append(f"shot {i}: frozen: {where} says \"{fz.group(0)}\". Only the mouth needs control; give "
                            f"everyone in frame business of their own, let the place move, and keep a true hold "
                            f"for one deliberate beat.")
            if PHONE_EAR.search(seg) and not QUOTE.search(seg):
                lint.append(f"shot {i}: phone: {where} puts a phone at an ear with no line. Give the call a line and "
                            f"an end, or keep the receiver down.")
    # Without a map this is a hint: a long description pasted into 3+ hops is usually a prop.
    # With a map, the map's own props list is checked instead (prop-picture).
    seen = {}
    for i, s in enumerate(shots, 1) if not a.map else []:
        words = re.findall(r"[@\w'-]+", (s.get("beat") or "").lower())
        for j in range(len(words) - 9):
            gram = words[j:j + 10]
            tagged = any(w.startswith("@") for w in words[max(0, j - 2):j])  # "@card, the black card ..."
            # eyelines, camera lines, sounds and places repeat on purpose; only objects count
            if gram[0] == "the" and not tagged and not any(w.startswith("@") or w in NOT_PROP for w in gram):
                seen.setdefault(" ".join(gram), set()).add(i)
    flagged = []
    for gram, hops in sorted(seen.items(), key=lambda kv: (-len(kv[1]), min(kv[1]))):
        if len(hops) >= 3 and not any(len(set(gram.split()) & set(f.split())) >= 6 for f in flagged):
            flagged.append(gram)
            lint.append(f"prop-words: \"{gram} ...\" repeats in hops {sorted(hops)} with no tag. A recurring prop "
                        f"held by words is redrawn each time; give it a picture, a tag and a row (ignore if it is "
                        f"a place or a pose).")
            if len(flagged) >= 3:
                break

    # --- lints that read the scene map ---
    if a.map:
        smap = json.loads(Path(a.map).read_text(encoding="utf-8"))
        sched = {}
        for r in all_refs:
            for h in r.get("shots") or []:
                sched.setdefault(int(h), set()).add(r["tag"])
        for sc in smap.get("scenes") or []:
            hops, place, goal = sc.get("hops") or [], sc.get("place"), sc.get("goal")
            for h in hops:
                if not 1 <= h <= len(shots):
                    continue
                beat = shots[h - 1].get("beat") or ""
                segs = re.split(r"\[Shot\s+\d+\]", beat, flags=re.I)
                for k, seg in enumerate(segs[1:] if len(segs) > 2 else [beat], 1):
                    other = [t for _, t in tags_in(seg, plates) if t != place]
                    if other:
                        continue  # the shot names a different view; the goal map is for `place`
                    if goal == "far" and TOWARD_CAM.search(seg):
                        lint.append(f"shot {h}: goal-behind: [Shot {k}] runs or walks toward the camera, but in "
                                    f"@{place}'s view the goal ({sc.get('goal_is', 'the destination')}) is far ahead. "
                                    f"The plate puts it behind her. Shoot from behind, side-on, or give the front "
                                    f"view its own plate.")
                    if goal == "near" and AWAY.search(seg):
                        lint.append(f"shot {h}: goal-behind: [Shot {k}] travels away from the camera, but the goal "
                                    f"lies behind the camera in @{place}'s view.")
            # a continuation remembers everyone in the room from the hop before; a person left off
            # it is rebuilt with no picture and lands on the nearest look-alike. A restart starts
            # fresh, so only continuations are checked.
            for who in sc.get("cast") or []:
                for h in hops:
                    if not 1 <= h <= len(shots) or h == 1 or shots[h - 1].get("anchor") == "restart":
                        continue
                    on = {t for r in all_refs if r.get("subject") and h in (r.get("shots") or [])
                          for t in [r["tag"]] if same_base(t, who)}
                    if 1 <= h <= len(shots) and not on:
                        lint.append(f"shot {h}: cast-missing: {who} is in this scene (the map's cast) but no row of "
                                    f"theirs rides hop {h}. Put the row on the hop and place them in the shots "
                                    f"they would be seen in, or show them leaving in an earlier hop (restarts are exempt).")
            for view, sides in (sc.get("sides") or {}).items():
                for h in hops:
                    if not 1 <= h <= len(shots):
                        continue
                    beat = shots[h - 1].get("beat") or ""
                    for seg in re.split(r"\[Shot\s+\d+\]", beat, flags=re.I):
                        if f"@{view}".lower() not in seg.lower() and not (view == place and not tags_in(seg, plates)):
                            continue
                        for m in re.finditer(r"@(\w+)(?:\s+[\w']+){0,3}?\s+on the (left|right)\b", seg, re.I):
                            tag, side = m.group(1), m.group(2).lower()
                            wrong = "right" if side == "left" else "left"
                            if any(same_base(tag, n) for n in sides.get(wrong) or []):
                                lint.append(f"shot {h}: sides: @{tag} is put on the {side}, but the map puts them on "
                                            f"the {wrong} of @{view}'s view.")
        for name, pr in (smap.get("props") or {}).items():
            hops = sorted({int(x) for x in pr.get("hops") or []})
            pic = pr.get("picture")
            if len(hops) >= 2 and not pic:
                lint.append(f"prop-picture: the {name} appears in hops {hops} with no picture. Words alone redraw "
                            f"it in every appearance; make one (the object alone on plain grey), tag it, give it a row.")
            if pic:
                miss = [h for h in hops if pic not in sched.get(h, set())]
                if miss:
                    lint.append(f"prop-picture: @{pic}'s row does not ride hops {miss}, where the {name} appears.")
            for h, who in (pr.get("holder") or {}).items():
                h = int(h)
                if 1 <= h <= len(shots) and not any(same_base(t, who) for _, t in
                                                    tags_in(shots[h - 1].get("beat") or "", people)):
                    lint.append(f"prop-holder: the map says {who} holds the {name} on hop {h}, but {who} is not in "
                                f"that hop's beat.")

    pushes = [i for i, s in enumerate(shots, 1) if re.search(r"\bpush(?:es)?\s+(?:\w+ly\s+)?in\b", s.get("beat") or "", re.I)]
    if len(pushes) > max(1, len(shots) // 4):
        lint.append(f"push-in: shots {pushes} all push in. Ration it (one per scene); use arcs, tracks, rises, holds.")
    print(f"lints {len(lint)}")
    for x in lint:
        print("  L", x)

    print("\n== review by reading (not machine-checkable)")
    multi = [i for i, s in enumerate(shots, 1)
             if len({t for _, t in tags_in(s.get("beat") or "", people)}) >= 2]
    conts = [i + 1 for i in range(1, len(shots)) if shots[i].get("anchor") != "restart"
             and (shots[i].get("directives") or {}).get("join") != "hard_cut"]
    if multi:
        print(f"  shots {multi}: is it clear who raps/sings, and does everyone else have an action?")
    if conts:
        print(f"  shots {conts}: does the first sentence MOVE from the previous shot's last pose?")
    print("  every plate: is it shot from the same camera angle the beat asks for?")
    if not ran:
        sys.exit(2)


if __name__ == "__main__":
    main()
