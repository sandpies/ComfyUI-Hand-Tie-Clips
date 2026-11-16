"""SandTie HTTP routes (/h3_ref_chain/sandtie/*), 128px thumb cache, Auto-Wake writer, and Reference Bible CRUD."""
from __future__ import annotations

import asyncio
import hashlib
import os

SANDTIE_OPTIONS_ROUTE = "/h3_ref_chain/sandtie/options"
SANDTIE_WRITE_ROUTE = "/h3_ref_chain/sandtie/write"
SANDTIE_EXTRACT_ROUTE = "/h3_ref_chain/sandtie/extract_video"
SANDTIE_PRESET_ROUTE = "/h3_ref_chain/sandtie/preset"
SANDTIE_REFBANK_ROUTE = "/h3_ref_chain/sandtie/ref_bank"
SANDTIE_THUMB_ROUTE = "/h3_ref_chain/sandtie/thumb"

TAG = "HandTieClips-SandTie"


def _build_ref_thumb(src_path: str, width: int = 128) -> str | None:
    from . import refs as _refs
    try:
        from PIL import Image, ImageOps
    except Exception:
        return None
    if not src_path or not os.path.isfile(src_path):
        return None
    w = max(48, min(320, int(width or 128)))
    try:
        st = os.stat(src_path)
        key = f"{os.path.basename(src_path)}|{int(st.st_mtime)}|{st.st_size}|{w}"
    except Exception:
        key = f"{src_path}|{w}"
    tdir = _refs.thumb_cache_dir()
    digest = hashlib.sha1(key.encode("utf-8", "ignore")).hexdigest()[:24]
    out_path = os.path.join(tdir, f"{digest}_{w}.jpg")
    if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
        return out_path
    try:
        with Image.open(src_path) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA", "P"):
                rgba = im.convert("RGBA")
                bg = Image.new("RGB", rgba.size, (22, 24, 28))
                bg.paste(rgba, mask=rgba.split()[-1])
                im = bg
            elif im.mode != "RGB":
                im = im.convert("RGB")
            im.thumbnail((w, w), Image.Resampling.LANCZOS)
            tmp = out_path + ".tmp"
            im.save(tmp, format="JPEG", quality=84, optimize=True)
            os.replace(tmp, out_path)
        return out_path
    except Exception:
        return None


async def ensure_writer_ready(_llm, auto_wake: bool = True) -> tuple[bool, str]:
    conn = _llm.load_conn()
    backend = _llm.backend_name(conn.get("backend"))
    if await _llm.server_running_async(backend):
        return True, "running"
    if backend != "ninfer" or not auto_wake:
        return False, f"{_llm.active_label()} is not running."
    ok, msg = await _llm.start_process_async(name="ninfer")
    if not ok:
        return False, msg
    for _ in range(50):
        await asyncio.sleep(1.5)
        if await _llm.server_running_async("ninfer"):
            return True, "auto-started nInfer"
        err = _llm.startup_error("ninfer")
        if err:
            return False, f"nInfer stopped during startup: {err}"
    return False, "nInfer did not answer within 75s after auto-start."


def _wait_for_ninfer_exit(timeout_ms: int = 2500) -> int:
    stopped = 0
    try:
        import ctypes
        from ctypes import wintypes

        TH32CS_SNAPPROCESS = 0x00000002
        SYNCHRONIZE = 0x00100000
        PROCESS_TERMINATE = 0x0001
        INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260),
            ]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snap == INVALID_HANDLE_VALUE:
            return 0
        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
        try:
            ok = k32.Process32First(snap, ctypes.byref(pe))
            while ok:
                name = (pe.szExeFile or b"").decode("latin-1", "ignore").lower()
                if name == "ninfer-serve.exe":
                    h = k32.OpenProcess(PROCESS_TERMINATE | SYNCHRONIZE, False, pe.th32ProcessID)
                    if h:
                        if k32.TerminateProcess(h, 0):
                            print(f"[{TAG}] stopped {name} (pid {pe.th32ProcessID})", flush=True)
                            stopped += 1
                        k32.WaitForSingleObject(h, int(timeout_ms))
                        k32.CloseHandle(h)
                ok = k32.Process32Next(snap, ctypes.byref(pe))
        finally:
            k32.CloseHandle(snap)
    except Exception:
        pass
    return stopped


def register_sandtie_routes(instance, web) -> None:
    from .. import llm as _llm
    from .. import media as _media
    from .. import mv_solver as _mvs
    from . import catalogs as _cat
    from . import finisher as _fin
    from . import refs as _refs
    from . import vision_cv as _vcv
    from . import writer as _wr

    def _is_dry_only_prompt(json_data) -> bool:
        if not isinstance(json_data, dict):
            return False
        prompt_map = json_data.get("prompt")
        if not isinstance(prompt_map, dict) or not prompt_map:
            return False
        htc_nodes = [
            n for n in prompt_map.values()
            if isinstance(n, dict) and n.get("class_type") == "HandTieClips"
        ]
        if not htc_nodes:
            return False
        all_dry = all(
            isinstance(n.get("inputs"), dict) and str(n["inputs"].get("dry_run") or "off") == "on"
            for n in htc_nodes
        )
        if not all_dry:
            return False
        gpu_types = ("MiniMaxH3", "KSampler", "SamplerCustom", "VAEDecode", "VAEEncode")
        return not any(
            isinstance(n, dict) and any(gt in str(n.get("class_type") or "") for gt in gpu_types)
            for n in prompt_map.values()
        )

    def _free_writer_on_prompt(json_data):
        try:
            if not _llm.configured():
                return json_data
            if _is_dry_only_prompt(json_data):
                return json_data
            conn = _llm.load_conn()
            if conn.get("unload_on_run", True):
                spec = _llm.backend_spec(conn.get("backend"))
                if not spec.get("evictable", True):
                    if _llm.shares_this_gpu(conn.get("server_url")):
                        n_stopped = _llm.stop_process(conn.get("backend"))
                        n_waited = _wait_for_ninfer_exit(1500)
                        if n_stopped or n_waited:
                            print(f"[{TAG}] auto-stopped {spec['label']} before render", flush=True)
                else:
                    # Never block ComfyUI's aiohttp event loop waiting on HTTP unload
                    # + VRAM settle; dispatch asynchronously when inside an active loop.
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None
                    if loop is not None:
                        async def _bg_unload(url=conn.get("server_url") or "", mdl=conn.get("model") or ""):
                            try:
                                await _llm.unload_all(url, mdl)
                            except Exception:
                                pass
                        loop.create_task(_bg_unload())
                    else:
                        _llm.free_for_render()
        except Exception as exc:
            print(f"[{TAG}] on_prompt writer stop skipped: {exc!r}", flush=True)
        return json_data

    if hasattr(instance, "add_on_prompt_handler"):
        instance.add_on_prompt_handler(_free_writer_on_prompt)

    def _list_sandtie_videos():
        seen = set()
        out = []
        for f in _media.listing({"video"}):
            nm = str(f.get("name") or "").strip()
            if nm and nm not in seen:
                seen.add(nm)
                out.append(nm)
        try:
            inp_dir = _media.input_dir()
            if os.path.isdir(inp_dir):
                for nm in sorted(os.listdir(inp_dir)):
                    if nm in seen or _media.kind_of(nm) != "video":
                        continue
                    p = os.path.join(inp_dir, nm)
                    if os.path.isfile(p):
                        seen.add(nm)
                        out.append(nm)
        except Exception:
            pass
        return out

    def _resolve_sandtie_video(raw_name: str) -> str | None:
        clean = str(raw_name or "").strip().replace("\\", "/")
        if not clean:
            return None
        if clean.lower().startswith("h3_refs/"):
            clean = clean[len("h3_refs/"):]
        hit = _media.resolve(clean, kinds={"video"})
        if hit and os.path.isfile(hit):
            return hit
        base = os.path.basename(clean)
        if _media.kind_of(base) != "video":
            return None
        inp_dir = os.path.abspath(_media.input_dir())
        cand = os.path.abspath(os.path.join(inp_dir, base))
        if (cand == inp_dir or cand.startswith(inp_dir + os.sep)) and os.path.isfile(cand):
            return cand
        return None

    @instance.routes.get(SANDTIE_OPTIONS_ROUTE)
    async def _sandtie_options(request):
        try:
            conn = _llm.load_conn()
            running = await _llm.server_running_async(conn.get("backend"))
            lite = str(request.query.get("lite") or "").strip().lower() in ("1", "true", "yes")
            payload = {
                "ok": True,
                "running": running,
                "backend": conn.get("backend") or "lmstudio",
                "backend_label": _llm.backend_spec(conn.get("backend"))["label"],
                "model": conn.get("model") or "",
                "startup_error": "" if running else _llm.startup_error(conn.get("backend")),
            }
            if not lite:
                payload["catalog"] = _cat.ui_catalog()
            payload["audio_files"] = [f["name"] for f in _media.listing({"audio"})]
            payload["video_files"] = _list_sandtie_videos()
            return web.json_response(payload)
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=500)

    @instance.routes.post(SANDTIE_PRESET_ROUTE)
    async def _sandtie_preset(request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "expected JSON"}, status=400)
        body = body if isinstance(body, dict) else {}
        pid = str(body.get("id") or "").strip()
        raw_script = str(body.get("script") or "").strip()
        text = raw_script or _cat.load_preset_script(pid)
        if not text:
            return web.json_response({"ok": False, "error": f"Preset not found: {pid}"})
        if body.get("adapt"):
            dur_label = str(body.get("duration") or "").strip()
            frames = _mvs.DURATION_FRAMES.get(dur_label)
            try:
                duration_s = (frames / 24.0) if frames else float(dur_label.split()[0])
            except Exception:
                duration_s = 10.0
            raw_vf = body.get("voice_files")
            voice_files = [str(v or "").strip() for v in (raw_vf if isinstance(raw_vf, list) else ()) if str(v or "").strip()]
            flavors = body.get("flavors") if isinstance(body.get("flavors"), dict) else {}
            adapted = _fin.adapt_preset_script(
                text, ref_plan=str(body.get("ref_plan") or ""),
                duration_s=duration_s, voice_files=voice_files,
                flavors=flavors, brief=str(body.get("brief") or ""),
            )
            adapted["id"] = pid
            return web.json_response(adapted)
        return web.json_response({"ok": True, "id": pid, "script": text})

    @instance.routes.get(SANDTIE_THUMB_ROUTE)
    async def _sandtie_thumb(request):
        raw_file = str(request.query.get("file") or "").strip()
        src_kind = str(request.query.get("source") or "").strip().lower()
        if not raw_file:
            return web.Response(status=400, text="missing file")
        try:
            width = int(request.query.get("w") or 128)
        except Exception:
            width = 128
        if src_kind == "refmod" or _media.resolve(os.path.basename(raw_file), kinds={"image"}) is None:
            rm_mod = _refs._refmod_module()
            if rm_mod is not None and rm_mod.resolve(raw_file) is not None:
                jpg = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: rm_mod.thumb_bytes(raw_file, member_idx=0, width=width)
                )
                if jpg:
                    headers = {"Cache-Control": "public, max-age=31536000, immutable" if request.query.get("v") else "public, max-age=300"}
                    return web.Response(body=jpg, content_type="image/jpeg", headers=headers)
                if src_kind == "refmod":
                    return web.Response(status=404, text="no preview")
        fname = os.path.basename(raw_file)
        fpath = _media.resolve(fname, kinds={"image"})
        if not fpath or not os.path.isfile(fpath):
            return web.Response(status=404, text="not found")
        thumb_path = await asyncio.get_running_loop().run_in_executor(None, _build_ref_thumb, fpath, width)
        target = thumb_path if (thumb_path and os.path.isfile(thumb_path)) else fpath
        headers = {"Cache-Control": "public, max-age=31536000, immutable" if request.query.get("v") else "public, max-age=300"}
        return web.FileResponse(target, headers=headers)

    def _refbank_payload(**extra):
        return {
            "ok": True,
            "items": _refs.load_ref_bank(),
            "audio_files": [f["name"] for f in _media.listing({"audio"})],
            "has_refmods": bool(_refs._refmod_module() is not None),
            **extra,
        }

    @instance.routes.get(SANDTIE_REFBANK_ROUTE)
    async def _sandtie_refbank_get(_request):
        try:
            return web.json_response(_refbank_payload())
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=500)

    @instance.routes.post(SANDTIE_REFBANK_ROUTE)
    async def _sandtie_refbank_post(request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "expected JSON"}, status=400)
        body = body if isinstance(body, dict) else {}
        action = str(body.get("action") or "list").strip().lower()
        try:
            if action == "list":
                return web.json_response(_refbank_payload())
            if action == "sync_refmods":
                return web.json_response({
                    "ok": True,
                    "items": _refs.sync_refmods_to_bank(),
                    "audio_files": [f["name"] for f in _media.listing({"audio"})],
                    "has_refmods": bool(_refs._refmod_module() is not None),
                })
            if action == "save":
                saved = _refs.upsert_ref_bank_item(body.get("item") if isinstance(body.get("item"), dict) else body, user_edited=True)
                return web.json_response(_refbank_payload(item=saved))
            if action == "delete":
                removed = _refs.delete_ref_bank_item(
                    str(body.get("id") or ""),
                    file_name=str(body.get("file") or ""),
                    source=str(body.get("source") or ""),
                )
                return web.json_response(_refbank_payload(removed=removed))
            if action == "import_rail":
                items = _refs.import_rail_to_ref_bank(str(body.get("ref_plan") or ""), voice_files=body.get("voice_files") or ())
                return web.json_response({
                    "ok": True,
                    "items": items,
                    "audio_files": [f["name"] for f in _media.listing({"audio"})],
                    "has_refmods": bool(_refs._refmod_module() is not None),
                })
            if action == "scan":
                raw_file = str(body.get("file") or "").strip()
                src_kind = str(body.get("source") or "image").strip().lower()
                role = str(body.get("role") or "subject").strip().lower()
                auto_wake = bool(body.get("auto_wake", True))
                rm_mod = _refs._refmod_module()
                is_rm = (src_kind == "refmod") or (
                    _media.resolve(os.path.basename(raw_file)) is None
                    and rm_mod is not None
                    and rm_mod.resolve(raw_file) is not None
                )
                ready, wake_msg = await ensure_writer_ready(_llm, auto_wake=auto_wake)
                if not ready:
                    return web.json_response({"ok": False, "error": wake_msg})
                conn = _llm.load_conn()
                if not conn.get("model"):
                    found = await _llm.models(conn["server_url"])
                    if found:
                        conn["model"] = found[0]["id"]

                async def complete_fn(messages, schema=None, temperature=0.1, max_tokens=320):
                    return await _llm.complete(conn["server_url"], conn["model"], messages, schema=schema, temperature=temperature, max_tokens=max_tokens)

                if is_rm:
                    if rm_mod is None or rm_mod.resolve(raw_file) is None:
                        return web.json_response({"ok": False, "error": f"Could not resolve RefMod: {raw_file}"})
                    urls = await asyncio.get_running_loop().run_in_executor(
                        None, lambda: rm_mod.vision_data_urls(raw_file, max_images=2, max_side=1024)
                    )
                    if not urls:
                        return web.json_response({"ok": False, "error": f"RefMod {raw_file} has no kept look photos to Eye Scan."})
                    prompt_key = role if role in _vcv.ROLE_PROMPTS else "subject"
                    content = [{"type": "text", "text": _vcv.ROLE_PROMPTS[prompt_key]}]
                    for u in urls:
                        content.append({"type": "image_url", "image_url": {"url": u}})
                    raw_scan = await complete_fn([{"role": "user", "content": content}], schema=None, temperature=0.2, max_tokens=260)
                    scanned = _vcv._clean_desc(raw_scan, 480, strip_studio=(prompt_key in ("subject", "auto")))
                    fname = _refs._clean_ref_file(raw_file, "refmod")
                    src_save = "refmod"
                else:
                    fname = os.path.basename(raw_file)
                    fpath = _media.resolve(fname)
                    if not fpath or not os.path.isfile(fpath):
                        return web.json_response({"ok": False, "error": f"Could not resolve image in h3_refs: {fname}"})
                    scanned = await _vcv.scan_reference_file(fpath, role if role in ("subject", "place", "prop") else "auto", complete_fn)
                    src_save = "image"
                if not scanned:
                    return web.json_response({"ok": False, "error": "Eye Scan returned empty description."})
                import re
                cleaned = _refs.clean_subject_scan_desc(scanned) if role == "subject" else re.sub(r"^(?:Set|Prop):\s*", "", scanned, flags=re.I).strip()
                existing = _refs.find_ref_bank_entry(file_name=fname, source=src_save) or {}
                saved_payload = {
                    "id": body.get("id") or existing.get("id") or "",
                    "name": body.get("name") or existing.get("name") or "",
                    "tag": body.get("tag") or existing.get("tag") or "",
                    "role": role,
                    "file": fname,
                    "source": src_save,
                    "voice": body.get("voice") or existing.get("voice") or "",
                    "desc": cleaned or scanned,
                    "locked": body.get("locked") or existing.get("locked") or "",
                    "context": body.get("context") or existing.get("context") or "",
                }
                if src_save == "refmod":
                    saved_payload["strength"] = body.get("strength") if "strength" in body else existing.get("strength", 1.0)
                    saved_payload["step_curve"] = body.get("step_curve") or existing.get("step_curve") or "full"
                saved = _refs.upsert_ref_bank_item(saved_payload, user_edited=True)
                return web.json_response(_refbank_payload(item=saved))
            return web.json_response({"ok": False, "error": f"Unknown ref_bank action: {action}"}, status=400)
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)})

    @instance.routes.post(SANDTIE_EXTRACT_ROUTE)
    async def _sandtie_extract(request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "expected JSON"}, status=400)
        video_file = str((body or {}).get("video_file") or "").strip()
        in_sec = float((body or {}).get("in_sec") or 0.0)
        out_sec = float((body or {}).get("out_sec") or 0.0)
        auto_wake = bool((body or {}).get("auto_wake", True))
        if not video_file:
            return web.json_response({"ok": False, "error": "Pick, drop, or upload a video file first."})
        vpath = _resolve_sandtie_video(video_file)
        if not vpath or not os.path.isfile(vpath):
            return web.json_response({"ok": False, "error": f"Could not resolve video file in input/ or h3_refs/: {video_file}"})
        ready, wake_msg = await ensure_writer_ready(_llm, auto_wake=auto_wake)
        if not ready:
            return web.json_response({"ok": False, "error": wake_msg})
        conn = _llm.load_conn()
        if not conn.get("model"):
            found = await _llm.models(conn["server_url"])
            if found:
                conn["model"] = found[0]["id"]

        async def complete_fn(messages, schema=None, temperature=0.25, max_tokens=2200):
            return await _llm.complete(conn["server_url"], conn["model"], messages, schema=schema, temperature=temperature, max_tokens=max_tokens)

        try:
            res = await _vcv.extract_video_to_plan(vpath, complete_fn, in_sec=in_sec, out_sec=out_sec)
            res["woke_writer"] = wake_msg == "auto-started nInfer"
            return web.json_response(res)
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)})

    @instance.routes.post(SANDTIE_WRITE_ROUTE)
    async def _sandtie_write(request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "expected JSON"}, status=400)
        if not isinstance(body, dict):
            return web.json_response({"ok": False, "error": "expected JSON object"}, status=400)

        stage = str(body.get("stage") or "write").strip().lower()
        brief = str(body.get("brief") or "").strip()
        plan = str(body.get("plan") or "").strip()
        dur_label = str(body.get("duration") or "").strip()
        ref_plan = str(body.get("ref_plan") or "")
        start_file = str(body.get("start_image_file") or "").strip()
        raw_vf = body.get("voice_files")
        voice_files = [str(v or "").strip() for v in (raw_vf if isinstance(raw_vf, list) else ()) if str(v or "").strip()]
        flavors = body.get("flavors") if isinstance(body.get("flavors"), dict) else {}
        extracted_video = body.get("extracted_video") if isinstance(body.get("extracted_video"), dict) else None
        prev_hop_context = str(body.get("prev_hop_context") or "").strip()
        auto_wake = bool(flavors.get("wake_writer", flavors.get("auto_wake", True)))

        frames = _mvs.DURATION_FRAMES.get(dur_label)
        try:
            duration_s = (frames / 24.0) if frames else float(dur_label.split()[0])
        except Exception:
            duration_s = 10.0

        if stage in ("skeleton", "cpu"):
            try:
                out = await _wr.run_sandtie_write(
                    stage, brief or "Perform the configured scene.", complete_fn=None,
                    ref_plan=ref_plan, duration_s=duration_s,
                    start_image="1" if start_file else None, plan=plan,
                    voice_files=voice_files, flavors=flavors, extracted_video=extracted_video,
                    prev_hop_context=prev_hop_context,
                )
                out["duration_s"] = round(duration_s, 3)
                return web.json_response(out)
            except Exception as exc:
                return web.json_response({"ok": False, "error": str(exc)})

        if not brief and not extracted_video and not (stage == "dialogue" and str(flavors.get("current_block") or plan or "").strip()):
            auto_bits = []
            for dk in ("explicit", "combat", "pose", "place", "wardrobe", "character", "style"):
                for opt in _cat.resolve_dial_opts(dk, flavors.get(dk)):
                    lbl = _wr._clean_ui_label(opt.get("label") or "")
                    if lbl:
                        auto_bits.append(lbl)
                        break
            if auto_bits:
                brief = "; ".join(auto_bits[:4])
            else:
                return web.json_response({"ok": False, "error": "Type a scene brief (or pick SandTie dials / extract a video) first."})

        ready, wake_msg = await ensure_writer_ready(_llm, auto_wake=auto_wake)
        if not ready:
            return web.json_response({"ok": False, "error": wake_msg})

        conn = _llm.load_conn()
        if not conn.get("model"):
            found = await _llm.models(conn["server_url"])
            if found:
                conn["model"] = found[0]["id"]
            else:
                return web.json_response({"ok": False, "error": "no model selected -- click ⚙ beside Writer status (or WRITE -> Settings) and pick one."})

        def encode():
            try:
                lab = _refs.sandtie_labels(ref_plan, voice_files=voice_files)
            except Exception:
                lab = {"pictures": [], "audios": []}
            ims = []
            for p in lab.get("pictures") or []:
                if not p.get("file"):
                    continue
                url = None
                if p.get("source") == "refmod":
                    try:
                        from .. import refmod as _refmod
                        mems = p.get("members") if isinstance(p.get("members"), list) else None
                        url = _refmod.vision_data_url(p["file"], member_idx=(mems[0] if mems else 0))
                    except Exception:
                        url = None
                else:
                    url = _media.vision_data_url(p["file"])
                if url:
                    ims.append({"tag": p["tag"], "data_url": url})
            start_url = _media.vision_data_url(start_file) if start_file else None
            start_path = _media.resolve(start_file) if start_file else ""
            return ims, start_url, start_path

        try:
            images, start_url, start_path = await asyncio.get_running_loop().run_in_executor(None, encode)
        except Exception:
            images, start_url, start_path = [], None, ""

        notes = []
        if wake_msg == "auto-started nInfer":
            notes.append("nInfer was stopped after your last render — auto-started it in VRAM.")
        write_temp = max(0.9, float(conn.get("temperature") or 0.95)) if conn.get("backend") == "ninfer" else float(conn.get("temperature") or 0.8)

        async def complete_fn(messages, schema=None, temperature=None, max_tokens=None):
            t_use = write_temp if temperature is None else float(temperature)
            kw = {"schema": schema, "temperature": t_use}
            if max_tokens is not None:
                kw["max_tokens"] = int(max_tokens)
            try:
                return await _llm.complete(conn["server_url"], conn["model"], messages, **kw)
            except _llm.LLMError as exc:
                if _llm.has_images(messages) and "HTTP 4" in str(exc):
                    notes.append("model processed labels as text-only")
                    return await _llm.complete(conn["server_url"], conn["model"], _llm.text_only(messages), **kw)
                raise

        try:
            out = await _wr.run_sandtie_write(
                stage, brief, complete_fn=complete_fn, ref_plan=ref_plan,
                duration_s=duration_s, images=images, start_image=start_url,
                start_image_path=start_path or "", plan=plan, voice_files=voice_files,
                flavors=flavors, extracted_video=extracted_video,
                prev_hop_context=prev_hop_context, resolve_file_fn=_media.resolve,
            )
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)})

        if notes:
            out["warnings"] = list(out.get("warnings") or []) + notes
        out["duration_s"] = round(duration_s, 3)
        out["running"] = await _llm.server_running_async(conn.get("backend"))
        if not conn.get("keep_warm") and _llm.backend_spec(conn.get("backend")).get("evictable", True):
            try:
                await _llm.unload(conn["server_url"], conn["model"])
            except Exception:
                pass
        return web.json_response(out)
