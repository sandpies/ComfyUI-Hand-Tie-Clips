Source: 2D / anime grammar compiled 2026-06-11 by `Emily2040/seedance-2.0`
(`references/2d-anime-grammar.md`), practitioner-reported. No H3 render behind it —
see the vetting note in `CHANGELOG.md`.

# Anime / 2D overlay

Medium overlay. Load after the mode guide when the request is anime, 2D, cel,
hand-drawn, or cartoon. Stacks with `director.md`; `performance.md` still
governs faces. Official shot timestamps, camera verbs and labels stay in
`base-en.md` / `ref-en.md`, or `multishot.md` when that chain is on. Inner
motion-clock ranges are `field-craft.md` and are not extra cuts. This file
governs that 2D medium only. Live-action does not load it. Pixar 3D,
papercraft, collage, and handdrawn-live fusion stay in `official-looks.md`.

## 1. The no-lens rule

The one rule that matters most, because it is the one live-action habits break.

**Never use lens, bokeh, depth-of-field, focal-length, or camera-body vocabulary
in a 2D prompt.** Those words summon photoreal rendering, and the model reads them
as a request for a photograph. Name the medium first and keep every sentence
inside the animation process: *hand-drawn 2D animation, cel-shaded characters
over a painted background.*

This is the 2D equivalent of the affirmative-only law. Both are about naming only
what you want rendered.

## 2. Layers

A 2D scene reads as stacked artwork, and the model responds to layer language.

- **Cel over painted.** Crisp cel-shaded subjects over a soft gouache or
  watercolor painted background.
- **Background scroll / multiplane.** *The painted background scrolls past.*
  *Foreground silhouettes slide faster than the distant skyline.* Depth is made by
  differential speed, not by focus.
- **Held background, animated subject.** Say what stays still. A held frame is a
  feature of this medium, not a failure — see §3.

## 3. Motion grammar

- **Burst and hold.** Alternate high-effort fully animated bursts with held poses:
  *a burst of fluid full animation as she turns, then a held frame on her
  expression.* Continuous full animation is not the goal and reads as cheap.
- **Timing.** *Animated on twos* for classic cel cadence. *On ones* only for the
  one showcase move. [heuristic — test on your material]
- **Impact frames.** *A single high-contrast impact frame on the hit.*
- **Speed lines and smears.** *Speed lines streak the background during the dash.*
  *Her arm smears across the swing.* Put the speed in the lines, not in the face.
- **Follow-through.** Hair, cloth and coat tails keep settling after the body
  stops.

### Held frames on a chain

`multishot.md` rule 2 defers here when this file is on. A held frame is correct
grammar. Write the hold as a hold and put the motion in the lines, the smears
and the background scroll. Micro-motion on a held 2D frame is the animated-TV
look being asked for not to happen. Live-action chains still follow rule 2.

## 4. Camera in 2D

The camera is a rostrum over artwork, not a rig in a room. Pan across the painted
background; slow push-in on a held face; vertical tilt down a tower artwork. One
motivated move per shot still applies. Avoid dolly, handheld shake, and
lens-breathing wording.

Shot sizes still come from `base-en.md`. Wide is a painted vista, not a lens.

## 5. Light and colour

Light is drawn, not rendered.

- *Hard two-tone cel shadow.*
- *Rim light as a clean shape along the jaw.*
- *Specular drawn as a white wedge in the eye.*
- *Limited palette, warm paper texture.*
- *Flat colour with painted light bloom.*

Name a palette and a finish. The live-action lighting vocabulary in
`field-craft.md` — literal light sources and their direction — is compatible;
the photoreal adjectives are not.

## 6. Sound

Stylised sound reads better than realistic foley. A whoosh on the smear, a sharp
sting on the impact frame, room tone dropping out on the held frame.

Official writes keep ambience and physical sound in `overall_soundscape`.
A chain keeps diegetic sound inside the paragraph (`multishot.md` §3 and §6):
no field names, nothing invented, no score on a talking chain.

## 7. Across a chain or a multi-shot

- **Repeat the exact medium line in every shot.** Style that is stated once
  flickers between shots. The same words, the same order, every block.
- **Carry** character sheets, palette, line weight, layer roles and screen
  direction.
- **Open motion carries.** The last visible action in one block is the first
  visible action in the next.
- Use the accepted clip's observed final layout as the next opening layout.
- Do not switch to photographic lens or sensor language in a continuation.

## 8. Style safety

Describe technique, era and palette. Not a studio, franchise, or living artist.
*1990s hand-painted TV-anime look with grainy film texture* is safe grammar.
For a named studio or franchise, describe its technique, era and palette instead.

## 9. Failures

| symptom | fix |
|---|---|
| output drifts photoreal or 3D-CG | remove lens and depth-of-field words; lead with the medium line; name the painted background |
| motion feels floaty or rotoscoped | ask for snappy bursts on twos, held frames between beats, smears on fast arcs |
| faces melt during fast action | put the speed into lines, smears and background scroll; cut to a held impact frame |
| style flickers between shots | repeat the exact medium line in every block; keep one palette phrase constant |

## 10. Self-check

Fix before showing if:

- lens, bokeh, depth-of-field, focal-length or camera-body wording appears in a 2D prompt
- the medium line is missing, or appears in one block but not the others
- the medium line is not the first clause of the style opening
- a held frame is written as micro-motion because `multishot.md` rule 2 was applied
- continuous full animation is written with no held pose anywhere
- depth is created by focus rather than by differential layer speed
- fast action is carried by facial detail instead of lines, smears or background scroll
- live-action camera verbs (dolly, handheld shake, lens breathing) are in a 2D block
- photoreal light adjectives appear; the drawn-light vocabulary does not
- a studio, franchise or living-artist name is the style anchor
- a 2D chain changes palette, line weight, layer roles or screen direction between blocks
- a continuation block introduces photographic lens or sensor language
- this file's rules are applied to a live-action request or to an official look
