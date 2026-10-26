---
name: minimax-h3
description: >
  Write MiniMax H3 (Hailuo H3) prompts for local ComfyUI only. Never generate
  video. Never call MiniMax API or MiniMax Hub. Use when rewriting a scene
  into official T2VA, I2VA, FL2VA, L2VA, or Ref2VA fields for a local MiniMax
  H3 / Hailuo H3 / H3-Context-IR node, or when the user names T2VA, I2VA,
  I2V, FL2VA, L2VA, Ref2VA, integrated_multimodal_description, or
  subject_definitions. Use when rewriting for ComfyUI-H3-Multishot,
  H3-Multishot, a seamless chain, H3MultishotSampler, context_pin, or a
  --- separated multishot script. Use when the user runs /minimax-h3, or
  when the scene is a fight / combat rewrite, a
  cinematic / movie-cut / director coverage rewrite, an Astro Cinema
  look rewrite, an NSFW / undress / sex
  rewrite, an acting / facial-performance / emotion-beat / wooden-face
  rewrite, a fix / identity-drift / extra-fingers / phantom-camera
  repair, an anime / 2D / cel / hand-drawn / cartoon medium rewrite, a
  MiniMax official look (product ad, papercraft, paper
  collage, handdrawn-live fusion, music video / lyric typography,
  Pixar 3D short, brand promo, co-op game intro), or when they ask to
  plan / storyboard / multi-segment an H3 scene. Plan the shot
  list before writing when the shots are not already named.
when-to-use: >
  MiniMax H3, Hailuo H3, H3-Context-IR, T2VA, I2VA, FL2VA, L2VA, Ref2VA,
  H3 prompt rewrite, ComfyUI MiniMax H3, ComfyUI-H3-Multishot, H3-Multishot,
  multishot, seamless chain, H3MultishotSampler, context_pin, combat scene,
  fight, brawl, martial arts, 1vMany, director,
  cinematic, movie-cut, Hollywood, Astro Cinema, NSFW, undress, acting, facial performance, wooden,
  expression, identity drift, extra fingers, phantom camera, storyboard,
  plan, multi-segment, product ad, papercraft, paper collage, handdrawn,
  music video, lyric typography, Pixar 3D, brand promo, co-op game intro,
  motion clock, micromovement, inner timestamp, anime, 2D, cel, cel-shaded,
  hand-drawn, cartoon
argument-hint: "[t2va|i2va|fl2va|l2va|ref2va|multishot|combat|director|astrocinema|nsfw|performance|failures|plan|anime|2d|product-ad|papercraft|collage|handdrawn|mv|pixar3d|promo|game-intro] scene or refs"
metadata:
  short-description: Plan, then write local ComfyUI MiniMax H3 prompts (no generation)
  source: https://huggingface.co/MiniMaxAI/MiniMax-H3
---

# MiniMax H3 (local ComfyUI)

Turn the request into a paste-ready local ComfyUI MiniMax H3 prompt. Default
is official T2VA / I2VA / FL2VA / L2VA / Ref2VA. If this turn is the
H3-Multishot chain (`references/multishot.md`), that file owns the format —
not official `[Shot N]` fields. Do not collapse either into a 1–2 sentence
Imagine video prompt.

This skill is prompt-only. Never generate a clip. Never call a host image
or video generator. Never call MiniMax API, MiniMax Hub, or any remote
renderer. Words like "generate", "animate", "make a video", "i2v", or
"run it" mean write or repair the ComfyUI prompt, not render.

**Plan** is the default when the scene does not already name its shots.
Read `references/planning.md`, propose a story spine and a storyboard, and wait. Do not emit
the H3 prompt in that turn. The references exist to choose coverage, mode,
and continuity. A paragraph in and a prompt out skips that choice.

**Write** when any of these is true: they confirmed the storyboard; they
pasted an H3 prompt or a `---` chain to repair; they already named the
shots (sizes, cuts, and moves); or they said to skip the plan. The word
"write" alone does not skip it. After confirm, Write one clip at a time.

A specified `---` chain whose shots are already named is Write via
`multishot.md`. A chain whose shots are not named is Plan first.

Syntax, instruction templates, camera vocabulary, labels, and retention
markers live only in `references/`. Do not write those from memory.

## Context load

A skill folder is **not** all in context on first load. Hosts that follow
Agent Skills (Grok, LM Studio Bionic, Claude) inject only `name` +
`description` until this skill is selected; then they load **this file**.
`references/` stays on disk until you open a path below.

Read **only** the matching files this turn. Never open every file in
`references/`. Do not load official syntax or `multishot.md` during Plan.

| This turn | Read |
|---|---|
| Plan / shots not named | `references/planning.md` only |
| Plan, official look named | also `references/official-looks.md` |
| Plan, canvas / resolution step | also `references/canvas.md` |
| Plan, acting / face / emotion / dialogue | also `references/performance.md` |
| Plan, storyboard step | also `references/coverage-menu.md` |
| Write T2VA / I2VA / FL2VA / L2VA | `references/base-en.md`, then `references/field-craft.md` |
| Write Ref2VA | `references/ref-en.md`, then `references/base-en.md`, then `references/clarifications.md`, then `references/field-craft.md` |
| Write, a confirmed board named a coverage-menu row | also `references/coverage-menu.md` (copy that Paste cell) |
| Write ComfyUI-H3-Multishot / seamless chain / pack **multishot** | `references/multishot.md` (not `base-en`, not `ref-en`, not `field-craft`) |
| Fight | also `references/combat-scene.md` |
| Anime / 2D / cel / hand-drawn / cartoon medium | also `references/anime-2d.md` |
| Director coverage | also `references/director.md` |
| Astro Cinema | also `references/astro-cinema.md` |
| NSFW / undress | also `references/nsfw.md` |
| Acting / face / emotion / wooden / dialogue-heavy | also `references/performance.md` |
| Fix / identity drift / extra fingers / phantom camera | also `references/failures.md` |
| Product ad / papercraft / collage / handdrawn / music video / Pixar 3D short / brand promo / co-op game intro | also `references/official-looks.md` |
| Named film/TV/celebrity (Plan or T2VA) | H3 often knows famous roles by name in T2VA; original or obscure faces need Ref2VA sheets |

After a Plan confirm, Write uses the Write row plus any overlays already
chosen. Cap: one syntax file set + the overlays that apply. Official set is
`base-en` (± `ref-en`, ± `clarifications`) + `field-craft`. Chain set is
`multishot.md`. Never both. `field-craft` is off on a chain.
`coverage-menu.md` is not a third syntax. It is the storyboard menu, and
at Write it is only the Paste cell of a row the board chose.

The user wires images, video, and audio in ComfyUI. Do not invent ComfyUI
node graphs, socket maps, or file paths unless they asked for wiring help.

## 1. Inspect

Read every attached image (and video/audio if present) from the pixels, not
the filename. Note identity, clothing, colors, pose, composition, lighting,
and the role the user assigned each asset.

If they already pasted an H3-shaped prompt or a `---` chain, repair
violations only. Do not restyle it unless they asked for an overlay
restyle or a plan.

## 2. Mode and duration

If this turn is Write and the format is the H3-Multishot chain, mode is
`multishot` and duration is `frames_per_shot` (default 362 / ~15.1 s unless
they named 243 or 192). Skip the table below. Syntax is only in
`multishot.md`. A chain whose shots are not named stays in `planning.md`.

Honor an explicit official mode name. Otherwise:

| Situation | Mode |
|---|---|
| Text only | T2VA |
| One image is the opening frame ("i2v", "animate this") | I2VA |
| Labeled first + last frame | FL2VA |
| One image is the ending only | L2VA |
| Identity, wardrobe, scene, style, or motion refs; or any mix that is not purely keyframe | Ref2VA |

A single image used as a character or scene reference, not as a frame, is Ref2VA.

First-frame or last-frame **plus** other identity/style refs is Ref2VA with
`keyframe completion`, not I2VA. The frame image gets a standalone
`<Picture N>`; the reusable look gets a `<Subject N>`.

If the user named I2VA but attached multiple character sheets, switch to
Ref2VA and say why.

Duration: the user's value if it is in 4–15 s, else `6.58` (158 frames).
Off-grid seconds snap up — `references/canvas.md`. Combat overlay overrides
unspecified duration; see `references/combat-scene.md`. Official-look
defaults are in `references/official-looks.md`. Decide duration
before any cut time or motion-clock range. Longer than 15 s → sequential clips, one H3 prompt each.

## 3. Read the spec

Open only the files in **Context load** for this turn. Bare “cinematic”
loads director, not astro. Bare acting / wooden / expression / a face
emotion loads performance, not director. Anime, 2D, cel, hand-drawn, or
cartoon loads `anime-2d.md`. Pixar 3D, papercraft, collage, and
handdrawn-live fusion load `official-looks.md` only. If `multishot.md`
is on, skip the rest of this section — the paste is a `---` script.

If director and/or astro apply and the user has not already named the
combo **and** the field schema, ask once:

1. coverage / look / both
2. official H3 fields vs author fields (`style_and_tone`,
   `continuous_shot` / `multi_shot_sequence`, `audio_design`)

On a Plan turn this is one interview step. It does not replace the
storyboard. Shots that are not named stay in `planning.md` until the
board is confirmed. On a Write turn, after those answers, write one
block. Do not emit both schemas. Author fields are not a ComfyUI
official paste; mapping is only in `astro-cinema.md`.

Copy I2VA / FL2VA / L2VA instruction lines character-for-character from
base-en. Official field names and retention markers unless author-fields
was chosen.

## 4. Rewrite

Lock the timeline, then write.

If `multishot.md` is on, ignore official `[Shot N]` / field names / 250–500
word density in this section. Syntax, density, and join rules are only in
that file.

**Density.** The multimodal body is a playback transcript, not a logline.
Every sentence must be something visible or audible on the timeline. The
cases in base-en teach structure, not length — a 6–10 s clip usually needs
~250–500 words. Ref2VA `detailed_description` length is in ref-en §5.2.

**Shots.** `[Shot 1]` has no timestamp. A later `[Shot N]` starts
`At MM:SS.mmm` and is only a camera cut, strictly increasing, inside the
duration. Inner `At MM:SS.mmm-MM:SS.mmm` ranges clock micromovements inside
the current shot; syntax is only in `references/field-craft.md`. I2VA and
FL2VA default to one shot; add a cut only when the user asked, a new
viewpoint is required, or `performance.md` is on and the face-beat count
requires a split. A cut must introduce new information — distance or slight
angle changes are camera motion. FL2VA lands on the last frame in the final
shot. L2VA infers a plausible opening and converges onto the last frame.

**Invent vs lock.**
- T2VA: fill unspecified scene, character, action, and sound so the
  timeline is complete and consistent with the ask.
- I2VA / FL2VA: lock what the keyframe shows (identity, clothes, colors,
  objects, spatial relationships). Invent only the motion path.
- L2VA: invent only a preceding state that can land on the last frame.
- Ref2VA: lock defined subject traits. New actions are fine; changing a
  defined trait is `partially_preserved` or `attribute_transfer`.
- Never invent dialogue, lyrics, or on-screen text. Never translate them.
  If the user's lines do not fit the duration, keep them verbatim and use
  `<cutoff>`.

**Style.** Open with a concrete style token (`Live-action, cinematic`,
`2D-animated`, …) derived from the keyframe or refs — from the text for
T2VA. Do not inject a named studio unless they asked. Do not pad with
empty adjectives (`beautiful`, `stunning`, `emotional`).

**Sound.** Dialogue, singing, and diegetic music stay in the multimodal body.
`overall_soundscape` is ambience + physical + non-verbal only (`N/A` only
for requested silence). `non_diegetic_music` is instruments, tempo, and
dynamics — no mood words — or `N/A`.

**Ref2VA extras.** Style opening is 1–2 sentences *before* `[Shot 1]`.
`summary` starts with a `[task type]` prefix. The summary must be
self-contained: subjects, setting, shot flow, and FX. The node has no
memory of prior clips — never cite earlier takes or “same as last pass.”
One retention line per label. Do not create a standalone `<Picture N>`
for a subject-only image.

## 5. Contracts

**Base** — T2VA starts at the three fields. I2VA / FL2VA / L2VA start with
the exact instruction from base-en, a blank line, then:

```text
integrated_multimodal_description: ...
overall_soundscape: ...
non_diegetic_music: ...
```

**Ref2VA** — this order, these names:

```text
subject_definitions:
summary:
retention_analysis:
detailed_description:
overall_soundscape:
non_diegetic_music:
```

Author-fields contract is only in `astro-cinema.md`.

**Multishot chain** — contract is only in `multishot.md`. One paragraph per
generate, `---` between them. No official field names.

## 6. Self-check

Re-read the rewrite against the selected guide. Fix before showing it if:

- an instruction line is paraphrased
- Shot 1 has a timestamp, or a cut time is ≥ duration
- an official write fails the `field-craft.md` self-check, including a negation in the paste (no, not, don't, never, without, avoid)
- an undefined label appears, or a defined label is never used
- music uses mood words, or the soundscape repeats dialogue
- a keyframe mode contradicts the image
- Ref2VA style sits inside `[Shot 1]` instead of before it
- combat overlay is on but its self-check fails (see combat-scene.md)
- anime / 2D overlay is on but its self-check fails (see anime-2d.md)
- director overlay is on but its self-check fails (see director.md)
- astro overlay is on but its self-check fails (see astro-cinema.md)
- nsfw overlay is on but its self-check fails (see nsfw.md)
- performance overlay is on but its self-check fails (see performance.md)
- failures overlay is on but its self-check fails (see failures.md)
- official-looks overlay is on but its self-check fails (see official-looks.md)
- multishot chain is on but its self-check fails (see multishot.md)
- a coverage-menu row is in the paste but its self-check fails (see coverage-menu.md)
- a named studio appears that the user did not ask for
- the prompt cites a previous generation the model cannot see
- a Ref2VA write fails the `clarifications.md` self-check
- on-screen text or a `<d>` tag uses curly quotes, a spaced or uppercased tag, or a non-breaking space

## 7. Output

Always prompt-only. If Plan is open (`references/planning.md`), interview
and stop — header `· plan`, no prompt block yet.

If the director/astro confirm in §3 is still open, ask those two questions
and stop — no prompt block yet.

Otherwise: one-line `mode · duration` header, then overlay tags from the
files that were actually on (`combat`, `director`, `astrocinema`, `nsfw`,
`performance`, `failures`, `anime2d`, plus the look tag from `official-looks.md`;
`author-fields` only if chosen). `field-craft` and `coverage-menu` have no
header tag. Chain mode is `multishot`; its duration line is in
`multishot.md`. Do not keep `· plan` on a Write
block. Official schema is ready to paste into a local ComfyUI H3 node.
Chain schema is ready to paste into the Multishot sampler `script` input.
Author-fields is not. After a Plan confirm, include the handoff in
`planning.md` (label → file, canvas). Stop there. Do not add a LoRA file, trigger, or strength. `references/adapters.md` is retired.

Do not generate. Do not call a host image or video tool. Do not add host
image/audio bindings. Keep official H3 labels (`<Picture N>`,
`<Subject N>`, `<Video N>`, `<Audio N>`) so the user can match them to
ComfyUI inputs in definition order.

Local Ref2VA sockets: ≤9 images, ≤3 videos, ≤3 paired video soundtracks,
≤3 standalone audios. There is no combined file cap. If the user exceeds a
socket, keep every label in the prompt and say which type they must drop
or split in ComfyUI. Detail is in `references/canvas.md`.

On a safety block, stop and do not render a substitute clip.
