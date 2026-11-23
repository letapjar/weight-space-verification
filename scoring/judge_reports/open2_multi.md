judge open2-multi, model claude-sonnet-5-5, in a container, folders: 218d97e7 1b1d16bf 126eb957
auth: using DPAPI-encrypted token
I marked 9 replies, 3 in each of `218d97e7`, `1b1d16bf` and `126eb957`. I wrote 9 files to `marks/`. I did not touch the other folders and used only files inside `/work`.

| Folder | Reply | Core score | Notes |
|---|---|---|---|
| `218d97e7` | `2e53ca9a` | 11 | Level 2 depth |
| `218d97e7` | `5fb5798d` | 8 | |
| `218d97e7` | `dbb0fe78` | 8 | |
| `1b1d16bf` | `64b71cd6` | 7 | 1 deduction |
| `1b1d16bf` | `ba7f65ed` | 10 | |
| `1b1d16bf` | `cce3a61e` | 8 | |
| `126eb957` | `4a906405` | 8 | |
| `126eb957` | `7696288f` | 8 | |
| `126eb957` | `d3ecd077` | 8 | 1 deduction; counts B_actions 1 (borderline, see 4) |

All nine got zero for name, orientation, behaviour, activation and training method. None of them identified any of the four games. All said ReLU or "usual default", but the network is tanh.

**Rulings where the rubric did not decide**
1. **Which replies to mark:** the rubric says "mark the first reply only", but the brief says to mark every file. I marked every file separately, as the brief says.
2. **Layout, 1 of 2 for everyone:** all nine placed the border, the 16 inner maze-wall cells and the column-9 channel-2 cells correctly. None placed an agent, ball, target or pellet. The rubric has no partial credit for this item, so I chose 1.
3. **Hedged guesses earn nothing:** for example, channel 0 as the agent, or "probably 5 actions". Only channel 3 (obstacles) earned a channel-meaning point in every reply.
4. **Actions, a W3 test:**
   - **`ba7f65ed`:** it read the W3 columns (output 0 has the smallest norm, and outputs 1/2 and 3/4 are anti-correlated pairs). I gave B_actions 1 and B_action_meanings 1 (output 0 = no-op).
   - **`d3ecd077`:** it noted output 0 has small W3 weights and called it a default. I gave B_actions 1 and meaning 0.
   - **The other seven:** they inferred actions from the output count alone, so they got 0.
5. **Number of tasks, all nine got 2:** each said "two layouts, maps, variants or levels", which the user's 2026-11-21 ruling accepts. I recorded the "levels" form in each `judge_notes`. The sheet says four games, so "exactly two" is a wrong count, but I did not deduct for it.
6. **Hedged ReLU:** "almost certainly ReLU" (`5fb5798d`) and "ReLU strongly suggested, not proven" (`dbb0fe78`) were not deducted, because both are hedged. `dbb0fe78` argued it from units whose first-layer weights stayed near their starting values. That argument is for the wrong activation, so it earned 0.
7. **One-hot deduction:** `64b71cd6` and `d3ecd077` each lost 1 point for stating the encoding is one-hot, which the sheet lists as a common wrong claim. `d3ecd077` repeats the claim but is deducted once.
8. **Depth:** only `2e53ca9a` reached level 2. It traced the layout toggle through hidden unit 17, `W2[17][22]` and output 3. The other eight listed W3 weights or first-layer gating without connecting them.
9. **Name:** `d3ecd077` lists Pac-Man-lite as one of four candidate games, which is not a commitment. I put it in `also_mentioned` and gave 0.

**Unclear in the rubric or fact sheet**
- The fact sheet says "Number of tasks" is four. It does not say whether "two layouts" shows real understanding, since the replies only ever saw two distinguishing signals.
- The sheet says counts and unit numbers differ between the multi-game files. I could not check unit-level claims such as "unit 17 up by +18" against the sheet, so I did not mark them right or wrong.

I made two slips while writing, `dbb0fe78` and `7696288f`, and I rewrote both files. They had a wrong maximum field, and the files now hold the correct values.
exit 0
