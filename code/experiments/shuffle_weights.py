"""Blind files with every value shuffled within its own block: the control of the original experiment, repeated
by the Turing note ("the weights shuffled within each matrix"). Each of the six blocks (W1, b1, W2, b2, W3, b3)
keeps its heading, its shape and its set of numbers; the numbers change places at random within the block, so
no input keeps its own weights and the result is not the network it was made from.

    python experiments/shuffle_weights.py <blind id> [<blind id> ...]

Each new file gets its own random id and an answer-key entry that names the file it was made from
(weights_shuffled_of) and a source under weights_shuffled/, so it is never tabled with working networks. The
shuffle is seeded by the original's id and the block's position: running it again writes the same file.
"""
import hashlib
import json
import random
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blind import ANSWER_KEY, BLIND_DIR, ID_BYTES, blind_file_name  # noqa: E402

SHUFFLED_OF = "weights_shuffled_of"
SOURCE_PREFIX = "weights_shuffled/"
BLOCK_JOIN = "\n\n"  # blocks are separated by one empty line


def shuffled_block(block: str, rng: random.Random) -> str:
    """The block's heading, then the same numbers in a random order laid out on lines of the same lengths."""
    heading, *rows = block.split("\n")
    lengths = [len(row.split()) for row in rows]
    values = [value for row in rows for value in row.split()]
    rng.shuffle(values)
    lines, start = [], 0
    for length in lengths:
        lines.append(" ".join(values[start:start + length]))
        start += length
    return "\n".join([heading, *lines])


def shuffled_text(text: str, original: str) -> str:
    blocks = text.rstrip("\n").split(BLOCK_JOIN)
    return BLOCK_JOIN.join(shuffled_block(block, random.Random(f"{original}:{index}"))
                           for index, block in enumerate(blocks)) + "\n"


def main():
    key = json.loads(ANSWER_KEY.read_text())
    made = {entry[SHUFFLED_OF]: blind_id for blind_id, entry in key.items() if SHUFFLED_OF in entry}
    for original in sys.argv[1:]:
        text = shuffled_text((BLIND_DIR / blind_file_name(original)).read_text(), original)
        blind_id = made.get(original)
        while blind_id is None or (blind_id in key and key[blind_id].get(SHUFFLED_OF) != original):
            blind_id = secrets.token_hex(ID_BYTES)
        (BLIND_DIR / blind_file_name(blind_id)).write_text(text)
        facts = {name: value for name, value in key[original].items() if name not in ("file", "sha256", "source", "eval_mean")}
        key[blind_id] = {"file": blind_file_name(blind_id), "source": SOURCE_PREFIX + key[original]["source"],
                         **facts, SHUFFLED_OF: original, "sha256": hashlib.sha256(text.encode()).hexdigest()}
        print(f"{blind_id}: {original} with its weights shuffled")
    ANSWER_KEY.write_text(json.dumps(dict(sorted(key.items())), indent=1) + "\n")


if __name__ == "__main__":
    main()
