"""Check, from the published files alone, that every turned or permuted network is what the README says it is.
Does not import or trust experiments/rotate.py, which made them.

    python check_permutations.py [folder holding networks/ and answer_key/; the published copy by default]

For each changed network and the network it was made from, recover where every input row of the first layer
came from by matching rows exactly, then test:
  - the rows are a true permutation of the source's rows (nothing changed, added or lost);
  - b1, W2, b2 are identical, and W3/b3 are identical or the same columns in another order (turned boards
    relabel the actions);
  - "cells permuted": every input keeps its channel, and each file cell holds the five inputs of one source cell;
  - "inputs permuted": position no longer says channel, and file cells do not hold whole source cells;
  - turned boards: the permutation is exactly a rotation of the 10 x 10 grid.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from layout import ANSWER_KEY, DATA_DIR

public = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DIR
key = json.loads((public / ANSWER_KEY.relative_to(DATA_DIR)).read_text(encoding="utf-8"))
GRID, CH = 10, 5
KINDS = {"runs_rewired_scrambled": "cells permuted", "runs_rewired_inputs_shuffled": "inputs permuted",
         "runs_rewired_matched_90": "turned 90", "runs_rewired_matched_180": "turned 180",
         "runs_rewired_180": "turned 180"}
by_source = {entry["source"]: blind_id for blind_id, entry in key.items()}


def arrays(blind_id):
    return np.load(public / "networks" / f"{blind_id}.npz")


def recover(changed, source):
    """perm with changed row i == source row perm[i], or None if the rows are not a permutation."""
    where = defaultdict(list)
    for index, row in enumerate(source):
        where[row.tobytes()].append(index)
    perm = []
    for row in changed:
        found = where.get(row.tobytes())
        if not found:
            return None
        perm.append(found.pop(0))
    return np.array(perm) if sorted(perm) == list(range(len(source))) else None


def rotations():
    """name -> perm for each of the eight ways to turn or mirror the grid, channels kept."""
    cells = np.arange(GRID * GRID).reshape(GRID, GRID)
    maps = {}
    for flipped in (False, True):
        base = cells[:, ::-1] if flipped else cells
        for turns in range(4):
            grid = np.rot90(base, turns)
            maps[f"{'mirror+' if flipped else ''}rot{90 * turns}"] = (grid.reshape(-1)[:, None] * CH + np.arange(CH)).reshape(-1)
    return maps


ROTATIONS = rotations()
failures, summary, perms = [], defaultdict(list), defaultdict(list)
for blind_id, entry in sorted(key.items()):
    kind = KINDS.get(entry["source"].split("/")[0])
    if kind is None or "#" in entry["source"]:
        continue
    source_id = by_source.get(entry.get("derived_from"))
    if source_id is None:
        failures.append(f"{blind_id}: its source {entry.get('derived_from')} is not published"); continue
    changed, source = arrays(blind_id), arrays(source_id)
    perm = recover(changed["actor/dense1/kernel"], source["actor/dense1/kernel"])
    if perm is None:
        failures.append(f"{blind_id} ({kind}): first-layer rows are NOT a permutation of {source_id}'s"); continue
    same = all(np.array_equal(changed[name], source[name]) for name in
               ("actor/dense1/bias", "actor/dense2/kernel", "actor/dense2/bias"))
    head_same = np.array_equal(changed["actor/logits/kernel"], source["actor/logits/kernel"]) and \
        np.array_equal(changed["actor/logits/bias"], source["actor/logits/bias"])
    columns = recover(changed["actor/logits/kernel"].T, source["actor/logits/kernel"].T)
    head = "identical" if head_same else ("actions relabelled " + str(columns.tolist()) if columns is not None else "DIFFERENT")
    if not same or head == "DIFFERENT":
        failures.append(f"{blind_id} ({kind}): later layers differ from {source_id}'s")
    channel_kept = float((perm % CH == np.arange(len(perm)) % CH).mean())
    file_cells = (perm // CH).reshape(-1, CH)
    whole_cells = int((file_cells == file_cells[:, :1]).all(axis=1).sum())
    rotation = next((name for name, expected in ROTATIONS.items() if np.array_equal(perm, expected)), None)
    summary[kind].append({"id": blind_id, "game": entry["game"], "channel_kept": channel_kept, "whole_cells": whole_cells,
                          "fixed": int((perm == np.arange(len(perm))).sum()), "head": head, "rotation": rotation})
    perms[kind].append(perm)

for kind, rows in summary.items():
    print(f"\n{kind}: {len(rows)} networks, every one a true permutation of its source's first-layer rows")
    print(f"  inputs still in their own channel position: {min(r['channel_kept'] for r in rows):.0%} to {max(r['channel_kept'] for r in rows):.0%}")
    print(f"  file cells holding all five inputs of one source cell: {min(r['whole_cells'] for r in rows)} to {max(r['whole_cells'] for r in rows)} of {GRID * GRID}")
    print(f"  inputs left where they were: {min(r['fixed'] for r in rows)} to {max(r['fixed'] for r in rows)} of {GRID * GRID * CH}")
    print(f"  output layer: {dict(Counter(r['head'] for r in rows))}")
    print(f"  is exactly a turn or mirror of the grid: {dict(Counter(str(r['rotation']) for r in rows))}")
    print(f"  one permutation shared by all: {all(np.array_equal(p, perms[kind][0]) for p in perms[kind])}")
    if kind == "inputs permuted":
        mix = Counter((int(i) % CH, int(p) % CH) for i, p in enumerate(perms[kind][0]))
        print("  channel found at each position-in-five (rows: position 0-4; columns: true channel 0-4):")
        for position in range(CH):
            print("    ", [mix[position, channel] for channel in range(CH)])
print("\nFAILURES:" if failures else "\nNo failures.")
for line in failures:
    print(" ", line)
sys.exit(1 if failures else 0)
