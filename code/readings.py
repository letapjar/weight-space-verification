"""Track what readers said about the blind weight files, and score it against the answer key.

    python readings.py

Readings live in READINGS_DIR, one folder per blind id, one text file per read:

    readings/<blind id>/<model>_<effort>_<delivery>_<prompt>_<n>.txt
    readings/fdbe6bc4/opus-5.5_medium_file_open_1.txt

Fields are separated by underscores, so none may contain one (write `opus-5.5`,
not `opus_5_5`). `delivery` says how the weights reached the reader (see
DELIVERIES), `prompt` is a short label for the question asked (see PROMPTS) and
`n` numbers repeat reads. The file is the reader's reply as text, ideally with the prompt
at the top. This script joins every reading with the answer key, works out
which game (if any) the reply named, prints a table per network and a tally per
game, activation, rate and model, and writes the same to SUMMARY_FILE.

Scoring follows the original experiment: the reply's `Game:` (or `Answer:`) line
is mapped to a game by keywords. A reply with no such line is not scored; the games it
mentions anywhere are listed so a person can judge it.
"""
import argparse
import csv
import json
import re
from collections import defaultdict

from layout import ANSWER_KEY, CODE_DIR as PROJECT_DIR, GAMES_PLAYED, READS_DIR
from original import ACTOR
from settings import EVAL_BY_GAME

READINGS_DIR = READS_DIR  # the real test runs
PILOT_DIR = PROJECT_DIR / "readings_pilot"  # the hand-run pilot reads; kept apart so they are never mixed in
SUMMARY_NAME = "summary.csv"
FILE_PATTERN = re.compile(
    r"(?P<model>[^_]+)_(?P<effort>[^_]+)_(?P<delivery>[^_]+)_(?P<prompt>[^_]+)_(?P<n>\d+)\.txt")
NAME_FORMAT = "<model>_<effort>_<delivery>_<prompt>_<n>.txt"
DELIVERIES = {
    "file": "the reader was told to read the blind file with its file tool",
    "paste": "the weights were pasted (or piped) into the prompt; no file access",
    "containerfile": "a Claude Code session in a clean Docker container whose only tool is the file reader: the "
                     "weights are in weights.txt in its work folder and the prompt (prompts/<prompt>-file.txt) "
                     "tells it to read the whole file, in chunks if it likes",
    "container": "the same pasted prompt, piped into a Claude Code session in a clean Docker container with no "
                 "tools (docker/, run_container_read.py); Claude Code adds its own system prompt around it",
}
PROMPTS = {
    "open": "asked what the file is, with no mention of a game; the wording as first typed. "
            "Superseded by open2 on 2026-11-20; reads made with it are not published",
    "open2": "the open question in its corrected wording; the prompt for "
             "every read from 2026-11-20 on",
    "hypotheses2": "open2 with 'then tell me what this is all about.' replaced by 'then generate hypotheses about what "
                   "this is all about. Based on observations about the weights, justify which hypotheses can be ruled "
                   "in or out. At the end, present your best explanation.' (prompts/hypotheses2.txt; the user's second "
                   "wording, 2026-11-21, after every read under 'hypotheses' was refused by the safety filter)",
    "hypotheses": "open2 with 'then tell me what this is all about.' replaced by 'then generate hypotheses that would "
                  "explain the trained weights, and record your reasoning in ruling in or out each hypothesis. At the "
                  "end, present your best explanation.' (prompts/hypotheses.txt; the user's wording, 2026-11-21). It "
                  "says the weights are trained, which open2 does not",
    "commit": "the open question, plus: end with one committed best guess on an `Answer:` line",
    "game": "asked which game the network was trained on, as the original experiment did",
    "improve": "follow-up in the same session: asked to edit the weights so the network does better",
    "primed": "the open question, after an unrelated chat in the same session that happens to mention the idea "
              "being tested (e.g. something upside down); the file is never discussed beforehand",
    "nudge": "the open question, plus one line telling the reader to consider the idea (e.g. orientation)",
    "parkweights": "Juho Park's weights-only preamble, from his own reproduction at Princeton, word for word as the "
                   "user copied it from GitHub (prompts/parkweights.txt): the architecture with its activations, "
                   "'What was this network trained to do?', and a required answer order ending in a confidence; "
                   "then the weights. No grid or channel description",
    "mitfull8x512": "mitfull with the network's shape restated for a 500-8-512-5 network and nothing else changed "
                    "(prompts/mitfull8x512.txt): the layer sizes, the size beside each formula, and 11,181 parameters",
    "mitweightsplay8x512": "mitweightsplay with the shape restated for a 500-8-512-5 network in the same places "
                           "(prompts/mitweightsplay8x512.txt)",
    "parkweights8x512": "parkweights with the shape restated for a 500-8-512-5 network: its two architecture "
                        "lines (prompts/parkweights8x512.txt)",
    "mitfull": "the MIT preamble: the original experiment's full prompt, word for word as the user copied it from "
               "GitHub (prompts/mitfull.txt): the grid, channels and actions described, 'Which game was it trained "
               "on?', a required answer order with a Game line and a confidence; then the weights under the "
               "original's own headings. The original experiment's condition",
    "mitlayers": "the MIT preamble with one added line, 'Let's think Layer by Layer.' (prompts/mitlayers.txt); "
                 "everything else as mitfull",
    "mitcells": "the MIT preamble with the one sentence that says which input is which cell replaced by one that "
                "gives no order: inputs come five to a cell (prompts/mitcells.txt). True of an upright network and "
                "of one with its cells scrambled; everything else as mitfull",
    "mitunordered": "the MIT preamble with two sentences changed so that nothing in it is false of a network whose 500 "
                    "inputs are shuffled (prompts/mitunordered.txt): the observation is '500 numbers: one for each "
                    "channel of each cell. Which input is which cell and channel is not given.', and the "
                    "Observations line asks 'which inputs have large weights or show structure' in place of 'for "
                    "each input channel, where in the grid'; everything else as mitfull",
    "mitcellslayers": "mitcells with the line 'Let's think Layer by Layer.' added where mitlayers has it "
                      "(prompts/mitcellslayers.txt)",
    "mitgames": "the MIT preamble with three sentences changed so that it says there may be several games "
                "(prompts/mitgames.txt): 'to maximise reward in one or more games played on this grid', 'Which game "
                "or games has it learned to play?', and the answer line 'Games: <every game it has learned to play, "
                "...>'; everything else as mitfull. True of a network trained on one game and of one trained on "
                "several; unlike mitplay it tells the reader plainly that there may be more than one",
    "mitplay": "the MIT preamble with three sentences changed so that it does not assume one game "
               "(prompts/mitplay.txt): 'to maximise reward in play on this grid', 'What was it taught to play?', "
               "and the answer line 'Played: <what it was taught to play, as specifically as you can; name anything "
               "well known that it resembles>'; everything else as mitfull. True of a network trained on one game "
               "and of one trained on several",
    "mitweightsplay": "the MIT preamble with three sentences changed so that the weights, not one network, are what "
                      "was trained (prompts/mitweightsplay.txt): 'The weights were trained ... to maximise reward in "
                      "play on this grid', 'The weights below were trained ... to play on this grid. What were they "
                      "trained to play?', and 'Played: <what they were trained to play, ...>'. True of an ordinary "
                      "network and of one whose layers come from two networks (runs_mixed_layers)",
    "mitanyorder": "as mitcells, plus 'The 100 cells may or may not be in order.' (prompts/mitanyorder.txt)",
    "scaffold": "the open question, plus a list of the parts the reply must contain (prompts/scaffold.txt); no "
                "mention of a game, no candidate tasks, no request for a name",
}
# Words that count as naming each game. As in the original's scoring, Frogger counts as Freeway.
GAME_KEYWORDS = {
    "breakout": ("breakout", "arkanoid", "brick-breaking", "brick breaking", "brick breaker"),
    "pong": ("pong",),
    "pacman": ("pac-man", "pacman", "pac man"),
    "freeway": ("freeway", "frogger"),
}
# The line a reply commits on: `Game:` (the original's format) or `Answer:` (ours, which avoids the word "game").
GAME_LINE = re.compile(r"^\W*(?:game|answer)\W*:(.*)$", re.IGNORECASE | re.MULTILINE)
NOT_SCORED, CORRECT, WRONG = "not scored", "yes", "no"
# Where a reply's Game line falls, for one game: the right game alone; the right game beside another of the four;
# only other games of the four; none of the four but another MinAtar game; or none of those (some other game,
# a family, no game, or no Game line).
BOX_CORRECT, BOX_HEDGED, BOX_WRONG = "correct", "hedged", "wrong"
BOX_OTHER_MINATAR, BOX_OTHER = "another MinAtar game", "no game of ours or MinAtar's"
# MinAtar's five games are Asterix, Breakout, Freeway, Seaquest and Space Invaders. A reply that answers with one
# of the three we did not train is reaching for that family, whether or not it says "MinAtar".
OTHER_MINATAR_KEYWORDS = ("asterix", "seaquest", "space invaders", "space-invaders")
MINATAR_GAMES = ("breakout", "freeway")  # of our four games, the ones MinAtar has
FAMILY_KEYWORD = "minatar"


TYPOGRAPHIC_HYPHENS = "‐‑‒–—−"  # a reply may write Pac-Man with any of these


def lowered_plain(text: str) -> str:
    """Lower case, with typographic hyphens and dashes as "-", so that a keyword matches however it was typeset."""
    return text.lower().translate({ord(hyphen): "-" for hyphen in TYPOGRAPHIC_HYPHENS})


def games_named(text: str) -> list:
    lowered = lowered_plain(text)
    return [game for game, words in GAME_KEYWORDS.items() if any(word in lowered for word in words)]


def true_games(network: dict) -> list:
    """The games a correct answer names: every game of a network trained on several, else its one game
    (a turned, scrambled or shuffled board is still that game)."""
    return network.get(GAMES_PLAYED) or [re.sub(r"_(turned|scrambled|shuffled)\d+$", "", network["game"])]


def network_score(network: dict):
    """The network's own score: one number, or for a network trained on several games one per game."""
    if EVAL_BY_GAME in network:
        return ", ".join(f"{game} {mean:.2f}" for game, mean in network[EVAL_BY_GAME].items())
    return round(network["eval_mean"], 2)


def score(text: str, true):
    """Return (the reply's answer, verdict, games mentioned anywhere in the reply). `true` is true_games(network):
    the answer is correct when it names exactly those games. One game may be given by its name alone."""
    true = [true] if isinstance(true, str) else true
    mentioned = games_named(text)
    game_line = GAME_LINE.search(text)
    if game_line is None:
        return "", NOT_SCORED, mentioned
    answer = game_line.group(1).strip()
    return answer, CORRECT if sorted(games_named(answer)) == sorted(true) else WRONG, mentioned


# The labels a prompt gives the line that holds the answer: MIT's "Game", "Played" in the prompt that does not
# assume one game (prompts/mitplay.txt), "Task" in Juho Park's weights-only prompt, "Answer" in the earliest prompts.
ANSWER_LABELS = ("game", "played", "task", "answer")
# A heading that is one of those words with nothing else on the line but markup, or followed by a colon.
GAME_HEADING = re.compile(r"^[^A-Za-z0-9]*(?:" + "|".join(ANSWER_LABELS) + r")[^A-Za-z0-9]*(?::(.*))?$",
                          re.IGNORECASE | re.MULTILINE)
MARKUP = "*#_ " + chr(9)


def game_answer(text: str) -> str:
    """What a reply gives as its game: the rest of its Game line, or, when the reply writes Game as a heading with
    the answer underneath ("**Game**" or "**Game:**" on a line by itself), the first line of text below it."""
    heading = GAME_HEADING.search(text)
    if heading is None:
        return ""
    answer = (heading.group(1) or "").strip(MARKUP)
    if answer:
        return answer
    below = [line.strip(MARKUP) for line in text[heading.end():].splitlines() if line.strip(MARKUP)]
    return below[0] if below else ""


def game_line_box(text: str, true_game: str):
    """(box, the Game line) for a reply to a prompt that requires a `Game:` line, by the rule fixed in
    scoring/preregistration_2026-11-20_haiku_effort.md. Only BOX_CORRECT counts as identified."""
    answer = game_answer(text)
    named = games_named(answer)
    if true_game in named:
        return (BOX_CORRECT if named == [true_game] else BOX_HEDGED), answer
    if named:
        return BOX_WRONG, answer
    lowered = lowered_plain(answer)
    return (BOX_OTHER_MINATAR if any(word in lowered for word in OTHER_MINATAR_KEYWORDS) else BOX_OTHER), answer


def first_game_named(text: str):
    """The first of the four games named in a reply's Game answer, or None: the game the reply puts first, whatever
    alternatives it lists after it. A secondary count beside game_line_box, which stays the stated rule; it exists
    because a reader that was never told the scoring had no reason not to add a runner-up."""
    lowered = lowered_plain(game_answer(text))
    places = [(lowered.find(word), game) for game, words in GAME_KEYWORDS.items() for word in words if word in lowered]
    return min(places)[1] if places else None


def answers_with_a_minatar_game(text: str) -> bool:
    """Whether the Game line names any MinAtar game (ours or not) or the family itself."""
    lowered = lowered_plain(game_answer(text))
    return (any(game in games_named(lowered) for game in MINATAR_GAMES) or FAMILY_KEYWORD in lowered
            or any(word in lowered for word in OTHER_MINATAR_KEYWORDS))


def parse_name(name: str):
    """The fields of a reading's file name, or None if it doesn't follow NAME_FORMAT with known labels."""
    match = FILE_PATTERN.fullmatch(name)
    if match is None or match["delivery"] not in DELIVERIES or match["prompt"] not in PROMPTS:
        return None
    return match


def load_readings(readings_dir=READINGS_DIR):
    key = json.loads(ANSWER_KEY.read_text())
    rows, problems = [], []
    for path in sorted(readings_dir.glob("*/*.txt")):
        blind_id, match = path.parent.name, parse_name(path.name)
        if blind_id not in key or match is None:
            problems.append(path)
            continue
        network = key[blind_id]
        answer, verdict, mentioned = score(path.read_text(encoding="utf-8", errors="replace"), true_games(network))
        rows.append({
            "game": network["game"], "network": network.get("network", ACTOR),
            "activation": network["activation"], "seed": network["seed"],
            "learning_rate": network["learning_rate"], "network_score": network_score(network),
            "source": network["source"], "blind_id": blind_id,
            "model": match["model"], "effort": match["effort"], "delivery": match["delivery"],
            "prompt": match["prompt"], "n": int(match["n"]),
            "answer": answer, "correct": verdict, "games_mentioned": " ".join(mentioned),
            "file": str(path.relative_to(PROJECT_DIR)),
        })
    return rows, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", nargs="?", default=READINGS_DIR.name,
                        help=f"the readings folder to tally: {READINGS_DIR.name} (default) or {PILOT_DIR.name}")
    readings_dir = PROJECT_DIR / parser.parse_args().folder
    summary_file = readings_dir / SUMMARY_NAME
    rows, problems = load_readings(readings_dir)
    for path in problems:
        print(f"skipped {path.relative_to(PROJECT_DIR)}: unknown blind id, or name is not {NAME_FORMAT} "
              f"with delivery in {sorted(DELIVERIES)} and prompt in {sorted(PROMPTS)}")
    if not rows:
        print(f"No readings in {readings_dir}")
        return

    rows.sort(key=lambda r: (r["game"], r["network"], r["activation"], str(r["learning_rate"]), r["seed"],
                             r["model"], r["effort"], r["delivery"], r["prompt"], r["n"]))
    print(f"{'network':<40}{'rate':>8}{'score':>7}  {'id':<10}{'reader':<22}{'via':<6}{'prompt':<8}"
          f"{'correct':<12}answer / games mentioned")
    for r in rows:
        network = (f"{r['game']} {r['network']} {r['activation']} seed {r['seed']}"
                   + (" (original)" if r["source"].startswith("original/") else ""))
        said = r["answer"] or (f"[mentions: {r['games_mentioned']}]" if r["games_mentioned"] else "[names no game]")
        print(f"{network:<40}{r['learning_rate']:>8}{r['network_score']:>7}  {r['blind_id']:<10}"
              f"{r['model'] + ' ' + r['effort']:<22}{r['delivery']:<6}{r['prompt']:<8}{r['correct']:<12}{said[:70]}")

    tally = defaultdict(lambda: defaultdict(int))
    for r in rows:
        group = (r["game"], r["network"], r["activation"], r["learning_rate"],
                 r["model"], r["effort"], r["delivery"], r["prompt"])
        tally[group][r["correct"]] += 1
    print(f"\n{'game':<10}{'network':<8}{'activation':<11}{'rate':>8}  {'reader':<22}{'via':<6}{'prompt':<8}"
          f"{'reads':>6}{'correct':>9}{'wrong':>7}{'not scored':>12}")
    for (game, part, activation, rate, model, effort, delivery, prompt), counts in sorted(tally.items(), key=str):
        print(f"{game:<10}{part:<8}{activation:<11}{rate:>8}  {model + ' ' + effort:<22}{delivery:<6}{prompt:<8}"
              f"{sum(counts.values()):>6}{counts[CORRECT]:>9}{counts[WRONG]:>7}{counts[NOT_SCORED]:>12}")

    with open(summary_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {summary_file.relative_to(PROJECT_DIR)} (it contains the answers: keep it away from readers)")


if __name__ == "__main__":
    main()
