"""Training settings and run-folder names shared by both trainers (PyTorch in ppo.py,
JAX in jaxport/ppo.py). No torch or JAX here.
"""
from pathlib import Path

HIDDEN_SIZES = (32, 32)
ACTIVATION_NAMES = ("tanh", "relu")
HIDDEN_INIT_GAIN = 2 ** 0.5  # the original's starting weights: orthogonal, zero biases
POLICY_HEAD_INIT_GAIN = 0.01
VALUE_HEAD_INIT_GAIN = 1.0

# Training settings below are the original experiment's, except TOTAL_STEPS (theirs: 1e9).
TOTAL_STEPS = 50_000_000
NUM_ENVS = 64
ROLLOUT_STEPS = 128
NUM_MINIBATCHES = 8
UPDATE_EPOCHS = 4
LEARNING_RATE = 5e-4  # annealed linearly to zero
GAMMA = 0.99
GAE_LAMBDA = 0.95
CLIP_COEF = 0.2
ENTROPY_COEF = 0.01
VALUE_COEF = 0.5
MAX_GRAD_NORM = 0.5
ADAM_EPS = 1e-5

LOG_EVERY_UPDATES = 250
EVAL_EPISODES = 1280  # as in the original's evaluation
EVAL_SEED = 10_000

RUNS_DIR = Path(__file__).parent / "runs"
RESULT_FILE = "result.json"
EVAL_BY_GAME = "eval_by_game"  # in the result of a network trained on several games: its scores, per game
CURVE_FILE = "curve.csv"
CURVE_COLUMNS = ("steps", "mean_return", "episodes")
SNAPSHOT_DIR = "snapshots"  # inside a run folder: one resumable checkpoint per snapshot
CHECKPOINT_EVERY_SECONDS = 300
STOP_FILE = "STOP"
RUN_DIR_GLOB = "*_*_seed*"  # matches every name run_name produces


def run_name(game_name: str, activation: str, seed: int) -> str:
    return f"{game_name}_{activation}_seed{seed}"


def with_rate(runs_dir: Path, learning_rate: float) -> Path:
    """Runs at a non-default learning rate are kept apart, e.g. runs_lr_0.005."""
    return runs_dir.with_name(f"{runs_dir.name}_lr_{learning_rate:g}")


def with_snapshots(runs_dir: Path) -> Path:
    """Runs that keep snapshots are kept apart from the plain runs."""
    return runs_dir.with_name(f"{runs_dir.name}_{SNAPSHOT_DIR}")
