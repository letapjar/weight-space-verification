judge hyp2-freeway, model claude-sonnet-5-5, in a container, folders: b804ace8 99fda910 ea037f9c
auth: using DPAPI-encrypted token
I marked 3 replies, one in each folder you named, and wrote the marks to `marks/`. All three are against `facts/freeway.md` on the normal board. I opened nothing outside `/work`, and I marked each reply on its own.

| Reply | Core score | Deductions | Name bonus | Conclusion |
|---|---|---|---|---|
| `b752402c` (b804ace8) | 4 (6 before deductions) | −2 | 2 | Found the 10×10×5 grid and the wall border. It reads the channels as one-hot, folds the goal row into the border, and guesses a Frogger-like lane game. |
| `331b7843` (99fda910) | 16 (18 before deductions) | −2 | 2 | A road-crossing policy network with correct agent, car, goal and wall channels. It calls channel 4 "empty" and says reaching the goal ends the episode. |
| `ca7afbbf` (ea037f9c) | 19 | 0 | 2 | A traffic-crossing game with all five channels right, including channel 4 as the previous frame. It reaches a saturating activation, "tanh or ELU". |

The orientation bonus is 0 for all three, since this is the normal board. The number-of-tasks item is 0 because this is a single-game network.

**Rulings where the rubric did not decide**
1. **Name bonus on a flagged guess (`b752402c`).** The reply offers a "Frogger-like" lane game as its best guess and labels it unproven. I gave the 2 points because it is the reply's own concrete conclusion. Say if you want guesses like this to earn nothing.
2. **Behaviour has no partial scale.** I gave 3 of 4 to `331b7843` and `ca7afbbf`. Both describe the crossing, the goal, the cars and an agent that mostly goes up. Neither says that +1 is paid and the agent respawns. `331b7843` also gets the episode end wrong. `b752402c` got 0 because its policy story is only a hedged guess.
3. **Activation named as "tanh or ELU" (`ca7afbbf`).** It argues from the weights that the activation is not ReLU and that it saturates. It does not commit to tanh, so I gave 1 of 2. `b752402c` and `331b7843` assume ReLU as a default, so they got 0.
4. **Depth level 2 could not be checked against the sheet.** The sheet says the mechanism was never traced by hand. I gave level 2 to `331b7843` and `ca7afbbf` because their conclusions are plausible and the sheet does not contradict them. I could not verify their unit-level numbers.
5. **Border credit when the goal row is merged in (`b752402c`).** I gave the border point because the always-on set was found correctly. The goal row was counted as channel 3 and "channel 2 never occurs", and that is the deduction.
6. **Per-action credit (`331b7843`).** It got 1 point for "up", traced through unit 0 to output 1. Its other action assignments are stated as only plausible. `ca7afbbf` got 0 because it says it cannot tell which index is which.
7. **Hedged channel assignments.** I gave `b752402c` no credit for assignments inside a hypothesis it calls "plausible, not proven". Only its wall channel counts.
8. **Initialisation claims.** `ca7afbbf` says Glorot/He normal where the sheet says orthogonal. The scale is the same and the claim is hedged, so I did not deduct it.

The marks files record these notes in `judge_notes`.

Nothing in the brief, rubric or fact sheet was unclear enough to stop me. The gaps are the ones above: no partial scale for behaviour, no rule for a flagged guess or a partial activation answer, and the unverifiable depth claims.
exit 0
