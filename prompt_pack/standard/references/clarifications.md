Source: staff answers on https://huggingface.co/MiniMaxAI/MiniMax-H3/discussions/71. The "Measured locally" section is from ruashots/open-h3-ir and is not a staff answer.

# Ref2VA clarifications

Staff answers do not replace `ref-en.md`. They settle cases the guide leaves ambiguous. The measured section settles two cases the guide does not.

## Subjects may reference each other

If an outfit, prop, or other unit must be tracked on its own, define it as its own subject and state the relationship:

```text
<Subject 3> is the young blonde woman in <Video 1>, with long blonde hair and a light-pink button-down shirt with rolled-up sleeves.
<Subject 5> is the referenced outfit in <Picture 2>, worn by <Subject 3>.
```

If it does not need independent tracking, fold its features into the parent subject instead of creating a second label.

## Partial visibility is not `partially_preserved`

`partially_preserved` means some *defined* reference characteristics are changed, omitted, or only partly used. A tighter crop that still keeps the defined look is `fully_preserved`.

One line per label. Do not split a subject into per-shot retention rows because later shots show less of it. Put the tighter framing in `detailed_description`.

```text
<Subject 1> (appears in [Shot 1], [Shot 2], [Shot 3]): fully_preserved - the referenced coffee-shop environment is retained.
```

## What actually has to be exact

Label meaning, subject relationships, the correct retention marker, and using each label in the shots where it applies. The template wording does not have to be copied.

## Why visual details repeat

Each section does a different job:

- `subject_definitions` — what the referenced content is
- `retention_analysis` — how those characteristics are kept or changed
- `detailed_description` — how the content appears in each shot

Repeat the relevant traits at first clear appearance, then reuse the label. Do not paste the same sentence into all three sections.

## Measured locally

Not MiniMax staff. Source: ruashots/open-h3-ir, main, read 2026-10-09.

### A video edit does not lock framing

Twelve renders of a 124-frame source on a 5090, 20 steps, `res_multistep`. Identity held, and a requested change to the subject held. Action timing held. Framing over time did not: nearest-source-frame agreement sat around 0.20–0.27, against 1.00 for the clip compared with itself.

Write a `<Video N>` edit as the same subject and the same beats, plus the change that was asked for. Do not promise a frame-for-frame match. Do not mark the source framing or cut structure `fully_preserved` — `weak_reference` is the marker for that, as in the official video-structure example. A subject's identity taken from the video can still be `fully_preserved`.

### Audio is never a frame

`<Audio N>` is a sound signal. It has no frames. Do not write that it is a first frame, a last frame, or a keyframe. Do not use `keyframe completion` unless an image is that frame. A writer with the guide in context still did this on 4 of 50 audio-only briefs.

## Self-check

Fix before showing if:

- a video edit promises the source framing shot for shot, or marks that framing `fully_preserved`
- an `<Audio N>` is called a frame, or `keyframe completion` is used with no image
