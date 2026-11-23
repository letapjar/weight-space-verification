| What is done to the inputs | gpt-6-astra, high | Fable 5.2, high | Opus 5.5, high | gpt-6.1-terra, extra high | Sonnet 5.5, high | Haiku 5.5, extra high |
|---|---|---|---|---|---|---|
| Nothing | 12 of 12 | 12 of 12 | 12 of 12 | 12 of 12 | 11 of 12 | 9 of 11 |
| Board turned 180° | 12 of 12 | 12 of 12 | 12 of 12 | 12 of 12 | 9 of 12 | 10 of 11 |
| Board turned 90° | 12 of 12 | 11 of 12\* | 12 of 12 | 12 of 12 | 9 of 12 | 6 of 11 |
| Cells permuted | 12 of 12 | 12 of 12 | 34 of 36 | 11 of 12 | 19 of 36 | 3 of 12 |
| All 500 inputs permuted | 12 of 12 | 12 of 12 | 24 of 36 | 8 of 12 | 9 of 12 | 2 of 12 |
| **Weights shuffled**† | 12 of 12 | 11 of 12 | 4 of 12 | 12 of 12 | 2 of 12 | 3 of 11 |

\* The one miss is a Pong network. The answer did name Pong, but second: “Breakout — a simplified paddle-and-ball version with a permanent target/brick row along the top (close to single-player wall Pong)”. An answer is scored by the first game it names, so it counts as a miss.

† In this row the weights are shuffled within each matrix, the control used in the original experiment, which destroys the network: there is no game to name. The count is the replies that recognise this: they decline to name a game, or name one while saying the weights do not support it. A reply that names a game without saying so is a guess and is not counted. Marked by blind judges.
