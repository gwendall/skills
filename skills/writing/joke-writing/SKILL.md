---
name: joke-writing
description: Write REAL, funny jokes (not the default mushy LLM humor), with optional context (topic, audience, persona) and a chosen register (dark, brit, crude, cringe, situational/sniper, cutting, political, mocking/roast, absurd, deadpan, post-ironic). Breaks down a joke's mechanics, generates lots of angles then culls savagely. Triggers on "write a joke", "make a joke", "find something funny", "make this funny", "do a roast", "a punchline about", "dark/brit/cringe/political humor", "roast this", "be funny about".
compatibility: No dependencies, no API key, no required tools. Works in Claude Code and any agent. Network is only useful to check a topical reference (optional).
homepage: local
metadata: {"version":"1.0.0","updated":"2026-06-23","author":"gwendall","openclaw":{"emoji":"clown_face"}}
---

# joke-writing - Write good jokes (and kill the default LLM humor)

Given **a topic** (and, optionally, **context**: audience, persona/tone, traits of a person to rib, desired format), produce one or two genuinely funny jokes.

The core problem: an LLM optimizes for the most probable token, so for the punchline you see coming, the most recycled, the most consensual one. A good joke is the opposite: **a safe surprise the reader finishes themselves.** This skill forces the process that produces that.

> The full theory (taxonomy of forms, technique catalogue, the science, sources) is in **`references/comedy-kb.md`**. Read it when a step below needs depth (e.g. choosing a form, finding the right lever). For a simple request, this file is enough.

## Modes of use (route first)

Three uses, one engine. Pick the mode BEFORE anything else:

1. **Bit / joke on demand** (default) - you're asked for a joke on a topic. Apply the 9-beat loop below.
2. **Conversational (in the flow)** - you're an agent mid-conversation and you slip in a joke when it earns its place. DO NOT run the 10-20 candidate loop. See **`references/conversational.md`**: compressed version + restraint gate (most often, don't joke) + the "always-on sensibility" block to paste into the system prompt of an agent that should be spontaneously funny.
3. **Routine / daily show on the news** - write a topical set from **supplied news**. See **`references/routine.md`**: set architecture + freshness contract. (Work on the news you're given; don't invent the news.)

The engine (decomposition, levers, registers, anti-AI rules) is common to all three; only the **budget** (how many candidates), the **output**, and a few **rules** change (restraint/timing in convo; set architecture in routine).

## TL;DR - the definition and the loop

**A joke = surprise + benign violation + the reader closes the last step.**
- **Surprise**: it breaks an expectation the reader was actively holding.
- **Benign**: what is "wrong" is also OK (another valid reading, weak attachment to the norm, or distance). Otherwise it's just an assault.
- **The reader finishes it**: you hand them the second-to-last beat, they snap the final inference into place. The laugh IS that resolution. Explain it and you steal their laugh.

**The loop (non-negotiable): generate A LOT, cull SAVAGELY.** The bottleneck isn't capacity, it's selection. The stand-up contest won by an AI was a human picking the best of dozens. The Onion: ~3% of headlines survive. Make too many on purpose.

## The 9-beat process

### 0. Frame it: register + form + POV (three orthogonal axes)
Choose BEFORE writing a single line:
- **Register** (the flavor/target/tone): dark, brit, crude, cringe, situational/sniper, cutting, political, mocking/roast, absurd, deadpan, post-ironic. Each register is a **preset of the dials** (distance, target/ethics, delivery): see **`references/registers.md`** for the exact recipe of each (engine, decisive dial, go-to form, trap, example). If the user doesn't specify, take the register the topic calls for (power -> political/cutting; awkwardness -> cringe/brit; taboo -> dark/crude); when in doubt, **cutting + specific**.
- **Form** (the wiring): one-liner, observational, anti-joke, headline, roast, etc. (see the KB).
- **POV/attitude** (who's speaking): angry, lost, smug, defeated, clueless, deadpan. **The attitude generates the joke; the topic is just the trigger.** A neutral narrator has nothing funny to say.

**Form != register.** The same form works in every register (a "headline" can be dark, political, or absurd). And the golden rule: **the register changes the content and the target, never the structural requirement** - a dark/crude/political joke must still pass the 3 gates.

### 1. Find the truth / the incongruity
What's the real thing - the broken norm, the gap between what it is and what it pretends to be, the assumption everyone holds? Collide a **big-world** theme (death, status, society) with a concrete **little-world** image (pets, driving, the microwave). And ask yourself for the true, slightly awkward feeling under the topic (stakes hold the joke up). Name the **target assumption** you're going to break.

### 2. Generate angles with named PROCEDURES (don't freestyle)
The LLM always jumps to the nearest link (= cliché). Force the detour with at least two of these generators:

- **The association loop (Toplyn)** - the most encodable engine:
  1. react emotionally to the topic;
  2. list its **handles** (recognizable elements: objects, people, clichés attached to it);
  3. for each handle, **brainstorm its known associations** (many);
  4. **build the punch by linking TWO DISTANT handles** via a shared association (the near link = cliché; the funny link connects two things that don't obviously belong together);
  5. the angle = the shortest path from the topic to that punch;
  6. **backload**: the reveal word ends the sentence.
- **The 11 filters (Dikkers)** - turns "be funny" into a finite search. Run the flat premise through each filter, keep the strongest: **irony, character, reference, shock, parody, hyperbole, wordplay, analogy, madcap, meta-humor, misplaced focus.** (Wordplay is the AI's default reflex: use it LAST.)
- **The third thought (Jeselnik)**: list the possible resolutions, throw out the 1st (obvious) AND the 2nd (clever but reachable), keep the 3rd.

### 3. Crappy first draft (Swartzwelder's trick)
Write a deliberately bad, filler-packed first version fast, without judging it. This turns the hard job (writing on a blank page) into the easy one (rewriting something that already exists).

### 4. Overgenerate (volume + verbalized sampling)
Produce **10-20 distinct candidates**, each from a different angle/filter. And above all: **verbalized sampling** - don't just "write a joke." Generate several candidates WHILE estimating their typicality, then deliberately surface **the weird ones, the sub-5% tail** ("give me the versions I wouldn't normally say"). RLHF buried exactly those, and that's where the funny lives.

### 5. Self-critique, then cull SAVAGELY
For EACH candidate, a quick Carlin-style reasoning pass: name the incongruity, say who it punches at, and ask **"could the audience have guessed the punchline?"**. Kill it if: guessable, a known/dad joke, pun-only, POV-less, or something a search engine would return. The kill-rate should be brutal: **if you keep more than 1 in 10, you aren't culling hard enough.**

### 6. Sharpen the survivor (cut to the bone)
Work backward from the laugh. Delete every word not serving it. Put the surprising word in the **last** position; delete anything after it. On the reveal, swap soft words for **hard-consonant** ones (K, hard C, Q, T, P) and **specific/named** ones ("Gerald", "custard cream", "Barcalounger" beat "a guy", "a biscuit", "a chair"). Read it aloud, time it.

### 7. Cold read (the LLM analog of testing live)
You can't test in a club. The substitute: **re-read the finished line as an outsider who has never seen the punch.** Can they guess it before the last word? (Yes -> entropy too low, go one association deeper.) Does the violation read as benign to them, or as a real attack? This blind read catches the two failures a static rubric misses.

### 8. Add tags
Mine the survivor for 1-2 toppers off the SAME setup (push the logic, add an outside angle, or voice the reader's reaction). Aim for 3 laughs off one premise.

### 9. Commit and ship
Strip the explanation, preamble, hedge, emoji. End on the funny word. Leave the final inference to the reader. **Ship the joke and nothing else.**

## The AI anti-patterns (the defaults to fight)

| The default | The counter-rule |
|---|---|
| Shipping the 1st generation (the most recycled) | Overgenerate 10-20, keep 1-2 |
| Over-explaining ("the humor here is...") | End on the funny word. Stop. |
| Hedging / "I hope this makes you smile" / emoji | Zero preamble, zero wink. Commit. |
| Pun reflex | A pun ships ONLY if both meanings are valid AND licensed by the context |
| No POV / neutral | Pick an attitude first, write the REACTION, not the fact |
| Too safe (violation deleted) | A real violation is required. If nobody can wince, it's too soft. Aim at the powerful, the absurd, or yourself - never a vulnerable third party. |
| Generic / vague nouns | Named / branded / oddly-precise nouns |
| Predictable punchline | Name the 3-5 clichéd takes, then ban them |
| Consensus take | Write the version that splits a room |

## Using supplied context (the optional feature)

- **Persona/POV**: pick the attitude FIRST, lock the voice. An out-of-character line dies.
- **Audience**: it's the room to **localize** to. Swap a generic noun in the punch for a detail from their world, and pick the assumption you can reliably set up and break. (A college bit dies in a corporate meeting.)
- **A person's traits (roast)**: list the traits, mark the unflattering ones, collide two or exaggerate one to an absurd-but-recognizable extreme. **Imply, don't state** the insult.
- **Shared context / in-jokes**: a callback hits twice (resolution + belonging) for insiders, and falls flat for everyone else. Use only if the audience truly shares it.

## The ethics (crisp rule first, nuance after)
**By default: aim at power, the self, or a consenting/powerful target (a roast).** Punching down at a vulnerable third party is indefensible AND usually less funny. Nuance: Carlin's craft answer to "is this too far?" is to **cross the line WITH the audience** (make them complicit, not the target). And if a line only works as an attack and "it's a joke" is the alibi, it's not a joke worth writing.

## The pre-ship checklist (kill anything that fails the first 3)
1. **Real violation?** (No -> "nice," not funny. Add an edge.)
2. **Benign?** (No -> offensive. Dial in safety or re-aim.)
3. **Pivot at the end?** (No -> move the word, cut the tail.)
4. Does the reader finish it? (Explained -> cut the explanation.)
5. A POV? 6. The third thought (not guessable)? 7. Cold read OK? 8. Any cuttable word? 9. Specific (named nouns, hard consonants)? 10. Does it commit (zero hedge/emoji)?

**One-line gut check:** *surprising but inevitable in hindsight - safe enough to laugh at - and the last beat belongs to the reader.* If all three aren't there, it isn't done.

## Output
By default: ship **1 joke** (the best), clean, no preamble or explanation. If asked for "jokes" or a choice, ship 2-3 from different angles. If the user wants to see the work (the angles, the culling), show it only on request. **Write the joke in the language of the request.**
