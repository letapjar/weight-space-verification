"""Known-good check of the vendored PureJaxRL PPO: train it, unchanged, on Gymnax's
own Breakout-MinAtar and report the learning curve and speed.

    python jaxport/baseline_gymnax.py [total steps] [parallel games]

This is not one of our games. It only shows that the trainer and the JAX install
work, so a later problem can be put down to our game code.
"""
import sys
import time
import types
from pathlib import Path

VENDORED = Path(__file__).parent / "third_party" / "purejaxrl"
sys.path.insert(0, str(VENDORED))
# wrappers.py imports brax and navix for wrappers this check never uses.
for name in ("brax", "brax.envs", "brax.envs.wrappers", "brax.envs.wrappers.training", "navix"):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules["brax"].envs = sys.modules["brax.envs"]
sys.modules["brax.envs.wrappers.training"].EpisodeWrapper = None
sys.modules["brax.envs.wrappers.training"].AutoResetWrapper = None

import jax  # noqa: E402
import numpy as np  # noqa: E402
from ppo import make_train  # noqa: E402

DEFAULT_STEPS = 1_000_000
DEFAULT_ENVS = 64
CURVE_POINTS = 5

config = {
    "LR": 5e-4, "NUM_ENVS": int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_ENVS, "NUM_STEPS": 128,
    "TOTAL_TIMESTEPS": int(float(sys.argv[1])) if len(sys.argv) > 1 else DEFAULT_STEPS,
    "UPDATE_EPOCHS": 4, "NUM_MINIBATCHES": 8, "GAMMA": 0.99, "GAE_LAMBDA": 0.95,
    "CLIP_EPS": 0.2, "ENT_COEF": 0.01, "VF_COEF": 0.5, "MAX_GRAD_NORM": 0.5,
    "ACTIVATION": "tanh", "ENV_NAME": "Breakout-MinAtar", "ANNEAL_LR": True, "DEBUG": False,
}
train = jax.jit(make_train(config))
start = time.time()
out = jax.block_until_ready(train(jax.random.PRNGKey(0)))
first = time.time() - start
start = time.time()  # the second call reuses the compiled program, so this is training time alone
out = jax.block_until_ready(train(jax.random.PRNGKey(1)))
elapsed = time.time() - start

info = out["metrics"]
returns = np.asarray(info["returned_episode_returns"])  # updates x steps x envs
finished = np.asarray(info["returned_episode"])
steps = config["NUM_UPDATES"] * config["NUM_STEPS"] * config["NUM_ENVS"]
print(f"devices {jax.devices()} | {config['NUM_ENVS']} games | {steps:,} steps | compile {first - elapsed:.1f}s "
      f"| run {elapsed:.1f}s | {steps / elapsed:,.0f} steps/s")
for chunk_r, chunk_f in zip(np.array_split(returns, CURVE_POINTS), np.array_split(finished, CURVE_POINTS)):
    print(f"  mean return over finished episodes: {chunk_r[chunk_f].mean():6.2f}  ({chunk_f.sum()} episodes)")
