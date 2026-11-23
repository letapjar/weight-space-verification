"""Turned boards: the turn is a reordering of the inputs, actions follow the screen, and a rewired network plays the same."""
import jax
import numpy as np
import pytest

from experiments.rotate import rewire, turned_arrays
from jaxport.games import GAMES
from jaxport.play import actor_from_arrays, logits, play
from jaxport.turned import (Scrambled, Turned, game_action_of, make_game, parse_game_name, scrambled_inputs,
                            scrambled_name, turned_inputs, turned_name)
from original import reference_npz
from spec import GRID_SIZE, NUM_CHANNELS, OBS_SHAPE, OBS_SIZE, PLAY_MAX, PLAY_MIN, Action, Channel

GAME = "breakout"
HALF_TURN = 2
EPISODES = 256
SCORE_TOLERANCE = 1.0  # the two plays sample their actions differently, so the scores match only about this closely


def agent_cells(obs):
    return np.argwhere(np.asarray(obs).reshape(OBS_SHAPE)[..., Channel.AGENT] == 1)


def test_names():
    assert parse_game_name(GAME) == (GAME, 0)
    assert parse_game_name(turned_name(GAME, HALF_TURN)) == (GAME, HALF_TURN) and turned_name(GAME, HALF_TURN) == "breakout_turned180"
    assert isinstance(make_game(turned_name(GAME, 1)), Turned) and isinstance(make_game(GAME), GAMES[GAME])
    for bad in ("breakout_turned45", "breakout_turned360", "tetris", "tetris_turned90"):
        with pytest.raises(ValueError):
            make_game(bad)


@pytest.mark.parametrize("quarter_turns", (1, 2, 3))
def test_a_turn_reorders_the_inputs_and_four_quarter_turns_undo_it(quarter_turns):
    inputs = turned_inputs(quarter_turns)
    assert sorted(inputs) == list(range(OBS_SIZE))
    np.testing.assert_array_equal(turned_inputs(4), np.arange(OBS_SIZE))
    np.testing.assert_array_equal(inputs[turned_inputs(4 - quarter_turns)], np.arange(OBS_SIZE))
    actions = game_action_of(quarter_turns)
    assert actions[Action.NOOP] == Action.NOOP and sorted(actions) == list(range(len(Action)))
    np.testing.assert_array_equal(actions[game_action_of(4 - quarter_turns)], np.arange(len(Action)))


def test_half_turned_breakout_has_its_paddle_at_the_top_and_left_still_moves_it_left():
    env, turned = GAMES[GAME](), make_game(turned_name(GAME, HALF_TURN))
    key = jax.random.PRNGKey(0)
    normal_obs, _ = env.reset(key)
    obs, state = turned.reset(key)
    assert set(agent_cells(normal_obs)[:, 0]) == {PLAY_MAX} and set(agent_cells(obs)[:, 0]) == {GRID_SIZE - 1 - PLAY_MAX} == {PLAY_MIN}
    assert int(turned.always_on().sum()) == int(env.always_on().sum())  # the border is the same under a turn
    for action, shift in ((Action.LEFT, -1), (Action.RIGHT, 1)):
        moved, *_ = turned.step(key, state, action)
        np.testing.assert_array_equal(agent_cells(moved)[:, 1], agent_cells(obs)[:, 1] + shift)


def test_a_rewired_network_plays_the_turned_game_as_the_original_plays_the_game():
    arrays = np.load(reference_npz(GAME))
    env, turned = GAMES[GAME](), make_game(turned_name(GAME, HALF_TURN))
    actor, rewired = actor_from_arrays(arrays), actor_from_arrays(turned_arrays(arrays, HALF_TURN))
    boards = jax.vmap(lambda key: env.reset(key)[0])(jax.random.split(jax.random.PRNGKey(1), 64))
    np.testing.assert_array_equal(np.asarray(logits(rewired, boards[:, turned.inputs])),
                                  np.asarray(logits(actor, boards))[:, game_action_of(HALF_TURN)])
    key = jax.random.PRNGKey(0)
    normal_score = play(env, actor, key, EPISODES)["returns"].mean()
    assert abs(play(turned, rewired, key, EPISODES)["returns"].mean() - normal_score) <= SCORE_TOLERANCE
    assert play(turned, actor, key, EPISODES)["returns"].mean() < normal_score / 2  # not rewired, it cannot play


def test_a_scramble_moves_whole_cells_and_a_rewired_network_gives_the_same_outputs():
    seed = 7
    inputs = scrambled_inputs(seed)
    np.testing.assert_array_equal(np.sort(inputs), np.arange(OBS_SIZE))  # every input, once
    np.testing.assert_array_equal(inputs % NUM_CHANNELS, np.arange(OBS_SIZE) % NUM_CHANNELS)  # channels in place
    cells = (inputs // NUM_CHANNELS).reshape(-1, NUM_CHANNELS)
    assert (cells == cells[:, :1]).all() and len(set(cells[:, 0].tolist())) == GRID_SIZE * GRID_SIZE  # whole cells
    assert not np.array_equal(inputs, np.arange(OBS_SIZE)) and not np.array_equal(inputs, scrambled_inputs(seed + 1))
    env, scrambled = GAMES[GAME](), make_game(scrambled_name(GAME, seed))
    assert isinstance(scrambled, Scrambled) and int(scrambled.always_on().sum()) == int(env.always_on().sum())
    arrays = np.load(reference_npz(GAME))
    actor = actor_from_arrays(arrays)
    rewired = actor_from_arrays(rewire(arrays, inputs, np.asarray(scrambled.game_action)))
    boards = jax.vmap(lambda key: env.reset(key)[0])(jax.random.split(jax.random.PRNGKey(1), 64))
    np.testing.assert_array_equal(np.asarray(logits(rewired, boards[:, scrambled.inputs])), np.asarray(logits(actor, boards)))


def test_pong30_plays_on_where_pong_ends_its_episode():
    """The same keys and moves: Pong ends its episode after 5 points; pong30 is still in the same episode."""
    pong, long_pong = make_game("pong"), make_game("pong30")
    assert pong.rules.POINTS_PER_EPISODE == 5 and long_pong.rules.POINTS_PER_EPISODE == 30
    key = jax.random.PRNGKey(0)
    (_, state), (_, long_state) = pong.reset(key), long_pong.reset(key)
    for step_key in jax.random.split(key, 199):
        action = jax.random.randint(step_key, (), 0, len(Action))
        _, state, _, done, info = pong.step(step_key, state, action)
        _, long_state, _, long_done, _ = long_pong.step(step_key, long_state, action)
        if done:
            assert not info["timed_out"] and not long_done and int(long_state.game.points_played) == 5
            break
    else:
        raise AssertionError("Pong did not finish an episode in 199 steps of random play")
