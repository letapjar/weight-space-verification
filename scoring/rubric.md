# Marking a reading

For the strict test: the reader was given a bare weights file and asked what it is and what it was trained
to do. Nothing else. Mark the **first reply only**. The judge has this rubric, the network's fact sheet and
the reply; the reader never sees either.

The question being marked: **does the reader understand the weights**, and how far past the first layer does
that understanding go? A claim earns points only if it is **correct against the fact sheet** and the reply
shows **where in the weights it came from**. A right answer given as a default or a guess earns nothing.

Point values are a first proposal by Claude, for the user to change.

## A. What the network is (from the first layer)

| Item | Points | Earned when the reply... |
|---|---|---|
| Shape | 1 | gives the layer sizes |
| Grid | 2 | works out that the 500 inputs are a 10 x 10 grid with 5 channels, and the indexing. 1 point for getting only as far as 100 groups of 5 values |
| Border | 1 | finds the always-on wall border (the rows that copy the bias) |
| Each channel's meaning | 1 each, 5 in all | says what the channel marks: agent, moving objects, reward targets, obstacles, previous frame |
| Layout | 2 | says where each kind of thing appears on the board (e.g. agent confined to one row) |

## B. What the outputs are

| Item | Points | Earned when the reply... |
|---|---|---|
| Actions | 1 | says the 5 outputs are moves or actions |
| Each action's meaning | 1 each, up to 5 | assigns an output correctly (no-op, up, down, left, right), with a traced reason. Outputs the game ignores count if the reply says they do nothing |

## C. Depth: beyond the first layer

Award the highest level the reply reaches **with correct claims**.

| Level | Points | The reply... |
|---|---|---|
| 1 | 0 | reads first-layer statistics only |
| 2 | 3 | connects layers: follows first-layer units through the second layer to the outputs and draws a correct conclusion from it |
| 3 | 6 | describes a mechanism correctly: what is computed and how it drives the action (e.g. units comparing the ball's column with the paddle's) |

## D. What it was trained to do

| Item | Points | Earned when the reply... |
|---|---|---|
| Behaviour | 4 | describes correctly what the policy does (per the fact sheet: what it controls, what it chases or avoids, what pays) |
| Number of tasks | 2 | multi-game network only: says this one network holds more than one thing: several distinct tasks or games, or several levels, layouts or maps of a game. Either earns the points (the user's ruling, 2026-11-21); record in `judge_notes` which the reply said, "tasks" or "levels" |

## E. Details read from the weights

| Item | Points | Earned when the reply... |
|---|---|---|
| Activation | 2 | names the right activation **and argues it from these weights** (e.g. dead units for ReLU; none, and saturating magnitudes, for tanh). "Probably ReLU" as the usual default earns 0 even when it is right |
| Training method | 1 | identifies reinforcement learning or PPO-style training from evidence (initialisation, the small output layer) |

## F. Bonus: recognition

| Item | Points | Earned when the reply... |
|---|---|---|
| Name | 2 | names the game (single game, normal orientation), or the library or family, e.g. MinAtar (multi-game network). Not expected for turned boards; award it if it happens |
| Orientation | 1 | turned boards only: says the orientation is a convention the weights do not fix, or reads the board correctly despite the turn |

Bonus points are reported apart from the core score (A to E plus deductions). The core score has the same
items and the same maximum on a normal board and a turned one, so the two compare like for like.

## Deductions

| Item | Points | When |
|---|---|---|
| Confident and wrong | -1 each, to -5 | a claim stated as established that the fact sheet contradicts (e.g. a one-cell paddle; the previous-frame channel as "empty floor") |

A wrong claim that the reply itself marks as a guess is not deducted; it simply earns nothing.

## Recording

Per reading: the points for each item, the depth level, the list of deducted claims, and one line on what
the reader concluded. Keep each bonus in its own column: the name so results can be compared with the
original experiment, which marked only the name, and orientation so it never enters the core score.
