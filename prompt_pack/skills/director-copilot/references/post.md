# Post: kinetic text and fx in the edit

The post pass runs after the render is accepted (stage 13). Everything here goes on top of the
rendered film: it is exact, it can be redone one range at a time, and it never costs a render.
`scripts/post.py` does all of it. Dips and the warning card come last (`transitions.py`, [camera](camera.md#transitions)).

## Order of work

1. **Measure.** `post.py measure film.mp4` gives the shot cuts (scene detect at 24 fps), the
   kicks and a `.measure.json`. If another render of the same song already has timed words, add
   `--ref other.mp4` to get the offset between the two soundtracks. Measure against the raw
   renders: a finished copy with fades and dips matches worse and lands a frame off.
2. **Looks on real frames.** Burn four to six text looks onto stills from the film (sticker,
   ring, glitch, editorial and so on) and show them side by side. The user picks a mix, and each
   style in it gets a job.
3. **FX samples.** Make a short clip of each candidate fx on the shot it would live on. The user
   keeps or drops each one, and only kept fx go on the cue sheet.
4. **Cue sheet.** Write `plan.json` (below), run `post.py cues plan.json` and read the drop log.
   Draw it as a timeline for the board: song sections, shots by world, text hits, fx windows, and
   the fx already in the render.
5. **Sample burn**, about the first minute, at full quality. Show it, fix it, then burn the
   whole film. Redo a single stretch by burning only that range.

## Text

- **Hero words, not subtitles.** Use a few words per lyric moment, timed to word stamps. Words
  already timed by hand for one render of a song carry to another render through the measured
  offset.
- **Each style has a job.**
  - **Orbit** carries the hook words. It is a ring of letters circling the singer at neck height
    while the back half passes behind her through a matte. It follows her face with smoothing,
    keeps the letters upright (tilt clamped), and snaps onto the next shot when a cut falls
    within 0.35 s of the hit. At face height the ring crosses her face.
  - **Glitch** is for edgy single words, and only in dark or neon worlds. On bright sets it
    turns into a sticker.
  - **Sticker (telop)** carries the rest: bold rounded type, a thick outline, and a stamp-in
    on the hit.
  - **Counter** is an alternative to Orbit when the video has a number that climbs or counts down
    (floors, laps, a clock). It is a small dark LED panel in one corner whose readout ticks over on
    given times (two dim frames, then lit), with a short stamped flash under it on the hook beats.
    It hides during blocking fx and baked windows. Plan key `counter`:
    `{"floors": [[0, "1F"], [12.96, "2F"]], "flash": [49.2], "flash_text": "うえ!", "corner": "tl"}`,
    in film time (the plan `offset` is not applied). Tick it over on the measured cuts, not the plan's
    hop times, or it changes a shot early. Used on Ue e in place of Orbit (user's pick).
- **Never over the star.** Each word is placed by scoring every slot over its whole hold (three
  frames: in, middle, out). People count after a generous dilation and faces count three times;
  busy detail only breaks ties. If no slot is clear, the word shrinks in two steps, and if it is
  still crowded it is dropped. A dropped word beats a covered face. Words on screen at the same
  time block each other's boxes.
- **Spacing.** Keep 1.3 s or more between words. Hooks have right of way: move an fx off the
  hook bar rather than lose the hook.
- **Quiet zones.** No text during a freeze card, kaleidoscope, colour isolation or shake, or over
  an effect the render already has. Watch the film and list those as `baked` windows.
- **Vertical Japanese.** Stack the characters with `\N`. A vertical font flag renders the
  characters sideways in libass.
- **Name card.** Put it on the lead's first clean close-up, big, over the clothing edge rather
  than the face, with a small subtitle line under it.

## FX: one window each, placed by hand

| FX | Where it belongs | How |
|---|---|---|
| Freeze name card | the lead's first clean close-up | the picture holds about 1 s while the song runs on: one white frame, colour up, card stamps in |
| Punch zoom | dance or formation wides, two or three bars after a hook | about 6% scale pop on each kick, decaying fast |
| Bass shake | bar 2 of a chorus | short decaying jitter; the drop itself belongs to the hook text |
| RGB split | neon or street walking sections, with the glitch words | channels pulled apart for about 2 frames on each kick |
| Colour isolation | one bar on a busy colourful set | world greyed. Keep the subject from a tight matte (eroded a little), plus her signature colour from the loose person matte. The loose matte alone leaves a halo of the set's colour round her |
| Kaleidoscope | an opener on a shot with no face | zoom in enough that no corner goes black; unfold by about 2 s. Mirrored faces read as creepy |
| Light trails | a slow bridge | bright pixels linger; ease in over 1 s, out over 1.5 s, and stop before an after-image the render already has |
| Light leak | the last 3-4 s | warm flare drifting across, then fade to black |

- Run one fx at a time. Text and fx share a frame only by design (RGB split with glitch words).
- Kicks for zooms, splits and shakes come from the rises of the sound under 120 Hz, measured over
  the whole song so a sample burn hits the same kicks as the full burn.
- Tried and dropped: a short speed ramp read as dropped frames on a 24 fps source, so use one
  only when it is long and gradual and the moment calls for it. A breathing letterbox was not
  readable and meant nothing.

## The tool

```
python post.py measure film.mp4 [--ref other_render.mp4]
python post.py cues plan.json
python post.py burn cues.json START END [--yunet face_model.onnx]
```

`plan.json` (paths relative to it; `cuts` from the measure file, or left out to measure again):

```json
{"video": "film.mp4", "bpm": 136, "offset": -0.29, "fonts": "fonts",
 "cuts": [4.0, 6.375], "worlds": ["carousel", "glam", "street"],
 "words": [[16.7, "WHO'S THAT?"], [56.3, "WATCH ME MOVE"]],
 "orbit": ["WATCH ME MOVE"], "glitch": ["SWITCH"], "glitch_worlds": ["street", "void"],
 "baked": [[37.5, 39.9, "katakana rain"]],
 "fx": [[0, 2.0, "kaleidoscope"], [9.2, 10.3, "freeze card", {"card": "NAME", "sub": "role"}],
        [66.2, 68.0, "colour isolation", {"keep_hue": [[0, 8], [165, 180]]}],
        [184.4, 187.9, "light leak"]],
 "ring": " WATCH ME MOVE ・ ", "glow": {"street": "&HFF50E0&"},
 "font_names": {"telop": "Mochiy Pop One"}}
```

- `words` times are in the source render's clock; `offset` moves them onto this film. One world
  name per shot. `glow` colours (ASS `&HBBGGRR&`) tint the ring per world.
- The font files go in the `fonts` folder. A word that burns blank means a font is missing, and
  the tool warns.
- Requirements: ffmpeg with libass, numpy and opencv. rembg (people mattes) and a YuNet face
  model are optional; without them placement uses detail only, the ring is not tucked, and
  colour isolation is skipped, and the tool says which. Use the ComfyUI venv python when rembg
  lives there.
- Cost: CPU only. Frames that need a matte (orbit and isolation) run at about ten times real time
  at 48 fps, and everything else is fast; a 3 min film with eight such moments took about half an
  hour. Burn the sample range first.
