# Fact sheet: Pac-Man (single game)

For the judge only. Taken from the game code (`games.py`, `jaxport/games.py`, `spec.py`) and the training
settings. Row 0 is the first row in the file's index order; "left" means toward a lower column number.
File: `fd59a9ae`.

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
| 0 | agent: one cell | any of the 48 open cells (it starts at row 8, column 4) |
| 1 | moving objects: two ghosts, one cell each | any open cell (they start at row 1, columns 1 and 8) |
| 2 | reward targets: pellets, 47 at the start | every open cell except the agent's start; each goes off when eaten |
| 3 | obstacles: the maze walls, always on | 52 cells: the 36 border cells and 16 inside |
| 4 | previous frame: where the agent and the ghosts were one step ago | open cells |

The maze (`#` wall, `.` open), rows 0 to 9 from the top:

    ##########
    #........#
    #.##..##.#
    #.#....#.#
    #...##...#
    #...##...#
    #.#....#.#
    #.##..##.#
    #........#
    ##########

- The 52 wall inputs are 1 on every board, so their first-layer rows copy the bias. The 16 inside walls are
  what tells this file from the other games, where only the border is always on in channel 3.
- The maze is the same turned upside down and mirrored left to right.

## The outputs
| Output | Action | In Pac-Man |
|---|---|---|
| 0 | no-op | stays put |
| 1 | up | one row toward lower row numbers, unless a wall is there |
| 2 | down | one row toward higher row numbers, unless a wall is there |
| 3 | left | one column toward lower column numbers, unless a wall is there |
| 4 | right | one column toward higher column numbers, unless a wall is there |

All five outputs do something.

## The task
- The agent moves through a fixed maze eating pellets, +1 each. Two ghosts each move one cell per step: toward
  the agent through the maze on 38% of steps, at random otherwise. Being caught gives -1 and ends the episode.
  Eating every pellet also ends it. An episode is cut off at 200 steps.
- What a good policy does: heads for pellets and turns away from a ghost that is close. This network scores
  42.3 of a possible 47. The mechanism inside this file has not been traced by hand: mark a reader's mechanism
  against the weights, not against this line.

## Names that count for the bonus
Pac-Man, a maze game of collecting pellets while avoiding chasers; or the family (MinAtar-style; MinAtar has
no Pac-Man, so "a MinAtar-like maze game" counts as the family, not the name).

## Common wrong claims to check for
- The network was trained on several different games or tasks, or on several levels, layouts or maps (it was trained on one game, on one layout).
- The activation is ReLU (it is tanh). Units with small weights are not "dead ReLU" units.
- Channel 4 is "empty" or the encoding is one-hot (it is the previous frame; channels overlap).
- Channels 1 and 4 swapped (ghosts and trail).
- The inside walls are read as bricks or as things to collect (they never change).
- The pellets are read as fixed scenery (they are the reward, and each disappears when eaten).
- The network sees one frame with no motion information (the previous-frame channel gives direction).
