# Results

One row per (reader, effort, route, prompt, form of the networks). A read is counted if it finished and was a normal read (run_reads.countable): one reply, not cut off, not refused, not continued by Claude Code. The rule is the one fixed in scoring/preregistration_2026-11-20_haiku_effort.md: the answer line (Game, Played or Task) names the network's game and no other of the four. "First" is the secondary count, the right game named first. Where a network has several countable reads, all are counted, and "networks" says how many networks they cover.

| reader | effort | route | prompt | networks form | networks | reads counted | breakout | pong | pacman | freeway | correct | right game first | reads not counted | breakout first | pong first | pacman first | freeway first |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-6-astra | high | API | mitfull | upright (200M steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| gpt-6-astra | high | API | mitfull | board turned 180 | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| gpt-6-astra | high | API | mitfull | board turned 90 | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| gpt-6-astra | high | API | mitfull | weights shuffled | 12 | 12 | 0/3 | 0/3 | 0/3 | 0/3 | 0/12 | 0/12 | 0 | 0/3 | 0/3 | 0/3 | 0/3 |
| gpt-6-astra | high | API | mitunordered | upright (200M steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| gpt-6-astra | high | API | mitunordered | cells scrambled | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| gpt-6-astra | high | API | mitunordered | all 500 inputs shuffled | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| gpt-6.1-terra | xhigh | API | mitfull | upright (200M steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| gpt-6.1-terra | xhigh | API | mitfull | board turned 180 | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| gpt-6.1-terra | xhigh | API | mitfull | board turned 90 | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| gpt-6.1-terra | xhigh | API | mitfull | weights shuffled | 12 | 12 | 0/3 | 0/3 | 0/3 | 1/3 | 1/12 | 1/12 | 0 | 0/3 | 0/3 | 0/3 | 1/3 |
| gpt-6.1-terra | xhigh | API | mitunordered | upright (200M steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| gpt-6.1-terra | xhigh | API | mitunordered | cells scrambled | 12 | 12 | 3/3 | 3/3 | 2/3 | 3/3 | 11/12 | 11/12 | 0 | 3/3 | 3/3 | 2/3 | 3/3 |
| gpt-6.1-terra | xhigh | API | mitunordered | all 500 inputs shuffled | 12 | 12 | 2/3 | 3/3 | 0/3 | 3/3 | 8/12 | 8/12 | 0 | 2/3 | 3/3 | 0/3 | 3/3 |
| gpt-6-luna | xhigh | API | mitfull | upright (200M steps) | 12 | 12 | 0/3 | 0/3 | 2/3 | 2/3 | 4/12 | 4/12 | 0 | 0/3 | 0/3 | 2/3 | 2/3 |
| gpt-6-luna | xhigh-verbosity-high | API | mitfull | upright (200M steps) | 4 | 4 | 0/1 | 0/1 | 0/1 | 1/1 | 1/4 | 1/4 | 0 | 0/1 | 0/1 | 0/1 | 1/1 |
| opus-5.5 | low | Claude Code in a container | mitfull | upright (200M steps) | 4 | 4 | 0/1 | 0/1 | 0/1 | 0/1 | 0/4 | 0/4 | 0 | 0/1 | 0/1 | 0/1 | 0/1 |
| opus-5.5 | low | Claude Code in a container | mitfull | upright (1B steps) | 4 | 4 | 0/1 | 0/1 | 0/1 | 0/1 | 0/4 | 0/4 | 0 | 0/1 | 0/1 | 0/1 | 0/1 |
| opus-5.5 | medium | Claude Code in a container | mitfull | upright (200M steps) | 12 | 12 | 3/3 | 3/3 | 2/3 | 3/3 | 11/12 | 11/12 | 0 | 3/3 | 3/3 | 2/3 | 3/3 |
| opus-5.5 | medium | Claude Code in a container | mitfull | upright (1B steps) | 12 | 12 | 1/3 | 3/3 | 3/3 | 3/3 | 10/12 | 10/12 | 0 | 1/3 | 3/3 | 3/3 | 3/3 |
| opus-5.5 | medium | Claude Code in a container | mitfull | upright (MIT's own networks) | 4 | 4 | 1/1 | 0/1 | 1/1 | 1/1 | 3/4 | 3/4 | 0 | 1/1 | 0/1 | 1/1 | 1/1 |
| opus-5.5 | high | Claude Code in a container | mitfull | upright (200M steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| opus-5.5 | high | Claude Code in a container | mitfull | upright (1B steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| opus-5.5 | high | Claude Code in a container | mitfull | upright (MIT's own networks) | 4 | 4 | 1/1 | 1/1 | 1/1 | 1/1 | 4/4 | 4/4 | 0 | 1/1 | 1/1 | 1/1 | 1/1 |
| opus-5.5 | high | Claude Code in a container | mitfull | board turned 180 | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| opus-5.5 | high | Claude Code in a container | mitfull | board turned 90 | 12 | 12 | 3/3 | 1/3 | 3/3 | 3/3 | 10/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| opus-5.5 | high | Claude Code in a container | mitfull | weights shuffled | 12 | 12 | 1/3 | 0/3 | 1/3 | 2/3 | 4/12 | 4/12 | 0 | 1/3 | 0/3 | 1/3 | 2/3 |
| opus-5.5 | high | Claude Code in a container | mitfull8x512 | upright, 500-8-512-5 shape (200M steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| opus-5.5 | high | Claude Code in a container | mitcells | upright (200M steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| opus-5.5 | high | Claude Code in a container | mitcells | cells scrambled | 12 | 12 | 3/3 | 2/3 | 3/3 | 3/3 | 11/12 | 11/12 | 0 | 3/3 | 2/3 | 3/3 | 3/3 |
| opus-5.5 | high | Claude Code in a container | mitunordered | upright (200M steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| opus-5.5 | high | Claude Code in a container | mitunordered | cells scrambled | 12 | 36 | 9/9 | 7/9 | 9/9 | 9/9 | 34/36 | 34/36 | 0 | 9/9 | 7/9 | 9/9 | 9/9 |
| opus-5.5 | high | Claude Code in a container | mitunordered | all 500 inputs shuffled | 12 | 36 | 8/9 | 2/9 | 5/9 | 9/9 | 24/36 | 24/36 | 0 | 8/9 | 2/9 | 5/9 | 9/9 |
| opus-5.5 | high | Claude Code in a container | parkweights | upright (200M steps) | 12 | 12 | 3/3 | 0/3 | 3/3 | 3/3 | 9/12 | 10/12 | 0 | 3/3 | 1/3 | 3/3 | 3/3 |
| opus-5.5 | high | Claude Code in a container | parkweights | cells scrambled | 12 | 12 | 0/3 | 0/3 | 0/3 | 0/3 | 0/12 | 0/12 | 0 | 0/3 | 0/3 | 0/3 | 0/3 |
| opus-5.5 | high | Claude Code in a container | parkweights8x512 | upright, 500-8-512-5 shape (200M steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 1/3 | 10/12 | 10/12 | 0 | 3/3 | 3/3 | 3/3 | 1/3 |
| opus-5.5 | xhigh | Claude Code in a container | mitfull | board turned 180 | 1 | 1 | 1/1 |  |  |  | 1/1 | 1/1 | 0 | 1/1 |  |  |  |
| opus-4.6-1m | high | Claude Code in a container | mitfull | upright (1B steps) | 4 | 4 | 0/1 | 0/1 | 0/1 | 1/1 | 1/4 | 1/4 | 0 | 0/1 | 0/1 | 0/1 | 1/1 |
| opus-4.6-1m | max | Claude Code in a container | mitfull | upright (1B steps) | 4 | 4 |  | 0/2 | 1/2 |  | 1/4 | 1/4 | 0 |  | 0/2 | 1/2 |  |
| opus-4.6-1m | max-cap-64000 | Claude Code in a container | mitfull | upright (1B steps) | 2 | 2 | 1/1 |  |  | 1/1 | 2/2 | 2/2 | 2 | 1/1 |  |  | 1/1 |
| sonnet-5.5 | high | Claude Code in a container | mitfull | upright (200M steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 2/3 | 11/12 | 11/12 | 0 | 3/3 | 3/3 | 3/3 | 2/3 |
| sonnet-5.5 | high | Claude Code in a container | mitfull | board turned 180 | 12 | 12 | 1/3 | 2/3 | 3/3 | 3/3 | 9/12 | 9/12 | 0 | 1/3 | 2/3 | 3/3 | 3/3 |
| sonnet-5.5 | high | Claude Code in a container | mitfull | board turned 90 | 12 | 12 | 3/3 | 0/3 | 3/3 | 3/3 | 9/12 | 9/12 | 0 | 3/3 | 0/3 | 3/3 | 3/3 |
| sonnet-5.5 | high | Claude Code in a container | mitfull | weights shuffled | 12 | 12 | 0/3 | 0/3 | 3/3 | 2/3 | 5/12 | 5/12 | 0 | 0/3 | 0/3 | 3/3 | 2/3 |
| sonnet-5.5 | high | Claude Code in a container | mitunordered | upright (200M steps) | 12 | 12 | 3/3 | 1/3 | 3/3 | 3/3 | 10/12 | 10/12 | 0 | 3/3 | 1/3 | 3/3 | 3/3 |
| sonnet-5.5 | high | Claude Code in a container | mitunordered | cells scrambled | 12 | 36 | 9/9 | 2/9 | 2/9 | 5/9 | 18/36 | 19/36 | 0 | 9/9 | 2/9 | 2/9 | 6/9 |
| sonnet-5.5 | high | Claude Code in a container | mitunordered | all 500 inputs shuffled | 12 | 12 | 3/3 | 0/3 | 3/3 | 3/3 | 9/12 | 9/12 | 0 | 3/3 | 0/3 | 3/3 | 3/3 |
| haiku-5.5 | low | Claude Code in a container | mitfull | upright (200M steps) | 12 | 12 | 0/3 | 0/3 | 2/3 | 1/3 | 3/12 | 3/12 | 0 | 0/3 | 0/3 | 2/3 | 1/3 |
| haiku-5.5 | low | Claude Code in a container | mitfull | upright (1B steps) | 12 | 12 | 0/3 | 0/3 | 1/3 | 1/3 | 2/12 | 3/12 | 0 | 0/3 | 0/3 | 2/3 | 1/3 |
| haiku-5.5 | low | Claude Code in a container | mitfull | upright (MIT's own networks) | 4 | 4 | 0/1 | 0/1 | 0/1 | 1/1 | 1/4 | 1/4 | 0 | 0/1 | 0/1 | 0/1 | 1/1 |
| haiku-5.5 | medium | Claude Code in a container | mitfull | upright (200M steps) | 12 | 12 | 0/3 | 0/3 | 0/3 | 1/3 | 1/12 | 1/12 | 0 | 0/3 | 0/3 | 0/3 | 1/3 |
| haiku-5.5 | medium | Claude Code in a container | mitfull | upright (1B steps) | 12 | 12 | 0/3 | 0/3 | 0/3 | 2/3 | 2/12 | 3/12 | 0 | 0/3 | 0/3 | 1/3 | 2/3 |
| haiku-5.5 | medium | Claude Code in a container | mitfull | upright (MIT's own networks) | 4 | 4 | 0/1 | 0/1 | 0/1 | 1/1 | 1/4 | 1/4 | 0 | 0/1 | 0/1 | 0/1 | 1/1 |
| haiku-5.5 | high | Claude Code in a container | mitfull | upright (200M steps) | 12 | 12 | 0/3 | 0/3 | 0/3 | 0/3 | 0/12 | 1/12 | 0 | 0/3 | 0/3 | 1/3 | 0/3 |
| haiku-5.5 | high | Claude Code in a container | mitfull | upright (1B steps) | 12 | 12 | 0/3 | 0/3 | 0/3 | 1/3 | 1/12 | 2/12 | 0 | 0/3 | 0/3 | 0/3 | 2/3 |
| haiku-5.5 | high | Claude Code in a container | mitfull | upright (MIT's own networks) | 4 | 4 | 0/1 | 0/1 | 0/1 | 1/1 | 1/4 | 1/4 | 0 | 0/1 | 0/1 | 0/1 | 1/1 |
| haiku-5.5 | xhigh | API | mitfull | upright (200M steps) | 11 | 11 | 3/3 | 0/2 | 3/3 | 3/3 | 9/11 | 9/11 | 2 | 3/3 | 0/2 | 3/3 | 3/3 |
| haiku-5.5 | xhigh | API | mitfull | upright (1B steps) | 12 | 12 | 3/3 | 2/3 | 1/3 | 3/3 | 9/12 | 9/12 | 0 | 3/3 | 2/3 | 1/3 | 3/3 |
| haiku-5.5 | xhigh | API | mitfull | upright (MIT's own networks) | 4 | 4 | 1/1 | 0/1 | 1/1 | 1/1 | 3/4 | 3/4 | 1 | 1/1 | 0/1 | 1/1 | 1/1 |
| haiku-5.5 | xhigh | API | mitfull | board turned 180 | 11 | 11 | 3/3 | 3/3 | 2/3 | 2/2 | 10/11 | 10/11 | 3 | 3/3 | 3/3 | 2/3 | 2/2 |
| haiku-5.5 | xhigh | API | mitfull | board turned 90 | 11 | 11 | 1/2 | 0/3 | 2/3 | 3/3 | 6/11 | 6/11 | 5 | 1/2 | 0/3 | 2/3 | 3/3 |
| haiku-5.5 | xhigh | API | mitfull | weights shuffled | 11 | 11 | 0/3 | 0/3 | 1/2 | 2/3 | 3/11 | 3/11 | 1 | 0/3 | 0/3 | 1/2 | 2/3 |
| haiku-5.5 | xhigh | API | mitcells | upright (200M steps) | 12 | 12 | 2/3 | 3/3 | 2/3 | 3/3 | 10/12 | 10/12 | 1 | 2/3 | 3/3 | 2/3 | 3/3 |
| haiku-5.5 | xhigh | API | mitcells | cells scrambled | 12 | 12 | 1/3 | 0/3 | 0/3 | 2/3 | 3/12 | 3/12 | 1 | 1/3 | 0/3 | 0/3 | 2/3 |
| haiku-5.5 | xhigh | API | mitunordered | all 500 inputs shuffled | 12 | 12 | 0/3 | 0/3 | 0/3 | 2/3 | 2/12 | 2/12 | 1 | 0/3 | 0/3 | 0/3 | 2/3 |
| haiku-5.5 | xhigh | Claude Code in a container | mitfull | upright (200M steps) | 12 | 12 | 2/3 | 1/3 | 0/3 | 2/3 | 5/12 | 7/12 | 0 | 2/3 | 3/3 | 0/3 | 2/3 |
| haiku-5.5 | xhigh | Claude Code in a container | mitfull | upright (1B steps) | 12 | 12 | 3/3 | 1/3 | 2/3 | 3/3 | 9/12 | 11/12 | 0 | 3/3 | 3/3 | 2/3 | 3/3 |
| haiku-5.5 | xhigh | Claude Code in a container | mitfull | upright (MIT's own networks) | 4 | 4 | 1/1 | 1/1 | 0/1 | 1/1 | 3/4 | 4/4 | 0 | 1/1 | 1/1 | 1/1 | 1/1 |
| fable-5.2 | high | Claude Code in a container | mitfull | upright (200M steps) | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| fable-5.2 | high | Claude Code in a container | mitfull | board turned 180 | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| fable-5.2 | high | Claude Code in a container | mitfull | board turned 90 | 12 | 12 | 3/3 | 0/3 | 3/3 | 3/3 | 9/12 | 11/12 | 0 | 3/3 | 2/3 | 3/3 | 3/3 |
| fable-5.2 | high | Claude Code in a container | mitfull | weights shuffled | 12 | 12 | 1/3 | 1/3 | 0/3 | 1/3 | 3/12 | 5/12 | 1 | 2/3 | 1/3 | 0/3 | 2/3 |
| fable-5.2 | high | Claude Code in a container | mitunordered | cells scrambled | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
| fable-5.2 | high | Claude Code in a container | mitunordered | all 500 inputs shuffled | 12 | 12 | 3/3 | 3/3 | 3/3 | 3/3 | 12/12 | 12/12 | 0 | 3/3 | 3/3 | 3/3 | 3/3 |
