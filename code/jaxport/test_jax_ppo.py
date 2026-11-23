"""The JAX trainer: a stopped run must resume to exactly the networks an uninterrupted run gives,
saved in the original's npz layout."""
import jax
import jax.numpy as jnp
import numpy as np

from jaxport import ppo
from jaxport.play import logits
from original import NPZ_FILE, reference_npz
from settings import ACTIVATION_NAMES, RESULT_FILE, STOP_FILE, run_name
from spec import OBS_SIZE

GAME, ACTIVATION, SEEDS = "breakout", "tanh", (0, 1)
UPDATES_PER_CHUNK = 2
TOTAL_STEPS = 2 * UPDATES_PER_CHUNK * ppo.BATCH_SIZE


def networks(runs_dir):
    return [np.load(runs_dir / run_name(GAME, ACTIVATION, seed) / NPZ_FILE) for seed in SEEDS]


def test_stopped_run_resumes_to_the_same_networks(tmp_path, monkeypatch):
    monkeypatch.setattr(ppo, "LOG_EVERY_UPDATES", UPDATES_PER_CHUNK)
    straight, stopped = tmp_path / "straight", tmp_path / "stopped"
    assert ppo.train(GAME, [ACTIVATION], SEEDS, TOTAL_STEPS, runs_dir=straight)

    stopped.mkdir()
    (stopped / STOP_FILE).touch()
    assert ppo.train(GAME, [ACTIVATION], SEEDS, TOTAL_STEPS, runs_dir=stopped) is None
    run_dirs = [stopped / run_name(GAME, ACTIVATION, seed) for seed in SEEDS]
    assert all((run_dir / ppo.CHECKPOINT_FILE).exists() and not (run_dir / RESULT_FILE).exists() for run_dir in run_dirs)
    (stopped / STOP_FILE).unlink()
    assert ppo.train(GAME, [ACTIVATION], SEEDS, TOTAL_STEPS, runs_dir=stopped) == run_dirs
    assert not any((run_dir / ppo.CHECKPOINT_FILE).exists() for run_dir in run_dirs)
    assert ppo.train(GAME, [ACTIVATION], SEEDS, TOTAL_STEPS, runs_dir=stopped) == []  # finished runs are left alone

    original = np.load(reference_npz(GAME))
    for ours, resumed in zip(networks(straight), networks(stopped)):
        assert {name: ours[name].shape for name in ours.files} == {name: original[name].shape for name in original.files}
        for name in ours.files:
            np.testing.assert_array_equal(ours[name], resumed[name])
    first, second = networks(straight)
    assert not np.array_equal(first["actor/dense1/kernel"], second["actor/dense1/kernel"])  # seeds differ


def test_a_run_can_start_from_another_runs_weights(tmp_path, monkeypatch):
    """One update at a learning rate of zero, from a finished network or from its snapshot, leaves exactly those weights."""
    monkeypatch.setattr(ppo, "LOG_EVERY_UPDATES", 1)
    monkeypatch.setattr(ppo, "EVAL_EPISODES", 8)
    first, steps = tmp_path / "first", 2 * ppo.BATCH_SIZE
    ppo.train(GAME, [ACTIVATION], SEEDS[:1], steps, runs_dir=first, snapshot_every=ppo.BATCH_SIZE)
    finished = np.load(first / run_name(GAME, ACTIVATION, SEEDS[0]) / NPZ_FILE)
    for name, start_steps in (("from_finished", 0), ("from_snapshot", steps)):
        (run_dir,) = ppo.train(GAME, [ACTIVATION], SEEDS[:1], ppo.BATCH_SIZE, 0.0, runs_dir=tmp_path / name,
                               start_from=first, start_steps=start_steps)
        started = np.load(run_dir / NPZ_FILE)
        for array in finished.files:
            np.testing.assert_array_equal(started[array], finished[array])


def test_activation_switch_is_the_plain_activation():
    """Networks trained side by side pick their activation by index; each must compute what the named one does."""
    network = ppo.ActorCritic()
    obs = jax.random.uniform(jax.random.PRNGKey(1), (8, OBS_SIZE))
    for index, name in enumerate(ACTIVATION_NAMES):
        params = network.init(jax.random.PRNGKey(0), jnp.zeros(OBS_SIZE), index)
        pi, _ = network.apply(params, obs, index)
        expected = jax.nn.log_softmax(logits(ppo.actor_layers(params), obs, name))  # the distribution normalises its logits
        np.testing.assert_allclose(pi.logits, expected, rtol=1e-5, atol=1e-6)


def test_tanh_and_relu_train_together(tmp_path, monkeypatch):
    monkeypatch.setattr(ppo, "LOG_EVERY_UPDATES", UPDATES_PER_CHUNK)
    run_dirs = ppo.train(GAME, ACTIVATION_NAMES, SEEDS[:1], UPDATES_PER_CHUNK * ppo.BATCH_SIZE, runs_dir=tmp_path)
    assert [run_dir.name for run_dir in run_dirs] == [run_name(GAME, name, SEEDS[0]) for name in ACTIVATION_NAMES]
    first, second = (np.load(run_dir / NPZ_FILE)["actor/dense1/kernel"] for run_dir in run_dirs)
    assert not np.array_equal(first, second)
