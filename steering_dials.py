"""Clean-room MIT steering dials for MiniMax H3 (`token_refiner` & early-block seams).

Applies compact (~14 KB) prompt-difference vectors onto H3's refined prompt
embeddings without modifying model weights or interfering with LoRAs:
  * Loads standard `.safetensors` steering dial files (`diffusion_model.token_refiner.dials_shift`
    and `diffusion_model.condition_proj.diff_b`) from `models/loras/dials/`,
    `models/dials/`, and (if installed) `custom_nodes/ComfyUI-Dials/dials/`.
  * Accumulates multiple post-refiner shifts in `float64` before casting to compute
    dtype so dial ordering never alters outputs.
  * Supports `blocks_0_24 (voice safe)` via `double_block` span injection (leaving
    late acoustic/detail blocks clean) or `all_blocks` via `token_refiner` wrap.
  * Includes a clean-room prompt-pair synthesizer (`HTCMakeSteeringDial`) with
    `{subject}` expansion, `! hold` orthogonalization, and built-in starter
    recipes for Motion, Expression, Energy, and Life.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from typing import Any

import torch

TAG = "HTCSteeringDials"

SCOPE_MODES = ("blocks_0_24 (voice safe)", "all_blocks")
NONE = "None"
POST_KEY = "diffusion_model.token_refiner.dials_shift"
PRE_KEY = "diffusion_model.condition_proj.diff_b"
OPT_KEY = "htc_steering_dials"
RAW_OPT_KEY = "_htc_steering_specs"

_SAFE_FILE_RE = re.compile(r"[^A-Za-z0-9._-]+")
_DIAL_CACHE: dict[tuple[str, int, int], tuple[str, torch.Tensor, str, dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()

BUILTIN_DIAL_SUBJECTS = (
    "A young woman",
    "A young man",
    "An older man",
    "An East Asian woman",
    "A tall athlete",
    "A smiling dancer",
)

BUILTIN_NUISANCE_PAIRS = (
    ("{subject} stands in a room.", "{subject} stands in a room, visible clearly."),
    ("{subject} is inside a space.", "{subject} is right there inside a detailed space."),
    ("A scene showing {subject}.", "A cinematic scene featuring {subject} in clear focus."),
    ("{subject} in everyday light.", "{subject} under ordinary natural ambient light."),
)

BUILTIN_DIAL_RECIPES: dict[str, dict[str, Any]] = {
    "motion": {
        "file": "htc_motion.safetensors",
        "neg_label": "Freeze / Still",
        "pos_label": "Dynamic / Fast",
        "pairs": "\n".join([
            "{subject} stands perfectly still, posing steadily in place. ||| {subject} moves briskly across the scene, stepping and gesturing energetically.",
            "{subject} sits calmly without shifting posture. ||| {subject} leaps up, pivots cleanly, and sweeps arms through space.",
            "{subject} holds a quiet, stationary stance facing forward. ||| {subject} strides rapidly past frame with dynamic full-body momentum.",
        ]),
    },
    "expression": {
        "file": "htc_expression.safetensors",
        "neg_label": "Stoic / Deadpan",
        "pos_label": "Vivid / Expressive",
        "pairs": "\n".join([
            "{subject} keeps a flat, neutral, stoic face with unmoving eyebrows and relaxed lips. ||| {subject} reacts with vivid facial acting, raised expressive eyebrows, bright widening eyes, and dynamic mouth expression.",
            "{subject} holds a calm, unreadable deadpan gaze straight ahead. ||| {subject} shifts rapidly from an amused grin to surprised wide eyes and an expressive smirk.",
            "{subject} shows minimal restrained emotion in the eyes and cheeks. ||| {subject} radiates rich charismatic facial emotion with animated brow and cheek movement.",
            "! {subject} speaks in a quiet low voice. ||| {subject} speaks in a loud booming voice.",
        ]),
    },
    "energy": {
        "file": "htc_energy.safetensors",
        "neg_label": "Hushed / Calm",
        "pos_label": "Charged / Intense",
        "pairs": "\n".join([
            "{subject} carries a quiet, relaxed, unhurried emotional tone. ||| {subject} radiates urgent, charged dramatic intensity and high emotional stakes.",
            "{subject} breathes gently with calm composure in a quiet moment. ||| {subject} breathes rapidly with fierce commitment, sharp tension, and electric dramatic presence.",
            "{subject} delivers a calm, understated performance. ||| {subject} delivers a passionate, commanding performance at peak intensity.",
        ]),
    },
    "life": {
        "file": "htc_life.safetensors",
        "neg_label": "Locked / Spare",
        "pos_label": "Alive / Kinetic Air",
        "pairs": "\n".join([
            "{subject} stands in still air with motionless hair, fabric, and quiet background. ||| {subject} blinks naturally and breathes visibly as hair, fabric, dust motes, and background lights move continuously.",
            "{subject} rests in a static room with still curtains and steady light. ||| {subject} shifts weight naturally with subtle hand micro-business while air, steam, and light drift behind.",
        ]),
    },
}


def _dials_search_dirs() -> list[str]:
    dirs: list[str] = []
    try:
        import folder_paths  # noqa: PLC0415

        for base in folder_paths.get_folder_paths("loras") or ():
            dirs.append(os.path.join(base, "dials"))
        models_dir = getattr(folder_paths, "models_dir", "")
        if models_dir:
            dirs.append(os.path.join(models_dir, "dials"))
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    custom_nodes_dir = os.path.dirname(here)
    comfy_dials = os.path.join(custom_nodes_dir, "ComfyUI-Dials", "dials")
    if os.path.isdir(comfy_dials):
        dirs.append(comfy_dials)
    seen, out = set(), []
    for d in dirs:
        nd = os.path.normcase(os.path.abspath(d))
        if nd not in seen:
            seen.add(nd)
            out.append(d)
    return out


def default_save_dir() -> str:
    dirs = _dials_search_dirs()
    for d in dirs:
        if "ComfyUI-Dials" not in d:
            os.makedirs(d, exist_ok=True)
            return d
    fallback = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dials")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def list_dial_files() -> list[str]:
    """Return sorted relative filenames of available `.safetensors` steering dials."""
    found: dict[str, str] = {}
    for root in _dials_search_dirs():
        if not os.path.isdir(root):
            continue
        for dp, dns, fns in os.walk(root):
            dns[:] = sorted(d for d in dns if not d.startswith(("_", ".")))
            for fn in sorted(fns):
                if not fn.lower().endswith(".safetensors"):
                    continue
                rel = os.path.relpath(os.path.join(dp, fn), root).replace("\\", "/")
                if rel not in found:
                    found[rel] = os.path.join(dp, fn)
    return sorted(found.keys(), key=lambda s: s.lower())


def dial_choices() -> list[str]:
    return [NONE] + list_dial_files()


def resolve_dial_path(name: str) -> str | None:
    clean = str(name or "").strip().replace("\\", "/")
    if not clean or clean == NONE:
        return None
    if os.path.isabs(clean) and os.path.isfile(clean):
        return clean
    for root in _dials_search_dirs():
        cand = os.path.abspath(os.path.join(root, clean))
        try:
            if os.path.commonpath([os.path.abspath(root), cand]) == os.path.abspath(root) and os.path.isfile(cand):
                return cand
        except ValueError:
            continue
    base = os.path.basename(clean).lower()
    for rel in list_dial_files():
        if os.path.basename(rel).lower() == base:
            for root in _dials_search_dirs():
                cand = os.path.abspath(os.path.join(root, rel))
                if os.path.isfile(cand):
                    return cand
    return None


def resolve_axis_dial(axis: str) -> str | None:
    """Resolve the best available `.safetensors` dial for a built-in performance axis."""
    ax = str(axis or "").strip().lower()
    candidates = {
        "motion": ("htc_motion.safetensors", "h3_motion.safetensors"),
        "expression": ("htc_expression.safetensors", "h3_expression.safetensors", "h3_face.safetensors"),
        "energy": ("htc_energy.safetensors", "h3_energy.safetensors"),
        "life": ("htc_life.safetensors", "h3_life.safetensors"),
    }.get(ax, ())
    for c in candidates:
        p = resolve_dial_path(c)
        if p:
            return p
    return None


def load_dial_file(path: str) -> tuple[str, torch.Tensor, str, dict[str, Any]]:
    """Load `(seam, vec_f64_cpu, sha16, metadata)` from a `.safetensors` steering dial."""
    from safetensors import safe_open  # noqa: PLC0415

    ap = os.path.abspath(path)
    st = os.stat(ap)
    ck = (ap, int(st.st_mtime_ns), int(st.st_size))
    with _CACHE_LOCK:
        hit = _DIAL_CACHE.get(ck)
        if hit is not None:
            return hit

    with safe_open(ap, framework="pt", device="cpu") as f:
        meta = dict(f.metadata() or {})
        fam = str(meta.get("model_family") or "").strip().lower()
        if fam and fam not in ("minimax_h3", "h3", "minimax-h3"):
            raise ValueError(f"{TAG}: dial '{os.path.basename(ap)}' belongs to model family '{fam}', not MiniMax H3.")
        keys = set(f.keys())
        if POST_KEY in keys:
            seam = "post_refiner"
            t = f.get_tensor(POST_KEY)
        elif PRE_KEY in keys:
            seam = "pre_refiner"
            t = f.get_tensor(PRE_KEY)
        elif "dials_shift" in keys:
            seam = "post_refiner"
            t = f.get_tensor("dials_shift")
        elif "delta" in keys:
            seam = "post_refiner"
            t = f.get_tensor("delta")
        else:
            raise ValueError(f"{TAG}: '{os.path.basename(ap)}' has no recognized steering vector key ({sorted(keys)}).")
        vec = t.detach().to(device="cpu", dtype=torch.float64).reshape(-1)
    sha16 = hashlib.sha256(vec.to(dtype=torch.float32).numpy().tobytes()).hexdigest()[:16]
    val = (seam, vec, sha16, meta)
    with _CACHE_LOCK:
        if len(_DIAL_CACHE) > 64:
            _DIAL_CACHE.clear()
        _DIAL_CACHE[ck] = val
    return val


def dial_catalog_info() -> list[dict[str, Any]]:
    """Lightweight UI list of installed dial files + labels/ranges."""
    items = []
    for rel in list_dial_files():
        p = resolve_dial_path(rel)
        if not p:
            continue
        try:
            seam, vec, sha16, meta = load_dial_file(p)
            info_raw = meta.get("dial_info")
            dinfo = {}
            if isinstance(info_raw, str) and info_raw.strip():
                try:
                    dinfo = json.loads(info_raw)
                except Exception:
                    dinfo = {}
            items.append({
                "file": rel,
                "name": str(dinfo.get("name") or meta.get("name") or os.path.splitext(os.path.basename(rel))[0]),
                "seam": seam,
                "dim": int(vec.numel()),
                "sha16": sha16,
                "neg_label": str(dinfo.get("neg_label") or meta.get("neg_label") or "−"),
                "pos_label": str(dinfo.get("pos_label") or meta.get("pos_label") or "+"),
                "useful": float(dinfo.get("useful") or 1.0),
                "overcook": float(dinfo.get("overcook") or 1.5),
            })
        except Exception:
            continue
    return items


class _ConditionProjShift:
    """Wraps `diffusion_model.condition_proj` to add a pre-refiner bias vector."""

    def __init__(self, inner, shift_f64: torch.Tensor):
        self._inner = inner
        self._shift = shift_f64

    def __call__(self, *args, **kwargs):
        out = self._inner(*args, **kwargs)
        d = self._shift.to(device=out.device, dtype=out.dtype)
        return out + d

    def __getattr__(self, name: str):
        return getattr(self._inner, name)


class _TokenRefinerShift:
    """Wraps `diffusion_model.token_refiner` to add a post-refiner steering vector."""

    def __init__(self, inner, shift_f64: torch.Tensor):
        self._inner = inner
        self._shift = shift_f64

    def __call__(self, *args, **kwargs):
        out = self._inner(*args, **kwargs)
        d = self._shift.to(device=out.device, dtype=out.dtype)
        return out + d

    def __getattr__(self, name: str):
        return getattr(self._inner, name)


def _unwrap_module(mod):
    while isinstance(mod, (_ConditionProjShift, _TokenRefinerShift)):
        mod = mod._inner
    return mod


def _add_text_span(img: torch.Tensor, layout, delta: torch.Tensor, sign: float) -> torch.Tensor:
    segs = getattr(layout, "segments", None) if layout is not None else None
    if not segs:
        return img
    out = img.clone()
    d = delta.to(device=out.device, dtype=torch.float32) * float(sign)
    for a, b, kind in segs:
        if kind == "text":
            out[a:b] = (out[a:b].float() + d).to(dtype=out.dtype)
    return out


def _make_block_text_hook(delta_f64: torch.Tensor, sign: float, prev_patch):
    def _hook(args: dict, orig: dict):
        lay = args.get("layout") or (args.get("transformer_options") or {}).get("minimax_h3_layout")
        if lay is not None:
            args = dict(args)
            args["img"] = _add_text_span(args["img"], lay, delta_f64, sign)
        if prev_patch is not None:
            return prev_patch(args, orig)
        return orig["original_block"](args)
    return _hook


def apply_steering_dials(
    model,
    specs: list[tuple[str, str, float]],
    *,
    scope: str = SCOPE_MODES[0],
) -> tuple[Any, str]:
    """Clone `model` with stacked steering dials applied cleanly.

    `specs`: list of `(display_name, file_path, strength)`.
    Returns `(patched_model, summary_str)`.
    """
    clean_specs = [(str(nm), str(fp), float(s)) for nm, fp, s in (specs or ()) if fp and abs(float(s)) >= 1e-5]
    base_to = (getattr(model, "model_options", None) or {}).get("transformer_options") or {}
    prev_raw = list(base_to.get(RAW_OPT_KEY) or ())
    combined_raw = prev_raw + clean_specs
    if not combined_raw:
        return model, "no active steering dials"

    post_sum: torch.Tensor | None = None
    pre_sum: torch.Tensor | None = None
    fp_records: list[tuple[str, str, float, str]] = []
    labels: list[str] = []

    use_early = str(scope or "").startswith("blocks_0_24")
    if use_early:
        # blocks_0_24 is a pair of `double_block` patches; core calls a replaced block
        # with `attention=`, which an old KJNodes block forward cannot take.
        try:
            from .sparse_attn import block_forward_takes_attention as _bfta  # noqa: PLC0415
        except ImportError:
            from sparse_attn import block_forward_takes_attention as _bfta  # noqa: PLC0415
        if not _bfta(model):
            print(f"[{TAG}] scope blocks_0_24 needs a newer ComfyUI-KJNodes (its patched H3 "
                  "block forward has no `attention` argument); using all_blocks.", flush=True)
            use_early = False
    scope_tag = "blocks_0_24" if use_early else "all_blocks"

    for nm, fp, strength in combined_raw:
        seam, vec, sha16, _meta = load_dial_file(fp)
        scaled = vec * float(strength)
        if seam == "pre_refiner":
            pre_sum = scaled if pre_sum is None else (pre_sum + scaled)
        else:
            post_sum = scaled if post_sum is None else (post_sum + scaled)
        fp_records.append((os.path.basename(fp), sha16, round(float(strength), 4), scope_tag))
        labels.append(f"{nm}:{strength:+.2f}")

    m = model.clone()
    to = m.model_options.setdefault("transformer_options", {})
    to[RAW_OPT_KEY] = combined_raw
    to[OPT_KEY] = tuple(fp_records)

    dm = getattr(getattr(m, "model", None), "diffusion_model", None)
    if dm is None:
        return m, ", ".join(labels)

    hidden_dim = int(getattr(dm, "hidden_size", 5376))

    if pre_sum is not None:
        if int(pre_sum.numel()) != hidden_dim:
            raise ValueError(f"{TAG}: pre-refiner dial dim {int(pre_sum.numel())} != model hidden_size {hidden_dim}")
        orig_cp = _unwrap_module(m.get_model_object("diffusion_model.condition_proj"))
        m.add_object_patch("diffusion_model.condition_proj", _ConditionProjShift(orig_cp, pre_sum))

    if post_sum is not None:
        if int(post_sum.numel()) != hidden_dim:
            raise ValueError(f"{TAG}: dial dim {int(post_sum.numel())} != model hidden_size {hidden_dim}")
        n_blocks = len(getattr(dm, "blocks", ()) or ())
        if use_early and n_blocks > 25:
            # Strip any previous steering hooks if stacking multiple HTCSteeringDials nodes
            dit_rep = dict((to.get("patches_replace") or {}).get("dit") or {})
            prev0 = dit_rep.get(("double_block", 0))
            prev25 = dit_rep.get(("double_block", 25))
            if getattr(prev0, "_htc_steering_inner", None) is not None:
                prev0 = prev0._htc_steering_inner
            if getattr(prev25, "_htc_steering_inner", None) is not None:
                prev25 = prev25._htc_steering_inner
            h0 = _make_block_text_hook(post_sum, +1.0, prev0)
            h25 = _make_block_text_hook(post_sum, -1.0, prev25)
            h0._htc_steering_inner = prev0  # type: ignore[attr-defined]
            h25._htc_steering_inner = prev25  # type: ignore[attr-defined]
            m.set_model_patch_replace(h0, "dit", "double_block", 0)
            m.set_model_patch_replace(h25, "dit", "double_block", 25)
            orig_tr = _unwrap_module(m.get_model_object("diffusion_model.token_refiner"))
            m.add_object_patch("diffusion_model.token_refiner", orig_tr)
        else:
            orig_tr = _unwrap_module(m.get_model_object("diffusion_model.token_refiner"))
            m.add_object_patch("diffusion_model.token_refiner", _TokenRefinerShift(orig_tr, post_sum))

    return m, f"[{scope_tag}] " + ", ".join(labels)


def _expand_pair_lines(pairs_text: str) -> tuple[list[tuple[str, str, float]], list[tuple[str, str]]]:
    """Parse `A ||| B [:: weight]` and `! holdA ||| holdB` lines with `{subject}` expansion."""
    main_pairs: list[tuple[str, str, float]] = []
    hold_pairs: list[tuple[str, str]] = []
    for raw_ln in str(pairs_text or "").splitlines():
        ln = raw_ln.strip()
        if not ln or ln.startswith("#"):
            continue
        is_hold = ln.startswith("!")
        if is_hold:
            ln = ln[1:].strip()
        if "|||" not in ln:
            continue
        weight = 1.0
        if not is_hold and "::" in ln:
            body, w_str = ln.rsplit("::", 1)
            try:
                weight = float(w_str.strip())
                ln = body.strip()
            except ValueError:
                pass
        a, b = (part.strip() for part in ln.split("|||", 1))
        if not a or not b:
            continue
        if "{subject}" in a or "{subject}" in b:
            for subj in BUILTIN_DIAL_SUBJECTS:
                ea = a.replace("{subject}", subj)
                eb = b.replace("{subject}", subj)
                if is_hold:
                    hold_pairs.append((ea, eb))
                else:
                    main_pairs.append((ea, eb, weight))
        else:
            if is_hold:
                hold_pairs.append((a, b))
            else:
                main_pairs.append((a, b, weight))
    return main_pairs, hold_pairs


def _encode_prompt_mean(clip, dm, text: str) -> torch.Tensor:
    """Encode prompt -> H3 refined token mean `[hidden]` in float64."""
    tokens = clip.tokenize(text)
    cond = clip.encode_from_tokens_scheduled(tokens)
    qwen_states = cond[0][0]
    dev = next(dm.condition_proj.parameters()).device
    dt = getattr(dm, "dtype", None) or qwen_states.dtype
    with torch.no_grad():
        refined = dm.preprocess_text_embeds(qwen_states.to(device=dev, dtype=dt))
        mean_vec = refined[0].float().mean(dim=0).to(device="cpu", dtype=torch.float64)
    return mean_vec


def synthesize_dial_file(
    *,
    clip,
    model,
    dial_name: str,
    pairs_text: str,
    neg_label: str = "−",
    pos_label: str = "+",
    debias: bool = True,
) -> tuple[str, dict[str, Any]]:
    """Compute a clean-room post-refiner steering vector from prompt pairs & save `.safetensors`."""
    from safetensors.torch import save_file  # noqa: PLC0415
    import comfy.model_management as mm  # noqa: PLC0415

    main_pairs, hold_pairs = _expand_pair_lines(pairs_text)
    if not main_pairs:
        raise ValueError(f"{TAG}: need at least one valid `A ||| B` prompt pair.")

    clean_stem = _SAFE_FILE_RE.sub("_", os.path.splitext(os.path.basename(str(dial_name or "custom_dial")))[0]).strip("_")
    if not clean_stem:
        clean_stem = "custom_dial"
    out_dir = default_save_dir()
    out_path = os.path.join(out_dir, clean_stem + ".safetensors")

    dm = getattr(getattr(model, "model", None), "diffusion_model", None)
    if dm is None or not hasattr(dm, "preprocess_text_embeds"):
        raise ValueError(f"{TAG}: MODEL must be a MiniMax H3 diffusion model.")

    # Ensure condition_proj + token_refiner are runnable on GPU/device via ComfyUI loader
    mm.load_models_gpu([model])
    mm.load_models_gpu([clip.patcher])

    diffs: list[torch.Tensor] = []
    weights: list[float] = []
    for a, b, w in main_pairs:
        va = _encode_prompt_mean(clip, dm, a)
        vb = _encode_prompt_mean(clip, dm, b)
        diffs.append(vb - va)
        weights.append(float(w))

    w_sum = sum(abs(w) for w in weights) or 1.0
    raw_vec = sum(d * (w / w_sum) for d, w in zip(diffs, weights))

    # Pair agreement cosine
    raw_norm = float(raw_vec.norm().item()) or 1.0
    cos_vals = [float(torch.dot(d, raw_vec).item() / ((float(d.norm().item()) or 1.0) * raw_norm)) for d in diffs]
    pair_agree = sum(cos_vals) / max(1, len(cos_vals))

    # Collect nuisance + ! hold directions and orthogonalize via QR
    nuis_vecs: list[torch.Tensor] = []
    if debias:
        for na, nb in BUILTIN_NUISANCE_PAIRS:
            ea = na.replace("{subject}", BUILTIN_DIAL_SUBJECTS[0])
            eb = nb.replace("{subject}", BUILTIN_DIAL_SUBJECTS[0])
            nuis_vecs.append(_encode_prompt_mean(clip, dm, eb) - _encode_prompt_mean(clip, dm, ea))
    for ha, hb in hold_pairs:
        nuis_vecs.append(_encode_prompt_mean(clip, dm, hb) - _encode_prompt_mean(clip, dm, ha))

    vec = raw_vec.clone()
    debias_frac = 0.0
    if nuis_vecs:
        mat = torch.stack([v for v in nuis_vecs if float(v.norm().item()) > 1e-6], dim=1)
        if mat.numel() > 0 and mat.shape[1] > 0:
            q, _ = torch.linalg.qr(mat, mode="reduced")
            proj = q @ (q.T @ vec)
            before_sq = float(torch.dot(vec, vec).item()) or 1.0
            vec = vec - proj
            after_sq = float(torch.dot(vec, vec).item())
            debias_frac = max(0.0, 1.0 - (after_sq / before_sq))

    meta = {
        "format": "HTC-SteeringDial v1",
        "model_family": "minimax_h3",
        "name": clean_stem,
        "inject": "post_refiner (hook)",
        "n_pairs": str(len(main_pairs)),
        "pair_agreement_cos": f"{pair_agree:.3f}",
        "debias_removed": f"{debias_frac:.3f}",
        "dial_info": json.dumps({
            "version": 2,
            "name": clean_stem,
            "neg_label": str(neg_label or "−"),
            "pos_label": str(pos_label or "+"),
            "useful": 1.0,
            "overcook": 1.5,
        }),
    }
    tmp_path = out_path + ".tmp"
    save_file({POST_KEY: vec.to(dtype=torch.bfloat16).contiguous()}, tmp_path, metadata=meta)
    os.replace(tmp_path, out_path)
    with _CACHE_LOCK:
        _DIAL_CACHE.clear()
    return out_path, {
        "path": out_path,
        "file": os.path.basename(out_path),
        "n_pairs": len(main_pairs),
        "n_holds": len(hold_pairs),
        "pair_agreement": round(pair_agree, 3),
        "debias_removed": round(debias_frac, 3),
    }


def _parse_rack_json(raw: str) -> list[tuple[str, str, float]]:
    if not raw or not str(raw).strip():
        return []
    try:
        rows = json.loads(str(raw))
    except Exception:
        return []
    if not isinstance(rows, list):
        return []
    any_solo = any(isinstance(r, dict) and r.get("on", True) and r.get("solo") for r in rows)
    out: list[tuple[str, str, float]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        if not r.get("on", True):
            continue
        if any_solo and not r.get("solo"):
            continue
        fn = str(r.get("file") or r.get("dial") or "").strip()
        try:
            s = float(r.get("strength") or 0.0)
        except (TypeError, ValueError):
            s = 0.0
        if not fn or fn == NONE or abs(s) < 1e-5:
            continue
        p = resolve_dial_path(fn)
        if p:
            out.append((os.path.splitext(os.path.basename(fn))[0], p, s))
    return out


class HTCSteeringDials:
    """Apply signed steering dial vectors to MiniMax H3 (`Motion / Expr / Energy + Rack`)."""

    CATEGORY = "Hand Tie Clips"
    RETURN_TYPES = ("MODEL", "STRING")
    RETURN_NAMES = ("model", "info")
    FUNCTION = "apply"
    DESCRIPTION = (
        "Clean-room MIT steering dials for MiniMax H3. Steers Motion, Expression, "
        "Energy, and Mood vectors directly in H3's prompt space with float64 order-independent "
        "addition and optional Blocks 0-24 voice-safe protection."
    )

    @classmethod
    def INPUT_TYPES(cls):
        choices = dial_choices()
        return {
            "required": {
                "model": ("MODEL", {
                    "tooltip": "MiniMax-H3 model to steer in prompt space (chains cleanly before or after HTCTokenLoRA / HTCSparseAttention).",
                }),
                "motion": ("FLOAT", {
                    "default": 0.0, "min": -2.5, "max": 2.5, "step": 0.05,
                    "tooltip": "Motion energy steering (-2 calmer/held <-> +2 dynamic action). Uses htc_motion or h3_motion dial; auto-synthesizes if CLIP is wired.",
                }),
                "expression": ("FLOAT", {
                    "default": 0.0, "min": -2.5, "max": 2.5, "step": 0.05,
                    "tooltip": "Facial expression steering (-2 stoic/restrained <-> +2 vivid/expressive). Auto-synthesizes htc_expression.safetensors if CLIP is wired.",
                }),
                "energy": ("FLOAT", {
                    "default": 0.0, "min": -2.5, "max": 2.5, "step": 0.05,
                    "tooltip": "Vocal & dramatic intensity steering (-2 soft/hushed <-> +2 high-energy delivery). Auto-synthesizes htc_energy.safetensors if CLIP is wired.",
                }),
                "mood_dial": (choices, {
                    "default": NONE,
                    "tooltip": "Optional custom .safetensors dial vector from models/loras/dials/ (e.g. a dial created by HTC Make Steering Dial).",
                }),
                "mood_strength": ("FLOAT", {
                    "default": 0.0, "min": -2.5, "max": 2.5, "step": 0.05,
                    "tooltip": "Signed strength for mood_dial (-2.5 pushes toward A side, +2.5 pushes toward B side; 0 = off).",
                }),
                "scope": (list(SCOPE_MODES), {
                    "default": SCOPE_MODES[0],
                    "tooltip": (
                        "Where the steering vector applies in H3's 50 DiT blocks: "
                        "blocks_0_24 (voice safe) steers early composition/motion blocks and leaves blocks 25-49 untouched for clean voice & skin; "
                        "all_blocks shifts the refined prompt once across the whole stack."
                    ),
                }),
            },
            "optional": {
                "clip": ("CLIP", {
                    "tooltip": "Optional H3 CLIP (Qwen3-VL). Only needed once to auto-mint missing built-in Motion/Expression/Energy .safetensors dials.",
                }),
                "rack_json": ("STRING", {
                    "default": "[]", "multiline": False,
                    "tooltip": "JSON list of extra stacked dial rows managed by the node's Dial Rack & Map panel.",
                }),
            },
        }

    def apply(
        self,
        model,
        motion: float = 0.0,
        expression: float = 0.0,
        energy: float = 0.0,
        mood_dial: str = NONE,
        mood_strength: float = 0.0,
        scope: str = SCOPE_MODES[0],
        clip=None,
        rack_json: str = "[]",
    ):
        specs: list[tuple[str, str, float]] = []
        notes: list[str] = []

        for ax, val in (("motion", motion), ("expression", expression), ("energy", energy)):
            s = float(val or 0.0)
            if abs(s) < 1e-5:
                continue
            p = resolve_axis_dial(ax)
            if p is None and clip is not None and ax in BUILTIN_DIAL_RECIPES:
                rec = BUILTIN_DIAL_RECIPES[ax]
                try:
                    p, _ = synthesize_dial_file(
                        clip=clip, model=model,
                        dial_name=rec["file"],
                        pairs_text=rec["pairs"],
                        neg_label=rec["neg_label"],
                        pos_label=rec["pos_label"],
                    )
                    notes.append(f"synthesized {os.path.basename(p)}")
                except Exception as exc:
                    notes.append(f"{ax} synth skipped ({exc})")
                    p = None
            if p is not None:
                specs.append((ax, p, s))
            else:
                notes.append(f"{ax}: no .safetensors found (wire CLIP or run HTCMakeSteeringDial)")

        if mood_dial and mood_dial != NONE and abs(float(mood_strength or 0.0)) >= 1e-5:
            mp = resolve_dial_path(mood_dial)
            if mp:
                specs.append((os.path.splitext(os.path.basename(mood_dial))[0], mp, float(mood_strength)))
            else:
                notes.append(f"missing dial '{mood_dial}'")

        specs.extend(_parse_rack_json(rack_json))
        patched, summary = apply_steering_dials(model, specs, scope=scope)
        if notes:
            summary = summary + " | " + "; ".join(notes)
        return (patched, summary)


class HTCMakeSteeringDial:
    """Clean-room MIT prompt-pair steering vector builder (`models/loras/dials/*.safetensors`)."""

    CATEGORY = "Hand Tie Clips"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("dial_file", "report")
    FUNCTION = "build"
    OUTPUT_NODE = True
    DESCRIPTION = (
        "Build a compact ~14 KB H3 steering dial from `A ||| B` prompt pairs "
        "(supports `{subject}` expansion and `! hold` orthogonalization). Saves to models/loras/dials/."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP", {
                    "tooltip": "MiniMax-H3 text encoder (Qwen3-VL) used to encode each contrast prompt pair.",
                }),
                "model": ("MODEL", {
                    "tooltip": "MiniMax-H3 model whose token_refiner + condition_proj project the prompt pair difference into a compact ~14 KB dial.",
                }),
                "recipe": (["custom", "motion", "expression", "energy", "life"], {
                    "default": "expression",
                    "tooltip": "Pick a built-in contrast recipe (motion, expression, energy, life) or custom to use pairs_text below.",
                }),
                "dial_name": ("STRING", {
                    "default": "htc_expression", "multiline": False,
                    "tooltip": "Output filename saved in models/loras/dials/ (.safetensors added automatically).",
                }),
                "neg_label": ("STRING", {
                    "default": "Stoic / Calm", "multiline": False,
                    "tooltip": "Human label shown on the negative (-1) end of this dial in HTC Steering Dials.",
                }),
                "pos_label": ("STRING", {
                    "default": "Vivid / Expressive", "multiline": False,
                    "tooltip": "Human label shown on the positive (+1) end of this dial in HTC Steering Dials.",
                }),
                "pairs_text": ("STRING", {
                    "multiline": True,
                    "default": BUILTIN_DIAL_RECIPES["expression"]["pairs"],
                    "tooltip": (
                        "Contrast prompt pairs, one per line as 'negative A ||| positive B'. "
                        "Supports {subject} expansion and '! hold: ...' lines to project out unwanted traits (like hair or lighting)."
                    ),
                }),
                "debias": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Orthogonalize the dial direction against any '! hold' lines and remove shared prompt drift so only the target trait moves.",
                }),
            }
        }

    def build(
        self,
        clip,
        model,
        recipe: str = "custom",
        dial_name: str = "htc_expression",
        neg_label: str = "−",
        pos_label: str = "+",
        pairs_text: str = "",
        debias: bool = True,
    ):
        rec = BUILTIN_DIAL_RECIPES.get(str(recipe or "").strip().lower())
        # The recipe wins unless pairs_text was edited away from EVERY built-in text:
        # the widget defaults to the expression pairs, so `recipe=motion` with the
        # default text used to mint an expression vector (under a motion name).
        builtin_pairs = {r["pairs"].strip() for r in BUILTIN_DIAL_RECIPES.values()}
        builtin_stems = {os.path.splitext(r["file"])[0] for r in BUILTIN_DIAL_RECIPES.values()}
        if rec is not None and (not str(pairs_text or "").strip()
                                or str(pairs_text).strip() in builtin_pairs):
            pairs_text = rec["pairs"]
            if not str(dial_name or "").strip() or os.path.splitext(str(dial_name).strip())[0] in builtin_stems:
                dial_name = rec["file"]
            neg_label = rec["neg_label"]
            pos_label = rec["pos_label"]
        out_path, rep = synthesize_dial_file(
            clip=clip,
            model=model,
            dial_name=dial_name,
            pairs_text=pairs_text,
            neg_label=neg_label,
            pos_label=pos_label,
            debias=bool(debias),
        )
        msg = (
            f"Saved {rep['file']} ({rep['n_pairs']} pairs, {rep['n_holds']} holds, "
            f"agreement={rep['pair_agreement']}, debias_removed={rep['debias_removed']})"
        )
        return (rep["file"], msg)


NODE_CLASS_MAPPINGS = {
    "HTCSteeringDials": HTCSteeringDials,
    "HTCMakeSteeringDial": HTCMakeSteeringDial,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HTCSteeringDials": "HTC Steering Dials (H3)",
    "HTCMakeSteeringDial": "HTC Make Steering Dial (H3)",
}
