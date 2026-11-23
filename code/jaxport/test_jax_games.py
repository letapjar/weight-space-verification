"""The JAX games must be the games in the top-level games.py. Run from the project root:

    python -m pytest jaxport

The step-for-step check is the strong one, and it carries the GIF checks with it:
games.py replays all four of the original's GIFs (test_games.py), and each JAX game
is shown here to take exactly the steps games.py takes. The two GIFs that need no
scripted randomness are also replayed directly.
"""
import jax
import jax.numpy as jnp
import numpy as np
import pytest

import games as reference
from jaxport.env import EnvState
from jaxport.games import GAMES, PacmanDraws, PongBall, PongDraws
from jaxport.play import load_actor, logits, play
from original import RETURN_TOLERANCE, gif_trace, recorded_play, reference_npz
from spec import NUM_ACTIONS, PLAY_MAX, PLAY_MIN, Action

NUM_ENVS = 256
STEPS_COMPARED = 3 * reference.MAX_EPISODE_STEPS  # long enough to cross several episode ends
LENGTH_TOLERANCE = 0.05
ACTION_SHARE_TOLERANCE = 0.02


def game_state(env, numpy_game):
    """The reference game's arrays as the JAX game's state (fields share their names)."""
    return env.State(*(jnp.asarray(getattr(numpy_game, field)) for field in env.State._fields))


def env_state(env, numpy_game):
    return EnvState(game_state(env, numpy_game), jnp.asarray(numpy_game._agent_or_moving), jnp.asarray(numpy_game.steps))


class RecordedRandom:
    """The reference game's random generator, keeping every array of uniforms it hands out."""

    def __init__(self, random):
        self._random, self.uniforms = random, []

    def rand(self, *shape):
        self.uniforms.append(self._random.rand(*shape))
        return self.uniforms[-1]

    def __getattr__(self, name):
        return getattr(self._random, name)


def pong_draws(uniforms, after):
    # A ball that appeared during the step is the reference game's new-ball draw.
    return PongDraws(jnp.asarray(uniforms[0]), PongBall(*(jnp.asarray(getattr(after, field)) for field in PongBall._fields)))


# A game's draws for one step, from the uniforms the reference game used (after its
# sticky-action roll) and the reference game as it stands after that step.
DRAWS = {
    "breakout": lambda uniforms, after: None,
    "freeway": lambda uniforms, after: None,
    "pong": pong_draws,
    "pacman": lambda uniforms, after: PacmanDraws(*(jnp.asarray(u) for u in uniforms)),
}
UNIFORM_ARRAYS_PER_STEP = {"breakout": 0, "freeway": 0, "pong": 1, "pacman": 3}


def test_every_game_is_ported():
    assert set(GAMES) == set(reference.GAMES) == set(DRAWS) == set(UNIFORM_ARRAYS_PER_STEP)


@pytest.mark.parametrize("name", GAMES)
def test_every_step_matches_the_reference_game(name):
    """From the reference game's own state, with its own draws, one JAX step must give its next state exactly.

    Half the copies play at random and half follow the original's network, so both
    early blunders and deep, well-played positions are compared.
    """
    env, numpy_game = GAMES[name](), reference.GAMES[name](num_envs=NUM_ENVS, seed=0)
    numpy_game.random = recorder = RecordedRandom(numpy_game.random)
    transition = jax.jit(jax.vmap(env.transition))
    actor, random = load_actor(reference_npz(name)), np.random.RandomState(1)
    plays_randomly = np.arange(NUM_ENVS) % 2 == 0
    obs, episodes_ended, rewards_seen = numpy_game.observation(), 0, set()
    for step in range(STEPS_COMPARED):
        policy_actions = jax.random.categorical(jax.random.PRNGKey(step), logits(actor, jnp.asarray(obs)))
        actions = np.where(plays_randomly, random.randint(NUM_ACTIONS, size=NUM_ENVS), np.asarray(policy_actions))
        before = env_state(env, numpy_game)
        recorder.uniforms.clear()
        obs, expected_reward, expected_done = numpy_game.step(actions)
        _sticky_roll, *uniforms = recorder.uniforms
        assert len(uniforms) == UNIFORM_ARRAYS_PER_STEP[name]
        # Copies whose episode ended now hold the next episode's opening state: pass it in as the fresh game.
        ours, after, reward, done, info = transition(before, jnp.asarray(actions), DRAWS[name](uniforms, numpy_game),
                                                     game_state(env, numpy_game))
        np.testing.assert_array_equal(ours, obs)
        np.testing.assert_array_equal(reward, expected_reward)
        np.testing.assert_array_equal(done, expected_done)
        np.testing.assert_array_equal(info["timed_out"], numpy_game.timed_out)
        for mine, theirs in zip(jax.tree.leaves(after), jax.tree.leaves(env_state(env, numpy_game))):
            np.testing.assert_array_equal(mine, theirs)
        episodes_ended += int(expected_done.sum())
        rewards_seen |= set(expected_reward.tolist())
    assert episodes_ended > NUM_ENVS  # resets and time-outs were exercised
    assert 1.0 in rewards_seen


@pytest.mark.parametrize("name", GAMES)
def test_original_network_plays_as_its_record_says(name):
    """The original's network must score, last and choose in the JAX game as it did in its own.

    This also covers the JAX game's own randomness (starts, the Pong opponent, the
    ghosts), which the step-for-step check takes from the reference game.
    """
    recorded = recorded_play(name)
    result = play(GAMES[name](), load_actor(reference_npz(name)), jax.random.PRNGKey(0), recorded["episodes"])
    assert abs(result["returns"].mean() - recorded["mean_return"]) <= RETURN_TOLERANCE * abs(recorded["mean_return"])
    assert abs(result["lengths"].mean() - recorded["mean_length"]) <= LENGTH_TOLERANCE * recorded["mean_length"]
    action_share = result["action_counts"] / result["action_counts"].sum()
    np.testing.assert_allclose(action_share, recorded["action_usage"], atol=ACTION_SHARE_TOLERANCE)


def test_breakout_reproduces_the_original_gif_step_for_step():
    """Feed the GIF's own paddle moves through the JAX rules: ball and bricks must match."""
    env, steps = GAMES["breakout"](), gif_trace("breakout")
    (row, col), second = steps[0]["ball"], steps[1]["ball"]
    game = env.reset_game(jax.random.PRNGKey(0))._replace(
        ball_row=jnp.int32(row), ball_col=jnp.int32(col), ball_d_row=jnp.int32(second[0] - row),
        ball_d_col=jnp.int32(second[1] - col), paddle_left=jnp.int32(steps[0]["paddle_left"]))
    _, state = env.start(game)
    step = jax.jit(env.step)
    move = {-1: Action.LEFT, 0: Action.NOOP, 1: Action.RIGHT}
    for number, (now, following) in enumerate(zip(steps, steps[1:])):
        assert [int(state.game.ball_row), int(state.game.ball_col)] == now["ball"]
        assert int(state.game.paddle_left) == now["paddle_left"]
        assert int(state.game.bricks.sum()) == now["bricks"]
        _, state, _, done, _ = step(jax.random.PRNGKey(number), state, move[following["paddle_left"] - now["paddle_left"]])
        assert not done
    assert len(steps) > 100


def test_freeway_reproduces_the_original_gif_step_for_step():
    """Feed the GIF's own agent moves through the JAX rules: agent and every lane must match."""
    env, steps, rules = GAMES["freeway"](), gif_trace("freeway"), reference.Freeway
    game = env.State(jnp.int32(steps[0]["agent"][0]), jnp.int32(steps[0]["agent"][1]),
                     jnp.asarray(steps[0]["lane_offsets"], dtype=jnp.int32))
    _, state = env.start(game)
    step = jax.jit(env.step)
    for number, (now, following) in enumerate(zip(steps, steps[1:])):
        assert [int(state.game.agent_row), int(state.game.agent_col)] == now["agent"]
        assert state.game.lane_offset.tolist() == now["lane_offsets"]
        (row, col), (next_row, next_col) = now["agent"], following["agent"]
        scores = row == rules.GOAL_ROW + 1 and [next_row, next_col] == [rules.START_ROW, rules.START_COL]
        if scores or next_row == row - 1:  # into the goal row and back to the start, or one row up
            action = Action.UP
        elif next_col != col:
            action = Action.RIGHT if next_col > col else Action.LEFT
        else:
            action = Action.NOOP
        _, state, reward, _, _ = step(jax.random.PRNGKey(number), state, action)
        assert float(reward) == (row == rules.GOAL_ROW + 1 and action == Action.UP)
    assert len(steps) > 100


def test_breakout_starts_in_every_column_heading_both_ways():
    env = GAMES["breakout"]()
    start = jax.vmap(env.reset_game)(jax.random.split(jax.random.PRNGKey(0), NUM_ENVS))
    assert set(np.asarray(start.ball_col).tolist()) == set(range(PLAY_MIN, PLAY_MAX + 1))
    assert set(np.asarray(start.ball_d_col).tolist()) == {-1, 1}
    assert int(start.bricks.sum()) == NUM_ENVS * int(env.FULL_WALL.sum())
