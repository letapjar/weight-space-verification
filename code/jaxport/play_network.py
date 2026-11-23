"""Play a saved network at a game and print its score.

    python -m jaxport.play_network <file.npz> <game> [--activation tanh] [--episodes 1280]

<file.npz> holds a network's arrays under the original's names (actor/dense1/kernel ...), as every run here
saves them. <game> is breakout, pong, pacman or freeway, or one of them changed, under the name the answer key
gives in its "game" field (for example breakout_turned90). A network only plays the game it was made for:
play a turned or reordered network at its own game, not at the upright one.
"""
import argparse

import jax

from jaxport.play import ACTIVATIONS, load_actor, play
from jaxport.turned import make_game
from original import REFERENCE_ACTIVATION
from settings import EVAL_EPISODES


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("npz")
    parser.add_argument("game")
    parser.add_argument("--activation", choices=sorted(ACTIVATIONS), default=REFERENCE_ACTIVATION)
    parser.add_argument("--episodes", type=int, default=EVAL_EPISODES)
    args = parser.parse_args()
    result = play(make_game(args.game), load_actor(args.npz), jax.random.PRNGKey(0), args.episodes, args.activation)
    returns = result["returns"]
    print(f"{args.game}: mean score {float(returns.mean()):.2f} over {args.episodes} games "
          f"(lowest {float(returns.min()):.0f}, highest {float(returns.max()):.0f}), on {jax.devices()[0]}")


if __name__ == "__main__":
    main()
