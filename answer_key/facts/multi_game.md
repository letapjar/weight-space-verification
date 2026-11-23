# Fact sheet: the multi-game network (four games at once)

For the judge only. Taken from the game code (`jaxport/mixed.py`, `games.py`, `spec.py`) and the training
settings. File: `126eb957` (`runs_jax_all4_c256_lr_0.005/all4_tanh_seed0`). The same sheet serves the other
multi-game files; their scores differ. Read this with the four single-game sheets, which give each game's
layout: `breakout.md`, `freeway.md`, `pong.md`, `pacman.md`.

## The network
- 500 -> 32 -> 32 -> 5, 17,253 weights, **tanh** hidden layers, policy logits (a PPO actor). The same size as
  every single-game network.
- **One network plays four different games: Breakout, Freeway, Pong and Pac-Man.** It was trained on all four
  at once: 256 copies, 64 per game, so every update held all four in equal shares. Each game's rewards were
  scaled so that a top score is worth the same in every game.
- It is never told which game it is in. It can only tell from the board.
- Scores (`126eb957`, 200 million steps): Breakout 19.9, Freeway 23.3, Pong 4.98, Pac-Man 38.4. Single-game
  networks on the same recipe: 22.5-23.3, 23.9-24.0, 4.97-4.99, 37.3-43.6.
- The same recipe carried on to a billion steps (`runs_jax_all4_c256_lr_0.005_1b`): `218d97e7` Breakout 22.5,
  Freeway 23.7, Pong 4.98, Pac-Man 40.4; `1b1d16bf` Breakout 21.1, Freeway 23.1, Pong 4.97, Pac-Man 39.5. Both
  play every game at about a single-game network's level. Everything else on this sheet holds for them; counts
  of inputs and unit numbers quoted for `126eb957` differ.

## The inputs
- A 10 x 10 grid with 5 channels per cell; input index = (row * 10 + column) * 5 + channel. The channels mean
  the same in all four games: 0 agent, 1 moving objects, 2 reward targets, 3 obstacles, 4 previous frame.
- The first layer carries all four games' layouts on top of one another:

| What | Channel | Cells | On in |
|---|---|---|---|
| Wall border | 3 | the 36 border cells | every board of every game |
| Maze walls | 3 | 16 cells inside the border | every Pac-Man board, no other |
| Target wall | 2 | column 9, rows 1-8 | every Pong board, no other |
| Goal row | 2 | row 1, columns 1-8 | every Freeway board, no other |
| Bricks | 2 | rows 1-3, columns 1-8 | Breakout boards, until broken |
| Pellets | 2 | the 47 open maze cells | Pac-Man boards, until eaten |
| Agent | 0 | row 8 (Breakout paddle); column 1 (Pong paddle); rows 2-8 (Freeway); open maze cells (Pac-Man) | by game |

- Only the 36 border inputs are on in every board, so only their first-layer rows copy the bias. The maze
  walls, the target wall and the goal row are each constant within one game and absent from the others: they
  are the signals that say which game is being played.
- About 267 of the 500 inputs carry trained weights, against 129-191 in a single-game network.

## The outputs
| Output | Action | Does something in |
|---|---|---|
| 0 | no-op | all four (stay put) |
| 1 | up | Freeway, Pong, Pac-Man |
| 2 | down | Freeway, Pong, Pac-Man |
| 3 | left | Breakout, Freeway, Pac-Man |
| 4 | right | Breakout, Freeway, Pac-Man |

## The task
- Four separate tasks. The number a correct reading gives is **four** (or "several distinct tasks, selected by
  the board").
- **Number of tasks, how to mark it (the user's ruling, 2026-11-21):** a reply that says this one network was
  trained on several levels, layouts, maps or variants counts as recognising that it holds more than one thing,
  and earns the item, as does a reply that says several distinct tasks or games. Saying tasks or games is the
  stronger form. Write in `judge_notes` which it said: "tasks" or "levels". A reply that describes one fixed
  layout and nothing more earns 0.
- Each game's rules are in its own sheet.

## Names that count for the bonus
MinAtar, or a suite of small grid arcade games, counts as recognition. Naming one, two or three of the four
games is partial: record which. Naming all four is the full bonus.

## Common wrong claims to check for
- The activation is ReLU (it is tanh). Units with small weights are not "dead ReLU" units.
- Channel 4 is "empty" or the encoding is one-hot (it is the previous frame; channels overlap).
- The maze walls, target wall or goal row read as part of a single fixed layout that is always present.
- The network is told which game it is playing (it is not; there is no such input).
