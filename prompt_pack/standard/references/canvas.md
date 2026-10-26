Source: ComfyUI `comfy_extras/nodes_minimax_h3.py` (`adapt_canvas`, Empty/I2VA/Ref2VA node defaults).

# Canvas

Generation canvas and reference sizing. Load when planning assets, or when the user asks resolution / aspect / ref size. Do not tell them H3 renders 4K. Local H3-Base is short-edge 768. 2K is hosted `H3-Regenerate-2K`, not this node.

## 1. Output

| | |
|---|---|
| Default landscape | `1344 × 768` |
| Portrait | `768 × 1344` |
| Short edge | `768` |
| Area cap | `768 × 1344` |
| Round | multiple of `32` |
| FPS | `24` |
| Length | frame count on the `17n + 5` grid (trained ~124–362) |

Pick aspect from the story, then those defaults. Other ratios still use short-edge 768 and the area cap, rounded to 32.

## 2. I2VA / FL2VA / L2VA stills

Match the canvas aspect. The node cover-crops a mismatched last/follower frame. Same pixel area as the generation when possible.

## 3. Ref2VA images

Node `ref_image_size`:

| | |
|---|---|
| `match` (default) | Scale down only, keep aspect, to the generation pixel area |
| `max` | Short edge up to `2048` (never upscale). Better identity; several times slower because ref tokens ride every step |

Down only. A 4K still is not a 4K video. Identity-critical faces: `max`. Background/style refs: `match` is enough.

Sockets on `MiniMaxH3ReferenceToVideo`, from that node's templates: ≤9 images, ≤3 videos, ≤3 paired video soundtracks, ≤3 standalone audios. There is no combined 12-file cap. That older note refused wirings the node accepts, including a video plus its soundtrack plus standalone audio. Label mapping stays in `ref-en.md`.

Ref videos: 24 fps. The node truncates a reference video to the target frame count, and raises below 5 frames. About 2–15 s is the useful range to attach.

## 4. Length grid

Frame count is `17n + 5`. Off-grid values snap **up** silently (`6.00` s = 144 frames → 158 / `6.58` s). Write the timeline for the **snapped** length, or leftover unprompted frames are the tail collapse.

Unspecified Write default is `6.58` (158). Combat unspecified is `10.13` (243). User value still wins if it is 4–15 s — snap it to this table before writing cut times.

Trained range (~124–362):

| Frames | Seconds |
|---|---|
| 124 | 5.17 |
| 141 | 5.88 |
| 158 | 6.58 |
| 175 | 7.29 |
| 192 | 8.00 |
| 209 | 8.71 |
| 226 | 9.42 |
| 243 | 10.13 |
| 260 | 10.83 |
| 277 | 11.54 |
| 294 | 12.25 |
| 311 | 12.96 |
| 328 | 13.67 |
| 345 | 14.38 |
| 362 | 15.08 |

H3 often degrades 1.2–1.7 s before the end (production, 9:16 Ref2VA; same source as `performance.md`). Budget ~1.3–1.5 s of holdable end state on official clips. Inspect the last second after they render.

Chain `frames_per_shot` table and ~2 s settle stay in `multishot.md`.

## 5. Portrait: whole vs large

A roughly square subject fully inside `768 × 1344` tops out around 50–60% of frame height (width fills first). Whole-subject and large are mutually exclusive. Crop the base off to go larger (~70%). Prompt crop phrasing is `performance.md` when that overlay is on.
