# Planning

Interactive phase. This is the default when the scene does not already name its shots. Also load when they say plan, storyboard, multi-segment, help me figure it out, or they do not know the scene yet. Do not write the H3 prompt until they confirm the spine and the storyboard. Do not read `base-en.md`, `ref-en.md`, `field-craft.md`, or `multishot.md` during the interview — those wait for Write. If the scene has a face, emotion, or spoken line, also read `references/performance.md` (beat budget, eyeline, speaking-shot length).

Skip every step they already answered. If the spine and the coverage are the open steps, propose both in this turn.

A `---` chain whose shots are not named is still this file. After confirm, that chain is Write via `references/multishot.md`. A chain whose shots are already named does not open this file.

One or two questions per turn. If they have no idea, suggest 2–3 H3-feasible options (mode, duration, refs) and wait.

Write skips this file only when SKILL.md says this turn is Write.

Header during the interview: `· plan`. After confirm, Write one clip at a time.

## Interview order

Skip a step they already answered.

1. **Logline or discover.** Empty → 2–3 ideas that fit 4–15 s.
2. **Mode.** Use the SKILL.md table. Character sheets = Ref2VA, not I2VA. Say why if you switch. If they name a film/TV role or celebrity, H3 often knows it by name: T2VA-by-name is an option for known faces; original OCs and locked likeness still need Ref2VA sheets.
3. **Duration and segments.** 4–15 s per clip on the `17n + 5` grid (`references/canvas.md`). Do not write `6.00` — that snaps to `6.58`. If they already named an official look, use that look's unspecified duration (`references/official-looks.md`). Split longer stories. End a clip on a complete action, not mid-word. Ask how clips chain: last frame of N as FL2VA first/last of N+1, vs a still from the previous render as a Ref2VA ref. Do not assume.
4. **Continuity bible (2+ clips).** Identity, wardrobe, location, lighting, injuries, props. Each later Write must restate this. The node has no memory — never “same as last pass.”
5. **Cast, location, style.** H3 covers many styles. Do not inject a studio name unless they asked. If they named a MiniMax official look (product ad, papercraft, collage, handdrawn, music video, Pixar 3D short, brand promo, co-op game intro), read `references/official-looks.md`. If style is open, offer 2–3 options (live-action photoreal, a named anime studio they might want, 3D CG, …) and wait. Write uses only the chosen token.
6. **No LoRA.** Do not suggest a LoRA, a finetune, a trigger, or a strength. Combat and Astro Cinema are prompt overlays. NSFW is `references/nsfw.md` when the scene is undress or sex.
7. **Dialogue ledger.** User lines only. Fit to the **speaking shot** (mouth fills that whole shot — `references/performance.md`), not the gap to the next timestamp. `(S1)` / `<d>`. Keep the writing-guide cutoff marker (`<cutoff>`).
8. **Audio.** On-screen vs VO, soundscape vs score vs `N/A`.
9. **Assets (Ref2VA / keyframes).** Each file: identity / wardrobe / scene / first frame / last frame / motion / audio. Identity/wardrobe/scene/motion → `<Subject N>`. Concrete first/last/keyframe → standalone `<Picture N>`. Video / audio assets → `<Video N>` / `<Audio N>`. Caps, per socket: ≤9 images, ≤3 videos, ≤3 paired video soundtracks, ≤3 standalone audios. No combined 12-file cap. Drop or split only the type that is over. Detail is in `references/canvas.md`. Prefer 2–4 separate identity stills over one multi-view character sheet (`references/failures.md`). Full label rules wait for Write (`references/ref-en.md`).
10. **Canvas.** Read `references/canvas.md`. Output W×H, I2VA/FL2VA stills matching aspect, Ref2VA `match` vs `max`.
11. **Story spine.** One clip is one change. Before any shot, write four lines. When `official-looks.md` is on, its beat recipe is this spine. Do not replace it.

- **Promise.** The question or stake the first image makes visible.
- **Start.** The state at 0. Already true. No prologue and no normal-life setup.
- **Turn.** The one change that makes a new ending possible. It sits around the middle. The payoff follows from it.
- **Payoff.** The last image, complete, held long enough to read. It answers the promise. Nothing after it.

Beat count is the story, not the motion clocks:

| Clip | Beats |
|---|---|
| ~6.5 s | Start, then the turn and the payoff as one landing |
| ~10 s | Start, turn, payoff |
| ~15 s | Start, attempt, turn, payoff |

Each beat is one visible change, and each beat causes the next. Two beats that show the same state merge. A fight's strikes are not story beats (`combat-scene.md`). A face's expression beats are not story beats (`performance.md`). If they already named the start, the turn, and the end, skip this step. If two endings would change the story, show both spines and wait. Otherwise propose the spine in the same turn as the shot list.

12. **Storyboard.** Read `references/coverage-menu.md`. Per clip: duration, one line per shot (time range, size, a plain official verb or a menu row, which spine beat it delivers), pickups (and clothing states if nsfw — `references/nsfw.md`), label → file. One shot delivers one beat, or a new view of that beat the previous shot cannot show. A shot that restates a beat comes out. Prefer a plain verb. Use a menu row only when the beat needs that result. Propose one board. If two coverages would change the scene, show both in a few lines and wait. Do not emit the prompt. The shot list is camera cuts only. Micromovement clocks are added at Write inside each shot (`references/field-craft.md`); do not storyboard one shot per twitch. If the clip has a face, emotion, or spoken line: count expression beats and split any shot that holds more than two or three (`references/performance.md`).
13. **Confirm** the spine and the storyboard. If **2+ clips**, also lock the long-chain block below before Write. Then Write the clip they pick (default clip 1).

## Long chain (2+ clips)

H3 does not output a feature. It outputs sequential ≤15 s clips. The node has no memory of prior clips. Plan this as a **master plan**, not one prompt.

### Master plan table

One row per clip, before any Write:

| Clip | Duration | Mode | Starts from | Harvest after |
|---|---|---|---|---|
| 1 | s | Ref2VA / T2VA / … | sheets / none | last frame (+ identity still if needed) |
| 2 | s | usually Ref2VA or FL2VA | last frame of 1 as `<Picture>` and/or still as `<Subject>` | last frame |
| N | … | … | … | … |

End each clip on a **complete action**, not mid-word and not mid-thrust. That is the cut you will stitch on.

Chain-in (ask; do not assume):

- **Last-frame bridge:** last frame of N → first frame of N+1 (I2VA) or FL2VA pair.
- **Still as Ref2VA:** a still (or last frame) as `<Subject>` identity/wardrobe; new action in the prompt. Restate the continuity bible in every Write — never “same as last pass.”
- **Video ref:** `<Video>` only if they actually feed a prior clip (counts against the 3-video cap).

### Generation checklist (repeat each clip)

Before Write clip N:

1. Continuity bible restated (identity, wardrobe, location, light, injuries, props).
2. Label → file for **this** clip (definition order). Shared sheets keep the same role; the harvested last frame is a new `<Picture>` / `<Subject>` as planned.
3. Canvas W×H identical across the chain (see `references/canvas.md`).
4. Dialogue leftover from the ledger that still fits this duration.

After they generate clip N (they run ComfyUI; this skill does not):

- Ask them to **harvest** the last frame from the **native H3 clip** (24 fps, canvas W×H), before interpolate/upscale. Use a clean identity still if that last frame is motion-blurred.
- Update the master-plan “starts from” for N+1.
- Write clip N+1 only when that harvest exists.

### Stitch / post (once for the chain, after the master plan)

This skill does not stitch by default and does not invent a Comfy graph. **Check the post pipeline, then concat viability**, then advise. Do not assume 24 fps or canvas W×H at join time.

**Post pipeline (ask before any concat advice):**

H3 generation is 24 fps at the canvas W×H (`references/canvas.md`). Many workflows then 2× interpolate (FILM, RIFE, …), 4×, or upscale.

Lock, for **every** clip the same:

| | Native H3 | After post (delivery) |
|---|---|---|
| FPS | 24 | e.g. 48 if 2×, 60/96 if they said so, or still 24 |
| W×H | canvas | e.g. 2× spatial, or still canvas |

If they interpolate or upscale: do it **per clip with the same settings**, then join the **post** files. Concat of mixed 24 + 48 fps (or mixed sizes) will fail or judder.

Last-frame harvest for chain-in stays on the **native** 24 fps H3 frame, not an interpolated in-between.

**Concat check (in this order):**

1. If this host can run a local shell: run `ffmpeg -version` (Windows: `where ffmpeg`). Treat a version line as yes.
2. If this host cannot run a shell, or the check fails: ask whether **they** have `ffmpeg` (or another local concat) on the machine they will join clips on.
3. If still unknown: discover what they *can* use — NLE (Resolve, Premiere, CapCut, …), a Comfy stitch/concat node, or neither.

**If ffmpeg (or equivalent concat) is available**

Join only files that already share **delivery** fps, W×H, and codec. Hard-cut concat, no scale, no fps convert at join. At stitch time (clips exist), recipe — `-c copy` only if those match:

```text
file 'clip01.mp4'
file 'clip02.mp4'
```

```text
ffmpeg -f concat -safe 0 -i list.txt -c copy out.mp4
```

If copy fails (codec/size/fps mismatch): they did not finish post the same way on every clip — fix that; do not fps-convert in the concat unless they asked. Do not invent xfade or audio ducking unless they asked.

**If they cannot concat locally**

Do not pretend they can. Advise the next thing they actually have. Timeline fps and size = **delivery**, not native 24 unless they skipped interpolate/upscale:

| They have | Advise |
|---|---|
| NLE | Import the post clips in order, timeline at delivery fps and W×H, hard cuts on the planned boundaries. Mix or replace score there if they want one piece of music. |
| Comfy stitch / concat | Use that node on the post clips; same delivery fps and W×H. Do not invent a graph unless they asked for wiring. |
| Neither | Export numbered post clips (`clip01`, `clip02`, …). Join later on any phone/desktop editor: drop in order, do not stretch. Optionally point them at installing ffmpeg if they want a one-command join next time. |

Also lock:

- **Cut type:** hard cut on the planned action boundary (default) vs a short overlap they must generate on both sides (native H3), then interpolate after.
- **Performance pause / late reaction:** if `performance.md` was on, put the pause and the missed ~0.2 s on an insert or the cut, not in the prompt. Keep insert shots in the storyboard so there is something to cut to.
- **Audio:** keep each clip’s native stereo, or replace score in post. H3 score will not continue across clips unless they reuse `<Audio>` or replace it in the NLE. Interpolate does not invent audio frames — duration should stay the same if fps only changes.

## Handoff (each Write, not only clip 1)

Not a node graph unless they asked:

- Definition order: `<Picture 1>` = this file, …
- Canvas W×H and length (same W×H as the chain)
- Clip N of M, what to harvest after
- One fenced official prompt
