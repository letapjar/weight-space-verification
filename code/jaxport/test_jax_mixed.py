"""A mix of games: each game's share of the copies plays exactly that game, a balanced mix evens the games out,
and a network trained on a mix is scored on every game."""
import json

import jax
import jax.numpy as jnp
import numpy as np
import pytest

from jaxport import ppo
from jaxport.games import GAMES
from jaxport.mixed import MIXES, Copies, Mixed, games_of, make_batch, reward_scales
from jaxport.play import actor_from_arrays
from jaxport.turned import make_game
from original import NPZ_FILE, ORIGINAL_SCORES
from settings import EVAL_BY_GAME, LEARNING_RATE, NUM_ENVS, RESULT_FILE, ROLLOUT_STEPS, run_name
from spec import NUM_ACTIONS, OBS_SIZE

BALANCED, RAW = "all4", "all4raw"
SHARE = NUM_ENVS // len(GAMES)
STEPS = 30
HIDDEN = (24, 16, 8)  # three hidden layers where the original has two
COPIES = 4 * NUM_ENVS
UPDATES = 2


def test_names():
    assert games_of(BALANCED) == games_of(RAW) == tuple(GAMES) and games_of("pong") == ("pong",)
    assert isinstance(make_batch(BALANCED), Mixed) and isinstance(make_batch("pong_turned90"), Copies)
    assert make_batch(BALANCED).balance and make_batch(RAW).balance is None and make_batch("pong").balance is None
    with pytest.raises(ValueError):
        make_batch("tetris")


def test_scales_make_the_originals_best_scores_equal():
    scales = reward_scales(GAMES)
    worth = [scales[game] * max(ORIGINAL_SCORES[game].values()) for game in GAMES]
    np.testing.assert_allclose(worth, worth[0])
    np.testing.assert_array_equal(make_batch(RAW).scales, 1.0)


@pytest.mark.parametrize("name", MIXES)
def test_each_share_plays_its_own_game(name):
    """Stepping the mix is stepping each game alone on its share of the keys and actions, rewards scaled."""
    mix = make_batch(name)
    keys = jax.random.split(jax.random.PRNGKey(0), NUM_ENVS)
    obs, states = mix.reset_all(keys)
    assert obs.shape == (NUM_ENVS, OBS_SIZE) and len(states) == len(GAMES)
    alone = [jax.vmap(make_game(game).reset)(share) for game, share in zip(GAMES, jnp.split(keys, len(GAMES)))]
    for step in range(STEPS):
        step_keys = jax.random.split(jax.random.PRNGKey(step + 1), NUM_ENVS)
        actions = jax.random.randint(jax.random.PRNGKey(-step - 1), (NUM_ENVS,), 0, NUM_ACTIONS)
        obs, states, reward, done = mix.step_all(step_keys, states, actions)
        for index, game in enumerate(GAMES):
            share = slice(index * SHARE, (index + 1) * SHARE)
            game_obs, game_state, game_reward, game_done, _ = jax.vmap(make_game(game).step)(
                step_keys[share], alone[index][1], actions[share])
            alone[index] = (game_obs, game_state)
            np.testing.assert_array_equal(obs[share], game_obs)
            np.testing.assert_array_equal(done[share], game_done)
            np.testing.assert_allclose(reward[share], game_reward * mix.scales[index], rtol=1e-6)


def test_balance_normalises_each_games_advantages():
    advantages = jax.random.normal(jax.random.PRNGKey(0), (16, NUM_ENVS)) * jnp.repeat(jnp.array([1.0, 5.0, 0.1, 30.0]), SHARE) + 3.0
    by_game = np.asarray(make_batch(BALANCED).balance(advantages)).reshape(16, len(GAMES), SHARE)
    np.testing.assert_allclose(by_game.mean((0, 2)), 0.0, atol=1e-5)
    np.testing.assert_allclose(by_game.std((0, 2)), 1.0, atol=1e-4)


def test_only_the_border_is_on_in_every_game():
    always_on = make_batch(BALANCED).always_on()
    assert always_on.sum() == min(make_game(game).always_on().sum() for game in GAMES) == 36


def test_a_mix_trains_and_is_scored_on_every_game(tmp_path, monkeypatch):
    monkeypatch.setattr(ppo, "LOG_EVERY_UPDATES", 1)
    monkeypatch.setattr(ppo, "EVAL_EPISODES", 8)
    rollout = ROLLOUT_STEPS // 2
    (run_dir,) = ppo.train(BALANCED, ["tanh"], [0], UPDATES * COPIES * rollout, runs_dir=tmp_path,
                           hidden_sizes=HIDDEN, copies=COPIES, rollout_steps=rollout)
    assert run_dir.name == run_name(BALANCED, "tanh", 0)
    result = json.loads((run_dir / RESULT_FILE).read_text())
    assert list(result[EVAL_BY_GAME]) == list(GAMES) and "eval_mean" not in result and result["hidden_sizes"] == list(HIDDEN)
    assert result["num_envs"] == COPIES and result["total_steps"] == UPDATES * COPIES * rollout
    assert result["rollout_steps"] == rollout
    arrays = np.load(run_dir / NPZ_FILE)
    assert arrays["actor/dense1/kernel"].shape == (OBS_SIZE, HIDDEN[0])
    assert arrays["actor/dense3/kernel"].shape == HIDDEN[1:] and arrays["actor/logits/kernel"].shape == (HIDDEN[2], NUM_ACTIONS)
    assert len(actor_from_arrays(arrays)) == len(HIDDEN) + 1


def test_what_differs_from_the_original_names_the_folder_and_nothing_else_does():
    assert ppo.variant_tags() == [] and ppo.runs_dir_for(LEARNING_RATE) == ppo.JAX_RUNS_DIR
    tags = ppo.variant_tags((32, 32, 32), COPIES, always_on=ppo.FROZEN, matmul_precision="highest")
    assert tags == ["h32x32x32", "c256", "frozen", "highest"]
    assert ppo.runs_dir_for(0.005, 1, tags[:2]).name == "runs_jax_h32x32x32_c256_lr_0.005_snapshots"
