"""Dialogue lock: freeze a hop's spoken lines in H3's audio latent, leave the rest live.

No ComfyUI imports; the VAE encode, splice and draft render live in
h3_ref_chain.py. This module is the arithmetic, so the checkers can prove it.

Two sources give the same thing per hop -- a waveform on the hop's own clock and
the spans where the scripted lines are spoken:

- **file** (`dialogue_audio_file`): one recording laid on the film's timeline,
  lines where they are spoken, digital silence between them. Each hop takes its
  window with `audio_lock.hop_audio_window_s`, exactly as `master_audio_file`
  does; the lines are found from the recording's own level.
- **draft** (file empty): H3 drafts the hop's sound on a small canvas, Whisper
  hears it with word timings, the words that match the beat's lines (quoted or `<d>`) are
  the lines, and every other word is babble, silenced and frozen silent.

Then, per hop, the audio latent is frozen (mask 0) over each line with margins,
optionally held quiet after it, and left generative (mask 1) everywhere else, so
H3 still makes the room, the footsteps and the music. After the decode the line
cores are spliced back sample for sample, so the delivered words are the source,
not the VAE's second reading of it. `full` freezes the whole hop, as a song is.

Mask polarity is ComfyUI's: 1 = denoise (generate), 0 = keep the latent image.
"""
from __future__ import annotations

import re

import torch

AUDIO_HZ = 40.0
MODES = ("off", "lines", "lines+hold", "full")

PRE_S = 0.20         # frozen before a line (breath, onset)
POST_S = 0.25        # frozen after a line (consonant tail)
HOLD_S = 1.5         # lines+hold: frozen quiet after a line, where tag-on babble starts
FEATHER_S = 0.10     # linear 0 -> 1 outside the frozen edge
BABBLE_PAD_S = (0.05, 0.10)
ENERGY_DB = -40.0    # a file's speech: 20 ms frames above this (dBFS)
FRAME_S = 0.02
MIN_GAP_S = 0.30     # gaps shorter than this join two pieces into one line
MIN_LEN_S = 0.12     # shorter bursts are clicks, not lines
WORD_GAP_S = 0.45    # matched words closer than this are one line
LOOKAHEAD = 3        # script words a heard word may skip ahead to match
XFADE_S = 0.01       # the core splice's edge
MAX_WORD_S = 0.8     # longer is Whisper stretching a word over the silence before it

_WORD = re.compile(r"[a-z0-9']+")


def normalize_mode(mode):
    m = str(mode or "off").strip().lower()
    return m if m in MODES else "off"


def _mono(wav):
    w = wav.detach().float().cpu()
    while w.dim() > 2:
        w = w[0]
    return w.mean(0) if w.dim() == 2 else w


def speech_spans(wav, sr, db=ENERGY_DB):
    """[(t0, t1)] seconds where a recording carries sound above `db` dBFS.

    For the file source, where silence between lines is digital silence.
    """
    m = _mono(wav)
    hop = max(1, int(round(FRAME_S * float(sr))))
    n = int(m.shape[-1]) // hop
    if n <= 0:
        return []
    fr = m[: n * hop].reshape(n, hop)
    rms = fr.pow(2).mean(1).sqrt().clamp_min(1e-9)
    on = (20.0 * torch.log10(rms)) > float(db)
    spans, start = [], None
    for k, v in enumerate(on.tolist()):
        if v and start is None:
            start = k
        elif not v and start is not None:
            spans.append([start * FRAME_S, k * FRAME_S])
            start = None
    if start is not None:
        spans.append([start * FRAME_S, n * FRAME_S])
    merged = []
    for a, b in spans:
        if merged and a - merged[-1][1] < MIN_GAP_S:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(round(a, 3), round(b, 3)) for a, b in merged if b - a >= MIN_LEN_S]


def _norm(w):
    return _WORD.findall(str(w or "").lower())


def script_words(block):
    """The words a hop's block asks it to say, in order, quoted or `<d>`.

    Most plans and the writer write single-quoted lines ("says, 'Hey.'"), which
    HTC sends to H3 as they are; `hand_tie.hop_words` reads `<d>` only and saw
    no line in them (the first GPU test, 10-26).
    """
    from . import planner as _planner
    return [w for _a, _b, t in _planner.dialogue_spans(block)
            for w in _norm(str(t).replace("<|cutoff|>", " "))]


def _merge(items, gap):
    out = []
    for a, b in sorted(items):
        if out and a - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(float(a), float(b)) for a, b in out]


def match_words(heard, script):
    """Split heard words into the scripted line and babble. -> (lines, babble).

    `heard` is hear.transcribe_words' [(word, t0, t1)]; `script` the beat's
    words in order (script_words). In order, with LOOKAHEAD so a word
    Whisper dropped does not strand the rest. A babble word between two line
    words of one line (a split or a filler Whisper heard) is part of the line.
    """
    want = [w for s in script or [] for w in _norm(s)]
    pos = 0
    hit, miss = [], []
    for w, t0, t1 in heard or []:
        toks = _norm(w)
        if not toks:
            continue
        t1 = max(float(t1), float(t0))
        # Whisper stretches a word over the silence beside it: a clip's first
        # word back to 0.00 (10-26: said at 1.5 s), a last word forward to the
        # clip's end (10-26: 'now.' at 1.2 s stamped to 10.1 s). Stamped from
        # 0.00 its end is real; otherwise its start is.
        if t1 - float(t0) > MAX_WORD_S:
            if float(t0) <= 0.05:
                t0 = t1 - MAX_WORD_S
            else:
                t1 = float(t0) + MAX_WORD_S
        k = next((j for j in range(pos, min(len(want), pos + LOOKAHEAD + 1))
                  if want[j] == toks[0]), None)
        if k is not None:
            hit.append((float(t0), t1))
            pos = k + len(toks)
        else:
            miss.append((float(t0), t1))
    lines = _merge(hit, WORD_GAP_S)
    babble = [s for s in miss
              if not any(a <= s[0] and s[1] <= b for a, b in lines)]
    return lines, _merge(babble, WORD_GAP_S)


def frozen_spans(lines, mode, babble=()):
    """The intervals the mask freezes, before feathering. -> [(t0, t1)]."""
    mode = normalize_mode(mode)
    post = POST_S + (HOLD_S if mode == "lines+hold" else 0.0)
    out = [(a - PRE_S, b + post) for a, b in lines or []]
    out += [(a - BABBLE_PAD_S[0], b + BABBLE_PAD_S[1]) for a, b in babble or []]
    return _merge(out, 0.0)


def mask_steps(n_steps, lines, mode, babble=(), hz=AUDIO_HZ):
    """Per audio-latent step: 0 frozen, 1 generative, feathered between.

    `full` freezes every step. A hop with no line and no babble is all 1.
    """
    mode = normalize_mode(mode)
    n = int(n_steps)
    if mode == "full":
        return torch.zeros(n)
    spans = frozen_spans(lines, mode, babble)
    t = (torch.arange(n, dtype=torch.float32) + 0.5) / float(hz)
    m = torch.ones(n)
    for a, b in spans:
        d = torch.maximum(a - t, t - b)              # <= 0 inside, distance outside
        m = torch.minimum(m, (d / FEATHER_S).clamp(0.0, 1.0))
    return m


def outside(spans, opens):
    """`spans` minus every `opens` interval. -> [(t0, t1)]

    Under hand_tie the previs windows own a hop's head and tail, picture and
    sound; a line, or a babble cut, is kept only where no window is.
    """
    out = [tuple(s) for s in spans or []]
    for o0, o1 in opens or []:
        nxt = []
        for a, b in out:
            if b <= o0 or a >= o1:
                nxt.append((a, b))
                continue
            if a < o0:
                nxt.append((a, o0))
            if b > o1:
                nxt.append((o1, b))
        out = nxt
    return [(a, b) for a, b in out if b - a > 1e-6]


def open_steps(m, opens, hz=AUDIO_HZ):
    """The steps mask with every `opens` interval forced generative (1),
    feathered inward over FEATHER_S so a line's frozen edge never meets a
    window as a step."""
    m = m.clone()
    t = (torch.arange(int(m.shape[0]), dtype=torch.float32) + 0.5) / float(hz)
    for a, b in opens or []:
        d = torch.maximum(a - t, t - b)          # <= 0 inside the window
        m = torch.maximum(m, (1.0 - d / FEATHER_S).clamp(0.0, 1.0))
    return m


def silence(wav, sr, spans, fade_s=XFADE_S):
    """A copy with each span zeroed, faded in and out over `fade_s`."""
    out = wav.clone()
    n = int(out.shape[-1])
    f = max(1, int(round(fade_s * float(sr))))
    for a, b in spans or []:
        s0 = max(0, int(round(a * sr)))
        s1 = min(n, int(round(b * sr)))
        if s1 <= s0:
            continue
        g = torch.zeros(s1 - s0, dtype=out.dtype)
        k = min(f, (s1 - s0) // 2)
        if k:
            g[:k] = torch.linspace(1.0, 0.0, k, dtype=out.dtype)
            g[-k:] = torch.linspace(0.0, 1.0, k, dtype=out.dtype)
        out[..., s0:s1] = out[..., s0:s1] * g
    return out


def splice_cores(hop_wav, src_wav, cores, sr, xfade_s=XFADE_S):
    """`hop_wav` with each core replaced by `src_wav`, crossfaded at the edges.

    Both on the hop's own clock and sample rate; `src_wav` is padded or cut to
    `hop_wav`'s length. Outside the cores `hop_wav` is untouched.
    """
    out = hop_wav.clone()
    n = int(out.shape[-1])
    src = src_wav.to(dtype=out.dtype)
    while src.dim() < out.dim():
        src = src.unsqueeze(0)
    if int(src.shape[-1]) < n:
        src = torch.nn.functional.pad(src, (0, n - int(src.shape[-1])))
    src = src[..., :n]
    if int(src.shape[-2]) != int(out.shape[-2]):
        src = src.mean(-2, keepdim=True).expand_as(out)
    f = max(1, int(round(xfade_s * float(sr))))
    for a, b in cores or []:
        s0 = max(0, int(round(a * sr)))
        s1 = min(n, int(round(b * sr)))
        if s1 <= s0:
            continue
        w = torch.ones(s1 - s0, dtype=out.dtype)
        k = min(f, (s1 - s0) // 2)
        if k:
            w[:k] = torch.linspace(0.0, 1.0, k, dtype=out.dtype)
            w[-k:] = torch.linspace(1.0, 0.0, k, dtype=out.dtype)
        out[..., s0:s1] = out[..., s0:s1] * (1 - w) + src[..., s0:s1] * w
    return out


def hop_local(spans, t0, t1):
    """Film-clock spans clipped to [t0, t1) and moved onto the hop's clock."""
    out = []
    for a, b in spans or []:
        a2, b2 = max(a, t0), min(b, t1)
        if b2 > a2:
            out.append((round(a2 - t0, 4), round(b2 - t0, 4)))
    return out


def describe(lines, babble, mode):
    def f(sp):
        return ", ".join(f"{a:.2f}-{b:.2f}s" for a, b in sp) or "none"
    return f"{normalize_mode(mode)}: lines {f(lines)}; babble silenced {f(babble)}"
