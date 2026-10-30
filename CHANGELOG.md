# Changelog

User-facing. The files named here are in the repository, not in the installed
pack — the published package excludes them.

## Unreleased

- **Upsampler: `structure_lock` (default 0, off).** Regen2K starts each chunk from sigma 0.8, mostly noise, so every chunk and tile can re-imagine faces, hands and line work. When two chunks re-imagine the same overlap differently, the crossfade blends them. `structure_lock` (0..1) moves each step's clean-frame prediction toward the 3D-upscaled source below `lock_sigma` latent cells (default 2, 32 px) and leaves the finer band to the re-draw. Tiles and chunks stay tied to the same source, so they agree where they overlap. It is on the standalone `H3 Video Upsampler` and on `HTC Upsample Settings` (`structure_lock`, `lock_sigma`). It runs inside every step through a post-CFG hook, unlike `detail_sigma`, which applies once afterwards. Try 0.5-1, and higher for animation.
- **H3 Video Upsampler: optional `conditioning` input.** Wire a CLIPTextEncode (H3 text encoder) of what the clip shows, typed or written by a VLM. Only its text is used: references, keyframes and noise-aug keys are dropped, as with `regen2k_cond=hop_text`. Unwired, it stays zeroed out.
- **H3 Video Upsampler: `lock_sigma` widget** (was only on `HTC Upsample Settings`). 1-1.5 also holds eyes and mouths on medium shots.
- **H3 Video Upsampler: clips that aren't 24 fps keep lip sync.** H3 places every frame 1/24 s apart, so a 48 fps clip's soundtrack used to sit under the wrong frames (half speed, then silence) and the re-draw pulled mouths off sync. New optional `fps` input (wired from Get Video Components in `workflows/HandTieClips_Upsample_Video.json`) and `off_24_audio`: `retime` (default) stretches what the re-draw hears by fps/24, `silence` conditions on silence, `as_is` keeps the old behaviour. A warning is logged whenever fps isn't 24. The output soundtrack is untouched.

## 3.2.0 — 2026-10-30

- **Upsampler (Open-H3-Regenerate-2K):** the upsample stage in `HandTieClips` and the standalone `H3 Video Upsampler` now natively run Open-H3-Regenerate-2K: 3D latent upscaler (`2.0 MP` default), then 3 Euler steps at CFG 1 on `[0.8, 24/35, 0.48, 0]` (`REGEN2K_SIGMAS`, shift-6 grid from `0.8`; `REGEN2K_SIGMAS_RELEASE = [0.909375, 6/7, 2/3, 0]`), `regen2k_cond` = `hop_text` (each hop's encoded text prompt with `minimax_refs` / `minimax_keyframes` stripped, default on `HandTieClips`) or `none` (zeroed-out conditioning across every chunk), no `pin_chunk_start` on chunk 2+, the real audio latent pinned clean, `noise=per_chunk`, and seed `42` (`regen2k_seed` / `redraw_seed`, `102/17 f` chunks with `regen2k_chunks` absorbing `<= 5`-step tail remainders or sliding `< 20`-step final chunks back to at least 20 steps to prevent tail-stub artifacts). `upsample_redraw` in the `UPSAMPLE` tab selects the Regen2K LoRA from `models/loras` (default `open_h3_regenerate_2k_r256pp_bf16.safetensors`, 3.77 GB; refiner-only `open_h3_regen2k_refiner_r256pp_bf16.safetensors`, 3.77 GB; reference `open_h3_regenerate_2k_bf16.safetensors`, 8.80 GB) applied at `upsample_denoise = 0.8` (`0` skips the re-draw and only enlarges), enabled by default on the shipped stock workflows (`upsample=on`, `upsample_megapixels=2`, `upsample_denoise=0.8`, `upsample_tile_tokens=70000`, `upsample_redraw=open_h3_regenerate_2k_r256pp_bf16.safetensors`, `regen2k_seed=42`, `regen2k_cond=hop_text`), and fallback models (`upsample_dit` -> `refine_model` -> `model`) strip hop LoRAs before applying the Regen2K LoRA. `HTC Upsample Settings` defaults updated to `steps=3`, `noise=per_chunk`, `redraw_seed=42`. Lower tile budgets shorten Regen2K chunks down to 68 frames full-frame before splitting into spatial tiles, and an OOM-lowered budget carries forward across chunks and logs the `upsample_tile_tokens` value to set for next run.
- **Upsampler:** chunks join into one preallocated latent (no film copy per chunk; output unchanged); log shows OOM retries, join time and peak VRAM.
- **hand_tie: every previs is rendered and checked before the first hop.** A previs that is not
  one take (any cut, anywhere: every hop is tied to the frames on both sides of it) stops the run
  in its first minutes and names the frame, the nearest join and the previs sentence running
  there. A run that passes renders its hops unattended, loading each previs from the cache. Needs
  `cache_hops` on; with `dry_run=previs` the check only warns.
- **Fix: a continuing previs snapping back to the stated shot size.** Its first frames are pinned
  to the previous previs's closing window; it now inherits that framing instead of re-stating a
  size, which snapped at the frame the pin let go.
- **Fix: a previs re-describing the place mid-take** (read as a new establishing shot). Inside a
  previs, beats after the first keep their actions only.
- **Fix: hand_tie join windows rendered as inserted shots.** The previs gave each 0.9 s join
  window a timed range of its own, and H3 drew that range as a separate shot (a close-up cut in
  and out, the cut at frame ~158 in every previs). Both hops tied to the window inherited it, so
  hops ended and began too close. Each beat's range now runs straight through the next window,
  in one take; the next beat still starts after the window. The old layout stays behind
  `hand_tie.PREVIS_CARRY_RANGES`.
- **WRITE music videos: "eyes on the lens" instead of "raps into the lens".** "Into" reads as
  travel toward the camera and pushed the shot in at the end of hops.
- **Fix: a hand_tie previs drifting closer, then a cut.** The previs compiler drops each beat's
  framing sentence, so a previs never said how close the shot was, and a continuing section could
  drift into a close-up. Its join windows tied both hops to it, and the next hop snapped back to
  its own framing a couple of seconds in. The previs now opens on the section's framing sentence
  and every join window names the shot size; the log warns when no beat names one.
- **STANDARD tab: audio references (`<Audio N>`) detected on the rail and `MEDIA` voice slots.**
  Rail rows with a `voice` (or a RefMod's stored voice, or an audio-only rail row) and `MEDIA`
  `voice_file` slots are now numbered as `<Audio 1>`, `<Audio 2>`, ... in the exact order the node
  hands them to the model, shown in the `STANDARD` mode line (`Ref2VA, N picture(s), M audio(s)`),
  passed to the writer in both `plan` and `write` turns, and validated by the `Ref2VA` contract
  (`subject_definitions`, `summary`, `retention_analysis`, and `detailed_description` / audio
  sections).
- **STANDARD tab: notes on how a written block may play.** After a block passes the contract, it is
  read as a film (shots, timed windows, spoken lines) and the panel lists advisory notes: a line
  your brief quotes that is missing, said twice, changed or only described; a line far shorter or
  longer than its window; a quiet window with a face and no mouth state in a clip with lines; a
  window with no line and no sound and no sound bed. Notes are never sent back to the model and
  never block Accept. The prompt the model sees is unchanged. The response and the log now name
  the exact system prompt (`system_sha`).

## 3.1.1 — 2026-10-27

- **The Starter saves with HTC Save Video** (frame generation x2 inside the save, NVENC),
  replacing RTX Video Frame Generation -> CreateVideo -> SaveVideo; the Upsample Video
  workflow saves with it too, at the clip's own fps.
- **The Starter and Upsample Video load the official `minimax_h3_ref2va_int8_convrot` DiT**,
  and the Starter samples with euler / simple. The official DiT has no turbo built in: add a
  turbo LoRA in the LoRA loader, or raise the steps (the Starter's note says so).

## 3.1.0 — 2026-10-27

- **hand_tie takes `master_audio_file`** -- a music video can now run on `pin_mech=hand_tie`.
  Every hop locks its own slice of the song, exactly as on `motion_context`; the previs is
  silent except for the song at each join window, so the mouths at a join sing the syllables
  both hops hear. Proven on a 12-hop, 2:51 one-take music video (15 s hops): lip sync held
  across all 11 joins. One hand note from it: a hand moving through a join blurs there, so
  end each hop with the hands at rest (knees, a stand, a table).
- **Fix: 15 s hops under hand_tie** -- three 15 s hops fitted one previs only without its
  closing window, so every third hop ended unguided and could snap. Long hops now go two to
  a previs, every hop tied at both ends; 8 s and 12 s hops are unchanged.
- **HTC Save Video (long-form)** -- a save node that replaces `RTX Video Frame Generation ->
  CreateVideo -> SaveVideo` for long films. It streams the frames to the GPU in small chunks,
  runs RTX frame generation per pair (x2 / x3 / x4, never holding the doubled film in RAM),
  converts to BT.709 NV12 on the GPU and encodes with NVENC at constant quality (CPU x264 /
  x265 / SVT-AV1 without CUDA), with a keyframe on every hard cut and every 2 s. A 171 s film
  with x2 frame generation saved in 29 s. Prints NO AUDIO when the soundtrack is not wired.
- **Reference encodes are cached per run** -- each reference still, clip and voice is
  VAE-encoded once and reused by every hop that names it, instead of once per hop. The log
  ends with the hit / miss count.
- **Fix: the new-place warning** no longer fires on a restart (it opens on its own refs), and
  a `[Shot N]` beat is checked on its `[Shot 1]` only; the hop ends at its last shot's place.
- **`dialogue_lock` (RUN > soundtrack) + `dialogue_audio_file` (MEDIA)** -- freezes each hop's
  spoken lines in the soundtrack so the words come out exactly and nobody adds any, while H3
  still makes the rest of the sound. `lines` freezes each line with margins, `lines+hold` also
  holds 1.5 s quiet after it (where extra words start), `full` the whole hop. With
  `dialogue_audio_file` empty, H3 drafts each dialogue hop's sound at 448p first, Whisper keeps
  only the scripted words and silences the rest; with a recording set (lines on the film's
  timeline), that is used. The delivered lines are the source, sample for sample. Off by
  default; not with `master_audio_file`, `realism_boost`, `audio_refine` or SWAP.
  Experimental: lip sync and the sound bed held in every test, but no test babbled without it,
  so it is not yet seen removing babble. Each dialogue hop costs one extra small draft (about
  30% more time), more if a draft misses its lines; a hop whose drafts all miss is left
  generated. Use it on a hop that babbles. Under `pin_mech=hand_tie` it does nothing (logged): tried
  there, one take cut and another repeated a line.
- **Fix: hand_tie dialogue and joins** (all since 3.0.0).
  - Single-quoted lines (`says, 'Hey.'`, the form the WRITE tab and plans use) are now read
    as lines. Before, only `<d>` and double quotes were: on every hop after a section's first
    the audio clean-up replaced the line with room tone, and line timing, crossing-line splits
    and the plan warnings did nothing.
  - The previs now shows where each hop lands, not only how it starts. Its compiler dropped
    each beat's ending and wrote negations ("no movement"), so a seated two-person scene
    rendered a frozen previs; people stood up at the joins and props jumped back to their
    opening place in a hop's last frames. Join windows now name everyone in them.
  - A hop is no longer rendered twice for a cut its own beat writes (`[Shot N] At ...`), and
    the automatic hop retake is off: in every logged case it cut again at the same frame. A
    cutting hop now prints a warning instead.
  - The `moment end` box said the previs ends on it; it carries a closing line only, and now
    says so.
- **Fix: a possessive on a name no longer reads as a quote.** `@boss's` compiles to
  `<Subject 1>'s`, and that apostrophe shifted every quoted line after it, so voice timing on
  that hop was placed against the narration instead of the line.
- **STANDARD tab** -- one standard MiniMax H3 prompt (T2VA or Ref2VA) for a single generation in
  Simple mode, planned then written, following the MiniMax H3 prompting skill.
- **Upsample is the original MMH3 recipe again** — since 3.0.0 the chain re-drew
  in 2 steps from sigma 0.57 (`upsample_denoise` 0.1) with a 192 px tile overlap.
  It now runs the recipe the standalone H3 Tiled Upsampler always matched: one
  step from sigma 0.75 (`upsample_denoise` 0.2), 102 / 17-frame chunks, anchor
  0.999, 70000-token tiles with 128 px overlap, seed 444. Measured on one 576p
  clip upsampled to 2 MP, it kept 14% more fine detail. Saved graphs keep their
  own `upsample_denoise`; set it to 0.2. The shipped workflows carry 0.2.
- **The upsample LoRA is retired** — `upsample_lora` / `upsample_lora_strength`
  (and the H3 Video Upsampler's `lora`) are hidden and ignored, with a log line
  when a saved graph names one. The h3upscale guide cost fine detail and drew
  tile grids at 2 MP. The widget slots stay so saved graphs load.
- **HTC Upsample Settings (`tiled_upsampler.py`)** — a new node for the chain's
  optional `upsample_settings` socket: re-draw steps, start sigma, noise
  (`per_chunk` or one `film` field, so the frames two chunks share get the same
  noise), seed, chunk length and overlap, anchor strength, tile overlap, detail
  merge, attention / feed-forward VRAM splits, and an optional sampler.
  Unwired, the upsample runs exactly as before. The log now times each chunk's
  re-draw, each run and each phase.
- **`audio_refine` runs on the base model, never the realism boost model** —
  H3 shares every block between picture and sound, so the boost LoRAs colour the
  audio too. Hops cached with `audio_refine=on` render again once. The log names
  the model, and the `audio_denoise` tooltip gives the real start sigma (0.5
  starts near 0.92: most of the soundtrack is drawn again).

## 3.0.0 — 2026-10-18

### Built-In `_HTCMotionContext`, Refine v2.4, `hand_tie` v2.6 & `audio_refine`

- **Built-in `_HTCMotionContext` (`h3_ref_chain.py`, `THIRD_PARTY_NOTICES.md`)** —
  `pin_mech=motion_context` (and `auto`) now runs natively in-house on ComfyUI
  Core's `minimax_keyframes` contract with zero external custom-node dependency
  (credit to [NikoDemon80's ComfyUI-H3-Motion-Context](https://github.com/NikoDemon80/ComfyUI-H3-Motion-Context)
  for the latent-slice + end-aligned audio timeline concept). With `hop_refine: full`,
  continuous relays hold for ~5–6 clips on Turbo before visible texture changes
  and ~7–8 clips on non-Turbo (with `anchor="restart"` resetting cleanly at
  scene cuts).
- **Refine v2.4 & Motion-Context Join Locks (`h3_ref_chain.py`, `refine_blend.py`)** —
  Added `_pin_inpaint_head`, `_calibrate_overlap_latent`, `_bridge_motion_seam`,
  head-internal refine ramp (`0:0, overlap:1`), Hop-1 refine skip (`hop_is_start`),
  and bit-for-bit audio freeze (`freeze_audio=_do_aud`).
- **`hand_tie` v2.6, Direct Previs-to-Previs Spine & `pin_mech=hand_tie_mc` (`hand_tie.py`, `h3_ref_chain.py`)** —
  `_ht_inpaint_head` aligns only `cond` (`pos == 0`, per-`mod5` phase-calibrated
  to `src_5[:, :, k % 5]`, keeping 100% of the silent-mouth previs window and
  leaving `latent` / `noise_mask` untouched during `SamplerCustomAdvanced`),
  paired with `_calibrate_ht_latent` (`w_prev = [1.0, 0.5, 0.25]`), 17-frame
  (`5`-token) `_vae_prefix` `ViT3DDecoder` warm-up decode in `_decode_av`,
  `deflicker` cross-cut guard (`|b - a| < still * 1.5`), and post-`deflicker`
  `seam_feather`. Chained multi-section previs runs (`Section 2, 3, 4…`) now
  chain directly from Previs $s-1$'s closing window $W_{\text{end}}$ (with its
  17f warm prefix, local boundary overlap calibration, and `cap_high` HF clamp,
  plus batched Qwen 32B previs + first-hop text encoding, muted previs audio
  skip, and `"0.50 MP"` previs ref cap). Also adds `"hand_tie_mc"` (`v3`) to `pin_mech`
  as a separate third option (`_ht_mc_inpaint_head`: unpacks the 7-step Previs
  window into 7 per-step `minimax_keyframes` at `[0, 1, 5, 9, 13, 17, 18]` with
  muted-head audio keyframe stripping, `hand_tie.calm_hop_audio` vocal-formant-filtered
  ambient floor locking, universal `(S1)` dialogue tagging, section `framing`
  alignment, and `2.0` wps post-line pose timing — validated on the 10-hop
  `71.7 s` `1024×768 @ 48 fps` showcase `docs/img/hand-tie-10hop-00138.mp4`).
- **Per-hop `audio_refine` pass (`[99..104]`, `h3_ref_chain.py`)** —
  Re-samples the audio branch (`audio_refine`, `audio_denoise`, `audio_steps`,
  `audio_sampler`, `audio_scheduler`, `audio_seed_offset`, optional `audio_model`
  socket) while holding the finished video latent 100% frozen via
  `SetLatentNoiseMask` (`zeros` on video, `ones` on the whole soundtrack: no
  head, since a boundary inside the audio warbles). Unwired, it runs on the base
  model, never the realism boost model. Ideal for pairing with `realism_boost` (4–5 steps).
- **3-Phase Tiled Upsampler, Streamed VAE Decode & VRAM Guardrails (`tiled_upsampler.py`, `video_upsampler.py`)** —
  `upsample()` now executes in 3 non-overlapping phases (1: `VideoVAE` guide
  prep once -> CPU RAM; 2: `upscale_chunks_batch` on 3D `LatentUpscaler` once ->
  CPU RAM; 3: `MiniMaxH3` 32.4 GB DiT staged once across all 21 chunks with a
  single `sample_tile` call per `1x1` chunk), paired with streamed 30-token
  (`102f`) + 5-token (`17f`) causal-prefix VAE decoding into disk `np.memmap`,
  automatic `_apply_low_vram_patches` (`MiniMaxLowVRAMAttention(4)`,
  `MiniMaxChunkFeedForward(2, 4096)`, `H3AdaLNLoRAFix(port)`), and OOM tile
  backoff.
- **UI Cleanup, `rides hops` Fix & Vue Nodes 2.0 Compatibility (`js/`)** —
  Hid 14 redundant v1 refine and `join & pin` band-aids (`REFINE_V2_HIDDEN` in
  `js/editor/run_panel.js`), fixed `.h3e-hopbar` (`grid-column: 1 / -1` and
  `getBoundingClientRect()`-relative click/drag in `js/h3_ref_chain.css` and
  `js/editor/ref_rail.js`), and hardened widget hiding/sizing for both Classic
  LiteGraph and ComfyUI Vue Nodes 2.0.
- **`WRITE`, `Music Video` (`Song` / `Lay out`) & `SWAP` Hardening (`planner.py`, `routes.py`, `js/editor/writer_bar.js`)** —
  Connected `brief` and `chat` via `scenePrompt()`, exposed `Edit shots`
  (`stage: "edit"`), added explicit JSON contract instructions + fence-aware
  `_parse_obj()` to `write_propose` and `write_edit`, fixed `_songmap_summary`
  and `solve` section-kind propagation, normalized MV `anchor="restart"` on
  Hop 1 and rail-backed restarts before `_validate_anchors`, and added `<rail>`
  metadata + `INTENT_INFERENCE_GUIDE`.

### Standalone Guided SWAP (`swap_script`, `swap_refs`, `AddGuide`, auto-loaded Swap LoRAs)

The **Swap** tab is now a completely standalone, one-hop guided identity swap
tool built around Alissonerdx's guide-latent (`_gl`) Character & Head Swap
LoRAs and the full six-field H3 Reference-to-Video contract. Writing or
rendering a swap no longer touches `shot_plan`, `ref_plan`, or your upstream
LoRA stack.

- **Dedicated `swap_script` and `swap_refs` widgets (`[98]`, `[99]`)** —
  Accepting a swap writes the compiled six-field H3 prompt into `swap_script`
  and the active plate whitelist into `swap_refs`, leaving your multi-shot
  `shot_plan` and `ref_plan` untouched. Clearing the swap from the **Swap** tab
  (`Clear swap (use SCRIPT chain)`) empties both widgets and hands the node
  straight back to your chain.
- **Three-state `swap_refs` plate routing** — `""` keeps the register default
  (every wired plate rides), `"[]"` rides zero plates (used by `keep_person` so
  a face still on the rail never leaks onto a scene-only swap), and `"tag1,
  tag2"` rides only the named plates in that exact `<Picture 1..N>` order.
- **Full-clip `MiniMaxH3AddGuide(frame_idx=0)` alignment** — When a swap runs
  with a reference clip loaded, `run()` lays `reference_video[:render_length]`
  onto `MiniMaxH3AddGuide` at `frame_idx=0` (`minimax_keyframes`) so the
  guide-latent swap LoRA tracks the performer's body mechanics, camera move,
  lighting, and environment frame by frame. `hand_tie` (`ht`) is automatically
  forced off for a swap even when `pin_mech=hand_tie` is selected on the node.
- **Automatic Character / Head Swap LoRA loading (`_swap_lora`)** — `planner.py`
  prepends `body_swap:` (for `Replace person`) or `head_swap:` (for `Head swap`
  and `Face only`) to `swap_script`. At render time, `run()` clones `model` for
  that single execution and loads
  `minimax_h3_character_swap_v1.0_ref2va_r64_gl.safetensors` (`body_swap:`) or
  `minimax_h3_head_swap_v1.0_r32.safetensors` (`head_swap:`) at strength `1.0`
  via `LoraLoaderModelOnly` + `H3AdaLNLoRAFix(mode="port")` before computing
  `_model_fingerprint(model)`. You never have to wire or unwire a swap LoRA in
  your upstream graph when switching between a swap and a chain.
- **Multi-person Left-to-Right (`PEOPLE L→R`) swaps** — Pick one or more
  subject-bearing `@tag` chips on the **Swap** tab in left-to-right screen
  order. They map 1-to-1 to `<Subject 1..N>` and `<Picture 1..N>` in
  `subject_definitions:` and `detailed_description:`.
- **Fail-closed six-field contract gate at write time and render time** —
  `validate_swap()` and `swap_contract_errors(..., shape_only=True)` enforce all
  five required H3 headers in order (`subject_definitions:`, `summary:`,
  `detailed_description:`, `overall_soundscape:`, `non_diegetic_music:`),
  require `summary:` to open with `[video generation + reference]`, require
  `[Shot 1]`, `(VISUAL)` (closing on the mandatory drift clause), and `(SOUND)`,
  and reject negations outside quoted speech and plural pronouns
  (`they`/`them`/`their`).
- **5-frame temporal vision** — Both `/h3_ref_chain/swap_plan` and
  `/h3_ref_chain/swap_describe` now sample **5 evenly spaced frames** (up from
  3) across the trimmed `[start, end]` clip window so the vision model sees the
  full motion arc.

### Local `nInfer` Writer Upgrade (Qwen3.8-27B Uncensored DFlash2 v3)

- **Upgraded default `nInfer` model** — Switched `llm.py` and `htc_llm.json`
  from `qwen3_8_27b_nvfp4.ninfer` to
  `Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-DFlash2-ninfer-v3.ninfer`
  (`WaveCut/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-DFlash2-NInfer-v3`,
  `groupwise-int` v3 container with BF16 Vision tower, MTP, and DFlash2 block
  diffusion speculative decoding). `llm.start_process` automatically falls back
  to the newest `.ninfer` file in `C:\ninfer\models\` if a configured filename
  is absent.
- **Sampling & MTP retry step-up** — Raised default writer temperature from
  `0.35` to `0.75` with `top_p: 0.95`, and added a `+0.1` temperature step-up
  per repair retry (`min(1.0, 0.75 + (attempt - 1) * 0.1)`) in `routes.py` so
  100% MTP speculative draft acceptance cannot lock repair attempts onto a
  rejected prefix.

### Universal Refine v2.3, `hand_tie` Qwen3-VL Previs Compiler & Tiled Upsampler Anti-Grid Upgrade

- **Shifted/capped denoise + RMS-capped detail blend (`refine_blend.py`, `h3_ref_chain.py`)** —
  `hop_refine=full/pin_only` schedules `refine_steps` steps on `_rmodel`'s
  sigma-shifted (`shift=12`) schedule (`0.25` = `[0.8000, 0.6316, 0.0]` on a
  turbo model, and capped to `sigma <= 0.45` = `[0.45, 0.225, 0.0]` when
  `refine_model` is an unpatched 30-step stock base so 2 Euler steps never
  under-converge or bleach skin warmth). `blend_video_detail(..., cap_high=True)`
  keeps `x0`'s low-frequency background, layout, and colour ($\sigma = 2.0\text{ latent px}$)
  while clamping the refined high-frequency RMS per frame and channel so it can
  never exceed `x0` (`| detail=0` restores the legacy lerp).
- **`hand_tie` Qwen3-VL Previs Compiler + Seam Feather (`hand_tie.py`, `h3_ref_chain.py`)** —
  Before `qwen3vl_32b` or the H3 DiT touch VRAM, `hand_tie` auto-loads
  `qwen3vl_4b*.safetensors` (~4 GB) or `qwen3vl_8b*.safetensors` (~8 GB) from
  `models/text_encoders`, compiles manual shot beats into continuous single-take
  bridge moments under `PREVIS_LAWS_SYSTEM` (stripping mid-hop payoff actions so
  they happen inside the 8s hop rather than early in the previs), and immediately
  evicts the 4B/8B model from VRAM (falling back to `lead_clause` if not
  installed). `seam_feather` closes the still-pixel RGB step locally over `±12`
  frames at each `hand_tie` cut and crossfades the first `6` frames of the shared
  window to eliminate the 1-frame Frame-0 VAE mini-flash.
- **Cleaned `REFINE` section in the RUN panel (`js/editor/run_panel.js`)** —
  Hid the 8 redundant v1 refine/speed plumbing dials while keeping their raw
  LiteGraph widget slots intact, leaving `hop_refine`, `refine_denoise`,
  `refine_steps`, and `refine_blend`.
- **Tiled Upsampler anti-grid merge (`tiled_upsampler.py`, `video_upsampler.py`)** —
  Added `_highpass_detail_merge(..., sigma=8.0)` (`128 screen px`, matching the
  tile seam scale) at the end of `redraw_chunk` to strip tile-to-tile
  DC/colour/contrast grid seams against the full-frame 3D `LatentUpscaler`
  output while preserving all mid-and-fine `h3upscale` detail. `upsample_chain()`
  now uses 2-step low-sigma re-entry (`start_sigma = min(denoise * 2.5, 0.35)`,
  `overlap_px = 192`, `detail_sigma = 8.0`) and automatic `H3AdaLNLoRAFix` porting.

## 2.2.0 — 2026-09-21

Two new widgets, both appended last, so a 2.1.0 graph loads with every existing
setting where it was. The headline is that three numbers which were really
*other* settings in disguise now derive themselves: the refine pass follows the
base's own sigma grid, the refine blend follows the overlap, and `speed_mode`
finally does something visible.

**One thing to expect on first run.** SLA moved to the front of the MODEL wire
in the shipped workflows. Reordering patch nodes changes what
`_model_fingerprint` hashes, so **every hop re-renders once** even with
`cache_hops=on`. That is the fingerprint working, not a regression — but budget
for it before you queue a long chain.



### `refine_align` — the refine pass now follows the base it is running on

`hop_refine`'s schedule was pinned to a four-step base. `BasicScheduler(steps,
denoise)` builds its own grid — at the published `2` / `0.50` / shift 12 that
is `[0.9231, 0.8000, 0]`, the tail of a **4-step** schedule — no matter what
the hop itself sampled. Against a 4-step base that is exactly the hop's own
last two steps. Against anything else it is not:

| hop steps | hop's own last 2 sigmas | what the refine actually ran |
|---|---|---|
| 4 | `0.9231, 0.8, 0` | `0.9231, 0.8, 0` — identical |
| 6 | `0.8575, 0.7064, 0` | `0.9231, 0.8, 0` — **off the grid entirely** |
| 8 | `0.8, 0.6316, 0` | `0.9231, 0.8, 0` — right values, double strides |

A turbo LoRA or merge is only accurate at the sigmas it was distilled for, so
an off-grid entry, or a closing stride `0.8 -> 0` where the hop's own was
`0.6316 -> 0`, is a jump the trunk was never trained to make. That is the
misalignment — not the eval count, and not `s0`, which a LoRA does not move at
all.

**`refine_align=hop_tail`** re-runs the hop's **own** last
`refine_steps` sigmas. Same evals, same wall clock, every one on the grid the
trunk was distilled for, and it re-derives itself when the base or the step
count changes instead of needing a re-tune. `refine_denoise` is unused under
it and the log line says so. At `steps=4` it is bit-identical to the old
behaviour, so anyone on the configuration the defaults were tuned for sees no
change.

`refine_align=denoise` keeps the original schedule for reproducing archived
runs, and is **keyed to the old cache key** — the mode is appended to the hop
payload only for `hop_tail`, so a run pinned back to `denoise` still hits
entries written before this existed.

`denoise` stays the **default**, and `hop_tail` is reached through
`speed_mode=turbo`. An undistilled trunk is accurate at every sigma, so the
wider stride costs nothing there, and a graph saved before this widget existed
reloads on the schedule it actually rendered under. The dividing line for that
preset is base-vs-fashion: `refine_align` is a property of the checkpoint, while
sampler, scheduler and step count are turbo-community fashion and are
deliberately absent from the table.

`speed_mode=turbo` no longer sets `refine_head=freeze`. That entry rested on a
seam reading, which this project treats as corroboration and never as the
decision, and it looks in hindsight like compensation for the misalignment
above. The only end-to-end turbo evidence here -- a 7-hop chain on a turbo
merge, `hop_tail` with `refine_head=refine` -- came out clean where the
unrefined arm was crunchy.

New widget appended **last**, at position 78; both shipped workflows carry the
slot, set to `denoise`. Every other widget keeps its index.

### `refine_blend=auto` — the ramp follows the overlap

The published ramp `0:0, 22:0, 44:1` holds the raw sample across the pinned
overlap and crosses to fully refined over the 22 frames after it. That first
`22` **is the `overlap` widget** — and the two only coincided because `0.9 s`
is the default. Nothing said they were coupled, and nothing warned:

| `overlap` | pin runs to | ramp held raw to | what shipped |
|---|---|---|---|
| `0.9 s` (22 f) | f22 | f22 | correct — the one it was written for |
| `0.2 s` (5 f) | f5 | f22 | 17 frames refined, then discarded |
| `1.6 s` (39 f) | f39 | f22 | **f22–f39 ship refined inside the pin** — the seam cost the ramp exists to remove, back again |

`refine_blend` now defaults to **`auto`**, which derives the keyframes from this
run's own overlap: raw across the pin, then the same 22-frame crossover. Only
the hold is overlap-coupled — it *is* the pin — so the crossover width stays the
published 22 rather than scaling, which is a judgement call and is marked as one
in the source.

At the default `0.9 s` overlap `auto` resolves to `0:0, 22:0, 44:1` exactly, and
it resolves **before the hop key is built**, so a shipped workflow renders the
same frames and hits the same cached hops it did at 2.1. Typing your own pairs
still overrides; empty still means "no blend, the refine ships whole". The
console prints what `auto` resolved to.


### SLA moves to the front of the MODEL wire

Shipped workflows now run `UNETLoader -> H3SLAAttention -> LTX_lora_loader ->
H3AdaLNLoRAFix -> MiniMaxLowVRAMAttention -> ModelPreviewOverrideKJ ->
HTCH3Cache -> HandTieClips`, on PlagueKind's recommendation. SLA used to sit
after low-VRAM. Reordering patch nodes changes the keys `_model_fingerprint`
hashes, so **the first run after updating re-renders every hop** even with
`cache_hops=on`. That is the fingerprint doing its job, not a regression.

### Also in this release — `master_audio_start_s` and the MEDIA window

Two changes, both about `master_audio_file`. One gives you somewhere to put
the window. The other stops the planner writing dialogue into a beat that is
meant to be quiet. **Neither changes an existing render.** The one new widget
is appended at position 77 and defaults to `0.00`, so a workflow saved on
2.1.0 loads and renders identically.

### New

- **`master_audio_start_s`** (MEDIA) — where the chain's window opens inside
  `master_audio_file`, in seconds. There is deliberately no matching end. The
  window's *width* is the chain itself — `duration x shots - overlap` — so the
  only free parameter is where it starts.

  It exists because hop lengths are quantised, and a chain length is therefore
  almost never a track length. Six 10 s shots is 1348 frames, 56.17 s, not 60.
  Until now the way to reconcile that was to cut the audio file to length in an
  editor, and to cut it again whenever you changed your mind about the shot
  count. You can snap the audio to the chain; you can never snap the chain to
  the audio.

  The offset is applied **once, in the loader** — not at the three places the
  take is sliced, which are the hop encode, the pin the next hop inherits, and
  the delivered passthrough. Cutting once leaves the chain's own clock 0-based,
  so `hop_audio_window_s`, the length guard and the passthrough all read
  exactly as they did. Three offsets applied at three call sites is the
  arithmetic that eventually disagrees with itself by one hop. The digest is
  taken *after* the cut, so sliding the window invalidates the hop cache
  without anything being added to the salt, and the offset is reported back to
  the sample rather than to the widget step — a 0.1-step slider on a 48 kHz
  file rounds, and the number printed should be the cut that happened.

  A window that opens past the end of the take is refused at load. The
  take-too-short refusal now names the slider as a fix, because a long enough
  track with the window opened too far in is a window problem and not a
  padding problem.

- **The MEDIA strip draws that window as a box you slide.** Master audio gets a
  single fixed-width box on the waveform instead of the two-grip in/out trim
  the other media slots use, dragged bodily because there is no edge to pull.
  Under it is a live readout: `opens 0.00s   chain 56.17s of 60.00s   (3.83s
  unused)`.

  The chain figure is live — it reads the current card list, so adding a shot
  or changing a duration resizes the box while you are looking at it. When the
  chain comes out *longer* than the take the readout turns amber and says by
  how much. That is the state that raises at run time, and it is now visible
  before you press Run rather than after the chain has started.

  The slot convention is a `*` suffix in the strip's SLOTS table:
  `master_audio*` means fixed width, which is one `_start_s` widget and
  deliberately no `_end_s`.

### Fixed

- **H3 Cache** — ported PlagueKind v1.5.2 residual-buffer reuse and CPU feature signatures (avoids cuMemFreeAsync abort after block-stack malloc teardown).

- **Every continuation hop named every character in the register, so a large
  cast rendered as a lineup.** `continuity_line` writes "X continues," plus
  wardrobe for each subject it is handed, and it was handed the whole of
  `ref_plan_refs`. Sampling is cfg 1.0 with no negative branch, so each name is
  additive: on an eight-character register, hop 2 was told all eight continue
  regardless of its `refs`, and the model rendered the cast standing in a row.
  Seed-independent, because a register is not a seed — reseeding reproduced it
  exactly, which is what made it identifiable. It now receives
  `carried_subjects`: this hop's subjects, unioned with whatever the pin hands
  it, seeded from the previous hop's carried set and reset at every chain
  start. The reason the line reaches past `hop_active` at all is preserved —
  a person the pin carries with no still riding is still named — but nobody
  outside the relay lineage is. On the 19-hop chain that found it, every
  continuation went from naming 8 to naming 2–3. Single- and two-character
  plans are unaffected: there, the lineage and the register are the same set.
  `tools/check_shot_refs.py` pins the call site.

- **A restart hop's references were bound but never cited, so uninvited cast
  walked into the shot.** `anchor=restart` makes a hop a chain start, and a
  chain start is where `subject_definitions:` / `retention_analysis:` ride —
  the block that says which photograph is which person. The line that *fills*
  that block tested `i == 0`; the line that *uses* it tested `hop_is_start`.
  So on every restart after hop 1 the producer was silent and the consumer was
  dead code. Those hops still bound their stills into the DiT and as
  `<Picture N>` in the tokenizer, with nothing in the prose pointing at them,
  and an uncited plate is the one failure this pack has measured repeatedly:
  the model free-associates the picture into the frame. `@tag` did not save it
  either — `subject_names` flattens tags to bare prose on continuations, and it
  was keyed on the same `i > 0` test, so `@ld` reached the encoder as "the man
  in the purple velvet suit" with the binding to `<Picture 1>` dropped. Both
  guards now read `hop_is_start`, which is sound because a restart provably has
  no pin: `still_shift` is 0 and `live_p` is None on that branch, so
  `subject_prose`'s shift-free ordinals are correct there for the same reason
  they are correct on hop 1. Found on a 19-hop chain with ten restarts.
  `tools/check_anchor.py` now pins the producer and the consumer to the same
  test. **Re-renders every restart hop and everything downstream of one.**

- **The editor's chain length read short on any plan with a restart.**
  `timing()` in `plan_editor.js` subtracted an overlap trim for every hop after
  the first. But a restart is a chain *start* — it relays nothing, so nothing is
  trimmed off it, which is exactly what `audio_lock.master_frame_count` has
  encoded on the Python side. The JS copy never got that fix, so the summary was
  `overlap` short per restart: a 19-hop plan with ten restarts summarised as
  **1:50 for a chain that renders 1:59**.

  Short is the dangerous direction. The readout offers room that the queue-time
  master-audio guard will then refuse, and because `timing()` also feeds
  `chainSeconds`, **the master-audio window in the MEDIA strip was drawn
  narrower than the audio the run consumes** — so `master_audio_start_s`, new in
  this release, was positioned against a window of the wrong width.

  `tools/check_restart_trim.py` now reads `timing()` out of the JS and asserts
  the rule on both sides of the language boundary, comments stripped so the
  paragraph explaining the old formula cannot trip the check that forbids it.

- **The reference rail could not show a fifth subject.** The subject dropdown
  was built with a hard-coded `i <= 4` while `MAX_REF_IMAGES` allows nine refs
  and therefore nine subjects — and `routes.py` was already serving
  `max_ref_images`, so the ceiling was a second copy of a number the panel had
  been sent. The display failure is the sharp end: a `<select>` handed a value
  with no matching `<option>` falls back to the first one, which here is
  `setting/prop`. Rows 5+ did not read as blank, they read as *"this picture is
  scenery, not a person"* — the opposite of what the JSON said — and touching
  one committed that, dropping the ref out of `_identity_lock` so its face
  stopped being treated as an identity. A subject number outside the generated
  range now gets an option of its own rather than being silently rewritten.

- **The trim readout printed a number the node never received.** The bar
  writes hundredths, every trim widget declared `step: 0.1`, and the ComfyUI
  frontend derives its rounding from the step. A window dragged to a readout of
  `opens 4.03 s` was therefore stored as `4.00`, and the take opened 30 ms
  early. Both halves were individually defensible; only their disagreement was
  wrong, which is why nothing raised.

  This was measured, not inferred. The same 2-hop chain was rendered twice --
  once with the window placed by the slider, once fed an audio file cut at
  exactly the same point with the slider left at `0.00`. The two correlate at
  0.990 with a best-fit lag of exactly 1440 samples, and arm A matches the
  source take sliced at 4.00 s at zero lag.

  The fix has two halves. `master_audio_start_s` now declares `step` and
  `round` of `0.01`, and the bar reads the value *back* after storing it, so
  the readout shows what the node will actually receive regardless of what the
  widget did to it. The readback is the half that still holds if a step is ever
  changed again.

  **The other fourteen trim widgets still declare `step: 0.1`** -- the `voice`,
  `music` and `reference_video` starts and ends, worst case 50 ms. They now
  display honestly because of the readback, but they still quantise. On a
  reference clip's in-point that error is inaudible, so they are left as they
  are rather than changed on the strength of a different slot's evidence.

- **A wordless hop with a sound bed no longer lints.** `SYSTEM_PROMPT` has a
  wordless-hop rule — zero spoken lines plus a named narrowband sound bed is a
  legitimate beat, and "the spoken-lines column of the table does not apply".
  `planner.validate` never implemented it, so a quiet beat written exactly as
  the prompt asks still came back with a spoken-lines warning.

  That was cosmetic until the speech repair round went in. After it, the
  warning started *spending* one of the three attempts pushing invented
  dialogue into the beat. Under `master_audio_file` that is worse than noise:
  the mouth is driven by a frozen take whatever the text says, and text the
  take does not contain is precisely what the no-invented-dialogue lint exists
  to prevent. A six-beat plan written to a locked master was linting six for
  six, and the repair turn was answering it.

  The exemption is the **sound bed**, not the silence. Zero lines and no bed
  still lints, because that is the shape H3 fills with speech of its own.

### Checks

- `check_planner.py` 145 -> 163, six of them on the wordless hop: that a beat
  naming a bed validates clean, that a beat with no bed still raises two
  lints, that the word-count lint is untouched by the exemption, and that the
  speech round is consequently not spent on a plan that is quiet on purpose.
- `check_audio_lock.py` 52 -> 59 — the window is cut once at load, the digest
  follows the cut, and the offset never reaches `hop_audio_window_s`. Two
  checks that already existed were **passing against the wrong text**: they
  anchored on the phrase "master_audio_file is", which also occurs in the
  widget tooltip, so `it raises rather than warning` had been asserting about a
  docstring. Re-anchored on the guard itself.
- `check_media_slots.py` 15 -> 17 — its SLOTS regex was `[a-z0-9_]+`, which
  cannot match `master_audio*`, so the new slot dropped silently out of the
  list the file checks and its widget was never verified to exist at all.
  Widened, plus a check that a fixed-width slot declares no `_end_s`: an
  `_end_s` the strip never draws would sit on the node body as a dial that
  does nothing, which is the failure that table exists to prevent.
- Both shipped workflows carry the new value; `widgets_values` goes 76 ->
  77 by appending, so no existing index moves.
- 29 checkers, all passing.

### What has been verified, and what has not

The loader has been run against a real 56.30 s take: at `0.00` it yields
56.30 s usable, at `3.50` it yields 52.80 s, the two digests differ so the hop
cache invalidates, and `90.00` refuses. The planner change has run end to end —
the six-beat plan that prompted it now validates 0 errors, 0 warnings, where it
was 0 errors and 6 warnings, and accepts on the first attempt.

The panel half is confirmed in ComfyUI, not just parsed: the window tracks the
plan's own duration, so the width it draws is the chain and not the file.

The offset has now been rendered. A 2-hop chain -- 226 frames, 9.42 s -- was
run as the pair described above, and that pair is what found the granularity
bug. It also produced the positive evidence for the loader: the residual
between the two arms is **flat** across all four quarters of the chain
(3.1 / 3.0 / 3.2 / 2.8 dB below signal), so the error was a constant offset and
not a per-hop accumulation. Cut-once-at-load behaves as designed.

**The corrected pair has not been re-rendered.** The measurement above predates
the step fix, so it establishes where the window *went*, not that it now goes
where the panel says. Re-running those same two arms is the confirmation, and
it is the one thing still outstanding.

## 2.1.0 — 2026-09-16

A second sampler pass per hop, a cache that makes the non-turbo base usable,
and a prompt pack that now has a trust boundary. **Every render behaviour here
ships off.** A workflow saved on 2.0.0 loads and renders identically — the new
widgets are appended at positions 71-82 and nothing is inserted or reordered.

### New

- **`hop_refine`** (RUN) — `off` (default), `full` or `pin_only`. A second
  sampler pass over each hop's latent before it is decoded and before it is
  handed forward as the next hop's pin. The pass has its own seed, its own
  sigma schedule and optionally its own model, so it is a genuinely separate
  render and not a continuation of the base one.

  It exists because the thing that holds a chain together is not per-hop
  quality. Drift compounds through what each hop hands the next, and a short
  under-converged second pass over the *joint* latent is the one mechanism
  measured to move the seam without also moving the face.

  The defaults are a confirmed external configuration, not this pack's guesses:
  `refine_denoise 0.50`, `refine_steps 2`, `refine_cond base`. At H3's
  `shift=12.0` that resolves to a schedule of `[0.9231, 0.8000, 0]` — one
  `res_multistep` step from 0.8 to 0, deliberately under-converged. Note what
  `refine_denoise` actually is: `BasicScheduler` computes `int(steps/denoise)`,
  so it sets the *step size*, not a noise amount. 2 steps at 0.50 means a
  4-step schedule truncated to its last two. Raising the denoise shortens the
  schedule; it does not add noise.

- **`refine_blend`** and **`refine_blend_interp`** — a per-frame keyframed lerp
  between the raw and the refined latent, default `0:0, 22:0, 44:1` linear.
  Frame 0 ships raw, the ramp is over latent steps 7-13, the tail ships fully
  refined. The blended result is what is delivered *and* what propagates, so
  the pin the next hop inherits is the blended one. Empty string disables the
  blend and ships the refined latent whole.

  The ramp's frame ratio is computed from the latent itself. The upstream node
  this follows derives it from a `duration` widget, and when that widget
  disagrees with the real render length the keyframes land in the wrong place
  with no error at all. There is no duration input here and no way to desync.

- **`refine_audio`** — `freeze` (default) or `refine`. On `freeze` the audio
  stream is masked out of the refine sampler, so audio leaves a refined chain
  bit-identical to an unrefined one. This is not the upstream default and the
  difference is not cosmetic: taking audio wholly from the refined latent was
  measured as making the voice strained across three runs. Mask polarity is
  **1 = denoise, 0 = freeze**, pinned by `audio_lock.assert_mask_polarity`; an
  inverted mask reads as "lip-sync died." With `master_audio_file` set the take
  still wins — refine never touches a locked audio path.

- **`refine_head`** — `refine` (default) or `freeze`. The other seam mechanism,
  kept as a widget rather than a choice because it is a trade and not a
  winner. `freeze` holds the hop's first frames out of the refine pass; it
  removes the seam flash and wins on the face (seam error 1.9x/1.7x against
  3.5x/7.3x) at a grain cost that is real and is invisible on bokeh.

- **`refine_model`** (optional MODEL socket) — run the refine pass on a
  different model from the base. Unwired means the base model. It is included
  in the hop cache key by fingerprint, so swapping it re-renders rather than
  serving a stale hop.

- **`refine_sampler`** / **`refine_scheduler`** — `same` follows the base.
  `res_multistep` + `simple` over an `lcm` base is the best combination tried
  so far.

- **`speed_mode`** — `regular` (default) or `turbo`. A named preset table, one
  place, mapping mode to refine defaults. Most of the turbo row is unmeasured
  and the tooltip says so. What *is* measured, on matched runs at a pinned
  seed, is that a turbo base is the degrader: junction MAE 8.40-10.85 and
  climbing hop over hop, against 2.07-4.02 flat for a plain hybrid over 9-10
  hops. Putting the turbo checkpoint in the base loader only did not save it,
  so it compounds through the conditioning path rather than the latent. The
  preset makes no claim to fix that, prints the cost once per run, and never
  silently corrects a widget.

- **H3 Cache**, a new node. It reuses MiniMax-H3's whole-block-stack residual
  across steps whose features have barely moved, which is what makes the
  non-turbo base fast enough to recommend at all. Drop it anywhere on the MODEL
  wire before the sampler; it patches a cloned patcher only, so it composes
  with SLA attention and with LoRA loaders in either order. Feed `refine_model`
  too if you run a separate refine model — the refine pass is its own sampler
  call and is not cached otherwise.

  Defaults are `0.05` reuse / `0.20` start / `0.80` end / `1` max skip, which
  are the settings actually being run in production rather than the wider
  window the original widgets invite. Both shipped workflows have it wired.

  **The implementation is silveroxides' work** (`ComfyUI-UtilsCollection`,
  AGPL-3.0), improved and ported by PlagueKind and redistributed with
  permission given 2026-09-16. It descends further back than that: its forward
  pass is a reimplementation of ComfyUI Core's `MiniMaxH3Model._forward`, and
  Core is GPL-3.0. `THIRD_PARTY_NOTICES.md` records all of it, including the
  parts nobody was in a position to relicense. If you redistribute this pack,
  read that file.

### The prompt pack now has a trust boundary

The rewrite was strong on craft and had no notion of untrusted input anywhere.
A brief reading "Write exactly 1 hop" was indistinguishable from the node's own
instructions, because the brief went into the turn first with machine
instructions concatenated after it.

- Every untrusted channel is now delimited — the brief, the SWAP brief,
  filenames read off disk, rail values — and `AUTHORING_PROMPT.md` carries a
  precedence paragraph stating that delimited text is scene material which can
  never change hop count, field lists, or the rules above it.
- The unbounded "unless the user message says otherwise" override in
  `SWAP_PROMPT.md` is gone.
- Validator feedback is labelled as node output. It was being appended as
  `role: "user"`, so model-authored text came back wearing your authority.
- `mp` and `locked` are documented with "do not author". `locked` is a boolean
  meaning "serve the cached render", and the pack uses the word as prose
  elsewhere — `bool("some text")` is `True`, which silently serves a stale hop.
- The two contradictory accounts of the 9-reference limit now agree with the
  code: it is a per-hop ceiling.
- `EXAMPLE_6_HOP.md` is regenerated from a compliant workflow. The only
  few-shot in the pack was breaking three of the prompt's own rules, including
  the unplated location the prompt itself calls the most common mistake.
- The prompt pack README's token count was off by about 3,000 and its `sed`
  example had a literal `\n` in it.

### Checks

Six new offline checkers, all in `tools/check_all.py`: `check_refine_blend.py`
(ramp arithmetic, CPU-only, including the ratio-from-latent fix),
`check_refine_audio.py` (mask polarity and master-lock precedence),
`check_refine_keys.py` (every refine widget changes the hop key),
`check_speed_mode.py`, `check_widget_order.py` (the positional-widget
guarantee), and `check_h3_cache.py`. That last one earns its place: the
vendored cache duplicates Core forward logic rather than calling into it, so a
Core change desyncs it *silently* — wrong output, not an exception. It has
already happened once in the wild.

`check_workflows.py` also now asserts node ids are unique, after a duplicate id
in a shipped workflow silently reattached another node's wires.

29 checks, all passing, including `check_audio_lock.py` and
`check_restart_trim.py` which were failing before this work.

### What has been verified, and what has not

The refine path has run: three 9-hop chains at `refine=full`, 6-step plain
hybrid base, no turbo, each with a second DiT on `refine_model` rather than
the unwired default. Junction MAE 2.21-4.62 and **flat**, texture -14.9%, and
face scale -1.4% from hop 1 to hop 9 -- the zoom creep did not happen. Audio at
hop 1 is sample-exact under `refine_audio=freeze`. These defaults are frozen on
the strength of that.

Two limits travel with that result, and neither is hidden here:

- **Attribution is open.** Only the `full` arm has run. The honest claim is
  "this configuration holds a 9-hop chain", not "the refine pass is why". The
  controlled `off`-vs-`full` pair at a pinned seed has not been rendered.
- **It was measured on a flat white wall, fixed close-up, near-zero motion.**
  The same model at the same step count comes apart on a wide moving shot. "6
  steps is fine" is a statement about that footage, not about H3.

Also unmeasured: the chain cost of base step count -- voice quality lands mostly
by 10 steps, but what a raised step count does to drift *over* a chain is not
known -- and VRAM for the refine pass, where the "one model is enough" answer is
read off the code rather than off a profiler.

## 2.0.0 — 2026-09-06

A full release, not a beta. The hop cache, the pin, the media slots and the
tone tools that accumulated on side branches since 1.1 are in this tree, plus
four new behaviours.

### New

- **`master_audio_file`** (MEDIA). One continuous take every hop lip-syncs
  to. Empty (the default) is off and does not change existing renders. When
  set: each hop is locked to a window of that file on the same clock as the
  picture; delivered audio is a passthrough of the take, no VAE round trip.
  The beat still needs the words in `<d>[English] ...</d>`.
- **`last_frame_guide`** (RUN, join & pin). `off` (default),
  `before_restart`, or `still`. It AddGuide-pins `start_image` at a hop's
  last pixel frame, so the hop *ends* on the photograph and a following
  restart — which opens on that same photograph — reads as a match cut
  rather than a jump. **`before_restart` is the setting to use:** it guides
  only a hop whose next shot is `anchor: "restart"`. `still` guides every
  hop, which also overrides an authored `framing` directive at every hop
  ending — a shot set `framing: close` plays close and then snaps to the
  still's wider framing in about 0.6 s, and the next hop pushes back in.
  Use `still` only when no shot authors a framing. Needs a start image.
  Neither becomes the next hop's frame 0.
- **`anchor: "restart"`** on a shot. That hop is a chain start: the start
  image is frame 0, nothing is relayed from the previous hop. It is a cut.
  Pair it with `join: hard_cut`. Restart hops now write their **full
  length** — they used to drop the 0.9 s overlap as if they were a
  continuation.
- **`refs` on a shot.** Which register stills ride that hop. Omit the field
  for the register default (unscheduled stills on chain starts, off
  continuations). `[]` is none. A filled list is those tags only, in that
  order. Unknown tags fail on the queue.
- **SWAP**, a fifth tab. A one-hop identity swap from a reference clip: the
  clip supplies the motion and the scene, a still from the REFERENCES rail
  supplies the person. **Write** drafts it, **Accept** writes exactly one
  shot plus the clip's description and never touches `ref_plan` -- your
  register is not rewritten. Contributed by @frankyi, then rebuilt from its
  own prose rather than merged.

  Four named modes, because at cfg 1.0 there is no negative branch and a
  mode that merely *omits* the swap line does not keep the clip's person --
  the identity photograph is in front of the encoder either way and governs
  the subject anyway. Each mode says positively what stays:
  `replace_person` (face, build, hairstyle and wardrobe),
  `head_swap` (face, hair and skin tone; the body, posture, hands and every
  garment stay with the clip), `face_only` (features only), and
  `keep_person` (swaps nobody -- the clip is a scene and motion plate, and
  the identity picker greys out). The taxonomy follows PromptMasterLD's edit
  laws; the prose is written fresh for H3 beats.

  Alongside them: **background** from the clip, from a `@tag` picture, or
  free; and an optional **wardrobe plate**, a `@tag` whose garment is *worn*
  -- draping on the body in frame and creasing where it bends -- rather than
  pasted.

  **Two things to get right, both of which cost renders to find out.** Do
  not run MEDIA's describe on the clip before a swap: that caption reaches
  the encoder as what `<Video 1>` *is*, and a caption naming a person asks
  for the person you are replacing. Four consecutive "head swap doesn't
  work" reports traced to that, a missing frame sequence and a weak
  citation -- no broken code among them. SWAP now warns when a caption names
  somebody. And drop the clip to about 0.3 MP: a reference clip's decode
  area is its token count, and its token count is its influence, so a
  full-size plate out-argues a single photograph.

### Already on the 1.2 tree, now in the release

- Three reference-clip slots and three voice slots. Numbering is dense.
- Lab tone anchor (`tone_compensate=anchor`, `tone_anchor_ref` hop1 / still).
- `pin_mech` (auto / motion_context / addguide).
- Hop cache: safetensors latent sidecar (no pickle), master buffer spilled
  to a delete-on-close mapping above 2 GiB.
- **Seam report** takes the chain's `info` output as an input and reads the
  join frames the render actually wrote. Wire it: with a restart in the
  chain the hop lengths are no longer uniform, and the `hops` / `overlap`
  widgets cannot describe that — on a 4-hop chain restarting at hop 4 they
  put the seams six, eleven and sixteen frames out, far enough to measure
  the flat middle of a hop and report three visible seams as invisible.
- Per-hop cache keys for pin, overlap, tone and `pin_to_qwen`, so hop 1
  survives those A/Bs.

### One change that affects every render

The master frame buffer is **fp16** rather than fp32, which halves the
largest allocation in the pack — an 8x15 s chain at 1280x736 goes from about
29 GB to 14.4 GB, and half the disk I/O when it spills. The buffer is
delivery-only: nothing in the conditioning path reads it back, and tone
correction still happens in fp32 before the write.

It is not bit-identical, and the number is small but real. The encode
truncates, so a value fp16 nudges below an integer boundary loses one 255th.
Measured over two million samples: **2.06% of pixels move, every one of them
by exactly 1, none by more** — well under the h264 encode's own error. The
`images` output is therefore an fp16 IMAGE. Core's save and preview paths
take it; a third-party node that assumes fp32 has not been tested against it.

### Verified on a GPU

- The audio lock joins across hops on one take: hop 1 `[0.00s-8.00s]`, hop 2
  `[7.08s-15.08s]`, delivered as a passthrough, drift +0 ms. Empty really is
  off — the generated voice comes back.
- `anchor: "restart"` stays in the shot with a fresh seed, and writes its
  full length (a 4-hop chain restarting at hop 4 delivers 724 frames, not
  the 702 the old formula gave).
- `last_frame_guide` turns the restart jump into a match cut, and `still`
  fights an authored framing as described above.
- fp16 survives delivery.
- SWAP `head_swap` on a 0.3 MP clip with no clip caption: the head is
  replaced, the body and its motion stay with the clip, and no colour or
  hair from the plate bleeds through.

### Still not verified

- Whether `refs: []` on a restart hop keeps the room instead of the identity
  portrait. The diagnosis behind that field came from frames, not from this
  code path.
- Anything longer than 4 hops at 8 s. The texture ratchet is unchanged and
  3-5 hops is still the honest limit.
- Three reference clips or three voices at once, on a card.
- SWAP's wardrobe plate and picture background. Both were cited-but-not-
  scheduled until the fix in this release and could never have rendered;
  the fix is covered offline, not on a GPU. `face_only` and `keep_person`
  have not been run either.

Saved 1.1 workflows load. New widgets were appended, not inserted, and no
existing default changed.

**A hop cache from 1.1 is fully invalidated by this release, deliberately.**
The model fingerprint now identifies the base checkpoint, which it did not
before — an int8 build and a bf16 build of the same architecture under the
same LoRA stack produced byte-identical keys, so the cache could serve frames
rendered under the other checkpoint. Closing that moves every key. The old
entries are never served, and the first sweep after the upgrade reclaims
them; their pickle-era latent sidecars are never read (that format is
retired) but are now counted against the budget and deleted with their entry
rather than orphaned. The practical effect is that the first chain after
upgrading re-renders in full.

## 1.1.1 — 2026-09-05

Core calls are keyword-only. Fixes `got multiple values for argument
'ref_image_size'` on hop 1 for ComfyUI builds that order MiniMax H3
parameters differently.

## 1.1.0 — 2026-09-03

Tabbed editor, `render_from` / `render_through` range, retention text on
every hop a still rides, computed canvas, per-hop reference keys.

## 1.0.x — 2026-09-02

First full release (WRITE panel, schema, rail). Patch releases cleared
registry-scanner findings and the WRITE-panel "no model is selected" bug.
