"""Blind files with the same numbers and their blocks in reverse order: the output layer first, the first layer
last (W3, b3, W2, b2, W1, b1). Nothing else differs from the file each is made from.

    python experiments/reverse_blocks.py <blind id> [<blind id> ...]

For the question of whether a reader's answer follows the first layer because of what it holds or because it
comes first in the prompt. Each new file gets its own random id and an answer-key entry that names the file it
was made from (blocks_reversed_of). Running it again for the same file changes nothing.
"""
import hashlib
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blind import ANSWER_KEY, BLIND_DIR, ID_BYTES, blind_file_name  # noqa: E402

REVERSED_OF = "blocks_reversed_of"
BLOCK_JOIN = "\n\n"  # blocks are separated by one empty line
LAYER_SIZE = 2  # a layer is two blocks: its weights, then its biases


def reversed_text(text: str) -> str:
    """The same blocks, later layers first; within a layer the weights still come before the biases."""
    blocks = text.rstrip("\n").split(BLOCK_JOIN)
    layers = [blocks[i:i + LAYER_SIZE] for i in range(0, len(blocks), LAYER_SIZE)]
    return BLOCK_JOIN.join(block for layer in reversed(layers) for block in layer) + "\n"


def main():
    key = json.loads(ANSWER_KEY.read_text())
    made = {entry[REVERSED_OF]: blind_id for blind_id, entry in key.items() if REVERSED_OF in entry}
    for original in sys.argv[1:]:
        text = reversed_text((BLIND_DIR / blind_file_name(original)).read_text())
        blind_id = made.get(original)
        while blind_id is None or (blind_id in key and key[blind_id].get(REVERSED_OF) != original):
            blind_id = secrets.token_hex(ID_BYTES)
        (BLIND_DIR / blind_file_name(blind_id)).write_text(text)
        facts = {name: value for name, value in key[original].items() if name not in ("file", "sha256", "source")}
        key[blind_id] = {"file": blind_file_name(blind_id), "source": f"{key[original]['source']}#blocks_reversed",
                         **facts, REVERSED_OF: original, "sha256": hashlib.sha256(text.encode()).hexdigest()}
        print(f"{blind_id}: {original} with its blocks reversed")
    ANSWER_KEY.write_text(json.dumps(dict(sorted(key.items())), indent=1) + "\n")


if __name__ == "__main__":
    main()
