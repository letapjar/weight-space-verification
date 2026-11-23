"""The post's result figures, in the heat maps' style.

    .venv/Scripts/python post_figures.py

Writes into figures/post/:
  held_back/main_table.png   the main table as a picture (the post uses the text table instead)
and post/main_table.md, the same table as text. Both are read from scoring/results.csv (run results_table.py first).
  mixed_networks.png      what a mixed network is, and which game the readers name for it
  prompt_ladder.png       how many networks Opus names as the prompt says less

The first is derived from the results file. The other two rest on counts that are not in that file (the mixed
networks are scored by which of two games is named; two ladder rows are blind judges' marks), so those counts
are stated once here, each with the test in scoring/preregistration_2026-11-20_haiku_effort.md it comes from.
"""
import csv
import os
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

from heatmaps import BACKGROUND, CAPTION_GREY, COLOURS

ROOT = Path(__file__).parent
RESULTS = ROOT / "scoring" / "results.csv"
OUT = ROOT / "figures" / "post"
INK, MUTED = "#1c1c1c", "#444444"
NOT_RUN = "#efe8d4"

# ---- the main table -------------------------------------------------------------------------------------------
# (column title, reader, effort, route) in the order the post discusses them
READERS = [
    ("gpt-6-astra\nhigh", "gpt-6-astra", "high", "API"),
    ("Fable 5.2\nhigh", "fable-5.2", "high", "Claude Code in a container"),
    ("Opus 5.5\nhigh", "opus-5.5", "high", "Claude Code in a container"),
    ("gpt-6.1-terra\nextra high", "gpt-6.1-terra", "xhigh", "API"),
    ("Sonnet 5.5\nhigh", "sonnet-5.5", "high", "Claude Code in a container"),
    ("Haiku 5.5\nextra high", "haiku-5.5", "xhigh", "API"),
]
# (row title, networks form, prompts to look under, first found wins)
FORMS = [
    ("Nothing", "upright (200M steps)", ["mitfull"]),
    ("Board turned 180°", "board turned 180", ["mitfull"]),
    ("Board turned 90°", "board turned 90", ["mitfull"]),
    ("Cells permuted", "cells scrambled", ["mitunordered", "mitcells"]),
    ("All 500 inputs permuted", "all 500 inputs shuffled", ["mitunordered"]),
]


# The count the post shows: the right game named first on the answer line (the user's ruling of 2026-11-22;
# scoring/results.csv also carries the stricter count registered before the reads).
SHOWN = "right_game_first"
# A starred cell and the line under the table that explains it: (reader, row title) -> note.
STARRED = {
    ("fable-5.2", "Board turned 90°"):
        "The one miss is a Pong network. The answer did name Pong, but second: “Breakout — a simplified "
        "paddle-and-ball version with a permanent target/brick row along the top (close to single-player wall "
        "Pong)”. An answer is scored by the first game it names, so it counts as a miss.",
}


def load_results(column: str = SHOWN) -> dict:
    with open(RESULTS, newline="", encoding="utf-8") as handle:
        return {(r["reader"], r["effort"], r["route"], r["prompt"], r["networks_form"]): r[column]
                for r in csv.DictReader(handle)}


# The last row is a different measure, marked by blind judges (judging_shuffled.py writes the counts).
SHUFFLED_TABLE = ROOT / "scoring" / "weights_shuffled.csv"
SHUFFLED_TITLE = "Weights shuffled"
SHUFFLED_NOTE = ("In this row the weights are shuffled within each matrix, the control used in the original experiment, "
                 "which destroys the network: there is no game to name. The count is the replies that recognise this: "
                 "they decline to name a game, or name one while saying the weights do not support it. A reply that "
                 "names a game without saying so is a guess and is not counted. Marked by blind judges.")


def weights_shuffled() -> dict:
    """reader -> (replies that recognise there is nothing to read, replies counted)."""
    with open(SHUFFLED_TABLE, newline="", encoding="utf-8") as handle:
        return {r["reader"]: (int(r["correct_read"]), int(r["reads"])) for r in csv.DictReader(handle)}


def results_by_reader():
    results = load_results()
    figure, axis = plt.subplots(figsize=(15, 8.8), facecolor=BACKGROUND)
    axis.set_facecolor(BACKGROUND)
    notes = []
    for row, (title, form, prompts) in enumerate(FORMS):
        for column, (_, reader, effort, route) in enumerate(READERS):
            score = next((results[key] for prompt in prompts
                          if (key := (reader, effort, route, prompt, form)) in results), None)
            y = len(FORMS) - 1 - row
            if score is None:
                axis.add_patch(Rectangle((column, y), 1, 1, facecolor=NOT_RUN, edgecolor="white", linewidth=3))
                axis.text(column + 0.5, y + 0.5, "not run", ha="center", va="center", fontsize=12, color=CAPTION_GREY)
                continue
            right, total = (int(part) for part in score.split("/"))
            share = right / total
            axis.add_patch(Rectangle((column, y), 1, 1, facecolor=COLOURS(share), edgecolor="white", linewidth=3))
            star = "*" if (reader, title) in STARRED else ""
            if star:
                notes.append("* " + STARRED[reader, title])
            axis.text(column + 0.5, y + 0.5, f"{right} of {total}{star}", ha="center", va="center", fontsize=17,
                      fontweight="bold", color="white" if share > 0.45 else INK)
    judged, low = weights_shuffled(), -1.2  # the judged row sits below the others, after a gap
    for column, (_, reader, *_rest) in enumerate(READERS):
        right, total = judged[reader]
        share = right / total
        axis.add_patch(Rectangle((column, low), 1, 1, facecolor=COLOURS(share), edgecolor="white", linewidth=3))
        axis.text(column + 0.5, low + 0.5, f"{right} of {total}", ha="center", va="center", fontsize=17,
                  fontweight="bold", color="white" if share > 0.45 else INK)
    notes.append("† " + SHUFFLED_NOTE)
    axis.set_xlim(0, len(READERS))
    axis.set_ylim(low, len(FORMS))
    axis.set_xticks([c + 0.5 for c in range(len(READERS))], [title for title, *_ in READERS], fontsize=13)
    axis.set_yticks([len(FORMS) - 0.5 - r for r in range(len(FORMS))] + [low + 0.5],
                    [title for title, *_ in FORMS] + [SHUFFLED_TITLE + "†"], fontsize=13)
    axis.xaxis.tick_top()
    axis.tick_params(length=0)
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.subplots_adjust(left=0.17, right=0.98, top=0.8, bottom=0.22)
    figure.text(0.02, 0.96, "Naming the game with the layout taken away", fontsize=18, fontweight="bold", va="top")
    figure.text(0.02, 0.905, "Networks named correctly, by what was done to the order of the network's inputs. "
                "The network plays identically in the first five rows.", fontsize=11, color=MUTED, va="top")
    footer = ("Twelve networks (four games, three seeds), one read each; the cells out of 36 are three reads each. The reader "
              "is told what the inputs mean. An answer is scored by the first game it names. A read that was refused or cut "
              "off is not counted, which is why some of Haiku's rows are out of 11.")
    figure.text(0.02, 0.18, chr(10).join(textwrap.fill(line, 175) for line in [footer] + notes), fontsize=10,
                color=CAPTION_GREY, va="top", linespacing=1.4)
    figure.savefig(OUT / "held_back" / "main_table_with_shuffled.png", dpi=100, facecolor=BACKGROUND)
    plt.close(figure)


def main_table_markdown():
    """The same table as text, for the post, with a starred note under it for the cells in STARRED."""
    shown = load_results(SHOWN)
    lines = ["| What is done to the inputs | " + " | ".join(", ".join(title.splitlines()) for title, *_ in READERS) + " |",
             "|---" * (len(READERS) + 1) + "|"]
    notes = []
    for title, form, prompts in FORMS:
        cells = []
        for _, reader, effort, route in READERS:
            key = next((k for prompt in prompts if (k := (reader, effort, route, prompt, form)) in shown), None)
            cell = shown[key].replace("/", " of ") if key else "not run"
            if (reader, title) in STARRED:
                cell += "\*"
                notes.append("\* " + STARRED[reader, title])
            cells.append(cell)
        lines.append(f"| {title} | " + " | ".join(cells) + " |")
    judged = weights_shuffled()
    lines.append(f"| **{SHUFFLED_TITLE}**† | " + " | ".join(
        f"{judged[reader][0]} of {judged[reader][1]}" if reader in judged else "not run" for _, reader, *_ in READERS) + " |")
    lines += [""] + notes + ["", "† " + SHUFFLED_NOTE]
    (ROOT / "post" / "main_table.md").write_text(os.linesep.join(lines) + os.linesep, encoding="utf-8", newline="")


# ---- mixed networks -------------------------------------------------------------------------------------------
# (label, first layer's game alone, with another beside it, later layers' game, neither); tests 15, 16, 19, 20
MIXED = [
    ("Opus 5.5 · 500-32-32-5", 9, 2, 0, 1),
    ("gpt-6.1-terra · 500-32-32-5", 11, 0, 0, 1),
    ("Opus 5.5 · blocks in reverse order", 10, 2, 0, 0),
    ("Opus 5.5 · 500-8-512-5 (first layer 37% of the file)", 11, 1, 0, 0),
    ("Opus 5.5 · that shape, blocks in reverse order", 11, 1, 0, 0),
]
GAME_A, GAME_B = "#0c2c63", "#d98a2b"
ANSWER_COLOURS = [GAME_A, "#3d87e8", GAME_B, "#b9b2a0"]
ANSWER_LABELS = ["the first layer's game", "the first layer's game, with another beside it",
                 "the later layers' game", "neither"]


def draw_network(axis, x, colours, title):
    """Three stacked blocks, the first layer much the largest, as in the file."""
    for (bottom, height, name), colour in zip([(1.6, 3.0, "first layer"), (0.8, 0.6, "second layer"),
                                               (0.0, 0.6, "output layer")], colours):
        axis.add_patch(Rectangle((x, bottom), 1.5, height, facecolor=colour, edgecolor="white", linewidth=2))
        axis.text(x + 0.75, bottom + height / 2, name, ha="center", va="center", fontsize=10, color="white")
    axis.text(x + 0.75, 4.85, title, ha="center", va="bottom", fontsize=11, color=INK)


def mixed_networks():
    figure, (diagram, bars) = plt.subplots(1, 2, figsize=(14, 6.2), facecolor=BACKGROUND,
                                           gridspec_kw={"width_ratios": [1, 1.35]})
    for axis in (diagram, bars):
        axis.set_facecolor(BACKGROUND)
        for spine in axis.spines.values():
            spine.set_visible(False)
    draw_network(diagram, 0.0, [GAME_A] * 3, "trained on\nBreakout")
    draw_network(diagram, 2.2, [GAME_B] * 3, "trained on\nPong")
    draw_network(diagram, 5.2, [GAME_A, GAME_B, GAME_B], "mixed:\nplays neither game")
    diagram.add_patch(FancyArrowPatch((3.9, 2.4), (5.0, 2.4), arrowstyle="-|>", mutation_scale=22, color=MUTED, linewidth=2))
    diagram.set_xlim(-0.2, 6.9)
    diagram.set_ylim(-0.3, 5.9)
    diagram.set_xticks([])
    diagram.set_yticks([])

    for row, (label, *counts) in enumerate(MIXED):
        y, left = len(MIXED) - 1 - row, 0
        for count, colour in zip(counts, ANSWER_COLOURS):
            if count:
                bars.barh(y, count, left=left, color=colour, edgecolor="white", linewidth=2, height=0.55)
                bars.text(left + count / 2, y, str(count), ha="center", va="center", fontsize=12, fontweight="bold",
                          color="white")
            left += count
        bars.text(0, y + 0.36, label, ha="left", va="bottom", fontsize=11, color=INK)
    bars.set_xlim(0, 12)
    bars.set_ylim(-0.6, len(MIXED) - 0.2)
    bars.set_yticks([])
    bars.set_xticks([0, 3, 6, 9, 12])
    bars.tick_params(length=0, labelsize=10, colors=CAPTION_GREY)
    bars.set_xlabel("reads, of 12: which game the answer names", fontsize=11, color=MUTED)
    handles = [Rectangle((0, 0), 1, 1, facecolor=colour) for colour in ANSWER_COLOURS]
    bars.legend(handles, ANSWER_LABELS, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False, fontsize=10)

    figure.subplots_adjust(left=0.03, right=0.97, top=0.8, bottom=0.2, wspace=0.08)
    figure.text(0.02, 0.96, "The answer follows the first layer", fontsize=18, fontweight="bold", va="top")
    figure.text(0.02, 0.895, "One game's first layer joined to another game's later layers. The result plays both games at the "
                "level of random, and readers name the first layer's game.", fontsize=11, color=MUTED, va="top")
    figure.savefig(OUT / "mixed_networks.png", dpi=100, facecolor=BACKGROUND)
    plt.close(figure)


# ---- the prompt ladder ----------------------------------------------------------------------------------------
# (what the reader is told, named of 12, how scored); Opus 5.5 at high, upright networks; tests 3, 14, 24, 17
LADDER = [
    ("The grid, the channels and the actions;\n“which game was it trained on?”", 12, "answer line"),
    ("The network's shape only;\n“what was this network trained to do?”", 9, "answer line"),
    ("Nothing; asked for hypotheses\nand a best explanation", 7, "blind judges"),
    ("Nothing;\n“tell me what this is all about”", 4, "blind judges"),
]


def prompt_ladder():
    figure, axis = plt.subplots(figsize=(12, 5.6), facecolor=BACKGROUND)
    axis.set_facecolor(BACKGROUND)
    for row, (label, named, scored) in enumerate(LADDER):
        y = len(LADDER) - 1 - row
        axis.barh(y, 12, color=NOT_RUN, height=0.55)
        axis.barh(y, named, color=COLOURS(named / 12), height=0.55)
        axis.text(named - 0.2, y, f"{named} of 12", ha="right", va="center", fontsize=15, fontweight="bold", color="white")
        axis.text(12.2, y, scored, ha="left", va="center", fontsize=10, color=CAPTION_GREY)
    axis.set_yticks([len(LADDER) - 1 - r for r in range(len(LADDER))], [label for label, *_ in LADDER], fontsize=12)
    axis.set_xlim(0, 13.6)
    axis.set_xticks([])
    axis.tick_params(length=0)
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.subplots_adjust(left=0.36, right=0.98, top=0.78, bottom=0.12)
    figure.text(0.02, 0.96, "How much the prompt is doing", fontsize=18, fontweight="bold", va="top")
    figure.text(0.02, 0.885, "Networks Opus 5.5 names, as the prompt tells it less. The same twelve upright networks in every row.",
                fontsize=11, color=MUTED, va="top")
    figure.text(0.02, 0.05, "With cells permuted: 34 of 36 when told what the inputs mean, 0 of 12 when told only the "
                "network's shape.", fontsize=10, color=CAPTION_GREY, va="center")
    figure.savefig(OUT / "prompt_ladder.png", dpi=100, facecolor=BACKGROUND)
    plt.close(figure)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "held_back").mkdir(exist_ok=True)
    main_table_markdown()
    for draw_figure in (results_by_reader, mixed_networks, prompt_ladder):
        try:
            draw_figure()
        except OSError as error:  # a picture open in a viewer cannot be rewritten on Windows
            print(f"not rewritten ({draw_figure.__name__}): {error}")
    print("wrote", ", ".join(sorted(p.name for p in OUT.glob("*.png"))))


if __name__ == "__main__":
    main()
