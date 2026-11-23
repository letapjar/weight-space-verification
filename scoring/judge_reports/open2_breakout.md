judge open2-breakout, model claude-sonnet-5-5, in a container, folders: d545d98a 472fb44c bc26df6b 93b4f9dc b0399ce0 01a9fefe 2db098c5
auth: using DPAPI-encrypted token
I marked 7 replies, one in each of the seven folders you named, and wrote the files to `/work/marks/`. All seven were Breakout, so I used `facts/breakout.md`. I left the other folders alone and opened nothing outside `/work`.

| Folder | Reply id | Board | Core score (max 36) | Name bonus | Orientation bonus |
|---|---|---|---|---|---|
| d545d98a | 3a2ddd88 | normal, 8→512 | 7 | 0 | – |
| 472fb44c | 73e090e2 | normal, 8→512 | 25 | 2 | – |
| bc26df6b | 62fc4628 | normal, 8→512 | 25 | 0 | – |
| 93b4f9dc | 3d79a407 | normal | 27 | 2 | – |
| b0399ce0 | fd2af14f | normal | 18 | 0 | – |
| 01a9fefe | ccfafdb0 | normal | 13 | 2 | – |
| 2db098c5 | a2fc0150 | upside-down | 6 | 0 | 0 |

No reply got a deduction. Every wrong claim was hedged ("probably", "looks like"), so those earned nothing but cost nothing.

The core maximum is 36 on a single-game board, since the tasks item applies only to the multi-game network.

**Rulings where the rubric did not decide**
1. **Name, 62fc4628.** The reply's answer is "Breakout/Catch-style", and it says the exact game is unknown. I treated that as one possibility among several, so it gets 0. If "Breakout-style" alone counts, it would get 2.
2. **Orientation, a2fc0150.** Its channel footprints match the upside-down column exactly, but it reads the game as Frogger or Freeway with the agent at the bottom. I gave 0, since it never says orientation is a convention. If you count footprint-correct as "reads the board correctly", it would get 1.
3. **Grouped "do nothing" outputs.** The rubric says ignored outputs count if the reply says they do nothing.
   - Two replies (73e090e2, 62fc4628) treat outputs 0–2 as interchangeable and ineffective, and trace left and right. Both got 5/5, even though 62fc4628 guesses "fire".
   - ccfafdb0 says 0–2 act as "stay" but cannot say which of 3 and 4 is left. It got 3 for the three ignored outputs and none for left and right.
   - fd2af14f got up wrong ("fire"), so it scored 4.
4. **Border.** A point needs the always-on, bias-copying border. Two replies (73e090e2, 62fc4628) say only that the border is "never trained" or "ignored", and a third (3a2ddd88) says the same without even guessing "walls". All three got 0 for the border. With the 8-unit first layer, the small biases make a copy look like init noise, so the rubric may be hard on those networks.
5. **Channels 1 and 4 (ball and previous frame).** I credited a reply's primary assignment even when it hedged. 01a9fefe left both as "ball or trail" and weakly favoured the swapped reading, so it got no credit for either. fd2af14f described channel 4 as a second moving object (bombs, shots, or a trail), so it got none for channel 4.
6. **Depth, 3d79a407.** This was a borderline call between level 2 and 3. It traces units through to outputs 3 and 4, including one that compares paddle and ball position, so I gave level 3.
7. **Activation and training method.**
   - Every reply guessed or assumed ReLU without arguing it from the weights, so activation is 0 throughout. The net is tanh.
   - Where a reply listed policy-gradient or PPO next to behaviour cloning or a classifier, I counted that as not committing. Training method is 0 throughout.
8. **Layout without kinds, 3a2ddd88.** It gave footprints but never said what each channel is, so layout got 1 of 2.

**Unclear in the brief and rubric**
- The rubric says "mark the first reply only", but each folder holds one reply, so it never came up.
- The brief doesn't say whether "named" or the bonus applies to hedged names ("X or Y-style"). Ruling 1 covers how I handled it.
- The rubric is silent on how to score outputs given as a group. Ruling 3 is my reading.

I first wrote wrong `maximums` into six of the files, then rewrote all seven to match the template. They now match.
exit 0
