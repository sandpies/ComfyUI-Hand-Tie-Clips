# H3 context windows × HTC: proposal for Claude

Written 2026-10-30 (opencode). **PLAN ONLY. No code changed.**
Paths relative to `D:\ComfyUI\custom_nodes\ComfyUI-Hand-Tie-Clips`. Core paths are relative to `D:\ComfyUI`.
Line numbers drift; search for the quoted symbol when they miss.

Source of the feature: upstream PR **Comfy-Org/ComfyUI#17425** (kijai), merged 2026-10-30 as `6651247` —
"Support context windows for MiniMax-H3". This tree is pinned to core `d07dff45` (2026-10-22), which has the
multimodal context-window substrate (LTXAV) but **no MiniMax H3 support at all** — verified:
`comfy_extras/nodes_context_windows.py:138-144` registers only `ContextWindowsManual` / `WanContextWindowsManual` /
`LTXVContextWindows`, and `comfy/model_base.py:2191 class MiniMaxH3` has neither `context_window_modality_dims`
nor `resize_cond_for_context_window`.

---

## 0. Verdict, in one paragraph

This is not a better `_keyframe_in`. It is a different **execution model** for long H3 clips: a whole clip's latent
is denoised in *one* trajectory, with the sequence sliced into overlapping temporal windows that are re-attended and
fused at every step. HTC currently cannot do that; every long clip is N independent denoise passes joined afterwards
(`_crossfade`) or continued by holding already-drawn steps (`known`). Those joins are the bug class HTC has spent
months on (`chunk_join`, `pin_chunk_start`, seam feathering, `_calibrate_ht_latent`). Windows remove the *seam*, not
the *drift* — worth being precise about that with the user. The immediately useful win is the upsampler: it can lift
the whole-clip ceiling from "fits in VRAM" to "fits in RAM", without tiles or crossfades, with audio kept in sync by
core's own H3 modality mapping. The chain-level "fused take" is the bigger prize and the bigger risk; it should not
ship until the upsampler proves the mechanism.

---

## 1. What the feature actually is (mechanics, not marketing)

- A node patches a **handler** onto the model: `model.model_options["context_handler"] = IndexListContextHandler(...)`
  (`comfy_extras/nodes_context_windows.py:43-57`).
- Every step, `comfy/samplers.py:209-212` calls that handler instead of the plain cond batch. The handler builds the
  window list for this timestep, runs the model **once per window**, and fuses the window outputs back into one
  `x_t` (`comfy/context_windows.py:572-631`, `:636-710`, `:711-740`).
- Consequence: windows are **not** chunks. There is one sigma schedule, one noise field, one latent; windows only
  decide how much temporal context each forward sees. Overlapping windows see the *same* `x_t`.
- The current window is exposed to wrappers/post-CFG functions: `model_options["transformer_options"]["context_window"] = window`
  (`comfy/context_windows.py:685`). This is the hook HTC needs for any per-window model-side work.
- Cost per step is `n_windows` forwards; today it is `n_chunks` full schedules. Roughly equal compute, but **peak
  VRAM is bounded by window length, not clip length**.
- PR #17425 adds the H3 pieces:
  - per-modality temporal axes (`modality_dims`): H3 audio is `[B,32,2,T]`, time on the last axis;
  - `map_context_window_to_modalities` (`model_base.py`, new): audio is split at the video latents' pixel-frame
    boundaries, so audio windows line up with `FRAME_PER_TOKEN=(1,4,4,4,4)`;
  - `_window_payload`: keyframes/refs cropped to the window on 5-latent chunk starts, `resolved_frame_index`
    re-anchored (with a `causal_anchor_index` shift), audio guide cropped at `5/3 * frame`, and
    `cond_video_latents`/`cond_audio_latents` rebuilt in packed order;
  - `MiniMaxH3ContextWindows` node: `context_length` min 22, step 17, default 124 f; overlap min 5, default 39 f;
    converts to latents via `video_latent_t` (`comfy_extras/nodes_minimax_h3.py:44-45`), i.e. windows are
    **`5n+2` latent steps**, `dim=2`, `causal_window_fix=False`, FreeNoise on by default, PYRAMID fuse.

`5n+2` is the same invariant HTC already lives by: `CHUNK_FRAMES=102` / `CHUNK_OVERLAP=17`
(`tiled_upsampler.py:53-54`) are 32 / 7 latent steps. Upstream's defaults (124 / 39 f) are 37 / 12 steps.

---

## 2. Why this matters to HTC: the seam is a scheduling artifact

`tiled_upsampler.upsample()` builds a chunk plan and runs each chunk at the *start* sigma
(`tiled_upsampler.py:1629-1724`, `:1784-1860`). Chunk 2 re-noises frames it already saw, then the overlap is
crossfaded (`_crossfade`, `:1524`) or held (`known`, `:1436-1440`, `:1517-1519`). `known` only works on whole-frame
chunks and is silently downgraded to a crossfade when the grid needs tiles (`:1447-1450`). That asymmetry is exactly
why small cards see the worst joins.

Under windows there is nothing to join: chunk boundaries become window overlaps inside one trajectory, and the
overlap is fused by weight, not blended after the fact. This is also the honest reading of the repo's own note
(CLAUDE.md: "one pass over the joined film lets the recipe's own 17-frame chunk crossfades run across the joins") —
windows make that literal.

What windows do **not** fix: the photocopy/ratchet drift (REFINE_V2_BUILD_PLAN.md §A1). A continuous pass still
accumulates drift; it just does it without a discrete seam. Any claim of "seamless" must be backed by the MAD profile
in §6.

---

## 3. Applications, ranked by value ÷ risk

### 3.1 (Phase 2) Whole-clip upsampler pass — the win to build first

Today: `chunking=False` is only allowed while the clip fits `WHOLE_CLIP_MAX * tile_tokens` tokens
(`:123`, gating at `:1691-1695`). A 192 f clip at 2 MP blows past it, so it chunks.

With a window handler installed, a whole-clip `redraw_chunk` carries only `window × tile` per forward. That raises the
ceiling from VRAM to system RAM, and removes crossfade joins entirely for the Regen2K path. The existing machinery
stays: HTC's step loop, tile feather merge, structure lock, OOM budget ladder.

Two concrete code consequences, both small:

1. **Budget basis must become the window, not the clip.** `redraw_chunk` derives the tile grid and the logged token
   count from `t` (`:1393-1394`, `:1406-1408`); `upsample()` logs the same basis (`:1845-1848`). Under windows the
   forward carries `min(t, window_steps)`, so `tile_grid`/`_LAST_TOKENS`/`solve_grid` must be called with
   `window_t`. Otherwise the budget thinks a 57-step clip is one forward and refuses / over-tiles.
2. **`plan` collapses to one entry** (`:1702`), so `glats`/`raw_cvs`/`anchors` all become single-element lists and the
   join loop degenerates. That part is free.

Effort: small. Risk: medium (see §4).

### 3.2 (Phase 3, conditional) `join=fused` for the hop chain

The chain's join is a pin: hop k+1 inherits hop k's tail latent through Motion-Context rows and re-noises it. Windows
would instead sample the whole section as one trajectory, with each hop's prompt assigned to its windows by
`get_region_index` (`comfy/context_windows.py:92-94`, `split_conds_to_windows`) — one cond per window, chosen by the
window's centre.

That deletes the seam class outright instead of repairing it. It also deletes, by necessity:

- per-hop LoRA swaps (`_swap_ref_pin_wrapper`, `h3_ref_chain.py:3323-3346`) — one model for the whole pass;
- per-hop `steps`/`speed_mode`/sigma changes;
- previs pins and `minimax_keyframes` at hop boundaries (there is no "previous hop" to pin yet);
- `ht_seam_fix`, `_ht_mc_inpaint_head`, `_calibrate_ht_latent`, `seam_feather`, `tail_feather` — all of which exist
  only to hide joins.

So this is a *mode*, not a replacement: "one continuous take, same LoRA, same steps, refs only". It fits long
single-take shots (vlog/MV verse with no cut), not the multi-look, per-hop-LoRA work HTC is actually used for.
Do not start it before 3.1 reports.

### 3.3 (Phase 1) Adopt-only details — no new tech required

- `_keyframe_in` (`:539-566`) keeps a keyframe step only when it is **wholly** inside `[f0, f1)`
  (`f0 <= pos and pos + span <= f1`). Core's `_window_payload` keeps a 5-latent chunk that merely **overlaps** the
  window start and explicitly allows it to begin a few frames before the origin. HTC's stricter rule silently drops
  a guide that straddles a boundary; `pin_chunk_start` covers the frame-0 case only. Worth matching core.
- Local copies of core constants: `FRAME_PER_TOKEN` / `FRAME_RESCALE` (`:144-145`) duplicate
  `comfy/ldm/minimax/model.py:30-31`; `refine_blend.py:44` duplicates `FRAME_PER_TOKEN` again. Import from core with
  a local fallback so the three cannot drift.
- `_cond_latents` ordering (keyframes then refs) is now an explicit core contract. HTC relies on core rebuilding
  `cond_video_latents` from `minimax_keyframes`/`minimax_refs` each sample; any place HTC builds or mutates those
  lists must keep that order.

---

## 4. Integration contracts and hazards (the part that will bite)

Each of these is a *must-test-before-claiming*, not a footnote.

**C0. Budget basis.** See §3.1(1). Test: a 192 f whole-clip pass must compute the same tile grid as the 102 f chunk
today, at the same `tile_tokens`.

**C1. `structure_lock` / `detail_sigma` are full-time, windows are time slices.** `structure_lock_fn`
(`:1235-1273`) closes over a whole-tile tensor and is installed as a post-CFG function; under windows it receives the
*time-sliced* `x` and will shape-mismatch. Fix path: read
`transformer_options["context_window"]` (`context_windows.py:685`) inside the lock and narrow the reference to
`window.index_list` (and to the window's modality for audio). Until that exists, the prototype must run with
`structure_lock=0.0` and `detail_sigma=0.0` and say so in the log. This is the single largest hidden cost of 3.1.

**C2. The strided guide (`STRIDE_KEY`) is HTC's, not core's.** `add_guide` (`:660-669`) appends the guide as a
keyframe at frame 0 with `htc_grid_stride=factor`. Core's `_window_payload` crops keyframes on 5-latent chunk starts
and re-anchors `resolved_frame_index`; it knows nothing about the stride, and the layout patch reads `STRIDE_KEY`
(`:133`, `upscale_guide.py`). Two options: (a) verify core's crop is stride-safe (time axis is shared, spatial is
already 1/factor), or (b) attach an instance-level override — `model.resize_cond_for_context_window = types.MethodType(fn, model)`
on `model_patcher.model` — that handles `minimax_payload` itself, the way `_window_payload` does. Preview: (a) first,
(b) if the guide misanchors.

**C3. Frozen audio + `denoise_mask`.** `sample_tile` freezes audio with a nested zero mask (`:1163-1173`). Core
resizes only `audio_denoise_mask` per window (PR) and fuses per modality; whether a zero mask survives the
window fan-out *and* the fuse is untested. Test: guided pass with hard-muted audio; assert audio latent is
bit-identical to input after one windowed step.

**C4. `h3_cache` residual reuse.** `h3_cache.py` caches block residuals keyed by feature signature/timestep
(`:143-220`). Windowed forwards change sequence length and step count per window. Verify the key includes enough to
prevent serving window A's residual to window B, and that a windowed pass does not silently poison a cached hop.

**C5. Sparse attention.** `apply_sparse_attention` (`:1103`) plus `_h3sla_protected_ranges` are computed per forward
from the layout. Under windows the layout is rebuilt per window (good), but the block-sparse map config may assume a
full-clip length. Test at `attention=sparse` before enabling the flag by default.

**C6. FreeNoise vs `noise=film`.** `freenoise=True` shuffles the noise field (`context_windows.py:396-419`,
`:767-780`). HTC's `noise="film"` already draws one film-wide field and slices it per chunk (`:1381-1385`). Running
both double-shuffles. Rule: `freenoise = (noise != "film")`.

**C7. Audio edge rounding.** Core derives audio window edges **proportionally**
(`round(s * audio_T / total)` in `map_context_window_to_modalities`); HTC uses exact `5/3` (`audio_span`, `:242-244`).
Identical for well-formed lengths, divergent otherwise. Log both and assert equality once per run rather than
trusting it.

**C8. Reference cost per window.** `minimax_refs` have no temporal extent, so they ride **every** window: per-window
sequence = window + all ref rows + guide. With 3 picture/video refs this can exceed one chunk's current budget. The
budget solver must count refs once per window (it already counts them once per tile, `_cond_extra_tokens`, `:1274`),
which means the tile grid may need to grow even though the clip does not.

**C9. Version gate.** Nothing here exists before core `6651247`. Probe with
`hasattr(comfy.model_base.BaseModel, "context_window_modality_dims")` (or the presence of `MiniMaxH3ContextWindows`
in `NODE_CLASS_MAPPINGS`), log one line, and fall back to today's path. Users pin core versions; a missing gate turns
into an ImportError at queue time, which is the worst failure mode this repo has.

---

## 5. Phases

### Phase 0 — capability probe + docs (no behavior change)
- `tiled_upsampler._core_windows_ready() -> bool`; one log line in `upsample()`:
  `context windows: available (core 6651247+)` / `unavailable (core too old)`.
- New checker `tools/check_context_windows_probe.py` covering: both branches, missing attribute, attribute raising.
  Mutants: probe returns True unconditionally; probe swallows exceptions and returns True.
- Docs: one paragraph in README upsample section + THIRD_PARTY_NOTICES unchanged (upstream core, not vendored).

### Phase 1 — adopt-only details (independent, safe)
- `_keyframe_in` overlap semantics + regression test: a 5-latent guide whose chunk starts 4 frames before
  `f0` must be kept and re-anchored, not dropped.
- Core constants with local fallback; assert equality when both exist (assert, don't silently prefer one).
- Checkers: `tools/check_all.py` must stay green (currently 58/58); add mutants for the crop rule.

### Phase 2 — `upsample_windows` (the prototype)
Scope: Regen2K path, `chunking` off, **`structure_lock=0`, `detail_sigma=0`, `tiling` on as usual**, guide allowed.
`chunking=False` currently falls back to chunked when the clip exceeds `WHOLE_CLIP_MAX * tile_tokens`
(`:1689-1695`); with windows on, that gate must test the **window** token count instead, or it will silently undo
the switch. Grep `WHOLE_CLIP_MAX` and change the gate and its log line together.
- New switch appended at the **end** of the widget tail: `upsample_windows` (bool, default False) on
  `HTCUpsampleSettings` and `HandTieClips`, i.e. after `regen2k_cond` (today's last widget). The tail assertions in
  `tools/check_workflows.py:112-116` and `tools/check_widget_order.py` must move in the same commit, and
  `check_upsample_settings` must own + hide it correctly. No other widget moves.
- Implementation: build the handler directly (no node), attach to a model clone, keep `redraw_chunk` intact:
  ```python
  # sketch — verify every symbol against the upgraded core before writing it
  import comfy.context_windows as cw
  from comfy_extras.nodes_minimax_h3 import video_latent_t
  m = model.clone()
  m.model_options["context_handler"] = cw.IndexListContextHandler(
      context_schedule=cw.get_matching_context_schedule(cw.ContextSchedules.STATIC_STANDARD),
      fuse_method=cw.get_matching_fuse_method(cw.ContextFuseMethods.PYRAMID),
      context_length=video_latent_t(window_frames),      # 5n+2 steps
      context_overlap=min(video_latent_t(overlap_frames), video_latent_t(window_frames) - 5),
      dim=2, freenoise=(noise != "film"), causal_window_fix=False)
  cw.create_prepare_sampling_wrapper(m)                   # VRAM estimator only
  ```
  `plan = [(0, 0, tv, frames_in(tv))]`; `tile_grid`/token logging use `window_t` (C0).
- Acceptance: (a) one window ≥ clip length reproduces today's whole-clip output within fp noise; (b) 192 f @ 2 MP
  completes with `structure_lock=0`; (c) peak VRAM ≤ today's chunked peak; (d) join MAD profile (§6) no worse at
  every 17-frame boundary; (e) wall time within 1.25×.
- Failure = keep the switch, default off, report the numbers. No removal of the chunk path.

### Phase 3 — `join=fused` (only after Phase 2 passes)
- New `join` option; requires equal LoRA/steps per hop and `hand_tie`/previs pins off; refuse loudly otherwise.
- Hops become window spans; conds assigned by `split_conds_to_windows` + `get_region_index`; audio is the section's
  one track.
- Acceptance: same-seed A/B vs `hand_tie` at 4+ hops, 8 steps: join MAD ≤ baseline, texture_probe mid band ≤
  baseline, no new audio clicks at hop times, wall time within 1.4×.

### Phase 4 — optional: windowed refine
`_refine_sampled` currently re-samples per hop. A windowed refine over the whole section would remove its own join
artifact. Only if Phase 3 exists; do not scope it now.

---

## 6. A/B proof protocol (repo law: one change per render)

- Material: a 192 f (3×102/17) clip at 2 MP, same seed, same sigmas, Regen2K LoRA, 8 steps where applicable.
- Metrics, all on the same file:
  1. **Join MAD profile** — per 17-frame boundary, mean abs delta vs the 5-frame neighbourhood median (the metric
     used in the 10-28 join investigations). Report every boundary, not the average.
  2. **texture_probe mid band** — drift over the clip.
  3. **Peak VRAM** and wall time (the upsampler already prints both).
  4. **Audio**: RMS delta across each join, and overall length match.
- Pass = no boundary worse than baseline by >20% MAD, peak VRAM not higher, wall time ≤1.25×, audio deltas ≤ baseline.
- Store the A/B pair in `workflows/` only if the switch ships on; otherwise keep it in `tools/` as a dry-run script.

---

## 7. What not to do

- Do not wire upstream's `MiniMaxH3ContextWindows` node into shipped workflows. It is marked experimental upstream and
  needs a core version most users do not have.
- Do not delete or default-off `chunking`, `chunk_join`, `known`, or `pin_chunk_start`. The window path is additive;
  the chunk path is the fallback and the comparison.
- Do not enable the window path with `structure_lock > 0` or `detail_sigma > 0` until C1 is implemented and tested.
- Do not touch `_keyframe_in` semantics and the window path in the same commit (Phase 1 vs Phase 2).
- Do not add the widget before Phase 2's A/B passes; the tail is fragile (105 slots on the chain node, owned/hidden
  rules in `check_upsample_settings`).
- Do not claim "seamless" from a single watch. The MAD profile is the claim.

---

## 8. Open questions for the user

1. Is the destination the **upsampler** only (Phase 2), or do we also want the "one continuous take" chain mode
   (Phase 3) even at the cost of dropping per-hop LoRAs and previs pins?
2. Which window length do we standardize on: 102/17 (HTC's current chunk), 124/39 (upstream default), or expose both?
3. Is a core-version bump acceptable in a release note ("requires ComfyUI ≥ 6651247 for `upsample_windows`"), or must
   HTC keep running on older cores with the flag absent from the UI?
4. Do we accept the extra forward count (windows × tiles per step) in exchange for flat VRAM, or should Phase 2 also
   keep a "windows only when the clip does not fit" auto rule?

---

## 9. Facts checked against this tree (2026-10-30)

| Claim | Where |
|---|---|
| Context handler read per step by the sampler | `comfy/samplers.py:209-212` |
| Handler fans out per window per step, fuses into one latent | `comfy/context_windows.py:572-631`, `:636-710`, `:711-740` |
| Current window visible to wrappers | `comfy/context_windows.py:685` |
| Handler ctor args used by the prototype sketch | `comfy/context_windows.py:342-357` |
| FreeNoise path needs the sampler wrapper | `comfy/context_windows.py:767-786` |
| No H3 window support in this core | `comfy_extras/nodes_context_windows.py:138-144`, `comfy/model_base.py:2191` |
| H3 latent length law `5k+2` | `comfy_extras/nodes_minimax_h3.py:44-45` |
| HTC chunk = 32/7 latent steps | `tiled_upsampler.py:53-54` |
| Whole-clip ceiling is token-based | `tiled_upsampler.py:123`, `:1691-1705` |
| Tile grid + token log derive from clip length | `tiled_upsampler.py:1393-1408`, `:1845-1848` |
| `known` continuation disabled under tiling | `tiled_upsampler.py:1447-1450` |
| Strict "wholly inside" keyframe crop | `tiled_upsampler.py:539-566` |
| Strided guide keyframe | `tiled_upsampler.py:133`, `:660-669` |
| Frozen-audio mask | `tiled_upsampler.py:1163-1173` |
| Structure lock is a full-tile post-CFG function | `tiled_upsampler.py:1235-1273` |
| Duplicate frame constants | `tiled_upsampler.py:144-145`, `refine_blend.py:44` vs `comfy/ldm/minimax/model.py:30-31` |
| Residual cache keyed by feature signature | `h3_cache.py:143-220` |
