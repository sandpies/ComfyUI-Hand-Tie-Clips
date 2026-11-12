"""What Qwen3-VL sees of each reference picture, apart from the DiT's copy.

Core's MiniMaxH3ReferenceToVideo hands ONE resized copy of a reference to two
readers: the VAE (the DiT's latent block) and Qwen3-VL's vision patches (the
text context). Under `ref_image_size=match` that copy is the generation's pixel
area, so a large character sheet reaches Qwen as a thumbnail: a 4562x6184 sheet
became 672x896 at 576p, every face on it a few dozen pixels.

Qwen's patches are cheap next to the DiT copy (one token per 32x32 pixels,
attended as text context; halving the context moved DiT time ~4% in a
same-seed A/B), and the DiT copy is what costs memory and time. So
this module changes only Qwen's view, by the row's retention, with no widget:

  identity rows (fully_preserved, partially_copy): the ORIGINAL file, read
      fresh from disk, at the larger of IDENTITY_QWEN_PX^2 and the render's
      area, never above the file's own size. Core's copy has already lost the
      detail, so the view has to come from the file.
  prop rows: core's copy shrunk to PROP_QWEN_PX^2 (shape, not texture).
  everything else (plates, RefMods, pins, video refs): untouched.
  a row's `qwen_mp` (REFS tab, "qwen" box) overrides all of the above for
      that picture: the original at that many MP, down only.

Same-seed A/B (3 hops, 576p): a character sheet shown to Qwen
from the original at ~1 MP held likeness better than core's 0.6 MP copy, at no
measurable render cost.

How it plugs in: `register()` maps the exact tensor the chain hands Core to its
planned view; `wrap()` returns a clone of the CLIP whose tokenizer swaps those
views in, matched by ORDER (Core walks `ref_images.values()` skipping None and
emits one "image" item each, in that order). If the counts ever disagree the
items pass through untouched, with a note.
"""

import math

import torch

TAG = "HandTieClips"
VERSION = "qv1"

IDENTITY_QWEN_PX = 1024     # area side for sheets and garments (1024^2 ~ 1.05 MP)
PROP_QWEN_PX = 384          # area side for props (~0.15 MP)
FACTOR = 32                 # Qwen3-VL: 16 px patches, 2x2 merge -> one token per 32x32

IDENTITY = ("fully_preserved", "partially_copy")
PROP = ("prop",)

# id(tensor handed to Core) -> (tensor, plan). The tensor is held so its id
# cannot be reused by another object while the entry lives. plan is a
# [1, H, W, 3] view tensor (identity) or an int area side (prop).
_REGISTRY = {}


def reset():
    _REGISTRY.clear()


def _fit(h, w, area, multiple=FACTOR):
    scale = math.sqrt(float(area) / float(h * w))
    th = max(multiple, round(h * scale / multiple) * multiple)
    tw = max(multiple, round(w * scale / multiple) * multiple)
    return th, tw


def identity_view(path, render_area, area=None):
    """The original file at max(IDENTITY_QWEN_PX^2, render_area), down only.
    `area` (pixels) overrides that target: the row's own qwen_mp."""
    from PIL import Image, ImageOps  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        want = (float(area) if area else
                max(float(IDENTITY_QWEN_PX ** 2), float(render_area)))
        area = min(float(im.width * im.height), want)
        th, tw = _fit(im.height, im.width, area)
        if (tw, th) != (im.width, im.height):
            im = im.resize((tw, th), Image.Resampling.LANCZOS)
        arr = np.asarray(im, dtype=np.float32) / 255.0
    return torch.from_numpy(arr)[None], (im.width, im.height)


def register(tensor, retention, path=None, render_area=0, tag="", qwen_mp=0.0):
    """Plan Qwen's view of `tensor` (the exact object handed to Core).

    `qwen_mp` is the row's REFS-tab setting: > 0 shows Qwen the original file
    at that many megapixels (down only, never above the file), whatever the
    retention. 0 is auto, by retention."""
    ret = str(retention or "")
    try:
        qwen_mp = float(qwen_mp or 0.0)
    except (TypeError, ValueError):
        qwen_mp = 0.0
    if (qwen_mp > 0 or ret in IDENTITY) and path:
        try:
            view, _orig = identity_view(path, render_area,
                                        area=qwen_mp * 1e6 if qwen_mp > 0 else None)
        except Exception as exc:  # unreadable: Core's copy stands
            print(f"[{TAG}] @{tag}: Qwen view from the original failed ({exc!r}); "
                  f"Qwen sees the render-size copy", flush=True)
            return None
        _REGISTRY[id(tensor)] = (tensor, view)
        print(f"[{TAG}] @{tag}: Qwen sees the original at "
              f"{int(view.shape[2])}x{int(view.shape[1])}"
              + (f" (row setting {qwen_mp:g} MP)" if qwen_mp > 0 else ""), flush=True)
        return view
    if ret in PROP:
        _REGISTRY[id(tensor)] = (tensor, PROP_QWEN_PX)
        return PROP_QWEN_PX
    return None


def _plan_for(t):
    hit = _REGISTRY.get(id(t)) if t is not None else None
    return hit[1] if hit is not None and hit[0] is t else None


def key(ref_images):
    """Hop-cache payload: what Qwen is shown differently, or None for nothing."""
    out = {}
    for k, t in sorted((ref_images or {}).items()):
        p = _plan_for(t)
        if p is None:
            continue
        out[k] = int(p) if isinstance(p, int) else list(p.shape[1:3])
    return [VERSION, out] if out else None


def _resize(x, th, tw):
    if int(x.shape[1]) == th and int(x.shape[2]) == tw:
        return x
    y = torch.nn.functional.interpolate(x.movedim(-1, 1).float(), size=(th, tw),
                                        mode="area")
    return y.movedim(1, -1).to(x.dtype).clamp(0, 1)


class _ViewTokenizer:
    """The real tokenizer, with planned views swapped into minimax_ref_items."""

    def __init__(self, inner, plans):
        self._inner = inner
        self._plans = plans

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def tokenize_with_weights(self, text, return_word_ids=False, **kwargs):
        items = kwargs.get("minimax_ref_items")
        if items:
            imgs = [k for k, it in enumerate(items)
                    if it.get("type") == "image" and it.get("data") is not None]
            if len(imgs) != len(self._plans):
                print(f"[{TAG}] Qwen view: {len(imgs)} pictures reached the encoder, "
                      f"{len(self._plans)} expected; leaving them as Core sent them",
                      flush=True)
            else:
                new = list(items)
                for k, plan in zip(imgs, self._plans):
                    if plan is None:
                        continue
                    data = items[k]["data"]
                    if isinstance(plan, int):
                        h, w = int(data.shape[1]), int(data.shape[2])
                        if h * w <= plan * plan:
                            continue
                        th, tw = _fit(h, w, plan * plan)
                        view = _resize(data[:1], th, tw)
                    else:
                        view = plan.to(dtype=data.dtype)
                    new[k] = dict(items[k], data=view)
                kwargs["minimax_ref_items"] = new
        return self._inner.tokenize_with_weights(text, return_word_ids, **kwargs)


def wrap(clip, ref_images):
    """`clip`, or a clone whose tokenizer shows Qwen the planned views."""
    if clip is None or not ref_images or not _REGISTRY:
        return clip
    plans = [_plan_for(t) for t in ref_images.values() if t is not None]
    if not any(p is not None for p in plans):
        return clip
    c = clip.clone()
    c.tokenizer = _ViewTokenizer(clip.tokenizer, plans)
    return c
