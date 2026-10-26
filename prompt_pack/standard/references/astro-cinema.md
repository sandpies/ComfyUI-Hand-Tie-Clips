Look overlay, not coverage. Shot budget lives in `director.md`. Shot / camera / dialogue syntax stay in `base-en.md` and `ref-en.md`.

# Astro Cinema

Look overlay. Load after the mode guides when the user names Astro Cinema. Bare “cinematic” does not load this file.

Stack with `director.md` only when the user asked for both this turn (or already named the combo). Confirm policy lives in SKILL.md.

Write photoreal film photography (motivated light, lens, materials, grain). It does not freeze the camera. Do not write `HOLD` / `static` / tableau. Do not write `ASTROCINEMAV01K2T`, `CinematicMH3`, or a safetensors name.

## 1. Style opening

No trigger token. The style opening is the cinematography below.

- Official T2VA / I2VA / FL2VA / L2VA: start of `integrated_multimodal_description` (before `[Shot 1]`).
- Official Ref2VA: the 1–2 style sentences before `[Shot 1]`.
- Author `style_and_tone`: the look sentence only.

Never put a LoRA tag on an I2VA / FL2VA / L2VA instruction line.

## 2. Cinematography

Do not lean on the word “cinematic”. In the style opening / `style_and_tone`, name what the shot needs among:

- time of day
- dominant light, secondary light, visible practicals
- camera distance and framing
- lens / depth of field
- skin and material response only when visible
- production design / environment
- weather / atmosphere
- color relationship
- grain, halation, or highlight rolloff when useful

Name which source is dominant. Do not list random light colors. One clear action per beat.

Photoreal: do not mix vector-art, cel-shading, or illustration language unless the user insisted — then warn in the header.

I2VA / FL2VA: describe lighting and materials the keyframe already shows. Do not invent a new grade.

## 3. Header

Append `· astrocinema`. If author-fields is on, also append `· author-fields`.

## 4. Author fields (only if chosen this turn)

Not a ComfyUI official paste. Mapping:

| Field | Content |
|---|---|
| `style_and_tone` | Cinematography (look only; no timeline, no trigger token) |
| `continuous_shot` | Single-shot body: action, acting, camera, timing |
| `multi_shot_sequence` | Multi-shot body; `[Shot N]` cut times still from `base-en.md`. Inner motion-clock ranges from `field-craft.md` stay inside the shot |
| `audio_design` | Ambience + physical + score in one block |

Keep `(S1)` and `<d>` dialogue inside the shot body. Do not drop spoken lines into `audio_design` only.

I2VA / FL2VA / L2VA instruction lines from `base-en.md` still come first when the mode needs them.

## 5. Wiring (only if asked)

Do not add a LoRA loader or a strength. Do not invent a node graph.

## 6. Self-check

Fix before showing if:

- `ASTROCINEMAV01K2T`, `CinematicMH3`, or a `.safetensors` name is in the paste
- style is only the word “cinematic”
- lights are a color list with no dominant source
- I2VA / FL2VA grade contradicts the keyframe
- cel / illustration is mixed in without the user insisting
- author field names appear without author-fields being chosen
- official field names are renamed on an official-schema rewrite
