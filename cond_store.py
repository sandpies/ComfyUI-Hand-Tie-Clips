"""Disk copy of the ref2va conditioning cache, so a restart does not re-pay Qwen.

The in-memory cache in h3_ref_chain.py (`_QWEN_COND_CACHE`) is keyed by object
ids, which die with the process. This file keeps the same entries on disk under
a key built only from content: the prompt, every reference's bytes, the text
encoder's and the VAEs' fingerprints, and a hash of core's MiniMax H3 node file.
A hit returns the exact tensors that were encoded (dtype and values), so a run
served from disk renders the same as one that encoded.

Best effort throughout: anything that cannot be stored without pickling is not
stored, and any read problem is a miss (the bad file is deleted). Lives in the
user hop-cache folder (`<user>/h3_ref_chain_hops/qwen_cond/`), so it survives
restarts and the hop cache's "clear" (location user) empties it too.
"""
import hashlib
import json
import os
import sys

import safetensors
import torch
from safetensors.torch import save_file as _st_save

from . import store as _store

TAG = "HandTieClips"
DISK_COND_CACHE = True      # False = memory cache only (as before 2026-11-17)
VERSION = 1                 # bump when the stored layout or the key changes
BUDGET_BYTES = 4 * 1024 ** 3
SUBDIR = "qwen_cond"
EXT = ".cond.safetensors"


class _Unstorable(Exception):
    pass


def root():
    return os.path.join(_store.cache_root("user"), SUBDIR)


# ---------------------------------------------------------------- key

_CORE_HASH = {}


def core_hash(node_cls):
    """sha256 of the file that defines core's node, so a core update that changes
    how conditioning is built misses instead of serving the old encode."""
    try:
        path = sys.modules[node_cls.__module__].__file__
        st = os.stat(path)
    except Exception:  # noqa: BLE001
        return "?"
    k = (path, st.st_size, int(st.st_mtime))
    if k not in _CORE_HASH:
        with open(path, "rb") as fh:
            _CORE_HASH[k] = hashlib.sha256(fh.read()).hexdigest()[:16]
    return _CORE_HASH[k]


def disk_key(content, clip_fp, vae_fp, audio_vae_fp, core):
    """`content` = the id-free part of the memory key (prompt, sizes, flags,
    reference digests). -> hex key, or None."""
    if content is None:
        return None
    return _store.hop_key(None, {"v": VERSION, "content": list(content), "clip": clip_fp,
                                 "vae": vae_fp, "avae": audio_vae_fp, "core": core})


# ---------------------------------------------------------------- pack

def _pack(obj, flat):
    if isinstance(obj, torch.Tensor):
        if obj.is_nested or type(obj) is not torch.Tensor and not isinstance(obj, torch.nn.Parameter):
            raise _Unstorable(type(obj).__name__)
        name = f"t{len(flat)}"
        flat[name] = obj.detach().cpu().contiguous().clone()
        return {"__t": name}
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple)):
        return {"__l": [_pack(v, flat) for v in obj], "tuple": isinstance(obj, tuple)}
    if isinstance(obj, dict):
        if not all(isinstance(k, str) for k in obj):
            raise _Unstorable("non-str dict key")
        return {"__d": {k: _pack(v, flat) for k, v in obj.items()}}
    raise _Unstorable(type(obj).__name__)


def _unpack(obj, flat):
    if isinstance(obj, dict):
        if "__t" in obj:
            return flat[obj["__t"]]
        if "__l" in obj:
            vals = [_unpack(v, flat) for v in obj["__l"]]
            return tuple(vals) if obj.get("tuple") else vals
        if "__d" in obj:
            return {k: _unpack(v, flat) for k, v in obj["__d"].items()}
        raise ValueError("bad node")
    return obj


def pack(cond, latent):
    """-> (flat tensors, metadata) or None when anything needs pickling."""
    flat = {}
    try:
        tree = _pack(cond, flat)
    except _Unstorable:
        return None
    meta = {"htc_cond": json.dumps(tree, separators=(",", ":")), "htc_v": str(VERSION)}
    if latent is not None:
        packed = _store._latent_to_flat(latent)
        if packed is None:
            return None
        lflat, lmeta = packed
        for k, v in lflat.items():
            flat["lat." + k] = v
        meta["htc_lat"] = lmeta["htc"]
    return flat, meta


def unpack(flat, meta):
    if meta.get("htc_v") != str(VERSION):
        raise ValueError("version")
    cond = _unpack(json.loads(meta["htc_cond"]), flat)
    lat = None
    if "htc_lat" in meta:
        lflat = {k[4:]: v for k, v in flat.items() if k.startswith("lat.")}
        lat = _store._latent_from_flat(lflat, meta["htc_lat"])
        if lat is None:
            raise ValueError("latent")
    return cond, lat


# ---------------------------------------------------------------- io

def _path(key, base=None):
    return os.path.join(base or root(), key + EXT)


def get(key, base=None):
    """-> (cond, latent) or None."""
    if not DISK_COND_CACHE or not key:
        return None
    p = _path(key, base)
    if not os.path.isfile(p):
        return None
    try:
        with safetensors.safe_open(p, framework="pt", device="cpu") as fh:
            meta = fh.metadata() or {}
            flat = {k: fh.get_tensor(k) for k in fh.keys()}
        out = unpack(flat, meta)
    except Exception as e:  # noqa: BLE001 -- a bad file is a miss, never a failed run
        print(f"[{TAG}] cond disk cache: dropping unreadable {os.path.basename(p)} ({e})",
              flush=True)
        try:
            os.remove(p)
        except OSError:
            pass
        return None
    try:
        os.utime(p, None)   # most recently used
    except OSError:
        pass
    return out


def put(key, cond, latent, base=None, budget=None):
    """Store one entry. -> True if written."""
    if not DISK_COND_CACHE or not key:
        return False
    packed = pack(cond, latent)
    if packed is None:
        return False
    flat, meta = packed
    d = base or root()
    p = _path(key, d)
    tmp = p + ".tmp"
    try:
        os.makedirs(d, exist_ok=True)
        _st_save(flat, tmp, metadata=meta)
        os.replace(tmp, p)
    except Exception as e:  # noqa: BLE001
        print(f"[{TAG}] cond disk cache: write failed ({e})", flush=True)
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    sweep(d, BUDGET_BYTES if budget is None else budget, keep=p)
    return True


def sweep(d, budget, keep=None):
    """Delete least-recently-used entries until under `budget` bytes."""
    items = []
    try:
        names = os.listdir(d)
    except OSError:
        return 0
    for fn in names:
        if not fn.endswith(EXT):
            continue
        fp = os.path.join(d, fn)
        try:
            st = os.stat(fp)
        except OSError:
            continue
        items.append((st.st_mtime, st.st_size, fp))
    total = sum(s for _, s, _ in items)
    freed = 0
    for _, size, fp in sorted(items):
        if total - freed <= budget:
            break
        if fp == keep:
            continue
        try:
            os.remove(fp)
            freed += size
        except OSError:
            pass
    return freed
