# Field craft

Official T2VA / I2VA / FL2VA / L2VA / Ref2VA writes. Load with the mode guide on every official Write. Off when `multishot.md` is on: a timestamp inside a chain block fights the join.

Shot headers, camera verbs, `<d>`, and retention markers stay in `base-en.md` / `ref-en.md`. This file owns motion clocks, action mechanics, anchor paths, and mix. Field-tested on local H3: millisecond clocks inside a shot keep micromovements distinct. A `[Shot N]` is still only a camera cut.

No header tag.

## 1. Motion clocks

`[Shot 1]` has no timestamp. A later shot is `[Shot N] At MM:SS.mmm,` plus a cut phrase from `base-en.md`. That time is the edit.

Inside the current shot, clock every visible state change with a contiguous range on its own sentence:

```text
At MM:SS.mmm-MM:SS.mmm,
```

Three decimals. The first range of the clip starts at `00:00.000`. The last range ends at the exact duration. Ranges touch: no gap, no overlap. A cut time is a range boundary. The new shot's first range starts at that same time.

One primary change per range: a limb arrival, a contact, a weight shift, a cloth or hair reaction, a camera move that changes the frame, a spoken line, or a music hit. A finger or wrist change can be a few hundred milliseconds. A crossing or a hold can be longer. Do not pad ranges to one second. Do not slice the clip into equal blocks because there are N pictures.

Every range keeps something moving: body, object, cloth, hair, effect, camera, or environment. On a hold, write the continuing motion (breath, cloth, light, a settling hand).

A range is not a shot. Distance or angle changes inside the shot are camera sentences.

If the confirmed storyboard names a row in `references/coverage-menu.md`, open that file and copy its Paste cell into the camera sentence. Do not rephrase the move. A plain official verb stays in `base-en.md` and does not open that file.

The last range of an FL2VA or L2VA clip is the arrival on the end anchor. The ranges before it produce that arrival.

When `performance.md` is on, the spoken line fills its speaking shot. Clock body motion during the line inside that shot. A swallow or "finishes speaking" is the next shot. Clocks do not raise the expression-beat ceiling in that file.

Shape only — do not reuse the scene:

```text
[Shot 1] Live-action, cinematic, a medium shot holds both men in the temple doorway.
At 00:00.000-00:00.380, his rear heel rolls inward and the rear knee bends.
At 00:00.380-00:00.920, the hip turns and the lead hand travels from the ribs to the other man's cheek.
At 00:00.920-00:01.450, the knuckles meet the cheek, the head turns with the hit, and the coat hem swings past the hip.
[Shot 2] At 00:01.450, the camera cuts to a close view of the struck man.
At 00:01.450-00:02.100, his lead foot slides back across the stone and his guard rises to the cheek.
```

## 2. Action grammar

For every interaction name the actor, the moving body part or object, the path, the target or contact, the immediate result, and the subsequent response.

Write those six facts in place of: engage, interact, react, battle, dynamic movement, dramatic action, aggressive movement, powerful movement.

Write onset, intermediate state, and completion. A pose, composition, transformation, or last frame needs that path in the ranges before it.

If a later anchor is mirrored or reverses screen space, name each reversal first: subject screen sides, facing, handedness, asymmetric marks, prop placement, background geometry, light direction, camera. Then write the move that produces each one.

A requested medium wins over the source image's medium. Describe the target with concrete visual properties.

Add a detail only when motion, continuity, framing, or sound is ambiguous without it.

## 3. Anchors

Unchanged fine detail stays on the keyframe or reference. In prose, state only the traits needed for identity, disambiguation, or a real change. Spend the remaining words on paths, timing, contact, and sound.

Compare anchors before writing. Crop, focus, occlusion, blur, and light are not transformations. Partial visibility of an intact defined look stays `fully_preserved` (`clarifications.md`).

A picture is not its own shot, its own equal time slice, or an automatic endpoint. Several pictures may be one subject through one action. Keep their order. Place each intermediate constraint where the action puts it.

Cite a label inside the sentence where it acts. Do not append a detached label list.

## 4. Continuity

Across a cut, carry screen direction, eyelines, possession, contact, momentum, cloth, light, and ongoing audio. State an intentional break.

Keep balance, joint articulation, foot placement, grip, inertia, collision, recoil, follow-through, and settling. Hair, loose cloth, fur, liquid, smoke, dust, debris, vegetation, reflections, and shadows answer the force.

Scale the number of ranges to the duration. A short clip does not hold a long chain. A long clip does not go empty after the main action. The principal motion runs to the endpoint and not past it.

## 5. Foreground

One foreground per range: a line, a lyric phrase, a physical change, or a music hit. Duck the score under speech. Place a loud impact in the range before or after the line. Animal and creature noise stays in the shot sentence and `overall_soundscape`, never inside `<d>`. Give `(S1)` only to a real vocal event. A silent person, an animal, a crowd whose roar stays unlabelled, and a sound-making object get no speaker ID. Do not invent a score because an instrument is visible. A line, a loud score, dense effects, and a heavy action do not share one range.

## 6. Additive paste

H3 is CFG-distilled. CFG is 1. There is no negative branch, so every word in the six fields is something to render. Name the state that is there.

The paste itself contains none of these words: no, not, don't, never, without, avoid, isn't, aren't. `N/A` stays only as the official empty value of `overall_soundscape` or `non_diegetic_music`. A sentence such as "No intelligible words" is a line of dialogue the model will try to honor.

Same rule as `multishot.md`. This file is the one official writes load.

## 7. Self-check

Fix before showing if:

- the paste contains no, not, don't, never, without, avoid, isn't, or aren't
- a motion range is written as `[Shot N]`
- the `[Shot 1]` header carries a timestamp
- ranges gap, overlap, or stop short of the duration
- a range only captions a still
- a banned summary verb replaces the six action facts
- an endpoint or a reversed anchor has no path
- pictures are cut one-per-image or sliced into equal time blocks
- a detached label list is appended
- a line, a loud score, dense effects, and a heavy action share one range
- creature noise, or a silent subject, gets `(Sx)` or `<d>`
- `performance.md` is on and a post-speech beat shares the speaking shot
- `multishot.md` is on and any timestamp appears
