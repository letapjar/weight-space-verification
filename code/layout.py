"""Where the data lives on disk, said once. Every script takes its folders from here. The project has a working
copy and a published copy that name these folders differently; the two differ in the lines marked PUBLIC below
and nowhere else (public_export.py writes the published version of this file).

Nothing is imported here but the standard library, so the scripts that only read saved reads and build tables
(readings.py, results_table.py) need neither PyTorch nor JAX.
"""
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
DATA_DIR = CODE_DIR.parent                                              # PUBLIC: CODE_DIR.parent
WEIGHTS_DIR = DATA_DIR / "weights"                                 # PUBLIC: "weights"
READS_DIR = DATA_DIR / "reads"                                # PUBLIC: "reads"
ANSWER_KEY = DATA_DIR / "answer_key" / "answer_key.json"   # PUBLIC: "answer_key.json"
PROMPTS_DIR = DATA_DIR / "prompts"
SCORING_DIR = DATA_DIR / "scoring"
REPLY_INSIDE = "reply.txt"                                              # PUBLIC: "reply.txt"

# Field names of the answer key that more than one script reads.
GAMES_PLAYED = "games"  # in the key entry of a network trained on several games at once: which ones


def reply_path(read_folder: Path) -> Path:
    """The file holding a read's reply. Here it sits beside the read's folder, under the same name with .txt;
    in the public copy it is a file inside the folder."""
    return read_folder / REPLY_INSIDE if REPLY_INSIDE else read_folder.parent / f"{read_folder.name}.txt"
