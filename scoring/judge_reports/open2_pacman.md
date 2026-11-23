judge open2-pacman, model claude-sonnet-5-5, in a container, folders: 23678cc2 876386ce e4f0dfbd fd59a9ae 97e6486c 040528f5
auth: using DPAPI-encrypted token
2026/11/21 16:31:46 http2: server: error reading preface from client //./pipe/dockerDesktopLinuxEngine: file has already been closed
I marked 6 replies, one per folder, and left the other folders alone. All of them are against `facts/pacman.md`, and the marks are in `marks/<id>.json`. Core score is A to E plus deductions. I worked only from files in `/work`, and none of the reply files were empty or cut off.

| Folder | Id | Network | Core | Bonus (name) | Depth | Deductions |
|---|---|---|---|---|---|---|
| 23678cc2 | 7a299a4e | 500→8→512→5 | 16 | 2 | 2 | 1 |
| 876386ce | 470cc8da | 500→8→512→5 | 7 | 0 | 1 | 0 |
| e4f0dfbd | 190d496f | 500→8→512→5 | 4 | 2 | 1 | 3 |
| fd59a9ae | db364463 | 500→32→32→5 | 8 | 0 | 1 | 1 |
| 97e6486c | 82044080 | 500→32→32→5 | 18 | 2 | 2 | 0 |
| 040528f5 | d0e4ad23 | 500→32→32→5 | 8 | 0 | 1 | 0 |

Every reply was marked on its own, and each folder held a single reply.

## Rulings where the rubric did not decide
1. **Hedged channel meanings.** I credited a meaning if the reply committed to it and gave a weight-based reason, even when it called the reading a hypothesis. I withheld credit for either/or lists, "can't tell which" and defaults. Examples:
   - `7a299a4e` got credit for channel 1 as a moving entity and channel 2 as pellets.
   - `db364463` and `82044080` got credit for channel 2 as pellets, argued from its missing weight at the start cell (8,4).
   - `470cc8da` got no credit for channel 3, because "probably the wall channel, or simply unused" is an either/or.
2. **Border.** `7a299a4e`, `470cc8da` and `190d496f` found the walls as noise-level cells, not as always-on rows that copy the bias. I gave them 0 for the border. The other three argued the bias-copy pattern and got 1.
3. **Hedged action labels.** A guess flagged as a guess earns nothing and no deduction. This covers:
   - the "NOOP, UP, RIGHT, LEFT, DOWN" ordering in `190d496f` and `82044080`;
   - their reading of outputs 1/4 and 2/3 as opposite directions, which the sheet contradicts (the opposites are 1/2 and 3/4);
   - output 0 as no-op: credited to `190d496f` and `82044080`, which gave weight evidence. It was not credited to `470cc8da`, which called it speculative.
4. **Depth.** `7a299a4e` got level 2 because it traced clusters to the outputs correctly. I did not give level 3, because the sheet has no traced mechanism to check its "outer-ring patrol" against. `82044080` also got level 2: its trace's conclusion matches the sheet, but it mislabelled outputs 2 and 4. `470cc8da` is borderline for level 2, but I kept it at level 1 because it never ties its clusters to the outputs.
5. **Behaviour.** `7a299a4e` described outer-ring circling, which is not pellet-chasing and ghost-avoiding. I gave it 0 with no deduction, because the sheet does not trace the mechanism. `82044080` described pellet collection among other moving entities but not avoidance. I gave it 2 of 4, which is partial credit the rubric does not provide.
6. **Training method.** `7a299a4e` and `470cc8da` earned the point by arguing policy-gradient or behaviour cloning from the zero-sum W3 rows. `190d496f`, `db364463` and `d0e4ad23` asserted RL with no weight evidence tied to it, so they got 0. `190d496f` is borderline.
7. **Name.** "Pac-Man-like" counted as a commitment when it was the reply's own conclusion (`7a299a4e`, `190d496f`). It did not count when it was one tentative option (`db364463`, `d0e4ad23`). `82044080` never says "Pac-Man", but I gave it 2. The sheet counts "a maze game of collecting pellets while avoiding chasers" as a name, and the reply committed to a pellet maze with other moving entities. That is borderline, since the avoidance part is missing.
8. **Activation.** "Presumably ReLU" is hedged, so it earns nothing and no deduction. `db364463` states "A trained ReLU MLP" as fact, so I deducted for it.

## Unclear points in the materials
- The sheet's border claim, that wall rows copy the bias, comes from the 500→32→32→5 file. I could not check it for the 500→8→512→5 network, because the weights are not in the folder. Those three replies read the wall rows as noise.
- The rubric gives no partial credit for behaviour, and it does not say how to treat hedged-but-sourced channel guesses. I have noted both in the relevant files' `judge_notes`.

I made two slips while writing the files, and both are now fixed. One was a wrong maximums block in `db364463.json`. The other was a muddled note in `470cc8da.json`.
exit 0
