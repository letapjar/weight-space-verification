"""One picture of the Haiku effort study, for post/haiku_effort_study.md.

    .venv/Scripts/python haiku_effort_figure.py

Counts come from scoring/results.csv (run results_table.py first); thinking and time come from each read's
record.json. Writes post/haiku_effort_study.png.
"""
import csv
import json
import statistics
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from heatmaps import BACKGROUND, CAPTION_GREY, COLOURS
from post_figures import INK, MUTED, NOT_RUN, RESULTS, ROOT

READER, ROUTE, PROMPT = "haiku-5.5", "Claude Code in a container", "mitfull"
EFFORTS = [("low", "low"), ("medium", "medium"), ("high", "high"), ("xhigh", "extra high")]
SETS = [("upright (200M steps)", "our networks, 200 million steps", "#3d87e8"),
        ("upright (1B steps)", "our networks, a billion steps", "#0c2c63")]
GAMES = [("breakout", "Breakout"), ("freeway", "Freeway"), ("pacman", "Pac-Man"), ("pong", "Pong")]
CHANCE = 3  # of 12: four games, guessing


def rows() -> dict:
    with open(RESULTS, newline="", encoding="utf-8") as handle:
        return {(r["effort"], r["networks_form"]): r for r in csv.DictReader(handle)
                if (r["reader"], r["route"], r["prompt"]) == (READER, ROUTE, PROMPT)}


def of(text: str) -> tuple:
    right, total = text.split("/")
    return int(right), int(total)


def thinking_and_time() -> dict:
    found = {effort: ([], []) for effort, _ in EFFORTS}
    for path in (ROOT / "readings").glob(f"*/{READER}_*_container_{PROMPT}_1/record.json"):
        effort = path.parent.name.split("_")[1]
        record = json.loads(path.read_text(encoding="utf-8"))
        if effort in found and record.get("normal_read"):
            found[effort][0].append(record["usage"]["output_tokens_details"]["thinking_tokens"])
            found[effort][1].append(record["seconds"])
    return {effort: (statistics.median(tokens), statistics.median(seconds), sum(t == 0 for t in tokens), len(tokens))
            for effort, (tokens, seconds) in found.items()}


def plain(axis):
    axis.set_facecolor(BACKGROUND)
    axis.tick_params(length=0)
    for spine in axis.spines.values():
        spine.set_visible(False)


def main():
    data, effort_stats = rows(), thinking_and_time()
    figure = plt.figure(figsize=(15, 9.4), facecolor=BACKGROUND)
    grid = figure.add_gridspec(2, 3, height_ratios=[1.15, 1], left=0.06, right=0.98, top=0.84, bottom=0.07,
                               hspace=0.42, wspace=0.28)

    # correct of 12 by effort, both sets
    bars = figure.add_subplot(grid[0, :2])
    plain(bars)
    width = 0.36
    for index, (form, label, colour) in enumerate(SETS):
        for position, (effort, _) in enumerate(EFFORTS):
            named, _ = of(data[effort, form]["right_game_first"])
            x = position + (index - 0.5) * width
            bars.bar(x, named, width * 0.92, color=colour, label=label if position == 0 else None)
            bars.text(x, named + 0.25, str(named), ha="center", va="bottom", fontsize=13, fontweight="bold", color=INK)
    bars.axhline(CHANCE, color=CAPTION_GREY, linewidth=1.2, linestyle=":")
    bars.text(len(EFFORTS) - 0.42, CHANCE + 0.15, "guessing", fontsize=10, color=CAPTION_GREY, ha="right")
    bars.set_xticks(range(len(EFFORTS)), [label for _, label in EFFORTS], fontsize=13)
    bars.set_ylim(0, 13.2)
    bars.set_yticks([0, 3, 6, 9, 12])
    bars.tick_params(axis="y", labelsize=10, colors=CAPTION_GREY)
    bars.set_title("Networks named correctly, of 12", fontsize=13, loc="left", color=INK, pad=10)
    bars.legend(frameon=False, fontsize=11, loc="upper left")
    bars.text(0.0, -0.17, "An answer is scored by the first game it names.", transform=bars.transAxes, fontsize=10,
              color=CAPTION_GREY)

    # thinking per effort
    thinking = figure.add_subplot(grid[0, 2])
    plain(thinking)
    for position, (effort, _) in enumerate(EFFORTS):
        tokens, seconds, none, reads = effort_stats[effort]
        thinking.bar(position, tokens, 0.62, color=COLOURS((position + 1) / len(EFFORTS)))
        note = f"{tokens:,.0f}\n{seconds:.0f} s" + (f"\n{none} of {reads} reads\nwith none" if none else "")
        thinking.text(position, tokens + 1500, note, ha="center", va="bottom", fontsize=10, color=INK)
    thinking.set_xticks(range(len(EFFORTS)), [label for _, label in EFFORTS], fontsize=11)
    thinking.set_yticks([])
    thinking.set_ylim(0, max(stats[0] for stats in effort_stats.values()) * 1.3)
    thinking.set_title("Thinking per read (median tokens, seconds)", fontsize=13, loc="left", color=INK, pad=10)

    # by game, one grid per set
    for index, (form, label, _) in enumerate(SETS):
        axis = figure.add_subplot(grid[1, index])
        plain(axis)
        for row, (game, _) in enumerate(GAMES):
            for column, (effort, _) in enumerate(EFFORTS):
                right, total = of(data[effort, form][f"{game}_first"])
                y = len(GAMES) - 1 - row
                axis.add_patch(Rectangle((column, y), 1, 1, facecolor=COLOURS(right / total) if right else NOT_RUN,
                                         edgecolor=BACKGROUND, linewidth=3))
                axis.text(column + 0.5, y + 0.5, f"{right} of {total}", ha="center", va="center", fontsize=12,
                          fontweight="bold", color="white" if right / total > 0.45 else INK)
        axis.set_xlim(0, len(EFFORTS))
        axis.set_ylim(0, len(GAMES))
        axis.set_xticks([c + 0.5 for c in range(len(EFFORTS))], [name for _, name in EFFORTS], fontsize=11)
        axis.set_yticks([len(GAMES) - 0.5 - r for r in range(len(GAMES))], [name for _, name in GAMES], fontsize=12)
        axis.set_title(f"By game: {label}", fontsize=13, loc="left", color=INK, pad=10)

    notes = figure.add_subplot(grid[1, 2])
    plain(notes)
    notes.set_xticks([])
    notes.set_yticks([])
    notes.text(0, 0.95, "Reading it", fontsize=13, color=INK, va="top")
    lines = ["Only extra high beats guessing.",
             "It is not a steady climb: low, medium and high are all at or below guessing.",
             "Breakout and Pong are never named below extra high.",
             "Better-trained networks are read better at extra high: 11 against 7 of 12."]
    notes.text(0, 0.80, (chr(10) * 2).join(textwrap.fill("• " + line, 42, subsequent_indent="  ") for line in lines),
               fontsize=11.5, color=MUTED, va="top", linespacing=1.35)

    figure.text(0.02, 0.965, "Does Haiku's reading depend on effort?", fontsize=19, fontweight="bold", va="top")
    figure.text(0.02, 0.915, "Haiku 5.5 given a network's weights and a full description of its inputs, and asked which game it "
                "was trained on. One read per network per effort level; no tools.", fontsize=11, color=MUTED, va="top")
    figure.savefig(ROOT / "post" / "haiku_effort_study.png", dpi=100, facecolor=BACKGROUND)
    print("wrote post/haiku_effort_study.png")
    for effort, _ in EFFORTS:
        print(effort, effort_stats[effort])


if __name__ == "__main__":
    main()
