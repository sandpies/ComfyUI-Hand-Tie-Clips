# Story, cast and plates

## Story

- **A storyline beats a dance video.** A video of mostly choreography and little singing to the
  camera reads as "not quite a music video". Every sung hop leads with the singing.
- One line of story, then **one place per section**: e.g. hotel exit → limo → night market → club →
  rooftop at dawn; or casino → corridor → security room → vault → getaway car → rooftop.
- Use the lyrics: an action in a verse ("late night market, grab chips") becomes that hop's action.
- Spectacle wides open a restart or close the film (rule 8 in SKILL.md).
- Pitch 3-5 concepts when the user is undecided: song idea + video idea + why it suits H3 (faces
  and lip sync are its strength; crowds, choreography and 3+ people in frame are harder). Give a
  recommendation.

## Cast

Per character, decide and write down:
- **Ref:** a character sheet (several views of one person on a plain backdrop) or a full-body
  photo. One ref per character, whole. A sheet whose panels sit in a busy scene bleeds that scene
  into every hop; suggest a plain-backdrop version.
- **Check one-sided details in every view of a sheet.** Image models put a single earring on
  both ears or flip a scar between panels, and a sheet that contradicts itself teaches the video
  both. In a front view the character's left is on the right of the picture; in a side view, work
  out which side faces the camera from something fixed (the shoulder the bag hangs on). Send the
  sheet back with the exact fix ("remove the earring from the ear in the side view") before using
  it. Plain designs with nothing one-sided avoid the problem.
- **Sings:** which sections. Masked/faceless characters: none.
- **Job:** what they do when not singing (and in instrumental hops).
- `ref_plan.subjects`: `name` (a short description, not a real name: "the woman in the red leather
  jacket"), `locked` (face/hair traits that must not change), `context` (wardrobe and appearance as
  prose, never a pose or a place; it is sent on every hop).
- **Never dress two characters alike.** Two women in the same white top and grey pleated skirt,
  side by side in a wide shot, came out as two copies of the same woman (one took the other's
  hair). Give every character a different outfit and colour before the sheets are made; the
  hair alone does not keep them apart.
- **Name each person's ethnicity and age in `locked` and `context`** ("a young East Asian woman,
  ..."), and the same for a person who appears only in a photo or a prop picture. Left out, the
  model fills them in by its own guess and can drift away from the sheet.

The camera can be "you", the viewer: the singer performs to the lens and the camera has no body.

## Plates

A plate is a picture of a place (no people) that rides the hops set in that place. They are
optional: a beat can name a place in words alone. They give the look control.

The same goes for a **key prop**: an object the story turns on, seen in several hops or close
inserts, gets its own picture (one object, plain neutral background, even light, no hands, no
text), its own tag and a row on every hop it is in (camera.md, Props). Hand its prompt off with
the plates.

A prop that changes state on screen (opens, unfolds, lights up, breaks) needs a **prop sheet**,
not one picture: one generation laid out like a character sheet, the object in each state the
story shows (closed front, closed side or back, open showing exactly what is inside), plus any
part a hand works (a clasp, a hinge, a switch), on a plain neutral background. A picture of only
the closed state leaves the open state to the model, and it invents it differently every time.

### Which places get a plate

- **Yes:** every place a restart (or hop 1) opens in, when the look matters: a set the film
  returns to, a signature location (vault, rooftop, stage), anything the words alone render
  generically.
- **No:** a continuation in the same place (it carries the picture over); a place seen for one
  passing moment; a close prop (a dial, a phone screen) unless the beat frames people around it;
  a moving view the plate cannot match (a car at speed: describe it in words instead).
- When unsure, fewer plates. A wrong-angle plate does more harm than none (rule 2).

### Write the camera first, then the plate

For each place, decide the shot's camera **first** (position, facing, framing, who must be seen).
Then write the plate prompt **from that exact viewpoint**, so the plate and the beat agree:

- Faces must be visible → the plate looks at the empty spots where the people will be.
  Car interior for a band in the front seats: "view from the windscreen looking back at the empty
  driver and passenger seats, rear window behind them", not "view from the back seat looking
  forward".
  Car interiors are hard for most image models, and one car matching across several plates is
  harder. If the interior plates fail, drop them: keep every shot inside the car medium or close
  (faces, hands on the wheel, a prop on the mirror), name the interior in words in each shot, and
  give plates only to the outside (the car at the kerb, the car on the road).
  A plate that shows a vehicle draws that vehicle, whatever the words say: a 1950s sedan in one
  plate and a 1970s muscle car in another came out as two different cars. Use plates that show
  the same model, or a plate with no car in it (the empty road) and the car in words.
- A walking shot toward the camera → the plate looks down the corridor/street the way they walk.
- A close prop plate (a dial, a screen) works only if the beat puts people around it.
- **Image models have a favourite view of a room and keep returning to it.** A second angle of
  the same small room (a booth from the side after a booth from the front) came back as the
  same picture through twenty tries, with the viewpoint written as a position and as a POV.
  Plan a small room around at most two plates, the view and its reverse (the reverse has
  something the first cannot show: a door, a counter). Cover a third angle with framing
  instead: over one person's shoulder from an existing plate, or a close shot that needs no
  plate. Assume single text-to-image generations: most users have no image-edit model, so never
  plan a shot that only works if a plate is edited into another angle.

### Plate prompt template

> `<place>, <time of day / light>, <3-5 concrete details>, <where the empty space is for the
> people>, <camera position and facing>, <the film's grade>, no people, <aspect>.`

- **No people in plates.** A person in a plate becomes an extra character.
- Leave floor or seat space where the cast will be.
- One consistent grade across all plates (e.g. "night, teal and amber").
- Same aspect as the film.
- **Every prompt stands alone.** The image model has no memory of other plates, so never write
  "the same room" or "same platform, reverse angle". When two plates show one place, repeat every
  feature that must match (materials, colours, lights, props, weather, time of day) in both
  prompts. Expect two generations of one place to differ anyway; plan few plates per place, and
  let close shots carry the rest.

Before handing the prompts over, check each against its beat's camera line (rule 2).

### What to hand the user

One table, one row per plate, so they can generate in one sitting:
(then each prompt again as one paragraph in its own code block, style line already appended, so it
pastes straight into the image model; never as a `>` quote, which copies with the markers)

| File | Tag | Hops | Beat camera | Prompt |
|---|---|---|---|---|
| `rooftop.jpg` | `@rooftop` | 10 | low, in front, facing the ledge, all three faces | Rooftop of a ... , camera at chest height facing the ledge ..., no people, 16:9. |

Plus one line on how to make them (below), and ask them to send the images back before you write
the plans: the beats get written against what the plates actually show.

### Making the plates

Any text-to-image model works: whatever the user already runs (a ComfyUI image workflow, a local
model, a hosted generator). Photos work too, if they were taken from the beat's camera position.
Tell the user:

- **Size:** the film's aspect at roughly 1-2 MP (1920x1080 or 1344x768 for 16:9; 1080x1920 or
  768x1344 for 9:16). Landscape plates in a portrait film get cropped.
- **One model, one style line** for every plate, appended to each prompt (e.g. "cinematic still,
  night, teal and amber grade, 35mm"), so the places match each other and the `prompt_prefix`.
- **Reroll, don't settle:** generate a few per prompt; pick the one whose angle matches the beat.
- **Reject** any plate with people, faces, mannequins, posters of people, legible text or
  watermarks (they all come back as things in the video). Image models often slip a figure into
  "empty" scenes; add "empty, deserted" and look closely at the edges.
- **Fixing an almost-right plate:** reroll. A stray background figure that will not go away can
  stay if the beats name it as a still extra ("one old customer sitting still far back"). If the
  user happens to have an edit or inpaint model, it can remove a stray person or sign; never
  require one.
- For anime or stylised films, make the plates in the same style as the character sheets.
  Name the medium in every plate prompt ("flat 2D anime background art, clean line art,
  cel-shaded flat colour"), add "3D render, CGI, photorealistic" to the negative prompt when the
  image model has one, and reject a plate that looks rendered. Put the same medium words in the
  graph's `establish` and `prompt_prefix`, or the video drifts toward 3D.

### Checking returned plates

Look at each image before writing the plans, and report per plate:
- Does the viewpoint match the beat's camera (position, facing, where the faces will be)? If not:
  a new plate, or change the beat's camera to match the plate, or drop the plate from that hop.
- Is there empty space where the people stand or sit?
- Any people, text or logos? Does the grade match the others?
Then write the beats to what the plate shows (the counter on the left, the window behind).

### Plate filenames and tags

Copy plates into `input/h3_refs/` with plain names. The tag is the plate's short name; no tag may
be the start of another (`@vault` and `@vault_dial` collide: use `@vault` and `@dial`).
