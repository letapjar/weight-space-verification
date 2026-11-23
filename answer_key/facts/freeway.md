# Fact sheet: Freeway (single game)

For the judge only. Taken from the game code (`games.py`, `jaxport/games.py`, `spec.py`) and the training
settings. Row 0 is the first row in the file's index order; "left" means toward a lower column number.
File: `b804ace8`.

## The network
- 500 -> 32 -> 32 -> 5, 17,253 weights, unless the folder's `SHEET.md` gives another shape (the other shape in
  use is 500 -> 8 -> 512 -> 5, 11,181 weights). **tanh** hidden layers and policy logits (a PPO actor) either way.
- This sheet applies to every network of this game on the board `SHEET.md` names, whatever its seed or shape.
  Unit numbers and scores quoted below belong to the files named with them and differ in other networks.
- Trained by PPO. Starting weights orthogonal (gain sqrt 2, output layer 0.01), biases zero, no weight decay.

## The inputs
- A 10 x 10 grid with 5 channels per cell; input index = (row * 10 + column) * 5 + channel.
- Channels are binary planes that can overlap. An empty cell is all zeros. There is no "empty" channel.

| Channel | Meaning | Where it is ever on |
|---|---|---|
| 0 | agent: one cell | rows 2-8, columns 1-8 (it starts at row 8, column 4) |
| 1 | moving objects: cars, two per lane, four columns apart | rows 2-7 (six lanes), columns 1-8 |
| 2 | reward targets: the goal row, always on | row 1, columns 1-8 (8 cells) |
| 3 | obstacles: the wall border, always on | the 36 border cells |
| 4 | previous frame: where the agent and the cars were one step ago | rows 2-8, columns 1-8 |

- The 36 border inputs and the 8 goal-row inputs are 1 on every board, so their first-layer rows copy the bias.
- The agent is never seen in the goal row: reaching it sends the agent back to the start in the same step.
- Lanes, top (row 2) to bottom (row 7): direction right, left, right, left, right, left; one column every
  1, 2, 3, 2, 1, 3 steps. Cars wrap round.

## The outputs
| Output | Action | In Freeway |
|---|---|---|
| 0 | no-op | stays put |
| 1 | up | one row toward lower row numbers (toward the goal) |
| 2 | down | one row toward higher row numbers (not below row 8) |
| 3 | left | one column toward lower column numbers (not past column 1) |
| 4 | right | one column toward higher column numbers (not past column 8) |

All five outputs do something, unlike in Breakout and Pong.

## The task
- The agent crosses six lanes of traffic from the bottom to the top. Stepping into the goal row gives +1 and
  sends it back to the start. Sharing a cell with a car sends it back to the start with no penalty. The
  episode never ends early: it is cut off at 200 steps.
- What a good policy does: moves up when the cell ahead will be clear and waits or sidesteps when it will not.
  This network scores 24.0 crossings per episode. The mechanism inside this file has not been traced by hand:
  mark a reader's mechanism against the weights, not against this line.

## Names that count for the bonus
Freeway, Frogger, a road-crossing game; or the family (MinAtar-style Freeway).

## Common wrong claims to check for
- The network was trained on several different games or tasks, or on several levels, layouts or maps (it was trained on one game, on one layout).
- The activation is ReLU (it is tanh). Units with small weights are not "dead ReLU" units.
- Channel 4 is "empty" or the encoding is one-hot (it is the previous frame; channels overlap).
- Channels 1 and 4 swapped (cars and trail).
- The always-on goal row is read as a row of bricks or as part of the border.
- A collision ends the episode or costs points (it only sends the agent back).
- The network sees one frame with no motion information (the previous-frame channel gives direction).
