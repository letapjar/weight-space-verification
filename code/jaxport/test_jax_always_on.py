"""Always-on inputs: which they are, that their weights train in step with the bias, and the two ways of taming that."""
import json

import jax
import numpy as np
import pytest

from jaxport import ppo
from jaxport.games import GAMES
from original import ACTOR, ACTOR_LAYERS, CRITIC, CRITIC_LAYERS
from settings import ACTIVATION_NAMES, CURVE_FILE, LEARNING_RATE, RESULT_FILE, STOP_FILE, run_name
from spec import GRID_SIZE, NUM_ACTIONS

BORDER_CELLS = 4 * (GRID_SIZE - 1)
EXTRA_ALWAYS_ON = {"breakout": 0, "freeway": 8, "pong": 8, "pacman": 16}  # goal row, wall behind the opponent, maze walls
PROBE_GAMES, PROBE_STEPS = 32, 60
GAME, UPDATES, NUM_UPDATES = "pacman", 2, 100
RELU = ACTIVATION_NAMES.index("relu")
IN_STEP_RTOL, IN_STEP_ATOL = 1e-2, 1e-6  # a change is the difference of two float32 weights, so it is only this exact


@pytest.mark.parametrize("name", GAMES)
def test_always_on_inputs_are_on_in_every_board(name):
    env = GAMES[name]()
    fixed = env.always_on()
    assert fixed.sum() == BORDER_CELLS + EXTRA_ALWAYS_ON[name]

    def random_play(key):
        reset_key, key = jax.random.split(key)
        first, state = env.reset(reset_key)

        def one_step(state, key):
            action_key, step_key = jax.random.split(key)
            obs, state, _, _, _ = env.step(step_key, state, jax.random.randint(action_key, (), 0, NUM_ACTIONS))
            return state, obs

        _, boards = jax.lax.scan(one_step, state, jax.random.split(key, PROBE_STEPS))
        return first, boards

    first, boards = jax.jit(jax.vmap(random_play))(jax.random.split(jax.random.PRNGKey(0), PROBE_GAMES))
    assert (np.asarray(first)[..., fixed] == 1).all() and (np.asarray(boards)[..., fixed] == 1).all()


def first_layers(runner):
    weights = runner.params[ppo.FLAX_PARAMS]
    return [{name: np.asarray(array) for name, array in weights[net][layers[0]].items()}
            for net, layers in ((ACTOR, ACTOR_LAYERS), (CRITIC, CRITIC_LAYERS))]


def changes(strategy):
    """(change in each always-on weight, change in the bias, largest change among the other weights), per network."""
    init, advance = ppo.make_trainer(GAME, LEARNING_RATE, NUM_UPDATES, scale_steps=True)
    before = init(jax.random.PRNGKey(0), RELU)
    after, _ = jax.jit(advance, static_argnums=1)(before, UPDATES, ppo.ALWAYS_ON_STRATEGIES.index(strategy))
    fixed = GAMES[GAME]().always_on()
    return [(new["kernel"][fixed] - old["kernel"][fixed], new["bias"] - old["bias"],
             np.abs(new["kernel"][~fixed] - old["kernel"][~fixed]).max())
            for old, new in zip(first_layers(before), first_layers(after))]


def test_always_on_weights_train_in_step_with_the_bias_unless_frozen_or_slowed():
    normal, frozen, slowed = (changes(strategy) for strategy in ppo.ALWAYS_ON_STRATEGIES)
    for (normal_rows, normal_bias, _), (frozen_rows, frozen_bias, frozen_rest), (slowed_rows, slowed_bias, slowed_rest) in zip(
            normal, frozen, slowed):
        # Normal training: every always-on weight of a unit moves exactly as that unit's bias does.
        np.testing.assert_allclose(normal_rows, np.broadcast_to(normal_bias, normal_rows.shape), rtol=IN_STEP_RTOL, atol=IN_STEP_ATOL)
        assert np.abs(normal_bias).max() > 0
        # Frozen: those weights stay put; the bias and the other weights still train.
        assert (frozen_rows == 0).all() and np.abs(frozen_bias).max() > 0 and frozen_rest > 0
        # Slowed: still in step with the bias, but both take much smaller steps; the other weights train as usual.
        np.testing.assert_allclose(slowed_rows, np.broadcast_to(slowed_bias, slowed_rows.shape), rtol=IN_STEP_RTOL, atol=IN_STEP_ATOL / 10)
        assert 0 < np.abs(slowed_bias).max() < np.abs(normal_bias).max() / 10 and slowed_rest > 0


# On a graphics card, a network trained in a group does not come out the same as that network trained alone:
# the card computes a batch of networks in a different order of operations, and the numbers drift apart from the
# start. On a processor the two agree, and that is where this test holds.
@pytest.mark.skipif(jax.devices()[0].platform != "cpu", reason="group size changes the arithmetic on a graphics card")
def test_strategies_side_by_side_train_as_they_do_alone():
    """One program holding every strategy gives each network what a program of that strategy alone gives."""
    init, advance = ppo.make_trainer(GAME, LEARNING_RATE, NUM_UPDATES, scale_steps=True)
    start = init(jax.random.PRNGKey(0), RELU)
    indices = np.arange(len(ppo.ALWAYS_ON_STRATEGIES))
    together, _ = jax.jit(jax.vmap(advance, in_axes=(0, None, 0)), static_argnums=1)(
        jax.tree.map(lambda leaf: np.stack([leaf] * len(indices)), start), UPDATES, indices)
    for index in indices:
        alone, _ = jax.jit(advance, static_argnums=1)(start, UPDATES, index)
        for side_by_side, by_itself in zip(jax.tree.leaves(ppo.one_network(together.params, index)),
                                           jax.tree.leaves(alone.params)):
            np.testing.assert_allclose(side_by_side, by_itself, rtol=1e-4, atol=1e-6)


def test_step_scales_are_what_each_strategy_says():
    normal, frozen, slowed = (ppo.ALWAYS_ON_STRATEGIES.index(strategy) for strategy in (ppo.NORMAL, ppo.FROZEN, ppo.SLOWED))
    for name in GAMES:
        env = GAMES[name]()
        fixed = np.asarray(env.always_on())
        weight_scales, bias_scales = (np.asarray(scales) for scales in ppo.first_layer_step_scales(env))
        smaller = np.float32(1.0 / (1 + fixed.sum()))
        assert (weight_scales[:, ~fixed] == 1).all()  # no strategy touches the other inputs
        assert (weight_scales[normal] == 1).all() and bias_scales[normal] == 1  # so normal training is unchanged
        assert (weight_scales[frozen, fixed] == 0).all() and bias_scales[frozen] == 1
        assert (weight_scales[slowed, fixed] == smaller).all() and bias_scales[slowed] == smaller


def test_strategies_stopped_apart_resume_together(tmp_path, monkeypatch):
    """Two programs of one strategy each, stopped, carry on as one program once they are at the same step."""
    monkeypatch.setattr(ppo, "LOG_EVERY_UPDATES", 1)
    steps, seeds = 4 * ppo.BATCH_SIZE, (0,)
    dirs = {strategy: tmp_path / strategy for strategy in (ppo.FROZEN, ppo.SLOWED)}

    def one_chunk(strategy):
        (dirs[strategy] / STOP_FILE).touch()
        assert ppo.train(GAME, ["relu"], seeds, steps, always_on=strategy, runs_dir=dirs[strategy]) is None
        (dirs[strategy] / STOP_FILE).unlink()

    def together():
        return ppo.train(GAME, ["relu"], seeds, steps, strategy_dirs=dirs)

    dirs[ppo.FROZEN].mkdir()
    one_chunk(ppo.FROZEN)
    with pytest.raises(SystemExit):  # slowed has no checkpoint yet: starting it would restart frozen too
        together()
    dirs[ppo.SLOWED].mkdir()
    one_chunk(ppo.SLOWED)
    one_chunk(ppo.SLOWED)
    with pytest.raises(SystemExit):  # slowed is a chunk ahead
        together()
    one_chunk(ppo.FROZEN)

    run_dirs = [folder / run_name(GAME, "relu", seed) for folder in dirs.values() for seed in seeds]
    assert together() == run_dirs
    for strategy, run_dir in zip(dirs, run_dirs):
        result = json.loads((run_dir / RESULT_FILE).read_text())
        assert result["always_on"] == strategy and result["total_steps"] == steps and result["trained_together"] == 2
        assert not (run_dir / ppo.CHECKPOINT_FILE).exists()
        curve = (run_dir / CURVE_FILE).read_text().splitlines()
        assert len(curve) == 1 + steps // ppo.BATCH_SIZE  # the chunks before the stops are still in the curve
