"""Advisory notes on a finished STANDARD block, read as a film.

`standard.contract_errors` decides whether a block is well-formed, and only its
errors go back to the model. These notes are the other half: what the block
will probably do on screen. They are shown to the person and never retried,
for the reason `planner.validate` gives -- a model asked to fix a note it
disagrees with rewrites the parts that were fine.

Checks:
  line-ledger  a line the brief quotes is missing, said twice, changed, or only
               described instead of spoken
  speech-share a timed window whose line is far shorter than the window (the
               rest fills with words nobody wrote) or longer than it
  silent-face  in a clip with lines, a window where someone is on screen with no
               line and no mouth state: empty time on a face fills with talk
  gap          a window with no line and no sound, and no sound bed to cover it

No density note: single generations follow the vendored minimax-h3 skill, not
HTC's chain word table (user, 2026-10-26).

`issues` never raises; a failing check is logged once and the rest still run.
No ComfyUI imports.
"""
from __future__ import annotations

import re

from . import blockmodel as _bm
from . import hand_tie as _ht
from . import planner as _pl

TAG = "HandTieClips"
SHORT_SHARE = _pl.SPEECH_MIN_SHARE    # a line filling under half its window
MIN_WINDOW_S = 2.5                    # shorter windows are a line and a breath
ALTERED_OVERLAP = 0.6                 # word overlap that reads as the same line, changed

_DOUBLE = re.compile("[\"“”]([^\"“”]{2,}?)[\"“”]")
_CURLY_SINGLE = re.compile("‘([^‘’]{2,}?)’")
_WORD = re.compile(r"[a-z0-9']+")
_MOUTH = re.compile(r"\b(lips?|mouth|jaw|silent|closed|pressed|smil\w*|grin\w*|frown\w*|purs\w*|"
                    r"swallow\w*|chew\w*|bit(?:es|ing) (?:his|her) lip)\b", re.I)
_PERSON = re.compile(r"<Subject \d+>|\b(?:he|she|his|her|the (?:man|woman|boy|girl))\b", re.I)
_NO_BED = re.compile(r"^\s*(?:n/?a|none|silence)?\s*\.?\s*$", re.I)


def _norm(text):
    return " ".join(_WORD.findall(str(text or "").lower().replace("’", "'")))


def brief_lines(brief):
    """The lines a brief quotes, in order: double quotes (straight or curly),
    curly single quotes, and straight single quotes by the pack's own rule
    (an apostrophe inside a word is not a quote)."""
    t = str(brief or "")
    found = [(m.start(), m.group(1)) for m in _DOUBLE.finditer(t)]
    found += [(m.start(), m.group(1)) for m in _CURLY_SINGLE.finditer(t)]
    found += [(a, t[a + 1:b]) for a, b in _ht.quote_spans(t)]
    out, seen = [], set()
    for _pos, said in sorted(found):
        n = _norm(said)
        if n and n not in seen:
            seen.add(n)
            out.append(said.strip())
    return out


def _head(line, n=4):
    w = line.split()
    return " ".join(w[:n]) + (" ..." if len(w) > n else "")


def _ledger(blk, brief):
    said = [_norm(l) for s in blk.shots for b in s.beats for l in b.lines]
    said += [_norm(l) for s in blk.shots for l in _bm._lines(s.view)]
    whole = _norm(" ".join(blk.fields.values()))
    out = []
    for line in brief_lines(brief):
        n = _norm(line)
        hits = sum(1 for s in said if n in s)
        if hits == 1:
            continue
        if hits > 1:
            out.append(f"line-ledger: the line \"{_head(line)}\" is spoken {hits} times; the brief has it once.")
            continue
        want = set(n.split())
        best = max((len(want & set(s.split())) / len(want) for s in said), default=0.0)
        if best >= ALTERED_OVERLAP:
            out.append(f"line-ledger: the line \"{_head(line)}\" is spoken with different words than the brief's.")
        elif n in whole:
            out.append(f"line-ledger: the line \"{_head(line)}\" is described but never spoken; "
                       f"H3 says only what is written as a <d> line.")
        else:
            out.append(f"line-ledger: the line \"{_head(line)}\" from the brief is not in the block.")
    return out


def _windows(blk):
    for s in blk.shots:
        for b in s.beats:
            yield s, b


def _when(s, b):
    return f"shot {s.n}, {b.a:.1f}-{b.b:.1f} s"


def _speech_share(blk):
    out = []
    for s, b in _windows(blk):
        if not b.lines:
            continue
        win = b.b - b.a
        talk = _pl.speech_seconds(" ".join(b.lines))
        if win >= MIN_WINDOW_S and talk < win * SHORT_SHARE:
            out.append(f"speech-share: {_when(s, b)}: the line takes about {talk:.1f} s of a "
                       f"{win:.1f} s window; the rest of a speaking window tends to fill with "
                       f"words nobody wrote. Give the line its own shorter window.")
        elif win > 0 and talk > win:
            out.append(f"speech-share: {_when(s, b)}: the line takes about {talk:.1f} s in a "
                       f"{win:.1f} s window; it gets rushed or cut.")
    return out


def _silent_face(blk):
    if not any(b.lines for _s, b in _windows(blk)):
        return []
    out = []
    for s, b in _windows(blk):
        if b.lines or not _PERSON.search(b.text) or _MOUTH.search(b.text):
            continue
        out.append(f"silent-face: {_when(s, b)}: someone is on screen with no line and no mouth "
                   f"state; in a clip with lines, a face with nothing to say tends to talk.")
    return out


def _gap(blk):
    bed = blk.fields.get("overall_soundscape:", "")
    if bed and not _NO_BED.match(bed):
        return []
    out = []
    for s, b in _windows(blk):
        if not b.lines and not _pl._SOUND.search(b.text):
            out.append(f"gap: {_when(s, b)} has no line and no sound, and the soundscape names none; "
                       f"H3 fills an unnamed silence itself.")
    return out


_CHECKS = (("line-ledger", lambda blk, brief: _ledger(blk, brief)),
           ("speech-share", lambda blk, brief: _speech_share(blk)),
           ("silent-face", lambda blk, brief: _silent_face(blk)),
           ("gap", lambda blk, brief: _gap(blk)))
_LOGGED = set()


def issues(block, *, brief="", names=()):
    """Advisory notes for a finished block, deduplicated, in check order."""
    try:
        blk = _bm.parse(block, names)
    except Exception as exc:  # noqa: BLE001 -- a note must never break a write
        _log_once("parse", exc)
        return []
    out = []
    for name, fn in _CHECKS:
        try:
            for msg in fn(blk, brief):
                if msg not in out:
                    out.append(msg)
        except Exception as exc:  # noqa: BLE001
            _log_once(name, exc)
    return out


def _log_once(name, exc):
    if name not in _LOGGED:
        _LOGGED.add(name)
        print(f"[{TAG}] STANDARD note check {name} failed and was skipped: {exc!r}", flush=True)
