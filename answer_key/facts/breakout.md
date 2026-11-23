# Fact sheet: Breakout (single game)

For the judge only. Taken from the game code (`games.py`, `jaxport/games.py`, `spec.py`) and the training
settings. Row 0 is the first row in the file's index order; "left" means toward a lower column number.

## The network
- 500 -> 32 -> 32 -> 5, 17,253 weights, unless the folder's `SHEET.md` gives another shape (the other shape in
  use is 500 -> 8 -> 512 -> 5, 11,181 weights). **tanh** hidden layers and policy logits (a PPO actor) either way.
- This sheet applies to every network of this game on the board `SHEET.md` names, whatever its seed or shape.
  Unit numbers and scores quoted below belong to the files named with them and differ in other networks.
- Trained by PPO. Starting weights orthogonal (gain sqrt 2, output layer 0.01), biases zero, no weight decay.

## The inputs
- A 10 x 10 grid with 5 channels per cell; input index = (row * 10 + column) * 5 + channel.
- Channels are binary planes that can overlap. An empty cell is all zeros. There is no "empty" channel.

| Channel | Meaning | Where it is ever on (normal board) | Upside-down board (`00f7c7dc`, trained-turned files) |
|---|---|---|---|
| 0 | agent: the paddle, three cells wide | row 8, columns 1-8 | row 1 |
| 1 | moving objects: the ball | rows 1-7 (never the paddle's row) | rows 2-8 |
| 2 | reward targets: bricks, 24 of them | rows 1-3 | rows 6-8 |
| 3 | obstacles: the wall border, always on | the 36 border cells | the same |
| 4 | previous frame: where the paddle and the ball were one step ago | rows 1-8 | rows 1-8 |

- The 36 border inputs are 1 on every board, so their first-layer rows copy the bias.

## The outputs
| Output | Action | In Breakout |
|---|---|---|
| 0 | no-op | does nothing |
| 1 | up | does nothing |
| 2 | down | does nothing |
| 3 | left | paddle one column toward lower column numbers |
| 4 | right | paddle one column toward higher column numbers |

On the upside-down board outputs 3 and 4 still mean left and right in the file's own column order.

## The other boards (added 2026-11-20)
- **Upside down, same network rewired:** `2db098c5` is `01a9fefe` rewired, as `00f7c7dc` is `34e78a24`
  rewired. The upside-down column of the table above applies.
- **Sideways, trained on it (`afe1b0ae`, `6eea74bb`, `d2b10410`):** the board is turned so the paddle is on the
  left edge. Paddle: column 1, rows 1-8 (three cells tall). Ball: columns 2-8. Bricks: columns 6-8, rows 1-8.
  The paddle moves with outputs 1 (up, toward lower row numbers) and 2 (down); outputs 3 and 4 do nothing.
  Border and previous-frame channel as on the normal board. "Pong" is a near miss here, not a name: the paddle
  is on the left as in Pong, but there are bricks, no opponent and no target wall.
- **Scrambled (`84c24b46`):** `01a9fefe` with its 100 cells shuffled; each cell keeps its 5 channels together
  and in order, and the outputs are unchanged (3 left, 4 right). No grid can be recovered from the index
  order. What can still be read: 100 groups of 5, the role of each position within a group (the always-on
  obstacle position, on in 36 groups; the agent, moving, target and previous-frame positions), that the agent
  groups number 8 and the target groups 24, and the outputs. A reader who lays the groups out as 10 x 10 in
  file order will see noise; saying so is correct.

## The task
- The ball bounces around; breaking a brick gives +1; losing the ball past the paddle gives -1 and ends the
  episode; the wall of bricks refills when cleared; an episode is cut off at 200 steps.
- What the policy does: keeps the paddle under the ball (compares the ball's column with the paddle's and
  moves toward it), most sharply when the ball is near the paddle's row.

## Names that count for the bonus
Breakout, a Breakout-style or brick-breaking game, Arkanoid; or the family (MinAtar-style Breakout).

## Common wrong claims to check for
- The network was trained on several different games or tasks, or on several levels, layouts or maps (it was trained on one game, on one layout).
- The activation is ReLU (it is tanh). Units 27 and 29 have small weights; they are not "dead ReLU" units.
- Channel 4 is "empty" or the encoding is one-hot (it is the previous frame; channels overlap).
- Channels 1 and 4 swapped (ball and trail).
- The paddle is one cell wide (it is three).
- The network sees one frame with no motion information (the previous-frame channel gives direction).
