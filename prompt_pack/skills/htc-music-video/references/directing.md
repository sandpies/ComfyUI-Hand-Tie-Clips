# Directing: see the scene, predict the model

The rules in this skill are consequences. Each one is a failed render explained by one of six
facts about how the video model reads a beat. A director who knows the six facts can see a
failure coming in a case no rule covers, and can build a scene that makes sense instead of
assembling sentences that pass a checklist. Read this page before writing any beats, and come
back to it whenever a case is new.

## Part 1. How the model reads a beat

**1. Every word adds; nothing subtracts.** The model draws what the beat names, including
things named in order to say they are absent, gone or ending. "Stops talking" keeps the
talking. "Her eyes follow him as he walks off" puts him back in her shot. "Holds the phone to
her ear" makes a phone call, with a voice. A fiddly task given to a small figure in the
background gets its own unwritten close-up so the model can show it. *So:* never name what
should not be seen or heard. Name what is there instead: the closed mouth, the empty corner,
the receiver lying in its cradle.

**2. Every picture on a hop pulls.** A place picture pulls its own view in behind every shot of
the hop, whichever way the words turn the camera. A character sheet pulls its person into the
frame, and with no body of its own in the shot it lands on the nearest similar person. Two
people who look alike (the same clothes, the same haircut) merge into one, or swap features.
*So:* the plate is the camera. A view no plate shows is either a close shot with its background
named, or it gets its own plate. A sheet rides only the hops where its person is visible. No two
characters are dressed alike.

**3. Every gap is filled with the most likely thing.** A face with no mouth state talks. A quiet
stretch in a busy place fills with crowd voices, in the language the faces and signs suggest. A
prop with no picture gets a new design in every appearance. A reverse angle with no background
gets the plate. A move with no direction goes the easiest way, often toward the lens. Silence
is not a thing the model can draw, and **empty time is a gap too**: a few seconds where a face
is on screen with nothing to do is filled with talk. Every case of invented speech so far came
in an empty window (a nod alone, "presses his lips shut and waits", two people standing
together with no business); the same people moving with sound of their own (footsteps, a glass
set down) stayed quiet. *So:* fill every gap yourself, and fill time with action that makes
its own sound: a mouth state on every silent
face, a sound or score for every silent stretch, a picture for anything that comes back, a
background behind every face, a direction and an end for every move.

**4. There is only screen space.** The model has no map of the room. It knows the left and right
of the frame, near and far, toward and away from the lens, and nothing else. It cannot work out
that a clock "above the lockers" is behind her head, that someone who leaves one view on the
right enters its reverse from the left, or that "towards the ship" means "away from the camera"
when the ship is at the far end of the plate. *So:* you hold the map of the place (the scene
map below), and every shot translates it into screen words.

**5. Each hop forgets.** A restart knows only its own words and pictures. A continuation knows
those plus the last frames of the hop before. A seat, a prop, a pair of glasses or a scar not in
this hop's words or pictures is lost or reinvented, and the face at the end of a hop is all the
next hop has to rebuild a person from. *So:* restate positions, props and looks in every hop;
follow every prop from hop to hop; end a hop that hands over on a clear face.

**6. Time in a hop is loose and runs ahead.** Cuts land within about half a second of the written
time; a sound written on a cut arrives a little early; an action that needs room makes room (a
person jumps back to start a sprint); anything set going keeps going until something stops it.
*So:* give actions room, give every move an end mark, write sounds on the cut, and don't
schedule tighter than half a second.

## Part 2. The method

1. **Understand the moment.** For each beat ask the director's questions
   ([camera](camera.md#three-questions-before-every-shot)): what changes here, who holds the power,
   what must the viewer discover. That decides hold, move or cut.
2. **Build the scene map before writing a beat.** The map is the world the film happens in,
   kept outside the model because the model has none (fact 4). For each place: what its plate
   shows far away, near (behind the camera), left and right. For each scene: who stands or sits
   where in each plate's view, which way each faces, where the goal of any journey lies. For
   each prop: which hops it is in, whether it has a picture, who holds it on each hop. For each
   person: an outfit unlike anyone else's. Write it as `scene_map.json` (format below).
3. **Place the camera in the map.** Every shot is a camera standing somewhere in the map. Prefer
   the views a plate shows. A view no plate shows is a close shot with its background named,
   or a new plate.
4. **Write the beat as what that camera sees.** The camera and its move first, then everyone in
   frame by screen side, facing, eyes and mouth, then the action with its end, then the sound.
   Derive every screen direction from the map: if B stands at A's right, then in a shot facing
   A, B is off the frame to the left.
5. **Run the shot in your head the way the model will.** Take the six facts one at a time:
   - What does the shot name that should not appear (1)?
   - Which pictures ride this hop, and what does each pull into this frame (2)?
   - What gaps are left: a silent face, a silent stretch, an undesigned prop, an unnamed
     background, a move with no direction (3)?
   - Does every left, right, toward and away agree with the map (4)?
   - What does this hop need that only an earlier hop had (5)?
   - Does anything start without an end, or need room it hasn't got (6)?

   Write down the frame you predict. If it is not the frame you want, change the beat, the map
   or the plate, and run it again.
6. **Check.** `check_plan.py shot.json ref.json --map scene_map.json`, then the read-through
   ([camera](camera.md#the-read-through-before-a-long-render)).

### Worked: a run to a goal

The map: the pier plate is seen from the land end, the ship moored at the far end. The goal is
the ship, so the goal is *far* in this view.

The first draft: "a medium shot of @a running toward the camera down the pier, the dark terminal
behind her". Run it as the model: the pier plate rides the hop and pulls its view in behind her
(fact 2), so the ship comes out at her back, and she seems to run away from the ship (fact 4:
the words say toward the camera, the plate says the goal is behind). Predicted frame: wrong.

The fix comes from the map: in this plate's view, running to the ship is running away from the
camera, so "@a runs away from the camera down the pier toward the ship far ahead, her back to
the camera". For a front view of her face, either a plate from the far end looking back at the
land, or a close shot with the background named and the plate kept off that hop.

### Worked: a watcher

The want: B watches A leave, alone in the frame. The first draft: "B's eyes follow A, who walks
off the frame to the left". Run it: A is named in B's shot (fact 1), and with A's sheet on the
hop, A is drawn beside her (fact 2). Two people close together with nothing to say then fill
the shot with talk (fact 3). The fix names only what is there: "B alone in the frame, far down
the street, her eyes on the corner where the woman has just disappeared; nobody else is in the
frame", and gives the silence a sound.

## Part 3. Keep the world alive

Control the mouths, never the bodies. The rules that keep faces quiet (a mouth state on every
silent face, a sound in every silent stretch) are about the mouth and the soundtrack only. A
person with their lips pressed shut can still shift their weight, turn a glass, tap a ring on
the table, breathe hard, glance at the door, pull a coat tighter. Freezing everyone but the
speaker turns a film into a slideshow, and it is the most common way a careful beat goes dead.

Every shot carries layers, the way a real scene does:

1. **The main action:** what the moment is about (the line, the reveal, the strike).
2. **Secondary actions:** everyone else in frame has business of their own that fits who they
   are and what they feel: the listener turns her glass, the guard shifts his weight, the twin
   traces the table edge with one nail. Keep it small, independent, and clear of the main
   action's body contact.
3. **The place breathing:** smoke drifting, rain on the glass, extras crossing far behind,
   lights flickering, a curtain moving.
4. **The camera breathing:** a slow drift, a creep in, an arc of a few degrees. A true hold is a
   choice for one moment (a stare, a reveal), not the default for every shot.

A busy frame is also how a face stays quiet. A mouth state stops the lips; the business around
it, with sounds of its own (a chair creaks, ice clinks, footsteps cross the floor), gives the
soundtrack something to be instead of speech. "Lips pressed shut" on a frozen body is the weakest
silence there is.

**Every face in frame plays the moment.** The people who are "not important" in a shot are where
AI film looks most fake: a fixed, blank stare while someone else acts. Give each face its own
reaction, true to who they are in that moment, and make them differ: one smug, one wary, one
amused. A face lives in small moves: a blink, a glance down and back, a brow lifting, a jaw
tightening, a swallow, a breath through the nose, a half smile that comes and goes. Write
them in the same window as the main action, joined by "while" and "as".

**Write the blinks.** The model almost never blinks on its own, which is a large part of the
dead stare. Ask for it where a face holds the screen for more than a couple of seconds: "she
blinks slowly once", "he blinks twice, fast, as the words land". Not yet proven.

**Write the frame as an ensemble, not a soloist.** A timed window that names one person ("At
00:03-00:06, @a nods") plays one action while the rest of the frame waits for its turn, even
when the others have "business" written somewhere else in the shot. In a frame with several
people and a whole place, each window says what *everyone* in it does at the same time, and
what the place does: "At 00:03-00:06, all at once: @a swirls his glass and smiles, @b trails a
nail down the back of his chair, @c grips the other side and gives one slow nod; the city lights
pulse behind them." The moment the scene is about is the strongest action in that window, not
the only one (lint `solo-window`).

**The connectives do the binding.** H3 weighs a few small words very strongly when one scene
holds several people:

- **and**, **while**, **as**, and the **semicolon** mean *at the same time*: "@a swirls his glass
  and smiles **while** @b trails a nail down the back of his chair, **as** @c grips its other
  side and nods; the city lights pulse through the window."
- **then** means *after*: "@c grips the chair, **then** nods once."

So build each window as one sentence of simultaneous clauses joined by these words, one clause
per person in frame plus one for the place, and use "then" only where the order matters. A run
of separate sentences, one person each, plays as one person at a time.

Stillness is a beat, not a state: "for one breath nobody moves" lands because everything around
it moves. What is rationed is contact (fact 6: fast contact warps bodies) and crossing paths in
a tight frame. Everything else can run at once.

Worked: "@a says the line. @b holds still, lips pressed shut." becomes "@a leans in and says the
line, tapping one ring on the glass. @b turns his whisky glass a slow quarter turn on the table,
lips pressed shut, eyes never leaving her; behind them a waiter crosses the far end of the room
with a tray, and the camera creeps in a few inches."

## The cut-by-cut pass (before hand-over)

Checks passing is not a plan that works: the checker reads words, not frames. Before a plan goes out, read every hop cut by cut and write one line per cut:

- where each person is, which side they face, and which side anyone left by;
- where each prop is, and in whose hand;
- what this camera, from where it stands, can actually see, checked against the plate.

Then read each next cut against that line. Fix anything that moves between cuts without being shown:
- A prop changes place or hands only on screen: an insert of the hand taking it, never across a cut.
- A prop rests where the camera sees it. A hand reaching over or behind something puts the prop there.
- Once a prop is gone, frame away from its spot. "The empty seat" draws the seat, and the prop comes back on it while its picture rides the hop.
- Someone who left the frame stays out of it: name them only as the eyes' target, and give their action to a sound.
- Someone keeps the side they left by, and the direction they travel, into the next shot and the next hop.
- Backgrounds follow the facing: what is behind a face is what lies opposite where they look.

- Every movement gets the time it really takes, or it is squeezed, skipped or doubled: a step about half a second, standing up or sitting down 2 s, opening a door and getting in 3 s, walking round a car 4-5 s. One travel movement per person per timed window; several people each moving through the frame at once in a short window is where extra copies of people appear. If the time is not there, cut the movement or give it its own shot.
A plan is handed over only when every cut reads clean against the line before it.

A small or distant figure gets almost nothing from its sheet: the words draw it. Name its clothes and their colours in that shot, and keep any one colour on the part it belongs to ("black hoodie, only the white mask pale"). The tag is read as a word too, so a tag that names a thing (ghost, angel, wolf) pulls that thing in at small sizes.

## The scene map

`scene_map.json` sits beside the plans. The node never reads it; the checker and you do.

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

- `goal`: where a journey's destination lies in the place's plate view: `far` (ahead of the
  camera's view) or `near` (behind the camera). The checker flags a run the wrong way.
- `sides`: for a plate's view (by its tag), who is on the left and the right of the frame. Use
  each person's base tag (`a`, not `quiet_a`). A reverse view is its own entry with the sides
  swapped.
- `cast`: everyone physically in the scene. Each of them needs a row on every continuation hop
  of the scene, even one where they are not the subject: a continuation remembers them from
  the hop before, and with no picture their features land on the nearest look-alike. A
  restart starts fresh, so it needs only the people it shows.
- `props`: every prop that appears in more than one hop. `picture` is its picture's tag (no
  picture is a lint), `holder` names who has it on each hop.

The map is also the first thing to show the user before the beats: a one-line layout per scene
lets them catch a wrong side or a prop with no route before a word is written.

## When the facts point past the rules

The rules are the cases already met. When a beat is new (a mirror, a crowd, a vehicle, a screen
inside the screen), run it through the six facts and write the prediction down before the
render. If the render shows something the facts did not predict, that is a seventh fact worth
finding: describe what happened, find the word or picture that caused it, and add the rule to
[status](status.md) as unproven.
