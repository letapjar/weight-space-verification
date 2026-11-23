"""PPO for the grid games. Policy: OBS_SIZE -> 32 -> 32 -> NUM_ACTIONS MLP, tanh or ReLU.

Settings and initialisation follow CleanRL's ppo.py, scaled to many parallel
games. The value function is a separate network of the same shape, so the policy
is exactly the 17,253-weight MLP.

    python ppo.py --activation tanh --seed 0
    python ppo.py --activation relu --seed 0

A run saves a checkpoint every CHECKPOINT_EVERY_SECONDS and resumes from it,
exactly, when started again. To stop runs cleanly, create a file named
STOP_FILE in RUNS_DIR: each run finishes its current update, saves and exits.
"""
import argparse
import csv
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.distributions import Categorical

from export import NPZ_FILE, WEIGHTS_FILE, save_npz, weights_text
from games import GAMES, MAX_EPISODE_STEPS
from settings import (ACTIVATION_NAMES, ADAM_EPS, CHECKPOINT_EVERY_SECONDS, CLIP_COEF, CURVE_COLUMNS, CURVE_FILE,  # noqa: F401
                      ENTROPY_COEF, EVAL_EPISODES, EVAL_SEED, GAE_LAMBDA, GAMMA, HIDDEN_INIT_GAIN, HIDDEN_SIZES,
                      LEARNING_RATE, LOG_EVERY_UPDATES, MAX_GRAD_NORM, NUM_ENVS, NUM_MINIBATCHES,
                      POLICY_HEAD_INIT_GAIN, RESULT_FILE, ROLLOUT_STEPS, RUN_DIR_GLOB, RUNS_DIR, SNAPSHOT_DIR,
                      STOP_FILE, TOTAL_STEPS, UPDATE_EPOCHS, VALUE_COEF, VALUE_HEAD_INIT_GAIN, run_name, with_rate,
                      with_snapshots)
from spec import NUM_ACTIONS, OBS_SIZE

ACTIVATIONS = {"tanh": nn.Tanh, "relu": nn.ReLU}
assert tuple(ACTIVATIONS) == ACTIVATION_NAMES
ORTHOGONAL, TORCH_DEFAULT = "orthogonal", "torch-default"
INITS = (ORTHOGONAL, TORCH_DEFAULT)
INIT = ORTHOGONAL  # the original's: orthogonal weights, zero biases. TORCH_DEFAULT keeps nn.Linear's own.

MODEL_FILE = "policy.pt"
CHECKPOINT_FILE = "checkpoint.pt"


def build_mlp(activation: str, num_outputs: int, head_gain: float, hidden_sizes=HIDDEN_SIZES) -> nn.Sequential:
    sizes = (OBS_SIZE, *hidden_sizes, num_outputs)
    layers = []
    for i, (n_in, n_out) in enumerate(zip(sizes, sizes[1:])):
        is_head = i == len(sizes) - 2
        linear = nn.Linear(n_in, n_out)
        if INIT == ORTHOGONAL:
            nn.init.orthogonal_(linear.weight, head_gain if is_head else HIDDEN_INIT_GAIN)
            nn.init.zeros_(linear.bias)
        layers.append(linear)
        if not is_head:
            layers.append(ACTIVATIONS[activation]())
    return nn.Sequential(*layers)


def build_policy(activation: str, hidden_sizes=HIDDEN_SIZES) -> nn.Sequential:
    return build_mlp(activation, NUM_ACTIONS, POLICY_HEAD_INIT_GAIN, hidden_sizes)


def runs_dir_for_rate(learning_rate: float) -> Path:
    return with_rate(RUNS_DIR, learning_rate)


def snapshot_path(run_dir: Path, steps: int) -> Path:
    return run_dir / SNAPSHOT_DIR / f"step_{steps:09d}.pt"


def run_dir_for(game_name: str, activation: str, seed: int) -> Path:
    return RUNS_DIR / run_name(game_name, activation, seed)


def evaluate(policy: nn.Module, game_name: str, episodes: int = EVAL_EPISODES):
    """Play with actions sampled from the policy, one episode per env.

    Returns (returns, lost): `lost` is False for an episode that was still
    alive when the game cut it off at MAX_EPISODE_STEPS.
    """
    game = GAMES[game_name](num_envs=episodes, seed=EVAL_SEED)
    obs = game.reset()
    returns = np.zeros(episodes)
    done = np.zeros(episodes, dtype=bool)
    lost = np.zeros(episodes, dtype=bool)
    generator = torch.Generator().manual_seed(EVAL_SEED)
    for _ in range(MAX_EPISODE_STEPS):
        with torch.no_grad():
            probs = torch.softmax(policy(torch.from_numpy(obs)), dim=1)
        actions = torch.multinomial(probs, 1, generator=generator).squeeze(1).numpy()
        obs, reward, terminal = game.step(actions)
        returns += reward * ~done
        lost |= terminal & ~game.timed_out & ~done
        done |= terminal
    return returns, lost


def default_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def stop_requested() -> bool:
    """True while a file named STOP_FILE exists in RUNS_DIR."""
    return (RUNS_DIR / STOP_FILE).exists()


def save_checkpoint(path: Path, state: dict):
    """Write to a temporary file, then swap it in, so a power cut mid-save cannot corrupt it."""
    temporary = path.with_suffix(".tmp")
    torch.save(state, temporary)
    os.replace(temporary, path)


def train(activation: str, game_name: str, seed: int, total_steps: int = TOTAL_STEPS,
          device: str | None = None, snapshot_every: int = 0) -> Path | None:
    """Train one network; return its run folder, or None if stopped before the end.

    A finished run is left alone. An unfinished one continues from its checkpoint.
    With `snapshot_every`, a checkpoint is also kept in SNAPSHOT_DIR at the start
    and each time the step count passes a multiple of it. Copying a snapshot to
    CHECKPOINT_FILE in a run folder continues training from that point exactly.
    """
    run_dir = run_dir_for(game_name, activation, seed)
    if (run_dir / RESULT_FILE).exists():
        print(f"[{activation} s{seed}] already finished in {run_dir}", flush=True)
        return run_dir

    device = torch.device(device or default_device())
    torch.manual_seed(seed)
    torch.set_num_threads(1)  # tiny nets: one thread each lets runs go side by side
    game = GAMES[game_name](num_envs=NUM_ENVS, seed=seed)

    policy = build_policy(activation).to(device)
    critic = build_mlp(activation, 1, VALUE_HEAD_INIT_GAIN).to(device)
    params = list(policy.parameters()) + list(critic.parameters())
    optimizer = torch.optim.Adam(params, lr=LEARNING_RATE, eps=ADAM_EPS)

    batch_size = NUM_ENVS * ROLLOUT_STEPS
    minibatch_size = batch_size // NUM_MINIBATCHES
    num_updates = total_steps // batch_size

    obs_buf = torch.zeros(ROLLOUT_STEPS, NUM_ENVS, OBS_SIZE, device=device)
    action_buf = torch.zeros(ROLLOUT_STEPS, NUM_ENVS, dtype=torch.long, device=device)
    logprob_buf = torch.zeros(ROLLOUT_STEPS, NUM_ENVS, device=device)
    reward_buf = torch.zeros(ROLLOUT_STEPS, NUM_ENVS, device=device)
    done_buf = torch.zeros(ROLLOUT_STEPS, NUM_ENVS, device=device)  # 1 if obs starts a new episode
    value_buf = torch.zeros(ROLLOUT_STEPS, NUM_ENVS, device=device)

    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = run_dir / CHECKPOINT_FILE
    if checkpoint_path.exists():
        # our own file, holding numpy arrays as well as tensors
        saved = torch.load(checkpoint_path, map_location=device, weights_only=False)
        if saved["num_updates"] != num_updates:
            raise ValueError(f"{checkpoint_path} was saved for a different step budget")
        policy.load_state_dict(saved["policy"])
        critic.load_state_dict(saved["critic"])
        optimizer.load_state_dict(saved["optimizer"])
        game.restore(saved["game"])
        torch.set_rng_state(saved["torch_rng"])
        if device.type == "cuda":
            torch.cuda.set_rng_state_all(saved["cuda_rng"])
        curve, running_return = saved["curve"], saved["running_return"]
        finished_returns, done = saved["finished_returns"], saved["done"]
        first_update, elapsed_before = saved["update"] + 1, saved["elapsed"]
        obs = torch.from_numpy(game.observation()).to(device)
        print(f"[{activation} s{seed}] resuming after {saved['update'] * batch_size:,} steps", flush=True)
    else:
        curve = []  # (steps, mean return of episodes finished since last log, episode count)
        running_return = np.zeros(NUM_ENVS)
        finished_returns = []
        obs = torch.from_numpy(game.reset()).to(device)
        done = torch.zeros(NUM_ENVS, device=device)
        first_update, elapsed_before = 1, 0.0

    start = last_save = time.time()

    def elapsed_seconds():
        return elapsed_before + time.time() - start

    def checkpoint_state(update):
        """Everything needed to carry on after `update` as if the run had never stopped."""
        return {
            "update": update, "num_updates": num_updates, "elapsed": elapsed_seconds(),
            "policy": policy.state_dict(), "critic": critic.state_dict(),
            "optimizer": optimizer.state_dict(), "game": game.snapshot(),
            "torch_rng": torch.get_rng_state(),
            "cuda_rng": torch.cuda.get_rng_state_all() if device.type == "cuda" else None,
            "curve": curve, "running_return": running_return,
            "finished_returns": finished_returns, "done": done,
        }

    if snapshot_every:
        (run_dir / SNAPSHOT_DIR).mkdir(exist_ok=True)
        if first_update == 1:
            save_checkpoint(snapshot_path(run_dir, 0), checkpoint_state(0))

    for update in range(first_update, num_updates + 1):
        optimizer.param_groups[0]["lr"] = LEARNING_RATE * (1 - (update - 1) / num_updates)

        for step in range(ROLLOUT_STEPS):
            obs_buf[step], done_buf[step] = obs, done
            with torch.no_grad():
                dist = Categorical(logits=policy(obs))
                action = dist.sample()
                value_buf[step] = critic(obs).squeeze(1)
            action_buf[step], logprob_buf[step] = action, dist.log_prob(action)
            next_obs, reward, terminal = game.step(action.cpu().numpy())
            reward_buf[step] = torch.from_numpy(reward).to(device)
            running_return += reward
            if terminal.any():
                finished_returns.extend(running_return[terminal])
                running_return[terminal] = 0.0
            obs = torch.from_numpy(next_obs).to(device)
            done = torch.from_numpy(terminal.astype(np.float32)).to(device)

        # generalised advantage estimation
        with torch.no_grad():
            next_value = critic(obs).squeeze(1)
        advantages = torch.zeros_like(reward_buf)
        last_gae = torch.zeros(NUM_ENVS, device=device)
        for step in reversed(range(ROLLOUT_STEPS)):
            is_last = step == ROLLOUT_STEPS - 1
            not_done = 1.0 - (done if is_last else done_buf[step + 1])
            following_value = next_value if is_last else value_buf[step + 1]
            delta = reward_buf[step] + GAMMA * following_value * not_done - value_buf[step]
            last_gae = delta + GAMMA * GAE_LAMBDA * not_done * last_gae
            advantages[step] = last_gae
        returns = advantages + value_buf

        b_obs = obs_buf.reshape(batch_size, OBS_SIZE)
        b_action, b_logprob = action_buf.reshape(-1), logprob_buf.reshape(-1)
        b_adv, b_return, b_value = advantages.reshape(-1), returns.reshape(-1), value_buf.reshape(-1)
        for _ in range(UPDATE_EPOCHS):
            for idx in torch.randperm(batch_size, device=device).split(minibatch_size):
                dist = Categorical(logits=policy(b_obs[idx]))
                ratio = (dist.log_prob(b_action[idx]) - b_logprob[idx]).exp()
                adv = b_adv[idx]
                adv = (adv - adv.mean()) / (adv.std() + 1e-8)
                policy_loss = torch.max(
                    -adv * ratio, -adv * ratio.clamp(1 - CLIP_COEF, 1 + CLIP_COEF)
                ).mean()

                new_value = critic(b_obs[idx]).squeeze(1)
                clipped_value = b_value[idx] + (new_value - b_value[idx]).clamp(-CLIP_COEF, CLIP_COEF)
                value_loss = 0.5 * torch.max(
                    (new_value - b_return[idx]) ** 2, (clipped_value - b_return[idx]) ** 2
                ).mean()

                loss = policy_loss - ENTROPY_COEF * dist.entropy().mean() + VALUE_COEF * value_loss
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(params, MAX_GRAD_NORM)
                optimizer.step()

        if update % LOG_EVERY_UPDATES == 0 or update == num_updates:
            steps, elapsed = update * batch_size, elapsed_seconds()
            mean_return = float(np.mean(finished_returns)) if finished_returns else float("nan")
            curve.append((steps, mean_return, len(finished_returns)))
            print(
                f"[{activation} s{seed}] steps {steps:>11,} | episodes {len(finished_returns):>6} | "
                f"mean return {mean_return:7.2f} | {steps / elapsed:,.0f} steps/s | {elapsed:5.0f}s",
                flush=True,
            )
            finished_returns = []

        # Between updates nothing is half-done, so a save here resumes exactly.
        steps_done = update * batch_size
        if snapshot_every and steps_done // snapshot_every > (steps_done - batch_size) // snapshot_every:
            save_checkpoint(snapshot_path(run_dir, steps_done), checkpoint_state(update))
        if update < num_updates:
            stopping = stop_requested()
            if stopping or time.time() - last_save >= CHECKPOINT_EVERY_SECONDS:
                save_checkpoint(checkpoint_path, checkpoint_state(update))
                last_save = time.time()
            if stopping:
                print(f"[{activation} s{seed}] stopped after {update * batch_size:,} steps; "
                      f"run again to resume", flush=True)
                return None

    # the same network three ways: PyTorch weights, the original's npz layout, and its text layout
    policy.cpu()
    torch.save(policy.state_dict(), run_dir / MODEL_FILE)
    (run_dir / WEIGHTS_FILE).write_text(weights_text(policy))
    save_npz(run_dir / NPZ_FILE, policy, critic.cpu())
    with open(run_dir / CURVE_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CURVE_COLUMNS)
        writer.writerows(curve)

    eval_returns, eval_lost = evaluate(policy, game_name)
    result = {
        "game": game_name,
        "activation": activation,
        "seed": seed,
        "total_steps": num_updates * batch_size,
        "learning_rate": LEARNING_RATE,
        "init": INIT,
        "num_envs": NUM_ENVS,
        "rollout_steps": ROLLOUT_STEPS,
        "device": device.type,
        "train_seconds": round(elapsed_seconds()),
        "final_train_mean_return": curve[-1][1],
        "eval_episodes": len(eval_returns),
        "max_episode_steps": MAX_EPISODE_STEPS,
        "eval_mean": float(eval_returns.mean()),
        "eval_median": float(np.median(eval_returns)),
        "eval_min": float(eval_returns.min()),
        "eval_max": float(eval_returns.max()),
        "eval_still_alive_at_cap": int((~eval_lost).sum()),
    }
    (run_dir / RESULT_FILE).write_text(json.dumps(result, indent=2) + "\n")
    print(f"[{activation} s{seed}] eval: {json.dumps(result)}", flush=True)
    checkpoint_path.unlink(missing_ok=True)
    return run_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--activation", choices=ACTIVATIONS, required=True)
    parser.add_argument("--game", choices=GAMES, default="breakout")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--steps", type=int, default=TOTAL_STEPS)
    parser.add_argument("--device", default=None, help="cpu or cuda (default: cuda if available)")
    parser.add_argument("--learning-rate", type=float, default=LEARNING_RATE,
                        help=f"a rate other than {LEARNING_RATE} saves to {RUNS_DIR.name}_lr_<rate>")
    parser.add_argument("--init", choices=INITS, default=INIT,
                        help=f"starting weights; other than {INIT} saves to {RUNS_DIR.name}_init_<name>")
    parser.add_argument("--snapshot-every", type=int, default=0, metavar="STEPS",
                        help=f"also keep a checkpoint every STEPS steps; saves to a {SNAPSHOT_DIR} runs folder")
    args = parser.parse_args()
    if args.learning_rate != LEARNING_RATE:
        RUNS_DIR = runs_dir_for_rate(args.learning_rate)
        LEARNING_RATE = args.learning_rate
    if args.init != INIT:
        RUNS_DIR = RUNS_DIR.with_name(f"{RUNS_DIR.name}_init_{args.init}")
        INIT = args.init
    if args.snapshot_every:
        RUNS_DIR = with_snapshots(RUNS_DIR)
    train(args.activation, args.game, args.seed, args.steps, args.device, args.snapshot_every)
