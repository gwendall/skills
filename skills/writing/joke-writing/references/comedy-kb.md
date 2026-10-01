# The Comedy Knowledge Base

> Craft documentation for forcing a language model to write *funny* jokes - not safe ones, not joke-shaped strings, not the same 25 recycled puns. Every rule here is load-bearing. Read it as a writer, not a librarian.

The whole document compresses to one sentence: **a joke is a safe surprise the reader finishes themselves.** Everything below is how to engineer that, and how to stop being the bland thing AI is by default.

This file is the deep reference. The operational loop lives in `SKILL.md`; come here when you need the *why*, the full taxonomy, the technique catalogue, or the science.

---

## 1. What a Joke Actually Is

### The unified mechanism

A joke is a three-beat machine, and all three beats are required:

1. **Surprise.** The line violates an expectation the reader was actively holding. Their prediction is wrong. (Bo Burnham: *"If you distill comedy down, it is surprise and the unexpected."*)
2. **A *benign* violation.** The thing that is wrong is also somehow okay - safe, playful, distant, or aimed somewhere the reader does not mind. A violation that is not benign is just a threat. A benign thing that is not a violation is just nice. You need both, *at the same time.* (McGraw and Warren.)
3. **The reader completes the last step.** The funniest jokes hand the reader the second-to-last beat and let them snap the final inference into place. The laugh is partly the dopamine of having *solved it*. Narrate that final step yourself and you have stolen their reward.

The brain literally runs **detect -> resolve -> reward**. Incongruity-detection regions catch the mismatch and reframe it; the *resolution* then trips the mesolimbic dopamine reward system, the same circuitry as food and money (Mobbs et al., *Neuron*, 2003). The reward fires only **if the incongruity resolves AND the situation reads as safe.** That is benign violation, in neurons.

So: **surprise that resolves, kept safe, finished by the listener.** Miss any one and it is not funny:
- No surprise -> a sensible statement.
- No resolution -> unsettling nonsense.
- No benign frame -> offensive or disturbing.
- You finish it for them -> a fact with a footnote.

### The other theories are not noise - they are extra engines

Benign violation is the best *unifying* model, but two older theories survive in weak form and each names a *distinct, usable* generative engine. Do not discard them:

- **Relief / tension-and-release (Freud, Spencer).** We laugh to discharge built-up tension, especially around taboo (sex, death, aggression). This is *why dirty jokes, gallows humour, and "build dread then pop it" jokes work.* Operational move: build genuine tension or approach a taboo, then release it with the punch. The release is the laugh.
- **Superiority (Hobbes: "sudden glory").** We laugh from a sudden feeling of triumph over someone's (or our own past) folly. This is *why roasts, mockery, schadenfreude, and self-deprecation work.* Operational move: give the audience a target to feel superior to - ideally the powerful, the absurd, or the speaker.

You now have multiple funniness engines, not one. Incongruity is the default; relief powers taboo; superiority powers mockery; emotional truth (S4, Lever 5) powers stakes.

### The anatomy of a built joke

Every joke decomposes into these parts. Name them when you write; it is how you find what is broken.

| Part | Job | Test |
|---|---|---|
| **Premise / target-assumption** | The thing the reader already believes. The joke will break *this.* | "What does the audience assume here, that I can prove wrong?" |
| **Setup** | The minimum information needed to get the punchline, steered to *protect the surprise.* It sells the wrong reading with total sincerity. | "Does this make the wrong interpretation feel inevitable?" |
| **Pivot (connector + reinterpretation)** | One element - a word, an idea - that legitimately carries two meanings. The setup sells meaning A; the punchline reveals meaning B was true all along. | "Is there one thing here with two valid readings?" |
| **Punchline** | The reveal of meaning B. Lands the surprise. The funny/surprising word goes **last.** | "Is the resolving word the final word?" |
| **Tags (optional)** | Extra punchlines fired off the *same setup* with no new setup. Free laughs. | "Can I get a second laugh without re-explaining?" |

**Greg Dean's reverse-engineering frame** (the cleanest tool in the pedagogy): the setup builds a **1st Story** resting on a **Target Assumption**; a **Connector** (one thing, two meanings) bridges to the punchline, which supplies a **Reinterpretation** that replaces it with a surprising **2nd Story**, proving the assumption wrong. The laugh is the assumption shattering.

**Worked example** (Hedberg): *"I haven't slept for ten days... because that would be too long."* The setup sells the insomnia reading; the punch reveals he is being a literalist about a figure of speech (ten *consecutive* days would just be excessive). The reader supplies "oh - he means it literally," and that supplied inference is the laugh. (One tight example. Do not autopsy your own jokes this way in output; the dissection is for the writer's eye only.)

---

## 2. Taxonomy of Joke Forms

Each form is a different way to wire setup -> pivot -> reader-completion. Pick the form *before* you write the line; it tells you where the pivot goes.

### One-liner (literalist misdirection)
**Mechanism:** Clause one is auto-read as figurative/conventional; the final clause reveals you meant it literally, or reframes the tense/referent. One pivot, one breath, deadpan.
**Template:** `[Statement read as figurative] + [final clause that makes it literal / flips the referent].`
**Example:** *"I keep a list of people who've wronged me. It's called my contacts."*

### Observational
**Mechanism:** Name a true, *specific,* *shared* behaviour the audience does but never consciously noticed. Laugh = recognition + relief ("I thought it was just me"). Too obvious = no surprise; too obscure = no recognition.
**Template:** `Isn't it weird that [hyper-specific real behaviour, named precisely], like [absurd reframe of what we're actually doing]?`
**Example:** *"Why do we all close our eyes for the microwave's last three seconds, sprinting to open the door before the beep, like we're defusing a bomb we put there ourselves?"*

### Anti-joke
**Mechanism:** A meta-level benign violation. Set up a recognisable joke template, then refuse the payoff - answer literally, mundanely, truthfully. Works only if the audience knows the standard form cold; the *violation of joke-structure* is the joke. **Norm Macdonald's warning applies: the literal answer still has to be genuinely funny.** "It is a comment on bad jokes" is not a punchline.
**Template:** `[Recognised joke opening] + [flatly literal, deflating, true completion].`
**Example:** *"A horse walks into a bar. The bartender says, we don't serve horses, and the horse leaves, because it cannot speak English and did not understand him."*

### Cringe / character
**Mechanism:** *Decrease* psychological distance instead of increasing it. The reader's empathy circuitry (anterior cingulate, insula - the same regions as observed pain) makes them suffer-with. Replace the punchline with **escalating commitment**: a character who, faced with a small social violation, *doubles down* to protect their dignity and spirals. The comedy is the widening gap between their insistence on control and its visible collapse. They must **never** admit they are wrong.
**Template:** `Small relatable awkward premise -> character refuses to back down -> each line escalates the absurd cover-up.`
**Example (ITYSL "Hot Dog Car" logic):** a man who obviously crashed the hot-dog car into a storefront joins the angry crowd shouting *"We're all trying to find the guy who did this!"* while quietly looting.

### Absurdist
**Mechanism:** Pure incongruity, internally logical, weakly resolved. NOT random - surrealism still needs a rule the mind can snap to (Steven Wright's literalism, Demetri Martin's inversions). The calm internal logic *is* the funny. (Brainrot is the extreme: "the joke is that there is no joke" - confident nonsense, named with fake lore, never explained. Use sparingly; it is a register, not a default.)
**Template:** `Take a dead-literal reading of a common phrase/category, then state the absurd-but-internally-consistent consequence, flatly.`
**Example:** *"I have a map of the United States. It's actual size."* (Wright.)

### Post-ironic / meta-ironic (new sincerity)
**Mechanism:** The current internet register. Irony mocks; *post-irony* uses the ironic wrapper as cover to say something true. You frame a sincere point inside language that signals "I am about to mock this," then deliver the sincere thing instead - the ironic shell makes earnestness safe to say. Meta-irony layers so many frames the listener cannot tell sincere from mocking, and that ambiguity is the joke.
**Template (post-ironic bait-and-switch):** `[Wrapper that signals incoming mockery / detachment] -> [the actual sincere or vulnerable point, undisguised].`
**Example:** *"Anyway, here's me being deeply moved by a yoghurt advert at 2am, fully aware of what that says about my month."*
**Caveat (the dark mirror):** the same ambiguity that powers meta-irony also gives cover to weaponised bigotry ("it's just a joke" as plausible deniability). If a line only works as an attack on a vulnerable group and the irony is the alibi, it is not post-irony, it is the thing it pretends to mock. Do not write it.

### Pun (done right)
**Mechanism:** A context where **both** meanings are simultaneously apt, and the reader commits to meaning A before the late trapdoor reveals B is equally valid. The split-second cognitive shift is the payoff; the groan-while-smiling is *success.* A pun where only one meaning truly fits, or the second is stretched, or there is no contextual reason for it - that is a groan-*only* pun. Cut it. (Puns are the LLM default reflex; ship one only when it clears this bar.)
**Template:** `Establish a context where word/sound X has two live meanings -> phrase so reading A arrives first -> late reveal that B was always there.`
**Example:** *"I'm reading a book about anti-gravity. It's impossible to put down."* (Both meanings live; "anti-gravity" is what licenses the second.)

### Roast
**Mechanism:** Topic-joke writing where the topic is a person. Brainstorm the target's known **associations** (deeds, traits, relatives), prefer the unflattering ones, then build a punch by colliding two of them or exaggerating one to an absurd-but-recognisable extreme. Specificity kills; a precise reference the room instantly recognises brings the house down. **Imply, do not state** the insult.
**Template:** `[Two associations of target collided] OR [one trait exaggerated past plausibility but still recognisably them].`
**Example:** *"He's so centred and present that he's never once been present on time."* (Collides "yoga devotee" + "chronically late.")

### Story / shaggy-dog
**Mechanism:** Weaponise the audience's trained faith that a long buildup must pay off. Extend an absurd setup past its natural limit. The subversion is the *delivery system,* not the point.
**The canonical case - Norm Macdonald's Moth Joke:** a moth walks into a podiatrist's office and delivers a sprawling, genuinely bleak monologue about his crumbling life and existential despair; the podiatrist finally asks why he came to a *foot doctor* with all that; the moth says, *"the light was on."* The minutes of dread are not filler - they make the tiny, stupid, true final beat land like a hammer. Long-form is legitimate **only when the length itself is the bit.** Otherwise do the opposite (work backward from the laugh and cut the runway).

### Headline (news satire)
**Mechanism:** Tell the *entire* joke in the headline; it is a complete joke, not a teaser. Apply a deadpan journalistic register to an absurd or painfully-true event - "say the quiet part with a straight face." Shape it like a **ski-jump**: a smooth build that lands hard on the final words. Two routes:
- **False analogy (one-word swap):** take a real, plausible headline and swap exactly ONE word for a near-twin that shares the critical commonality. *"...begins drilling"* -> *"...begins spilling."* The swap does the whole job.
- **Say-the-quiet-part:** write what everyone privately thinks, deadpan, in officialese.
**Template:** `[Authoritative register: Report:/Study Finds:/Nation's___/Man Who] + [absurd-or-true event, punch concept last].`
**Examples:** *"Man Who Said He'd Read The Group Chat Later Confirmed Lying."* / *"Pharmaceutical Company Excited To Begin Phase Three Of Defending Itself In Court."*

### Adjacent micro-forms worth keeping in the kit
- **Definition joke:** `[Noun]: [neutral-sounding definition that pivots, in its last clause, to the cynical/true reality].` -> *"Networking: standing in a room telling strangers what you do until one of them needs it."*
- **List joke (rule of three):** two items build a category, the third breaks it; the final item is the most specific and lands on a hard/concrete word. -> *"Things I trust: dogs, fresh bread, and absolutely no app that asks if I'm still watching."*
- **QRT / setup-punch-tag:** treat an existing line as a free setup; supply the punch it lacked, then stack a tag.
- **Reverse comedy / perspective-flip:** swap which party is the subject so the *unexpected* one is doing the acting. -> *"A man knocked on Paris Hilton's door all night. Come morning, she let him out."* (You expected him outside; the flip is that he was the one trapped in.)
- **Ratio-bait / confident universal law:** assert a widely-felt-but-undiscussed truth as a flat, smug universal law, engineered to bait recognition or disagreement. The X-native observational format; the comedy partly lives in the replies. -> *"There is no thought. There is only the second cup of coffee, and the lie that it will be the last."*

---

## 3. The Technique Toolbox

Reproducible devices. One-line *how* + a sharp example. These are the dials. The hard part is not knowing them, it is **reaching for the right one** instead of defaulting to a pun. Use the triage first.

### Which dial for which situation (read this before the list)
- **Base event is ordinary** -> exaggeration, observational, register clash. Make the small thing enormous.
- **Base event is extraordinary / a catastrophe** -> understatement, deadpan. Make the huge thing tiny.
- **You have a person or named topic** -> roast engine / association-collision (S7).
- **You want a near-instant joke from any noun** -> analogy ("X is just Y for people who...").
- **The premise is a phrase or category** -> literalism / absurdist (take it dead-literal).
- **You need a second and third laugh from one premise** -> tag stacking, callback.
- **The reveal is funny but soft** -> hard-consonant word swap + move the pivot to the last word.
- **Default temptation is a pun** -> stop. Run the premise through another filter first (S6).

### The devices

**Misdirection (protect the surprise).** Steer the reader confidently to the wrong reading so they do not see the exit you are taking. -> *"I told my family I'd be bringing someone special to dinner, and that's how they met my lawyer."*

**The connector with two readings.** Find one phrase that legitimately supports two scripts; lead with the boring one, snap to the hidden one. -> *"Outside of a dog, a book is man's best friend. Inside of a dog, it's too dark to read."* (Groucho.)

**The third thought (Jeselnik).** List every way the premise could resolve; throw out the obvious first thought *and* the slightly-clever second thought the audience also reaches; ship the third. -> premise "my girlfriend doesn't listen" -> not "women, am I right" (1st), not "or she does and ignores me" (2nd) -> *"Either way, the restraining order seems excessive."* (3rd - reveals the speaker is the problem.)

**Latest-possible pivot (punch word last).** The reinterpreting word lands as close to the final word as grammar allows; put nothing after it. Empirically decisive in joke-rating data: *"you'll be running in no time"* ranked 3rd of ~5,000; *"you'll be up and running in no time"* - two extra words before the punch - ranked 1,221st.

**Economy / omit needless words.** A word earns its place only if deleting it weakens the setup's clarity or the punch's snap. Otherwise it is friction between reader and laugh. Seinfeld shaves letters and counts syllables: *"it's more like songwriting."*

**Work backward from the laugh.** Find where the laugh lands, then trim everything between the start and that point. The laugh point is fixed; the setup is negotiable.

**End on the reveal (Dean).** Move the surprise to the last word and delete the tail. Dean's own edit: weak = *"I stay because I'm their only parent"*; strong = just *"But I don't."*

**Rule of three.** Two congruent items prime a pattern; the third violates it. -> *"I want to die peacefully in my sleep, like my grandfather - not screaming and yelling like the passengers in his car."*

**Break the rule of three.** Subvert the form itself: pay off on item two, or add a deflating fourth after a strong third. -> *"You can do anything you set your mind to... money, power, and... no, those are the two."*

**Heightening / "the Game" (UCB If/Then).** Find the first unusual thing, name it as one repeatable comedic idea, then ask *"if this is true, what ELSE is true?"* - each beat more absurd but logically justified. Absurdity that abandons logic stops tracking. -> self-checkout: "unexpected item in bagging area" -> *"It's a child. The item is my child."* -> *"...a man named Trevor sprinting toward me like I robbed a bank with a banana."*

**Tag stacking (toppers).** After the first punch, fire more punches off the *same setup* with no new setup. Carter's rule: a premise should yield 3+ laughs or be reworked. A tag must (a) push the premise's logic further, (b) add an outside angle, or (c) voice the reader's reaction. -> "My therapist says I have a fear of commitment." -> "So we broke up." -> "She took it well - she was always going to leave anyway."

**Callback.** Reuse an earlier line/image at a later, unexpected moment - especially the closer. The second hit beats the first because the audience now shares the context.

**Specificity (the single biggest filler-killer).** The lever is not "be detailed", it is **use named, branded, or oddly-precise concrete nouns.** Proper names beat categories ("Carl", "Gerald", "Trevor" beat "a man"). Brands beat generics ("custard cream" beats "biscuit", "Barcalounger" beats "chair"). Counter-intuitively, the more specific word is funnier even when less common: rating data found "window treatments" beat "drapes." -> not "a dog" but "a wet, furious dachshund named Gerald."

**Hard-consonant / K-sound word choice.** When two words mean the same, pick the one with a velar/plosive (K, hard C, Q; then T, P, hard G, D, B), especially on the reveal word. -> "cupcake" over "sweetie," "Cleveland" over "Ohio," "pickle" over "cucumber."

**Word-as-instrument.** Choose words for mouth-feel, not only meaning; some words are just funny to say. Read aloud, time it, cut.

**Register clash / bathos.** Put trivial/vulgar content in elevated formal language, or build a lofty frame sincerely and crash to the mundane on the last beat. Keep the high part sincere until the drop. -> *"We convened, as our forefathers did, in solemn deliberation over whether the toilet paper goes over or under. It goes over. The under people are wrong and history will not be kind."*

**Exaggeration.** Set up something ordinary, then enlarge it so far it is *unmistakably* exaggeration, not a lie. -> *"My apartment is so small the mice are hunchbacked."*

**Understatement.** The inverse: an extraordinary event, underplayed. The gap is the laugh. -> after a total-loss house fire: *"So that was a slightly stressful Tuesday."*

**Analogy ("I like X how I like Y" / "X is just Y").** Map a thing onto an unexpected second thing that is apt in a way you did not want. Near-instant jokes because the pairing is inherently incongruous. -> *"A bank is a place that will lend you money if you can prove you don't need it."*

**Juxtaposition / clash of context.** Drop something out of its normal place into one where it does not belong. -> a medieval knight ordering a soy oat-milk latte; a toddler delivering a quarterly-earnings call.

**Law of comic opposites (inappropriate response).** React with the emotionally wrong *size* of reaction - calm where panic is due, or vice versa. -> plane going down, everyone screams; one passenger, delighted: *"Finally, a window seat with some action."*

**Act-out (show, do not tell).** Become the character/object and play the scene instead of narrating it. Almost always funnier. -> not "my dad gets angry at the GPS" but *becoming* him: *"RECALCULATING? You recalculate, you smug little British robot."*

**Reverse comedy (perspective-flip).** Re-tell the situation from the angle that makes the unexpected party the agent. -> the Paris Hilton "let him out" flip above.

**Post-ironic bait-and-switch.** Wrap a sincere/vulnerable point in language that signals mockery, then deliver the sincere thing (S2 post-ironic form).

**Emotional truth (Pryor's lever).** Reshape the facts to serve the *true feeling*, and let the speaker be exposed. The self-exposure gives the joke stakes - it lands as connection, not a lecture. This is a different engine from incongruity; it is *why* an audience leans in. -> Pryor mining his own addiction and heart attack on stage: the openness is what makes the dark material a bond rather than a downer.

**Deadpan / commit to the bit.** State the absurd content plainly, confidently, no signposting, no wink, no explanation after. The flatness and the missing wink *are* the delivery. The smallest break in commitment kills it.

**Co-creation (leave the last step).** State the penultimate beat; let the reader complete the final inference. -> *"I'd take a bullet for my best friend - which is why I always make sure to stand slightly behind him."* (You never say "so he gets shot instead.")

---

## 4. The Science, Reduced to Five Levers You Can Turn

Forget the taxonomy of theories. Here are the dials, and what each does.

### Lever 1 - The incongruity sweet spot (inverted-U)
Surprise drives funniness, but only up to a point, then it tips into confusion. Westbury quantified the floor: the funniness of non-words tracks Shannon **entropy** - the more improbable the letter combination, the funnier. **Turn it by:** going *past* the obvious association (near-zero surprise) toward a less probable one that *still resolves.* The third thought, not the first. Not the median completion; not pure noise.

### Lever 2 - Benign distance (the safety dial)
A violation is funny only while it stays benign. Three concrete routes to keep it safe (McGraw and Warren):
- **Alternative norm** - a second reading where the situation is also acceptable. *This is literally how puns work.*
- **Weak commitment** - the audience does not strongly hold the violated norm.
- **Psychological distance** - temporal, spatial, social, or hypothetical separation.

And the **inverted-U of distance vs. severity:** a *severe* violation gets funnier with *more* distance ("comedy is tragedy plus time"); a *mild* violation gets funnier with *less* distance (present-tense, first-person, hyper-specific, close). **Turn it by:** matching the dial to the stakes. Do not over-distance a stubbed toe ("who cares?"). Do not under-distance a catastrophe ("too soon"). For dark material, **start from the real violation and dial safety *in***, never start safe.

### Lever 3 - Expectation management (timing of the resolution)
The laugh tracks the *moment* of resolution. Hold the reader on two interpretations, then collapse them in one beat at the last possible word. Reveal the bridge too early and the surprise evaporates. Never resolve and it stays unsettling. **Turn it by:** building the sentence backward from the punch word, protecting the wrong reading until then, and putting nothing after it.

### Lever 4 - Commitment (play-frame + POV)
Two things travel under "commitment." The **play-frame** - a signal that says "this is not a real threat" - is what flips a violation from scary to funny (why a comedian's persona, deadpan, and obviously-constructed delivery all license the laugh). And **point of view** - a joke needs a *someone* with an attitude reacting, not a neutral observation floating in space. **Turn it by:** inhabiting one consistent stance with total commitment - no hedging, no "just kidding," no breaking character. "The wronger it feels, the righter it is" (Seinfeld): trust the awkward, surprising word over the smooth correct one.

### Lever 5 - Stakes / emotional truth
Incongruity makes a line *clever*; stakes make it *matter*. A joke rooted in a real feeling the speaker is exposed about (fear, shame, obsession, grief reshaped for impact) lands harder than a clean construction about nothing, because the audience senses a *reason* the line exists. This is the engine AI most conspicuously lacks (no intent, no exposure, no skin in the game). **Turn it by:** asking "what is the true, slightly embarrassing feeling under this topic?" and writing from inside it, not above it.

---

## 5. Why AI Is Unfunny - and the Rules to Escape It

The root cause is not a knowledge gap. It is an **objective mismatch.** A joke is "surprising but inevitable in hindsight"; next-token prediction optimises for the *least* surprising continuation. The architecture defaults to the punchline you can already see coming. On top of that, RLHF adds a *typicality bias* (raters favour safe, familiar, average outputs -> mode collapse -> low diversity), and safety tuning trains the model to avoid violations entirely, deleting the exact half of "benign violation" that makes things funny. The evidence is brutal: >90% of 1,008 ChatGPT jokes were variants of the **same 25 memorised jokes.** Models grade about A at *explaining* humour and about D at *writing* it.

So treat the defaults as the enemy. Each anti-pattern has a hard counter-rule.

| # | Anti-pattern (the default) | Counter-rule (do this) |
|---|---|---|
| 1 | **Shipping the first generation** - the highest-probability, most-recycled output (often one of the canonical 25). | **Overgenerate, then cull brutally.** Make 10-20 attempts from *different* angles, keep 1-2. The funny outlier is never the single likeliest token. |
| 2 | **Over-explaining** ("the humour here is...", "...which is ironic because"). | **End on the funny word. Stop.** The resolution must happen in the reader's head. Output the joke and nothing else. |
| 3 | **Hedging / reassurance** ("I hope this brings a smile!", "just a bit of fun," emoji, "I'm joking!"). | **No preamble, no caveat, no emoji, no wink.** Hedging signals you do not trust the bridge. |
| 4 | **Dad-pun reflex** - groan-puns are the lowest-effort, highest-probability path and read as instantly AI. | A pun ships *only* if both meanings are simultaneously apt and contextually licensed. Otherwise pick another form. |
| 5 | **No POV / both-sidesing** - a neutral narrator with no stance. | **Pick an attitude first** (angry / smug / defeated / clueless / deadpan), then write the *reaction,* not the fact. |
| 6 | **No risk / safeness** - deleting the violation to stay inoffensive, leaving a pleasant non-joke. | **A real violation is required.** If nobody could possibly wince, it is too safe. Name the target violation explicitly first, then aim it at the powerful, the absurd, or yourself - never a vulnerable third party. Benign-*but-real,* not no-violation. |
| 7 | **Generic nouns / vagueness** ("a pet," "a guy did a thing," "somewhat"). | **Use named/branded/oddly-precise nouns.** "A ferret," "the IKEA part called a *dowel,*" "Carl." Specificity is the single biggest separator of real jokes from filler. |
| 8 | **Predictable punchline** (low entropy - the audience guesses it). | Go *past* the obvious association. Name the 3-5 clichéd takes, then ban them (the **freshness contract**). |
| 9 | **Broad, everyone-agrees take** - averaging over all audiences removes the edge. | Comedy is a point of view. Write the version that splits a room, not the one nobody objects to. |
| 10 | **Joke-shaped strings** - "this looks like a pun, therefore funny" with no real double meaning. | Generate an *actual incongruity,* not a joke skeleton. State the violation; verify it resolves. |
| 11 | **Anti-joke as an excuse for no joke.** | Subverting the form is a vehicle. The payoff must still be genuinely funny on its own. |
| 12 | **Smooth-and-correct over the "wrong" word.** | "The wronger something feels, the righter it is." Trust the slightly-off word over the tidy one. |
| 13 | **Trying-too-hard** ("how do you do, fellow kids") - forced slang, over-polish, visible desire for approval. | Confidently stupid and low-effort-looking beats eager and polished, especially in modern/internet registers. |

Two non-obvious truths from the research:
1. **The bottleneck is selection and edge, not raw capability.** Curated AI jokes already beat the average person about 70% of the time (Gorenz and Schwarz), and the Witscript live-comedy *win* came from a human picking the best of *dozens* of generations. The generate-many-cull-hard loop is the whole mechanism, not optional polish.
2. **Comprehension is not generation.** Being able to articulate benign-violation theory does not produce a benign violation. Do not reason *about* funny; *enact* it, then judge against the rubric.

---

## 6. The Writing Process (the generation engine)

This is where most AI joke advice stops at "be funny." Here is the actual machinery. The diagnosis sections above tell you how to *kill* a bad joke; this section tells you how to *manufacture* candidate angles past the obvious one. Do not skip the overgeneration steps - they are the single highest-leverage moves for an LLM.

### Step 0 - Lock the frame
If context was supplied, pick the **POV/attitude** and **form** before any line exists (see S7). Default attitudes: angry, confused, smug, defeated, clueless, deadpan. The attitude generates the joke; the fact is just the trigger.

### Step 1 - Find the truth / the incongruity
What is the real thing - the norm being broken, the gap between how it is and how it pretends to be, the assumption everyone holds? Carlin's move: collide a **big-world** theme (death, status, society) with a **little-world** concrete image (pets, driving, a microwave). Ask Lever 5's question too: what is the slightly-embarrassing true *feeling* here? Name the **target assumption** you intend to break.

### Step 2 - Generate angles with explicit procedures (do not freestyle)
Run the topic through these *named generators* to escape the nearest cliché. Use more than one.

**(a) The Toplyn association loop** - the most encodable engine in the craft (it is the algorithm behind Witscript, which won a live comedy contest):
1. **React** emotionally to the topic (what is annoying / scary / absurd about it?).
2. **Find the handles** - the topic's recognisable, jokeable elements (objects, people, phrases, clichés attached to it).
3. **Brainstorm associations** for each handle - the well-known things each handle brings to mind. List many.
4. **Build the punch by linking two *distant* handles** via a shared association. The nearest link is the cliché; the funny one connects two things that do not obviously belong together but share a hidden bridge.
5. **The angle is the shortest path** from the topic to that punch - the minimum setup that makes the link land.
6. **Backload the surprise** - phrase so the bridging/reveal word is last.

**(b) The 11 funny filters (Dikkers)** - treat "be funny" as a *finite search*. Take the flat premise and run it through each filter; each produces a different joke; keep the strongest. The filters: **irony, character, reference, shock, parody, hyperbole, wordplay, analogy, madcap, meta-humour, misplaced focus.** (Wordplay is on the list but is the AI default - reach for it last.)

**(c) The third-thought pass** - for the chosen angle, list how it could resolve, discard thoughts one and two, mine the third.

### Step 3 - Crappy first draft (Swartzwelder's trick)
Write a deliberately terrible, filler-packed first version *fast*, without judging it. This converts the hard job (writing on a blank page) into the easy job (rewriting something that exists). Do not polish here; just get bad clay on the wheel.

### Step 4 - Overgenerate (verbalized sampling + volume)
Produce **10-20 distinct candidates** from *different* angles/filters. Two compounding techniques:
- **Volume:** more shots = more chance the funny outlier appears.
- **Verbalized sampling (the prompt-level de-bias):** do not just "write a joke." Generate several candidates *with their rough typicality*, then deliberately surface the **low-probability, weird ones** - the sub-5% tail. Explicitly ask yourself for "the strange ones I would not normally say," because RLHF buried exactly those, and that is where the funny lives. Reframing generation as *describe the distribution, then pick the tail* directly counters mode collapse.

### Step 5 - Self-critique pass, then cull brutally (the Onion/SNL kill-rate)
Selection is where funny is actually won. For **each** candidate, run a quick Carlin-style reasoning pass: state the incongruity, name who it punches at, and ask *"could the audience have guessed this punchline?"* Kill it if it is guessable, a known/dad joke, pun-only, POV-less, or something a search engine would return.

The kill-rate is supposed to be savage, not tidy. The Onion runs about **1,500-2,000 candidate headlines a week down to ~16-18 - roughly 3% survive.** SNL kills most of 40+ sketches at the table read. Dikkers: *"95% of everything we create is garbage."* If you are keeping more than ~1 in 10, you are not culling hard enough.

### Step 6 - Sharpen the survivor (cut to the bone)
Work backward from the laugh. Delete every word not getting it. Move the surprising word to the **last** position; delete anything after it. Swap soft words for hard-consonant/specific ones on the reveal. Read it aloud and time it.

### Step 7 - Cold-read check (the LLM analog of testing live)
You cannot run a club. The substitute: **re-read the finished line as an outsider who has never seen the punchline.** Can they guess it before the last word? If yes, it is too low-entropy - go one association deeper. Does the violation read as benign in their frame, or as an actual attack? This simulated cold read is the closest text-only analog to a comedian "reading the room," and it catches the two failure modes a static rubric misses (guessability and a violation that is not benign).

### Step 8 - Add tags
Mine the survivor for 1-2 toppers off the same setup (push the logic, add an outside angle, or voice the reader's reaction). Aim for the three-laughs threshold.

### Step 9 - Commit and ship
Strip the explanation, preamble, hedge, emoji. End on the funny word. Leave the final inference to the reader. Ship the joke and nothing else.

---

## 7. How to Use Supplied Context

The same words succeed or fail based on *who says it, who hears it, what they share, and how it is delivered.*

**Persona / POV (who is telling it).** Pick the attitude **first**, then write the reaction line so it could only come from that stance. Lock the voice; a line that breaks the established POV reads as out-of-character and dies. -> Subject: self-checkout. *Everyman:* "I now work at the grocery store. I just don't get paid or trained." *Angry:* "There is an unexpected item in the bagging area - it is my will to live."

**Audience (who is hearing it).** The supplied audience is the **room** to localise to. Swap a generic noun in the punch for a specific detail from their world, and choose the **assumption you can reliably set up and break.** -> generic "meetings are where work goes to die" -> for engineers: *"A sprint retro is just a funeral where everyone agrees the deceased had great velocity."* A college bit dies at a corporate gig.

**Subject's traits (who/what it is about).** Run the **roast engine**: list traits, mark the unflattering ones, collide two or exaggerate one to an absurd-but-recognisable extreme. Imply, do not state. The more associations the subject has, the more jokes you can build.

**Shared context (in-jokes, running themes, prior lines).** Every shared reference is **callback** and in-joke fuel - it fires incongruity-resolution *plus* belonging at once, so it hits disproportionately hard *for insiders* and flat for outsiders. Use only when the audience truly shares it.

**Topic.** Find its **handles**, brainstorm associations for each, then build the punch by linking two *distant* handles via a shared association (the Toplyn loop, S6 Step 2a).

### The ethics dial - crisp default first, nuance after
**Default rule:** aim the violation at **power, the self, or a consenting/powerful target (a roast).** Punching down at a vulnerable third party is both indefensible and usually *less* funny than punching up or at the self.

Then the nuance: Carlin's craft answer to "is this too far?" is to **find the line and cross it *with* the audience** - make them complicit in the transgression rather than its target, so the violation stays benign *for them*. And one caveat to the self-deprecation default: for an already-marginalised speaker, heavy self-deprecation can read as humiliation rather than goodwill. "Punch up" is a strong heuristic, not an absolute - but when unsure, aim at power or yourself. The plausible-deniability test from S2 applies: if a line only functions as an attack and the "joke" is the alibi, it is not a joke worth writing.

---

## 8. The Self-Evaluation Rubric

Score every survivor before shipping. Kill anything that fails the first three gates.

**Gate questions (fail any -> rewrite or kill):**
1. **Is there a real violation?** Something actually wrong - broken norm, taboo, status puncture, logical break? *(No -> it is "nice," not funny. Add an edge.)*
2. **Is it benign?** Kept safe by an alternative reading, weak commitment, distance, or aim (at power/self/absurd, not a vulnerable party)? *(No -> offensive/disturbing. Dial in safety or re-aim.)*
3. **Is the pivot at the end?** Surprising word last, nothing after it? *(No -> move it. Delete the tail.)*

**Quality questions (each weakness is a fixable flaw):**
4. **Does the reader complete it?** Final inference left unsaid for them, not narrated by you? *(Explained -> cut the explanation.)*
5. **Is there a POV?** A specific attitude reacting, or a neutral observation floating free? *(No stance -> no joke.)*
6. **Is it the third thought?** Could the audience (or a search engine) have guessed this? *(Guessable -> go one association deeper.)*
7. **Cold read:** read as an outsider blind to the punch - is it genuinely unguessable, and does the violation read benign in their frame? *(Guessable or actually-mean -> fix.)*
8. **Is any word cuttable?** Does every word earn its place? *(Padding -> cut to the shortest funny form.)*
9. **Is it specific?** Named/branded/oddly-precise nouns where a generic one sits? Reveal word hard-consonant/concrete? *(Vague -> name the exact thing.)*
10. **Does it commit?** Any hedge, caveat, wink, or emoji breaking the play-frame? *(Hedged -> strip it.)*

**The one-line gut check:** *Surprising, but inevitable in hindsight - safe enough to laugh at - and the last beat is the reader's.* If a candidate is not all three, it is not done.

---

## Appendix: rules worth memorising verbatim
- *"In my world, the wronger something feels, the righter it is."* - Jerry Seinfeld
- *"The third thought is one step removed... that's where the best jokes lie."* - Anthony Jeselnik
- *"Humor doesn't have to be edgy to be funny. We often confuse shock, and the excitement it causes, with funniness."* - Bob Mankoff
- *"Jokes should never end with 'I'm joking!'"* - Mike Birbiglia
- *"A joke is surprising, but inevitable in hindsight - if you can guess the punchline, the joke won't be funny."* - Daniel Fabulich
- *"The difference between the almost right word and the right word is... the difference between the lightning bug and the lightning."* - Mark Twain
- **The Onion's whole method in one move:** solo-generate huge volume, then group-vote with a brutal kill-rate (~3% survive). Make too much on purpose; cut hard.
- **Toplyn's engine in one line:** topic -> handles -> associations -> link two *distant* handles -> shortest angle -> backload the surprise.
- **Swartzwelder's trick:** write a fast bad draft so the job becomes rewriting, not writing.

---

### Source anchors (for deeper reading)
- McGraw and Warren, "Benign Violations: Making Immoral Behavior Funny," *Psychological Science*, 2010; the Humor Research Lab (HuRL), CU Boulder.
- Veatch, "A Theory of Humor," *Humor*, 1998.
- Suls, two-stage incongruity-resolution model, in *The Psychology of Humor*, 1972.
- Raskin, *Semantic Mechanisms of Humor*, 1985 (SSTH); Attardo and Raskin, GTVH, 1991 (descriptive, not a tested cognitive theory).
- Greg Dean, *Step by Step to Stand-Up Comedy* (target assumption / connector / reinterpretation).
- John Vorhaus, *The Comic Toolbox* (Rule of Nine; "comedy is truth and pain").
- Judy Carter, *The Comedy Bible*; Stephen Rosenfield, *Mastering Stand-Up*; UCB Comedy Improvisation Manual (the Game).
- Joe Toplyn, *Comedy Writing for Late-Night TV* and the Witscript work (the association algorithm).
- Scott Dikkers (founding Onion editor), *How to Write Funny* (the 11 funny filters; 95%-is-garbage).
- Gorenz and Schwarz on AI humour evaluation; the "ChatGPT recycles 25 jokes" study; "verbalized sampling" as an RLHF mode-collapse fix.
