"""Play a hand-written network at one of our games.

    python experiments/play_npz.py <file.npz> [--activation relu] [--game breakout] [--steps 5000] [--episodes 256]

The file holds W1, b1, W2, b2, W3, b3 with each weight matrix as (units out, units in), the way the model that
wrote it listed them. A file in the original's layout (actor/dense1/kernel ..., as our runs save) plays too, for
comparison. --steps plays with an episode limit other than the game's own 200. Scored as every network here is: 1,280 games, actions sampled from the softmax of the
outputs, and again taking the largest output every step. Runs on the processor; nothing is written.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from export import linear_layers  # noqa: E402
import games  # noqa: E402
from games import GAMES  # noqa: E402
import ppo  # noqa: E402
from ppo import EVAL_EPISODES, EVAL_SEED, build_policy, evaluate  # noqa: E402
from report import policy_from_reference_npz  # noqa: E402


def policy_from_listed_npz(path: Path, activation: str):
    arrays = np.load(path, allow_pickle=False)
    if "W1" not in arrays.files:  # one of our runs, or the original's: the trainer's own layout
        return policy_from_reference_npz(path, activation)
    weights = [arrays[f"W{k}"] for k in range(1, 1 + len(arrays.files) // 2)]
    policy = build_policy(activation, tuple(weight.shape[0] for weight in weights[:-1]))
    with torch.no_grad():
        for k, layer in enumerate(linear_layers(policy), start=1):
            layer.weight.copy_(torch.from_numpy(arrays[f"W{k}"].astype(np.float32)))
            layer.bias.copy_(torch.from_numpy(arrays[f"b{k}"].astype(np.float32)))
    return policy


def play_greedy(policy, game_name: str, episodes: int = EVAL_EPISODES):
    """As ppo.evaluate, but taking the largest output every step."""
    game = GAMES[game_name](num_envs=episodes, seed=EVAL_SEED)
    obs = game.reset()
    returns, done, lost = np.zeros(episodes), np.zeros(episodes, dtype=bool), np.zeros(episodes, dtype=bool)
    for _ in range(games.MAX_EPISODE_STEPS):
        with torch.no_grad():
            actions = policy(torch.from_numpy(obs)).argmax(dim=1).numpy()
        obs, reward, terminal = game.step(actions)
        returns += reward * ~done
        lost |= terminal & ~game.timed_out & ~done
        done |= terminal
    return returns, lost


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("npz", type=Path)
    parser.add_argument("--activation", default="relu")
    parser.add_argument("--game", default="breakout")
    parser.add_argument("--steps", type=int, default=games.MAX_EPISODE_STEPS, help="the episode limit")
    parser.add_argument("--episodes", type=int, default=EVAL_EPISODES)
    args = parser.parse_args()
    games.MAX_EPISODE_STEPS = ppo.MAX_EPISODE_STEPS = args.steps  # read at each step, here and in ppo.evaluate
    policy = policy_from_listed_npz(args.npz, args.activation)
    for label, play in (("sampled from the softmax", evaluate), ("largest output each step", play_greedy)):
        returns, lost = play(policy, args.game, args.episodes)
        print(f"{args.game}, limit {args.steps} steps, {label}: mean {returns.mean():.2f}, lowest {returns.min():.0f}, highest "
              f"{returns.max():.0f}, still alive at the step limit {int((~lost).sum())} of {len(returns)}")
