"""Heat maps of a network's first layer, laid out on the board: one row of maps per network, one map per channel.

    python heatmaps.py out.png --title "..." "Upright=93b4f9dc" "Scrambled=aa5e444d" "Scrambled, put back=aa5e444d:restored"

Each network is a blind id with the label to print beside its row. A map is the GRID_SIZE x GRID_SIZE grid in
the order the inputs come in the file (row 0 at the top); a cell's colour is the size of its first-layer weights
(the length of the 32 weights leaving that input), from 0 (palest) to the map's maximum (darkest), which is
printed under the map. The scale never ends below SCALE_FLOOR, so a channel the network barely uses looks pale
and not dark (the Turing Institute note's figure does the same). After the id:
    :restored   puts a turned or scrambled network's cells back where the game has them, using what its result
                file records, so the upright picture can be seen again
    :channels   puts the five channels in a shuffled order, the same for every cell (whole inputs move)
    :inputs     puts all 500 inputs in a shuffled order, each on its own (whole inputs move; no groups of five)
    :shuffled   shuffles every first-layer weight among all the others, as the Turing Institute note's control
                does: the network no longer computes anything
--columns positions titles the maps by where their inputs sit in the file, for figures where a column no longer
holds one channel.

Reads the blind files and the answer key only; runs no network and calls no model.
"""
import argparse
import json

import matplotlib
import numpy as np

matplotlib.use("Agg")  # write files; open no window
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from blind import ANSWER_KEY, BLIND_DIR, PROJECT_DIR  # noqa: E402
from spec import GRID_SIZE, NUM_CHANNELS, OBS_SHAPE, OBS_SIZE, Channel  # noqa: E402

RESTORED, SHUFFLED = "restored", "shuffled"  # after "<blind id>:"
SHUFFLE_SEED = 0
SCALE_FLOOR = 1.5  # a map's colour scale runs from 0 to its maximum, or to this if its maximum is smaller
CHANNEL_LABELS = {Channel.AGENT: "agent", Channel.MOVING: "moving objects", Channel.TARGET: "reward targets",
                  Channel.OBSTACLE: "obstacles", Channel.PREVIOUS: "previous frame"}
COLOURS = LinearSegmentedColormap.from_list("pale_to_navy", ["#c6dbf9", "#3d87e8", "#0c2c63"])
BACKGROUND, CAPTION_GREY = "#fbf5e4", "#8a8474"  # cream, as the user asked, after the Turing note's figure
LINE_BREAK, LABEL_BREAK = chr(10), "/"  # "Breakout/93b4f9dc=93b4f9dc" prints the label on two lines
SUBTITLE = (f"Each map is the {GRID_SIZE} x {GRID_SIZE} grid in the order the inputs come in the file (row 0 at the top); a cell's "
            "colour is the size of its 32 first-layer weights," + LINE_BREAK
            + "from 0 (palest) to the map's own maximum (darkest; the value below "
            f"the map, and at least {SCALE_FLOOR}).")


def first_layer(blind_id: str) -> np.ndarray:
    """The first-layer weights as the blind file gives them: one row per input."""
    lines = (BLIND_DIR / f"{blind_id}.txt").read_text(encoding="utf-8").splitlines()
    return np.array([[float(value) for value in line.split()] for line in lines[1:1 + OBS_SIZE]])


def cell_sizes(weights: np.ndarray) -> np.ndarray:
    """(channel, row, column): the length of the weights leaving each input."""
    return np.linalg.norm(weights, axis=1).reshape(GRID_SIZE, GRID_SIZE, NUM_CHANNELS).transpose(2, 0, 1)


def game_order(blind_id: str) -> np.ndarray:
    """perm, with the network's inputs in the game's own order == its inputs in file order [perm]: the reverse of
    the turn or shuffle its result file records. The identity for a network that was never reordered."""
    network = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))[blind_id]
    result = json.loads((PROJECT_DIR / network["source"] / "result.json").read_text(encoding="utf-8"))
    inputs = np.arange(OBS_SIZE)
    # The two reorderings as jaxport/turned.py defines them (scrambled_inputs, turned_inputs). That module needs
    # JAX, which this environment lacks; test_heatmaps.py checks these against the upright source networks.
    if "scrambled_cells" in result:
        file_from_game = inputs.reshape(-1, NUM_CHANNELS)[result["scrambled_cells"]].reshape(-1)
    elif "shuffled_inputs" in result:
        file_from_game = np.asarray(result["shuffled_inputs"])
    elif "turned_degrees" in result:
        file_from_game = np.rot90(inputs.reshape(OBS_SHAPE), result["turned_degrees"] // 90, axes=(0, 1)).reshape(-1)
    else:
        return inputs
    return np.argsort(file_from_game)


def row_of_maps(spec: str):
    """(label, maps) for one "<label>=<blind id>" or "<label>=<blind id>:restored"."""
    label, _, network = spec.partition("=")
    blind_id, _, how = network.partition(":")
    weights = first_layer(blind_id)
    if how and how not in REORDERINGS:
        raise SystemExit(f"after ':' give one of {', '.join(REORDERINGS)}, not {how!r}")
    if how:
        weights = REORDERINGS[how](blind_id, weights, np.random.default_rng(SHUFFLE_SEED))
    return label.replace(LABEL_BREAK, LINE_BREAK), cell_sizes(weights)  # a label may be given on two lines


def channels_reordered(weights: np.ndarray, rng) -> np.ndarray:
    """The five channels in a shuffled order, the same for every cell: whole inputs move, none is broken up."""
    order = rng.permutation(NUM_CHANNELS)
    while np.array_equal(order, np.arange(NUM_CHANNELS)) or np.any(order == np.arange(NUM_CHANNELS)):
        order = rng.permutation(NUM_CHANNELS)  # every channel in a new position, so each column changes
    return weights.reshape(-1, NUM_CHANNELS, weights.shape[1])[:, order].reshape(weights.shape)


# What may follow "<blind id>:": (blind id, first layer in file order, a seeded generator) -> the first layer to draw.
# The first four move whole inputs (each input keeps its 32 weights), which leaves what the network computes
# unchanged when the board is fed in the same order; the last breaks every input up.
REORDERINGS = {
    RESTORED: lambda blind_id, weights, rng: weights[game_order(blind_id)],
    "channels": lambda blind_id, weights, rng: channels_reordered(weights, rng),
    "inputs": lambda blind_id, weights, rng: weights[rng.permutation(OBS_SIZE)],
    SHUFFLED: lambda blind_id, weights, rng: rng.permutation(weights.reshape(-1)).reshape(weights.shape),
}


COLUMN_TITLES = {  # --columns: what to print above each map
    "channels": lambda channel: f"ch {int(channel)}: {CHANNEL_LABELS[channel]}",
    "positions": lambda channel: f"inputs {int(channel)}, {int(channel) + NUM_CHANNELS}, {int(channel) + 2 * NUM_CHANNELS}, ...",
}


def draw(rows: list, title: str, out: str, subtitle: str = SUBTITLE, columns: str = "channels"):
    figure, axes = plt.subplots(len(rows), NUM_CHANNELS, figsize=(15.8, 3.15 * len(rows) + 2.2), squeeze=False,
                                facecolor=BACKGROUND)
    for row, ((label, maps), row_axes) in enumerate(zip(rows, axes)):
        for channel, axis in zip(Channel, row_axes):
            grid = maps[channel]
            axis.pcolormesh(grid, cmap=COLOURS, vmin=0, vmax=max(grid.max(), SCALE_FLOOR), edgecolors="white", linewidth=1.2)
            axis.invert_yaxis()  # row 0 at the top
            axis.set_aspect("equal")
            axis.axis("off")
            axis.text(0.5, -0.02, f"max {grid.max():.1f}", transform=axis.transAxes, ha="center", va="top",
                      fontsize=10, color=CAPTION_GREY)
            if row == 0:
                axis.set_title(COLUMN_TITLES[columns](channel), fontsize=14, pad=8)
        row_axes[0].text(-0.08, 0.5, label, transform=row_axes[0].transAxes, ha="right", va="center", fontsize=14,
                         multialignment="right")
    top = 1 - 2.0 / figure.get_figheight()
    figure.subplots_adjust(left=0.165, right=0.985, top=top, bottom=0.05, wspace=0.09, hspace=0.2)
    figure.text(0.02, 1 - 0.42 / figure.get_figheight(), title, fontsize=18, fontweight="bold", va="top")
    figure.text(0.02, 1 - 0.92 / figure.get_figheight(), subtitle, fontsize=11, color="#444444", va="top")
    figure.savefig(out, dpi=100, facecolor=BACKGROUND)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", help="the PNG to write")
    parser.add_argument("networks", nargs="+", metavar="LABEL=BLIND_ID[:restored]")
    parser.add_argument("--title", default="First-layer weights, laid out on the board")
    parser.add_argument("--columns", choices=list(COLUMN_TITLES), default="channels")
    args = parser.parse_args()
    draw([row_of_maps(spec) for spec in args.networks], args.title, args.out, columns=args.columns)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
