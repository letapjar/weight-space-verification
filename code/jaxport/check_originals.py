"""Print how the original's network plays each JAX game next to its own training record.

    python -m jaxport.check_originals
"""
import time

import jax

from jaxport.games import GAMES
from jaxport.play import load_actor, play
from original import recorded_play, reference_npz


def main():
    print(f"device {jax.devices()[0]}")
    for name, game in GAMES.items():
        recorded, start = recorded_play(name), time.time()
        result = play(game(), load_actor(reference_npz(name)), jax.random.PRNGKey(0), recorded["episodes"])
        share = result["action_counts"] / result["action_counts"].sum()
        print(f"{name:<9} return {result['returns'].mean():6.2f} (record {recorded['mean_return']:6.2f}) | "
              f"length {result['lengths'].mean():6.1f} (record {recorded['mean_length']:6.1f}) | "
              f"{recorded['episodes']} episodes in {time.time() - start:.1f}s")
        print(f"{'':<9} actions " + " ".join(f"{ours:.3f}/{theirs:.3f}" for ours, theirs in zip(share, recorded["action_usage"])))


if __name__ == "__main__":
    main()
