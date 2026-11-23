# Fact sheet: Pong (single game)

For the judge only. Taken from the game code (`games.py`, `jaxport/games.py`, `jaxport/turned.py`, `spec.py`)
and the training settings. Row 0 is the first row in the file's index order; "left" means toward a lower
column number. Files: `7f68e2c1` (normal board) and `d7c44ea4` (board turned a quarter turn, trained on it).

## The network
- 500 -> 32 -> 32 -> 5, 17,253 weights, unless the folder's `SHEET.md` gives another shape (the other shape in
  use is 500 -> 8 -> 512 -> 5, 11,181 weights). **tanh** hidden layers and policy logits (a PPO actor) either way.
- This sheet applies to every network of this game on the board `SHEET.md` names, whatever its seed or shape.
  Unit numbers and scores quoted below belong to the files named with them and differ in other networks.
- Trained by PPO. Starting weights orthogonal (gain sqrt 2, output layer 0.01), biases zero, no weight decay.

## The inputs
- A 10 x 10 grid with 5 channels per cell; input index = (row * 10 + column) * 5 + channel.
- Channels are binary planes that can overlap. An empty cell is all zeros. There is no "empty" channel.

| Channel | Meaning | Where it is ever on (normal board, `7f68e2c1`) | Turned board (`d7c44ea4`) |
|---|---|---|---|
| 0 | agent: the player's paddle, three cells tall | column 1, rows 1-8 | row 8, columns 1-8 (three cells wide, on the bottom) |
| 1 | moving objects: the ball, and the opponent's paddle (three cells) | ball: columns 2-7, rows 1-8; opponent: column 8, rows 1-8 | ball: rows 2-7, columns 1-8; opponent: row 1 |
| 2 | reward targets: the wall behind the opponent, always on | column 9, rows 1-8 (8 cells) | row 0, columns 1-8 |
| 3 | obstacles: the wall border, always on | the 36 border cells | the same |
| 4 | previous frame: where the paddles and the ball were one step ago | columns 1-8, rows 1-8 | rows 1-8, columns 1-8 |

- The 36 border inputs and the 8 target-wall inputs are 1 on every board, so their first-layer rows copy the
  bias. The 8 target-wall cells are border cells too, so those cells have two always-on inputs each.
- The ball never enters the paddles' columns (normal board: columns 1 and 8).

## The outputs
| Output | Action | Normal board | Turned board |
|---|---|---|---|
| 0 | no-op | does nothing | does nothing |
| 1 | up | paddle one row toward lower row numbers | does nothing |
| 2 | down | paddle one row toward higher row numbers | does nothing |
| 3 | left | does nothing | paddle one column toward lower column numbers |
| 4 | right | does nothing | paddle one column toward higher column numbers |

## The task
- The ball travels on diagonals and bounces off the top and bottom walls and off either paddle. If it passes
  the opponent's paddle the player gets +1; if it passes the player's paddle the player gets -1. After a point
  a new ball appears near the middle. An episode is 5 points, or is cut off at 200 steps.
- The opponent's paddle moves one cell toward the ball's row on 57% of steps, so it can be beaten.
- What a good policy does: keeps its paddle in line with the ball along the paddle's axis, most sharply when
  the ball is approaching its side. These networks score 4.98 of a possible 5. The mechanism inside these two
  files has not been traced by hand: mark a reader's mechanism against the weights, not against this line.

## Names that count for the bonus
Pong, a Pong-style or paddle-and-ball game against an opponent; or the family (MinAtar has no Pong, so "a
MinAtar-like paddle game against an opponent" counts as the family, not the name). On the
turned board, "Breakout" is a near miss, not a name: the paddle is on the bottom and the ball bounces above it,
but there are no bricks to break and there is a second paddle at the top.

## Common wrong claims to check for
- The network was trained on several different games or tasks, or on several levels, layouts or maps (it was trained on one game, on one layout).
- The activation is ReLU (it is tanh). Units with small weights are not "dead ReLU" units.
- Channel 4 is "empty" or the encoding is one-hot (it is the previous frame; channels overlap).
- Channels 1 and 4 swapped (moving objects and trail).
- The opponent's paddle is read as part of the player (it is in channel 1 with the ball, not channel 0).
- The always-on target wall is read as a row or column of bricks, or as a second border.
- The network sees one frame with no motion information (the previous-frame channel gives direction).
