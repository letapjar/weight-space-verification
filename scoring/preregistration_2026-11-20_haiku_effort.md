# Haiku effort test: question, predictions and scoring

Written 2026-11-20 by the coordinator session from the user's words in conversation, and committed before any
read in this design was made. Marked **[confirmed]** where the user said yes, **[proposed]** where the wording or
number is the coordinator's and the user has not confirmed it. Later changes are added as dated notes, never by
editing the text above them.

## Question [confirmed]

Under the original author's full prompt, is correct identification of the game a matter of reasoning effort for
Haiku?

## Design [confirmed]

- **Reader:** Haiku 5.5, through Claude Code in a clean Docker container (`docker/reads.sh`), no tools, on the
  subscription. Claude Code's own system prompt surrounds the prompt. The work folder holds only `AGENTS.md`,
  which reads "Answer the user's request."
- **Prompt:** `parkfull` (`prompts/parkfull.txt`): the original author's full prompt, word for word as the user
  copied it from GitHub, followed by the weights under the original's own section headings.
- **Effort:** medium, high, extra high. Low is run only if medium gets all 12 of our networks right.
- **Our networks, 36 reads:** the matched set (tanh, 256 copies, 200 million steps), all three seeds of each
  upright game, one read per network per effort. Breakout `93b4f9dc`, `b0399ce0`, `01a9fefe`; Freeway `b804ace8`,
  `99fda910`, `ea037f9c`; Pong `7f68e2c1`, `0a18cdcd`, `6cdd6045`; Pac-Man `fd59a9ae`, `97e6486c`, `040528f5`.
- **The original author's networks, 12 reads:** his four published networks, one read each per effort. Breakout
  `33b62d4f`, Pong `91cd9370`, Freeway `7fbdfec4`, Pac-Man `6d63f32a`. For comparison with others' results
  without the confound of our networks against his. His were trained for a billion steps on his recipe, ours for
  200 million on the faster one; there is one of his per game against three of ours.

## Scoring [confirmed]

The reply's `Game:` line is mapped to games by keyword, as the original experiment did; Frogger counts as
Freeway. Each read falls in exactly one box (`readings.game_line_box`):

| Box | Rule | Example, for a Freeway network |
|---|---|---|
| correct | names the right game and no other of the four | "Freeway", "Frogger", "a Frogger-like road-crossing game" |
| hedged | names the right game and at least one other of the four | "Freeway/Pac-Man", "Frogger or Pong" |
| wrong | names one or more of the four, none of them right | "Pac-Man", "Pong or Breakout" |
| none of the four | names none of the four: another game, a family, no game, or no `Game:` line | "Space Invaders", "a MinAtar-style game", "a grid navigation task" |

A script cannot tell another game ("Space Invaders") from no game ("a grid navigation task"), so those share the
last box, and the report prints each such `Game:` line in full. The split does not touch any threshold.

Only "correct" counts as identified. Hedged reads are reported in their own column, never added to correct and
never folded into wrong. No judge is used.

## Predictions

Two were stated by the user, the second as a revision of the first. They disagree about two games, so both are
recorded and the result can choose between them. **[proposed: recording both as competing predictions; the user
has not said whether he holds one or both.]**

- **Familiarity (the user's first statement):** "at xhigh we see the games with clear/unique signals identified
  but it struggles with pong and pacman because these don't natively exist in minatar so it has no prior."
  MinAtar has Breakout and Freeway and has neither Pong nor Pac-Man (checked against the copy in this repo).
- **Signature (the user's revision):** "the breakout in PAC have well define heat map signatures or well defined
  first layer signatures." Breakout and Pac-Man are identified because their first layers are distinctive: three
  rows of targets with the agent held to one row; a maze of always-on obstacle cells inside the border.

| | Breakout | Freeway | Pong | Pac-Man |
|---|---|---|---|---|
| Familiarity predicts | identified | identified | missed | missed |
| Signature predicts | identified | in between | missed | identified |

Thresholds, on our 36 reads **[proposed]**:

- **Familiarity is supported** if, at extra high, Breakout and Freeway are correct in at least 5 of their 6 reads
  and Pong and Pac-Man in at most 2 of their 6.
- **Signature is supported** if, at extra high, Breakout and Pac-Man are correct in at least 5 of their 6 reads
  and Pong in at most 1 of its 3.
- **Between the two:** over all three efforts, each game has 9 reads. Familiarity predicts Freeway correct more
  often than Pac-Man; signature predicts Pac-Man at least as often as Freeway. A difference of fewer than 3 reads
  is called unclear.
- **A matter of effort:** the number correct out of 12 rises by at least 4 from medium to extra high. A rise of
  fewer than 2 means effort is not what decides it; in between is unclear.
- **His networks against ours:** reported as counts side by side at each effort. No threshold.

## What had been seen when this was written

- With the user's open prompt (weights only, no description) through the API, Haiku at extra high named no game in
  24 reads of four upright networks (`readings/`, the `open` and `scaffold` prompts). Those reads carry a typing
  slip in the prompt and are not for publication.
- Opus and gpt-6-astra reads of the same games under that open prompt, and their marks, are known to the user and
  the coordinator.
- The user has seen Haiku recognise some games with this full prompt in his own earlier trials.
- The original author reported 4 of 4 with this prompt on gpt-6-astra, Pong and Pac-Man included.
- No read in this design had been made.

## Limits to state with any result

- One read per network per effort: a miss cannot be told from an unlucky read.
- If Pong and Pac-Man are missed, that is consistent with familiarity but does not show it; and Pong missed alone
  does not separate the two predictions.
- All networks are upright: this is a baseline for the rotation question, not a test of it.
- These reads go through Claude Code, not the bare API.

## Note, 2026-11-20, added before any read was made: the hypothesis in the user's words

"Given a detailed/leading prompt game identification is effort dependent for Haiku."

This is the claim the question above tests. It is tested by the "a matter of effort" threshold: supported if the
number correct out of 12 on our networks rises by at least 4 from medium to extra high; not supported if it rises
by fewer than 2; unclear in between. The threshold is still the coordinator's proposal.

## Note, 2026-11-20, added before any read was made: the last scoring box is split (the user's point)

The user: Space Invaders is a known MinAtar game and "a grid navigation task" is not, so a reply that names Space
Invaders without saying MinAtar "is still thinking about" MinAtar. The two must not share a box.

MinAtar's five games are Asterix, Breakout, Freeway, Seaquest and Space Invaders (checked against the copy in this
repo). The box "none of the four" above is replaced by two (`readings.game_line_box`):

| Box | Rule | Example |
|---|---|---|
| another MinAtar game | names none of our four, but names Asterix, Seaquest or Space Invaders | "Space Invaders" |
| no game of ours or MinAtar's | everything else: some other game, a family, no game, or no `Game:` line | "Snake", "a grid navigation task" |

"Correct" is unchanged and is still the only box that counts as identified, so no threshold above changes.

**An added measure, for the familiarity prediction** (`readings.answers_with_a_minatar_game`): for each read,
whether the `Game:` line names any MinAtar game (Breakout, Freeway, Asterix, Seaquest, Space Invaders) or the word
MinAtar. Reported for the Pong and Pac-Man networks, 18 reads over the three efforts. If the reader has a MinAtar
prior and no prior for these two games, its answers for them should land on MinAtar games. **[proposed]** Supports
familiarity: 9 or more of the 18. Against it: 4 or fewer. In between: unclear. The Game lines are printed in full
with the count.

## Note, 2026-11-20, added before any read was made: the thresholds are confirmed

The user: "I agree with your thresholds". Every threshold above marked [proposed] is confirmed as written,
including the one for the added MinAtar measure. Still open: whether the two predictions about which games are
identified are both held, or the second replaces the first.

## Note, 2026-11-20, added before any read was made: the user's revised prediction

The user: "my revised prediction is that the games with the strongest first layer signatures should be identified
most consistently and that would speak for break out and Pac Man I think then freeway then Pong".

This is the prediction he holds. It is the "signature" prediction above, now with an order: Breakout and Pac-Man
most consistently, then Freeway, then Pong. His first statement (familiarity: Pong and Pac-Man missed for want of
a MinAtar prior) stays on the record as the alternative the result is compared with; it is no longer his prediction.

How the order is read **[proposed]**: each game has 9 reads on our networks (three seeds, three efforts). Count
the correct ones per game.
- Supported: Breakout and Pac-Man each have at least as many correct as Freeway, Freeway at least as many as Pong,
  and the lower of Breakout and Pac-Man beats Pong by at least 3.
- Against: Pac-Man has fewer correct than Freeway by 3 or more (the familiarity pattern), or Pong is at or above
  both Breakout and Pac-Man.
- Anything else is unclear. All four counts are reported whatever the outcome.
The earlier signature threshold (at extra high, Breakout and Pac-Man correct in at least 5 of 6 and Pong in at most
1 of 3) stands beside this.

## Note, 2026-11-20, added before any read was made: low effort is added (the user's decision)

The user: "Go ahead and add the low effort in here as well". Low is now run for every network, in place of the
rule that it runs only if medium gets all 12 right. Efforts: low, medium, high, extra high.

- Our networks: 12 x 4 = 48 reads. The original author's: 4 x 4 = 16 reads. 64 in all.
- Each game now has 12 reads on our networks, not 9. The order test in the previous note is read on all 12; its
  margins (3 reads) are unchanged.
- The MinAtar measure covers the Pong and Pac-Man networks at all four efforts: 24 reads, not 18. Its marks scale
  with it **[proposed]**: 12 or more supports familiarity, 5 or fewer goes against it.
- The confirmed effort threshold is unchanged: a rise of at least 4 correct out of 12 from medium to extra high.
  The count at low is reported beside it. **[proposed]** If the rise from low to extra high is at least 4 while
  the rise from medium to extra high is not, the result is reported as "effort matters, and medium is already
  enough", not as support for the confirmed threshold.

## Note, 2026-11-20: a check against being right by chance (the user's question; added while the reads were running)

Timing, stated plainly: the 64 reads were launched at 16:43 local time. When this note was written 63 had
finished and one was still running. No reply had been opened by anyone. The coordinator had looked only at the
log's timings and token counts for the low-effort reads (14 to 28 seconds each, 13 of the first 14 with no
thinking tokens).

The user asked whether there is a way to detect a correct answer reached by chance, and said to add "the shuffle
and the table". Both are computed by `haiku_effort_report.py`, written and committed before any reply was opened:

- **The table of answers by true game**, for our 48 reads: for each true game, how many `Game:` lines named
  Breakout alone, Freeway alone, Pong alone, Pac-Man alone, several of the four, another MinAtar game, or none.
  Real identification sits on the diagonal; a favourite answer fills one column whatever the true game is.
- **A shuffle test.** The number correct is recomputed 10,000 times with the true games dealt out at random among
  the replies of the same effort level (fixed random seed 0). The reported figure is the share of shuffles that
  score at least the real number correct. It gives a reader no credit for a favourite answer. Done for the 48
  reads together and for each effort level's 12. A share under 0.05 is called better than chance; with 12 reads
  per level the per-level figures are coarse, and are reported as they come.

Not added: a control read of a file with no real structure (weights shuffled within each layer), which would show
what the prompt alone makes the reader answer. The coordinator suggested it; it is not part of this design.

## Note, 2026-11-20: a matched control on Opus at low effort (the user's request; added before those reads were made)

The user: "as a matched control run one seed of our four games at Opus on low we already know that Opus on High
can get a lot of them".

- Reader: Opus 5.5 at low effort. Everything else as for Haiku: the container, no tools, the `parkfull` prompt.
- Networks: seed 0 of each of our four games, one read each: Breakout `93b4f9dc`, Freeway `b804ace8`, Pong
  `7f68e2c1`, Pac-Man `fd59a9ae`. Four reads.
- Scored by the same boxes. Reported beside Haiku's low-effort row for the same four networks.
- No prediction was stated for it, and it has no threshold. What it is for: to show whether a low effort setting
  holds a stronger reader back in the way it holds Haiku back, or whether Haiku's low-effort result is about Haiku.
- Timing: written when the Haiku reads had finished or were finishing and before any reply, Haiku's or Opus's, had
  been opened. "Opus on High can get a lot of them" refers to the earlier reads under the open prompt.

## Note, 2026-11-20, AFTER the results were opened: a fault in the scoring script, fixed

The script took the game from text on the same line as the word "Game:". Five replies wrote Game as a heading with
the answer on the line below ("**Game**", "**Game:**" or "## Game"), and the script read those as naming no game.
That is a fault in reading the reply, not a ruling about what counts: the fix (`readings.game_answer`) takes the
first line of text under such a heading. It was found by looking at the first report, so it was made with the
results in view; both versions are given so the effect is plain.

| | Before the fix | After |
|---|---|---|
| Our networks, correct | 9 of 48 | 9 of 48 (no cell changed) |
| The original author's networks, correct | 4 of 16 | 6 of 16 (his Freeway at low and at high) |
| MinAtar measure, Pong and Pac-Man | 16 of 24 | 17 of 24 |
| Shuffle share, our 48 | 0.0874 | 0.1118 |
| Shuffle share, extra high | 0.0041 | 0.0088 |

The five reads: `ea037f9c` high (now hedged), `040528f5` extra high (now wrong), `7fbdfec4` low and high (now
correct), `6d63f32a` extra high (now hedged). The first report is kept as `scoring/haiku_effort_report_before_fix.txt`.

## Outcomes, 2026-11-20 (`scoring/haiku_effort_report.txt`, after the fix; nothing above is edited)

All 64 Haiku reads and the 4 Opus control reads finished normally, one turn each, none cut off.

Correct out of 12 on our networks, by effort: low 3, medium 1, high 0, extra high 5. By game, out of 12: Breakout
2, Pac-Man 2, Freeway 4, Pong 1.

- **The hypothesis (identification is effort dependent for Haiku): supported by the confirmed threshold, at its
  edge.** Medium to extra high rises by 4 (1 to 5), which is the threshold. Extra high is the only level better
  than chance by the shuffle test (share 0.0088; low 0.16, medium 0.78, high 1.0; all 48 together 0.11). Against
  reading more into it: the count does not climb steadily (high is 0 of 12), and the 3 correct at low are lines
  that begin "Unknown" or "Unable to determine" and then mention the right game as a guess, which the keyword
  rule counts.
- **The user's prediction of the order (Breakout and Pac-Man, then Freeway, then Pong): not supported.** Freeway
  has the most correct (4), ahead of Breakout and Pac-Man (2 each). By the stated rule it is "unclear" rather than
  "against", because Pac-Man trails Freeway by 2, not 3. At extra high, Breakout and Pac-Man are correct in 2 of 6
  where the signature threshold needed 5: Breakout 2 of 3, Pac-Man 0 of 3.
- **Familiarity (the earlier statement): its extra-high threshold is missed by one** (Breakout and Freeway correct
  in 4 of 6, needing 5; Pong and Pac-Man in 1 of 6, within its limit of 2). Freeway against Pac-Man over all
  efforts is 4 against 2: a difference of 2, "unclear" by the rule, in familiarity's direction.
- **MinAtar measure: 17 of 24, above the mark of 12.** But the table of answers shows why: Freeway or Frogger is
  the favourite answer whatever the network (named alone for 3 of the Pong reads, 5 of the Pac-Man reads and 4 of
  the Freeway reads; Pac-Man is the next most common). So this measure mostly counts one default answer, and
  cannot by itself tell a MinAtar prior from a liking for "Frogger".
- **His networks against ours:** 6 of 16 against 9 of 48 over all efforts; at extra high 3 of 4 against 5 of 12.
  His Freeway was correct at all four efforts, his Pac-Man at none. One network per game on his side.
- **Matched control, Opus at low effort:** 0 of 4. Haiku at low on the same four networks: 1 of 4 (one of the
  "unable to determine" lines). Opus used 638 to 1,266 thinking tokens per read and about half a minute.
- **Thinking tokens by effort (Haiku, 16 reads each):** low, median 0 (14 reads with none); medium, median 2,433
  (6 with none); high, median 15,366; extra high, median 56,429.

A weakness of the scoring rule, seen in these lines: a keyword match counts a game named as a low-confidence guess
or as "the main alternative" the same as a committed answer. The rule was fixed in advance and is applied as
written; every Game line is printed in the report so the reader can see which are which.

## Second test, 2026-11-20: is there a training effect? (written before any of its reads were made)

**Where it comes from.** The user, on seeing the outcomes above: "if it's getting 6 of 16 on park and only nine of
48 on ours that suggests that there might be a training effect We should run our billion step trained networks on
these as well". And: "And the opus low".

**Design.** Our billion-step set (`runs_jax_snapshots`: our games, the original author's own recipe, tanh), all
three seeds of each game, read exactly as in the first test: Haiku 5.5 in the container, no tools, `parkfull`, one
read per network at low, medium, high and extra high. 48 reads. Breakout `9c16e12c`, `665ddc59`, `7044aa52`;
Freeway `ecca4cec`, `b7106b1d`, `d6bafd26`; Pong `e1e80d47`, `b53584f2`, `502fb0db`; Pac-Man `179aa8ca`,
`9af33d14`, `08ed4a7c`. Plus the matched Opus control at low effort on seed 0 of each game (`9c16e12c`,
`ecca4cec`, `e1e80d47`, `179aa8ca`): 4 reads. Scoring as fixed above, with the script as it now stands.

**What it separates.** The original author's networks differ from our matched set in two ways: who built the game,
and the training (a billion steps on his recipe against 200 million on the faster one). This set has our games
and his training.

**Prediction (the user's): there is a training effect.** Our billion-step networks are identified more often than
our 200-million ones.

**Thresholds [proposed by the coordinator; the user has not confirmed them]:** the matched set scored 9 correct of
48. Supported if the billion-step set scores 14 or more of 48. Not supported if 11 or fewer. 12 or 13 is unclear.
Also reported: the count at extra high against the matched set's 5 of 12, and the per-game counts.

**What was known when this was written:** everything in the outcomes above, including that Freeway or Frogger is
Haiku's favourite answer and that four of the original author's six correct reads are his one Freeway network.
No container read of any billion-step network had been made.

## Third test, 2026-11-20: Opus under the same prompt at medium and high (written before any of its reads were made)

**Where it comes from.** The user asked what the earlier API runs showed for Opus at medium and high; they used the
open prompt and judge marking, so they are not comparable. The user: "we need to run the park full on Opus at
medium and high", and "Yeah include the billion step".

**Design.** Opus 5.5 in the container, no tools, `parkfull`, one read per network at medium and at high. Networks:
the twelve of our matched set, the original author's four, and the twelve of our billion-step set (all as listed
above): 28 networks, 56 reads. With the Opus low-effort controls (seed 0 of each game in the matched set and in
the billion-step set) this gives Opus three effort levels on those eight networks. Scoring as fixed above, by the
same script. Extra high is left out: through the API it was cut off in 10 of 15 reads, and Claude Code would
continue a cut-off reply, which makes a different kind of read.

**Prediction.** The user stated none for this test. The coordinator's, recorded as his own and not the user's:
with the full prompt Opus identifies every game at high effort, and the number correct rises from low to medium
to high. Pong is the game most likely to fall short, since no reader named it under the open prompt.

**Thresholds [the coordinator's]:** "identifies every game at high": on the matched set, at least 2 of 3 correct
for each of the four games. "Rises with effort": on the matched set, high has at least 3 more correct of 12 than
medium. Reported for the billion-step set and the original author's networks beside it, with no threshold.

**What was known when this was written:** all the Haiku outcomes above; the four matched-set Opus reads at low (0
of 4); the earlier API reads of Opus under the open prompt and their marks. The Haiku reads of the billion-step
set were running (25 of 48 finished) and none had been opened. No Opus read at medium or high under this prompt
had been made.

## Outcomes of the second and third tests, 2026-11-20 (`scoring/haiku_effort_report.txt`; nothing above is edited)

All 52 reads of the second test and all 56 of the third finished normally, one turn each, none cut off. Scored by
the same script, generalised to both readers and the three sets of networks before any of these replies was
opened; the scoring rule was not touched.

Correct out of 12, by effort (low, medium, high, extra high):

| Reader | Matched set (200 million) | Billion-step set | The original author's (out of 4) |
|---|---|---|---|
| Haiku 5.5 | 3, 1, 0, 5 | 2, 2, 1, 9 | 1, 1, 1, 3 |
| Opus 5.5 | 0 of 4, 10, 12, not run | 0 of 4, 10, 12, not run | not run, 3, 4, not run |

- **Second test, the user's prediction of a training effect: supported by the proposed threshold, at its edge.**
  Haiku scored 14 of 48 on the billion-step set against 9 of 48 on the matched set; the threshold was 14. At extra
  high it is 9 of 12 against 5 of 12. By game on the billion-step set: Breakout 3, Pong 1, Pac-Man 3, Freeway 7,
  of 12 each. Half of the 14 are Freeway, Haiku's favourite answer for any network; leaving Freeway out it is 7 of
  36 against 5 of 36. The shuffle test, which gives no credit for a favourite answer, puts the billion-step set at
  0.0039 over all efforts and under 0.0001 at extra high (matched set: 0.11 and 0.0088).
- **No such effect for Opus:** 22 of 28 on each set, with the same counts at each effort.
- **Haiku's effort dependence shows again on the billion-step set:** medium 2, extra high 9, a rise of 7. As on
  the matched set, low, medium and high are all at chance and only extra high is above it.
- **Third test, the coordinator's prediction that Opus identifies every game at high effort: supported.** 12 of
  12 on the matched set, 12 of 12 on the billion-step set, 4 of 4 on the original author's networks, Pong
  included. Every game is 3 of 3 at high on both of our sets.
- **The coordinator's prediction that Opus rises by at least 3 of 12 from medium to high: not supported.** It
  rises by 2 on both sets (10 to 12), because medium already gets 10. The large step is from low to medium: 0 of
  8 at low, 20 of 24 at medium.
- **Opus does not have Haiku's favourite answer.** Its answers sit on the diagonal of the table; none is hedged,
  and its MinAtar measure is 1 of 14 on each set against Haiku's 17 and 16 of 24.
- **Thinking tokens per read (median):** Haiku low 0, medium 2,277, high 14,313, extra high 60,716. Opus low 797,
  medium 6,109, high 10,862. Opus at medium, with about 6,000 thinking tokens, does what Haiku does not do with
  60,000.

Limits: one read per network per effort throughout; the keyword rule counts a low-confidence mention as an
answer, which flatters Haiku's low-effort rows more than any other; all networks are upright; all reads went
through Claude Code.

## Note, 2026-11-20: whose prompts these are, and a renamed label (the user's correction)

The user: the full prompt "is the MIT preamble", from the original experiment; "the weights only one is from Juho
Park who did his own reproduction at Princeton", and that is not the Turing Institute.

Everything above that says `parkfull` means the MIT preamble. The label is now `mitfull`: the prompt file is
`prompts/mitfull.txt` (the same bytes), and the 176 read folders made under the old label, with the `prompt`
field in their records, were renamed in one pass. No reply, request or result changed. `parkweights` keeps its
name: it is Juho Park's. Where this file says "the original author's networks" it means the MIT experiment's four
published networks; the coordinator had been calling them "Park's" in conversation, wrongly.

## Note, 2026-11-20, after the results: hedging, and how the result is to be written up (the user's ruling)

Looking at the lines counted as hedged, the user: "We're penalizing it for something we didn't tell it was a
penalty It didn't know that hedging was considered a penalty". The prompt asks for the game "as specifically as
you can" and says nothing against naming an alternative. Four of Haiku's hedged Pong lines at extra high give Pong
as the answer and then add "Freeway is the second candidate" or the like.

The user's ruling: "we'll still report the strict rule as the headline since that's the one we stated a-priori but
the write up should mention that since these networks were not given the scoring rubric they had no reason not to
hedge and we note that it named the correct game first in 11 of 12 at extra high".

So:
- **The headline stays the strict rule** stated in advance (`readings.game_line_box`: the right game and no other
  of the four). No number above changes.
- **A secondary count is reported beside it** (`readings.first_game_named`): the right game named first on the
  line, whatever alternatives follow. It was defined after the results were seen and is labelled that way. (The
  readers are the models; "networks" in the user's sentence means them.)
- Haiku, correct out of 12 by effort (low, medium, high, extra high). 200-million set: strict 3, 1, 0, 5; named
  first 3, 1, 1, 7. Billion-step set: strict 2, 2, 1, 9; named first 3, 3, 2, 11. The MIT networks, out of 4:
  strict 1, 1, 1, 3; named first 1, 1, 1, 4. Opus is the same under both counts on every set.
- The secondary count still counts a game named first inside a disclaimer ("Unknown. If forced to guess, ..."),
  which is most of Haiku's score at low effort.

## Fourth test, 2026-11-21: an earlier Opus under the same prompt (written before any of its reads were made)

**The user:** "claude-opus-4-6[1m] as the model and whatever highest effort and let's see what it brings back the
full gammut of networks at 1 billion steps and at 200 million the full prompt I predict it should get about half
of them right at the billion step networks."

**Design.** Claude Opus 4.6 (Claude Code's model id `claude-opus-4-6[1m]`, its long-context form) at `max`, the
highest effort it has, in the container, no tools, the MIT full prompt (`mitfull`), one read per network. Networks:
the twelve of our matched 200-million set and the twelve of our billion-step set, as listed above. 24 reads.
Scored by the same script: the strict rule is the headline, with the right game named first beside it.

**Prediction (the user's):** about half right on the billion-step networks.

**How "about half" is read [the coordinator's wording; not confirmed by the user]:** 4 to 8 of the 12 billion-step
networks correct by the strict rule. 9 or more is "more than half"; 3 or fewer is "fewer than half". The
200-million set is reported beside it; the user stated no prediction for it.

**What was known when this was written:** all the outcomes above, for Haiku 5.5 and Opus 5.5. A one-line probe
("Reply with exactly: OK") had confirmed the container accepts this model at this effort. No read of a network by
this model had been made.

## Fifth test, 2026-11-21: the same, with one line added to the prompt (written before any of its reads were made)

**The user:** "Then I want to try one variation of the prompt. use the full prompt but insert in there the line
'Let's think Layer by Layer.'" He was shown the file and its placement and said: "That's perfect".

**Design.** The fourth test again, with the prompt `mitlayers` (`prompts/mitlayers.txt`): the MIT full prompt with
the line "Let's think Layer by Layer." on a line of its own between the QUESTION paragraph and "Answer in this
order:", and nothing else changed. Same reader (Claude Opus 4.6, `max`), same 24 networks, same container, same
scoring. The coordinator took "the same reader and networks" from the context of the request; the user did not
say it in so many words.

**Prediction:** the user stated none. Reported beside the fourth test, network by network: how many more or fewer
are correct with the added line.

**What was known when this was written:** the fourth test was running and none of its replies had been opened.

## Sixth test, 2026-11-21: Haiku at extra high under the MIT full prompt, through the API (written before any of its reads were made)

**The user:** "Now I want you to run Haiku through the API at Extra high with the corrected full prompt".

**Why.** Haiku named no game in 24 API reads at extra high under the open prompt (weights only), and was correct
in 5 of 12 and 9 of 12 at extra high under the MIT full prompt through Claude Code in the container. Those two
differ in prompt and in route at once. This test changes the route only.

**Design.** Haiku 5.5 at extra high, prompt `mitfull`, sent directly to the API by `run_reads.py`: no system
prompt, no tools, output cap 128,000. The same 28 networks the container read at extra high: our 12 matched
200-million-step networks, our 12 billion-step networks and the MIT experiment's 4. One read each. Same scoring:
the strict rule as the headline, the first-named count beside it. The coordinator chose all 28 so that every
container cell at extra high has its API counterpart; the user did not name the networks.

**Prediction:** the user stated none. Reported beside the container's extra-high counts (strict: 5 of 12 matched,
9 of 12 billion-step, 3 of 4 MIT), network by network.

**What was known when this was written:** every outcome above. No read in this design had been made.

### Fourth test, note of 2026-11-21: stopped after four reads; resumed reads excluded; Opus 4.6 at high first

The `max` queue was stopped at the user's word after four reads (billion-step Breakout seeds 0 to 2 and Freeway
seed 0). In the container Claude Code applied its own output limit of 64,000 tokens to this model. Two of the
four (Breakout seeds 1 and 2) hit it with no reply and were continued by Claude Code with its own "Output token
limit hit. Resume directly..." message; both then answered Freeway. The two one-reply reads answered Breakout
and Freeway, both correct. Four reads do not test the prediction.

**The user's ruling on resumed reads:** "I think we have to throw the resumed reads away because it's breaking
its reasoning". A read that Claude Code continued after the output limit is kept on disk, flagged, and left out
of every count. Checked across all container reads to date: none of the Haiku 5.5 reads and none of the Opus 5.5
effort-test reads was resumed; one pilot read was (Opus 5.5, extra high, open prompt, pasted).

**Next, at the user's word:** "we should test on high before we test on Max ... test one seed of each of the
four games". Opus 4.6 at high, MIT full prompt, seed 0 of each billion-step game: Breakout `9c16e12c`, Freeway
`ecca4cec`, Pong `e1e80d47`, Pac-Man `179aa8ca`. One read each, output limit 128,000 (now set on every container
read). Written before any of these four reads were made. The user stated no prediction for them.

## Seventh test, 2026-11-21: the same networks with the board's cells scrambled (written before any of its reads were made)

**Why.** A line in the Turing Institute note says that with the weights shuffled within each matrix its readers
fell to chance, "so they are reading the weights, not guessing from what they know about the games". That
shuffle destroys what the network does and the picture in its first layer together. Here the 100 cells of the
board are put in a shuffled order (one shuffle, seed 1, for every network) and each network's first-layer
weights moved to match: the network gives the same outputs and the same score, and only the picture is gone.
The user: "what we didn't do is we didn't try the full prompt with the [scrambled] network".

**Networks.** Our twelve matched 200-million-step networks (four games, seeds 0 to 2) and the same twelve
scrambled (`runs_rewired_scrambled/`, rewired, not trained; each scores as its source). 24 networks.

**Prompt.** `mitcells`: the MIT full prompt with the one sentence that says which input is which cell replaced
by "The observation is flattened to 500 numbers, 5 per cell. Input number i = cell * 5 + channel; for example
inputs 0 to 4 are channels 0 to 4 of one cell, inputs 5 to 9 are channels 0 to 4 of some other cell, and so on."
The wording is the user's edit of the coordinator's draft. It says nothing false of either kind of network, and
the same prompt goes to both. (A second wording, `mitanyorder`, adds "The 100 cells may or may not be in
order."; the user: "Let's test the MIT cells first".)

**Reader.** Opus 5.5 at high effort, through Claude Code in the container, no tools, output limit 128,000. One
read per network. Under the unchanged MIT prompt this reader was correct on these twelve upright networks in
12 of 12. Scoring as before: the strict rule as the headline, the first-named count beside it; resumed reads are
not counted.

**Prediction:** the user stated none. Reported as three counts out of 12: upright under `mitfull` (12, known),
upright under `mitcells`, scrambled under `mitcells`.

**What was known when this was written:** every outcome above; under the open prompt in its first wording, the
one scrambled network then existing (Breakout seed 2) was named by no reader in 12 API reads. No read under
`mitcells` had been made.

### Fourth test, second note of 2026-11-21: Opus 4.6 at high, and a last check at max

Opus 4.6 at high, seed 0 of each billion-step game, one reply each: it answered Freeway or Frogger for all four
(1 of 4 correct, the Freeway network).

**The user:** "Clearly 4.6 needs the extra high to get anything beyond just freeway right ... you can try the
4.6 maximum for the other two games Pong and Pac Man give it two of each and let's see if it gets any of that
right if it doesn't get any of that right then we don't need to do anymore Max testing on 4.6".

**Design.** Opus 4.6 at `max`, MIT full prompt, billion-step Pong seeds 0 and 1 (`e1e80d47`, `b53584f2`) and
Pac-Man seeds 0 and 1 (`179aa8ca`, `9af33d14`). One read each, output limit 128,000 (the earlier `max` reads ran
under Claude Code's 64,000). **Stopping rule (the user's):** if none of the four is correct, no more `max`
testing on Opus 4.6. A read continued after the output limit is not counted. Written before any of these reads.

### Seventh test, outcome (2026-11-21)

All 24 reads finished in one reply; none was resumed or cut off. Opus 5.5 at high, strict rule (the first-named
count is the same everywhere):

| Networks | Prompt | Breakout | Freeway | Pong | Pac-Man | All |
|---|---|---|---|---|---|---|
| upright | `mitfull` (earlier test) | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 12 of 12 |
| upright | `mitcells` | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 12 of 12 |
| scrambled | `mitcells` | 3 of 3 | 3 of 3 | 2 of 3 | 3 of 3 | 11 of 12 |

The one miss is scrambled Pong seed 0, answered as Freeway.

**A scoring fault, fixed after these results were seen.** The keyword match did not recognise "Pac-Man" written
with a typographic hyphen (U+2011), so three of these Game lines ("A Pac-Man-style maze game ...") were first
counted as naming no game: before the fix the rows read 10 of 12 and 10 of 12. The fix reads typographic hyphens
and dashes as "-" (`readings.lowered_plain`). Across all 236 countable reads under the MIT prompts it changes
four: these three, and one earlier read (Opus 5.5 at medium, matched Pac-Man seed 1, now correct, making that
cell 11 of 12 where 10 of 12 was reported). No Haiku or Opus 4.6 count changes.

**Limits.** One read per network. The rule counts any Game line that names the right game and no other: the
upright `mitcells` line for Pac-Man seed 1 reads "An open-arena collect-and-dodge game. It is like Pac-Man with
no maze" and counts as correct.

### Seventh test, second reader (2026-11-21; written before any of these reads were made)

**The user:** "I do think we need to test Haiku Extra High at least on the version 1 shuffle if opus high can do
it haiku xhigh might be able to as well". ("Version 1" is the shuffle already tested: whole cells moved, each
cell's five channels kept together.)

**Design.** Haiku 5.5 at extra high, prompt `mitcells`, sent directly to the API (no system prompt, no tools,
output cap 128,000, no fallback model), on the same 24 networks as Opus: our twelve matched networks upright and
the same twelve with cells scrambled. One read each. Same scoring. A read the provider's filter refuses, or one
cut off at the output cap, is not counted. The coordinator chose the API route (through it Haiku named 9 of 11
of these upright networks under the unchanged MIT prompt) and added the upright twelve so both rows share the
`mitcells` wording; the user asked for the shuffled ones.

**Prediction (the user's):** Haiku at extra high might be able to read the cells-scrambled networks, as Opus at
high did (11 of 12). No number was given.

## Eighth test, 2026-11-21: all 500 inputs shuffled (written before any of its reads were made)

**Why.** In the seventh test whole cells moved and each cell's five channels stayed together, so the position of
an input still said which channel it was (input number modulo 5), and the count of strong cells per channel
survived. The user: "in our scramble the mod 5 nature of the relationships is still preserved right? is that too
much of a giveaway". A reader could name the game from those counts without following the network. Here every
input moves on its own (`runs_rewired_inputs_shuffled/`, one shuffle, seed 1, for all twelve networks; rewired,
not trained; each gives the same outputs as its source and scores as it does). Nothing in the order of the
inputs says which input is which cell or channel; what the network computes is unchanged. (A step between the
two, shuffling the order of the five channels, was dropped at the user's word: "you're not changing anything
except where to look".)

**Networks.** Our twelve matched networks in three orders: upright, cells scrambled, all inputs shuffled. 36.

**Prompt.** `mitunordered`: the MIT full prompt with two sentences changed, both approved by the user ("Yeah I
guess that wording works"). The observation sentence reads "The observation is flattened to 500 numbers: one for
each channel of each cell. Which input is which cell and channel is not given." In the answer format, "for each
input channel, where in the grid its weights are large or show structure" reads "which inputs have large weights
or show structure". Nothing in it is false of any of the three orders, and the same prompt goes to all.

**Reader.** Opus 5.5 at high, Claude Code in the container, no tools, output limit 128,000, one read per
network. Scoring as before; resumed reads are not counted.

**Prediction:** the user stated none. The coordinator's, recorded as his own: Opus still names the upright and
cells-scrambled networks (at least 10 of 12 each), and falls well short on the fully shuffled ones (6 of 12 or
fewer), because the per-channel counts are gone. Reported as three counts out of 12.

**What was known when this was written:** the seventh test's outcome for Opus (12, 12 and 11 of 12). The Haiku
reads of the seventh test were running and unopened. No read under `mitunordered` had been made.

**The user's prediction for the eighth test (2026-11-21), made blind.** No reply in this test had been opened,
scored or described by anyone when it was given: "my prediction is that opus falls [to] chance on the fully
scrambled if it is Reading pictures or relying on the periodicity that we supplied if it actually does the work
to find channels then it probably read them ... so yeah I guess I'd agree with your six out of 12". Read as: at
or near chance on the fully shuffled networks if Opus relies on the picture or on the grouping by fives; better
than that only if it works out the channels from the weights itself. The user accepts 6 of 12 or fewer as the
mark for "falls short". Chance for four games is 3 of 12.

## Ninth test, 2026-11-21: the same networks with the board turned (written before any of its reads were made)

**Networks.** Our twelve matched networks rewired for a board turned 90 degrees
(`runs_rewired_matched_90/`) and 180 degrees (`runs_rewired_matched_180/`, with Breakout seed 2 from
`runs_rewired_180/`): 24 networks, each the same network as its upright source, giving the same outputs and
score. On a turned board the actions keep their directions on the screen, so the MIT prompt is true of these
networks as written.

**Prompt and reader.** `mitfull`, unchanged. Opus 5.5 at high, Claude Code in the container, no tools, output
limit 128,000, one read per network. Scoring as before. Upright under the same prompt and reader: 12 of 12.

**Prediction (the user's, in his words; no read of this test had been made or seen).** "for games that have an
unambiguous signatures such as agent only in one row or column When given the full definition of what all the
channels mean Opus should be able to figure things out regardless of orientation it may have trouble with things
like freeway or pong versus breakout when Pong is rotated 90 degrees that can look like breakout so that the
interesting one is the ones [where] a rotation on one becomes similar to the [upright] version of another".

(An earlier remark of his, "I'm going to be flabbergasted if it's able to recognize the upright games even when
they're scrambled but not recognize the rotated games", was first written here as the prediction. He corrected
that: the prediction is the paragraph above.)

**The user's addition, on Pac-Man (before any read of this test):** "it may not be able to recognize a turned Pac
Man at all It may just call them all Pac Man". That is: turned Pac-Man networks are named Pac-Man, and the reply
does not notice the turn. Checked from the weights: the maze is the same after a quarter turn, a half turn and
either mirror (the cells the agent never enters are in the same places in the upright, turned-90 and turned-180
networks), so the layout gives a reader no sign of a turn. Naming the game is what is scored; whether each reply
remarks on an orientation is reported beside it, for every game.

**How it is read [the coordinator's wording].** Turned networks are named correctly in general. The misses, where
there are any, fall on the cases where one game turned looks like another game upright, and the wrong answer is
that other game: Pong turned 90 degrees (the paddle moves along a row, as in Breakout) answered as Breakout;
Breakout turned 90 degrees (the paddle moves along a column, as in Pong and as the agent does in Freeway)
answered as Pong or Freeway; Freeway and Pong taken for each other. Pac-Man, whose maze is symmetric, is
unaffected. Reported per game and turn, with every wrong answer listed beside the game it resembles.

**What had been seen when this was written:** the seventh test's outcome, and one network of this design: the
pilot's read of Breakout seed 2 turned 180 degrees under this prompt at high was correct (it is the 24th read
of this test and is not repeated). No other read of a turned matched network under `mitfull` had been made.

### Seventh test, second reader, outcome (2026-11-21)

Haiku 5.5 at extra high through the API, prompt `mitcells`, strict rule (first-named count the same):

| Networks | Breakout | Freeway | Pong | Pac-Man | All |
|---|---|---|---|---|---|
| upright | 2 of 3 | 2 of 2 | 3 of 3 | 2 of 3 | 9 of 11 |
| cells scrambled | 1 of 3 | 1 of 2 | 0 of 3 | 0 of 3 | 2 of 11 |

One read in each row was refused by the provider's filter and is not counted (upright Freeway seed 1, scrambled
Freeway seed 2); a second read of each was sent afterwards. Beside Opus 5.5 at high on the same networks and
prompt: 12 of 12 upright, 11 of 12 scrambled. The user's prediction, that Haiku at extra high might read the
scrambled networks as Opus did, is not borne out: 2 of 11 is at about chance for four games.

### Eighth test, outcome (2026-11-21)

Opus 5.5 at high, prompt `mitunordered`, all 36 reads finished in one reply, none resumed. Strict rule
(first-named count the same):

| Order of the inputs | Breakout | Freeway | Pong | Pac-Man | All |
|---|---|---|---|---|---|
| upright | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 12 of 12 |
| cells scrambled | 3 of 3 | 3 of 3 | 2 of 3 | 3 of 3 | 11 of 12 |
| all 500 inputs shuffled | 2 of 3 | 3 of 3 | 1 of 3 | 2 of 3 | 8 of 12 |

Against the predictions: both the coordinator and the user put "falls short" at 6 of 12 or fewer, with chance at
3. The result is 8 of 12: above that mark, below the other two rows. By the user's own statement of the
alternatives, this is the case where the reader "actually does the work to find channels". The four misses on
the fully shuffled networks: Breakout seed 0 as Catch, Pong seeds 1 and 2 as Freeway/Frogger, Pac-Man seed 0 as
Snake.

### Ninth test, outcome (2026-11-21)

Opus 5.5 at high, unchanged MIT prompt, the twelve matched networks turned. All 23 new reads finished in one
reply, none resumed; the 24th is the pilot's.

| Board | Breakout | Freeway | Pong | Pac-Man | Strict | Right game named first |
|---|---|---|---|---|---|---|
| upright (earlier test) | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 12 of 12 | 12 of 12 |
| turned 90 | 3 of 3 | 3 of 3 | 1 of 3 | 3 of 3 | 10 of 12 | 12 of 12 |
| turned 180 | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 12 of 12 | 12 of 12 |

The only two lines not counted correct by the strict rule are Pong turned 90, seeds 0 and 2: "A Pong/Breakout-style
paddle-and-ball game (single-player Pong against the top wall; Breakout without bricks)" and "A single-player
Pong-style paddle-and-ball game, similar to Pong or squash, or Breakout without bricks". Both name Pong first and
Breakout beside it.

**Against the user's prediction.** Borne out in each part. Turned networks were named regardless of orientation.
The only trouble fell on the look-alike he named, Pong turned 90 degrees, and the other game on those lines is
Breakout. Every turned Breakout and Freeway reply states the orientation ("rotated sideways", "the paddle
along the top row", "flipped so the agent crosses from top to bottom"); every turned Pong reply places the
paddle correctly (bottom row at 90, right column at 180). On Pac-Man: all six turned networks were named
Pac-Man and none of the six Game lines mentions a turn, as he predicted.

### Seventh test, second reader: the two second reads

The second reads of the two networks whose first read was refused were both countable and both correct (upright
Freeway seed 1: "Freeway"; scrambled Freeway seed 2: "Frogger/Freeway-style lane crossing ... a low-confidence
match"). With them Haiku's rows are 10 of 12 upright and 3 of 12 cells scrambled.

## Tenth test, 2026-11-21: "Let's think Layer by Layer." for Haiku on the cells-scrambled networks (written before any of its reads were made)

**The user:** "I think the let's think layer by layer would only help potentially haiku in the scramble ...
let's take one set of the scrambled haiku and do the think layer by layer prompt".

**Design.** Haiku 5.5 at extra high through the API (no system prompt, no tools, output cap 128,000, no
fallback), on our twelve matched networks with cells scrambled, one read each. Prompt `mitcellslayers`: the
`mitcells` prompt with the line "Let's think Layer by Layer." on a line of its own between the QUESTION
paragraph and "Answer in this order:", exactly where the approved `mitlayers` prompt has it, and nothing else
changed. Compared network by network with the same reader on the same networks under `mitcells`: 3 of 12 (2 of
11 first reads, and a second read of the network whose first was refused).

**Prediction (the user's):** the added line might help Haiku on the scrambled networks; he expects it to help
nowhere else. No number was given.

## Eleventh test, 2026-11-21: a second provider (written before any of its reads were made)

**The user:** "start filling in the Astra high effort results as well ... upright rotated and scrambled both ways
just so that we're not looking like we're only using one provider".

**Design.** `gpt-6-astra` at high effort through the API (no system prompt, no tools, default verbosity, output
cap 128,000), one read per network, on the same six rows Opus 5.5 has: under `mitfull`, the networks upright,
turned 90 degrees and turned 180 degrees; under `mitunordered`, the networks upright, with cells scrambled and
with all 500 inputs shuffled. To start, seed 0 of each of the four matched games: 24 reads. The other two seeds
fill the same rows later. Scoring as before.

**Prediction (the user's):** "I expect that Astra should be on par with Opus 5.5 I don't have any a priori
reason to suspect that it does better or worse ... depending on whether or not it gets into what the weights
actually do on the scramble That may be the one set where we'll see a difference but the difference wouldn't be
significant unless it was like three out of twelve 4 out of 12 as opposed to opus eight out of 12".
Read as: on par with Opus on every row; if a difference appears it is on the fully shuffled row, and it counts
as a difference only if Astra is at about 3 or 4 of 12 where Opus is at 8 of 12. With seed 0 alone each row has
four networks, so that mark can be judged only when all three seeds are in.

**Opus 5.5 at high on these 24 networks (seed 0), for comparison:** upright 4 of 4 under both prompts, turned 90
3 of 4 strict (Pong hedged with Breakout), turned 180 4 of 4, cells scrambled 4 of 4, all inputs shuffled 2 of 4.

### Tenth test, outcome (2026-11-21)

Eleven of the twelve reads were refused by the provider's filter (category `reasoning_extraction`), each
mid-thought after 3,900 to 30,000 output tokens with no visible reply. The one countable read answered Asterix
for a Pac-Man network. The test cannot be scored: 0 of 1 countable, against 3 of 12 without the line. Without
the line the same prompt on the same networks was refused once in twelve.

### Eleventh test, outcome for seed 0 (2026-11-21)

`gpt-6-astra` at high, one read per network, all 24 completed normally. Strict rule (first-named the same):

| Board | Prompt | gpt-6-astra | Opus 5.5 at high, same networks |
|---|---|---|---|
| upright | `mitfull` | 4 of 4 | 4 of 4 |
| turned 90 | `mitfull` | 4 of 4 | 3 of 4 (Pong hedged with Breakout) |
| turned 180 | `mitfull` | 4 of 4 | 4 of 4 |
| upright | `mitunordered` | 4 of 4 | 4 of 4 |
| cells scrambled | `mitunordered` | 4 of 4 | 4 of 4 |
| all 500 inputs shuffled | `mitunordered` | 4 of 4 | 2 of 4 |

Against the user's prediction (on par with Opus; any difference on the fully shuffled row): on par on every row,
and on the fully shuffled row Astra is ahead on these four networks, not behind. Four networks per row; the mark
he set needs all three seeds.

### Eighth test, repeats (2026-11-21; written before any of these reads were made)

At the user's word ("go ahead and do the triplicates for Opus"): two more reads of each of the twelve
cells-scrambled and twelve fully shuffled networks, Opus 5.5 at high under `mitunordered`, same container
settings, to make three reads per network. 48 reads. Reported per network as correct out of 3, and per row as
correct out of 36, beside the first reads (11 of 12 and 8 of 12). No new prediction was stated.

### Eleventh test, outcome for all three seeds (2026-11-21)

`gpt-6-astra` at high, one read per network, all 72 completed normally; no line was hedged.

| Board | Prompt | gpt-6-astra | Opus 5.5 at high (first reads) |
|---|---|---|---|
| upright | `mitfull` | 12 of 12 | 12 of 12 |
| turned 90 | `mitfull` | 12 of 12 | 10 of 12 (two Pong hedged with Breakout) |
| turned 180 | `mitfull` | 12 of 12 | 12 of 12 |
| upright | `mitunordered` | 12 of 12 | 12 of 12 |
| cells scrambled | `mitunordered` | 12 of 12 | 11 of 12 |
| all 500 inputs shuffled | `mitunordered` | 12 of 12 | 8 of 12 |

Against the user's prediction: on par with Opus on five rows. On the fully shuffled row the two differ, with
Astra ahead (12 of 12 against 8 of 12), the reverse of the direction he thought possible; by the mark he set
(a gap like 3 or 4 of 12 against 8) a gap of four is of that size.

### Eighth test, repeats: outcome (2026-11-21)

Opus 5.5 at high under `mitunordered`, three reads per network, all 72 in one reply, none resumed.

| Order of the inputs | Breakout | Freeway | Pong | Pac-Man | All | First reads alone |
|---|---|---|---|---|---|---|
| cells scrambled | 9 of 9 | 9 of 9 | 7 of 9 | 9 of 9 | 34 of 36 | 11 of 12 |
| all 500 inputs shuffled | 8 of 9 | 9 of 9 | 2 of 9 | 5 of 9 | 24 of 36 | 8 of 12 |

Both first-read rates hold (0.94 against 0.92; 0.67 against 0.67). On the fully shuffled networks the misses are
by game, not by network: Freeway is never missed and Breakout once; Pong is named in 2 of 9 and answered as
Freeway or Frogger in 6 of the 7 misses (Breakout in the other); Pac-Man is named in 5 of 9 and answered as
Snake or an unnamed collect-the-target game otherwise.

## Twelfth test, 2026-11-21: the network trained on all four games (written before any of its reads were made)

**The user:** "I want you to send the billion step one".

**Network.** `218d97e7`: seed 0 of the network trained on all four games at once for a billion steps
(`runs_jax_all4_c256_lr_0.005_1b/`), the best of its three seeds.

**Prompt.** `mitplay`: the MIT full prompt with three sentences changed so that it does not assume one game, the
wording worked out with the user and approved by him: "to maximise reward in play on this grid"; "What was it
taught to play?"; and the answer line "Played: <what it was taught to play, as specifically as you can; name
anything well known that it resembles>". It does not say whether there is one game or several.

**Reader.** Opus 5.5 at high, Claude Code in the container, no tools, output limit 128,000. Three reads.

**What is reported, per read:** which of the four games the Played answer names; whether the reply says the
network plays more than one game; any other game it names. No single number is fixed in advance as "correct".

**Prediction:** the user stated none. Under the open prompt in its first wording, the 200-million-step four-game
network was named by no reader in six API reads, and none said it was several tasks.

**Not run:** the single-game networks under this prompt. The user: "I think we already have the reads on the
billion step individual games" (under `mitfull`, Opus named 12 of 12). So a difference between this prompt and
`mitfull` on single-game networks is not measured.

## Thirteenth test, 2026-11-21: smaller OpenAI models, and Haiku on the remaining rows

**Luna and Terra, upright (reported as run; no prediction was recorded before them).** On seed 0 of each
upright game under `mitfull` at extra high: `gpt-6-luna` named 1 of 4, with default verbosity and again with
high verbosity (the same four answers); `gpt-6.1-terra` named 4 of 4.

**Terra, all three seeds, at extra high, one read per network, all completed normally:**

| Board | Prompt | Breakout | Freeway | Pong | Pac-Man | All |
|---|---|---|---|---|---|---|
| upright | `mitfull` | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 12 of 12 |
| upright | `mitunordered` | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | 12 of 12 |
| cells scrambled | `mitunordered` | 3 of 3 | 3 of 3 | 3 of 3 | 2 of 3 | 11 of 12 |

The user's rule: "do the scramble reads and then if the scramble reads succeed then do total input scramble".
11 of 12 succeeds; the twelve fully shuffled networks follow under `mitunordered`.

**Haiku 5.5 at extra high through the API, the remaining rows (written before any of these reads were made).**
The twelve matched networks turned 180 degrees and turned 90 degrees under `mitfull`, and with all 500 inputs
shuffled under `mitunordered`; one read each, 36 reads. The user chose both turns: the half turn is the same
picture upside down with nothing in it resembling another game; the quarter turn also makes Pong and Breakout
resemble each other. Pac-Man's maze is the same at any turn.

**Prediction (the user's):** "haiku is reading pictures not weights per se and therefore turning [them] makes
them unfamiliar enough"; "I really don't expect it to do well on the turn boards or especially on the 500 inputs
that should definitely read as chance". Chance for four games is 3 of 12.

**Terra on the fully shuffled networks (2026-11-21):** 8 of 12 (Breakout 2 of 3, Freeway 3 of 3, Pong 3 of 3,
Pac-Man 0 of 3). The misses: one Breakout hedged as "a Pong-like paddle-and-ball game, though Breakout ... also
fits"; all three Pac-Man networks answered as Snake, each marked tentative. Opus 5.5 at high on the same row:
8 of 12 on first reads (24 of 36 over three), missing mostly Pong; `gpt-6-astra` at high: 12 of 12.

## Fourteenth test, 2026-11-21: Sonnet, and one rung of less help (written before any of these reads were made)

Both through Claude Code in the container, no tools, output limit 128,000, one read per network, scored as before.

**Sonnet 5.5 at high, prompt `mitunordered`,** on our twelve matched networks upright, with cells scrambled and
with all 500 inputs shuffled: 36 reads. **Prediction (the user's):** "it makes me think that Sonnet would
probably perform well [on] the scrambled test".

**Opus 5.5 at high, prompt `parkweights`** (Juho Park's weights-only preamble: the network's shape and
activations, "What was this network trained to do?", a required answer order with a `Task:` line; no grid, no
channels, no actions, no statement that it plays a game; then the weights under our neutral headings, since what
his own prompt puts there is not known to us), on the twelve networks upright and with cells scrambled: 24
reads. The `Task:` line is scored by the same rule as the `Game:` line. The user's purpose: "so that when we
write it up we can say that it's reading the weights but how much help is it getting from the prompt". No
number was predicted.

**Haiku's remaining rows, outcome (2026-11-21).** Haiku 5.5 at extra high through the API, one read per network.
Seven of the 36 reads were refused by the provider's filter (`reasoning_extraction`) and are not counted: two at
180 degrees, four at 90 degrees, one fully shuffled. A second read of each was sent afterwards.

| Board | Prompt | Breakout | Freeway | Pong | Pac-Man | All (first reads) |
|---|---|---|---|---|---|---|
| turned 180 | `mitfull` | 3 of 3 | 2 of 2 | 3 of 3 | 1 of 2 | 9 of 10 |
| turned 90 | `mitfull` | 1 of 2 | 1 of 1 | 0 of 3 | 1 of 2 | 3 of 8 |
| all 500 inputs shuffled | `mitunordered` | 0 of 3 | 2 of 3 | 0 of 3 | 0 of 2 | 2 of 11 |

Against the user's prediction (Haiku reads pictures; poor on turned boards; chance when fully shuffled):
- Fully shuffled: borne out, 2 of 11.
- Turned 180: not borne out. 9 of 10, with the orientation stated ("the paddle on the top playable row", "the
  paddle is on the right edge"). The same picture upside down did not stop Haiku.
- Turned 90: borne out, and the wrong answers are look-alikes. All three turned Pong networks were answered as a
  catching game with "a paddle on the bottom row" (Catch, Kaboom!); one turned Breakout as Freeway ("the chicken
  is fixed in one column and moves up and down"); one Pac-Man as Freeway.

**Haiku's remaining rows with the second reads (2026-11-21).** Of the seven second reads, five were countable and
two were refused again (Freeway seed 0 at 180 degrees, Breakout seed 2 at 90 degrees). Taking each network's
first countable read: turned 180, 10 of 11; turned 90, 6 of 11 (Breakout 1 of 2, Freeway 3 of 3, Pong 0 of 3,
Pac-Man 2 of 3); all inputs shuffled, 2 of 12. Nine of 43 reads in these rows were refused.

## Fifteenth test, 2026-11-21: which part of a network the answer comes from (written before any of its reads were made)

**Why.** The readers' own accounts of the shuffled networks are mostly about the first layer: which inputs copy
the bias, which were never used, how many are strong. The user proposed leaving the second hidden layer out; he
then noted that withholding it forces the reader to use the rest, so it can show only that the rest is enough.
This test instead gives the reader a whole file whose parts disagree.

**Networks.** Four mixed files (`runs_mixed_layers/`, `experiments/mix_layers.py`): the first layer (W1, b1) of
one seed-0 matched network and the later layers (W2, b2, W3, b3) of another game's, every number unchanged:
Breakout first layer on Pong's later layers (`5df3d4e0`), Pong on Freeway's (`410b5a6f`), Freeway on Pac-Man's
(`cf39f3f0`), Pac-Man on Breakout's (`5336e436`). Such a network was never trained as a whole and has not been
played. Beside them, the four ordinary seed-0 networks under the same prompt.

**Prompt.** `mitweightsplay`: the MIT full prompt with three sentences changed so that it says the weights were
trained, not that one network was, the wording worked out with the user: "The weights were trained with
reinforcement learning (PPO) to maximise reward in play on this grid."; "The weights below were trained with
reinforcement learning to play on this grid. What were they trained to play?"; "Played: <what they were trained
to play, as specifically as you can; name anything well known that it resembles>". It is true of both kinds of
file and does not say how many networks the weights come from.

**Readers.** Opus 5.5 at high (container, no tools), then `gpt-6.1-terra` at extra high (API), at the user's
word. Three reads of each mixed file and one of each ordinary network, per reader: 16 reads each.

**What is reported, per read of a mixed file:** whether the Played answer names the first layer's game, the later
layers' game, both, or neither, and whether the reply says the parts do not belong together.

**Prediction:** the user stated none. The coordinator's, as his own: the answer follows the first layer's game in
most reads, and few or none remark that the layers do not fit.

### Fourteenth test, outcome (2026-11-21)

All 60 reads finished in one reply; none resumed.

**Sonnet 5.5 at high, `mitunordered`:**

| Order of the inputs | Breakout | Freeway | Pong | Pac-Man | All |
|---|---|---|---|---|---|
| upright | 3 of 3 | 3 of 3 | 1 of 3 | 3 of 3 | 10 of 12 |
| cells scrambled | 3 of 3 | 1 of 3 | 1 of 3 | 1 of 3 | 6 of 12 (right game first in 7) |
| all 500 inputs shuffled | 3 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | 9 of 12 |

Against the user's prediction (Sonnet would probably do well on the scrambled test): partly. It names 6 of 12
with cells scrambled and 9 of 12 fully shuffled, well above Haiku (3 of 12 and 2 of 12) and below Opus. Pong is
missed in 7 of 9 reads across the three rows, upright included. The fully shuffled row is above the
cells-scrambled row; with one read per network that order should not be leaned on.

**Opus 5.5 at high, `parkweights`** (no grid, channels, actions or mention of a game given), `Task:` line:

| Order of the inputs | Breakout | Freeway | Pong | Pac-Man | All |
|---|---|---|---|---|---|
| upright | 3 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | 9 of 12 (right game first in 10) |
| cells scrambled | 0 of 3 | 0 of 3 | 0 of 3 | 0 of 3 | 0 of 12 |

With the description (`mitunordered`) the same reader named 12 of 12 upright and 34 of 36 cells scrambled. Without
it, upright networks are still mostly named, and scrambled ones never are. The scrambled replies do recover the
form of the input ("a 10x10 gridworld", "5 channels per cell", "a border of walls around an 8x8 interior") and
call the network a policy or value network for a gridworld; none names a game.

### Fifteenth test, outcome (2026-11-21)

Three reads of each of the four mixed files per reader; all 24 completed in one reply. What the Played answer
named:

| Reader | First layer's game only | First layer's game with another | Later layers' game | Neither |
|---|---|---|---|---|
| Opus 5.5 at high | 9 of 12 | 2 of 12 (Pong first layer: "Pong ... Breakout without bricks") | 0 of 12 | 1 of 12 (Breakout first layer, answered Catch) |
| gpt-6.1-terra at extra high | 11 of 12 | 0 | 0 of 12 | 1 of 12 (Pong first layer, "a grid obstacle-navigation or avoidance game") |

No reply of the 24 names the later layers' game, and none says the layers do not belong together. The replies do
look at the output layer and report what is there: for Pac-Man's first layer on Breakout's later layers, Opus
writes "Left and right get the largest W3 weights" and "Up and down have smaller but non-trivial ... weights",
and still answers Pac-Man. Under the same prompt Opus named each of the four ordinary networks correctly.

The coordinator's prediction (the answer follows the first layer; few or none remark on the mismatch) is borne
out. What this shows: with this prompt, the game a reader names is the game of the first layer, whatever the
rest of the network computes.

**Fifteenth test: the mixed networks played (2026-11-21).** At the user's word ("score them on their first
layer and on their second layer game ... let's just see what the scores are"), each mixed network was played at
both of its games, 1,280 games each (`experiments/play_mixed.py`), beside the whole network trained on that game
and uniformly random play:

| First layer from | Later layers from | At the first layer's game: mixed / trained / random | At the later layers' game: mixed / trained / random |
|---|---|---|---|
| Breakout | Pong | 0.61 / 22.81 / 0.13 | -0.33 / 4.98 / -1.10 |
| Pong | Freeway | -0.54 / 4.98 / -1.10 | 1.47 / 23.86 / 0.02 |
| Freeway | Pac-Man | 0.00 / 23.86 / 0.02 | 1.86 / 42.63 / 4.05 |
| Pac-Man | Breakout | 2.81 / 42.63 / 4.05 | 0.78 / 22.81 / 0.13 |

No mixed network plays either of its games: every score is at the level of random play. So in 22 of 24 reads
the readers named a game that the network they were shown does not play. Terra's four ordinary networks under
the same prompt were all named correctly.

**Turned Pong under Breakout, played (2026-11-21).** The user's refinement: Pong on a board turned a quarter turn
moves its paddle left and right along the bottom row, as Breakout does, so its later layers use Breakout's
actions. Breakout's first layer on turned Pong's later layers, same seed, at Breakout, 1,280 games each
(`experiments/play_turned_pong_under_breakout.py`); random play scores 0.13:

| Seed | Whole Breakout network | Whole turned Pong at Breakout: rewired / trained | Breakout's first layer on turned Pong's later layers: rewired / trained |
|---|---|---|---|
| 0 | 22.81 | 13.50 / 19.90 | -0.23 / -0.58 |
| 1 | 22.62 | 20.05 / 14.29 | -0.54 / -0.47 |
| 2 | 23.37 | 18.74 / 19.94 | -0.51 / 1.60 |

A turned-Pong network, whole, plays Breakout at 13 to 20 without ever having seen it. The same later layers
under a Breakout network's first layer play at the level of random. The join between two networks is what
fails, not the actions.

**The reverse pairing, played (2026-11-21).** Turned Pong's first layer on Breakout's later layers, same seed,
1,280 games each (`experiments/play_turned_pong_over_breakout.py`). At Breakout: -0.62 to 2.81 across the six
pairings (random 0.13, a Breakout network 22.6 to 23.4). At turned Pong: -1.84 to -0.58 (random -1.13, a
turned-Pong network 4.97 to 4.99). A whole Breakout network at turned Pong scores -1.10, -0.65 and -1.07 over
the three seeds, at the level of random: the transfer is one way, as the earlier work on turned boards found.

**Swapped seeds within one game, played (2026-11-21).** At the user's question ("what if we swapped seeds so it's
still breakout but it's seed zero's top versus seed one's other layers"): one seed's first layer on another
seed's later layers, same game, every ordered pair of the three seeds, 1,280 games each
(`experiments/play_swapped_seeds.py`).

| Game | Whole networks | The six swapped pairings | Random |
|---|---|---|---|
| Breakout | 22.6 to 23.4 | -0.55 to -0.04 | 0.13 |
| Pong | 4.98 to 4.99 | -2.14 to -0.27 | -1.10 |
| Freeway | 23.7 to 23.9 | 0.00 to 0.60 | 0.02 |
| Pac-Man | 37.7 to 44.2 | -0.18 to 5.29 | 4.05 |

All 24 pairings play at the level of random. The join fails between two networks trained on the same game, so
the cross-game failures above say nothing about the games: a first layer works only with the later layers it
was trained beside.

## Sixteenth test, 2026-11-21: the same files with their blocks in reverse order (written before any of its reads were made)

**The user:** "what if we reordered the way the weights are presented in other words start with the output layer
and go backwards to the input layer does it still read the input layer only because I'm thinking of the
attention mechanism and how things that are at the earlier part of the prompt compared to things in the middle
compared to things at the bottom [affect] what gets paid attention to".

**Why.** In every file read so far the first layer comes first and is 93% of the numbers. On the mixed networks
the answer followed the first layer; that could be for what it holds, for coming first, or for its bulk. This
changes only the order.

**Files.** The four mixed networks and the four ordinary seed-0 networks, each with its six blocks in reverse
order: W3, b3, W2, b2, W1, b1 (`experiments/reverse_blocks.py`). Made as files, at the user's suggestion ("Why
don't we just create files with the blocks already reversed"), so the runner and the prompt are untouched. The
same lines, in the other order: `fce7ef81`, `ff4d6cc5`, `b98c6276`, `84fde3ec` (mixed: Breakout-Pong,
Pong-Freeway, Freeway-Pac-Man, Pac-Man-Breakout) and `aa7f0332`, `ba64146a`, `e7e107b8`, `bce0ac6b` (Breakout,
Pong, Freeway, Pac-Man).

**Prompt and reader.** `mitweightsplay`, unchanged; nothing in it says what order the blocks come in. Opus 5.5
at high, container, no tools; three reads of each mixed file, one of each ordinary network: 16 reads.

**Compared with** the fifteenth test, same reader and prompt, blocks in the usual order: first layer's game in
11 of 12 reads (9 alone, 2 with another beside it), later layers' game in 0, and the four ordinary networks all
named.

**Prediction:** the user stated none; his question is whether position decides what is read. The coordinator's,
as his own: the answer still follows the first layer's game. The bulk of the first layer is not changed by this.

**The user's prediction for the sixteenth test (2026-11-21), made blind: no reply in this test had been opened,
scored or described by anyone.** "I think that it is still going to get working networks correct It is still
going to guess the W1 for the mixed network because that's so much of the file percentage wise But this may give
it a chance to notice that things don't make sense". In three parts: the four ordinary networks are still named;
on the mixed networks the answer still follows the first layer's game, because of its share of the file; and
with the output layer first, some replies may remark that the parts do not fit.

### Sixteenth test, outcome (2026-11-21)

All 16 reads finished in one reply. With the blocks in reverse order (output layer first, first layer last):

| | First layer's game only | First layer's game with another beside it | Later layers' game | Neither |
|---|---|---|---|---|
| Blocks reversed | 10 of 12 | 2 of 12 (Pong's first layer: "Pong ... Breakout") | 0 of 12 | 0 |
| Usual order (fifteenth test) | 9 of 12 | 2 of 12 | 0 of 12 | 1 of 12 |

The four ordinary networks with blocks reversed were all named (Pong with Breakout beside it). Stated confidence
on the mixed files is 55 to 85%, much as on the ordinary ones (55 to 75%). No reply says that the layers do not
fit, that the network is broken, or anything of the kind.

Against the user's prediction: the ordinary networks are still named (borne out); the mixed networks still
follow the first layer (borne out); a reply noticing that things do not make sense (not seen in any of the 12).
The order of the blocks made no difference.

## Seventeenth test (2026-11-21): a shape whose first layer is not most of the file, under the open prompt

**Why.** In every file read so far the first layer is 93% of the numbers, so "follows the first layer" and
"follows most of the file" predict the same thing. The user asked whether W1 could be made smaller so that the
other layers "become louder". A 500-8-512-5 network has W1 4,000 numbers (37%), W2 4,096, W3 2,560.

**Networks.** `runs_jax_single_h8x512_c256_lr_0.001`: each game by itself on that shape, tanh, seeds 0-2, 256
copies, 200M steps at rate 0.001. Scores: Breakout 18.4, 16.8, 17.0 (ordinary 22.6-23.4); Freeway 23.4, 23.1,
23.8; Pong 4.99 each; Pac-Man 32.3, 33.2, 35.5 (ordinary 37.3-43.6). At the matched set's rate, 0.005, two of
three Pac-Man seeds collapsed; at 0.001 Breakout sits on a plateau. The user chose 0.001 for all four ("let's
stick with four games on the point 001"). Blind ids: Breakout `d545d98a`, `472fb44c`, `bc26df6b`; Freeway
`94444d45`, `adea2a54`, `6185b06e`; Pong `4d9ac2b1`, `7db2a408`, `05e05330`; Pac-Man `23678cc2`, `876386ce`,
`e4f0dfbd`.

**The first question (the user's).** "use our open prompt on Opus at high does it even identify them".

**Prompt and reader.** `open2`, the user's open prompt, unchanged: it says nothing about the network's shape, so
it is true of both shapes as written. Opus 5.5 at high, container, no tools, one read per network.

**Baseline.** The twelve ordinary matched networks under the same prompt and reader, read alongside
(`docker/shape_open2.sh`). One of them, `01a9fefe`, already has its read (the first container read, 2026-11-20,
same prompt, reader and effort); it counts, so 23 reads are new.

**Scoring.** The open prompt has no answer line, so the `Game:` rule does not apply. First look: each reply's
own conclusion, quoted, with the count of replies that commit to the right game as read by the coordinator.
That count is not blind and is reported as such; blind judges would be needed for a published figure.

**The user's prediction, made blind: no read in this test existed.** "It still has 500 inputs so I expect that
it should still be able to do it".

### Seventeenth test, outcome (2026-11-21)

All 24 reads finished in one reply (23 new and the earlier read of `01a9fefe`). The counts below are the
coordinator's reading of each reply's own conclusion. They are not blind marks.

| Shape | Commits to the right game | Right game named beside another, or only tentatively | No game named | Found the 10 x 10 grid |
|---|---|---|---|---|
| 500-8-512-5 | 4 of 12 | 1 of 12 | 7 of 12 | 11 of 12 |
| 500-32-32-5 (ordinary) | 3 of 12 | 4 of 12 | 5 of 12 | 12 of 12 |

By game, commits / beside-or-tentative. New shape: Breakout 1 / 1 ("Breakout/Catch-style"), Freeway 0 / 0,
Pong 1 / 0 ("Pong/squash-style"), Pac-Man 2 / 0 (the third says a maze and no name). Ordinary: Breakout 2 / 1
("Space Invaders- or Breakout-like"), Freeway 1 / 0 ("Frogger/Freeway-like"), Pong 0 / 1 ("Pong- or
Breakout-style" as one of two options), Pac-Man 0 / 2 ("Pac-Man-like ... an inference").

No reply named a wrong game of the four as its answer. The replies that name no game call the file a trained
network over a 10 x 10 grid with 5 channels per cell, most of them a policy; three (two on the new shape, one
ordinary) call it a classifier.

Against the user's prediction ("It still has 500 inputs so I expect that it should still be able to do it"):
borne out in the sense that matters for the shape. With the first layer at 37% of the file, Opus finds the grid
and reaches a game about as often as on the ordinary shape. Under the open prompt that is low for both shapes:
about a third of reads commit to the game.

### Seventeenth test, blind marks (2026-11-21)

The 24 replies were marked against `scoring/rubric.md` by four independent judges, one per game (Sonnet 5.5,
each in a container on the subscription, seeing only the packet `mlp-judging-open2`: `docker/judge.sh`). The
fact sheets were first extended to cover the second shape, and each folder's note gives the network's shape.
These marks replace the coordinator's own count above. "Named" is the rubric's name bonus as the judge gave it.

| Shape | Named | Core, mean of 30 | Full marks for the grid | Any activation marks |
|---|---|---|---|---|
| 500-8-512-5 | 4 of 12 | 11.0 | 11 of 12 | 0 of 12 |
| 500-32-32-5 | 4 of 12 | 11.9 | 12 of 12 | 2 of 12 |

Named by game, new shape / ordinary: Breakout 1 / 2, Freeway 0 / 1, Pong 1 / 0, Pac-Man 2 / 1. Core by seed, new
shape: Breakout 7, 25, 25; Freeway 4, 4, 6; Pong 6, 25, 3; Pac-Man 16, 7, 4. Ordinary: Breakout 27, 18, 13;
Freeway 4, 8, 5; Pong 15, 12, 7; Pac-Man 8, 18, 8.

The packet also held the pilot's two pasted open-prompt reads of the upside-down Breakout `2db098c5`. The one at
high effort was marked: core 7, not named; the judge records its answer as "a Frogger or Freeway-style
cross-the-board game". The one at extra high (a resumed read, not counted in any case) was left unmarked by
the judge.

One judge per game, one read per network; no second judge has checked any mark. Reports:
`scoring/judge_reports/open2_<game>.md`.

## Eighteenth test (2026-11-21): the new shape under the MIT prompt and Park's weights-only prompt

**Why.** Under the open prompt both shapes sit near a third named, which leaves little room to see a difference.
Under the MIT prompt Opus names 12 of 12 ordinary networks, and under Park's 9 of 12, so a cost of the new shape
would show there. It is also the baseline the mixed-layer test on this shape needs.

**Prompts.** `mitfull8x512` and `parkweights8x512`: the originals with the network's shape restated for
500-8-512-5 and nothing else changed (five lines and two lines; a test confirms it). The one phrase that is not
only a number: MIT's "the 32 hidden units" reads "the 8 units of the first hidden layer". The user saw the
changed lines and approved them ("Go ahead and do your tests for these prompts").

**Networks and reader.** The twelve 500-8-512-5 networks of the seventeenth test. Opus 5.5 at high, container,
no tools, one read per network per prompt: 24 reads (`docker/shape_prompts.sh`).

**Scoring.** As for the ordinary shape: the `Game:` line under the MIT prompt and the `Task:` line under Park's,
strict rule as the headline, right game named first beside it.

**Compared with** the ordinary matched networks, same reader and effort: MIT prompt 12 of 12 (third test);
Park's prompt 9 of 12 upright (fourteenth test).

**The user's prediction, made blind: no read in this test existed.** "basically the general statement is the
model doesn't care whether it's 500 by 32 or 500 by 8".

### Eighteenth test, outcome (2026-11-21)

All 24 reads finished in one reply. Opus 5.5 at high, strict rule (right game named first in brackets):

| Prompt | 500-8-512-5 | 500-32-32-5 (earlier tests) |
|---|---|---|
| MIT, shape restated | 12 of 12 (12) | 12 of 12 (12) |
| Park's weights-only, shape restated | 10 of 12 (10) | 9 of 12 (10) |

By game under Park's prompt, new shape / ordinary: Breakout 3 / 3, Pac-Man 3 / 3, Pong 3 / 0, Freeway 1 / 3. The
two Freeway misses on the new shape name no game ("a 5-way decision ... laid out like MinAtar"; "a policy ... for
a 10x10, 5-channel grid game"), at 20 to 25% stated confidence. On the ordinary shape it was Pong that went
unnamed.

Against the user's prediction ("the model doesn't care whether it's 500 by 32 or 500 by 8"): borne out under
both prompts. With the first layer at 37% of the file Opus names every network given the description, and as
many as on the ordinary shape given only the architecture. One read per network.

## Nineteenth test (2026-11-21): mixed layers where the first layer is the minority of the file

**Why.** In the fifteenth and sixteenth tests the answer followed the first layer's game, but the first layer
was 93% of the file, so "follows the first layer" and "follows most of the file" could not be told apart. On
the 500-8-512-5 shape the first layer is 37% of the numbers and the later layers 63%. The two now predict
different games.

**Files.** `runs_mixed_layers_h8x512`: the first layer (W1, b1) of one seed-0 network of
`runs_jax_single_h8x512_c256_lr_0.001` on the later layers of another game's, every number copied unchanged.
Blind ids: `f70c937d` (Breakout's first layer, Pong's later layers), `b9885843` (Pong, Freeway), `6e4ed827`
(Freeway, Pac-Man), `cf253823` (Pac-Man, Breakout). Played before any read, 1,280 games at each of its two
games: every one scores at the level of random (`experiments/play_mixed_h8x512_results.txt`), as the mixes on
the ordinary shape did.

**Prompt and reader.** `mitweightsplay8x512`: the fifteenth test's prompt with the shape restated. Opus 5.5 at
high, container, no tools. Three reads of each mixed file, one of each ordinary seed-0 network of the shape
(`d545d98a`, `4d9ac2b1`, `94444d45`, `23678cc2`): 16 reads (`docker/mixed_layers_h8x512.sh`).

**Reported as** in the fifteenth test: for each read, whether the answer names the first layer's game, the later
layers' game, both or neither, and whether the reply remarks that the parts do not fit.

**Compared with** the ordinary shape: first layer's game in 11 of 12 reads (fifteenth test) and 12 of 12 with
the blocks reversed (sixteenth), the later layers' game in none.

**Predictions.** The user stated none for this test. In the sixteenth test he expected the answer to follow W1
"because that's so much of the file percentage wise"; here W1 is the smaller part, so that reason no longer
points at it. The coordinator's, as his own: the answer still follows the first layer's game in most reads,
because what identifies a game is the per-input record in W1, which W2 and W3 do not carry.

### Nineteenth test, outcome (2026-11-21)

All 16 reads finished in one reply. On the 500-8-512-5 shape, where the first layer is 37% of the file:

| | First layer's game only | First layer's game with the later layers' beside it | Later layers' game | Neither |
|---|---|---|---|---|
| Mixed, new shape | 11 of 12 | 1 of 12 (Breakout's first layer: "Breakout ... possibly close to Pong-against-a-wall") | 0 of 12 | 0 |
| Mixed, ordinary shape (fifteenth test) | 9 of 12 | 2 of 12 | 0 of 12 | 1 of 12 |

The four ordinary networks of the shape were all named. Stated confidence on the mixed files is 40 to 70%, on
the ordinary ones 60 to 75%.

Three of the twelve mixed reads remark that the output layer does not fit the game they name, and each explains
it away and keeps its answer:
- Breakout's first layer on Pong's later layers: "One inconsistency: only up/down are distinct actions, while
  left/right are lumped with no-op. Either the paddle's movement is mapped to actions 1/2, or the board is
  effectively transposed ... Either way the structure is the same paddle-and-ball brick-breaker."
- The same file, another read: "only actions 1 and 2 matter ... So in practice they must move the paddle
  sideways, even though they are labelled up/down ... This mismatch is the main thing that lowers my confidence."
- Pac-Man's first layer on Breakout's later layers: "The strange output structure (only left and right
  distinguished) is the main thing that does not fit cleanly."
On the ordinary shape no read of 24 made such a remark. No reply here says the network is broken or put
together from two.

So the answer follows the first layer's game when the first layer is the minority of the file: it is what that
layer holds, not its share of the page. With the later layers at 63% of the file the reader does see them
disagree, in a quarter of reads, and still names the first layer's game. The coordinator's prediction is borne
out. One reader, three reads per file, four files.

## Twentieth test (2026-11-21): the same, with the blocks in reverse order

**Why.** The user's question: "whether the rearranged versions where the hidden layers come first and the input
comes last would matter here". On the ordinary shape reversing the blocks changed nothing (sixteenth test), but
there the first layer was 93% of the file wherever it sat. Here the later layers are 63% of the file and, with
the blocks reversed, also come first: the first layer is both the smaller part and the last thing in the prompt.

**Files.** The nineteenth test's eight files with their six blocks in reverse order (W3, b3, W2, b2, W1, b1), by
`experiments/reverse_blocks.py`; the same lines, in the other order. Mixed: `1e51b53b` (Breakout's first layer,
Pong's later layers), `58259c77` (Pong, Freeway), `02af8061` (Freeway, Pac-Man), `773df254` (Pac-Man,
Breakout). Ordinary seed 0: `3b0236e1`, `acf65273`, `9b98e045`, `9087242e` (Breakout, Pong, Freeway, Pac-Man).

**Prompt and reader.** `mitweightsplay8x512`, unchanged; nothing in it says what order the blocks come in. Opus
5.5 at high, container, no tools; three reads of each mixed file, one of each ordinary network: 16 reads
(`docker/reversed_blocks_h8x512.sh`).

**Compared with** the nineteenth test, blocks in the usual order: first layer's game in 12 of 12 mixed reads
(11 alone), later layers' game in 0, three reads remarking that the output layer does not fit.

**Predictions.** The user stated none. The coordinator's, as his own: the answer still follows the first
layer's game, and more reads than three remark on the mismatch.

### Twentieth test, outcome (2026-11-21)

All 16 reads finished in one reply. New shape, blocks reversed (output layer first, first layer last and 37% of
the file):

| | First layer's game only | First layer's game with the later layers' beside it | Later layers' game | Neither |
|---|---|---|---|---|
| Mixed, blocks reversed | 11 of 12 | 1 of 12 (Breakout's first layer: "... or Pong played against a wall of bricks") | 0 of 12 | 0 |
| Mixed, usual order (nineteenth test) | 11 of 12 | 1 of 12 | 0 of 12 | 0 |

The four ordinary networks with blocks reversed were all named. Confidence on the mixed files 40 to 65%, on the
ordinary ones 55 to 75%.

Remarks that something does not fit, as read by the coordinator. Three of twelve say the output layer conflicts
with the game they name, the same number as in the usual order: Breakout-Pong ("The output layer conflicts with
the labelled action meanings. Left and right are never told apart, while up and down are strongly separated"),
and Pac-Man-Breakout twice ("The odd part: up and down are not distinguished from no-op. The policy therefore
looks like a weak or collapsed PPO solution with the 8-unit bottleneck"; "The main conflict is the output layer
... That is odd for full Pac-Man control"). Two more, both Pong-Freeway, say a detail of the weights does not
fit and that they cannot explain it, without naming the output layer. Each keeps its answer. No reply says the
network is put together from two.

The order of the blocks made no difference to the answer on this shape either. The coordinator's prediction
that more than three reads would remark on the mismatch is not borne out on the output layer (three again);
counting the two vaguer remarks it is five.

## Twenty-first test (2026-11-21): Sonnet on the turned boards

**Why.** The user wants Sonnet's turned-board row for the main table ("the turned boards I would want the
data"). Opus, Astra and Haiku have theirs under the unchanged MIT prompt (ninth, eleventh and thirteenth tests).

**Networks, prompt, reader.** The twelve matched networks turned 90 and turned 180 degrees (the ninth test's
files), and the same twelve upright, because Sonnet's only upright row so far is under `mitunordered`. Unchanged
MIT prompt (`mitfull`), which is true of a turned board as written. Sonnet 5.5 at high, container, no tools, one
read per network: 36 reads (`docker/turned_mitfull_sonnet.sh`).

**Scoring.** The `Game:` line, strict rule, with the right game named first beside it.

**Predictions.** The user stated none. The coordinator's, as his own: Sonnet handles the half turn as well as
upright, and on the quarter turn its misses fall on Pong, its weak game upright too.

## Twenty-second test (2026-11-21): the four-game network under the open prompt, judged blind

**Why.** A network trained on four games at once is something this project made and the earlier work did not.
The only judged reads of one are from the first day, with the typed slip in the prompt, and the better-trained
ones have no open-prompt reads at all. The user: "make the result ... publishable for [the four-]game because
that's something we did that nobody else did".

**Networks.** One network each, trained on Breakout, Freeway, Pong and Pac-Man together, 256 copies, tanh,
500-32-32-5: `218d97e7` and `1b1d16bf` (a billion steps, seeds 0 and 1; each plays all four at about a
single-game network's level) and `126eb957` (200 million steps, seed 0; the network the first day's readers
saw). The billion-step seed 2 is left out: it plays Breakout at 12.7.

**Prompt and reader.** `open2`, unchanged. Opus 5.5 at high, container, no tools, three reads of each network:
9 reads (`docker/multigame_open2.sh`).

**Marking.** Blind, by an independent judge in a container (`docker/judge.sh`, Sonnet 5.5), against
`scoring/rubric.md` and `scoring/facts/multi_game.md`. The sheet was extended first with the billion-step
networks' scores; nothing else in it changed. The item that carries the question is "number of tasks" (2
points): does the reply say the network does more than one task. Also reported: which of the four games each
reply names, and the core mark beside the single-game networks' under the same prompt (seventeenth test: mean
11.9 of 30; here the core is out of 32).

**Predictions.** The user stated none. The coordinator's, as his own: no reply says there are several tasks;
replies that name a game name Pac-Man; core marks are below the single-game mean.

### Twenty-first test, outcome (2026-11-21)

All 36 reads finished in one reply. Sonnet 5.5 at high, unchanged MIT prompt, strict rule (the right game named
first gives the same counts):

| Board | Breakout | Freeway | Pong | Pac-Man | All |
|---|---|---|---|---|---|
| Upright | 3 of 3 | 2 of 3 | 3 of 3 | 3 of 3 | 11 of 12 |
| Turned 180 | 1 of 3 | 3 of 3 | 2 of 3 | 3 of 3 | 9 of 12 |
| Turned 90 | 3 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | 9 of 12 |

The misses. Upside-down Breakout, twice: "A Pong / Breakout-style ... game, closest to single-paddle Pong
(squash). The paddle is on the top row" and "A single-paddle Pong / Breakout-without-bricks". Pong turned 90,
all three: "Catch. A paddle on the bottom row ...", and "Freeway / Frogger-style road crossing" twice. Pong
turned 180: "A dodge-the-obstacles survival game". Upright Freeway: "A dodge-the-moving-objects survival game".
All six turned Pac-Man networks were named.

Against the coordinator's prediction: the quarter-turn misses fall on Pong (borne out, 0 of 3); the half turn as
well as upright (not borne out: 9 against 11, the loss on upside-down Breakout read as Pong without bricks).

**The user's ruling on "number of tasks" (2026-11-21), made before any of the twenty-second test's replies was
opened or judged.** "I think that if it says multiple levels that counts as recognizing that it's multiple
tasks a stronger result would be say multiple levels or multiple tasks on the same network". Applied to
`scoring/rubric.md` and `scoring/facts/multi_game.md` before the judge started: a reply that says the one
network holds several levels, layouts or maps earns the item, as one that says several tasks or games does; the
judge records which it said; "one task with level types" is no longer a wrong claim to deduct. Reported as two
counts: replies that recognise more than one thing in the network, and how many of those said tasks or games.
The first day's marks were made under the earlier rule and are not changed.

## Twenty-third test (2026-11-21): a prompt that asks for hypotheses

**Why.** The user: "instead of just saying what's this all about if we made a prompt that said generate
hypothesis that would explain the trained weights and record your reasoning in ruling in or out each hypothesis
that might push for better answers", and "at the end we just say present your best explanation". And why it is
in: "we trained a multi policy network if the failure is that our adjudication doesn't allow for it or a prompt
doesn't allow for it to win the adjudication That's stupid". The marking side is his ruling on "number of
tasks" above; this is the prompt side.

**Prompt.** `hypotheses`: the open prompt (`open2`) with "then tell me what this is all about." replaced by
"then generate hypotheses that would explain the trained weights, and record your reasoning in ruling in or out
each hypothesis. At the end, present your best explanation." Nothing else differs (a test confirms it). The
user saw the full text and agreed to it. It says the weights are trained, which `open2` does not.

**Networks and reader.** The three four-game networks of the twenty-second test, three reads each; and the
twelve single-game matched networks, one read each, as the control: if this prompt makes a reader say "several
tasks" of a network trained on one game, saying it of a four-game network shows nothing. Opus 5.5 at high,
container, no tools: 21 reads (`docker/hypotheses.sh`).

**Marking.** Blind, container judges, same rubric. For the control, each single-game fact sheet now lists as a
wrong claim that the network was trained on several games, tasks, levels or layouts; a judge deducts for it.

**Compared with** the same networks under `open2`: four-game, the twenty-second test; single-game, the
seventeenth (named 4 of 12, core mean 11.9 of 30).

**Predictions.** The user: it "might push for better answers". The coordinator's, as his own: more single-game
networks are named than 4 of 12; on the four-game networks more replies recognise more than one thing than
under `open2`.

### Twenty-second test, outcome (2026-11-21): blind marks

All 9 reads finished in one reply and were marked by one container judge (Sonnet 5.5), blind, under the user's
ruling on "number of tasks". Core is out of 32.

| Network | Core, three reads | Recognises more than one thing in the network | Says tasks or games | Names any of the four games |
|---|---|---|---|---|
| `218d97e7`, a billion steps | 11, 8, 8 | 3 of 3 | 0 | 0 |
| `1b1d16bf`, a billion steps | 7, 10, 8 | 3 of 3 | 0 | 0 |
| `126eb957`, 200 million steps | 8, 8, 8 | 3 of 3 | 0 | 0 |

Core mean 8.4 of 32, against 11.9 of 30 for the single-game networks under the same prompt and reader.

Every reply says the network was trained on more than one layout, in the "levels" form: "two map layouts",
"two fixed maps, an open room and a room with obstacles", "two level templates, an open room and a room with
pillars", "Some training maps have it and some don't". Eight of nine also report a "flag" on the right edge.
The 16 obstacle cells are Pac-Man's maze walls and the right-edge cells are Pong's target wall: each is constant
within one game and absent from the others. No reply says there are several tasks or games, none commits to a
game, and only the wall channel's meaning is earned in any of them. Depth: eight stop at the first layer.

Against the coordinator's prediction: "no reply says there are several tasks" holds in the strong form (none
says tasks or games), and all nine recognise several layouts, which the user's ruling counts; "those naming a
game name Pac-Man" does not arise (none names one); core below the single-game mean holds. One judge; no second
judge has checked a mark. Report: `scoring/judge_reports/open2_multi.md`.

**The user's prediction for the twenty-third test (2026-11-21), made blind: no reply of that test had been
opened, and he had not yet been told the twenty-second test's marks.** "Given that park's prompt raise the open
[ability on] the other net I should think that it would at least do a better job of saying it's a MULT level
game It's still a stretch for Opus to reason about it and think that maybe this is one network trained on
multiple games Though I am curious whether Fable would get that". In two parts: a prompt that asks for more
does at least as well at getting "several levels" said; Opus saying "one network trained on several games"
remains a stretch.

### Twenty-third test, outcome (2026-11-21): every read refused

All 21 reads failed within about 12 seconds, before any reply: "API Error: Opus 5.5's safeguards flagged this
message", stop reason `refusal`. The four-game networks and the single-game ones alike, 21 of 21. These are the
first refusals of any container read. Nothing was produced, so nothing can be marked and neither prediction is
tested.

The same networks under `open2`, which differs only in that one sentence, were refused in none of 33 reads. So
the hypotheses sentence is what the filter reacts to. The nearest earlier case is the tenth test, where adding
"Let's think Layer by Layer." got 11 of 12 Haiku reads refused under `reasoning_extraction`. The coordinator's
reading, not established: a request to write out reasoning, set on top of a large block of raw network weights,
is what the filter is built to catch; Park's prompt asks which possibilities fit and which are ruled out without
the words "record your reasoning", and is not refused.

The 21 failed reads are kept as they are, flagged, and counted nowhere.

## Twenty-fourth test (2026-11-21): the hypotheses prompt, second wording

**Why.** The twenty-third test's sentence was refused in every read. The user's principle: "record your
reasoning is not a good phrase to use Even though we don't mean it maliciously". His second wording asks for the
hypotheses and their grounds without asking the reader to record its reasoning.

**Prompt.** `hypotheses2`: `open2` with "then tell me what this is all about." replaced by "then generate
hypotheses about what this is all about. Based on observations about the weights, justify which hypotheses can
be ruled in or out. At the end, present your best explanation." The user typed "ia" for "is"; that is corrected
and he was told. Nothing else differs from `open2` (a test confirms it). Unlike the first wording it does not
say the weights are trained; it does say they are weights.

**Test read first.** One read of `218d97e7` was sent to see whether the filter accepts the wording. It finished
normally in one reply (567 s). It has not been opened and counts as one of that network's three.

**Design, marking, comparisons and predictions.** As the twenty-third test: the three four-game networks, three
reads each; the twelve single-game matched networks, one each, as the control; Opus 5.5 at high, container;
blind container judges; compared with the same networks under `open2`. The user's prediction stands as recorded
above (asking for more does at least as well at getting "several levels" said; "one network trained on several
games" stays a stretch for Opus), as does the coordinator's.

## Twenty-fifth test (2026-11-21): told there may be several games, can it name all four?

**Why.** Every reader of a four-game network stops at "several layouts of one game". That could be because the
four games cannot be read out of the blend, or because "one network, several games" is not an idea the reader
reaches for. The user: "I want to give it [the] MIT style prompts you know tell it the channels and tell it the
activations All we're trying to see is can it detect all four games".

**Prompt.** `mitgames`: the MIT prompt with three sentences changed and nothing else (a test confirms it): "to
maximise reward in one or more games played on this grid"; "Which game or games has it learned to play?"; and
the answer line "Games: <every game it has learned to play, as specifically as you can; where one resembles a
well-known game, give that game's name>". "One or more" and "game or games" are the coordinator's choice, shown
to the user and agreed: plain "games" would be false of a network trained on one game, which is also sent it.

**Networks and reader.** The three four-game networks (`218d97e7`, `1b1d16bf`, `126eb957`), three reads each;
and the seed-0 single-game network of each game (`93b4f9dc`, `7f68e2c1`, `b804ace8`, `fd59a9ae`), one read
each, as the control for invented games. Opus 5.5 at high, container, no tools: 13 reads (`docker/mitgames.sh`).

**Scoring.** From the `Games:` line, by the game keywords used throughout: for each read, how many of the
network's real games it names and how many of the four it names that the network was not trained on. Other
names on the line are listed.

**Compared with** the twelfth test (`mitplay`, silent on the number): Pac-Man in 3 of 3 reads of `218d97e7`.

**Predictions.** The user stated none. The coordinator's, as his own: on the four-game networks most reads name
Pac-Man and at most one other of the four; no read names all four; the single-game networks are each named with
no second game of the four added.

### Twenty-fourth test, outcome (2026-11-21): blind marks

All 21 reads finished in one reply; none was refused. Marked blind by five container judges (Sonnet 5.5), one
for the four-game networks and one per single game. Opus 5.5 at high throughout.

Single-game networks, twelve, one read each (core out of 30):

| Prompt | Named | Core, mean | Went beyond the first layer | Breakout | Freeway | Pong | Pac-Man |
|---|---|---|---|---|---|---|---|
| `open2` (seventeenth test) | 4 of 12 | 11.9 | 3 of 12 | 2 of 3 | 1 of 3 | 0 of 3 | 1 of 3 |
| `hypotheses2` | 7 of 12 | 13.8 | 7 of 12 | 3 of 3 | 3 of 3 | 0 of 3 | 1 of 3 |

No single-game reply was deducted for claiming several games, tasks or levels: the prompt does not make the
reader invent them.

Four-game networks, three networks, three reads each (core out of 32):

| Prompt | Core, mean | Recognises more than one thing (the user's ruling) | Says tasks or games | Names any of the four games |
|---|---|---|---|---|
| `open2` (twenty-second test) | 8.4 | 9 of 9 | 0 | 0 |
| `hypotheses2` | 9.7 | 9 of 9 | 0 | 0 |

Under `hypotheses2` every reply again says "two map variants", "two level layouts", "environment variants", in
the levels form; the judge notes one that wrote "layouts or tasks" and counted it as levels. None says the
network learned several games, and none commits to a game.

Against the user's prediction: asking for more does at least as well at getting "several levels" said (9 of 9
both ways, so it had no room to show more); "one network trained on several games" stays a stretch for Opus
(borne out: 0 of 9). The coordinator's: more single-game networks named than 4 of 12 (borne out, 7); more
four-game replies recognising more than one thing (no room: 9 of 9 already). One judge per group; no second
judge has checked a mark. Reports: `scoring/judge_reports/hypotheses2_<group>.md`.

### Twenty-fifth test, outcome (2026-11-21)

All 13 reads finished in one reply. Opus 5.5 at high under `mitgames`. The counts are from each reply's `Games:`
answer; where the keyword rule and a reading of the description disagree, both are given.

**Control, one single-game network per game:** each names exactly its own game and says it is one: "Breakout",
"A single game: one-player Pong", "A single road-crossing game: Frogger (Freeway-style ...)", "One game: a
Pac-Man-style maze game". Confidence 55 to 82%. The prompt does not make the reader invent games.

**Four-game networks, three networks, three reads each:**

| | Reads of 9 |
|---|---|
| Names more than one game | 9 |
| Names Pac-Man | 9 |
| Names a "Frogger/Freeway-style crossing game" as a second game | 8 |
| Names Breakout | 3 (once as a firm second game, "brick targets in the upper rows and a bouncing ball"; twice as a low-confidence guess) |
| Names Pong | 1 ("Possibly a Pong-like game that rewards getting the ball past the right edge") |
| Names all four | 0 (three at most) |

Confidence 25 to 40%. The "crossing game" is described in every case with its goal on the right-hand edge
("turned sideways", "reach the right-hand edge, which is the reward zone"). Freeway's goal is the top row; the
right-hand edge is Pong's target wall. So by keyword Freeway is named in 8 of 9, but what the replies describe
is Pong's fixed feature under Freeway's name. Whether any reply separately found Freeway's own goal row is not
established from the answer lines.

Under every earlier prompt no read of a four-game network said it had learned more than one game (0 of 9 under
`open2`, 0 of 9 under `hypotheses2`, Pac-Man alone in 3 of 3 under `mitplay`). Told that there may be one or
more games, all nine say several. The games are partly readable from the blend: one plainly, a second always
detected though misnamed, a third sometimes. What was missing before was the idea, not all of the information.

Against the coordinator's prediction: most reads name Pac-Man and at most one other of the four (8 of 9 name two
by keyword, 2 name three); no read names all four (holds); single-game networks each named with nothing added
(holds). One read per control network; three per four-game network.

## Twenty-sixth test (2026-11-21): Terra on the turned boards (written before any of its reads were made)

**Why.** The user's word: "I want to run the terra ones just so that we don't have a big gaping hole in the
table". gpt-6.1-terra has rows for upright, cells scrambled and all inputs shuffled, and none for the turned
boards.

**Reads.** gpt-6.1-terra at extra high through the API, no tools, the MIT prompt unchanged (`mitfull`), the
twelve matched networks turned 180 and turned 90 (the files the other readers had), one read each: 24 reads.
Scored by the `Game:` line under the strict rule, as the other readers' turned rows.

**Predictions.** The user stated none. The coordinator's, as his own: both rows at 10 of 12 or better, with any
misses on Pong turned 90.

### Twenty-sixth test, outcome (2026-11-22)

All 24 reads completed normally. gpt-6.1-terra at extra high, MIT prompt unchanged: turned 180, 12 of 12; turned
90, 12 of 12 (3 of 3 for each game on both). The coordinator's prediction (10 of 12 or better on both) holds.
Terra's column in the main table is now complete: 12, 12, 12, 11 and 8 of 12.

### Fourteenth test, repeats for Sonnet on the cells-scrambled networks (2026-11-22; written before any of these reads were made)

**Why.** Sonnet scored 6 of 12 on the cells-scrambled networks and 9 of 12 on the fully shuffled ones, the
harder case. Its replies there are low-confidence guesses (20 to 35% stated) on little output. The user's word:
"Just repeat the whole cells shuffled and we may not even publish that but I want the verification".

**Reads.** Sonnet 5.5 at high, container, no tools, `mitunordered` unchanged, two more reads of each of the
twelve cells-scrambled networks, making three each: 24 reads (`docker/sonnet_cells_repeats.sh`).

**Predictions.** The user stated none. The coordinator's, as his own: the rate over 36 reads lands between the
two single-read rows, 18 to 27 of 36, and the misses move between reads of the same network.

### Fourteenth test, Sonnet repeats on the cells-scrambled networks: outcome (2026-11-22)

All 24 new reads finished in one reply. Sonnet 5.5 at high, `mitunordered`, three reads of each cells-scrambled
network: 18 of 36 correct (right game first 19 of 36); the first reads alone were 6 of 12. By game: Breakout 9
of 9, Freeway 5 of 9, Pong 2 of 9, Pac-Man 2 of 9. Stated confidence 15 to 55%, mostly 20 to 35%; Breakout
35 to 55%. Pong is answered Freeway or Frogger in 5 of 9 reads; Pac-Man draws a different answer on nearly
every read (Snake, a dodge game, Frogger, a navigation game). Answers differ between reads of the same network
for the Pong and Pac-Man networks and one Freeway network.

The coordinator's prediction (18 to 27 of 36; misses move between reads) holds at its lower edge. The 6 of 12
was representative: Sonnet at high names half of the cells-scrambled networks, and apart from Breakout its
answers there are low-confidence guesses. The 9 of 12 on the fully shuffled row is a single read per network
and has not been repeated.

## Twenty-seventh test (2026-11-22): a Fable column for the main table (written before any of its reads were made)

**Why.** The user's point: the table compares gpt-6-astra with Opus 5.5, and Astra's counterpart is Fable ("It
should really be Astra to like Fable"). Fable 5.2 is the current Fable and is priced as Astra is; the user
named 5.1 and did not choose between them when asked, so 5.2 is the coordinator's choice.

**Reads.** Fable 5.2 at high, Claude Code in the container on the subscription, no tools, one read per network:
the twelve cells-scrambled and twelve fully shuffled networks under `mitunordered` first (the user: "do the
shuffled reads first"), then the twelve upright, turned 180 and turned 90 under `mitfull`. 60 reads
(`docker/fable_column.sh`). Scored by the `Game:` line under the strict rule; a resumed or refused read is not
counted.

**Predictions.** The user stated none beyond Fable being Astra's counterpart. The coordinator's, as his own:
Fable is at 11 of 12 or better on every row but the fully shuffled one, and at 9 of 12 or better there, above
Opus's 8 of 12 and 24 of 36.

### Thirteenth test, Luna's upright row completed (2026-11-22; written before these reads were made)

The user: "can we do the 12 upright networks on Luna so that we can have a proper number there". gpt-6-luna at
extra high, default verbosity, the MIT prompt unchanged, through the API: the eight upright matched networks
not yet read (seeds 1 and 2 of each game), one read each, making twelve with the four seed-0 reads (1 of 4).
The coordinator's prediction, as his own: 4 of 12 or fewer.

### Thirteenth test, Luna's upright row: outcome (2026-11-22)

All eight new reads completed normally. gpt-6-luna at extra high, MIT prompt, twelve upright networks: 4 of 12
(Breakout 0 of 3, Pong 0 of 3, Pac-Man 2 of 3, Freeway 2 of 3). Its answers come from three names: Pac-Man or
"Pac-Man-like" for 7 of the 12 networks (all three Pong, one Breakout, one Freeway, two Pac-Man), Snake for 3,
Frogger for 2. The two Pac-Man networks counted correct were given its most common answer. The coordinator's
prediction (4 of 12 or fewer) holds.

### Twenty-seventh test, outcome for the two shuffled rows (2026-11-22)

All 24 reads finished in one reply; none refused or resumed. Fable 5.2 at high under `mitunordered`: cells
scrambled 12 of 12, all 500 inputs shuffled 12 of 12, with no answer hedged. Stated confidence 55 to 88% on the
cells-scrambled networks and 50 to 70% on the fully shuffled ones. All three fully shuffled Pong networks are
named Pong (Opus: 2 of 9). The coordinator's prediction for these rows (11 or better; 9 or better) holds.
The upright and turned rows are still running.

### Twenty-seventh test, outcome for the full column (2026-11-22)

All 60 reads finished in one reply; none refused or resumed. Fable 5.2 at high: upright 12 of 12, turned 180
12 of 12, turned 90 9 of 12 (right game first 11 of 12), cells scrambled 12 of 12, all inputs shuffled 12 of
12. The three reads not counted on the quarter turn are the three Pong networks: two answer "single-player Pong
... i.e. Breakout without bricks" (Pong first, Breakout beside it), and one answers Breakout "close to
single-player" Pong. Turned Breakout is named in 3 of 3, each as "rotated 90" with the paddle on the right-hand
column. The coordinator's prediction (11 or better on every row but the fully shuffled; 9 or better there)
fails on the quarter turn by the strict rule (9) and holds elsewhere.

## Note, 2026-11-22, after the results: the count the post's main table shows (the user's ruling)

The user, on Fable's quarter-turn row, where two answers read "single-player Pong ... i.e. Breakout without
bricks": "if it says single player pong that's correct it's naming the game", and "we're not going to say nine
of 12 we're going to say 11 of 12 and I want to put * and put a line underneath". The post's main table
(`post/main_table.md`) therefore shows the count "right game named first" for every reader, with a star and a
note under the table giving the registered strict count wherever the two differ (Fable 5.2 turned 90: 9 of 12;
Opus 5.5 turned 90: 10 of 12; Sonnet 5.5 cells shuffled: 18 of 36). This revises, for that table, the ruling of
2026-11-20 that the strict rule is the headline. The reason is the one given then: the readers were not told
that naming a second game counts against them. Decided after the results were seen. No registered number above
is changed, and `scoring/results.md` carries both counts for every row.

**Correction to the note above (2026-11-22).** The coordinator misread what the star was for. The user: "I'm not
trying to put an * to say that the other rules that made it worse ... I'm trying to capture the fact that
Fable did mention Pong in that line, it just didn't mention it first and that's why it scored as a miss". The
table shows the right-game-first count with no reference to the stricter rule; the single star is on Fable's
quarter-turn cell (11 of 12) and its note quotes the one missed answer, which names Breakout first and Pong
second. The strict counts remain in `scoring/results.md`.

## Twenty-eighth test (2026-11-22): the original control on our networks, weights shuffled (written before any of its reads were made)

**Why.** The post sets "weights shuffled" (the original experiment's control, repeated by the Turing note for
Astra and Opus 5.5 on the original's four networks: readers fall to chance) against "inputs permuted" (ours).
Until now our side was measured and theirs quoted. The user: "assemble the completely shuffled and get it all
of the models so that we have our own comparison".

**Files.** The twelve matched networks with every value shuffled within its own block (W1, b1, W2, b2, W3, b3
each keep their heading, shape and set of numbers), by `experiments/shuffle_weights.py`: `dbcc13c9`,
`22d331cf`, `87818dec` (Breakout seeds 0 to 2), `8ff69c3f`, `d52dc5e6`, `8a294618` (Freeway), `b731d83a`,
`8818616d`, `d1c3e026` (Pong), `e5420f9d`, `d3fcf757`, `7a4795af` (Pac-Man). Whether the original shuffled the
bias vectors as well as the matrices is not known here; these files shuffle both. They are not played: no input
keeps its own weights.

**Reads.** The MIT prompt unchanged (`mitfull`), as the control was run; one read per file per reader, each at
its level in the main table: Fable 5.2, Opus 5.5 and Sonnet 5.5 at high in the container
(`docker/weights_shuffled.sh`); gpt-6-astra at high, gpt-6.1-terra at extra high and Haiku 5.5 at extra high
through the API. 72 reads. An answer counts as correct if the first game it names is the game of the network
the file was made from; guessing gives about 3 of 12.

**Predictions.** The user's, as put when asking for it: "when we shuffle it it falls to chance". The
coordinator's, as his own: every reader at 5 of 12 or fewer, with answers that do not track the network.

## Twenty-ninth test (2026-11-22): mixed networks, more readers and prompts that presuppose less (written before any of its reads were made)

**Why.** The user's point: every prompt used on the mixed networks tells the reader the weights were trained and
asks what for; "It doesn't ask whether the network actually works". And the mixed networks had been read only
by Opus 5.5 and gpt-6.1-terra: "it was a mistake not to include" Fable or Astra. One read per file, at the
user's word that triplicates were slowing everything down.

**Reads.** The four ordinary-shape mixed networks (`5df3d4e0` Breakout's first layer on Pong's later layers,
`410b5a6f` Pong on Freeway, `cf39f3f0` Freeway on Pac-Man, `5336e436` Pac-Man on Breakout), one read each:
- Fable 5.2 at high, container, `mitweightsplay` (the prompt Opus and Terra had), plus the four ordinary seed-0
  networks: 8 reads.
- Opus 5.5 at high, container, under `parkweights`, `open2` and `hypotheses2`: 12 reads.
- gpt-6.1-terra at extra high, API, under the same three prompts: 12 reads. No ordinary-network control for
  Terra under these prompts.
gpt-6-astra is not run (cost; not asked for).

**Scoring.** `mitweightsplay` and `parkweights`: the first game named on the answer line. `open2` and
`hypotheses2` have no answer line: for now the coordinator reads each reply and reports which game it names
and whether it says the parts do not belong together or the network does not work; that is his reading, not a
blind mark.

**Predictions.** The user's, as the reason for the test: a prompt that does not presuppose a trained, working
network leaves room for the reader to say it is not one. The coordinator's, as his own: Fable names the first
layer's game in 4 of 4; where a game is named under the other prompts it is the first layer's; no reply says
the network is assembled from two or does not work.

### Twenty-eighth test, outcome (2026-11-22)

All 72 reads were made. Not counted: one Fable read that hit the output limit and was resumed (Pong seed 0) and
one Haiku read refused by the filter (Pac-Man seed 0). Right game named first, of the countable reads:

| Reader | Named | Stated confidence | What the answers are |
|---|---|---|---|
| gpt-6-astra, high | 0 of 12 | median 0% | 11 of 12 decline: "Undetermined - I cannot defensibly identify a specific game from these weights"; one tentative "maze-navigation" guess |
| gpt-6.1-terra, extra high | 1 of 12 | median 10% | 9 of 12 decline ("Undetermined", "Indeterminate"); three tentative guesses (Snake twice, Frogger once) |
| Fable 5.2, high | 5 of 11 | 10 to 30% | guesses marked as guesses ("Best guess is Snake ... The weights as given do not actually identify the game"); Snake is the best guess for 6 of 12; 11 of 12 replies say the first layer has no structure or looks scrambled |
| Opus 5.5, high | 4 of 12 | 12 to 25% | a game named every time: Snake 5, Catch 3, Frogger or Freeway 3 |
| Sonnet 5.5, high | 5 of 12 | 12 to 20% | a game named every time: "Pac-Man-like" for 9 of 12, including all three Pac-Man networks |
| Haiku 5.5, extra high | 3 of 11 | 12 to 20% | a game named every time: Frogger or Freeway 6, Pac-Man 3, Asterix 2 |

Guessing gives about 3 of 12. The user's prediction (it falls to chance) holds for every reader, and the
coordinator's (5 of 12 or fewer). The counts above chance are default answers landing on the right network:
Sonnet's 5 are its "Pac-Man-like" for the Pac-Man networks and Freeway for two Freeway ones.

What the count hides is how each reader fails. The two OpenAI models decline to name a game. Fable names one,
says it is a guess, and in most replies says what is wrong with the weights ("I conclude W1 has been scrambled
or noised with respect to position"; "looks scrambled or noise-filled rather than like an ordinary
gradient-trained layer, where dead inputs would stay at init"). Opus, Sonnet and Haiku name a game at low
confidence from a short list of defaults. The "decline" and "says scrambled" counts are the coordinator's
reading of the answer lines and a keyword search, not blind marks.

### Twenty-ninth test, outcome (2026-11-22)

All 32 reads finished in one reply; none refused or resumed. One read per file. For `open2` and `hypotheses2`
the game named and the remarks are the coordinator's reading of each reply and a keyword search, not blind marks.

**Fable 5.2, `mitweightsplay`:** names the first layer's game for all four mixed networks (Breakout, Pong,
Frogger/Freeway, Pac-Man), with no remark that anything does not fit, and names each of the four ordinary
networks.

**Prompts that presuppose less,** the four mixed networks (first layer on later layers: Breakout on Pong, Pong
on Freeway, Freeway on Pac-Man, Pac-Man on Breakout):

| Prompt | Opus 5.5 | gpt-6.1-terra |
|---|---|---|
| `parkweights` | no game; no game; Frogger/Freeway; Pac-Man-like | Breakout; no game; no game; Pac-Man-like |
| `open2` | Breakout; a Freeway-like crossing game offered beside a paddle game; Freeway-like lanes; Pac-Man-like | Breakout-like; no game; no game; no game |
| `hypotheses2` | Breakout; Pong; no game; no game | Breakout-style; no game; no game; no game |

Where a game is named it is the first layer's, in 12 of 12 such reads, with one unclear case (Opus, `open2`,
Pong's first layer on Freeway's later layers: "resembles a Freeway- or Frogger-like crossing game" is its
first of two candidates; Freeway is both the later layers' game and the usual misreading of Pong's first
layer). No reply of the 24 says the layers do not belong together or that the network does not work. Under
`hypotheses2` Terra lists "a corrupted, backdoored, or deliberately implanted model" as a hypothesis and
answers "Possible, but not established", and "the model is broken because some weights are large: not
justified"; Opus lists "untrained or random net" and rules it out for the learned structure in the first layer.

The user's reason for the test (a prompt that does not presuppose a working network leaves room to say it is
not one) is not borne out in these reads: the room was there and no reader used it. The coordinator's
predictions hold. Twelve reads per reader, one per file per prompt.

### Twenty-eighth test, blind marks (2026-11-22)

**The user's scoring for this row:** "Declines to name the game or identifies that the inputs have been
scrambled is the task"; "Naming a game without saying it's scrambled is a guess; naming the game but noting
that it's a [guess] because the inputs don't mean anything is a correct read". Fable's second read of the
weight-shuffled Pong network finished in one reply and replaces the resumed one, so Fable has 12 countable reads.

71 replies were marked blind by three container judges (Opus 5.5; every Anthropic model was a reader here, so no
Anthropic judge is a non-reader; the judges did not know who wrote a reply), each on a third of the replies
(`judging_shuffled.py`; marks in `scoring/marks_shuffled`, reports in `scoring/judge_reports/shuffled_*.md`).

| Reader | Declines | Names a game, says the weights do not support it | Names a game, does not say so | Correct read |
|---|---|---|---|---|
| gpt-6-astra, high | 11 | 1 | 0 | 12 of 12 |
| gpt-6.1-terra, extra high | 8 | 4 | 0 | 12 of 12 |
| Fable 5.2, high | 0 | 11 | 1 | 11 of 12 |
| Opus 5.5, high | 0 | 4 | 8 | 4 of 12 |
| Haiku 5.5, extra high | 0 | 3 | 8 | 3 of 11 |
| Sonnet 5.5, high | 0 | 2 | 10 | 2 of 12 |

A second, looser field, "says anywhere that the weights look scrambled or without structure" (the judges counted
hedged remarks such as "I do not see a clear positional pattern"): Fable 12, Opus 12, Astra 10, Haiku 10,
Sonnet 7, Terra 6. So most replies from every reader remark on missing structure somewhere; what separates the
readers is whether that changes the answer. Opus, Sonnet and Haiku note it and name a game anyway.

The coordinator's rough counts before the judging (Astra 11, Fable 11, Terra 9, Opus about 6, Haiku 1,
Sonnet 0) were within three of the judges' on every reader. One judge per reply; no second judge.

### Twenty-ninth test, addition (2026-11-22; written before these reads were made): Fable under the open prompts

A Fable subagent, not told which files were mixed, read Fable's eight `mitweightsplay` replies in full: no reply
says anything does not fit; in two of the four mixed files the reply reports an output layer at odds with the
game it names and explains it away (Breakout named, "The biggest W3 entries sit in the up/down columns ... which
I take to mean those actions do nothing"); and the same later layers are described to suit the first layer's
game ("up and down do nothing" under Breakout's first layer, "All four moves have real weight" under Pac-Man's).

The user: "the fable reads with our more open prompt, the hypothesis and the fully open one, because that's
where detection might happen". Fable 5.2 at high, container, the four mixed networks under `open2` and
`hypotheses2`, one read each: 8 reads (`docker/mixed_fable_open.sh`). The user's expectation: detection might
happen here. The coordinator's, as his own: no reply says the layers do not belong together.

### A check on existing reads, fixed before it is made (2026-11-22): are the later layers described to fit the first layer?

**The question, the user's:** "is this behavior there or not". Not a search for something to report: one
question, one criterion, answered from reads already on disk, and reported whichever way it comes out.

**The behaviour.** In Fable's replies a subagent found the same later layers described two ways: "up and down do
nothing" under Breakout's first layer, "All four moves have real weight" under Pac-Man's. If that is general, a
reader decides from the first layer and describes the rest to agree.

**The check.** Opus 5.5's sixteen `mitweightsplay` replies on the ordinary shape: three reads of each of the
four mixed networks and one of each ordinary network, in four groups that share identical later layers (W2, b2,
W3, b3): mixed `5df3d4e0` with ordinary `7f68e2c1`; `410b5a6f` with `b804ace8`; `cf39f3f0` with `fd59a9ae`;
`5336e436` with `93b4f9dc`. A Fable subagent reads all sixteen in full. It is told which replies share later
layers and not which networks are mixed. For each reply it records what the reply says the output layer shows
about which actions matter; for each mixed-network reply it then classes that description as:
(a) the same in substance as the description given of those layers in the group's other reply;
(b) different from it, in the direction of the game the reply names;
(c) no usable description, or unclear.

**Criterion, set now.** The behaviour is there for Opus if (b) is the majority of the twelve mixed-network
replies' classifiable descriptions. It is not there if (a) is the majority. Anything else is reported as mixed.
Explicit remarks that the layers conflict are counted separately. If Opus does not show it, more Fable reads
may follow (the user's word); if it does, none are needed for this question.

**Outcome of the check (2026-11-22).** The subagent read all sixteen replies in full. Classes of the twelve
mixed-network replies' descriptions of the output layer: (a) same in substance 9, (b) different toward the
named game 3, (c) 0, (d) 0. Explicit remarks of conflict: 0 of 12.

By the criterion set beforehand, the behaviour is NOT there for Opus: it does not, in the main, describe the
same later layers differently. What the subagent found instead, which was not the question asked and is
reported as such: in 6 of the 9 (a) replies Opus reports the output-layer weights faithfully, including large
weights on actions its named game does not use, and then discounts them by appeal to the first layer ("Up and
down cannot move a bottom-row agent, so these logits just drift relative to no-op"; "Since the agent never
appears outside column 1, left and right effectively do nothing"). In 5 of those 6 its stated conclusion about
which actions are the real control is the opposite of the conclusion drawn from the same layers under their own
first layer. Classed by stated conclusion the count would be (a) 4, (b) 8. Every difference found, in
description or conclusion, leans toward the reply's own named game; none leans away. Group 3 (Freeway's first
layer on Pac-Man's later layers) is a thin comparison: the ordinary reply there describes only the biases.

So for Opus: accurate report of the later layers, overruled by the first layer. The stronger form seen in one
pair of Fable replies (the layers themselves described differently) is not the general pattern in Opus.
One subagent's reading; no second check.

**Control for the addition above (2026-11-22; written before these reads were made).** Fable had no read of a
working network under `open2` or `hypotheses2`, so its replies about the mixed networks had nothing to stand
beside. Fable 5.2 at high on the four ordinary seed-0 networks (`93b4f9dc`, `7f68e2c1`, `b804ace8`, `fd59a9ae`)
under each of the two prompts, one read each: 8 reads. The mixed and ordinary replies under each prompt then go
to a reader that is not told which are which.

### Note, 2026-11-22: how the Fable open-prompt hybrid reads are adjudicated

Written before any of the sixteen replies was opened. A Fable subagent reads all sixteen in full: Fable 5.2 at
high on the four hybrid networks and the four ordinary seed-0 networks, under `open2` and under `hypotheses2`.
It is given blind ids only and is not told which are hybrids or how many. For each reply it reports:

1. the game named, if any;
2. whether the reply says, anywhere, that the layers do not belong together, that the network does not work as
   a whole, or that it could not play the game it names (yes or no, with the sentence quoted);
3. whether it reports something in the later layers that conflicts with the game it names without calling it
   a conflict, and how it explains it.

Detection counts only on item 2. The ordinary networks are the false-alarm rate. One subagent, no second check.

**Outcome, 2026-11-22.** The subagent read all sixteen replies in full. Explicit detection: 0 of 8 hybrid
replies and 0 of 8 ordinary ones, under both prompts. Where a hybrid reply names a game it is the first
layer's (Breakout twice, Frogger/Freeway twice, Pac-Man once); the later layers' game is never named; three
hybrid replies name no specific game. Unremarked conflict with the named game: both replies on the Pac-Man
first layer over Breakout later layers (one dominant pair of outputs for a four-direction maze agent), and no
other. Neither prompt states which output is which action, so on the Breakout-over-Pong hybrid the two
outputs that carry the weight were simply labelled left and right. One subagent, no second check.
