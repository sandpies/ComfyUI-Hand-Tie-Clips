"""H3 Token LoRA: a LoRA loader that applies LoRAs per kind of token.

MiniMax H3 is one stream: text, reference pictures, video and audio rows all go
through the same 50 blocks. A normal loader changes the weights for every row.
This loader leaves the weights alone and adds each LoRA's low-rank term only on
the rows of the kinds you give a strength to:

    y[rows] = W x[rows] + s_kind * scale * B (A x[rows])

on the four block layers H3 LoRAs train (attn.qkv_proj, attn.out_proj,
mlp.fc1, mlp.fc2). Strength 0 for a kind = those rows run the plain model.
Rows of another kind still attend to the changed rows, so a video-only LoRA
can colour the sound a little through attention; it cannot act on the audio
rows directly.

One node holds several LoRAs: slots A, B, C in the widgets and any number more
behind "Add LoRA" (kept as JSON in `extra_loras`, letters D, E, ...). Each slot
has its own strengths, block range and refiner strength; a slot can be switched
off without losing its settings (`disabled_loras`). Two nodes in a row stack as
well: they share one hook set, so every LoRA sees the others' fc1 terms before
its fc2 term, as a weight merge would.

How the rows are found on every model call:
  * the packed layout (the same PackedLayout the model builds) gives each
    row's kind;
  * qkv_proj, out_proj and fc1 are module calls, so forward hooks see them.
    A layer may be called in slices: KJNodes' Chunk FeedForward calls fc1 once
    per chunk, ComfyUI's sparse attention calls qkv_proj in 4096-row slices,
    in order, or (vsa mode) in its padded tile order. Each hooked layer keeps a
    row cursor per model call, so every slice is matched to its own rows;
  * fc2 runs inside linear_input_act (no module call). Its term is computed per
    fc1 slice down to rank width only (rows x rank), then added onto the MLP's
    output, so chunked feed-forward keeps its memory saving.

add_mode: `bf16` adds the term in the GEMM epilogue (one rounding, as a runtime
LoRA does); `fp32_stochastic` adds in fp32 and rounds to bf16 with an unbiased
random tie-break, so a term far below bf16 resolution survives on average (closer
to an fp32 weight merge), at some speed cost.
"""
from __future__ import annotations

import hashlib
import json
import re
import weakref

import torch
import torch.nn.functional as F

TAG = "HTCTokenLoRA"
TARGETS = ("attn.qkv_proj", "attn.out_proj", "mlp.fc1", "mlp.fc2")
# PackedLayout segment kind -> the strength that covers it
KIND_GROUP = {"text": "text", "video": "video",
              "cond": "ref", "ref_img": "ref",
              "audio": "audio", "cond_audio": "audio", "ref_audio": "audio"}
NONE = "None"
# append only: saved graphs store the string
OTHER_KEYS = ("skip", "A to all tokens", "B to all tokens", "A+B to all tokens",
              "C to all tokens", "A+B+C to all tokens")
_OTHER_LETTERS = ("", "A", "B", "AB", "C", "ABC")
ADD_MODES = ("bf16", "fp32_stochastic")
_OPT_KEY = "htc_token_lora"
N_BLOCKS = 50

# an "Add LoRA" slot record (letters D, E, ...); the JS writes the same keys
EXTRA_DEFAULTS = {"lora_name": NONE, "video": 1.0, "audio": 0.0, "reference": -1.0,
                  "text": 0.0, "refiner": 0.0, "block_start": 0, "block_end": N_BLOCKS - 1,
                  "all_tokens": False}
_EXTRA_FLOATS = ("video", "audio", "reference", "text", "refiner")

# --- parsing -----------------------------------------------------------------

_PREFIXES = ("model.diffusion_model.", "diffusion_model.", "base_model.model.",
             "transformer.", "unet.")
_KOHYA = re.compile(r"^lora_unet_blocks_(\d+)_(attn_qkv_proj|attn_out_proj|mlp_fc1|mlp_fc2)\.(.+)$")
_BLOCK = re.compile(r"^diffusion_model\.blocks\.(\d+)\.(attn\.qkv_proj|attn\.out_proj|mlp\.fc1|mlp\.fc2)\.(.+)$")
_ROLE = {"lora_A.weight": "A", "lora_down.weight": "A", "lora.down.weight": "A",
         "lora_A.default.weight": "A",
         "lora_B.weight": "B", "lora_up.weight": "B", "lora.up.weight": "B",
         "lora_B.default.weight": "B", "alpha": "alpha"}


def canonical(key):
    m = _KOHYA.match(key)
    if m:
        tgt = m.group(2).replace("_", ".", 1)
        return f"diffusion_model.blocks.{m.group(1)}.{tgt}.{m.group(3)}"
    for p in _PREFIXES:
        if key.startswith(p):
            return "diffusion_model." + key[len(p):]
    return key


def parse(sd, dtype=torch.bfloat16):
    """-> (blocks {(i, target): (A, B, scale)}, refiner {key: t}, other {key: t})."""
    groups, rest = {}, {}
    for k, v in sd.items():
        c = canonical(k)
        m = _BLOCK.match(c)
        role = _ROLE.get(m.group(3)) if m else None
        if role is None:
            rest[c] = v
            continue
        groups.setdefault((int(m.group(1)), m.group(2)), {})[role] = (c, v)
    blocks = {}
    for key, g in groups.items():
        a, b = g.get("A"), g.get("B")
        if a is None or b is None or a[1].ndim != 2 or b[1].ndim != 2 or b[1].shape[1] != a[1].shape[0]:
            rest.update({kk: vv for kk, vv in g.values()})
            continue
        rank = int(a[1].shape[0])
        alpha = g.get("alpha")
        scale = float(alpha[1]) / rank if alpha is not None else 1.0
        blocks[key] = (a[1].to(dtype).contiguous(), b[1].to(dtype).contiguous(), scale)
    refiner = {k: v for k, v in rest.items() if k.startswith("diffusion_model.token_refiner.")}
    other = {k: v for k, v in rest.items() if k not in refiner}
    return blocks, refiner, other


def spans_for(segments, strengths):
    """[(start, stop, kind)] -> merged [(start, stop, s)] with s != 0."""
    out = []
    for a, b, kind in segments:
        s = float(strengths.get(KIND_GROUP.get(kind, ""), 0.0))
        if out and out[-1][1] == a and out[-1][2] == s:
            out[-1] = (out[-1][0], b, s)
        else:
            out.append((a, b, s))
    return [sp for sp in out if sp[2] != 0.0]


def _swiglu(x):
    import comfy.ops
    return comfy.ops.INPUT_ACT_EAGER["swiglu"](x)


# --- slots ---------------------------------------------------------------------

def slot_letter(index):
    """0 -> A, 25 -> Z, 26 -> AA."""
    s, n = "", index + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def parse_extra(text, available):
    """`extra_loras` JSON -> [(letter, record)] with every field checked."""
    try:
        records = json.loads(text or "[]")
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"{TAG}: extra_loras is not a JSON list of LoRA slots") from e
    if not isinstance(records, list):
        raise ValueError(f"{TAG}: extra_loras is not a JSON list of LoRA slots")
    out = []
    for i, rec in enumerate(records):
        L = slot_letter(i + 3)
        if not isinstance(rec, dict) or set(rec) - set(EXTRA_DEFAULTS):
            raise ValueError(f"{TAG}: LoRA {L}: unknown slot fields {sorted(set(rec) - set(EXTRA_DEFAULTS)) if isinstance(rec, dict) else rec}")
        slot = dict(EXTRA_DEFAULTS, **rec)
        name = slot["lora_name"]
        if not isinstance(name, str) or (name != NONE and name not in available):
            raise ValueError(f"{TAG}: LoRA {L}: pick a file from models/loras or None")
        for f in _EXTRA_FLOATS:
            v = slot[f]
            lo = -1.0 if f == "reference" else -4.0
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= 4.0:
                raise ValueError(f"{TAG}: LoRA {L}: {f} must be a number from {lo:g} to 4")
        for f in ("block_start", "block_end"):
            v = slot[f]
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < N_BLOCKS:
                raise ValueError(f"{TAG}: LoRA {L}: {f} must be a whole number from 0 to {N_BLOCKS - 1}")
        if not isinstance(slot["all_tokens"], bool):
            raise ValueError(f"{TAG}: LoRA {L}: all_tokens must be true or false")
        out.append((L, slot))
    return out


def parse_disabled(text, letters):
    """`disabled_loras` JSON -> set of slot letters, each one an existing slot."""
    try:
        d = json.loads(text or "[]")
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"{TAG}: disabled_loras is not a JSON list of slot letters") from e
    if not isinstance(d, list) or any(not isinstance(x, str) or x not in letters for x in d):
        raise ValueError(f"{TAG}: disabled_loras names a slot that does not exist ({d})")
    return set(d)


def strengths_of(video, audio, reference, text):
    return {"video": float(video), "audio": float(audio),
            "ref": float(video) if float(reference) < 0 else float(reference),
            "text": float(text)}


# --- the per-call hook session ------------------------------------------------

class Spec:
    def __init__(self, name, blocks, strengths, block_range, file_id=""):
        self.name = name
        self.blocks = blocks          # {(i, target): (A, B, scale)} on CPU
        self.strengths = strengths    # {"video", "ref", "text", "audio"}
        self.block_range = block_range
        self.file_id = file_id        # size + mtime of the file, for the key

    def describe(self):
        st = ",".join(f"{k}={float(v):g}" for k, v in sorted(self.strengths.items()))
        return f"{self.name}|{self.file_id}|{self.block_range[0]}-{self.block_range[1]}|{st}"


def _round_add_(dst, delta_fn):
    """dst (bf16) <- dst + delta, summed in fp32 and rounded to bf16 with an
    unbiased random tie-break. `delta_fn(acc)` adds the term into the fp32 acc."""
    acc = dst.float()
    delta_fn(acc)
    bits = acc.view(torch.int32)
    bits.add_(torch.randint_like(bits, 0, 1 << 16))
    bits.bitwise_and_(-65536)
    dst.copy_(acc)


class Session:
    """Forward hooks for one model call. `items`: {(i, target): [(A, B, scale, spans)]}
    already on the compute device. `gather`: the sparse-attention padded-row map
    (row -> source row, -1 = pad) when qkv is fed in vsa tile order, else None.
    `stochastic`: fp32 add + stochastic rounding on bf16 outputs."""

    def __init__(self, blocks, items, seq_len, gather=None, swiglu=None, stochastic=False):
        self.blocks = blocks
        self.items = items
        self.seq_len = int(seq_len)
        self.gather = gather
        self.swiglu = swiglu or _swiglu
        self.stochastic = bool(stochastic)
        self.cursor = {}
        self.fc2_parts = {}
        self.handles = []
        self._w = {}

    # rows of this call
    def _rows(self, idx, tgt, n):
        key = (idx, tgt)
        c = self.cursor.get(key, 0)
        if c == 0 and n == self.seq_len:
            return ("slice", 0)
        if tgt == "attn.qkv_proj" and self.gather is not None:
            total = int(self.gather.numel())
            sel = self.gather[c:c + n]
            if sel.numel() != n:
                raise RuntimeError(f"{TAG}: blocks.{idx} qkv got {n} rows past the end of the "
                                   f"sparse tile order ({c}/{total})")
            self.cursor[key] = 0 if c + n >= total else c + n
            return ("gather", sel)
        if c + n > self.seq_len:
            raise RuntimeError(f"{TAG}: blocks.{idx}.{tgt} got {n} rows at row {c} of "
                               f"{self.seq_len}: another node changed how H3 feeds this layer")
        self.cursor[key] = 0 if c + n >= self.seq_len else c + n
        return ("slice", c)

    def _weights(self, spans, device):
        key = (id(spans), device)
        w = self._w.get(key)
        if w is None:
            w = torch.zeros(self.seq_len + 1, dtype=torch.float32, device=device)  # last = pad
            for a, b, s in spans:
                w[a:b] = s
            self._w[key] = w
        return w

    def _sr(self, out):
        return self.stochastic and out.dtype == torch.bfloat16

    def _addmm(self, dst, lhs, B, alpha=1.0):
        """dst += alpha * lhs @ B.t(), plain or stochastic."""
        if self._sr(dst):
            _round_add_(dst, lambda acc: acc.addmm_(lhs.float(), B.float().t(), alpha=alpha))
        else:
            dst.addmm_(lhs.to(dst.dtype), B.t(), alpha=alpha)

    def _add(self, out, x, A, B, sc, spans, rows):
        kind, at = rows
        if kind == "slice":
            n = x.shape[0]
            for a, b, s in spans:
                lo, hi = max(a, at), min(b, at + n)
                if lo < hi:
                    self._addmm(out[lo - at:hi - at], F.linear(x[lo - at:hi - at], A), B, s * sc)
            return
        sel = torch.where(at >= 0, at, torch.full_like(at, self.seq_len))
        w = self._weights(spans, x.device)[sel] * sc
        self._addmm(out, F.linear(x, A) * w.to(x.dtype).unsqueeze(1), B)

    def _hook(self, idx, tgt):
        own = self.items.get((idx, tgt), ())
        fc2 = self.items.get((idx, "mlp.fc2"), ()) if tgt == "mlp.fc1" else ()

        def hook(mod, inputs, out):
            x = inputs[0]
            if x.ndim != 2:
                raise RuntimeError(f"{TAG}: blocks.{idx}.{tgt} input {tuple(x.shape)} is not packed rows")
            rows = self._rows(idx, tgt, x.shape[0])
            for A, B, sc, spans in own:
                self._add(out, x, A, B, sc, spans, rows)
            if fc2:
                if rows[0] != "slice":
                    raise RuntimeError(f"{TAG}: blocks.{idx}.mlp.fc1 rows are not in order")
                at, n = rows[1], x.shape[0]
                parts = self.fc2_parts.setdefault(idx, [])
                for A, B, sc, spans in fc2:
                    for a, b, s in spans:
                        lo, hi = max(a, at), min(b, at + n)
                        if lo < hi:
                            h = self.swiglu(out[lo - at:hi - at])
                            parts.append((lo, F.linear(h, A).mul_(s * sc), B))
            return out
        return _nocompile(hook)

    def _mlp_hook(self, idx):
        def hook(mod, inputs, out):
            for lo, dA, B in self.fc2_parts.pop(idx, ()):
                self._addmm(out[lo:lo + dA.shape[0]], dA, B)
            return out
        return _nocompile(hook)

    def __enter__(self):
        try:
            for i in sorted({i for i, _ in self.items}):
                blk = self.blocks[i]
                for tgt in ("attn.qkv_proj", "attn.out_proj"):
                    if (i, tgt) in self.items:
                        mod = blk.get_submodule(tgt)
                        self.handles.append(mod.register_forward_hook(self._hook(i, tgt)))
                if (i, "mlp.fc1") in self.items or (i, "mlp.fc2") in self.items:
                    self.handles.append(blk.mlp.fc1.register_forward_hook(self._hook(i, "mlp.fc1")))
                if (i, "mlp.fc2") in self.items:
                    self.handles.append(blk.mlp.register_forward_hook(self._mlp_hook(i)))
        except Exception:
            self.__exit__()
            raise
        return self

    def __exit__(self, *exc):
        for h in self.handles:
            h.remove()
        self.handles = []
        self.fc2_parts.clear()
        self.cursor.clear()
        self._w.clear()
        return False


def _nocompile(fn):
    dis = getattr(getattr(torch, "compiler", None), "disable", None)
    return dis(fn) if dis is not None else fn


# --- runtime: the wrappers on the model ---------------------------------------

_RUNTIMES = weakref.WeakValueDictionary()


def _sparse_patch(transformer_options):
    """ComfyUI's sparse-attention patch object behind the attention override, if any."""
    seen, todo = set(), [transformer_options.get("optimized_attention_override")]
    while todo:
        f = todo.pop()
        if f is None or id(f) in seen:
            continue
        seen.add(id(f))
        if hasattr(f, "vsa_plan") and hasattr(f, "vsa"):
            return f
        for cell in (getattr(f, "__closure__", None) or ()):
            try:
                todo.append(cell.cell_contents)
            except ValueError:
                pass
    return None


def layout_for(dm, x, context, payload):
    """The PackedLayout the model will build for this call."""
    import comfy.ldm.minimax.model as mm
    payload = payload or {}
    v = x[0]
    pt, ph, pw = dm.patch_size
    t = v.shape[2] + (-v.shape[2]) % pt
    h = v.shape[3] + (-v.shape[3]) % ph
    w = v.shape[4] + (-v.shape[4]) % pw
    audio_t = x[1].shape[-1]
    lay = payload.get("layout")
    if lay is None or lay.signature != (context.shape[1], t, h, w, audio_t):
        lay = mm.PackedLayout(context.shape[1], t, h, w, audio_t,
                              keyframes=payload.get("keyframes"), refs=payload.get("refs"))
    return lay


class Runtime:
    """The key is derived from the content (LoRA files, strengths, blocks, add
    mode), never random, and the only public attribute: HTC's hop cache
    fingerprints the scalar settings in transformer_options and on wrapper
    owners, so a random or run-mutated public value would re-render every hop
    on every queue."""

    def __init__(self, specs, stochastic=False):
        self.specs = list(specs)
        self._stochastic = bool(stochastic)
        text = "||".join(sp.describe() for sp in self.specs) + f"||{'sr' if self._stochastic else 'bf16'}"
        self.key = f"{_OPT_KEY}_{hashlib.sha256(text.encode()).hexdigest()[:16]}"
        self._dev = {}
        self._logged = False
        _RUNTIMES[self.key] = self

    def _on(self, device, dtype):
        """Specs' tensors on the device; a tensor shared by two specs (same file,
        another block range or slot) is moved once."""
        k = (str(device), dtype)
        if k not in self._dev:
            moved = {}

            def mv(t):
                key = id(t)
                if key not in moved:
                    moved[key] = t.to(device, dtype)
                return moved[key]
            self._dev[k] = [{bk: (mv(A), mv(B), sc) for bk, (A, B, sc) in sp.blocks.items()}
                            for sp in self.specs]
        return self._dev[k]

    def outer_sample_wrapper(self, executor, *args, **kwargs):
        self._logged = False
        try:
            return executor(*args, **kwargs)
        finally:
            self._dev.clear()

    def diffusion_wrapper(self, executor, x, timestep, context, transformer_options, *args, **kwargs):
        dm = executor.class_obj
        lay = layout_for(dm, x, context, kwargs.get("minimax_payload"))
        spans = [spans_for(lay.segments, sp.strengths) for sp in self.specs]
        if not any(spans):
            return executor(x, timestep, context, transformer_options, *args, **kwargs)
        dev, dt = x[0].device, x[0].dtype
        on = self._on(dev, dt)
        items = {}
        for sp_dev, sp_spans in zip(on, spans):
            if not sp_spans:
                continue
            for bk, (A, B, sc) in sp_dev.items():
                items.setdefault(bk, []).append((A, B, sc, sp_spans))
        patch = _sparse_patch(transformer_options or {})
        gather = None
        if patch is not None and getattr(patch, "vsa", False):
            gather = patch.vsa_plan(lay, dev)["src"]
        if not self._logged:
            self._logged = True
            seg = " ".join(f"{k}:{b - a}" for a, b, k in lay.segments)
            print(f"[{TAG}] " + " || ".join(
                f"{sp.name} blocks {sp.block_range[0]}-{sp.block_range[1]} "
                + " ".join(f"{k} {v:g}" for k, v in sp.strengths.items()) for sp in self.specs)
                + f" | rows {lay.seq_len} [{seg}]"
                + (" | add fp32-stochastic" if self._stochastic else "")
                + (" | sparse vsa order" if gather is not None else ""),
                flush=True)
        with Session(dm.blocks, items, lay.seq_len, gather=gather, stochastic=self._stochastic):
            return executor(x, timestep, context, transformer_options, *args, **kwargs)


def install(model, specs, stochastic=False):
    """Clone `model` with `specs` (one Spec or a list) added to its token-LoRA
    runtime (one per model). A later node's add mode wins for the whole stack."""
    import comfy.patcher_extension as pe
    if isinstance(specs, Spec):
        specs = [specs]
    m = model.clone()
    to = m.model_options.setdefault("transformer_options", {})
    old_key = to.get(_OPT_KEY)
    old = _RUNTIMES.get(old_key) if old_key else None
    all_specs = (old.specs if old is not None else []) + list(specs)
    if old_key:
        m.remove_wrappers_with_key(pe.WrappersMP.OUTER_SAMPLE, old_key)
        m.remove_wrappers_with_key(pe.WrappersMP.DIFFUSION_MODEL, old_key)
    rt = Runtime(all_specs, stochastic=stochastic)
    m.add_wrapper_with_key(pe.WrappersMP.OUTER_SAMPLE, rt.key, rt.outer_sample_wrapper)
    m.add_wrapper_with_key(pe.WrappersMP.DIFFUSION_MODEL, rt.key, rt.diffusion_wrapper)
    to[_OPT_KEY] = rt.key
    return m, rt


def strip(model):
    """Remove this loader's wrappers from `model` (a clone the caller owns), for
    passes meant to run on the plain model (the upsample re-draws). -> count."""
    to = getattr(model, "model_options", {}).get("transformer_options", {})
    key = to.pop(_OPT_KEY, None)
    if not key or not hasattr(model, "remove_wrappers_with_key"):
        return 0
    import comfy.patcher_extension as pe
    model.remove_wrappers_with_key(pe.WrappersMP.OUTER_SAMPLE, key)
    model.remove_wrappers_with_key(pe.WrappersMP.DIFFUSION_MODEL, key)
    rt = _RUNTIMES.get(key)
    return len(rt.specs) if rt is not None else 1


# --- the node -------------------------------------------------------------------

def _check_model(model, blocks, name):
    try:
        dm = model.get_model_object("diffusion_model")
        mblocks = dm.blocks
    except Exception:
        return
    bad = []
    for (i, tgt), (A, B, _) in blocks.items():
        if i >= len(mblocks):
            bad.append(f"blocks.{i} (model has {len(mblocks)})")
            continue
        w = mblocks[i].get_submodule(tgt).weight
        if A.shape[1] != w.shape[1] or B.shape[0] != w.shape[0]:
            bad.append(f"blocks.{i}.{tgt} {B.shape[0]}x{A.shape[1]} vs {w.shape[0]}x{w.shape[1]}")
    if bad:
        raise RuntimeError(f"{TAG}: {name} does not fit this model ({len(bad)} layers), e.g. {bad[:3]}")
    for (i, tgt), (A, B, _) in blocks.items():
        for p in model.patches.get(f"diffusion_model.blocks.{i}.{tgt}.weight", []):
            ws = getattr(p[1], "weights", None)
            if (ws and torch.is_tensor(ws[0]) and tuple(ws[0].shape) == tuple(B.shape)
                    and torch.equal(ws[0].detach().to("cpu", B.dtype), B)):
                raise RuntimeError(f"{TAG}: {name} is also in a normal LoRA loader on this model; "
                                   "remove it there, or it is applied twice.")


def plan_slots(slots, loaded, other_mode=OTHER_KEYS[0], extra_all=None, disabled=()):
    """Decide what each slot does. `slots`: [(letter, file, strengths, (lo, hi), refiner)];
    `loaded`: file -> (blocks, refiner_sd, other_sd). -> (specs_in [(name, file, blocks,
    strengths, range)], patches [(sd, strength, note)], lines)."""
    extra_all = extra_all or {}
    letters = _OTHER_LETTERS[OTHER_KEYS.index(other_mode)] if other_mode in OTHER_KEYS else ""
    live = [s for s in slots if s[0] not in disabled and s[1] not in (None, "", NONE)]
    lines = [f"{s[0]} '{s[1]}': off" for s in slots if s[0] in disabled and s[1] not in (None, "", NONE)]
    patches = []
    for L, nm, _st, _rg, rf in live:
        blocks, refiner, other = loaded[nm]
        if rf != 0.0 and refiner:
            patches.append((refiner, rf, f"{L} refiner {len(refiner)} weights @ {rf:g}"))
    first = {}
    for L, nm, *_ in live:
        first.setdefault(nm, L)
    for L, nm, *_ in live:
        other = loaded[nm][2]
        if not other:
            continue
        applies = extra_all[L] if L in extra_all else (L in letters)
        if applies:
            patches.append((other, 1.0, f"{L} {len(other)} non-block weights on all tokens @ 1"))
        elif first[nm] == L:
            lines.append(f"{L} '{nm}': {len(other)} weights that cannot be split by token skipped "
                         "(timestep/AdaLN, norms, final layer); other_keys applies them to all tokens")
    # same file + same block range -> one term with summed strengths
    groups = []
    for s in live:
        for g in groups:
            if g[0][1] == s[1] and g[0][3] == s[3]:
                g.append(s)
                break
        else:
            groups.append([s])
    specs = []
    for g in groups:
        L = "+".join(s[0] for s in g)
        nm, (lo, hi) = g[0][1], g[0][3]
        blocks = {k: v for k, v in loaded[nm][0].items() if lo <= k[0] <= hi}
        st = {k: float(sum(s[2][k] for s in g)) for k in g[0][2]}
        head = f"{L} '{nm}' blocks {lo}-{hi} " + " ".join(f"{k} {v:g}" for k, v in st.items())
        if not blocks or all(v == 0.0 for v in st.values()):
            lines.append(head + ": nothing to apply in these blocks")
            continue
        specs.append((f"{L} {nm}", nm, blocks, st, (lo, hi)))
        lines.append(head + f" ({len(blocks)} layers)" + (" shared file" if first[nm] != g[0][0] else ""))
    return specs, patches, lines


class HTCTokenLoRA:
    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths
        loras = folder_paths.get_filename_list("loras")
        step = {"step": 0.01}

        def fl(d, tip, lo=-4.0):
            return ("FLOAT", {"default": d, "min": lo, "max": 4.0, **step, "tooltip": tip})

        def blk(d, tip):
            return ("INT", {"default": d, "min": 0, "max": N_BLOCKS - 1, "tooltip": tip})

        def slot(L, file_tip, video, audio, ref, text, refiner, ref_tip_extra=""):
            p = L.lower()
            return {
                f"lora_{p}": ([NONE] + loras if L != "A" else loras, {"tooltip": file_tip}),
                f"{p}_video": fl(video, f"LoRA {L} on the video being made. 1 = as a normal loader, 0 = off."),
                f"{p}_audio": fl(audio, f"LoRA {L} on the soundtrack. 0 = the sound is made by the plain model: "
                                        "use it for a look or style LoRA that changes voices or adds noise."),
                f"{p}_reference": fl(ref, f"LoRA {L} on the reference pictures, reference clips and pinned frames "
                                          f"(the join between hops). -1 = same as {p}_video. 0 keeps the "
                                          "references read by the plain model, which can hold identity closer.", -1.0),
                f"{p}_text": fl(text, f"LoRA {L} on the prompt's rows inside the 50 blocks" + ref_tip_extra + "."),
                f"{p}_refiner": fl(refiner, f"LoRA {L}'s text refiner part (if it has one), applied as a normal "
                                            "weight patch at this strength. 0 = left out."),
                f"{p}_block_start": blk(0, f"First of H3's 50 blocks LoRA {L} is used in (0-{N_BLOCKS - 1})."),
                f"{p}_block_end": blk(N_BLOCKS - 1, f"Last block LoRA {L} is used in."),
            }
        req = {"model": ("MODEL", {"tooltip": "An H3 model. Chain several of these nodes to stack more."})}
        req.update(slot("A", "LoRA A, usually the video LoRA.", 1.0, 0.0, -1.0, 1.0, 1.0))
        req.update(slot("B", "LoRA B, usually the audio LoRA. None = A only.", 0.0, 1.0, 0.0, 0.0, 0.0,
                        " (adds to A's text on the same rows)"))
        req["other_keys"] = (list(OTHER_KEYS), {"default": OTHER_KEYS[0], "tooltip": (
            "Parts of a LoRA that cannot be split by token (timestep / AdaLN, norms, final layer, "
            "patch embeddings). skip leaves them out (the console says how many); the other modes "
            "apply that slot's parts everywhere as a normal patch at 1.0.")})
        req["add_mode"] = (list(ADD_MODES), {"default": ADD_MODES[0], "tooltip": (
            "bf16: plain add, as a runtime LoRA. fp32_stochastic: adds in fp32 and rounds with an "
            "unbiased tie-break, closer to an fp32 weight merge for tiny terms; a bit slower.")})
        opt = slot("C", "LoRA C, e.g. a look or style LoRA kept off the soundtrack. None = off.",
                   1.0, 0.0, -1.0, 0.0, 0.0, " (adds to A/B's text on the same rows)")
        opt["extra_loras"] = ("STRING", {"default": "[]", "tooltip": (
            "Slots D, E, ... added with the Add LoRA button, as JSON. Edited by the node's panel.")})
        opt["disabled_loras"] = ("STRING", {"default": "[]", "tooltip": (
            "Slot letters switched off with the checkbox, as JSON. Their settings stay.")})
        return {"required": req, "optional": opt}

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "apply"
    CATEGORY = "Hand Tie Clips"
    DESCRIPTION = ("Loads H3 LoRAs per kind of token: each slot gives the video, the soundtrack, the "
                   "reference pictures and the prompt their own strength (video 1, audio 0 keeps the "
                   "voices on the plain model). Slots A, B, C plus Add LoRA; chain nodes to stack more.")

    def apply(self, model, lora_a, a_video, a_audio, a_reference, a_text, a_refiner, a_block_start, a_block_end,
              lora_b, b_video, b_audio, b_reference, b_text, b_refiner, b_block_start, b_block_end,
              other_keys=OTHER_KEYS[0], add_mode=ADD_MODES[0],
              lora_c=NONE, c_video=1.0, c_audio=0.0, c_reference=-1.0, c_text=0.0, c_refiner=0.0,
              c_block_start=0, c_block_end=N_BLOCKS - 1, extra_loras="[]", disabled_loras="[]"):
        import os
        import comfy.sd
        import comfy.utils
        import folder_paths

        def rng(a, b):
            return (min(int(a), int(b)), max(int(a), int(b)))
        slots = [("A", lora_a, strengths_of(a_video, a_audio, a_reference, a_text), rng(a_block_start, a_block_end), float(a_refiner)),
                 ("B", lora_b, strengths_of(b_video, b_audio, b_reference, b_text), rng(b_block_start, b_block_end), float(b_refiner)),
                 ("C", lora_c, strengths_of(c_video, c_audio, c_reference, c_text), rng(c_block_start, c_block_end), float(c_refiner))]
        extra_all = {}
        for L, rec in parse_extra(extra_loras, folder_paths.get_filename_list("loras")):
            slots.append((L, rec["lora_name"], strengths_of(rec["video"], rec["audio"], rec["reference"], rec["text"]),
                          rng(rec["block_start"], rec["block_end"]), float(rec["refiner"])))
            extra_all[L] = rec["all_tokens"]
        disabled = parse_disabled(disabled_loras, {s[0] for s in slots})

        loaded, file_ids = {}, {}
        for L, nm, *_ in slots:
            if L in disabled or nm in (None, "", NONE) or nm in loaded:
                continue
            path = folder_paths.get_full_path_or_raise("loras", nm)
            blocks, refiner, other = parse(comfy.utils.load_torch_file(path, safe_load=True))
            if not blocks:
                raise RuntimeError(f"{TAG}: {nm} (slot {L}) has no H3 block layers "
                                   "(blocks.N.attn.qkv_proj / out_proj / mlp.fc1 / fc2). It may use "
                                   "Diffusers names: load it with a normal LoRA loader.")
            _check_model(model, blocks, nm)
            loaded[nm] = (blocks, refiner, other)
            st = os.stat(path)
            file_ids[nm] = f"{st.st_size}:{int(st.st_mtime)}"

        specs_in, patches, lines = plan_slots(slots, loaded, other_keys, extra_all, disabled)
        m = model
        for sd, s, note in patches:
            m, _ = comfy.sd.load_lora_for_models(m, None, sd, float(s), 0.0)
            lines.append(note)
        if not specs_in:
            print(f"[{TAG}] nothing to apply in the blocks:\n  " + "\n  ".join(lines), flush=True)
            return (m if m is not model else model.clone(),)
        specs = [Spec(name, blocks, st, rg, file_id=file_ids[nm]) for name, nm, blocks, st, rg in specs_in]
        m, rt = install(m, specs, stochastic=(add_mode == "fp32_stochastic"))
        print(f"[{TAG}] {len(specs)} LoRA set(s)" + (f", add {add_mode}" if add_mode != ADD_MODES[0] else "")
              + (f", stacked with {len(rt.specs) - len(specs)} from an earlier node" if len(rt.specs) > len(specs) else "")
              + ":\n  " + "\n  ".join(lines), flush=True)
        return (m,)


NODE_CLASS_MAPPINGS = {"HTCTokenLoRA": HTCTokenLoRA}
NODE_DISPLAY_NAME_MAPPINGS = {"HTCTokenLoRA": "H3 Token LoRA (HTC)"}
