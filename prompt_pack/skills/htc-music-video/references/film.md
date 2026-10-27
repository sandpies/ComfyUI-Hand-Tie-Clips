# Film: script, dialogue and sound

A film has no song. H3 makes every voice and sound itself, so the script carries what the song
carries in a music video: the timing, the speech and the silence. Read with [camera](camera.md).

## 1. The script

- **One-line story, then the turns:** anything that changes the situation (an arrival, an offer, a
  trick, a discovery, a betrayal, a payoff).
- **Budget the turns:** each needs a hop of its own plus room for reactions; three or four per
  minute plays well, five plays rushed. Cut a turn or add hops rather than squeeze.
- **End on a tease:** resolve, then open one small thread in the last shot (a phone that buzzes, a
  smile that fades), held 2-3 s with the last hop's `tail: hold`.
- **Show it, don't explain it:** a repeated image tells a betrayal better than a line.
- **A hop per place per moment:** restarts for a new place or time, continuations for the same
  moment carrying on. Most film hops are restarts with cuts inside them, on `motion_context`.
  A film in one room and one take can run on `hand_tie` (SKILL.md, one take or many places).

### The viewer knows only what the screen shows

- **The opening asks the question:** who these people are to someone and what they want, or
  something wrong. A showcase with no want reads as an advert; put the want inside it.
- **Every cut to a new place or time carries a visible link:** a look at what the next scene
  shows, a line naming where we go, an object carried across. By 2 s into the new scene the viewer
  can say why we are here.
- **A flashback has a trigger and a way back:** someone in the present sees, hears or says the
  thing; the past opens on that same thing in its own look; it returns to the face that
  remembered.
- **Show the first step of every decision** (a hand taking the card, the door opening) before
  cutting away.

**The viewer pass.** Before writing beats, retell the film as the screen alone shows it, scene by
scene, as someone who knows nothing. Write the viewer's question at each cut and where on screen
it gets answered; a cut with no answer gets a bridge or a new order. Hand the user the turn list
with hop numbers and running time, plus the viewer pass, before any beats.

## 2. Cast and voices

- Each speaking character gets a voice clip on their ref row (`"voice": "name_voice.mp3"`). It
  carries timbre only; write emotion, accent and pace in the beat.
- Each speaking character also gets a **voiceless row** (same sheet, same `subject`, another tag)
  for the hops where they do not speak: a voice riding a silent hop turns into speech.
- **Name the side of one-sided features** in `locked` ("a white streak over her right eye"), on a
  sheet whose every view agrees.
- **A masked or faceless character never speaks.** On a hop with lines his shot still needs a
  mouth state ("his mouth hidden behind the mask, his jaw still") and a loud sound of its own, and
  his moves start already done. A mask with a mouth shape that moves in a close got lip-synced;
  a mask with no mouth on the sheet is the likely cure. Never ask him a question.
- Graph: no `master_audio_file`, `voice_every_hop` = `speaking`, SLA Heavy Enforcement.
- `dialogue_lock` (`lines+hold`) on a `motion_context` hop that babbles; off by default, and it
  does nothing under `hand_tie`.

## 3. Writing a line

- **Delivery and face outside the quote:** `@a leans back and says in a low, amused voice, his
  eyes on @b, 'You play like a man with nothing to lose.'`
- **One delivery per line;** "excited, whispered and fast" fights itself.
- **About ten words, one sentence per quote,** single quotes, no ellipses or dashes, plain English
  spelling ("cafe", not "café"); hard names go outside the quote.
- **Behaviour, not feeling:** "lowers his gaze, jaw tight", never "he feels guilty".
- **Every line has a visible listener in a named direction,** never the lens.
- **The first line goes to the freest face:** the most central, frontal, not busy. To choose the
  order, give each line its own shot with the speaker alone.
- **The speaker stays in frame for the whole line;** moves and exits come after it.
- **About 20-25 spoken words in a 12-15 s hop at most,** with a beat after each line.

## 4. Silence and sound

**Busy frames stay quiet; empty ones talk** (directing.md, fact 3). Give every silent person
business with a sound of its own.

- **Every face without a line has a mouth state** ("lips pressed shut"), before, between and after
  the lines.
- **Every silent stretch has a named sound** ("the lamp humming", "rain drumming on the roof").
- **After a hop's last line, close the mouth and name the sound.** A longer last line does not
  stop the babble after it.
- **Phone calls end with the call clicking off.** A phone at an ear with no line gets talk; give
  the call a line and an end, or leave the receiver down.
- **Stings:** the model may score a reveal by itself. For one on purpose, name it on the cut ("a
  single low dramatic sting as the camera cuts to his face"); it lands about half a second early.
- **A no-line hop in a busy place fills with crowd speech.** Give it a score across the whole hop
  and keep extras out of the words and the plate. Not yet proven.
- **Narrowband sounds** ("the low hum of the fridge") over broadband ones ("street noise" is hiss).

## 5. Bodies, props and places

- Postures are states: "is already seated in the leather chair and stays seated".
- Name which way every seated or lying body faces, every shot (camera.md, vehicles and rows).
- Fix every prop in every shot; a held prop is in the plate or shown arriving.
- Don't name furniture nobody uses; one named in a moving clause moves with the person.
- No fast body contact: near misses, a grab that holds still, a shadow across someone.

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

Check with `check_plan.py ... --no-mv`. Film lints: `eyeline`, `after-line`, `no-stop`, `mouth`,
`back-view`, `phone`, `outfit`, `pull-in`, `no-eye-target`, `prop-words`, `lens-address`,
`shot-people`, `early-cut`, `push-in`; with `--map` also `goal-behind`, `sides`, `prop-picture`,
`prop-holder`.
