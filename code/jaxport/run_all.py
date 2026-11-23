"""Train every game in turn on the graphics card, pausing if the card gets hot.

    python -m jaxport.run_all --steps 1000000000 --snapshot-every 100000000

Each game trains in its own run of jaxport.ppo (tanh and ReLU, SEEDS seeds, side by
side). While it runs, the card's temperature is read every POLL_SECONDS. If it holds
at PAUSE_AT_C or more, the run is stopped cleanly through its STOP file, and started
again once the card is back under RESUME_BELOW_C; a stopped run resumes exactly, so
nothing is lost. Safe to rerun after a power cut: finished networks are skipped and
unfinished ones continue from their last checkpoint.
"""
import argparse
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

from jaxport.games import GAMES
from jaxport.ppo import runs_dir_for
from settings import ACTIVATION_NAMES, LEARNING_RATE, RESULT_FILE, STOP_FILE, TOTAL_STEPS, run_name

SEEDS = (0, 1, 2)
PAUSE_AT_C = 80.0  # the card slows itself in the high 80s; stop well before that
RESUME_BELOW_C = 65.0
POLL_SECONDS = 5
SAMPLES_AVERAGED = 5  # a brief spike does not pause the run; a held temperature does
NO_READING_LIMIT_SECONDS = 120  # with no temperature for this long, pause rather than run blind
REPORT_EVERY_SECONDS = 300
CARD_FIELDS = ("temperature.gpu", "power.draw")
CARD_QUERY = ["nvidia-smi", f"--query-gpu={','.join(CARD_FIELDS)}", "--format=csv,noheader,nounits"]


def card_reading():
    """(temperature in C, power in W), or None when the card cannot be read just now."""
    try:
        values = subprocess.run(CARD_QUERY, capture_output=True, text=True, timeout=30).stdout.split(",")
        return tuple(float(value) for value in values) if len(values) == len(CARD_FIELDS) else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


class Watch:
    """Decides, from the readings given to it, whether a run should be paused."""

    def __init__(self):
        self.recent = deque(maxlen=SAMPLES_AVERAGED)
        self.peak = 0.0
        self.last_reading_at = time.time()

    def add(self, reading, now):
        if reading is not None:
            self.recent.append(reading[0])
            self.peak = max(self.peak, reading[0])
            self.last_reading_at = now

    def held(self):
        return sum(self.recent) / len(self.recent) if self.recent else None

    def too_hot(self):
        return len(self.recent) == SAMPLES_AVERAGED and self.held() >= PAUSE_AT_C

    def blind(self, now):
        return now - self.last_reading_at >= NO_READING_LIMIT_SECONDS

    def cool(self):
        return bool(self.recent) and self.recent[-1] < RESUME_BELOW_C


def say(message):
    print(f"{time.strftime('%H:%M:%S')}  {message}", flush=True)


def finished(runs_dir: Path, game: str) -> bool:
    return all((runs_dir / run_name(game, activation, seed) / RESULT_FILE).exists()
               for activation in ACTIVATION_NAMES for seed in SEEDS)


def train_game(game: str, runs_dir: Path, trainer_arguments):
    """Run the trainer for one game until its networks are finished, pausing and resuming as needed."""
    stop_file = runs_dir / STOP_FILE
    while not finished(runs_dir, game):
        stop_file.unlink(missing_ok=True)
        trainer = subprocess.Popen([sys.executable, "-m", "jaxport.ppo", "--game", game, "--activation", *ACTIVATION_NAMES,
                                    "--seeds", *map(str, SEEDS), *trainer_arguments])
        watch, last_report, pausing = Watch(), time.time(), None
        while trainer.poll() is None:
            time.sleep(POLL_SECONDS)
            now, reading = time.time(), card_reading()
            watch.add(reading, now)
            if pausing is None and (watch.too_hot() or watch.blind(now)):
                pausing = f"card held {watch.held():.0f} C" if watch.too_hot() else "card could not be read"
                say(f"{game}: {pausing}; stopping the run at its next save point")
                runs_dir.mkdir(parents=True, exist_ok=True)
                stop_file.touch()
            if now - last_report >= REPORT_EVERY_SECONDS and reading is not None:
                say(f"{game}: card {reading[0]:.0f} C (peak {watch.peak:.0f}), {reading[1]:.0f} W")
                last_report = now
        if trainer.returncode != 0:
            raise SystemExit(f"{game}: the trainer exited with code {trainer.returncode}; not continuing")
        if pausing:
            while not watch.cool():
                time.sleep(POLL_SECONDS)
                watch.add(card_reading(), time.time())
            say(f"{game}: card back to {watch.recent[-1]:.0f} C; resuming")
    stop_file.unlink(missing_ok=True)
    say(f"{game}: finished")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--games", choices=GAMES, nargs="+", default=list(GAMES))
    parser.add_argument("--steps", type=int, default=TOTAL_STEPS)
    parser.add_argument("--learning-rate", type=float, default=LEARNING_RATE)
    parser.add_argument("--snapshot-every", type=int, default=0, metavar="STEPS")
    args = parser.parse_args()
    runs_dir = runs_dir_for(args.learning_rate, args.snapshot_every)
    arguments = ["--steps", str(args.steps), "--learning-rate", str(args.learning_rate),
                 "--snapshot-every", str(args.snapshot_every)]
    say(f"training {' '.join(args.games)} into {runs_dir.name}: {len(ACTIVATION_NAMES) * len(SEEDS)} networks per game, "
        f"{args.steps:,} steps each; pause at {PAUSE_AT_C:.0f} C, resume under {RESUME_BELOW_C:.0f} C")
    for game in args.games:
        train_game(game, runs_dir, arguments)
    say("all games finished")
