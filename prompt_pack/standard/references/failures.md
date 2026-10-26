Source: community empirical (mainly teskor-hub/minimax-h3-skill troubleshooting,
2026-08). Sheet-layout reproduction from MiniMax-AI/MiniMax-H3
`minimalist-product-ad-generator`. Face-beat rules stay in `performance.md`.
Length grid stays in `canvas.md`.

# Failures

Repair overlay. Load when the user wants to fix a clip, identity drift, extra
fingers, a phantom camera or phone, a weightless fall, a repeating event, or a
negative prompt that did nothing.

There is no negative socket on the stock ComfyUI H3 graph (CFG ~1). Write the
desired state. `no extra fingers` / `does not turn` put those tokens in.

## 1. Identity

Identity lives in `<Subject N>`, not a standalone `<Picture N>`. Merge sources
in one subject (`appearance from <Picture 1>`, `motion from <Video 1>`) and
scope the video in `retention_analysis`.

Name distinguishing marks by landmark and side, same wording in definitions,
retention, and shots. A centimetre mark will not survive a wide — frame closer
or accept it gone.

A multi-view character sheet, 4-panel product board, or storyboard grid as
**one** image is weaker than 2–4 separate stills: at `ref_image_size: max`
each panel is a fraction of 2048 px, and H3 treats gutters, panel borders,
and the sheet layout as content — it often **reproduces the grid in the
video**. Prefer separate stills. If they only have a sheet, treat it as a
weak identity ref, not the primary, and write a single full-frame
composition (never “four panels”, split-screen, or a product wall).

## 2. Camera as a prop

`she holds the camera` renders a device. Official camera vocabulary in one
sentence; arms and body in another. When the device is the viewpoint, use `POV`
and never name it.

## 3. Hands

Foreshortened hands reaching at the lens grow extra fingers. Crop them at the
frame edge, or if they must show: `five clearly separated fingers, a firm grip`.

## 4. Event speed

Duration is event speed. A 1.5 s fall is slow motion. Budget a real fall at
~0.5 s, then aftermath. Give intermediate poses and put the ground in frame.

Name an event once. Block a repeat with aftermath state (muzzle down, dust,
spent shell), not `no second shot`.

## 5. Camera and pose

One primary camera move per shot. An orbit is `Arc Shot` plus background
parallax, not `she turns`. Back-view + no body rotate + eye contact scrambles
anatomy — stop at three-quarter and let the shoulders turn with the head.

## 6. Header

Append `· failures`.

## 7. Self-check

Fix before showing if:

- identity is a standalone `<Picture>` instead of a `<Subject>`
- a distinguishing mark has no landmark + side
- a multi-view sheet, 4-panel board, or storyboard grid is the only
  identity/product still, or the prompt asks for a grid / split / product
  wall in frame
- the subject holds or points a camera/phone that is actually the viewpoint
- hands reach at the lens with no crop or finger count
- a physical beat is given slow-motion duration
- an event is named many times or banned instead of closed by scene state
- several equal-weight camera moves sit in one shot
