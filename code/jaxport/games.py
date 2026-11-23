"""The four games in JAX. Each is its class in the top-level games.py, restated as pure
functions on one copy of the game; rules are documented there, and every constant is
taken from there. State fields keep the names of that class's arrays.
"""
from typing import NamedTuple

import jax
import jax.numpy as jnp
import numpy as np

import games as reference
from jaxport.env import CELLS, COLS, ROWS, GridEnv, layers, select
from spec import PLAY_MAX, PLAY_MIN, Action

DIRECTIONS = jnp.array([-1, 1])


class BreakoutState(NamedTuple):
    ball_row: jax.Array
    ball_col: jax.Array
    ball_d_row: jax.Array
    ball_d_col: jax.Array
    paddle_left: jax.Array
    bricks: jax.Array


class Breakout(GridEnv):
    rules = reference.Breakout
    State = BreakoutState
    FULL_WALL = np.zeros(CELLS, dtype=bool)
    FULL_WALL[rules.BRICK_ROWS, rules.BRICK_COLS] = True

    def reset_game(self, key):
        col_key, direction_key = jax.random.split(key)
        return BreakoutState(
            ball_row=jnp.int32(self.rules.BALL_START_ROW),
            ball_col=jax.random.randint(col_key, (), PLAY_MIN, PLAY_MAX + 1),
            ball_d_row=jnp.int32(self.rules.BALL_START_D_ROW),
            ball_d_col=jax.random.choice(direction_key, DIRECTIONS),
            paddle_left=jnp.int32(self.rules.PADDLE_START_LEFT),
            bricks=jnp.asarray(self.FULL_WALL),
        )

    def _on_paddle(self, left, col):
        return (left <= col) & (col < left + self.rules.PADDLE_WIDTH)

    def step_game(self, game, action, steps, draws):
        rules = self.rules
        left = game.paddle_left
        left = jnp.where(action == Action.LEFT, jnp.maximum(PLAY_MIN, left - 1), left)
        left = jnp.where(action == Action.RIGHT, jnp.minimum(rules.PADDLE_MAX_LEFT, left + 1), left)

        row, col, d_row, d_col = game.ball_row, game.ball_col, game.ball_d_row, game.ball_d_col
        ahead_col = col + d_col
        d_col = jnp.where((ahead_col < PLAY_MIN) | (ahead_col > PLAY_MAX), -d_col, d_col)
        d_row = jnp.where(row + d_row < PLAY_MIN, -d_row, d_row)
        ahead_row, ahead_col = row + d_row, col + d_col

        at_paddle_row = ahead_row == rules.PADDLE_ROW
        paddle_below = at_paddle_row & self._on_paddle(left, col)
        paddle_clipped = at_paddle_row & ~paddle_below & self._on_paddle(left, ahead_col)
        lost = at_paddle_row & ~paddle_below & ~paddle_clipped

        brick_straight = game.bricks[ahead_row, col]
        brick_diagonal = ~brick_straight & game.bricks[ahead_row, ahead_col]
        broke = brick_straight | brick_diagonal
        broken_col = jnp.where(brick_straight, col, ahead_col)
        bricks = game.bricks & ~(broke & (ROWS == ahead_row) & (COLS == broken_col))
        bricks = jnp.where(bricks.any(), bricks, self.FULL_WALL)

        bounced = broke | paddle_below | paddle_clipped  # the ball stays put this step
        game = BreakoutState(
            ball_row=jnp.where(bounced | lost, row, ahead_row),
            ball_col=jnp.where(bounced | lost, col, ahead_col),
            ball_d_row=jnp.where(bounced, -d_row, d_row),
            ball_d_col=jnp.where(paddle_clipped, -d_col, d_col),
            paddle_left=left,
            bricks=bricks,
        )
        reward = broke.astype(jnp.float32) + rules.LOST_BALL_REWARD * lost
        return game, reward, lost

    def paint(self, game):
        paddle = (ROWS == self.rules.PADDLE_ROW) & self._on_paddle(game.paddle_left, COLS)
        ball = (ROWS == game.ball_row) & (COLS == game.ball_col)
        return layers(agent=paddle, moving=ball, target=game.bricks)


class FreewayState(NamedTuple):
    agent_row: jax.Array
    agent_col: jax.Array
    lane_offset: jax.Array  # per lane


class Freeway(GridEnv):
    rules = reference.Freeway
    State = FreewayState
    NUM_LANES = len(rules.LANE_ROWS)
    PLAYABLE_COLS = (COLS >= PLAY_MIN) & (COLS <= PLAY_MAX)
    STATIC_TARGETS = PLAYABLE_COLS & (ROWS == rules.GOAL_ROW)

    def reset_game(self, key):
        return FreewayState(
            agent_row=jnp.int32(self.rules.START_ROW),
            agent_col=jnp.int32(self.rules.START_COL),
            lane_offset=jax.random.randint(key, (self.NUM_LANES,), 0, self.rules.CAR_SPACING),
        )

    def _car_at(self, lane_offset, row, col):
        lane = row - self.rules.LANE_ROWS[0]
        in_lane = (lane >= 0) & (lane < self.NUM_LANES)
        offset = lane_offset[jnp.clip(lane, 0, self.NUM_LANES - 1)]
        return in_lane & ((col - PLAY_MIN - offset) % self.rules.CAR_SPACING == 0)

    def step_game(self, game, action, steps, draws):
        rules = self.rules
        row = game.agent_row + (action == Action.DOWN) - (action == Action.UP)
        col = game.agent_col + (action == Action.RIGHT) - (action == Action.LEFT)
        row, col = jnp.minimum(row, PLAY_MAX), jnp.clip(col, PLAY_MIN, PLAY_MAX)
        scored = row <= rules.GOAL_ROW

        moves = (steps + 1) % rules.LANE_PERIOD == 0
        lane_offset = (game.lane_offset + rules.LANE_DIRECTION * moves) % rules.CAR_SPACING

        to_start = scored | self._car_at(lane_offset, row, col)
        game = FreewayState(
            agent_row=jnp.where(to_start, rules.START_ROW, row),
            agent_col=jnp.where(to_start, rules.START_COL, col),
            lane_offset=lane_offset,
        )
        return game, scored.astype(jnp.float32), jnp.bool_(False)

    def paint(self, game):
        agent = (ROWS == game.agent_row) & (COLS == game.agent_col)
        cars = self.PLAYABLE_COLS & self._car_at(game.lane_offset, ROWS, COLS)
        return layers(agent=agent, moving=cars, target=self.STATIC_TARGETS)


class PongBall(NamedTuple):
    ball_row: jax.Array
    ball_col: jax.Array
    ball_d_row: jax.Array
    ball_d_col: jax.Array


class PongState(NamedTuple):
    ball_row: jax.Array
    ball_col: jax.Array
    ball_d_row: jax.Array
    ball_d_col: jax.Array
    agent_top: jax.Array
    opponent_top: jax.Array
    points_played: jax.Array


class PongDraws(NamedTuple):
    follow_roll: jax.Array  # uniform; the opponent follows the ball when it is below OPPONENT_FOLLOW_PROB
    new_ball: PongBall  # the ball that appears if this step ends a point


class Pong(GridEnv):
    rules = reference.Pong
    State = PongState
    PLAYABLE_ROWS = (ROWS >= PLAY_MIN) & (ROWS <= PLAY_MAX)
    STATIC_TARGETS = PLAYABLE_ROWS & (COLS == rules.TARGET_COL)  # the wall behind the opponent

    def _new_ball(self, key):
        rules, (row_key, col_key, d_row_key, d_col_key) = self.rules, jax.random.split(key, 4)
        return PongBall(
            ball_row=jax.random.randint(row_key, (), rules.BALL_START_ROWS[0], rules.BALL_START_ROWS[1] + 1),
            ball_col=jax.random.randint(col_key, (), rules.BALL_START_COLS[0], rules.BALL_START_COLS[1] + 1),
            ball_d_row=jax.random.choice(d_row_key, DIRECTIONS),
            ball_d_col=jax.random.choice(d_col_key, DIRECTIONS),
        )

    def reset_game(self, key):
        top_key, ball_key = jax.random.split(key)
        return PongState(
            *self._new_ball(ball_key),
            agent_top=jnp.int32(self.rules.AGENT_START_TOP),
            opponent_top=jax.random.choice(top_key, jnp.array(self.rules.OPPONENT_START_TOPS)),
            points_played=jnp.int32(0),
        )

    def draw(self, key):
        roll_key, ball_key = jax.random.split(key)
        return PongDraws(jax.random.uniform(roll_key), self._new_ball(ball_key))

    def _covers(self, top, row):
        return (top <= row) & (row < top + self.rules.PADDLE_HEIGHT)

    def step_game(self, game, action, steps, draws):
        rules = self.rules
        agent_top = game.agent_top + (action == Action.DOWN) - (action == Action.UP)
        agent_top = jnp.clip(agent_top, PLAY_MIN, rules.PADDLE_MAX_TOP)

        centre = game.opponent_top + rules.PADDLE_HEIGHT // 2
        follows = draws.follow_roll < rules.OPPONENT_FOLLOW_PROB
        opponent_top = jnp.clip(game.opponent_top + jnp.sign(game.ball_row - centre) * follows,
                                PLAY_MIN, rules.PADDLE_MAX_TOP)

        row, col, d_row, d_col = game.ball_row, game.ball_col, game.ball_d_row, game.ball_d_col
        ahead_row = row + d_row
        d_row = jnp.where((ahead_row < PLAY_MIN) | (ahead_row > PLAY_MAX), -d_row, d_row)
        ahead_row, ahead_col = row + d_row, col + d_col

        at_agent, at_opponent = ahead_col == rules.AGENT_COL, ahead_col == rules.OPPONENT_COL
        bounced = (at_agent & self._covers(agent_top, ahead_row)) | (at_opponent & self._covers(opponent_top, ahead_row))
        conceded, scored = at_agent & ~bounced, at_opponent & ~bounced
        point_over = conceded | scored
        moves = ~bounced & ~point_over
        ball = PongBall(
            ball_row=jnp.where(moves, ahead_row, row),
            ball_col=jnp.where(moves, ahead_col, col),
            ball_d_row=d_row,
            ball_d_col=jnp.where(bounced, -d_col, d_col),
        )
        points_played = game.points_played + point_over
        game = PongState(*select(point_over, draws.new_ball, ball), agent_top, opponent_top, points_played)
        reward = scored.astype(jnp.float32) - conceded
        return game, reward, points_played >= rules.POINTS_PER_EPISODE

    def paint(self, game):
        rules = self.rules
        agent = (COLS == rules.AGENT_COL) & self._covers(game.agent_top, ROWS)
        opponent = (COLS == rules.OPPONENT_COL) & self._covers(game.opponent_top, ROWS)
        ball = (ROWS == game.ball_row) & (COLS == game.ball_col)
        return layers(agent=agent, moving=opponent | ball, target=self.STATIC_TARGETS)


class PacmanState(NamedTuple):
    agent_row: jax.Array
    agent_col: jax.Array
    ghost_row: jax.Array  # per ghost
    ghost_col: jax.Array
    pellets: jax.Array


class PacmanDraws(NamedTuple):
    """Uniforms, per ghost (and per move for the first two)."""
    tie_break: jax.Array  # orders equally good chasing moves
    wander: jax.Array  # the open move with the largest value is the random one
    chase_roll: jax.Array  # the ghost chases when this is below GHOST_CHASE_PROB


class Pacman(GridEnv):
    rules = reference.Pacman
    State = PacmanState
    NUM_GHOSTS = len(rules.GHOST_STARTS)
    WIDTH = CELLS[1]
    MOVES = jnp.asarray(reference.MOVES)
    WALLS = jnp.asarray(rules.WALLS)
    DISTANCE = jnp.asarray(rules.DISTANCE, dtype=jnp.int32)
    START_PELLETS = ~rules.WALLS
    START_PELLETS[rules.AGENT_START] = False

    def reset_game(self, key):
        rules = self.rules
        return PacmanState(
            agent_row=jnp.int32(rules.AGENT_START[0]),
            agent_col=jnp.int32(rules.AGENT_START[1]),
            ghost_row=jnp.array([row for row, _ in rules.GHOST_STARTS], dtype=jnp.int32),
            ghost_col=jnp.array([col for _, col in rules.GHOST_STARTS], dtype=jnp.int32),
            pellets=jnp.asarray(self.START_PELLETS),
        )

    def draw(self, key):
        tie_key, wander_key, chase_key = jax.random.split(key, 3)
        per_move = (self.NUM_GHOSTS, len(self.MOVES))
        return PacmanDraws(jax.random.uniform(tie_key, per_move), jax.random.uniform(wander_key, per_move),
                           jax.random.uniform(chase_key, (self.NUM_GHOSTS,)))

    @staticmethod
    def _caught(agent_row, agent_col, ghost_row, ghost_col):
        return ((ghost_row == agent_row) & (ghost_col == agent_col)).any()

    def _move_ghosts(self, agent_row, agent_col, ghost_row, ghost_col, draws):
        new_row = ghost_row[:, None] + self.MOVES[:, 0]  # (ghost, move)
        new_col = ghost_col[:, None] + self.MOVES[:, 1]
        is_open = ~self.WALLS[new_row, new_col]
        distance = self.DISTANCE[new_row * self.WIDTH + new_col, agent_row * self.WIDTH + agent_col]
        shortest = jnp.where(is_open, distance, distance.max() + 1).min(axis=1, keepdims=True)
        chase = jnp.where(is_open & (distance == shortest), draws.tie_break, jnp.inf).argmin(axis=1)
        wander = jnp.where(is_open, draws.wander, -1.0).argmax(axis=1)
        move = self.MOVES[jnp.where(draws.chase_roll < self.rules.GHOST_CHASE_PROB, chase, wander)]
        return ghost_row + move[:, 0], ghost_col + move[:, 1]

    def step_game(self, game, action, steps, draws):
        row = game.agent_row + (action == Action.DOWN) - (action == Action.UP)
        col = game.agent_col + (action == Action.RIGHT) - (action == Action.LEFT)
        blocked = self.WALLS[row, col]
        row, col = jnp.where(blocked, game.agent_row, row), jnp.where(blocked, game.agent_col, col)

        ate = game.pellets[row, col]
        pellets = game.pellets & ~((ROWS == row) & (COLS == col))

        caught = self._caught(row, col, game.ghost_row, game.ghost_col)  # walked into a ghost
        ghost_row, ghost_col = self._move_ghosts(row, col, game.ghost_row, game.ghost_col, draws)
        caught |= self._caught(row, col, ghost_row, ghost_col)
        cleared = ~pellets.any()
        reward = ate.astype(jnp.float32) + self.rules.CAUGHT_REWARD * caught
        return PacmanState(row, col, ghost_row, ghost_col, pellets), reward, caught | cleared

    def paint(self, game):
        agent = (ROWS == game.agent_row) & (COLS == game.agent_col)
        ghosts = ((ROWS[..., None] == game.ghost_row) & (COLS[..., None] == game.ghost_col)).any(axis=-1)
        return layers(agent=agent, moving=ghosts, target=game.pellets, obstacle=self.WALLS)


GAMES = {"breakout": Breakout, "freeway": Freeway, "pong": Pong, "pacman": Pacman}


class Pong30(Pong):
    """Pong with episodes of LONG_PONG_POINTS points where the original plays 5. The step limit is unchanged, so
    an episode is cut off at MAX_EPISODE_STEPS long before that many points: in effect, Pong played to the limit."""
    rules = type("Pong30Rules", (reference.Pong,), {"POINTS_PER_EPISODE": 30})


# Games that are not the original's: never compared with its networks or with games.py step for step.
VARIANTS = {"pong30": Pong30}
