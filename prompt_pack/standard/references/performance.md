Source: https://github.com/phileiny/h3-storyboard-skill (MIT, Ray / phileiny, 2026).
Measured on 9:16 Ref2VA local ComfyUI drama unless marked unisolated. Apply at any
aspect when this overlay is on.

# Performance

Acting / face overlay. Load after the mode guides when Plan has a face, emotion,
or spoken line, or Write is acting, facial performance, emotion beats, a wooden
or flat face, or dialogue-heavy. Syntax stays in `base-en.md` / `ref-en.md`, or
in `multishot.md` when that chain is on. Coverage stays in `director.md`. Combat
hits stay in `combat-scene.md`. Length grid and 9:16 whole-vs-large stay in
`canvas.md`.

When `multishot.md` is on: extra face beats are another `---` generate (that
file). Do not emit official `[Shot N]`. Shot-size nouns, stillness, and negation
stay there. This file still owns eyeline, A→B hide, and prop / liquid contact.

Do not invent spoken lines to “help” a silent face. Split shots instead.

## 1. Beat budget

Count expression beats before writing. More than two or three in one shot →
split into ~2–3 s shots, one main face beat each. Nine beats in one 7 s close-up
averaged to a freeze (same seed; split recovered the motion). The ceiling
between 2 and 9 is unmeasured — split at more than two or three.

I2VA / FL2VA one-shot default yields when this overlay is on and the count
requires a split. FL2VA still lands on the last frame in the final shot.

The cut is the performance. The audience re-reads the face at the cut.

When `director.md` is also on: coverage shots still change size or axis; a
face-beat shot may hold a still crop. Do not write `HOLD`, `freeze`, or “nothing
changes” as a command — describe the crop and the one beat.

## 2. Face change

Do not write A→B on a visible face (`the crease smooths`, `the smile fades`).
H3 interpolates the two states; the face reads like rubber.

Hide the change: close the eyes, cover, or cut; change while occluded; open on
the new state. The same hide works for a **design** swap (a different eye ref)
if the lids go to a described full-closed shape. If a sheet is half-lidded,
“eyelids come down” snaps to that sheet — write the closed shape (`each eye is a
single curved line, no eye showing`).

Do not write “nothing about the face changes” to hold a pause. Unisolated from
beat density; still do not. The pause lives on the cut (`planning.md` stitch).

## 3. Eyeline

If the look-target is off-frame, H3 looks at the lens. Move the camera onto the
look so the plot pose already faces us. Write that they do not look at the
lens. Do not add a head-turn that fights the plot lock.

Top-down / straight down on a character: face and scale collapse. Put the
camera at table height looking across unless they asked for plan view.

## 4. Speaking shot

The mouth fills the **whole speaking shot**. A line timestamped 3.4 s with the
next beat at 4.0 s still moved the mouth from ~2.2 s to clip end. Post-speech
beats (swallow, “finishes speaking”) go in the **next** shot.

`<d>` reallocates frames toward that shot and squeezes neighbors. Keep
background-critical continuity out of a clip that carries a line, or run two
takes. Unisolated for the missing extra: treat it as likely.

Emotion sits in the delivery clause **outside** `<d>`. Inner VO:

```text
the young woman, in a small unsteady voice that catches once (S1), says in an
off-screen voiceover: <d>[Language] …</d> while her lips remain closed.
```

If they will dub: budget live-line length against the speaking **shot**, not
the gap to the next timestamp. VO laid in post can span shots.

Chain quoted speech and the +4 s quiet budget stay in `multishot.md`.

## 5. Scale and props

Fractions and unit distances are ignored (`two thirds as tall` → ~45–52%;
`a hand's width short` still touched). Describe the crop, or use something
already in frame as the ruler, and name the dry gap.

Do not name an object that must not appear (a phone used only as an aspect).
A specific panel / screen shape: blank geometry ref; do not feed a contentful
card (glyphs garbage). Screen contents stay post.

Prop contact and unbounded liquid: do not generate the collision or a volume
that “spreads / widens” with no stop. Sweep or cut, open on the aftermath.
Combat hits stay in `combat-scene.md`.

Do not glue dirt to a protected surface with a preposition (`around`, `on`,
`through`, `soaks into`). State a gap and that the surface is dry.

## 6. Audio ref (only if they feed one)

`<Audio N>` is a mouth / breath scaffold, not a keeper track. Expect pitch
~2 semitones high, a narrower range, and accent drift. Standalone wav →
`ref_audio_0`, not `ref_video_audio_0` (silent fail). Prompt text cannot
describe the waveform; delivery still belongs in the clause outside `<d>`.

## 7. Header

Append `· performance`.

## 8. Self-check

Fix before showing if:

- one shot holds more than two or three expression beats
- a visible face is written as A→B instead of hide-then-open
- “eyelids come down” is used when a half-lidded sheet exists
- the look-target is off-frame and the camera did not move onto it, or they
  look at the lens
- a pause is written as “nothing changes” / freeze this face
- a swallow or “finishes speaking” sits in the same shot as the line
- a fraction or unit distance is doing the work of a crop / in-frame ruler
- a clip with a line also carries background-critical continuity with no
  second take
- prop collision or unbounded liquid is generated in-camera (skip when
  `combat-scene.md` owns the contact)
- `multishot.md` is on and an official `[Shot N]` was used to split a face beat
