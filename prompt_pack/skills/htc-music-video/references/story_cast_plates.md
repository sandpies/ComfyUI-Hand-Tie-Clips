# Story, cast and plates

## Story

- **A storyline beats a dance video.** Mostly choreography reads as "not quite a music video";
  every sung hop leads with the singing.
- One line of story, then **one place per section** (hotel exit, limo, night market, club,
  rooftop at dawn). A one-take piece (`hand_tie`) is one place for the whole song: the story is in
  the performance, the small actions and the light.
- Use the lyrics: an action in a verse ("late night market, grab chips") becomes that hop's action.
- Spectacle wides open a restart or close the film.
- Undecided user: pitch 3-5 concepts (song idea + video idea + why it suits H3: faces and lip sync
  are its strength; crowds, choreography and 3+ people in frame are harder), with a recommendation.

## Cast

Per character, decide and write down:
- **Ref:** a character sheet (several views on a plain backdrop) or a full-body photo, one ref,
  whole. A sheet in a busy scene bleeds that scene into every hop; ask for a plain backdrop.
- **One-sided details agree in every view** (an earring, a scar). In a front view the character's
  left is on the picture's right. Send the sheet back with the exact fix before using it; plain
  symmetric designs avoid the problem.
- **Sings:** which sections (masked or faceless: none). **Job:** what they do when not singing.
- `ref_plan.subjects`: `name` (a short description, not a real name), `locked` (face and hair
  traits; ethnicity and age first: "a young East Asian woman, ..."), `context` (wardrobe as prose,
  never a pose or place; sent on every hop). The same for a person seen only in a photo.
- **Never dress two characters alike;** alike clothes merge two people into one. Fix outfits and
  colours before the sheets are made.

The camera can be "you": the singer performs to the lens and the camera has no body.

## Plates

A plate is a picture of a place (no people) that rides the hops set there. Optional, but it gives
the look control. A **key prop** (one the story turns on, seen in several hops or close inserts)
gets its own picture the same way: one object, plain neutral background, even light, no hands, no
text, its own tag. A prop that changes state needs a **prop sheet**: one generation showing each
state the story uses plus any part a hand works.

### Which places get a plate

- **Yes:** every place a restart (or hop 1) opens in when the look matters; a one-take piece's one
  place.
- **No:** a continuation in the same place; a passing moment; a close prop unless people are
  framed around it; a moving view the plate cannot match (a car at speed: words instead).
- When unsure, fewer. A wrong-angle plate does more harm than none (rule 2).

### Write the camera first, then the plate

Decide the shot's camera first (position, facing, framing, who must be seen), then write the plate
prompt from that exact viewpoint.

- Faces must be seen: the plate looks at the empty spots where the people will be ("view from the
  windscreen looking back at the empty front seats", not "from the back seat looking forward").
- Car interiors are hard for image models and one car across plates is harder. If they fail, keep
  inside shots medium or close, the interior in words, and plate only the outside. A plate showing
  a vehicle draws that vehicle: use one model throughout, or plate the empty road.
- A walk toward the camera: the plate looks down the way they walk.
- **Image models keep returning to their favourite view of a room.** Plan a small room on two
  plates at most (the view and its reverse); cover a third angle with framing. Assume single
  text-to-image generations: never plan on an image-edit model.

### Plate prompt template

> `<place>, <time of day / light>, <3-5 concrete details>, <where the empty space is for the
> people>, <camera position and facing>, <the film's grade>, no people, <aspect>.`

- No people (a person in a plate becomes an extra). Leave room where the cast will be.
- One grade and the film's aspect across all plates.
- **Every prompt stands alone:** never "the same room". Repeat every feature that must match in
  both prompts, and expect two generations of one place to differ anyway.

Check each prompt against its beat's camera line before handing it over (rule 2).

### What to hand the user

One table, one row per plate, then each prompt again as one paragraph in its own code block with
the style line appended (never as a `>` quote, which copies with the markers):

| File | Tag | Hops | Beat camera | Prompt |
|---|---|---|---|---|
| `rooftop.jpg` | `@rooftop` | 10 | low, in front, facing the ledge, all three faces | Rooftop of a ..., camera at chest height facing the ledge ..., no people, 16:9. |

Ask for the images back before writing the plans: the beats are written against what they show.

### Making the plates

Any text-to-image model works, or photos taken from the beat's camera position.

- **Size:** the film's aspect at roughly 1-2 MP (1920x1080 or 1344x768 for 16:9; 1080x1920 or
  768x1344 for 9:16).
- **One model, one style line** appended to every prompt, matching the `prompt_prefix`.
- **Reroll, don't settle;** pick the one whose angle matches the beat.
- **Reject** any plate with people, faces, posters of people, legible text or watermarks; add
  "empty, deserted" and check the edges. A stray figure that won't go can stay if the beats name it
  as a still extra.
- **Stylised films:** plates in the sheets' style, the medium named in every prompt ("flat 2D anime
  background art, clean line art, cel-shaded"), "3D render, CGI, photorealistic" in the negative
  prompt, and the same medium words in `establish` and `prompt_prefix`.

### Checking returned plates

Per plate: does the viewpoint match the beat's camera (if not: a new plate, a new camera line, or
drop it from that hop)? Is there empty space for the people? Any people, text or logos? Does the
grade match? Then write the beats to what the plate shows.

### Plate filenames and tags

Copy plates into `input/h3_refs/` with plain, free names. The tag is the plate's short name; no tag
may be the start of another (`@vault` and `@vault_dial` collide: use `@vault` and `@dial`).
