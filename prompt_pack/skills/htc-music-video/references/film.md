# Film: script, dialogue and sound

A film or scene has no song. H3 makes every voice and sound itself, so the script carries what
the song carries in a music video: the timing, the speech and the silence. Read this page with
[camera](camera.md) before writing a film's beats.

## 1. The script (producer's pass)

- **One-line story, then the turns.** A turn is anything that changes the situation: an arrival,
  an offer, a trick, a discovery, a betrayal, a payoff. List them in order.
- **Budget the turns against the running time.** Every turn needs at least one hop of its own,
  plus room for the reactions around it. About three or four turns per minute plays well; five
  in a minute plays rushed. Cut a turn or add hops rather than squeeze.
- **End on a tease.** Resolve the story, then open one small thread in the last shot (a phone
  that buzzes, a shadow across the table, a smile that fades) and hold it 2-3 s. Set the last
  hop's `tail` to `hold`.
- **Show it, don't explain it.** A repeated image (the same insert at the start and the end)
  tells a betrayal better than a line that explains it. Keep dialogue for what only a line can do.
- **A hop per place per moment.** Plan which hops are restarts (a new place or a time jump) and
  which are continuations (the same moment carrying on). Most film hops are restarts with cuts
  inside them.

### The viewer knows only what the screen shows

The audience has no plot notes, the same way the model has no map. A film whose story reads
only with the plot in hand fails at its cuts: a striking opening with no meaning, a jump to
another time with no reason, a scene that resolves into a new place with nothing linking them.

- **The opening asks the question.** The first hop shows who these people are to someone else
  and what they want, or something wrong that needs an answer. A character showcase (a walk, a
  pose, a reveal) with no want reads as an advert, and the next cut makes no sense against it.
  Show the want inside the showcase (the walker spots, in the crowd, the person she is after),
  or open on the trouble and bring the showcase later.
- **Every cut to a new place or time carries a link the viewer can see:** a look at something
  the next scene shows, a line that names where we are going, an object carried across, a
  person leaving toward it. By the first 2 s of the new scene the viewer can say why we are
  here now.
- **A flashback has a trigger and a way back.** Someone in the present looks at the thing,
  hears the name or says the line; the past opens on that same thing (a match cut, a whiteout)
  in its own look; it returns to the face that remembered. A past scene placed before the
  present it explains is a riddle, not a flashback.
- **Show the first step of every decision.** After a yes, a deal or a betrayal, show what it
  sets moving (a hand taking the card, the door opening, the crew getting up) before cutting
  away. A cut straight from a decision to an unrelated place leaves the viewer behind.

**The viewer pass.** Before writing beats, retell the film as the screen alone shows it, scene
by scene, as someone who knows nothing. Write the question a viewer has at each cut and where
on screen it gets answered. A cut with no answer gets a bridge (a line, an insert, an object
carried over) or a new order.

Hand the user the turn list with hop numbers and running time, plus the viewer pass, before
writing any beats.

## 2. Cast and voices

- Each speaking character gets a voice clip on their ref row (`"voice": "name_voice.mp3"`). A voice
  clip carries timbre only, not emotion, accent or pace; write those in the beat.
- Give each speaking character a **second, voiceless row** (same sheet, same `subject`, a different
  tag, no `voice`) and use that tag on the hops where he does not speak. A voice riding a hop
  where nobody says a word tends to turn into speech.
- **One-sided features flip between angles** (a streak of colour on one side, a scar, an eyepatch):
  name the side in the subject's `locked` text ("a white streak on her right side, over her right
  eye"). Not yet proven to hold; check it on the first render.
- A masked or faceless character never speaks. Give him actions and presence. On a hop where others
  speak, his shot still needs a mouth state ("his mouth hidden behind the mask, his jaw
  still") and a sound, and his moves start already done ("arms already folded"). Unsolved: on a hop with lines, a mask
  with a mouth shape (a skull's teeth) that moves in a close shot got lip-synced, even after a
  statement with a loud chord over his shot; the same figure moving on a hop with no lines did
  not. Do not solve it by freezing him or cutting his beat. A mask with no mouth shape on the
  sheet is the likely cure; test it. Never ask him a question or say a line
  to him that wants a reply: a question followed by his face got an answer in a voice, mask or
  not. Give his shot a loud sound of its own (a chord, a hit) instead of a pause.
- Graph settings for a film: no `master_audio_file`, `voice_every_hop` = `speaking`,
  `pin_mech` = `motion_context`, SLA `reference_protection` = Heavy Enforcement.

## 3. Writing a line

- **Delivery and face outside the quote, the line inside it:** `@a leans back and says in a low,
  amused voice, his eyes on @b, 'You play like a man with nothing to lose.'`
- **One delivery per line.** "low and amused" works; "excited, whispered and fast" fights itself.
- **About ten words, one sentence per quote.** Two short sentences are two quotes with an action
  between them. Single quotes, no ellipses, no dashes.
- **Plain English spelling inside quotes.** Accented or borrowed words ("café", "naïve", "jalapeño")
  get pronounced half one way, half another, and come out garbled. Write "cafe" or "coffee
  shop". Names that are hard to say go outside the quote, or get spelled the way they sound.
- **Describe behaviour, not feeling:** "lowers his gaze, jaw tight", never "he feels guilty".
- **Every line has a visible listener in a named direction.** The speaker's eyes go to that
  person ("his eyes on @b just left of the lens"), never into the lens. A line said to someone
  off screen, or to nobody, invites a reply or turns into a speech to the audience.
- **The first line goes to the freest face.** With several people in one frame the model gives
  the opening line to whoever is most central, facing the camera and not busy (eating,
  drinking). To choose the order, give each line its own shot with the speaker alone, and keep
  the first speaker's mouth free when the line starts.
- **The speaker stays in frame for the whole line.** A camera move or an exit comes after the
  line, never during it, or the line comes out of whoever is left on screen.
- **About 20-25 spoken words in a 12-15 s hop** at most. Leave a beat after each line for the
  face to settle.

## 4. Silence and sound

**Busy frames stay quiet; empty ones talk.** The model invents speech in empty time: a face on
screen with nothing to do. Give every silent person business with a sound of its own (a glass
turned on the table, a coat pulled tighter, footsteps), and keep every silent stretch full of
action and sound, not just a mouth state and a hum. Leading theory from every babble case so
far; not yet proven on purpose.

The model fills any stretch where a face is on screen and nothing is said with invented speech.

- **Every person on screen without a line has a mouth state:** "lips pressed shut", "jaw clenched,
  lips pressed shut". Write it before the first line, between lines and after the last one.
- **Name a sound for every silent stretch:** "the lamp humming", "rain drumming on the roof",
  "chips clicking". Silence is a sound, never an absence.
- **After a hop's last line, close the mouth and name the sound:** "He presses his lips shut and
  waits, the slot machines chiming far away." Making the last line longer does not stop a babble
  after it.
- **Phone calls end with the call ending:** "the call clicks off, and the only sound is the rain".
  Otherwise the other end gets a voice. A phone lifted to an ear with no line written gets talk
  too, even from someone small behind glass; give the call a line and an end, or keep the
  phone on the counter (she dials, the receiver still down).
- **The model may score a reveal on its own.** A cut to a knowing look after a discovery came
  with a single dramatic sting nobody wrote, and it landed. To get one on purpose, name it on
  the cut ("a single low dramatic sting as the camera cuts to his face"); it lands about half a
  second early, so write it on the cut, not after. To keep a reveal dry, name the room sound
  across the cut instead (not yet proven).
- **A hop with no lines in a busy place fills itself with crowd speech,** in the language the
  faces and signs suggest (a lantern market with an East Asian cast came out full of Mandarin
  chatter). Closed mouths do not stop voices from off screen. Give such hops a score that fills
  the whole hop ("a fast pounding drum score drives under the whole chase, rain hissing on the
  tarps") and keep the place empty of extras in the words and the plate. Not yet proven.
- **Narrowband sounds over broadband ones.** "The low hum of the fridge" renders as a hum; "street
  noise" renders as hiss.

## 5. Bodies, props and places

- **Starting postures are states, not moves:** "is already seated in the leather chair and stays
  seated". A bare "sits" renders the sitting down.
- **Name which way every seated or lying body faces, in every shot** (see camera.md, Bodies in
  vehicles and rows).
- **Car exits are unreliable.** Start the person already standing beside the car with the door
  open, or show the side of the car to the camera and name the door that opens.
- **Fix every prop in every shot it is in:** how many, what it shows, where it lies, and what it
  is after it changes (camera.md, Props the model would otherwise invent). A held prop is in the
  plate or is shown arriving.
- **Do not mention furniture nobody uses.** A named object gets used, and one named inside a
  moving clause moves with the person ("drags him away, the chair scraping" drags the chair too).
- **No fast body contact.** Near misses, a grab that then holds still, a shadow falling across
  someone: the threat reads, and nothing warps.

## 6. A film beat, worked

> [Shot 1] @a is already seated across the green felt table in @room, facing the camera
> three-quarter, his eyes on @b, lips pressed shut, two cards face down on the felt in front of
> him. A medium shot at seated eye level; the camera arcs slowly to the right around the table,
> about thirty degrees, keeping @a centred. At 00:00.000-00:04.000, chips click and the lamp hums.
> [Shot 2] At 00:04.000 a cut to a medium close shot of @b on the near side, facing the camera
> three-quarter, his eyes on @a just to the right of the frame, lips pressed shut. At
> 00:04.000-00:09.000, @b smiles slowly and says in a quiet, easy voice, 'Everybody has
> something. I just hide it better.' He presses his lips shut, still smiling, while the camera
> holds. [Shot 3] At 00:09.000 a cut to a close shot from just above the felt, looking down:
> @b's hand turns his two cards face up, two black aces. At 00:09.000-00:12.000, the camera
> holds on the cards, the lamp humming.

Check with `check_plan.py ... --no-mv` (dialogue allowed). The film lints are `eyeline`, `after-line`, `no-stop`, `mouth`, `back-view`, `phone`, `outfit`, `pull-in`, `no-eye-target`,
`prop-words` (and with `--map`: `goal-behind`, `sides`, `prop-picture`, `prop-holder`),
`lens-address`, `shot-people`, `early-cut` and `push-in`.
