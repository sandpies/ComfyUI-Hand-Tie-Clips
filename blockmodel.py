"""Read a finished standard H3 prompt block: fields -> shots -> beats -> lines.

The STANDARD writer checks a block's structure (`standard.contract_errors`);
this is what lets a check read it as a film instead: who speaks in which
window, what each window holds, what the soundscape names. It is permissive on
purpose. A block the contract would refuse still parses as far as it goes, and
deciding what is wrong is the checks' job, never the reader's.

No ComfyUI imports: the checker runs it on the CPU.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as _dc_field

from . import planner as _pl

DESCRIPTION_FIELDS = ("detailed_description:", "integrated_multimodal_description:")

_SHOT = re.compile(r"\[Shot (\d+)\]\s*(?:At (\d+):(\d+(?:\.\d+)?),?)?", re.I)
_WINDOW = re.compile(r"\bAt (\d+):(\d+(?:\.\d+)?)\s*-\s*(\d+):(\d+(?:\.\d+)?),?", re.I)


@dataclass
class Beat:
    a: float
    b: float
    text: str                     # the window's words with its spoken lines taken out
    lines: list                   # the spoken lines, in order, markup stripped


@dataclass
class Shot:
    n: int
    at: float | None              # the cut time; None on [Shot 1]
    view: str                     # what the shot says before its first timed window
    beats: list = _dc_field(default_factory=list)


@dataclass
class Block:
    fields: dict                  # field name -> body, in the order they appear
    shots: list

    def description(self):
        for name in DESCRIPTION_FIELDS:
            if name in self.fields:
                return self.fields[name]
        return ""


def field_text(text, name, names):
    """The body of field `name`: from its label to the next label in `names`.

    The one boundary rule; `standard._field` delegates here so the contract and
    the reader can never disagree on where a field ends.
    """
    i = text.find(name)
    if i < 0:
        return ""
    j = len(text)
    for f in set(names):
        k = text.find(f, i + len(name))
        if k > -1:
            j = min(j, k)
    return text[i + len(name):j]


def _secs(mm, ss):
    return int(mm) * 60 + float(ss)


def _lines(text):
    return [said.strip() for _a, _b, said in _pl.dialogue_spans(text) if said.strip()]


def _strip_lines(text):
    out, last = [], 0
    for a, b, _w in _pl.dialogue_spans(text):
        out.append(text[last:a])
        last = b
    out.append(text[last:])
    return " ".join("".join(out).split())


def parse(text, names):
    """`text` as a Block. `names` is every field label the writer may use."""
    t = str(text or "")
    found = sorted((t.find(n), n) for n in set(names) if t.find(n) > -1)
    fields = {n: field_text(t, n, names).strip() for _i, n in found}
    blk = Block(fields=fields, shots=[])
    body = blk.description()
    marks = list(_SHOT.finditer(body))
    for k, m in enumerate(marks):
        seg = body[m.end():marks[k + 1].start() if k + 1 < len(marks) else len(body)]
        at = _secs(m.group(2), m.group(3)) if m.group(2) else None
        wins = list(_WINDOW.finditer(seg))
        shot = Shot(n=int(m.group(1)), at=at,
                    view=_strip_lines(seg[:wins[0].start()] if wins else seg))
        for w, wm in enumerate(wins):
            words = seg[wm.end():wins[w + 1].start() if w + 1 < len(wins) else len(seg)]
            shot.beats.append(Beat(a=_secs(wm.group(1), wm.group(2)),
                                   b=_secs(wm.group(3), wm.group(4)),
                                   text=_strip_lines(words), lines=_lines(words)))
        blk.shots.append(shot)
    return blk
