"""Checkpointable MV Studio & Image/Song Forge helpers for HandTieClips.

Keeps ComfyUI's own GPU memory manager in charge:
  * Discovers installed diffusion models, LoRAs, VAEs, text encoders, and YuE2 nodes.
  * Ideates structured MV concept + tagged lyrics + asset prompts via the configured LLM.
  * Bridges `songmap.py` + `mv_solver.py` for interactive section editing and downbeat lock.
  * Builds validated ComfyUI `/prompt` API graphs for Qwen 2.1 + Viggle Turbo,
    RedQW2.1 Unlocked, MOSS Image, Official MiniMax-H3-Image, P-H3-Image, and YuE2.
  * Extracts video frames for SWAP keyframe painting and imports ComfyUI outputs into
    `input/h3_refs/` (+ optional Reference Bible update).
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import threading
import time
from typing import Any

import folder_paths
import nodes

from . import media as _media
from . import mv_solver as _mv_solver
from . import songmap as _songmap

TAG = "HandTieClips-Studio"

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_SONGMAP_CACHE: dict[tuple[str, float, bool], dict[str, Any]] = {}
_CACHE_LOCK = threading.Lock()
_SONGMAP_CACHE_MAX = 16
_PROGRESS_LOCK = threading.Lock()
_SONGMAP_PROGRESS: dict[str, dict[str, Any]] = {}
_SONGMAP_INFLIGHT: dict[tuple[str, float, bool], threading.Event] = {}

ASPECT_DIMENSIONS: dict[str, dict[str, tuple[int, int]]] = {
    "qwen": {
        "16:9": (1344, 768),
        "9:16": (768, 1344),
        "1:1": (1024, 1024),
        "4:3": (1152, 896),
        "3:4": (896, 1152),
    },
    "moss": {
        "16:9": (1344, 768),
        "9:16": (768, 1344),
        "1:1": (1024, 1024),
        "4:3": (1184, 896),
        "3:4": (896, 1184),
    },
    "h3_4mp": {
        "16:9": (2720, 1536),
        "9:16": (1536, 2720),
        "1:1": (2048, 2048),
        "4:3": (2368, 1760),
        "3:4": (1760, 2368),
    },
}

IMAGE_PROFILE_ORDER = (
    "qwen_viggle_6step",
    "qwen_turbo_8step",
    "qwen_unlocked_6step",
    "qwen_base_25step",
    "moss_5gb",
    "pk_h3_image_edit",
    "minimax_h3_image",
    "minimax_h3_image_pdmd",
    "minimax_h3_image_swap",
    "ph3_image",
    "ph3_image_pdmd",
)

SECTION_KINDS = (
    "intro",
    "verse",
    "pre_chorus",
    "chorus",
    "bridge",
    "drop",
    "instrumental",
    "outro",
)


def _norm(name: str) -> str:
    return str(name or "").replace("\\", "/").strip().lower()


def _pick_first(available: list[str], patterns: tuple[str, ...]) -> str:
    """Return the first available filename matching an ordered tuple of substrings/regexes."""
    if not available:
        return ""
    normed = [(f, _norm(f)) for f in available]
    for pat in patterns:
        p_low = pat.lower()
        for orig, low in normed:
            if p_low == low or p_low == os.path.basename(low):
                return orig
        for orig, low in normed:
            if p_low in low:
                return orig
    return ""


def _safe_list(folder: str) -> list[str]:
    try:
        return list(folder_paths.get_filename_list(folder) or [])
    except Exception:
        return []


def _node_mappings() -> dict[str, Any]:
    return dict(getattr(nodes, "NODE_CLASS_MAPPINGS", {}) or {})


def _resolve_dims(
    family: str,
    aspect: str,
    width: int = 0,
    height: int = 0,
    step: int = 32,
    megapixels: float = 0.0,
) -> tuple[int, int]:
    import math

    if width > 0 and height > 0:
        w = max(step, round(int(width) / step) * step)
        h = max(step, round(int(height) / step) * step)
        return w, h
    table = ASPECT_DIMENSIONS.get(family, ASPECT_DIMENSIONS["qwen"])
    key = str(aspect or "16:9").split()[0].strip()
    bw, bh = table.get(key, table["16:9"])
    mp = float(megapixels or 0.0)
    if mp > 0.0 and bw > 0 and bh > 0:
        scale = math.sqrt((mp * 1_000_000.0) / float(bw * bh))
        w = max(step, round((bw * scale) / step) * step)
        h = max(step, round((bh * scale) / step) * step)
        return w, h
    return bw, bh


def _clip_types() -> set[str]:
    mappings = _node_mappings()
    cls = mappings.get("CLIPLoader")
    if cls is None:
        return set()
    try:
        spec = cls.INPUT_TYPES()
        t_field = (spec.get("required") or {}).get("type")
        if isinstance(t_field, (list, tuple)) and t_field and isinstance(t_field[0], (list, tuple)):
            return {str(x) for x in t_field[0]}
    except Exception:
        pass
    return set()


def _detect_image_profiles() -> list[dict[str, Any]]:
    dm = _safe_list("diffusion_models")
    loras = _safe_list("loras")
    te = _safe_list("text_encoders")
    vaes = _safe_list("vae")
    mappings = _node_mappings()
    ctypes = _clip_types()

    has_qwen_node = "TextEncodeQwenImage21" in mappings
    qwen_te = _pick_first(te, (
        "qwen3vl_8b_int8_convrot.safetensors",
        "qwen3-vl-8b-int8_convrot_simple.safetensors",
        "qwen3-vl-8b-int8_convrot",
        "qwen3vl_8b",
        "qwen3-vl-8b",
    ))
    qwen_unlocked_te = _pick_first(te, (
        "qwen3-vl-8b-int8_convrot_simple.safetensors",
        "qwen3vl_8b_int8_convrot.safetensors",
        "qwen3-vl-8b-int8_convrot",
        "qwen3vl_8b",
        "qwen3-vl-8b",
    ))
    qwen_vae = _pick_first(vaes, (
        "texture_fix_vae_for_qwen_image_2.1_bf16.safetensors",
        "qwen_image_2.1_vae_bf16.safetensors",
        "qwen_image_vae.safetensors",
    ))
    viggle_lora = _pick_first(loras, (
        "Qwen-Image-2.1-viggle-turbo-v0.3-6step-lora-r128.safetensors",
        "viggle-turbo",
        "qwen-image-2.1-viggle",
    ))
    qwen_8step_lora = _pick_first(loras, (
        "p_qwen_image_2.1_8step_v0.1.safetensors",
        "qwen_image_2.1_8step",
    ))

    qwen_turbo_unet = _pick_first(dm, (
        "qwen_image_2.1_turbo_int8_convrot.safetensors",
        "qwen_image_2.1_turbo_bf16.safetensors",
    ))
    qwen_base_unet = _pick_first(dm, (
        "qwen_image_2.1_int8_convrot.safetensors",
        "qwen_image_2.1_bf16.safetensors",
    ))
    qwen_unlocked_unet = _pick_first(dm, (
        "redgptK2T2W6A8REDQW21_redqw21UNLOCKEDV2_int8.safetensors",
        "redqw21unlocked",
        "unlocked",
    ))

    moss_unet = _pick_first(dm, (
        "moss_image_sft_int8_convrot.safetensors",
        "moss_image_base_int8_convrot.safetensors",
        "kromoss_int8_convrot.safetensors",
    ))
    moss_te = _pick_first(te, (
        "qwen3.5_9b_abliterated_int8_convrot.safetensors",
        "qwen3.5_9b_moss_image_sft_w4a8_gptq.safetensors",
        "qwen3.5_9b",
    ))
    moss_vae = _pick_first(vaes, (
        "flux2-vae.safetensors",
        "moss_image_vae_bf16.safetensors",
        "flux2-vae_small.safetensors",
    ))
    moss_lora = _pick_first(loras, (
        "moss_image_dmd/lora.safetensors",
        "moss_image_dmd",
    ))

    h3_img_unet = _pick_first(dm, (
        "minimax_h3_image_pruned_int8_convrot.safetensors",
        "minimax_h3_image_pruned_fp8_scaled.safetensors",
        "minimax_h3_image_pruned_w4a8.safetensors",
        "minimax_h3_image_pruned_nvfp4.safetensors",
        "minimax_h3_image_pruned_bf16.safetensors",
        "minimax_h3_image",
    ))
    h3_32b_te = _pick_first(te, (
        "qwen3vl_32b_minimax_h3_int8_convrot.safetensors",
        "qwen3vl_32b_minimax_h3_native_w6g16",
        "qwen3vl_32b_minimax_h3_native_w4w6",
        "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
        "qwen3vl_32b_minimax_h3",
    ))
    h3_img_vae = _pick_first(vaes, (
        "minimax_h3_image_vae_fp16.safetensors",
        "minimax_h3_image_vae",
    ))
    h3_pdmd_lora = _pick_first(loras, (
        "minimax_h3_pdmd_2nfe_comfyui.safetensors",
        "minimax_h3_pdmd_2nfe",
    ))
    h3_swap_lora = _pick_first(loras, (
        "h3_character_swap_v1.5.safetensors",
        "character_swap",
    ))

    pk_unet = _pick_first(dm, (
        "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
    ))
    pk_enc_vae = _pick_first(vaes, (
        "minimax_h3_lynnreal_light_vae_int8_convrot.safetensors",
        "p-h3-image_vae_int8_convrot.safetensors",
        "p-h3-image_vae_bf16.safetensors",
    ))

    ph3_unet = _pick_first(dm, (
        "p-h3-image_int8_convrot.safetensors",
        "p-h3-image_w4a8.safetensors",
        "p-h3-image_bf16.safetensors",
    ))
    ph3_lora = _pick_first(loras, ("p-h3-image_lora_bf16.safetensors", "p-h3-image_lora"))
    fl2va_unet = _pick_first(dm, ("minimax_h3_fl2va_pruned_int8_convrot.safetensors", "minimax_h3_fl2va"))
    ph3_te = _pick_first(te, (
        "p-h3-image_text_encoder_int8_convrot.safetensors",
        "p-h3-image_text_encoder_w4a8.safetensors",
        "p-h3-image_text_encoder_bf16.safetensors",
    ))
    ph3_vae = _pick_first(vaes, (
        "p-h3-image_vae_int8_convrot.safetensors",
        "p-h3-image_vae_bf16.safetensors",
    ))

    profiles: list[dict[str, Any]] = []

    def add_profile(
        pid: str,
        label: str,
        *,
        ready: bool,
        supports_edit: bool,
        steps: int,
        cfg: float,
        sampler: str,
        scheduler: str,
        family: str,
        unet: str,
        lora: str = "",
        clip: str = "",
        clip_type: str = "",
        vae: str = "",
        encode_vae: str = "",
        sigma_shift: float | None = None,
        sigma_shift_audio: float = 1.0,
        lora_bypass: bool = False,
        adaln_fix: bool = False,
        cache_dtype: str = "default",
        default_mp: float = 0.0,
        missing: list[str] | None = None,
        note: str = "",
    ) -> None:
        profiles.append({
            "id": pid,
            "label": label,
            "ready": bool(ready),
            "supports_edit": bool(supports_edit),
            "steps": steps,
            "cfg": cfg,
            "sampler": sampler,
            "scheduler": scheduler,
            "family": family,
            "cache_dtype": cache_dtype,
            "default_mp": float(default_mp),
            "sigma_shift": sigma_shift,
            "sigma_shift_audio": float(sigma_shift_audio),
            "lora_bypass": bool(lora_bypass),
            "adaln_fix": bool(adaln_fix),
            "files": {
                "unet": unet,
                "lora": lora,
                "clip": clip,
                "clip_type": clip_type,
                "vae": vae,
                "encode_vae": encode_vae or vae,
            },
            "missing": [m for m in (missing or []) if m],
            "note": note,
        })

    q_clip_ok = bool(qwen_te and ("qwen_image" in ctypes or not ctypes))
    qwen_viggle_unet = qwen_base_unet
    add_profile(
        "qwen_viggle_6step",
        "Fast · Qwen 2.1 + Viggle Turbo (6-step)",
        ready=bool(has_qwen_node and qwen_viggle_unet and viggle_lora and q_clip_ok and qwen_vae),
        supports_edit=True,
        steps=6,
        cfg=1.0,
        sampler="euler",
        scheduler="viggle_6step",
        family="qwen",
        unet=qwen_viggle_unet,
        lora=viggle_lora,
        clip=qwen_te,
        clip_type="qwen_image",
        vae=qwen_vae,
        missing=[
            "" if has_qwen_node else "TextEncodeQwenImage21 node",
            "" if qwen_viggle_unet else "qwen_image_2.1_{int8_convrot,bf16} base UNET",
            "" if viggle_lora else "Qwen-Image-2.1-viggle-turbo LoRA",
            "" if qwen_te else "qwen3vl_8b text encoder",
            "" if qwen_vae else "qwen_image_2.1 VAE",
        ],
        note="6-step ~1 MP T2I + multi-ref SWAP keyframe & sheet extractor (unmerged LoRA + shifted sigmas).",
    )

    add_profile(
        "qwen_turbo_8step",
        "Fast · Qwen 2.1 Turbo (8-step)",
        ready=bool(has_qwen_node and qwen_turbo_unet and q_clip_ok and qwen_vae),
        supports_edit=True,
        steps=8,
        cfg=1.0,
        sampler="euler",
        scheduler="qwen_turbo_8step",
        family="qwen",
        unet=qwen_turbo_unet,
        clip=qwen_te,
        clip_type="qwen_image",
        vae=qwen_vae,
        missing=[
            "" if has_qwen_node else "TextEncodeQwenImage21 node",
            "" if qwen_turbo_unet else "qwen_image_2.1_turbo_{int8_convrot,bf16} UNET",
            "" if qwen_te else "qwen3vl_8b text encoder",
            "" if qwen_vae else "qwen_image_2.1 VAE",
        ],
        note="Official 8-step Qwen 2.1 Turbo (~17 GB int8, crisp single-angle extraction & edits).",
    )

    unl_te = qwen_unlocked_te or qwen_te
    unl_clip_ok = bool(unl_te and ("qwen_image" in ctypes or not ctypes))
    add_profile(
        "qwen_unlocked_6step",
        "Unlocked · RedQW2.1 (12-step, CFG 2, 3–4 MP)",
        ready=bool(has_qwen_node and qwen_unlocked_unet and unl_clip_ok and qwen_vae),
        supports_edit=True,
        steps=12,
        cfg=2.0,
        sampler="euler",
        scheduler="linear_quadratic",
        family="qwen",
        unet=qwen_unlocked_unet,
        lora="",
        clip=unl_te,
        clip_type="qwen_image",
        vae=qwen_vae,
        cache_dtype="int8",
        default_mp=3.0,
        missing=[
            "" if has_qwen_node else "TextEncodeQwenImage21 node",
            "" if qwen_unlocked_unet else "redgptK2T2W6A8REDQW21_redqw21UNLOCKEDV2_int8.safetensors UNET",
            "" if unl_te else "qwen3-vl-8b-int8_convrot_simple.safetensors text encoder",
            "" if qwen_vae else "qwen_image_2.1 VAE",
        ],
        note="RedQW2.1 Unlocked V2: 12-step euler / linear_quadratic, CFG 2.0, int8 KV cache, 3–4 MP ready.",
    )

    add_profile(
        "qwen_base_25step",
        "Quality · Qwen 2.1 Base (25-step)",
        ready=bool(has_qwen_node and qwen_base_unet and q_clip_ok and qwen_vae),
        supports_edit=True,
        steps=25,
        cfg=1.0,
        sampler="euler",
        scheduler="simple",
        family="qwen",
        unet=qwen_base_unet,
        clip=qwen_te,
        clip_type="qwen_image",
        vae=qwen_vae,
        missing=[
            "" if qwen_base_unet else "qwen_image_2.1 base UNET",
            "" if qwen_te else "qwen3vl_8b text encoder",
            "" if qwen_vae else "qwen_image_2.1 VAE",
        ],
        note="Full 25-step Qwen 2.1 for cleanest fine detail without turbo distortion.",
    )

    has_moss_latent = "EmptyFlux2LatentImage" in mappings
    moss_clip_ok = bool(moss_te and ("moss_image" in ctypes or not ctypes))
    moss_steps = 8 if moss_lora else 24
    moss_cfg = 1.0 if moss_lora else 3.0
    add_profile(
        "moss_5gb",
        f"Light · MOSS Image 5 GB ({moss_steps}-step)",
        ready=bool(moss_unet and moss_clip_ok and moss_vae and has_moss_latent),
        supports_edit=False,
        steps=moss_steps,
        cfg=moss_cfg,
        sampler="euler",
        scheduler="simple",
        family="moss",
        unet=moss_unet,
        lora=moss_lora,
        clip=moss_te,
        clip_type="moss_image",
        vae=moss_vae,
        missing=[
            "" if moss_unet else "moss_image UNET",
            "" if moss_te else "qwen3.5_9b text encoder",
            "" if moss_vae else "flux2/moss VAE",
        ],
        note="Ultra-fast 5 GB T2I layout drafter.",
    )

    has_ph3_node = "PH3ImageConditioning" in mappings
    has_h3_img_node = "MiniMaxH3ImageConditioning" in mappings

    add_profile(
        "pk_h3_image_edit",
        "Unlocked · PlagueKind H3-ImageEdit (10-step, 4–8 MP)",
        ready=bool(has_ph3_node and pk_unet and ph3_lora and h3_32b_te and pk_enc_vae and ph3_vae),
        supports_edit=True,
        steps=10,
        cfg=1.0,
        sampler="euler",
        scheduler="linear_quadratic",
        family="h3_4mp",
        unet=pk_unet,
        lora=ph3_lora,
        clip=h3_32b_te,
        clip_type="minimax",
        vae=ph3_vae,
        encode_vae=pk_enc_vae,
        sigma_shift=12.0,
        sigma_shift_audio=1.0,
        lora_bypass=True,
        adaln_fix=True,
        missing=[
            "" if has_ph3_node else "PH3ImageConditioning node",
            "" if pk_unet else "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
            "" if ph3_lora else "p-h3-image_lora_bf16.safetensors",
            "" if h3_32b_te else "qwen3vl_32b_minimax_h3 text encoder",
            "" if pk_enc_vae else "minimax_h3_lynnreal_light_vae_int8_convrot.safetensors",
            "" if ph3_vae else "p-h3-image_vae_int8_convrot.safetensors",
        ],
        note="H3 image/edit: fl2va DiT + P-H3 LoRA + lynnreal encode / P-H3 decode.",
    )

    add_profile(
        "minimax_h3_image",
        "Hero · MiniMax-H3-Image (6-step 4–16 MP)",
        ready=bool(has_h3_img_node and h3_img_unet and h3_32b_te and h3_img_vae),
        supports_edit=True,
        steps=6,
        cfg=1.0,
        sampler="euler",
        scheduler="simple",
        family="h3_4mp",
        unet=h3_img_unet,
        clip=h3_32b_te,
        clip_type="minimax",
        vae=h3_img_vae,
        missing=[
            "" if has_h3_img_node else "Update ComfyUI (2026-11-10+) for MiniMaxH3ImageConditioning",
            "" if h3_img_unet else "minimax_h3_image_pruned_{int8_convrot,fp8_scaled,w4a8}.safetensors",
            "" if h3_img_vae else "minimax_h3_image_vae_fp16.safetensors",
            "" if h3_32b_te else "qwen3vl_32b_minimax_h3 text encoder",
        ],
        note="Official 6-step MiniMax-H3-Image (~28–31 GB VRAM; matches H3 Ref2VA natively).",
    )

    add_profile(
        "minimax_h3_image_pdmd",
        "Fast · MiniMax-H3-Image pDMD (4-step)",
        ready=bool(has_h3_img_node and h3_img_unet and h3_pdmd_lora and h3_32b_te and h3_img_vae),
        supports_edit=True,
        steps=4,
        cfg=1.0,
        sampler="euler",
        scheduler="simple",
        family="h3_4mp",
        unet=h3_img_unet,
        lora=h3_pdmd_lora,
        clip=h3_32b_te,
        clip_type="minimax",
        vae=h3_img_vae,
        sigma_shift=12.0,
        sigma_shift_audio=3.0,
        missing=[
            "" if has_h3_img_node else "Update ComfyUI (2026-11-10+) for MiniMaxH3ImageConditioning",
            "" if h3_img_unet else "minimax_h3_image_pruned_int8_convrot.safetensors",
            "" if h3_pdmd_lora else "minimax_h3_pdmd_2nfe_comfyui.safetensors",
            "" if h3_img_vae else "minimax_h3_image_vae_fp16.safetensors",
            "" if h3_32b_te else "qwen3vl_32b_minimax_h3 text encoder",
        ],
        note="MiniMax-H3-Image + pDMD 2-NFE LoRA (4 steps = baseline quality at ~1.5-2x speed, shift 12).",
    )

    add_profile(
        "minimax_h3_image_swap",
        "Swap · MiniMax-H3-Image Character Swap (6-step)",
        ready=bool(has_h3_img_node and h3_img_unet and h3_swap_lora and h3_32b_te and h3_img_vae),
        supports_edit=True,
        steps=6,
        cfg=1.0,
        sampler="euler",
        scheduler="simple",
        family="h3_4mp",
        unet=h3_img_unet,
        lora=h3_swap_lora,
        clip=h3_32b_te,
        clip_type="minimax",
        vae=h3_img_vae,
        missing=[
            "" if has_h3_img_node else "Update ComfyUI (2026-11-10+) for MiniMaxH3ImageConditioning",
            "" if h3_img_unet else "minimax_h3_image_pruned_int8_convrot.safetensors",
            "" if h3_swap_lora else "h3_character_swap_v1.5.safetensors (155 MB)",
            "" if h3_img_vae else "minimax_h3_image_vae_fp16.safetensors",
            "" if h3_32b_te else "qwen3vl_32b_minimax_h3 text encoder",
        ],
        note="MiniMax-H3-Image + akatz Character Swap v1.5 LoRA (holds skin tone, pose & cross-style faces).",
    )

    ph3_ready = bool(
        has_ph3_node
        and ph3_te
        and ph3_vae
        and (ph3_unet or (fl2va_unet and ph3_lora))
    )
    add_profile(
        "ph3_image",
        "Pruna · P-H3-Image (8-step 4–8 MP)",
        ready=ph3_ready,
        supports_edit=True,
        steps=8,
        cfg=1.0,
        sampler="euler",
        scheduler="ph3_8step",
        family="h3_4mp",
        unet=ph3_unet or fl2va_unet,
        lora="" if ph3_unet else ph3_lora,
        clip=ph3_te,
        clip_type="minimax",
        vae=ph3_vae,
        sigma_shift=1.0,
        sigma_shift_audio=1.0,
        lora_bypass=not bool(ph3_unet),
        missing=[
            "" if has_ph3_node else "PH3ImageConditioning node",
            "" if (ph3_unet or (fl2va_unet and ph3_lora)) else "p-h3-image_int8_convrot.safetensors (or p-h3-image_lora_bf16)",
            "" if ph3_te else "p-h3-image_text_encoder_int8_convrot.safetensors",
            "" if ph3_vae else "p-h3-image_vae_int8_convrot.safetensors",
        ],
        note="Pruna 8-step 4–8 MP T2I/edit with official 8-step ManualSigmas & 4B encoder.",
    )

    add_profile(
        "ph3_image_pdmd",
        "Fast · P-H3-Image pDMD (4-step)",
        ready=bool(has_ph3_node and ph3_unet and h3_pdmd_lora and ph3_te and ph3_vae),
        supports_edit=True,
        steps=4,
        cfg=1.0,
        sampler="euler",
        scheduler="simple",
        family="h3_4mp",
        unet=ph3_unet,
        lora=h3_pdmd_lora,
        clip=ph3_te,
        clip_type="minimax",
        vae=ph3_vae,
        sigma_shift=12.0,
        sigma_shift_audio=1.0,
        lora_bypass=True,
        missing=[
            "" if has_ph3_node else "PH3ImageConditioning node",
            "" if ph3_unet else "p-h3-image_int8_convrot.safetensors",
            "" if h3_pdmd_lora else "minimax_h3_pdmd_2nfe_comfyui.safetensors",
            "" if ph3_te else "p-h3-image_text_encoder_int8_convrot.safetensors",
            "" if ph3_vae else "p-h3-image_vae_int8_convrot.safetensors",
        ],
        note="Pruna P-H3-Image + pDMD 2-NFE LoRA (4 steps at baseline quality, shift 12).",
    )

    return profiles


def _detect_song_engines() -> list[dict[str, Any]]:
    mappings = _node_mappings()
    ckpts = _safe_list("checkpoints")
    aud_enc = _safe_list("audio_encoders")
    yue2_ckpt = _pick_first(ckpts, (
        "yue2_3b_int8_convrot.safetensors",
        "yue2_3b_bf16.safetensors",
        "yue2",
    ))
    sheetsage2 = _pick_first(aud_enc, ("sheetsage2_bf16.safetensors", "sheetsage2"))

    has_pytraveler = "YuE2GenerateSong" in mappings
    has_core = all(k in mappings for k in ("YuE2GenerateABC", "YuE2GenerateMusic", "EmptyYuE2LatentAudio"))

    return [
        {
            "id": "yue2_pytraveler",
            "label": "YuE2-ComfyUI (pytraveler · Stems & Track Edit)",
            "ready": bool(has_pytraveler and (yue2_ckpt or _pick_first(ckpts, ("yue2",)))),
            "installed_nodes": has_pytraveler,
            "has_vocals_only": "YuE2VocalsOnly" in mappings,
            "has_edit_track": "YuE2EditTrack" in mappings,
            "checkpoint": yue2_ckpt,
            "missing": [
                "" if has_pytraveler else "Install pytraveler/YuE2-ComfyUI in custom_nodes/",
                "" if yue2_ckpt else "Place yue2_3b_int8_convrot.safetensors (3.69 GB) in models/checkpoints/",
            ],
        },
        {
            "id": "yue2_core",
            "label": "ComfyUI Core YuE2 (Built-In Nodes)",
            "ready": bool(has_core and yue2_ckpt),
            "installed_nodes": has_core,
            "has_sheetsage2": bool("SheetSage2AudioToABC" in mappings and sheetsage2),
            "checkpoint": yue2_ckpt,
            "missing": [
                "" if has_core else "ComfyUI YuE2 core nodes",
                "" if yue2_ckpt else "Place yue2_3b_int8_convrot.safetensors (3.69 GB) in models/checkpoints/",
            ],
        },
    ]


def _detect_h3_vaes() -> dict[str, str]:
    vaes = _safe_list("vae")
    video = _pick_first(vaes, (
        "minimax_h3_video_vae_fp16.safetensors",
        "minimax_h3_video_vae_int8_convrot.safetensors",
        "minimax_h3_sol_vae_fp16.safetensors",
        "minimax_h3_lynnreal_light_vae_int8_convrot.safetensors",
        "minimax_h3_video_vae",
    ))
    audio = _pick_first(vaes, (
        "minimax_h3_audio_vae_fp32.safetensors",
        "minimax_h3_audio_vae",
    ))
    return {"video": video, "audio": audio}


def capabilities() -> dict[str, Any]:
    """Inspect installed image & song engines + available audio files in `h3_refs/`."""
    img_profiles = _detect_image_profiles()
    song_engines = _detect_song_engines()
    default_img = next((p["id"] for p in img_profiles if p["ready"]), img_profiles[0]["id"])
    default_song = next((s["id"] for s in song_engines if s["ready"]), song_engines[0]["id"])
    h3_vaes = _detect_h3_vaes()

    audio_files = [f["name"] for f in _media.listing({"audio"})]
    video_files = [f["name"] for f in _media.listing({"video"})]
    image_files = [f["name"] for f in _media.listing({"image"})]

    return {
        "ok": True,
        "image_profiles": img_profiles,
        "default_image_profile": default_img,
        "song_engines": song_engines,
        "default_song_engine": default_song,
        "h3_vaes": h3_vaes,
        "media": {
            "audio": audio_files,
            "video": video_files,
            "image": image_files,
        },
        "section_kinds": list(SECTION_KINDS),
    }


def _find_profile(profile_id: str) -> dict[str, Any]:
    profiles = _detect_image_profiles()
    for p in profiles:
        if p["id"] == profile_id:
            return p
    ready = next((p for p in profiles if p["ready"]), None)
    if ready:
        return ready
    return profiles[0]


def _stage_ref_for_load_image(filename: str) -> str:
    """Resolve `filename` in `input/h3_refs/` (or `input/`) for ComfyUI LoadImage."""
    clean = str(filename or "").strip()
    if not clean:
        return ""
    # Prefer direct `h3_refs/<file>` (LoadImage.VALIDATE_INPUTS calls exists_annotated_filepath)
    if _media.resolve(clean, kinds={"image"}):
        return f"h3_refs/{os.path.basename(clean)}"
    inp = folder_paths.get_input_directory()
    cand = os.path.abspath(os.path.join(inp, os.path.basename(clean)))
    if folder_paths.is_within_directory(inp, cand) and os.path.isfile(cand):
        return os.path.basename(clean)
    raise FileNotFoundError(f"Reference image '{clean}' not found in input/h3_refs/ or input/.")


def _probe_staged_size(rpath: str) -> tuple[int, int] | None:
    """Return `(width, height)` for a staged LoadImage path like `h3_refs/foo.png`."""
    clean = str(rpath or "").strip().replace("\\", "/")
    if not clean:
        return None
    if clean.startswith("h3_refs/"):
        sz = _media.probe_size(clean[len("h3_refs/"):])
        if sz:
            return int(sz[0]), int(sz[1])
    inp = folder_paths.get_input_directory()
    cand = os.path.abspath(os.path.join(inp, *clean.split("/")))
    if folder_paths.is_within_directory(inp, cand) and os.path.isfile(cand):
        try:
            from PIL import Image
            with Image.open(cand) as im:
                return int(im.width), int(im.height)
        except Exception:
            return None
    return None


def _viggle_sigmas_str(w: int, h: int, steps: int = 6) -> str:
    """Exact resolution-dependent FlowMatch sigmas for Viggle Turbo."""
    import math
    tokens = max(256, (max(32, int(h)) // 16) * (max(32, int(w)) // 16))
    mu = 0.5 + (0.9 - 0.5) * (tokens - 256) / (8192 - 256)
    base_nodes = [1.0, 0.9375, 0.875, 0.75, 0.5, 0.25]
    if int(steps) == 5:
        base_nodes = [1.0, 0.875, 0.75, 0.5, 0.25]
    elif int(steps) >= 7:
        base_nodes = [1.0, 0.9583, 0.9167, 0.875, 0.75, 0.5, 0.25]
    sigmas = [math.exp(mu) / (math.exp(mu) + (1.0 / tv - 1.0)) for tv in base_nodes] + [0.0]
    return ", ".join(f"{s:.6f}" for s in sigmas)


_QWEN_TURBO_8STEP_SIGMAS = "1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0.0"
_PH3_8STEP_SIGMAS = "1.0, 0.984753, 0.967905, 0.951688, 0.925372, 0.881923, 0.810083, 0.528718, 0.0"


def _normalize_ref_tokens(prompt_text: str, family: str) -> str:
    txt = str(prompt_text or "").strip()
    if family == "qwen":
        txt = re.sub(r"<\s*Picture\s+(\d+)\s*>", r"<image\1>", txt, flags=re.IGNORECASE)
    elif family == "h3_4mp":
        txt = re.sub(r"<\s*image\s*(\d+)\s*>", r"<Picture \1>", txt, flags=re.IGNORECASE)
    return txt


def build_image_graph(
    *,
    profile_id: str = "",
    prompt: str = "",
    negative_prompt: str = "",
    ref_files: list[str] | tuple[str, ...] = (),
    aspect: str = "16:9",
    width: int = 0,
    height: int = 0,
    megapixels: float = 0.0,
    seed: int = 0,
    steps: int = 0,
    filename_prefix: str = "mv_forge/asset",
) -> dict[str, Any]:
    """Construct a ComfyUI API `/prompt` graph for the requested image profile."""
    import math

    prof = _find_profile(profile_id)
    if not prof["ready"]:
        miss = ", ".join(prof["missing"]) or "required weights missing"
        raise ValueError(f"Image profile '{prof['label']}' is not ready: {miss}")

    txt = _normalize_ref_tokens(prompt, prof["family"])
    if not txt:
        raise ValueError("Image Forge prompt is empty.")

    files = prof["files"]
    use_seed = int(seed) if int(seed or 0) > 0 else int(time.time() * 1000) % 2147483647
    use_steps = int(steps) if int(steps or 0) > 0 else int(prof["steps"])
    cfg = float(prof["cfg"])
    refs = [_stage_ref_for_load_image(f) for f in (ref_files or ()) if str(f or "").strip()]

    if refs and not prof["supports_edit"]:
        raise ValueError(f"Profile '{prof['label']}' is text-to-image only; pick Qwen 2.1 or H3-Image for multi-ref edits.")

    graph: dict[str, Any] = {}
    nid = 1

    def add_node(class_type: str, inputs: dict[str, Any]) -> str:
        nonlocal nid
        key = str(nid)
        nid += 1
        graph[key] = {"class_type": class_type, "inputs": inputs}
        return key

    unet_id = add_node("UNETLoader", {"unet_name": files["unet"], "weight_dtype": "default"})
    model_ref: list[Any] = [unet_id, 0]
    mappings = _node_mappings()
    lora_name = str(files.get("lora") or "")
    if lora_name:
        if "viggle" in lora_name.lower() and "HTCQwenViggleLora" in mappings:
            lora_id = add_node("HTCQwenViggleLora", {
                "model": model_ref,
                "lora_name": lora_name,
                "strength": 1.0,
            })
        elif prof.get("lora_bypass") and "LoraLoaderBypassModelOnly" in mappings:
            lora_id = add_node("LoraLoaderBypassModelOnly", {
                "model": model_ref,
                "lora_name": lora_name,
                "strength_model": 1.0,
            })
        else:
            lora_id = add_node("LoraLoaderModelOnly", {
                "model": model_ref,
                "lora_name": lora_name,
                "strength_model": 1.0,
            })
        model_ref = [lora_id, 0]

    if prof.get("adaln_fix"):
        if "HTCAdaLNFix" in mappings:
            fix_id = add_node("HTCAdaLNFix", {"model": model_ref, "mode": "port"})
            model_ref = [fix_id, 0]
        elif "H3AdaLNLoRAFix" in mappings:
            fix_id = add_node("H3AdaLNLoRAFix", {"model": model_ref, "mode": "port"})
            model_ref = [fix_id, 0]

    if prof.get("sigma_shift") is not None and "MiniMaxH3SigmaShift" in mappings:
        sh_id = add_node("MiniMaxH3SigmaShift", {
            "model": model_ref,
            "shift_video": float(prof["sigma_shift"]),
            "shift_audio": float(prof.get("sigma_shift_audio") or 1.0),
        })
        model_ref = [sh_id, 0]

    clip_id = add_node("CLIPLoader", {
        "clip_name": files["clip"],
        "type": files["clip_type"],
        "device": "default",
    })
    vae_id = add_node("VAELoader", {"vae_name": files["vae"]})
    enc_vae_name = str(files.get("encode_vae") or files["vae"])
    enc_vae_id = vae_id if enc_vae_name == files["vae"] else add_node("VAELoader", {"vae_name": enc_vae_name})

    asp_clean = str(aspect or "").strip().lower()
    explicit_mp = float(megapixels or 0.0)
    use_mp = explicit_mp or float(prof.get("default_mp") or 0.0)
    match_ref_size = bool(refs and int(width or 0) <= 0 and int(height or 0) <= 0 and asp_clean in ("match", ""))
    dim_step = 16 if prof["family"] == "moss" else 32
    w, h = _resolve_dims(
        prof["family"],
        "16:9" if asp_clean in ("match", "") else aspect,
        width,
        height,
        step=dim_step,
        megapixels=use_mp,
    )
    if match_ref_size and prof["family"] in ("qwen", "moss", "h3_4mp"):
        sz = _probe_staged_size(refs[0])
        if sz and sz[0] > 0 and sz[1] > 0:
            ratio = sz[0] / sz[1]
            default_px = 4_000_000.0 if prof["family"] == "h3_4mp" else 1024.0 * 1024.0
            target_px = max(256 * 256, use_mp * 1_000_000.0) if use_mp > 0 else default_px
            w = max(dim_step, round(math.sqrt(target_px * ratio) / dim_step) * dim_step)
            h = max(dim_step, round(math.sqrt(target_px / ratio) / dim_step) * dim_step)

    if prof["family"] == "qwen":
        actual_mp = (w * h) / 1_000_000.0
        cache_dtype = str(prof.get("cache_dtype") or ("int8" if actual_mp >= 1.9 else "default"))
        if "QwenImage21Cache" in mappings and refs:
            cache_id = add_node("QwenImage21Cache", {
                "model": model_ref,
                "device": "auto",
                "dtype": cache_dtype,
            })
            model_ref = [cache_id, 0]
        enc_res = 1024
        if actual_mp > 1.3:
            enc_res = max(1024, min(2048, round(math.sqrt(actual_mp * 1_000_000.0) / 32) * 32))
        enc_inputs: dict[str, Any] = {
            "clip": [clip_id, 0],
            "prompt": txt,
            "negative_prompt": str(negative_prompt or "").strip(),
            "resolution": enc_res,
        }
        if refs:
            enc_inputs["vae"] = [vae_id, 0]
            for idx, rpath in enumerate(refs[:9], 1):
                ld_id = add_node("LoadImage", {"image": rpath})
                enc_inputs[f"images.image_{idx}"] = [ld_id, 0]
        enc_id = add_node("TextEncodeQwenImage21", enc_inputs)
        if match_ref_size and explicit_mp <= 0.0 and use_mp <= 0.0:
            latent_ref: list[Any] = [enc_id, 2]
        else:
            lat_id = add_node("EmptyLatentImage", {"width": w, "height": h, "batch_size": 1})
            latent_ref = [lat_id, 0]
        pos_ref = [enc_id, 0]
        neg_ref = [enc_id, 1]

    elif prof["family"] == "moss":
        pos_id = add_node("CLIPTextEncode", {"clip": [clip_id, 0], "text": txt})
        neg_id = add_node("CLIPTextEncode", {
            "clip": [clip_id, 0],
            "text": str(negative_prompt or "").strip() or "blurry, flat colors, poor anatomy, watermark",
        })
        lat_id = add_node("EmptyFlux2LatentImage", {"width": w, "height": h, "batch_size": 1})
        pos_ref = [pos_id, 0]
        neg_ref = [neg_id, 0]
        latent_ref = [lat_id, 0]

    else:
        is_official_h3 = prof["id"] in ("minimax_h3_image", "minimax_h3_image_pdmd", "minimax_h3_image_swap")
        cond_node = "MiniMaxH3ImageConditioning" if is_official_h3 else "PH3ImageConditioning"
        explicit_size = not (match_ref_size and use_mp <= 0.0)
        cond_inputs: dict[str, Any] = {
            "clip": [clip_id, 0],
            "vae": [enc_vae_id, 0],
            "prompt": txt,
            "width": w if explicit_size else 0,
            "height": h if explicit_size else 0,
        }
        for idx, rpath in enumerate(refs[:9], 1):
            ld_id = add_node("LoadImage", {"image": rpath})
            cond_inputs[f"images.image_{idx}"] = [ld_id, 0]
        cond_id = add_node(cond_node, cond_inputs)
        zero_id = add_node("ConditioningZeroOut", {"conditioning": [cond_id, 0]})
        pos_ref = [cond_id, 0]
        neg_ref = [zero_id, 0]
        latent_ref = [cond_id, 1]

    sched = str(prof.get("scheduler") or "simple")
    use_custom_sigmas = (
        sched in ("viggle_6step", "qwen_turbo_8step", "ph3_8step")
        and all(k in mappings for k in ("BasicGuider", "RandomNoise", "KSamplerSelect", "ManualSigmas", "SamplerCustomAdvanced"))
    )
    use_adv_sched = (
        not use_custom_sigmas
        and prof["family"] == "h3_4mp"
        and cfg == 1.0
        and all(k in mappings for k in ("BasicGuider", "RandomNoise", "KSamplerSelect", "BasicScheduler", "SamplerCustomAdvanced"))
        and prof["id"] not in ("minimax_h3_image", "minimax_h3_image_swap")
    )
    if use_custom_sigmas:
        if sched == "qwen_turbo_8step":
            sig_str = _QWEN_TURBO_8STEP_SIGMAS
        elif sched == "ph3_8step":
            sig_str = _PH3_8STEP_SIGMAS
        else:
            sig_str = _viggle_sigmas_str(w, h, use_steps)
        guider_id = add_node("BasicGuider", {"model": model_ref, "conditioning": pos_ref})
        noise_id = add_node("RandomNoise", {"noise_seed": use_seed})
        samp_id = add_node("KSamplerSelect", {"sampler_name": prof["sampler"]})
        sig_id = add_node("ManualSigmas", {"sigmas": sig_str})
        adv_id = add_node("SamplerCustomAdvanced", {
            "noise": [noise_id, 0],
            "guider": [guider_id, 0],
            "sampler": [samp_id, 0],
            "sigmas": [sig_id, 0],
            "latent_image": latent_ref,
        })
        sample_out = [adv_id, 0]
    elif use_adv_sched:
        guider_id = add_node("BasicGuider", {"model": model_ref, "conditioning": pos_ref})
        noise_id = add_node("RandomNoise", {"noise_seed": use_seed})
        samp_id = add_node("KSamplerSelect", {"sampler_name": prof["sampler"]})
        bs_id = add_node("BasicScheduler", {
            "model": model_ref,
            "scheduler": sched,
            "steps": use_steps,
            "denoise": 1.0,
        })
        adv_id = add_node("SamplerCustomAdvanced", {
            "noise": [noise_id, 0],
            "guider": [guider_id, 0],
            "sampler": [samp_id, 0],
            "sigmas": [bs_id, 0],
            "latent_image": latent_ref,
        })
        sample_out = [adv_id, 0]
    else:
        ks_id = add_node("KSampler", {
            "model": model_ref,
            "seed": use_seed,
            "steps": use_steps,
            "cfg": cfg,
            "sampler_name": prof["sampler"],
            "scheduler": "simple" if sched in ("viggle_6step", "qwen_turbo_8step", "ph3_8step") else sched,
            "positive": pos_ref,
            "negative": neg_ref,
            "latent_image": latent_ref,
            "denoise": 1.0,
        })
        sample_out = [ks_id, 0]

    dec_id = add_node("VAEDecode", {"samples": sample_out, "vae": [vae_id, 0]})
    save_id = add_node("SaveImage", {
        "images": [dec_id, 0],
        "filename_prefix": str(filename_prefix or "mv_forge/asset"),
    })

    return {
        "prompt": graph,
        "output_node": save_id,
        "output_kind": "image",
        "profile": prof["id"],
        "seed": use_seed,
        "width": w,
        "height": h,
        "megapixels": round((w * h) / 1_000_000.0, 2),
        "steps": use_steps,
    }


def build_song_graph(
    *,
    engine: str = "",
    style: str = "",
    lyrics: str = "",
    mode: str = "full",
    max_duration: float = 120.0,
    seed: int = 0,
    vocals_only: bool = False,
    filename_prefix: str = "audio/mv_yue2",
) -> dict[str, Any]:
    """Construct a ComfyUI API `/prompt` graph for YuE2 song generation."""
    engines = _detect_song_engines()
    chosen = next((e for e in engines if e["id"] == engine), None)
    if chosen is None or not chosen["ready"]:
        chosen = next((e for e in engines if e["ready"]), None)
    if chosen is None:
        hints = ["; ".join(e["missing"]) for e in engines if e.get("missing")]
        raise ValueError("YuE2 song generation is not configured yet: " + (" | ".join(hints)))

    st_text = str(style or "").strip()
    if not st_text:
        raise ValueError("YuE2 style prompt is empty.")
    ly_text = str(lyrics or "").strip()
    use_seed = int(seed) if int(seed or 0) > 0 else int(time.time() * 1000) % 2147483647
    use_mode = str(mode or "full") if mode in ("full", "melody", "off") else "full"
    dur = max(16.0, min(360.0, float(max_duration or 120.0)))

    graph: dict[str, Any] = {}
    nid = 1

    def add_node(class_type: str, inputs: dict[str, Any]) -> str:
        nonlocal nid
        key = str(nid)
        nid += 1
        graph[key] = {"class_type": class_type, "inputs": inputs}
        return key

    if chosen["id"] == "yue2_pytraveler":
        mappings = _node_mappings()
        gen_inputs: dict[str, Any] = {
            "style": st_text,
            "lyrics": ly_text,
            "seed": use_seed,
        }
        if "YuE2Options" in mappings:
            ckpt_low = str(chosen.get("checkpoint") or "").lower()
            opt_inputs: dict[str, Any] = {
                "cot": use_mode,
                "max_seconds": dur,
                "keep_model_loaded": False,
                "quantization": "int8" if "int8" in ckpt_low else "bf16",
                "download": "auto",
                "vocals_only": bool(vocals_only),
            }
            opt_id = add_node("YuE2Options", opt_inputs)
            gen_inputs["options"] = [opt_id, 0]
        gen_id = add_node("YuE2GenerateSong", gen_inputs)
        audio_ref: list[Any] = [gen_id, 0]
        if vocals_only and "YuE2VocalsOnly" in mappings and "YuE2Options" not in mappings:
            v_id = add_node("YuE2VocalsOnly", {"audio": audio_ref})
            audio_ref = [v_id, 0]
        save_id = add_node("SaveAudio", {
            "audio": audio_ref,
            "filename_prefix": str(filename_prefix or "audio/mv_yue2"),
        })
        return {
            "prompt": graph,
            "output_node": save_id,
            "output_kind": "audio",
            "engine": "yue2_pytraveler",
            "seed": use_seed,
        }

    # ComfyUI Core YuE2 path
    ckpt_id = add_node("CheckpointLoaderSimple", {"ckpt_name": chosen["checkpoint"]})
    abc_ref: Any = ""
    if use_mode != "off":
        abc_id = add_node("YuE2GenerateABC", {
            "clip": [ckpt_id, 1],
            "style": st_text,
            "lyrics": ly_text,
            "seed": use_seed,
            "mode": use_mode if use_mode in ("full", "melody") else "full",
            "max_abc_tokens": 8192,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 30,
            "repetition_penalty": 1.005,
            "penalty_window": 100,
        })
        abc_ref = [abc_id, 0]

    music_id = add_node("YuE2GenerateMusic", {
        "clip": [ckpt_id, 1],
        "style": st_text,
        "lyrics": ly_text,
        "abc": abc_ref,
        "seed": use_seed,
        "mode": use_mode if use_mode in ("full", "melody") else "full",
        "max_duration": dur,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 100,
        "repetition_penalty": 1.2,
    })
    zero_id = add_node("ConditioningZeroOut", {"conditioning": [music_id, 0]})
    lat_id = add_node("EmptyYuE2LatentAudio", {"seconds": [music_id, 1], "batch_size": 1})
    ks_id = add_node("KSampler", {
        "model": [ckpt_id, 0],
        "seed": use_seed,
        "steps": 32,
        "cfg": 1.0,
        "sampler_name": "dpm_2",
        "scheduler": "sgm_uniform",
        "positive": [music_id, 0],
        "negative": [zero_id, 0],
        "latent_image": [lat_id, 0],
        "denoise": 1.0,
    })
    dec_id = add_node("VAEDecodeAudio", {"samples": [ks_id, 0], "vae": [ckpt_id, 2]})
    save_id = add_node("SaveAudio", {
        "audio": [dec_id, 0],
        "filename_prefix": str(filename_prefix or "audio/mv_yue2"),
    })
    return {
        "prompt": graph,
        "output_node": save_id,
        "output_kind": "audio",
        "engine": "yue2_core",
        "seed": use_seed,
    }


def build_refmod_graph(
    *,
    name: str,
    stills: list[str] | tuple[str, ...] = (),
    clip: dict[str, Any] | None = None,
    voice: str = "",
    subfolder: str = "",
    description: str = "",
    layout: str = "separate_pictures",
    role: str = "identity",
    default_step_curve: str = "full",
    subject_mask: str = "off",
    background_retention: float = 0.0,
    background_mode: str = "blur_bg",
    fit_mode: str = "crop",
    crop_margin: float = 0.0,
    max_tokens: int = 0,
) -> dict[str, Any]:
    """Construct a ComfyUI API `/prompt` graph to bake a v5 RefMod via HTCRefModBuilder."""
    import json as _json
    from . import refmod as _refmod

    clean_name = _refmod._clean_name(name)
    if not clean_name:
        raise ValueError("RefMod name is empty.")
    vaes = _detect_h3_vaes()
    if not vaes["video"]:
        raise ValueError("No MiniMax H3 video VAE found in models/vae/.")

    plan_obj: dict[str, Any] = {}
    still_list = [os.path.basename(str(s).strip()) for s in (stills or ()) if str(s or "").strip()]
    if still_list:
        plan_obj["stills"] = [{"file": s} for s in still_list]
    if isinstance(clip, dict) and str(clip.get("file") or "").strip():
        plan_obj["clip"] = {
            "file": os.path.basename(str(clip["file"]).strip()),
            "start": float(clip.get("start") or 0.0),
            "end": float(clip.get("end") or 0.0),
            "frames": int(clip.get("frames") or 0),
        }
    v_clean = os.path.basename(str(voice or "").strip())
    if v_clean:
        plan_obj["voice"] = v_clean
    if not still_list and "clip" not in plan_obj:
        raise ValueError("Add at least one kept still or clip before baking a RefMod.")

    # Validate mod_plan syntax cleanly before queueing
    _refmod.parse_mod_plan(plan_obj)

    graph: dict[str, Any] = {
        "1": {"class_type": "VAELoader", "inputs": {"vae_name": vaes["video"]}},
    }
    b_inputs: dict[str, Any] = {
        "vae": ["1", 0],
        "name": clean_name,
        "mod_plan": _json.dumps(plan_obj, indent=2),
        "max_tokens": max(0, int(max_tokens or 0)),
        "subfolder": str(subfolder or "").strip(),
        "save": True,
        "build": "start",
        "description": str(description or "").strip(),
        "subject_mask": str(subject_mask or "off"),
        "background_retention": float(background_retention or 0.0),
        "layout": str(layout or "separate_pictures"),
        "role": str(role or "identity"),
        "default_step_curve": str(default_step_curve or "full"),
        "fit_mode": str(fit_mode or "crop"),
        "background_mode": str(background_mode or "blur_bg"),
        "crop_margin": float(crop_margin or 0.0),
    }
    if v_clean and vaes.get("audio"):
        graph["2"] = {"class_type": "VAELoader", "inputs": {"vae_name": vaes["audio"]}}
        b_inputs["audio_vae"] = ["2", 0]

    b_id = "3" if "2" in graph else "2"
    graph[b_id] = {"class_type": "HTCRefModBuilder", "inputs": b_inputs}
    full_stem = f"{subfolder.strip().strip('/')}/{clean_name}" if str(subfolder or "").strip() else clean_name
    return {
        "prompt": graph,
        "output_node": b_id,
        "output_kind": "refmod",
        "refmod_name": full_stem,
    }


def _resolve_song_file(song_name: str) -> str:
    clean = str(song_name or "").strip()
    if not clean:
        raise ValueError("Pick or upload an audio file first.")
    p = _media.resolve(clean, kinds={"audio", "video"})
    if p:
        return p
    inp = folder_paths.get_input_directory()
    cand = os.path.abspath(os.path.join(inp, os.path.basename(clean)))
    if folder_paths.is_within_directory(inp, cand) and os.path.isfile(cand):
        return cand
    raise FileNotFoundError(f"Audio file '{clean}' was not found in input/h3_refs/ or input/.")


def _set_songmap_progress(song_key: str, *, running: bool, stage: str, pct: int, device: str = "") -> None:
    now = time.time()
    with _PROGRESS_LOCK:
        prev = _SONGMAP_PROGRESS.get(song_key) or {}
        started = float(prev.get("started_at") or now) if running and prev.get("running") else now
        _SONGMAP_PROGRESS[song_key] = {
            "song": song_key,
            "running": bool(running),
            "stage": str(stage or ""),
            "pct": max(0, min(100, int(pct))),
            "device": str(device or prev.get("device") or ""),
            "started_at": started,
            "elapsed_s": round(max(0.0, now - started), 1),
        }


def song_map_status(song_name: str = "") -> dict[str, Any]:
    key = os.path.basename(str(song_name or "").strip())
    with _PROGRESS_LOCK:
        st = dict(_SONGMAP_PROGRESS.get(key) or {})
        if not st and not key and _SONGMAP_PROGRESS:
            latest = max(_SONGMAP_PROGRESS.values(), key=lambda d: float(d.get("started_at") or 0.0))
            st = dict(latest)
    if not st:
        return {"ok": True, "running": False, "stage": "", "pct": 0, "elapsed_s": 0.0, "device": ""}
    if st.get("running"):
        st["elapsed_s"] = round(max(0.0, time.time() - float(st.get("started_at") or time.time())), 1)
    return {"ok": True, **st}


def _pick_songmap_device(listen: bool) -> tuple[str, int | None]:
    if not listen:
        return "cpu", None
    try:
        import torch  # noqa: PLC0415

        if torch.cuda.is_available():
            free_b, _total_b = torch.cuda.mem_get_info()
            if free_b >= int(4.0 * (1024 ** 3)):
                return "cuda", 8
    except Exception:
        pass
    return "cpu", 8


def _parse_songmap_pct(msg: str, prev_pct: int) -> int:
    m = re.search(r"vocal stem\s+(\d+)/(\d+)", msg)
    if m:
        ci, tot = int(m.group(1)), max(1, int(m.group(2)))
        return max(prev_pct, 12 + round(32 * ci / tot))
    if "whisper load" in msg:
        return max(prev_pct, 46)
    m2 = re.search(r"whisper lyrics\s+(\d+)/(\d+)", msg)
    if m2:
        ci, tot = int(m2.group(1)), max(1, int(m2.group(2)))
        return max(prev_pct, 48 + round(42 * (ci - 1) / tot))
    if "listening" in msg:
        return max(prev_pct, 10)
    return max(prev_pct, 5)


def _load_cached_song_map(song_name: str, *, listen: bool = False) -> tuple[str, dict[str, Any]]:
    path = _resolve_song_file(song_name)
    base = os.path.basename(path)
    try:
        mtime = float(os.path.getmtime(path))
    except OSError:
        mtime = 0.0
    key = (path, mtime, bool(listen))
    ev: threading.Event | None = None
    owner = False
    while True:
        with _CACHE_LOCK:
            hit = _SONGMAP_CACHE.get(key)
            if hit is not None:
                return path, hit
            ev = _SONGMAP_INFLIGHT.get(key)
            if ev is None:
                ev = threading.Event()
                _SONGMAP_INFLIGHT[key] = ev
                owner = True
                break
        ev.wait(timeout=1.0)

    if not owner:
        with _CACHE_LOCK:
            hit = _SONGMAP_CACHE.get(key)
            if hit is not None:
                return path, hit

    dev, threads = _pick_songmap_device(bool(listen))
    pct_box = [8]
    _set_songmap_progress(
        base,
        running=True,
        stage=f"Analyzing tempo & beats ({dev})..." if not listen else f"Starting tempo + vocal listen ({dev})...",
        pct=8,
        device=dev,
    )

    def _on_status(msg: str) -> None:
        print(f"[{TAG}] {msg}", flush=True)
        pct_box[0] = _parse_songmap_pct(str(msg or ""), pct_box[0])
        _set_songmap_progress(base, running=True, stage=str(msg), pct=pct_box[0], device=dev)

    try:
        sm = _songmap.song_map(
            path,
            listen=bool(listen),
            status=_on_status,
            allow_download=False,
            device=dev,
            threads=threads,
        )
        _set_songmap_progress(base, running=True, stage="Solving downbeat cuts...", pct=95, device=dev)
        with _CACHE_LOCK:
            if len(_SONGMAP_CACHE) >= _SONGMAP_CACHE_MAX:
                _SONGMAP_CACHE.clear()
            _SONGMAP_CACHE[key] = sm
        return path, sm
    finally:
        with _CACHE_LOCK:
            cur_ev = _SONGMAP_INFLIGHT.pop(key, None)
            if cur_ev is not None:
                cur_ev.set()
        _set_songmap_progress(base, running=False, stage="Ready", pct=100, device=dev)


def _format_sections_for_ui(sm: dict[str, Any]) -> list[dict[str, Any]]:
    downbeats = sm.get("downbeats") or []
    bar_s = float(sm.get("bar_s") or 2.0)
    sung = sm.get("sung")
    lines = sm.get("heard") or sm.get("lines") or []
    raw_secs = sm.get("sections") or []
    out: list[dict[str, Any]] = []
    if not raw_secs:
        nbars = max(1, len(downbeats))
        step = max(4, min(8, nbars // 4 or 4))
        raw_secs = [
            {"bar": 1 + i * step, "kind": "intro" if i == 0 else ("chorus" if i % 2 else "verse"), "why": "grid fallback"}
            for i in range(max(1, (nbars + step - 1) // step))
        ]

    for idx, s in enumerate(raw_secs):
        bar = max(1, int(s.get("bar") or 1))
        from_s = s.get("from_s")
        if from_s is None and 0 <= bar - 1 < len(downbeats):
            from_s = float(downbeats[bar - 1])
        elif from_s is None:
            from_s = float(sm.get("first_downbeat_s") or 0.0) + (bar - 1) * bar_s

        next_bar = (
            max(bar + 1, int(raw_secs[idx + 1].get("bar") or (bar + 1)))
            if idx + 1 < len(raw_secs)
            else len(downbeats) + 1
        )
        to_s = s.get("to_s")
        if to_s is None:
            if 0 <= next_bar - 1 < len(downbeats):
                to_s = float(downbeats[next_bar - 1])
            else:
                to_s = float(sm.get("ends_on_sound") or sm.get("dur") or (from_s + bar_s))

        kind = str(s.get("kind") or "verse").strip().lower().replace(" ", "_")
        if kind not in SECTION_KINDS:
            kind = "verse"

        is_sung = None
        if isinstance(sung, list) and sung:
            lo = max(0, bar - 1)
            hi = min(len(sung), max(lo + 1, next_bar - 1))
            slice_v = sung[lo:hi]
            if slice_v:
                is_sung = any(float(v) >= 0.35 for v in slice_v)

        lyric_parts = []
        for ln in lines:
            if isinstance(ln, dict):
                la = float(ln.get("a") or 0.0)
                if float(from_s) - 0.5 <= la < float(to_s):
                    t = str(ln.get("text") or "").strip()
                    if t:
                        lyric_parts.append(t)
        out.append({
            "index": idx + 1,
            "bar": bar,
            "from_s": round(float(from_s), 2),
            "to_s": round(float(to_s), 2),
            "kind": kind,
            "why": str(s.get("why") or "")[:90],
            "sung": is_sung,
            "lyric": " / ".join(lyric_parts[:2])[:110],
        })
    return out


def _solve_with_fallback(sm: dict[str, Any], sections: list[dict[str, Any]], *, pattern: tuple[str, ...] | None = None, end_s: float | None = None) -> dict[str, Any]:
    solver_secs = [{"bar": max(1, int(s.get("bar") or 1)), "kind": str(s.get("kind") or "verse")} for s in sections]
    last_exc = ""
    candidates = [solver_secs]
    for trim_k in range(1, min(len(solver_secs), 4)):
        candidates.append(solver_secs[:-trim_k])
    wide_labels = tuple(f"{i} s" for i in range(5, 16))
    for tol, lbls, pat in (
        (32, None, pattern),
        (72, None, pattern),
        (72, wide_labels, pattern),
        (144, wide_labels, pattern or ("R", "RC", "RCC", "RCCC", "RCCCC")),
    ):
        for cand in candidates:
            if not cand:
                continue
            try:
                sol = _mv_solver.solve(sm, cand, pattern=pat, end_s=end_s, tol_max=tol, labels=lbls)
                out = {"ok": True, **sol}
                if tol > 32 or len(cand) < len(solver_secs) or lbls is not None:
                    out["relaxed_tol"] = True
                return out
            except Exception as exc:
                last_exc = str(exc)
    return {"ok": False, "error": last_exc or "could not fit cuts", "hops": [], "master_audio_start_s": 0.0}


def analyze_song(
    song_name: str,
    *,
    listen: bool = False,
    sections: list[dict[str, Any]] | None = None,
    pattern: list[str] | None = None,
    end_s: float | None = None,
) -> dict[str, Any]:
    """Run `songmap` + `mv_solver` on an audio file and return UI-ready timeline data."""
    path, sm = _load_cached_song_map(song_name, listen=listen)
    sec_rows = sections if sections else _format_sections_for_ui(sm)
    pat_tuple = tuple(str(x) for x in pattern) if pattern else None
    solved = _solve_with_fallback(sm, sec_rows, pattern=pat_tuple, end_s=end_s)
    return {
        "ok": True,
        "file": os.path.basename(path),
        "bpm": round(float(sm.get("bpm") or 0.0), 2),
        "bar_s": round(float(sm.get("bar_s") or 0.0), 3),
        "beats_per_bar": int(sm.get("beats_per_bar") or 4),
        "first_downbeat_s": round(float(sm.get("first_downbeat_s") or 0.0), 3),
        "dur": round(float(sm.get("dur") or 0.0), 2),
        "ends_on_sound": sm.get("ends_on_sound"),
        "grid": str(sm.get("grid") or "fixed"),
        "drift_f": round(float(sm.get("drift_f") or 0.0), 2),
        "tracked_note": str(sm.get("tracked_note") or ""),
        "path": str(sm.get("path") or "tempo-only"),
        "has_stem": bool(sm.get("stem")),
        "sections": sec_rows,
        "solved": solved,
    }


def solve_mv(
    song_name: str,
    sections: list[dict[str, Any]],
    *,
    listen: bool = False,
    pattern: list[str] | None = None,
    end_s: float | None = None,
) -> dict[str, Any]:
    """Re-solve hop cut points cleanly after the user edits section bars/kinds."""
    return analyze_song(song_name, listen=listen, sections=sections, pattern=pattern, end_s=end_s)


def extract_clip_frame(
    video_name: str,
    *,
    frame_idx: int = 0,
    time_s: float | None = None,
    out_name: str = "",
) -> dict[str, Any]:
    """Extract one PNG frame from a video clip in `input/h3_refs/` for Qwen-Viggle painting."""
    src = _media.resolve(video_name, kinds={"video"})
    if not src:
        raise FileNotFoundError(f"Video '{video_name}' not found in input/h3_refs/.")

    import cv2  # noqa: PLC0415

    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video '{video_name}'.")
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
        total = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1))
        if time_s is not None and float(time_s) >= 0:
            idx = int(round(float(time_s) * fps))
        else:
            idx = int(frame_idx or 0)
        idx = max(0, min(total - 1, idx))
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, bgr = cap.read()
        if not ok or bgr is None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, bgr = cap.read()
            idx = 0
        if not ok or bgr is None:
            raise RuntimeError(f"Failed to decode frame {idx} from '{video_name}'.")
        dest_dir = _media.refs_dir(create=True)
        stem = _SAFE_NAME.sub("_", os.path.splitext(os.path.basename(video_name))[0]).strip("_") or "clip"
        target_base = _SAFE_NAME.sub("_", os.path.basename(out_name or f"_swap_src_{stem}_f{idx}.png"))
        if not target_base.lower().endswith(".png"):
            target_base += ".png"
        out_path = os.path.join(dest_dir, target_base)
        if not cv2.imwrite(out_path, bgr):
            raise RuntimeError(f"Failed writing extracted frame '{target_base}'.")
        h, w = bgr.shape[:2]
    finally:
        cap.release()

    return {
        "ok": True,
        "filename": os.path.basename(out_path),
        "frame_idx": idx,
        "total_frames": total,
        "fps": round(fps, 3),
        "width": int(w),
        "height": int(h),
    }


def _safe_output_path(filename: str, subfolder: str = "", output_type: str = "output") -> str:
    base_name = os.path.basename(str(filename or "").strip())
    if not base_name:
        raise ValueError("Missing output filename.")
    root_fn = {
        "output": folder_paths.get_output_directory,
        "temp": folder_paths.get_temp_directory,
        "input": folder_paths.get_input_directory,
    }.get(str(output_type or "output").lower(), folder_paths.get_output_directory)
    base_dir = os.path.abspath(root_fn())
    sub = str(subfolder or "").replace("\\", "/").strip("/")
    parts = [p for p in sub.split("/") if p and p not in (".", "..")]
    cand = os.path.abspath(os.path.join(base_dir, *parts, base_name))
    if not folder_paths.is_within_directory(base_dir, cand):
        raise ValueError("Invalid output path traversal.")
    if not os.path.isfile(cand):
        raise FileNotFoundError(f"Generated output '{base_name}' was not found in {output_type}.")
    return cand


def import_output(
    *,
    filename: str,
    subfolder: str = "",
    output_type: str = "output",
    dest_name: str = "",
    kind: str = "image",
    tag: str = "",
    desc: str = "",
    role: str = "cast",
    register_bible: bool = False,
) -> dict[str, Any]:
    """Copy a generated ComfyUI output into `input/h3_refs/` and optionally log to Reference Bible."""
    src = _safe_output_path(filename, subfolder=subfolder, output_type=output_type)
    refs_root = _media.refs_dir(create=True)
    _, ext = os.path.splitext(src)
    ext = ext.lower() or (".png" if kind == "image" else ".flac")
    raw_dest = str(dest_name or os.path.basename(src)).strip()
    clean_base = _SAFE_NAME.sub("_", os.path.basename(raw_dest))
    if not os.path.splitext(clean_base)[1]:
        clean_base += ext

    h = hashlib.sha256()
    with open(src, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    digest = h.hexdigest()

    existing = _media.find_by_hash(refs_root, digest)
    if existing:
        final_path = os.path.join(refs_root, existing)
    else:
        final_path = _media.claim_for_hash(refs_root, clean_base, digest)
        shutil.copy2(src, final_path)
        if kind == "image":
            final_path, _, _ = _media.shrink_image(final_path)

    saved_name = os.path.basename(final_path)
    bible_saved = False
    if register_bible and kind == "image":
        try:
            from .htc_sandtie import refs as _st_refs  # noqa: PLC0415

            clean_tag = re.sub(r"[^a-zA-Z0-9_]+", "_", str(tag or os.path.splitext(saved_name)[0]).lower()).strip("_") or "ref"
            item_role = "prop" if role == "prop" else ("place" if role in ("plate", "place") else "subject")
            _st_refs.upsert_ref_bank_item({
                "tag": clean_tag,
                "name": clean_tag.replace("_", " ").title(),
                "role": item_role,
                "file": saved_name,
                "desc": str(desc or "").strip(),
            }, user_edited=True)
            bible_saved = True
        except Exception as exc:
            print(f"[{TAG}] bible save skipped: {exc!r}", flush=True)

    return {
        "ok": True,
        "filename": saved_name,
        "kind": kind,
        "deduped": bool(existing),
        "bible_saved": bible_saved,
    }


IDEATE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "song_style", "lyrics", "cast_assets", "plate_assets", "prop_assets", "brief"],
    "properties": {
        "title": {"type": "string"},
        "song_style": {"type": "string"},
        "lyrics": {"type": "string"},
        "brief": {"type": "string"},
        "cast_assets": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tag", "prompt"],
                "properties": {
                    "tag": {"type": "string"},
                    "prompt": {"type": "string"},
                },
            },
        },
        "plate_assets": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tag", "section", "prompt"],
                "properties": {
                    "tag": {"type": "string"},
                    "section": {"type": "string"},
                    "prompt": {"type": "string"},
                },
            },
        },
        "prop_assets": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tag", "prompt"],
                "properties": {
                    "tag": {"type": "string"},
                    "prompt": {"type": "string"},
                },
            },
        },
    },
}

LYRICS_ONLY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["song_style", "lyrics"],
    "properties": {
        "song_style": {"type": "string"},
        "lyrics": {"type": "string"},
    },
}

_YUE2_VALID_TAGS = (
    "intro", "verse", "pre-chorus", "prechorus", "chorus", "hook",
    "bridge", "refrain", "outro", "instrumental", "interlude",
)
_YUE2_TAG_PRETTY = {
    "prechorus": "Pre-Chorus",
    "pre-chorus": "Pre-Chorus",
}
_YUE2_TAG_LINE_RE = re.compile(
    r"^[\s>*_#]*\[?\s*(" + "|".join(_YUE2_VALID_TAGS) + r")\s*(\d+)?\s*\]?[\s:*_#-]*$",
    re.IGNORECASE,
)
_LYRIC_PAREN_STAGE_RE = re.compile(r"^\s*[(\[][^)\]]{1,80}[)\]]\s*$")
_LYRIC_NUM_PREFIX_RE = re.compile(r"^\s*(?:\d+\s*[.)]\s+|[-*•]\s+)")


def _song_timing_plan(duration_target_s: int, vocal_mode: str = "auto") -> dict[str, Any]:
    """Scale section structure & exact sung-line budget to the selected MV duration."""
    dur = max(30, min(240, int(duration_target_s or 105)))
    v_low = str(vocal_mode or "auto").strip().lower()
    if v_low == "instrumental":
        return {
            "target_s": dur,
            "sections": [("[Intro]", 0), ("[Instrumental]", 0), ("[Outro]", 0)],
            "target_lines": 0,
            "min_lines": 0,
            "max_lines": 0,
            "note": "Pure instrumental score with no sung vocals.",
        }

    if dur <= 52:
        secs = [("[Verse 1]", 4), ("[Chorus]", 4), ("[Outro]", 2)]
        t_lines, min_l, max_l = 10, 8, 13
        note = "Tight hook sprint (~45 s): drop straight into Verse 1 and Chorus with zero long instrumental delay."
    elif dur <= 75:
        secs = [("[Intro]", 0), ("[Verse 1]", 4), ("[Chorus]", 4), ("[Verse 2]", 4), ("[Chorus]", 4)]
        t_lines, min_l, max_l = 16, 14, 19
        note = "Punchy ~60 s double-hook arc: brief intro pickup (<4 s), two 4-line verses, and two 4-line choruses."
    elif dur <= 97:
        secs = [("[Intro]", 0), ("[Verse 1]", 4), ("[Pre-Chorus]", 2), ("[Chorus]", 4), ("[Verse 2]", 4), ("[Chorus]", 4), ("[Outro]", 2)]
        t_lines, min_l, max_l = 20, 18, 24
        note = "Standard ~90 s MV arc: build into the Chorus via Pre-Chorus, advance the story in Verse 2, repeat Chorus, close cleanly."
    elif dur <= 112:
        secs = [("[Intro]", 0), ("[Verse 1]", 4), ("[Pre-Chorus]", 2), ("[Chorus]", 4), ("[Verse 2]", 4), ("[Chorus]", 4), ("[Bridge]", 4), ("[Outro]", 2)]
        t_lines, min_l, max_l = 24, 21, 28
        note = "Classic ~105 s MV arc with contrasting Bridge turn before the closing Outro."
    elif dur <= 135:
        secs = [("[Intro]", 0), ("[Verse 1]", 4), ("[Pre-Chorus]", 2), ("[Chorus]", 4), ("[Verse 2]", 4), ("[Pre-Chorus]", 2), ("[Chorus]", 4), ("[Bridge]", 4), ("[Chorus]", 4), ("[Outro]", 2)]
        t_lines, min_l, max_l = 30, 27, 34
        note = "Full ~120 s single structure: three Chorus hits, two Pre-Chorus lifts, and a full Bridge turnaround."
    elif dur <= 165:
        secs = [("[Intro]", 2), ("[Verse 1]", 6), ("[Pre-Chorus]", 2), ("[Chorus]", 4), ("[Verse 2]", 6), ("[Pre-Chorus]", 2), ("[Chorus]", 4), ("[Bridge]", 4), ("[Chorus]", 4), ("[Outro]", 2)]
        t_lines, min_l, max_l = 36, 32, 40
        note = "Extended ~150 s arrangement: 6-line story verses, vocal intro hook, three full choruses, Bridge, and Outro."
    else:
        secs = [("[Intro]", 2), ("[Verse 1]", 6), ("[Pre-Chorus]", 4), ("[Chorus]", 4), ("[Verse 2]", 6), ("[Pre-Chorus]", 4), ("[Chorus]", 4), ("[Instrumental]", 0), ("[Bridge]", 4), ("[Chorus]", 4), ("[Outro]", 4)]
        t_lines, min_l, max_l = 42, 37, 48
        note = "Full ~180 s feature MV: expanded 6-line verses, 4-line Pre-Choruses, Instrumental break/solo, Bridge, final Chorus, and 4-line Outro."

    return {
        "target_s": dur,
        "sections": secs,
        "target_lines": t_lines,
        "min_lines": min_l,
        "max_lines": max_l,
        "note": note,
    }


def _tidy_song_style(raw: Any) -> str:
    if isinstance(raw, list):
        txt = ", ".join(str(x).strip() for x in raw if x is not None and str(x).strip())
    else:
        txt = str(raw or "").strip()
    txt = txt.replace("\r\n", "\n").replace("\\n", " ")
    lines = [ln.strip().strip("`*_\"' ") for ln in txt.splitlines() if ln.strip()]
    joined = ", ".join(ln for ln in lines if not re.match(r"^style\s*[:.\-]*$", ln, re.I))
    joined = re.sub(r"^(?:style|song_style)\s*[:\-]+\s*", "", joined, flags=re.I)
    joined = re.sub(r"\s+", " ", joined).strip(" ,")
    return joined


def _normalize_section_tag(line: str) -> str:
    clean = str(line or "").strip()
    if not clean:
        return ""
    low = clean.lower()
    # Map common LLM aliases cleanly onto YuE2's recognized tags
    alias_map = (
        (r"^\[?\s*(?:final|last|outro)\s+chorus(?:\s*(\d+))?\s*\]?[:\s]*$", "Chorus"),
        (r"^\[?\s*guitar\s+solo\s*\]?[:\s]*$", "Instrumental"),
        (r"^\[?\s*dance\s+break\s*\]?[:\s]*$", "Instrumental"),
        (r"^\[?\s*drop\s*\]?[:\s]*$", "Hook"),
    )
    for pat, label in alias_map:
        m_al = re.match(pat, low)
        if m_al:
            num = m_al.group(1) if m_al.lastindex else ""
            return f"[{label}{' ' + num if num else ''}]"
    m = _YUE2_TAG_LINE_RE.match(clean)
    if not m:
        return ""
    word = m.group(1).strip().lower()
    pretty = _YUE2_TAG_PRETTY.get(word) or "-".join(p.capitalize() for p in word.split("-"))
    num = m.group(2)
    return f"[{pretty}{' ' + num if num else ''}]"


def _tidy_yue2_lyrics(raw: Any) -> str:
    if isinstance(raw, list):
        txt = "\n".join(str(x).strip() for x in raw if x is not None)
    else:
        txt = str(raw or "")
    txt = txt.replace("\r\n", "\n").replace("\\n", "\n")
    kept: list[str] = []
    for raw_ln in txt.splitlines():
        line = raw_ln.strip()
        if not line or line.startswith("```"):
            continue
        if re.match(r"^(?:lyrics|song lyrics)\s*[:.\-]*$", line, re.I):
            continue
        tag = _normalize_section_tag(line)
        if tag:
            if kept and kept[-1] != "":
                kept.append("")
            kept.append(tag)
            continue
        if _LYRIC_PAREN_STAGE_RE.match(line):
            continue
        line = _LYRIC_NUM_PREFIX_RE.sub("", line).strip()
        line = line.strip("*_`").strip()
        # Strip speaker prefix like "Mina:" or "Singer:" if emitted at start
        line = re.sub(r"^[A-Za-z0-9_@]{1,20}:\s+", "", line)
        # Strip @tags inside sung lyric lines (never sing literal "@mina")
        line = re.sub(r"@([A-Za-z0-9_]+)", r"\1", line)
        # Strip inline parenthetical stage directions (e.g. "(soft sigh)")
        line = re.sub(r"\([^)]{1,45}\)", "", line).strip()
        if len(line) >= 2 and line[0] in ('"', "'") and line[-1] == line[0]:
            line = line[1:-1].strip()
        line = re.sub(r"\s{2,}", " ", line).strip()
        if line:
            kept.append(line)
    while kept and not kept[-1]:
        kept.pop()
    return "\n".join(kept)


def _count_yue2_sung_lines(lyrics: str) -> int:
    cnt = 0
    for ln in (lyrics or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("[") and s.endswith("]"):
            continue
        if any(ch.isalnum() for ch in s):
            cnt += 1
    return cnt


def _count_yue2_sections(lyrics: str) -> int:
    return sum(
        1 for ln in (lyrics or "").splitlines()
        if ln.strip().startswith("[") and ln.strip().endswith("]")
    )


def _extract_bpm(style: str) -> int | None:
    m = re.search(r"\b(\d{2,3})\s*bpm\b", str(style or ""), re.I)
    return int(m.group(1)) if m else None


_MV_LANG_SCRIPT_RX = {
    "japanese": re.compile(r"[\u3040-\u30ff]"),
    "korean": re.compile(r"[\uac00-\ud7af]"),
    "chinese": re.compile(r"[\u4e00-\u9fff]"),
    "mandarin": re.compile(r"[\u4e00-\u9fff]"),
    "russian": re.compile(r"[\u0400-\u04ff]"),
    "thai": re.compile(r"[\u0e00-\u0e7f]"),
    "arabic": re.compile(r"[\u0600-\u06ff]"),
    "spanish": re.compile(r"[áéíóúüñ¿¡]|\b(?:que|como|más|aquí|ahora|esto|está|estás|contigo|conmigo|quiero|noche|luz|amor|tiempo|vida|bajo|sobre|entre|hasta|sin|para|por)\b", re.I),
    "french": re.compile(r"[àâçéèêëîïôûùüÿœ]|\b(?:je|tu|nous|vous|avec|sans|comme|encore|nuit|lumière|amour|temps|vie|sous|dans|pour|toujours|mon|ton|cette|c'est)\b", re.I),
    "portuguese": re.compile(r"[ãõáéíóúâêôç]|\b(?:você|aqui|agora|mais|noite|luz|amor|tempo|vida|comigo|sem|para|meu|minha|tudo|sempre|entre)\b", re.I),
    "italian": re.compile(r"[àèéìíîòóùú]|\b(?:notte|luce|amore|tempo|vita|qui|ancora|questo|questa|sempre|con|senza|mio|mia|tutto|verso)\b", re.I),
    "german": re.compile(r"[äöüß]|\b(?:ich|du|wir|und|mit|ohne|nacht|licht|liebe|zeit|leben|unter|durch|immer|mein|dein|nicht|ist)\b", re.I),
}

_MV_LANG_EXAMPLES = {
    "japanese": (
        "\"Japanese, high-energy anime J-Rock opening, soaring expressive female vocal with octave chorus harmonies, "
        "driving distorted electric guitars, fast punchy bass, tight double-kick drums, shimmering synth lead, 4/4, 168 BPM\"",
        "Write ALL sung lyrics strictly in natural native Japanese script (漢字 + ひらがな + カタカナ, e.g. `夜空を切り裂く光の中で`), NEVER English and NEVER romaji!"
    ),
    "korean": (
        "\"Korean, glossy K-Pop electro-dance pop, confident expressive female lead vocal with layered chorus harmonies, "
        "punchy 808 synth bass, snappy trap claps, bright arpeggio synths, soaring pre-chorus lift, 4/4, 124 BPM\"",
        "Write ALL sung lyrics strictly in natural native Korean Hangul (한글, e.g. `네온 불빛 아래 멈출 수 없어`), NEVER English sentences and NEVER romanized Korean!"
    ),
    "chinese": (
        "\"Chinese, cinematic modern Guofeng R&B pop, velvety expressive vocal with airy harmonies, "
        "plucked guzheng, airy bamboo flute, warm 808 sub-bass, crisp rimshot groove, 4/4, 96 BPM\"",
        "Write ALL sung lyrics strictly in natural native Simplified Chinese characters (汉字, e.g. `月色洒在青石街头`), NEVER English and NEVER pinyin!"
    ),
    "russian": (
        "\"Russian, nocturnal dark synth-pop, moody velvet vocal with wide atmospheric harmonies, "
        "pulsing analog bass, crisp gated snare, cold shimmering pads, 4/4, 118 BPM\"",
        "Write ALL sung lyrics strictly in natural native Russian Cyrillic (Русский, e.g. `Неон горит в холодном окне`), NEVER English and NEVER Latin transliteration!"
    ),
}


def _mv_lyrics_missing_target_lang(lyrics_txt: str, song_style: str, lang_clean: str) -> tuple[bool, str]:
    """Return `(missing, repair_reason)` if user chose a non-English language and LLM slipped back to English."""
    lc = str(lang_clean or "").strip().lower()
    if not lc or lc in ("auto", "english"):
        return False, ""
    body_lines = [ln.strip() for ln in str(lyrics_txt or "").splitlines() if ln.strip() and not ln.strip().startswith("[")]
    body = "\n".join(body_lines)
    if not body:
        return False, ""
    rx = _MV_LANG_SCRIPT_RX.get(lc)
    if lc == "chinese" or lc == "mandarin":
        has_native = bool(rx and rx.search(body)) and not bool(re.search(r"[\u3040-\u30ff]", body))
    elif rx is not None:
        hits = len(rx.findall(body))
        has_native = hits >= (4 if lc in ("japanese", "korean", "russian", "thai", "arabic") else 3)
    else:
        has_native = True
    has_style_lang = lc in str(song_style or "").lower()
    if has_native and has_style_lang:
        return False, ""
    ex_pair = _MV_LANG_EXAMPLES.get(lc)
    ex_hint = f" ({ex_pair[1]})" if ex_pair else ""
    return True, (
        f"Selected language is `{lang_clean}`, yet `song_style` or `lyrics` slipped into English/romanization! "
        f"Place `{lang_clean}` FIRST in `song_style` and rewrite EVERY sung line in `lyrics` strictly in authentic native {lang_clean} script{ex_hint} — ZERO English or romanization in `lyrics`."
    )


async def ideate_mv(
    idea: str,
    *,
    complete_fn,
    cast_rows: list[dict[str, Any]] | None = None,
    aspect: str = "16:9",
    duration_target_s: int = 105,
    image_profile: str = "qwen_viggle_6step",
    language: str = "auto",
    vocal_mode: str = "auto",
    lyrics_only: bool = False,
    existing_style: str = "",
    existing_title: str = "",
) -> dict[str, Any]:
    """Turn a rough concept + cast list into a duration-scaled YuE2 song spec, asset prompts, and MV brief."""
    from . import planner as _planner  # noqa: PLC0415

    cast_lines = []
    existing_with_files = 0
    for r in cast_rows or []:
        if not isinstance(r, dict):
            continue
        t = str(r.get("tag") or "").strip().lstrip("@")
        if not t:
            continue
        desc = str(r.get("desc") or "").strip()
        fn = str(r.get("file") or "").strip()
        ret = str(r.get("retention") or "").strip()
        subj = r.get("subject")
        role_hint = "cast" if subj is not None else ("prop" if ret == "prop" else "plate")
        if fn:
            existing_with_files += 1
        meta_bits = [f"file={fn or 'none'}", f"role={role_hint}"]
        if subj is not None:
            meta_bits.append(f"subject={subj}")
        if ret:
            meta_bits.append(f"retention={ret}")
        cast_lines.append(f"- @{t} ({', '.join(meta_bits)}): {desc or 'no visual description yet'}")

    prof = _find_profile(image_profile)
    plan = _song_timing_plan(duration_target_s, vocal_mode=vocal_mode)
    lang_clean = str(language or "auto").strip()
    vocal_clean = str(vocal_mode or "auto").strip()
    idea_str = str(idea or "").strip()
    req_bpm_m = re.search(r"\b(\d{2,3})\s*bpm\b", idea_str, re.I)
    req_bpm = int(req_bpm_m.group(1)) if req_bpm_m else None

    sec_checklist = "\n".join(
        f"  - {tag}: {'instrumental / atmospheric music only (0 sung lines)' if cnt == 0 else f'{cnt} sung lines'}"
        for tag, cnt in plan["sections"]
    )
    lang_key = lang_clean.lower()
    is_non_english = bool(lang_key and lang_key not in ("auto", "english"))
    lang_ex = _MV_LANG_EXAMPLES.get(lang_key)
    lang_rule = (
        (
            f"**STRICT LANGUAGE & NATIVE SCRIPT LAW ({lang_clean}):** You MUST place `{lang_clean}` FIRST in `song_style`, "
            f"and write ALL sung lines in `lyrics` strictly in authentic native {lang_clean} script/characters "
            + (f"({lang_ex[1]})" if lang_ex else f"(zero English words or romanization in `lyrics`)")
            + ". Keep section tags in English brackets (`[Intro]`, `[Verse 1]`, `[Chorus]`, `[Outro]`)."
        )
        if is_non_english
        else "Match the language implied by the concept (default English) and name it first in `song_style`."
    )
    vocal_rule = {
        "female": "Feature an expressive female lead vocal (describe specific vocal tone, register, and chorus harmonies in `song_style`).",
        "male": "Feature a charismatic male lead vocal (describe specific vocal tone, grit/warmth, and chorus harmonies in `song_style`).",
        "duet": "Describe a vocal duet pairing male and female voices in `song_style` (never put speaker names or per-section voice switches inside `lyrics`).",
        "rap": "Deliver tight rhythmic rap/cadenced verses paired with a melodic sung or chanted hook; specify flow/phrasing and BPM in `song_style`.",
        "choir": "Feature rich layered lead and ensemble choir harmonies in `song_style`.",
        "instrumental": "Strictly instrumental composition (`no vocals, purely instrumental`). Leave `lyrics` as `[Intro]\\n\\n[Instrumental]\\n\\n[Outro]`.",
    }.get(vocal_clean.lower(), "Pick the vocal character and harmonies in `song_style` that best fit the story and genre.")

    style_ex_block = (
        f"  1) {lang_ex[0]}\n"
        if lang_ex
        else (
            "  1) \"English, nocturnal dark synthwave pop, smoky female lead vocal with airy harmonies, pulsing Moog sub-bass, gated-reverb snare, Juno arpeggios, shimmering clean guitar, soaring hook, 4/4, 108 BPM\"\n"
            "  2) \"English, gritty Memphis phonk & dark street rap, tight rhythmic male baritone flow with chanted hook, distorted 808 sub-bass, crisp trap hi-hats, moody cowbell melody, vinyl grit, 4/4, 136 BPM\"\n"
            "  3) \"English, warm indie folk rock, heartfelt raspy male vocal with subtle acoustic chorus harmonies, fingerpicked acoustic guitar, upright bass, brushed snare, warm organ pad, intimate rising bridge, 4/4, 92 BPM\"\n"
        )
    )
    style_rules = (
        "RULES FOR `song_style` & SONG CHOICE OBEDIENCE (YuE2 reads this verbatim to decide sound, mix, and groove):\n"
        "- **OBEDIENT INTENT:** Obey EVERY song choice in the user's concept (genre, subgenre, era, exact BPM if stated, instruments, vocal gender/style, clean vs aggressive mood, acoustic vs electronic). Never substitute a different genre.\n"
        "- ONE single rich comma-separated line (20-34 words), NEVER generic 3-word tags.\n"
        "- Include in order: Language, exact Genre + Subgenre/Era/Atmosphere, detailed Singing Voice timbre & harmonies, "
        "3 to 5 specific named Instruments & rhythmic textures, Melody/Phrasing character (verse vs chorus lift), Meter (`4/4` or `6/8`), and exact Tempo (`<N> BPM`).\n"
        "- Diverse YuE2 `song_style` example(s) (match the user's chosen language & genre):\n"
        + style_ex_block
        + f"- {lang_rule}\n"
        + f"- {vocal_rule}\n"
    )

    if plan["target_lines"] == 0:
        lyrics_rules = (
            "RULES FOR `lyrics`:\n"
            "- Output `[Intro]\\n\\n[Instrumental]\\n\\n[Outro]` (zero sung words).\n"
        )
    else:
        line_len_rule = (
            f"- Write natural rhythmic {lang_clean} lines of roughly 8 to 15 syllables (morae/characters) per line in native {lang_clean} script so YuE2 sings smoothly in rhythm.\n"
            if lang_key in ("japanese", "korean", "chinese", "mandarin")
            else "- Write 6 to 11 words (roughly 8 to 14 syllables) per sung line so YuE2 sings cleanly in rhythm without rushing or gaps.\n"
        )
        lyrics_rules = (
            f"RULES FOR `lyrics` (SCALED TO ~{plan['target_s']} SECONDS — DO NOT SHORTEN OR ABBREVIATE):\n"
            f"- {plan['note']}\n"
            f"- Follow this exact section blueprint and write {plan['target_lines']} total sung lines "
            f"(minimum {plan['min_lines']}, maximum {plan['max_lines']}):\n"
            f"{sec_checklist}\n"
            + line_len_rule
            + "- Put section tags (`[Verse 1]`, `[Pre-Chorus]`, `[Chorus]`, etc.) on their own lines with ONE blank line between sections.\n"
            "- Repeat the exact `[Chorus]` lines consistently whenever `[Chorus]` returns so the song has a sticky recurring hook.\n"
            "- Put vivid imagery, sensory details, and emotional escalation INSIDE the poetic sung words themselves.\n"
            "- STRICTLY pure singable lyrics on sung lines: ZERO parenthetical directions like `(whispering)`, ZERO `@tags`, "
            "ZERO speaker prefixes like `Kai:`, ZERO line numbers, ZERO quotation marks, ZERO camera notes.\n"
        )

    if lyrics_only:
        sys_msg = (
            "You are a Songwriter and YuE2 Music Producer crafting full-length, rhythmic, emotionally vivid lyrics and style.\n"
            "Return ONLY one valid JSON object matching:\n"
            '{"song_style":"...","lyrics":"..."}\n\n'
            + style_rules + "\n" + lyrics_rules
        )
        user_msg = (
            f"MV Concept / Vibe: {str(idea or '').strip() or 'Moody late-night neon rooftop performance'}\n"
            f"Target Duration: ~{plan['target_s']} seconds ({plan['target_lines']} sung lines)\n"
            f"Language Preference: {lang_clean} | Vocal Preference: {vocal_clean}\n"
            + (f"Existing Title: {existing_title.strip()}\n" if existing_title.strip() else "")
            + (f"Current Style Line (refine/keep consistent BPM & genre): {existing_style.strip()}\n" if existing_style.strip() else "")
            + ("Cast context:\n" + "\n".join(cast_lines) if cast_lines else "")
        )
        schema_use = LYRICS_ONLY_SCHEMA
    else:
        sys_msg = (
            "You are an experienced Music Video Director and Songwriter preparing an end-to-end production pack "
            f"for MiniMax H3 video + YuE2 song synthesis + {prof['label']} image generation.\n"
            "Return ONLY one valid JSON object matching this exact schema (no markdown outside JSON; zero negative words anywhere in image prompts):\n"
            '{"title":"...","song_style":"...","lyrics":"...",'
            '"cast_assets":[{"tag":"lead","prompt":"..."}],'
            '"plate_assets":[{"tag":"street","section":"verse","prompt":"..."}],'
            '"prop_assets":[{"tag":"mic","prompt":"..."}],'
            '"brief":"..."}\n\n'
            + style_rules + "\n" + lyrics_rules + "\n"
            "RULES FOR H3 VISUAL ASSETS & PLATES (100% POSITIVE ENGLISH — ZERO negations like `no`, `not`, `never`, `without`, `nobody`, `empty of people` anywhere in prompts!):\n"
            "- `cast_assets`: list of `{tag, prompt}` ONLY for characters in the concept who do NOT already have a `role=cast` file in Existing Cast / Refs. "
            "(If two characters or a duet are implied, create 2 distinct cast entries with contrasting wardrobe colors/silhouettes.) "
            "Each prompt must be 55-85 words describing a crisp head-to-mid-thigh or full-body studio character sheet on a plain neutral mid-gray seamless backdrop, "
            "even flat diffused softbox studio lighting (keep colored neon/stage gels off the identity sheet so skin & clothing stay true across scenes), "
            "specific age/heritage/facial bone structure/hairline/skin texture, detailed layered outfit fabrics, and one signature asymmetric detail.\n"
            "- `plate_assets`: list of `{tag, section, prompt}` for 2 to 4 hero environment plates spanning the MV arc (`intro`/`verse`, `chorus`/`drop`, `bridge`/`outro`). "
            f"Each prompt must be 55-85 words authored for aspect {aspect} as an establishing camera-first background plate for H3 Ref2VA:\n"
            "  * Name exact lens & height (`28mm wide establishing eye-level frame` or `35mm dramatic low-angle`), clear horizontal ground/stage floor plane with wide open center floor space where performers can stand/dance/walk.\n"
            "  * Specify foreground framing edge, midground architectural landmarks, and background depth + coherent practical lighting direction, color temperature, and reflective surfaces shared across plates of the same shoot.\n"
            "  * Describe purely vacant architecture/lighting (`vacant rain-slicked asphalt plaza, clear empty oak stage floor, bare studio mirror wall`) with ZERO people, silhouettes, or negations.\n"
            "- `prop_assets`: list of `{tag, prompt}` for 1 to 2 signature hero objects isolated cleanly on a plain mid-gray surface under even diffused studio light.\n"
            "- `brief`: rich 5 to 7 sentence directing treatment for H3 Write citing exact `@tags` (`@cast`, `@plate`, `@prop`), mapping Intro -> Verse -> Pre-Chorus -> Chorus -> Bridge -> Outro, "
            "explicitly stating who lip-syncs/performs, camera energy per section (e.g. Verse tracking/medium -> Chorus dynamic orbit/push-in -> Bridge contrast shift -> Outro settle), and coherent lighting/wardrobe continuity."
        )
        user_msg = (
            f"MV Concept / Vibe: {str(idea or '').strip() or 'Moody late-night neon rooftop performance'}\n"
            f"Aspect Ratio: {aspect}\n"
            f"Target Duration: ~{plan['target_s']} seconds ({plan['target_lines']} sung lines)\n"
            f"Language Preference: {lang_clean} | Vocal Preference: {vocal_clean}\n"
            + (f"Existing Style Hint: {existing_style.strip()}\n" if existing_style.strip() else "")
            + "Existing Cast / Refs:\n" + ("\n".join(cast_lines) if cast_lines else "(none yet)")
        )
        schema_use = IDEATE_SCHEMA

    def _clean_tag(s: Any, fallback: str) -> str:
        c = re.sub(r"[^a-zA-Z0-9_]+", "_", str(s or "").lower().lstrip("@")).strip("_")
        return c or fallback

    def _as_text(val: Any, sep: str = "\n") -> str:
        if isinstance(val, str):
            return val.strip()
        if isinstance(val, list):
            return sep.join(str(v).strip() for v in val if v is not None and str(v).strip())
        if isinstance(val, dict):
            return sep.join(f"{k}: {v}" for k, v in val.items() if v is not None and str(v).strip())
        return str(val or "").strip()

    def _norm_assets(raw_val: Any, role: str, prefix: str) -> list[dict[str, Any]]:
        if not raw_val:
            return []
        if isinstance(raw_val, dict):
            items = [{"tag": k, **(v if isinstance(v, dict) else {"prompt": v})} for k, v in raw_val.items()]
        elif isinstance(raw_val, list):
            items = list(raw_val)
        elif isinstance(raw_val, str):
            items = [{"tag": f"{prefix}_1", "prompt": raw_val}]
        else:
            return []
        out: list[dict[str, Any]] = []
        for i, x in enumerate(items):
            if isinstance(x, str):
                p_txt = x.strip()
                t_raw = f"{prefix}_{i + 1}"
                sec_txt = ""
            elif isinstance(x, dict):
                p_txt = _as_text(x.get("prompt") or x.get("description") or x.get("desc") or "", sep=" ")
                t_raw = x.get("tag") or x.get("name") or x.get("id") or f"{prefix}_{i + 1}"
                sec_txt = str(x.get("section") or "").strip()
            else:
                continue
            if not p_txt:
                continue
            row: dict[str, Any] = {"tag": _clean_tag(t_raw, f"{prefix}_{i + 1}"), "role": role, "prompt": p_txt}
            if role == "plate":
                row["section"] = sec_txt
            out.append(row)
        return out

    def _normalize_result(obj: dict[str, Any]) -> dict[str, Any]:
        st_txt = _tidy_song_style(obj.get("song_style") or existing_style)
        ly_txt = _tidy_yue2_lyrics(obj.get("lyrics"))
        if plan["target_lines"] == 0 and not ly_txt:
            ly_txt = "[Intro]\n\n[Instrumental]\n\n[Outro]"
        return {
            "title": _as_text(obj.get("title") or existing_title or "Untitled MV", sep=" ") or "Untitled MV",
            "song_style": st_txt,
            "lyrics": ly_txt,
            "brief": _as_text(obj.get("brief"), sep=" "),
            "cast_assets": [] if lyrics_only else _norm_assets(obj.get("cast_assets"), "cast", "cast"),
            "plate_assets": [] if lyrics_only else _norm_assets(obj.get("plate_assets"), "plate", "plate"),
            "prop_assets": [] if lyrics_only else _norm_assets(obj.get("prop_assets"), "prop", "prop"),
        }

    _ASSET_NEG_RE = re.compile(r"\b(?:no|not|never|without|nobody|nothing|empty\s+of\s+people)\b", re.I)

    def _gaps_for(res: dict[str, Any]) -> list[str]:
        gaps: list[str] = []
        st = res["song_style"]
        ly = res["lyrics"]
        if len(st) < 35 or st.count(",") < 3 or _extract_bpm(st) is None:
            gaps.append(
                "Expand `song_style` into a full comma-separated YuE2 production line with Language, Genre/Subgenre, "
                "detailed Vocal timbre/harmonies, 3-5 named Instruments & textures, Melody/Phrasing, and explicit `<N> BPM`."
            )
        elif req_bpm is not None and _extract_bpm(st) != req_bpm:
            gaps.append(f"User explicitly requested `{req_bpm} BPM` in the concept — set `song_style` tempo to `{req_bpm} BPM`.")
        if plan["target_lines"] > 0:
            miss_lang, lang_gap = _mv_lyrics_missing_target_lang(ly, st, lang_clean)
            if miss_lang:
                gaps.append(lang_gap)
            sung_n = _count_yue2_sung_lines(ly)
            sec_n = _count_yue2_sections(ly)
            if sung_n < plan["min_lines"]:
                gaps.append(
                    f"`lyrics` only had {sung_n} sung lines across {sec_n} section(s), which is too short for the selected "
                    f"~{plan['target_s']} s timing dropdown! Expand the verses, pre-choruses, bridge, and repeated chorus to hit "
                    f"{plan['target_lines']} total sung lines (at least {plan['min_lines']}) using this exact structure:\n{sec_checklist}"
                )
            elif sec_n < 2:
                gaps.append("Include clear bracketed `[Verse 1]`, `[Chorus]`, `[Outro]` section headers in `lyrics`.")
        if not lyrics_only:
            has_existing_cast = any(
                isinstance(r, dict) and r.get("file") and (r.get("subject") is not None or r.get("role") == "cast")
                for r in (cast_rows or [])
            )
            has_existing_plate = any(
                isinstance(r, dict) and r.get("file") and r.get("subject") is None and r.get("retention") != "prop"
                for r in (cast_rows or [])
            )
            if not res["cast_assets"] and existing_with_files == 0 and not has_existing_cast:
                gaps.append("Include at least 1 rich photographic `cast_assets` character sheet (55-85 words) on plain neutral gray studio backdrop.")
            if not res["plate_assets"] and not has_existing_plate:
                gaps.append("Include 2 to 4 detailed camera-first vacant `plate_assets` environments with clear open floor space.")
            bad_neg = [
                a.get("tag") for a in (res["cast_assets"] + res["plate_assets"] + res["prop_assets"])
                if _ASSET_NEG_RE.search(str(a.get("prompt") or ""))
            ]
            if bad_neg:
                gaps.append(
                    f"Rewrite prompts for asset(s) {bad_neg} in 100% positive English — remove every negative word "
                    "(`no`, `not`, `never`, `without`, `nobody`, `empty of people`) and describe bare/vacant surfaces positively instead."
                )
        return gaps

    from .htc_sandtie import vision_cv as _vcv  # noqa: PLC0415

    def _parse_ideate(raw_txt: Any) -> dict[str, Any] | None:
        obj = _planner._parse_obj(raw_txt)
        if isinstance(obj, dict):
            return obj
        return _vcv._parse_lenient_json_obj(str(raw_txt or ""))

    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_msg},
    ]
    raw = await complete_fn(messages, schema=schema_use)
    parsed = _parse_ideate(raw)
    if not isinstance(parsed, dict):
        # Single syntax repair turn before giving up
        try:
            raw_fix = await complete_fn(
                messages + [
                    {"role": "assistant", "content": str(raw or "")},
                    {"role": "user", "content": "Your previous reply had invalid JSON syntax (e.g. a missing comma or unescaped quote). Return ONLY one valid JSON object matching the exact schema."},
                ],
                schema=schema_use,
            )
            parsed = _parse_ideate(raw_fix)
            if isinstance(parsed, dict):
                raw = raw_fix
        except Exception:
            pass
    if not isinstance(parsed, dict):
        raise ValueError("Writer did not return a valid MV ideation JSON object.")
    best = _normalize_result(parsed)

    # Single targeted self-repair if the model undershot the timing dropdown or gave a bare style line
    gaps = _gaps_for(best)
    if gaps:
        repair_note = (
            "Please upgrade your JSON output to satisfy every requirement below:\n- "
            + "\n- ".join(gaps)
            + "\nReturn ONLY the complete corrected JSON object matching the exact schema."
        )
        try:
            raw2 = await complete_fn(
                messages + [
                    {"role": "assistant", "content": str(raw)},
                    {"role": "user", "content": repair_note},
                ],
                schema=schema_use,
            )
            if raw2 and str(raw2).strip() != str(raw).strip():
                parsed2 = _parse_ideate(raw2)
                if isinstance(parsed2, dict):
                    cand = _normalize_result(parsed2)
                    # Keep non-empty assets if repair dropped them
                    if not lyrics_only:
                        if not cand["cast_assets"] and best["cast_assets"]:
                            cand["cast_assets"] = best["cast_assets"]
                        if not cand["plate_assets"] and best["plate_assets"]:
                            cand["plate_assets"] = best["plate_assets"]
                        if not cand["prop_assets"] and best["prop_assets"]:
                            cand["prop_assets"] = best["prop_assets"]
                        if not cand["brief"] and best["brief"]:
                            cand["brief"] = best["brief"]
                    if not cand["title"] or cand["title"] == "Untitled MV":
                        cand["title"] = best["title"]
                    # Accept repaired output if it improved compliance (more lines or fewer gaps)
                    if (
                        len(_gaps_for(cand)) <= len(gaps)
                        or _count_yue2_sung_lines(cand["lyrics"]) > _count_yue2_sung_lines(best["lyrics"])
                    ):
                        best = cand
        except Exception:
            pass

    sung_final = _count_yue2_sung_lines(best["lyrics"])
    secs_final = _count_yue2_sections(best["lyrics"])
    bpm_final = _extract_bpm(best["song_style"])
    return {
        "ok": True,
        **best,
        "lyrics_only": bool(lyrics_only),
        "timing_plan": {
            "target_s": plan["target_s"],
            "target_lines": plan["target_lines"],
            "min_lines": plan["min_lines"],
            "sung_lines": sung_final,
            "sections": secs_final,
            "bpm": bpm_final,
        },
    }


def _viggle_lora_fwd(x, ab):
    import torch.nn.functional as F
    return F.linear(F.linear(x, ab[0].to(device=x.device, dtype=x.dtype)), ab[1].to(device=x.device, dtype=x.dtype))


def _viggle_add_hook(mod, ab):
    return mod.register_forward_hook(lambda _m, inp, out: out + _viggle_lora_fwd(inp[0], ab))


def _viggle_add_mlp_hooks(mlp, gate, up, down):
    import torch
    import torch.nn.functional as F

    buf: dict[str, Any] = {}

    def gate_up_hook(_m, inp, out):
        buf["gu"] = out + torch.cat([_viggle_lora_fwd(inp[0], gate), _viggle_lora_fwd(inp[0], up)], -1)
        return buf["gu"]

    def mlp_hook(_m, _inp, out):
        g, u = buf.pop("gu").chunk(2, -1)
        return out + _viggle_lora_fwd(F.silu(g) * u, down)

    return [mlp.gate_up.register_forward_hook(gate_up_hook), mlp.register_forward_hook(mlp_hook)]


def _viggle_run_with_lora(lora, executor, *args, **kwargs):
    dm = executor.class_obj
    dev = args[0].device
    for ab in lora.values():
        if ab[0].device != dev:
            ab[0], ab[1] = ab[0].to(dev), ab[1].to(dev)
    hooks = []
    for name, ab in lora.items():
        parent, _, leaf = name.rpartition(".")
        if not getattr(dm.get_submodule(parent), "fused", False):
            hooks.append(_viggle_add_hook(dm.get_submodule(name), ab))
        elif leaf == "out":
            hooks += _viggle_add_mlp_hooks(
                dm.get_submodule(parent),
                lora[parent + ".gate_layer"],
                lora[parent + ".proj"],
                ab,
            )
    try:
        return executor(*args, **kwargs)
    finally:
        for hk in hooks:
            hk.remove()


class HTCQwenViggleLora:
    """Applies diffusers/PEFT Qwen-Image-2.1 LoRAs at runtime (unmerged) for Studio & RefMod extraction."""

    DEPRECATED = True
    CATEGORY = "Hand Tie Clips"
    RETURN_TYPES = ("MODEL",)
    FUNCTION = "load"
    DESCRIPTION = "Internal runtime PEFT LoRA loader for Qwen 2.1 Viggle Turbo (avoids int8 quantization noise)."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL", {"tooltip": "Qwen Image 2.1 / Viggle diffusion model to patch."}),
                "lora_name": (_safe_list("loras"), {"tooltip": "Diffusers/PEFT Qwen LoRA file from models/loras/."}),
                "strength": ("FLOAT", {"default": 1.0, "min": -4.0, "max": 4.0, "step": 0.05,
                                       "tooltip": "Runtime PEFT LoRA strength (applied without merging int8 weights)."}),
            }
        }

    def load(self, model, lora_name, strength=1.0):
        import json as _json
        import comfy.patcher_extension
        import comfy.sd
        import comfy.utils

        path = folder_paths.get_full_path_or_raise("loras", lora_name)
        sd, meta = comfy.utils.load_torch_file(path, return_metadata=True)
        has_peft = any(k.startswith("transformer.") and k.endswith(".lora_A.weight") for k in sd)
        if not has_peft:
            m_out, _ = comfy.sd.load_bypass_lora_for_models(model, None, sd, float(strength), 0.0)
            return (m_out,)

        cfg = _json.loads((meta or {}).get("lora_adapter_metadata", "{}"))
        scale = float(strength) * float(cfg.get("transformer.lora_alpha", 1)) / max(1.0, float(cfg.get("transformer.r", 1)))
        lora = {
            k.removeprefix("transformer.").removesuffix(".lora_A.weight"): [
                sd[k],
                sd[k.replace("lora_A", "lora_B")] * scale,
            ]
            for k in sd
            if k.endswith(".lora_A.weight")
        }
        m = model.clone()
        m.add_wrapper_with_key(
            comfy.patcher_extension.WrappersMP.DIFFUSION_MODEL,
            "htc_viggle_turbo_lora",
            lambda executor, *a, **kw: _viggle_run_with_lora(lora, executor, *a, **kw),
        )
        return (m,)


NODE_CLASS_MAPPINGS = {"HTCQwenViggleLora": HTCQwenViggleLora}
NODE_DISPLAY_NAME_MAPPINGS = {"HTCQwenViggleLora": "HTC Qwen Viggle LoRA"}
