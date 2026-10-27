# Directing: see the scene, predict the model

Every rule in this skill is a failed render explained by one of six facts about how the video
model reads a beat. Know the facts and you can see a failure coming in a case no rule covers.

## How the model reads a beat

**1. Every word adds; nothing subtracts.** "Stops talking" keeps the talking. "Her eyes follow him
as he walks off" puts him back in her shot. "Holds the phone to her ear" makes a call, with a
voice. *So:* never name what should not be seen or heard; name what is there instead (the closed
mouth, the empty corner, the receiver in its cradle).

**2. Every picture on a hop pulls.** A plate pulls its view in behind every shot, whichever way the
words turn the camera. A sheet pulls its person into the frame, and with no body of theirs in the
shot it lands on the nearest similar person. Look-alikes merge or swap features. *So:* the plate is
the camera; a view no plate shows is close with its background named, or gets a plate. A sheet
rides only the hops where its person is visible. Nobody dressed alike.

**3. Every gap is filled with the most likely thing.** A face with no mouth state talks. A quiet
stretch in a busy place fills with crowd voices in the language the faces and signs suggest. A
prop with no picture is redesigned each time. A move with no direction goes toward the lens.
**Empty time is a gap too:** every invented speech so far came in a window where a face had
nothing to do; the same people moving with sounds of their own stayed quiet. *So:* fill every gap
yourself, and fill time with action that makes its own sound.

**4. There is only screen space.** The model knows left and right of the frame, near and far,
toward and away from the lens, nothing else. It cannot work out that a clock "above the lockers"
is behind her head, or that "towards the ship" means "away from the camera" when the ship is at
the far end of the plate. *So:* you hold the map; every shot translates it into screen words.

**5. Each hop forgets.** A restart knows only its own words and pictures; a `motion_context`
continuation also knows the last frames before it; a `hand_tie` hop knows its previs windows.
A seat, prop, pair of glasses or scar not in this hop's words or pictures is lost or reinvented.
*So:* restate positions, props and looks in every hop.

**6. Time in a hop is loose and runs ahead.** Cuts land within about half a second, sounds early;
an action that needs room makes room; anything set going keeps going until something stops it.
*So:* give actions their real seconds and an end mark, write sounds on the cut, schedule no
tighter than half a second.

## Predict the frame

After the shot notes (SKILL.md, the method), run each shot the way the model will:

- What does it name that should not appear (1)?
- Which pictures ride this hop, and what does each pull into this frame (2)?
- What gaps are left: a silent face, a silent stretch, an undesigned prop, an unnamed background,
  a move with no direction (3)?
- Does every left, right, toward and away agree with the map (4)?
- What does this hop need that only an earlier hop had (5)?
- Does anything start without an end, or need room it hasn't got (6)?

Write down the frame you predict. If it is not the frame you want, change the beat, the map or the
plate, and run it again.

**Worked, a run to a goal.** Map: the pier plate is seen from the land end, the ship at the far
end. Draft: "@a running toward the camera down the pier, the terminal behind her". The plate pulls
its view in behind her (2), so the ship is at her back and she runs away from it (4). Fix from the
map: "@a runs away from the camera down the pier toward the ship far ahead, her back to the
camera". For her face, a plate from the far end, or a close with the background named.

**Worked, a watcher.** Draft: "B's eyes follow A, who walks off the frame to the left". A is named
(1) and A's sheet rides the hop (2), so A is drawn beside her; two people with nothing to say talk
(3). Fix: "B alone in the frame, far down the street, her eyes on the corner where the woman has
just disappeared; nobody else is in the frame", and a sound for the silence.

## Keep the world alive

Control the mouths, never the bodies. A person with lips pressed shut can still shift weight,
turn a glass, glance at the door. Freezing everyone but the speaker is the most common way a
careful beat goes dead. Every shot carries layers:

1. **The main action** (the line, the reveal, the strike).
2. **Everyone else's business,** small, in character, clear of any contact.
3. **The place breathing:** smoke, rain on the glass, extras far behind, a curtain moving.
4. **The camera breathing:** a slow drift or a few degrees of arc. A true hold is for one moment.

A busy frame is also how a face stays quiet: business with its own sound (a chair creaks, ice
clinks) gives the soundtrack something to be instead of speech.

- **Every face plays the moment, differently:** one smug, one wary, one amused. Faces live in
  small moves (a blink, a glance down and back, a jaw tightening, a swallow). Write blinks where a
  face holds the screen; the model rarely blinks on its own. Not yet proven.
- **Write the frame as an ensemble.** A window that names one person plays while the rest wait.
  Each window says what everyone in it does at once, plus the place (lint `solo-window`): "At
  00:03-00:06, all at once: @a swirls his glass and smiles, @b trails a nail down the back of his
  chair, @c grips the other side and gives one slow nod; the city lights pulse behind them."
- **The connectives bind:** **and / while / as / ;** mean at the same time, **then** means after.
  One sentence of simultaneous clauses per window; a run of one-person sentences plays one at a
  time.
- Stillness is a beat ("for one breath nobody moves"), not a state. Ration contact and crossing
  paths in a tight frame; everything else can run at once.

## The cut-by-cut pass (before hand-over)

Read every hop cut by cut and write one line per cut: where each person is and which side they
face, where each prop is and in whose hand, what this camera can actually see against the plate.
Read each next cut against that line:

- A prop changes place or hands only on screen, never across a cut. It rests where the camera sees
  it. Once it is gone, frame away from its spot ("the empty seat" brings the prop back).
- Someone who left stays out; they keep the side they left by into the next shot and hop.
- Backgrounds follow the facing: behind a face is what lies opposite where they look.
- Every movement gets its real seconds; several people moving through one short window is where
  extra copies of people appear.
- A small or distant figure gets almost nothing from its sheet: name its clothes and colours in
  that shot. A tag that names a thing (ghost, wolf) pulls that thing in at small sizes.

## The scene map

`scene_map.json` sits beside the plans; the checker and you read it, the node never does.

```json
{
 "places": {
  "pier": {"view": "from the land end looking down the pier", "far": "the ship",
           "near": "the terminal, behind the camera", "left": "lamp posts", "right": "lamp posts"}
 },
 "scenes": [
  {"hops": [4, 5], "place": "pier", "goal": "far", "goal_is": "the ship at the far end"},
  {"hops": [7, 8], "place": "deck", "cast": ["a", "b"],
   "sides": {"deck": {"left": ["a"], "right": ["b"]}}}
 ],
 "props": {
  "box": {"picture": "box", "hops": [1, 2, 5], "holder": {"1": "a", "2": "a", "5": "b"}}
 }
}
```

- `goal`: where a journey's destination lies in the plate's view, `far` or `near`; the checker
  flags a run the wrong way.
- `sides`: per plate tag, who is on the left and right (base tags). A reverse view is its own
  entry with the sides swapped.
- `cast`: everyone physically in the scene. Each needs a row on every continuation hop of it, or
  their features land on the nearest look-alike; a restart needs only who it shows.
- `props`: every prop in more than one hop, with its picture tag and holder per hop.

Show the user one layout line per scene before the beats; it catches a wrong side cheaply.

## When the facts point past the rules

For a new case (a mirror, a crowd, a screen inside the screen), run it through the six facts and
write the prediction down before the render. If the render does something the facts did not
predict, find the word or picture that caused it and add it to [status](status.md) as unproven.
