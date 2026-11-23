"""Drift tests: the env must match the written spec and the original's observed play."""
import numpy as np
import pytest
import torch

from games import GAMES, MAX_EPISODE_STEPS, MOVES, Breakout, Freeway, Pacman, Pong
from original import RETURN_TOLERANCE
from ppo import evaluate
from report import gif_trace, policy_from_reference_npz, reference_npz, reference_record
from spec import (
    GRID_SIZE,
    NUM_ACTIONS,
    OBS_SIZE,
    PLAY_MAX,
    PLAY_MIN,
    PLAY_SIZE,
    Action,
    Channel,
    obs_index,
)

NUM_ENVS = 16


def test_spec_numbers():
    assert (GRID_SIZE, PLAY_MIN, PLAY_MAX, PLAY_SIZE) == (10, 1, 8, 8)
    assert OBS_SIZE == 500
    assert [a.name for a in Action] == ["NOOP", "UP", "DOWN", "LEFT", "RIGHT"]
    assert NUM_ACTIONS == 5


def test_index_examples_from_spec():
    assert obs_index(0, 0, 0) == 0
    assert obs_index(0, 0, 4) == 4
    assert obs_index(0, 1, 0) == 5
    assert obs_index(9, 9, 4) == 499


@pytest.mark.parametrize("name", GAMES)
def test_flattening_matches_index_formula(name):
    game = GAMES[name](num_envs=NUM_ENVS, seed=0)
    grid, obs = game.grid(), game.observation()
    assert obs.shape == (NUM_ENVS, OBS_SIZE)
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            for channel in Channel:
                assert (obs[:, obs_index(row, col, channel)] == grid[:, row, col, channel]).all()


@pytest.mark.parametrize("name", GAMES)
@pytest.mark.parametrize("sticky", [0.0, 0.25])
def test_invariants_under_random_play(name, sticky):
    game = GAMES[name](num_envs=NUM_ENVS, sticky_action_prob=sticky, seed=0)
    rng = np.random.RandomState(0)
    interior = (slice(None), slice(PLAY_MIN, PLAY_MAX + 1), slice(PLAY_MIN, PLAY_MAX + 1))
    terminals = 0
    for _ in range(3000):
        before = game.grid()
        obs, reward, terminal = game.step(rng.randint(NUM_ACTIONS, size=NUM_ENVS))
        grid = game.grid()
        terminals += terminal.sum()

        assert set(np.unique(obs)) <= {0.0, 1.0}
        obstacle = grid[..., Channel.OBSTACLE]
        assert obstacle[:, [0, -1], :].all() and obstacle[:, :, [0, -1]].all()
        # the agent and moving objects never leave the playable area (Pong's target is a wall)
        for channel in (Channel.AGENT, Channel.MOVING):
            assert grid[..., channel].sum() == grid[interior + (channel,)].sum()
        # previous frame = last step's agent or moving cells (start frame after a reset)
        was = before[..., Channel.AGENT] | before[..., Channel.MOVING]
        now = grid[..., Channel.AGENT] | grid[..., Channel.MOVING]
        expected = np.where(terminal[:, None, None], now, was)
        assert (grid[..., Channel.PREVIOUS] == expected).all()
        assert set(np.unique(reward)) <= {-1.0, 0.0, 1.0}
    assert terminals > 0


def test_breakout_paddle_is_three_wide_and_only_left_right_move_it():
    game = Breakout(num_envs=1, seed=0)
    assert game.grid()[0, Breakout.PADDLE_ROW, :, Channel.AGENT].sum() == Breakout.PADDLE_WIDTH == 3
    left = game.paddle_left[0]
    for action in (Action.UP, Action.DOWN, Action.NOOP):
        game.step([action])
        assert game.paddle_left[0] == left
    game.step([Action.LEFT])
    assert game.paddle_left[0] == left - 1
    for _ in range(GRID_SIZE):  # cannot leave the playable area
        game.step([Action.RIGHT])
        if game.paddle_left[0] == Breakout.PADDLE_MAX_LEFT:
            break
    assert game.paddle_left[0] + Breakout.PADDLE_WIDTH - 1 == PLAY_MAX


def test_breakout_reproduces_the_original_gif_step_for_step():
    """Feed the GIF's own paddle moves through our rules: ball and bricks must match."""
    steps = gif_trace("breakout")
    game = Breakout(num_envs=1, seed=0)
    (game.ball_row[0], game.ball_col[0]), second = steps[0]["ball"], steps[1]["ball"]
    game.ball_d_row[0], game.ball_d_col[0] = second[0] - game.ball_row[0], second[1] - game.ball_col[0]
    game.paddle_left[0] = steps[0]["paddle_left"]
    game.refresh()
    move = {-1: Action.LEFT, 0: Action.NOOP, 1: Action.RIGHT}
    for now, following in zip(steps, steps[1:]):
        assert [game.ball_row[0], game.ball_col[0]] == now["ball"]
        assert game.paddle_left[0] == now["paddle_left"]
        assert game.bricks[0].sum() == now["bricks"]
        _, _, terminal = game.step([move[following["paddle_left"] - now["paddle_left"]]])
        assert not terminal[0]
    assert len(steps) > 100


@pytest.mark.parametrize("name", GAMES)
def test_original_network_scores_in_our_game_what_it_scored_in_its_own(name):
    """The strongest check that our rules match: the original's network, trained on its
    own game, must do as well in ours as its training record says it did there."""
    recorded = reference_record(name)["final_performance"]["sample"]["mean_return"]
    returns, _ = evaluate(policy_from_reference_npz(reference_npz(name)), name)
    assert abs(returns.mean() - recorded) <= RETURN_TOLERANCE * abs(recorded)


def test_freeway_reproduces_the_original_gif_step_for_step():
    """Feed the GIF's own agent moves through our rules: agent and every lane must match."""
    steps = gif_trace("freeway")
    game = Freeway(num_envs=1, seed=0)
    game.agent_row[0], game.agent_col[0] = steps[0]["agent"]
    game.lane_offset[0] = steps[0]["lane_offsets"]
    game.refresh()
    for now, following in zip(steps, steps[1:]):
        assert [game.agent_row[0], game.agent_col[0]] == now["agent"]
        assert list(game.lane_offset[0]) == now["lane_offsets"]
        (row, col), (next_row, next_col) = now["agent"], following["agent"]
        scores = row == Freeway.GOAL_ROW + 1 and [next_row, next_col] == [Freeway.START_ROW, Freeway.START_COL]
        if scores or next_row == row - 1:  # into the goal row and back to the start, or one row up
            action = Action.UP
        elif next_col != col:
            action = Action.RIGHT if next_col > col else Action.LEFT
        else:
            action = Action.NOOP
        _, reward, _ = game.step([action])
        assert reward[0] == (row == Freeway.GOAL_ROW + 1 and action == Action.UP)
    assert len(steps) > 100


def test_breakout_starts_vary_and_episodes_stop_at_the_step_limit():
    game = Breakout(num_envs=256, seed=0)
    assert (game.ball_row == Breakout.BALL_START_ROW).all() and (game.ball_d_row == 1).all()
    assert set(game.ball_col) == set(range(PLAY_MIN, PLAY_MAX + 1))
    assert set(game.ball_d_col) == {-1, 1}

    game = Breakout(num_envs=NUM_ENVS, seed=0)
    for step in range(1, MAX_EPISODE_STEPS + 1):  # a paddle under the ball never loses it
        actions = np.full(NUM_ENVS, Action.NOOP)
        actions[game.ball_col < game.paddle_left + 1] = Action.LEFT
        actions[game.ball_col > game.paddle_left + 1] = Action.RIGHT
        _, _, terminal = game.step(actions)
        assert terminal.all() == (step == MAX_EPISODE_STEPS) and terminal.any() == terminal.all()
    assert game.timed_out.all() and (game.steps == 0).all()


def test_pong_reproduces_the_original_gif_step_for_step():
    """Feed the GIF's paddle moves through our rules: the ball must follow the GIF.

    The opponent's moves and each new ball are random in the game, so both are
    taken from the GIF; everything the ball does in between is ours.
    """
    steps = gif_trace("pong")

    class ScriptedPong(Pong):
        follows = False

        def _opponent_follows(self):
            return np.array([self.follows])

    def place_ball(index):
        (row, col), (next_row, next_col) = steps[index]["ball"], steps[index + 1]["ball"]
        game.ball_row[0], game.ball_col[0] = row, col
        game.ball_d_row[0], game.ball_d_col[0] = next_row - row, next_col - col

    game = ScriptedPong(num_envs=1, seed=0)
    game.agent_top[0], game.opponent_top[0] = steps[0]["agent_top"], steps[0]["opponent_top"]
    place_ball(0)
    points = 0
    for index, (now, following) in enumerate(zip(steps, steps[1:])):
        assert [game.ball_row[0], game.ball_col[0]] == now["ball"], index
        assert (game.agent_top[0], game.opponent_top[0]) == (now["agent_top"], now["opponent_top"]), index
        move = following["agent_top"] - now["agent_top"]
        # a move away from the ball is the GIF's next episode starting, not the opponent following
        towards_ball = np.sign(now["ball"][0] - (now["opponent_top"] + Pong.PADDLE_HEIGHT // 2))
        game.follows = following["opponent_top"] - now["opponent_top"] == towards_ball != 0
        _, reward, terminal = game.step([{-1: Action.UP, 0: Action.NOOP, 1: Action.DOWN}.get(move, Action.NOOP)])
        if reward[0] != 0:  # a point ended: the GIF supplies the new ball (and, at a new episode, the paddles)
            points += 1
            assert terminal[0] == (points % Pong.POINTS_PER_EPISODE == 0)
            if terminal[0]:
                game.agent_top[0], game.opponent_top[0] = following["agent_top"], following["opponent_top"]
            if index + 2 < len(steps):
                place_ball(index + 1)
    assert points >= Pong.POINTS_PER_EPISODE and len(steps) > 100


def test_pacman_reproduces_the_original_gif_step_for_step():
    """Feed the GIF's agent moves through our rules: maze, pellets and the episode end must match.

    The ghosts move at random in the game, so their positions are taken from the GIF.
    """
    steps = gif_trace("pacman")
    move_action = {(-1, 0): Action.UP, (1, 0): Action.DOWN, (0, -1): Action.LEFT, (0, 1): Action.RIGHT, (0, 0): Action.NOOP}

    class ScriptedPacman(Pacman):
        next_ghosts = None

        def _move_ghosts(self):
            self.ghost_row[0], self.ghost_col[0] = zip(*self.next_ghosts)

    game = ScriptedPacman(num_envs=1, seed=0)
    cleared = 0
    for now, following in zip(steps, steps[1:]):
        assert [game.agent_row[0], game.agent_col[0]] == now["agent"]
        assert sorted(zip(game.ghost_row[0].tolist(), game.ghost_col[0].tolist())) == sorted(map(tuple, now["ghosts"]))
        hidden = {tuple(ghost) for ghost in now["ghosts"]}
        ours = {(int(r), int(c)) for r, c in zip(*np.nonzero(game.pellets[0]))} - hidden
        assert ours == {tuple(cell) for cell in now["visible_pellets"]}
        delta = (following["agent"][0] - now["agent"][0], following["agent"][1] - now["agent"][1])
        if delta not in move_action:  # the GIF jumps to a new episode: the agent stepped onto the last pellet
            (last_pellet,) = ours
            delta = (last_pellet[0] - now["agent"][0], last_pellet[1] - now["agent"][1])
        game.next_ghosts = following["ghosts"]
        _, _, terminal = game.step([move_action[delta]])
        cleared += int(terminal[0])
    assert cleared == 1 and len(steps) > 100
