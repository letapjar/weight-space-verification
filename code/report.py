"""Summarise finished runs and export each policy's weights as text.

    python report.py

Prints every run's score and marks the best seed per activation. It also
(re)writes weights.txt next to each policy; the trainer writes that file too.
"""
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from export import ACTOR_LAYERS, CRITIC_LAYERS, NPZ_FILE, WEIGHTS_FILE, linear_layers, save_npz, weights_text
from games import MAX_EPISODE_STEPS
from original import (ACTOR, CRITIC, ORIGINAL_SCORES, REFERENCE_ACTIVATION, REFERENCE_DIR, REFERENCE_NETWORKS,  # noqa: F401
                      gif_trace, reference_npz, reference_record)
from ppo import MODEL_FILE, RESULT_FILE, RUNS_DIR, VALUE_HEAD_INIT_GAIN, build_mlp, build_policy, evaluate
from settings import HIDDEN_SIZES

SMALL_WEIGHT = 0.05  # |w| below this counts as "near zero" in the summary

def load_results():
    results = []
    for path in sorted(RUNS_DIR.glob(f"*/{RESULT_FILE}")):
        result = json.loads(path.read_text())
        result["dir"] = path.parent
        results.append(result)
    return results


def load_policy(result) -> nn.Sequential:
    """A finished run's policy. The JAX trainer saves only the npz, so that is used when there is no MODEL_FILE."""
    if not (result["dir"] / MODEL_FILE).exists():
        return policy_from_reference_npz(result["dir"] / NPZ_FILE, result["activation"],
                                         tuple(result.get("hidden_sizes", HIDDEN_SIZES)))
    policy = build_policy(result["activation"])
    policy.load_state_dict(torch.load(result["dir"] / MODEL_FILE))
    return policy


def policy_from_weights_text(text: str, activation: str) -> nn.Sequential:
    """Inverse of weights_text: build a policy from a text dump in that layout.

    Any prose around the blocks is ignored; blocks are taken in file order
    (W1, b1, W2, b2, ...) and must fit the policy's layer shapes.
    """
    blocks, current = [], None
    for line in text.splitlines():
        try:
            row = [float(v) for v in line.split()]
        except ValueError:
            row = []
        if row:
            if current is None:
                current = []
                blocks.append(current)
            current.append(row)
        else:
            current = None
    policy = build_policy(activation)
    arrays = iter(np.array(block, dtype=np.float32) for block in blocks)
    with torch.no_grad():
        for layer in linear_layers(policy):
            layer.weight.copy_(torch.from_numpy(next(arrays).T))
            layer.bias.copy_(torch.from_numpy(next(arrays)[0]))
    return policy


def policy_from_reference_npz(path, activation: str = REFERENCE_ACTIVATION, hidden_sizes=HIDDEN_SIZES) -> nn.Sequential:
    """Load an actor from an npz in the original's layout (theirs, or ours from export.save_npz)."""
    return _network_from_npz(path, build_policy(activation, hidden_sizes), ACTOR, ACTOR_LAYERS)


def critic_from_npz(path, activation: str = REFERENCE_ACTIVATION, hidden_sizes=HIDDEN_SIZES):
    """Load the value network from an npz in the original's layout, or None if the file has no critic."""
    if f"{CRITIC}/{CRITIC_LAYERS[0]}/kernel" not in np.load(path, allow_pickle=False).files:
        return None
    return _network_from_npz(path, build_mlp(activation, 1, VALUE_HEAD_INIT_GAIN, hidden_sizes), CRITIC, CRITIC_LAYERS)


def _network_from_npz(path, network, prefix, layer_names) -> nn.Sequential:
    arrays = np.load(path, allow_pickle=False)
    with torch.no_grad():
        for layer, name in zip(linear_layers(network), layer_names):
            layer.weight.copy_(torch.from_numpy(arrays[f"{prefix}/{name}/kernel"].T))
            layer.bias.copy_(torch.from_numpy(arrays[f"{prefix}/{name}/bias"]))
    return network


def weight_summary(policy):
    """Per layer: (mean |w|, largest |w|, share of weights near zero)."""
    rows = []
    for layer in linear_layers(policy):
        magnitude = np.abs(layer.weight.detach().numpy())
        rows.append((magnitude.mean(), magnitude.max(), (magnitude < SMALL_WEIGHT).mean()))
    return rows


def main():
    results = load_results()
    if not results:
        print(f"No finished runs in {RUNS_DIR}")
        return

    best = {}
    for r in results:
        key = (r["game"], r["activation"])
        if key not in best or r["eval_mean"] > best[key]["eval_mean"]:
            best[key] = r

    print(f"{'run':<28}{'steps':>14}{'train mean':>12}{'eval mean':>11}{'median':>8}"
          f"{'min':>6}{'max':>6}{'alive@cap':>11}")
    for r in results:
        marker = "  <- best seed" if best[(r["game"], r["activation"])] is r else ""
        print(f"{r['dir'].name:<28}{r['total_steps']:>14,}{r['final_train_mean_return']:>12.2f}"
              f"{r['eval_mean']:>11.2f}{r['eval_median']:>8.1f}{r['eval_min']:>6.0f}"
              f"{r['eval_max']:>6.0f}{r['eval_still_alive_at_cap']:>11}{marker}")

    for game in sorted({r["game"] for r in results}):
        by_seed = ORIGINAL_SCORES[game]
        scores = ", ".join(f"seed {seed}: {score}" for seed, score in by_seed.items())
        print(f"\nOriginal {game} (tanh, 1B steps), as reported: {scores} | best {max(by_seed.values())}")
        returns, lost = evaluate(policy_from_reference_npz(reference_npz(game)), game)
        print(f"Original {game} network (seed {reference_record(game)['seed']}) scored our way "
              f"(sampled actions, {MAX_EPISODE_STEPS}-step cap): "
              f"mean {returns.mean():.2f} | median {np.median(returns):.1f} | min {returns.min():.0f} | "
              f"max {returns.max():.0f} | alive at cap {(~lost).sum()} of {len(returns)}")

    print(f"\nWeights of the best seed per activation (near zero = |w| < {SMALL_WEIGHT}):")
    print(f"{'run':<28}{'layer':>6}{'mean |w|':>10}{'max |w|':>9}{'near zero':>11}")
    for r in results:
        policy = load_policy(r)
        (r["dir"] / WEIGHTS_FILE).write_text(weights_text(policy))
        if not (r["dir"] / NPZ_FILE).exists():  # runs from before the trainer wrote it: actor only
            save_npz(r["dir"] / NPZ_FILE, policy)
        if best[(r["game"], r["activation"])] is r:
            for k, (mean, largest, small) in enumerate(weight_summary(policy), start=1):
                print(f"{r['dir'].name:<28}{k:>6}{mean:>10.3f}{largest:>9.3f}{small:>10.0%}")
    print(f"\nWrote {WEIGHTS_FILE} into each run folder under {RUNS_DIR}")


if __name__ == "__main__":
    main()
