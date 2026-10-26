# Combat Scene

Fight overlay. Load after the mode guides when the request is a fight, combat, brawl, martial arts, knockout, 1v1, 1vMany, or “direct the fight”.

Shot / camera / dialogue / label syntax still comes only from `base-en.md` and `ref-en.md`, or from `multishot.md` when that chain is on. This file only changes what the timeline contains and unspecified combat duration. Chain motion limits in `multishot.md` still apply (no fast complex motion).

The prompt decides what the fighters do. Do not add a Combat Base file, `prfight2`, `prfin1`, `prfight1`, or `prslow1`. If H3 does not already know a named style (Wing Chun, wrestling, kesagiri, kote), do not use that label — write the visible limb and blade path in plain English.

Vague lines (`two people fighting`, `they exchange blows`, `flurry of punches`) produce fast, logic-less flailing.

On an official write, each beat is one motion-clock range inside the current shot. Range syntax is `references/field-craft.md`. A new `[Shot N]` is only a camera cut. On a multishot chain, keep one mechanical action in the paragraph and do not add timestamps.

## 1. Choreograph, then write

Plan beats before the multimodal body. Each beat:

1. Attacker
2. Visible path in plain English (which limb or blade, how it travels — not a school name)
3. Target zone on the opponent
4. Contact: hit / miss / block
5. Result that the next beat needs (momentum, opening, accumulated damage)

T2VA: invent unspecified fight beats so the chain is complete. Keyframe / ref lock rules stay in SKILL.md.

Each fighter also gets one **weight line** before any beat is written: how long their travel takes, how much recovery follows it, and what the lighter fighter does inside that recovery window. A heavy weapon travels wide and pays for it; a light one darts in the gap the recovery leaves. Two fighters at the same tempo is the flattest thing a generated fight can do.

Each fighter also gets one **asymmetric identifying detail**, stated once with its side and reused in every beat — a scar, a glove, a braid, a patch, a ring on a finger. A detail with no side anchors nothing. On Ref2VA, a detail the reference shows is a locked trait (`ref-en.md`). Do not invent a side the picture does not have.

### Paths

One row per beat, not three. A school name may follow a path; it never replaces one.

```text
STRIKING — limb, travel, target, what it costs the body
  rear hand straight out from the hip, horizontal across the near cheek;
  shoulder and hip turn through, heel of the palm ends past the jaw
  lead hand short and vertical, snaps out and snaps straight back to the chin
  rear leg flat arc from the hip, shin across the near ribs; supporting
  heel lifts and the whole body turns through it
  forearm rising elbow-first under the chin, the body square behind it
  knee driven up the centre line into the gut, both hands dropping to the hip
  elbow swung around the guard, the whole shoulder turning into it
  overhead two-hand drop onto blade or shoulder, weight falling through it,
  both feet leaving the floor on the follow-through

DEFENDING — what gives way, and where it goes
  forearms turn to meet the descending strike, elbows closing to the ribs,
  the blow sliding off the outside of the guard
  lead foot slides off the line of the incoming punch, weight staying back
  chin drops to the far shoulder, feet planted, the overhand passing over
  whole body rolls under, shoulder and hip taking the floor first
  short backstep, distance opening by half a pace, guard still up
  caught wrist turned and pulled across the centre line to open the elbow

GRAPPLE — the lock, the break, the landing
  collar and elbow closed, the arm turned past its own shoulder
  grip at wrist and elbow, twisting away from the thumb
  hip under the weight, both feet driving, the throw carrying the arc
  leg swept low from the outside, the standing foot replaced before the fall
```

Specific beats specific bodies. Contrast, not adjectives:

```text
Vague  "they exchange blows."
Named  "the rear hand comes straight across and the defender's forearm turns
       to meet it, sliding it off the outside of the guard."

Vague  "a flurry of punches."
Named  "three beats in a row — lead hand short, rear hand horizontal, then
       the same rear hand again, each one met by the same turning guard
       before it lands."

Vague  "he fights intensely."
Named  "he closes on a backstep, weight forward, and puts a shoulder into
       the other man's chest at the edge of the arm."
```

## 2. Beat grammar

Every exchange names who, the visible swing or step in plain English, where it lands, and the result. Expand a logline into beats. Do not leave a school-name as the only description of the move.

Physics:

- Continuous chain. Do not reset to a neutral idle between hits.
- Misses keep traveling. Blocks redirect. Contact unsticks; limbs do not stick together.
- Hit state persists and accumulates (torso bend, dropped guard, impaired footwork, limp, torn cloth, blood) until the requested ending.
- Phrases overlap: the next swing is already coming while the last is still landing. Do not write one-strike-then-wait / one-block-then-wait.
- A dodge, slip, duck, sidestep, or wet-tile slide is as valid as a block.
- A landed hit must change the body: stagger, limp, or roll. The victim recovers on their own (comes up already moving). Do not have the attacker hunt the roll unless the user asked — that recovery-chase tends to collapse the clip.
- Punches, kicks, short hops, and a two-hand jumping **sword** slamdown (blade into guard or tiles, shock ring) are fair. Do not lift the opponent, sit them on scenery as a rest, or write long aerial throws unless the user insists.
- Every 4–8 exchanges, one beat is a **reset**: both disengage, weight shifts, breath is audible, distance reopens. Write it as its own motion-clock range. H3 generates audio for the whole duration and invents motion to fill whatever it is left, so a named reset says what happens instead of leaving it to guess.

**ACTION → DIALOGUE.** If combat and speech share a shot, finish the strike and the visible reaction, then the line. Wordless shouts and pained grunts are non-verbal (body + soundscape). Do not invent spoken lines or kiai text.

## 2a. Pace

Tag every beat before writing it. The tag decides the camera and the range length. The four words are planning labels and do not appear in the paste.

```text
BEAT     a strike is travelling or being met
IMPACT   contact; the camera is closest here
RECOVERY the body answers the contact and the distance reopens
RESET    both disengage, weight shifts, breath audible, then it escalates
```

A fight is `BEAT IMPACT RECOVERY BEAT IMPACT RESET BEAT IMPACT`. Escalate inside the BEATs and keep the RESETs flat — a fight that escalates in the resets reads as frantic and lands nothing.

On a fight with no requested cuts, hold the whole thing in one shot and let the range boundaries carry the rhythm. When `director.md` is also on, the IMPACT tag is what licenses a cut: land the impact, open the next shot on the RECOVERY.

## 3. 1v1 vs 1vMany

**1v1.** Two bodies, one lane. If the director overlay is also on, coverage lives in `director.md`; otherwise prefer camera motion over cuts.

**1vMany.** Staggered attacker entrances, spatial lanes, protagonist-centered tracking. Extra attackers do not all strike in the same instant unless the user asked for a pile-on. Cut only when a new lane or attacker cannot be shown by camera motion (and I2VA / FL2VA still default to one shot).

### 1v1 skeleton

Attacker A: [plain-English path] → [zone] → [hit/miss/block] → [B’s lasting state].  
That state creates the opening for A’s next beat, or B’s counter, until the requested end.

### 1vMany skeleton

Hold the protagonist. Attacker 1 enters [lane] and commits [beat]. Attacker 2 enters only after that beat has a result. Track the protagonist; bring the next lane into frame as motivated motion or a cut that adds information.

Three rules keep a group readable rather than a blur:

- **Zoning.** One foreground pair carries the fight; anyone else stays a named lane in the mid or far ground, in fewer words. A frame with four equal fights is a frame with none.
- **Name the matchup.** State who is engaging whom at each beat. "Five warriors fighting" is chaos; "two on the left, one on the right" is a scene.
- **Rotate the initiative.** Whoever owns the last beat does not own the next one. One attacker running every exchange reads as a punching bag, not a fight.

Build order when the user has not laid the group out:

1. **Ground and field first.** Where the fight is, how far apart they start, what the light is doing — before anyone enters it. A group that arrives into an unestablished space has no lanes to be read in.
2. **One complete entry, one proof action.** The first entrant crosses in and lands something. That beat is the one the rest of the frame is calibrated against.
3. **The next entrant waits for a readable result.** Not a simultaneous pile-on, and the fighter furthest from the action waits longest.
4. **Close on a shared commitment** — two or more committing at once — with each still legibly themselves: their route, their side, the fighter they came in on.

## 4. Environment

When a body hits scenery, write three stages: human impact → environment reaction → material result (dust, split wood, glass, water). Do not skip to debris.

At the point of contact itself, name one or two and let the rest stay silent: spark burst where weapon meets weapon; sweat flung off a turn; cloth rippling before the blow arrives; ground cracking outward from the foot; water displaced in the direction the force went; debris thrown the way the strike travelled. One primary effect per IMPACT, or the frame turns to noise.

## 5. Duration and header

If unspecified, use `10.13` (243 frames) instead of the skill’s `6.58`. User-given duration and clips longer than 15 s follow SKILL.md; snap off-grid values in `canvas.md`.

Header: `mode · duration · combat`.

## 6. No LoRA tokens

Do not write `prfight2`, `prfin1`, `prfight1`, or `prslow1`. A heavier hit is a heavier beat in the body, not a trigger. If the user wants a slow-mo finisher, the body says the last hit goes briefly slow at impact, then normal speed resumes.

## 7. Sound and character FX

Put ambience, cloth, breath, stagger, rolls, and environment materials in `overall_soundscape`. Synchronized hits, whooshes, and wordless grunts also appear in the multimodal body at the moment they happen.

If the user wants character FX, give each fighter a stable signature in the style opening and reuse it: blade-trail color, spark temperature, afterimages, fire-ribbon, shock rings, impact frames. Lantern or scenery fire flares on big hits only. Do not change the choreography to make room for FX.

Slow-motion is written in the body (brief crawl at contact, then snap back to full speed).

## 8. Wiring (only if asked)

If the user asks for ComfyUI sampler wiring: `res_multistep` + `simple`, or `euler` + `beta`. Do not add a LoRA loader.

## 9. Do not import from other fight-prompt skills

The paths, the pace tags, the weight lines and the zoning rules above came from
public Seedance 2.0 / Higgsfield fight skills. Their craft transfers. Their
platform rules do not, and one line in particular is the opposite of correct here:

- Never carry across *"avoid X"* phrasing — *"avoid hyperrealistic gore," "avoid
  mid-sentence dialogue."* At cfg 1.0 with no negative branch, naming the thing
  you do not want is how you get it. `nsfw.md` affirmative framing is the pattern
  for restraint; a borrowed prohibition is not.
- Never carry a slow-motion *speed control* (`0.25x`, `0.5x`). There is no such
  control. §7 already has the right form: write it in the body.
- Never carry labelled-section prompt shapes (`SETTING:`, `COMBATANTS:`,
  `EXCHANGE 1:`) or a word-count target. The field schema owns the shape, and it
  is in `base-en.md` / `ref-en.md`.
- Never carry "longer takes work better, quick cutting is weaker." That is a
  Seedance limitation. It contradicts the `director.md` shot budget.
- Never carry resolution, fps, aspect or social-platform advice. This skill does
  not render.
- Named martial arts and weapon systems only as an H3-known label, and never
  without the plain path beside them. That rule is §1 and it is not negotiable
  just because a source has a nice table of them.

## 10. Self-check

Fix before showing if:

- a fight logline is not expanded into beats
- a move is only a school name with no visible path
- a beat describes an interaction without the six facts in `field-craft.md`
- a fighter has no weight line, or two fighters share one tempo
- an asymmetric identifying detail is missing, stated without its side, or changes sides between beats
- a pose resets to idle between hits
- speech starts before the current strike has finished
- a hit leaves no lasting body state (no stagger, limp, roll, or injury that persists)
- phrases are one-strike-then-wait
- a long fight has no reset beat, or the resets escalate along with the strikes
- a pace tag (BEAT, IMPACT, RECOVERY, RESET) appears in the paste as a label
- the attacker hunts a roll the user did not ask for
- an opponent-lift or long aerial throw appears without being requested
- invented spoken lines or kiai sit in `<d>`
- 1vMany extras all strike at once without being asked
- 1vMany has two or more equally-weighted fights in one frame
- 1vMany starts an entry before the field or the first entrant's result is established
- 1vMany ends without a shared commitment, or ends with a fighter who has lost their route or side
- one attacker runs every exchange without the initiative rotating
- an environment hit skips material reaction
- more than one primary impact effect lands on the same beat
- a prohibition naming something unwanted appears anywhere in the prompt
- `prfight1`, `prfight2`, `prfin1`, or `prslow1` appears in the paste
- a requested finisher has no decisive last beat
