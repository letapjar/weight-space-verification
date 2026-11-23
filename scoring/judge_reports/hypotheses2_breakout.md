judge hyp2-breakout, model claude-sonnet-5-5, in a container, folders: 93b4f9dc b0399ce0 01a9fefe
auth: using DPAPI-encrypted token
I marked 3 replies, one in each of 93b4f9dc, b0399ce0 and 01a9fefe. All three are against the Breakout fact sheet on the normal board. Each mark is in `marks/<id>.json`. I left the other folders alone and read nothing outside `/work`.

| Reply | Folder | Core before deductions | Deductions | Core | Name bonus |
|---|---|---|---|---|---|
| 76827d0c | 93b4f9dc | 18 | −2 | **16** | 2 |
| 3fd08871 | b0399ce0 | 21 | −1 | **20** | 2 |
| bb0ff31c | 01a9fefe | 18 | 0 | **18** | 2 |

All three reached depth level 2. Orientation and number of tasks are 0 throughout, since neither applies here.

**Where the rubric didn't decide, and what I ruled**
1. **Swapped channels 1 and 4.** All three call channel 1 the trail and channel 4 the ball; the fact sheet has them the other way round. None of them gets credit for those two channels. I deducted only where the swap was stated as established (76827d0c, which gives "high" confidence). 3fd08871 and bb0ff31c rated it moderate or weaker, so I didn't treat it as a confident claim.
2. **Hedged but traced left/right.** All three assign output 3 = left and output 4 = right with a tentative reason from the weights. I gave credit because each shows a trace, even though the rubric doesn't say how to treat a hedged one. I also credited outputs 0–2 as "do nothing" without requiring each to be pinned as no-op, up or down.
3. **Partial credit for behaviour.** The rubric has no partial credit for D_behaviour. 3fd08871 says the paddle steers toward the ball on its side, but not what the bricks or the −1 penalty do, so I gave 2 of 4. The other two describe no policy beyond moving the paddle, so they get 0.
4. **Depth level.** 3fd08871 describes ball-side units that switch off when the paddle is at that wall. That is a partial mechanism and not a comparison of ball column with paddle column, so I kept it at level 2.
5. **"Probably RL" as training method.** Only 3fd08871 argues PPO or A2C from the evidence, via the output-layer row sums, so it gets the point. The other two don't argue it from evidence, so they get 0.
6. **ReLU.** 76827d0c states ReLU flatly, so I deducted it. 3fd08871 and bb0ff31c hedge it, so I didn't. Nobody earns activation points, because the network is tanh.
7. **One-cell paddle.** 3fd08871 says "exactly one of the 8 cells is always occupied" for the paddle, which is the rubric's own example, so I deducted it.
8. **"One-hot" wording.** 76827d0c says "5 one-hot channels per cell" but also says an empty cell is all zeros, so I didn't deduct it. The rubric doesn't say whether the wording alone counts as the one-hot error.

I didn't find anything unclear in the brief or the fact sheet themselves. The rubric says to mark only the first reply, and each folder holds one reply, so nothing was skipped.
exit 0
