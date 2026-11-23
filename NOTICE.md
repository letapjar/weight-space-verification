# Third-party material

The MIT License in `LICENSE` covers this project's own code and write-up. The following is other people's
work, included or built on here under its own terms.

**PureJaxRL** (https://github.com/luchris429/purejaxrl), Apache License 2.0.
`code/jaxport/third_party/purejaxrl/` is an unmodified copy of its `ppo.py` and `wrappers.py`, with its
`LICENSE`. `code/jaxport/ppo.py` is a modified version of that `ppo.py`: the same algorithm, changed to train
several networks side by side, to save and resume, and to use this project's games. Those two files stay
under the Apache License 2.0.

**The original experiment** (Takehi, Teoh, Zhang and Khattab, *Sparks of Weight-Space Programming*, 2026, and
its logs repository), used under the Creative Commons Attribution 4.0 International licence (CC BY 4.0,
https://creativecommons.org/licenses/by/4.0/legalcode), which its logs repository gives for its logs, data and
networks.
- `prompts/mitfull.txt` is its prompt, unchanged.
- Every other prompt whose name begins `mit` is that prompt with changes made here: the sentences named in
  `answer_key/prompts.json` are reworded, added or removed.
- Four of the files in `weights/` are its published networks (the answer key marks them). The numbers are
  unchanged; the text layout around them is this project's. The matching files in `networks/` are its own
  network files, unchanged.
- `code/reference/` holds those four network files and their training records unchanged, and
  `gif_trace.json`, each of its published animations decoded here to one entry per step.

**Juho Park's reproduction.** `prompts/parkweights.txt` is his weights-only preamble, unchanged, and
`prompts/parkweights8x512.txt` is the same with the network's shape restated. They are included with credit so
the reads can be checked, and belong to their author.

**The games** in `code/games.py` and `code/jaxport/games.py` follow the grid layout of the original experiment
and were written for this project from its published description and recordings. They are not copied from
MinAtar or Gymnax; `code/jaxport/env.py` follows the shape of Gymnax's environment interface so that
PureJaxRL's trainer can use it.

Libraries this code imports (JAX, Flax, Optax, Distrax, NumPy, PyTorch, Matplotlib, and the Anthropic and
OpenAI SDKs) are not included here.
