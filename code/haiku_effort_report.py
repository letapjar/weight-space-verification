"""Score the effort tests as their prediction file says (scoring/preregistration_2026-11-20_haiku_effort.md).

    python haiku_effort_report.py

Takes every finished container read of the `mitfull` prompt, puts each reply's Game line in its box, and prints,
for each reader and each set of networks: correct counts by game and effort, the boxes, the table of answers by
true game, and the shuffle test against chance. Then the share of Pong and Pac-Man answers that reach for a
MinAtar game, and every Game line. The scoring rule is readings.game_line_box; nothing here decides anything.
"""
import json
import random
import sys
from collections import Counter

from layout import ANSWER_KEY, SCORING_DIR, reply_path
from readings import (BOX_CORRECT, BOX_HEDGED, BOX_OTHER, BOX_OTHER_MINATAR, BOX_WRONG, FILE_PATTERN, GAME_KEYWORDS,
                      READINGS_DIR, answers_with_a_minatar_game, first_game_named, game_line_box, games_named)
from run_reads import RECORD_FILE, countable

PROMPT, DELIVERY = "mitfull", "container"
READERS = ("haiku-5.5", "opus-5.5", "opus-4.6-1m")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
GAMES = tuple(GAME_KEYWORDS)  # breakout, pong, pacman, freeway
# The sets of networks, by the start of the run folder each came from, in the order they are reported.
SETS = (("OUR MATCHED SET (200 million steps)", "runs_jax_single_c256_lr_0.005"),
        ("OUR BILLION-STEP SET (the original author's recipe)", "runs_jax_snapshots"),
        ("THE ORIGINAL AUTHOR'S NETWORKS", "original"))
NOT_IN_MINATAR = ("pong", "pacman")
SHUFFLES, SHUFFLE_SEED = 10_000, 0
SEVERAL = "several of the four"
BOXES = (BOX_CORRECT, BOX_HEDGED, BOX_WRONG, BOX_OTHER_MINATAR, BOX_OTHER)
REPORT_FILE = SCORING_DIR / "haiku_effort_report.txt"


def load():
    """One row per countable container read of the prompt: reader, effort, the network's set and game, the reply."""
    key = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))
    rows = []
    for record in sorted(READINGS_DIR.glob(f"*/*_{DELIVERY}_{PROMPT}_*/{RECORD_FILE}")):
        if not countable(json.loads(record.read_text(encoding="utf-8"))):
            continue  # unfinished, cut off, or continued by Claude Code after the output limit
        name = FILE_PATTERN.fullmatch(record.parent.name + ".txt")
        blind_id = record.parent.parent.name
        network = key[blind_id]
        group = next((title for title, source in SETS if network["source"].startswith(source)), None)
        if group is None or name["model"] not in READERS or name["effort"] not in EFFORTS:
            continue
        reply = reply_path(record.parent).read_text(encoding="utf-8")
        rows.append({"blind_id": blind_id, "game": network["game"], "seed": network["seed"], "set": group,
                     "reader": name["model"], "effort": name["effort"], "reply": reply})
    return rows


def answer_column(reply: str, true_game: str) -> str:
    """Which column of the answers table a reply belongs in."""
    box, answer = game_line_box(reply, true_game)
    named = games_named(answer)
    if len(named) == 1:
        return named[0]
    return SEVERAL if named else box  # the two boxes for a line naming none of the four


def count_correct(rows, games=None) -> int:
    games = games or [row["game"] for row in rows]
    return sum(game_line_box(row["reply"], game)[0] == BOX_CORRECT for row, game in zip(rows, games))


def fraction(rows) -> str:
    return f"{count_correct(rows)}/{len(rows)}" if rows else "-"


def shuffle_share(rows) -> float:
    """The share of shuffles, true games dealt at random among the replies of the same effort, that score at
    least as many correct as the real pairing."""
    generator = random.Random(SHUFFLE_SEED)
    real, at_least = count_correct(rows), 0
    by_effort = [[row for row in rows if row["effort"] == effort] for effort in EFFORTS]
    for _ in range(SHUFFLES):
        shuffled = 0
        for group in by_effort:
            games = [row["game"] for row in group]
            generator.shuffle(games)
            shuffled += count_correct(group, games)
        at_least += shuffled >= real
    return at_least / SHUFFLES


def section(title: str, rows: list) -> list:
    efforts = [effort for effort in EFFORTS if any(r["effort"] == effort for r in rows)]
    out = [title, f"  {'game':<9}" + "".join(f"{effort:>9}" for effort in efforts) + "      all   (correct / reads)"]
    for game in GAMES:
        of_game = [r for r in rows if r["game"] == game]
        cells = [fraction([r for r in of_game if r["effort"] == effort]) for effort in efforts]
        out.append(f"  {game:<9}" + "".join(f"{c:>9}" for c in cells) + f"{fraction(of_game):>9}")
    totals = [fraction([r for r in rows if r["effort"] == effort]) for effort in efforts]
    out.append(f"  {'all':<9}" + "".join(f"{c:>9}" for c in totals) + f"{fraction(rows):>9}")
    boxes = Counter(game_line_box(r["reply"], r["game"])[0] for r in rows)
    out.append("  boxes: " + ", ".join(f"{box} {boxes[box]}" for box in BOXES))
    first = [f"{sum(first_game_named(r['reply']) == r['game'] for r in rows if r['effort'] == effort)}/"
             f"{sum(r['effort'] == effort for r in rows)}" for effort in efforts]
    out.append(f"  secondary count, the right game named FIRST on the line (alternatives after it ignored):"
               + "".join(f"{c:>9}" for c in first)
               + f"{sum(first_game_named(r['reply']) == r['game'] for r in rows):>6}/{len(rows)}")
    columns = GAMES + (SEVERAL, BOX_OTHER_MINATAR, BOX_OTHER)
    out.append("  answers by true game (rows: true game; columns: what the Game line named):")
    out.append(f"    {'':<9}" + "".join(f"{c[:20]:>22}" for c in columns))
    for game in GAMES:
        counts = Counter(answer_column(r["reply"], game) for r in rows if r["game"] == game)
        out.append(f"    {game:<9}" + "".join(f"{counts[c]:>22}" for c in columns))
    shares = [f"all {shuffle_share(rows):.4f}"] + [
        f"{effort} {shuffle_share([r for r in rows if r['effort'] == effort]):.4f}" for effort in efforts]
    out.append(f"  shuffle test, share of {SHUFFLES:,} shuffles scoring at least the real number correct: " + ", ".join(shares))
    reach = [r for r in rows if r["game"] in NOT_IN_MINATAR]
    out.append(f"  MinAtar measure: of the {len(reach)} Pong and Pac-Man reads, "
               f"{sum(answers_with_a_minatar_game(r['reply']) for r in reach)} have a Game line naming a MinAtar game or MinAtar")
    return out + [""]


def main():
    rows = load()
    out = [f"Effort tests: {len(rows)} finished container reads under the `{PROMPT}` prompt. Only a Game line in the "
           f"box \"{BOX_CORRECT}\" counts as identified.", ""]
    for reader in READERS:
        for title, _ in SETS:
            group = [r for r in rows if r["reader"] == reader and r["set"] == title]
            if group:
                out += section(f"{reader.upper()}  |  {title}  |  {len(group)} reads", group)
    out.append("EVERY GAME LINE (reader, set, network, true game, seed, effort, box: the line)")
    order = [title for title, _ in SETS]
    for r in sorted(rows, key=lambda r: (READERS.index(r["reader"]), order.index(r["set"]), r["game"],
                                         EFFORTS.index(r["effort"]), r["seed"])):
        box, answer = game_line_box(r["reply"], r["game"])
        out.append(f"  {r['reader']:<10} {r['set'][:14]:<14} {r['blind_id']} {r['game']:<8} s{r['seed']} {r['effort']:<7} "
                   f"{box:<28} {answer[:130]}")
    REPORT_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")  # the replies hold characters a Windows console code page lacks
    print("\n".join(out))


if __name__ == "__main__":
    main()
