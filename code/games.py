"""MinAtar-style games on the shared grid spec (see spec.py), stepped in batches.

Every game runs `num_envs` independent copies at once as arrays. GridGame owns
what is common to all games: the wall border, the previous-frame channel, sticky
actions, the episode step limit, auto-reset and flattening. A game only supplies
its own rules (_reset, _step) and paints its AGENT / MOVING / TARGET cells.
"""
import numpy as np

from spec import OBS_SHAPE, OBS_SIZE, PLAY_MAX, PLAY_MIN, PLAY_SIZE, Action, Channel

MAX_EPISODE_STEPS = 200  # an episode still running after this many steps is cut off (the original's limit)
STICKY_ACTION_PROB = 0.0  # chance the previous action repeats (MinAtar uses 0.1); off by choice


class GridGame:
    def __init__(self, num_envs=1, sticky_action_prob=STICKY_ACTION_PROB, seed=None):
        self.num_envs = num_envs
        self.random = np.random.RandomState(seed)
        self.sticky_action_prob = sticky_action_prob
        self._env_ids = np.arange(num_envs)
        self.reset()

    # --- hooks a game implements -------------------------------------------
    def _reset(self, mask):
        """Start a new episode in every env where mask is True."""
        raise NotImplementedError

    def _step(self, actions):
        """Advance every env one step; return (reward, lost) arrays."""
        raise NotImplementedError

    def _paint(self, grid):
        """Set this game's AGENT, MOVING, TARGET (and any extra OBSTACLE) cells."""
        raise NotImplementedError

    # --- shared interface ---------------------------------------------------
    def reset(self):
        """Restart every env; return observations of shape (num_envs, OBS_SIZE)."""
        self.last_action = np.full(self.num_envs, Action.NOOP, dtype=np.int64)
        self.steps = np.zeros(self.num_envs, dtype=np.int64)
        self.timed_out = np.zeros(self.num_envs, dtype=bool)
        self._reset(np.ones(self.num_envs, dtype=bool))
        self.refresh()
        return self.observation()

    def refresh(self):
        """Re-render after game state was set directly (tests, replays).

        With no earlier step to show, the previous-frame channel shows the
        current frame.
        """
        grid = self._painted()
        self._agent_or_moving = self._agent_or_moving_of(grid)
        self._grid = self._finished(grid, self._agent_or_moving)

    def step(self, actions):
        """Return (observations, rewards, terminals).

        An episode ends when the game is lost or it reaches MAX_EPISODE_STEPS
        (`timed_out` says which, per env, for the step just taken). An env whose
        episode ends is reset immediately: its returned observation is the first
        frame of the next episode and its terminal flag is True.
        """
        actions = np.asarray(actions, dtype=np.int64)
        sticky = self.random.rand(self.num_envs) < self.sticky_action_prob
        actions = np.where(sticky, self.last_action, actions)
        previous = self._agent_or_moving

        reward, lost = self._step(actions)
        self.steps += 1
        self.timed_out = ~lost & (self.steps >= MAX_EPISODE_STEPS)
        terminal = lost | self.timed_out
        if terminal.any():
            self._reset(terminal)
            actions[terminal] = Action.NOOP
            self.steps[terminal] = 0
        self.last_action = actions

        grid = self._painted()
        current = self._agent_or_moving_of(grid)
        previous = np.where(terminal[:, None, None], current, previous)
        self._agent_or_moving = current
        self._grid = self._finished(grid, previous)
        return self.observation(), reward, terminal

    def snapshot(self):
        """Everything needed to continue these games exactly: all arrays and the random state."""
        arrays = {name: value.copy() for name, value in vars(self).items() if isinstance(value, np.ndarray)}
        return {"arrays": arrays, "random": self.random.get_state()}

    def restore(self, snapshot):
        """Put the games back exactly as they were when `snapshot` was taken."""
        for name, value in snapshot["arrays"].items():
            setattr(self, name, value.copy())
        self.random.set_state(snapshot["random"])

    def grid(self):
        """Observations as a (env, row, column, channel) boolean array."""
        return self._grid

    def observation(self):
        """Flattened: index = (row * GRID_SIZE + column) * NUM_CHANNELS + channel."""
        return self._grid.reshape(self.num_envs, OBS_SIZE).astype(np.float32)

    def _painted(self):
        grid = np.zeros((self.num_envs, *OBS_SHAPE), dtype=bool)
        self._paint(grid)
        return grid

    @staticmethod
    def _agent_or_moving_of(grid):
        return grid[..., Channel.AGENT] | grid[..., Channel.MOVING]

    @staticmethod
    def _finished(grid, previous):
        border = grid[..., Channel.OBSTACLE]
        border[:, [0, -1], :] = True
        border[:, :, [0, -1]] = True
        grid[..., Channel.PREVIOUS] = previous
        return grid


class Breakout(GridGame):
    """Breakout as played in the original experiment (rules read off its GIF).

    A PADDLE_WIDTH-cell paddle sits on the bottom playable row and moves one
    column per step. The ball travels on diagonals. Each step, after the paddle
    has moved:
      - a side or top wall ahead reverses that direction and the ball keeps moving;
      - a brick straight ahead (same column), else diagonally ahead, breaks for
        +1 reward: the ball stays where it is this step and reverses vertically;
      - at the paddle row, a paddle cell straight below reverses the ball
        vertically; clipping only the paddle's end reverses it both ways; in
        both cases the ball stays where it is this step. Otherwise the ball is
        lost: the episode ends with reward LOST_BALL_REWARD.
    When every brick is gone the wall is refilled. UP and DOWN do nothing here.

    Each episode starts with the ball on BALL_START_ROW in a random column,
    heading down and randomly left or right, above a centred paddle.
    """

    PADDLE_ROW = PLAY_MAX
    PADDLE_WIDTH = 3
    PADDLE_MAX_LEFT = PLAY_MAX - PADDLE_WIDTH + 1  # rightmost position of the paddle's left cell
    PADDLE_START_LEFT = PLAY_MIN + 3
    BRICK_ROWS = slice(PLAY_MIN, PLAY_MIN + 3)  # flush against the top wall
    BRICK_COLS = slice(PLAY_MIN, PLAY_MAX + 1)
    BALL_START_ROW = PLAY_MIN + 4
    BALL_START_D_ROW = 1  # heading down
    # The original's random play averages a negative return, so losing costs points;
    # the size of the penalty is inferred, not documented.
    LOST_BALL_REWARD = -1.0

    def __init__(self, num_envs=1, **kwargs):
        self.ball_row = np.zeros(num_envs, dtype=np.int64)
        self.ball_col = np.zeros(num_envs, dtype=np.int64)
        self.ball_d_row = np.zeros(num_envs, dtype=np.int64)
        self.ball_d_col = np.zeros(num_envs, dtype=np.int64)
        self.paddle_left = np.zeros(num_envs, dtype=np.int64)  # column of the paddle's left cell
        self.bricks = np.zeros((num_envs, *OBS_SHAPE[:2]), dtype=bool)
        super().__init__(num_envs, **kwargs)

    def _reset(self, mask):
        count = int(mask.sum())
        self.ball_row[mask] = self.BALL_START_ROW
        self.ball_col[mask] = self.random.randint(PLAY_MIN, PLAY_MAX + 1, size=count)
        self.ball_d_row[mask] = self.BALL_START_D_ROW
        self.ball_d_col[mask] = self.random.choice([-1, 1], size=count)
        self.paddle_left[mask] = self.PADDLE_START_LEFT
        self.bricks[mask] = False
        self._fill_bricks(mask)

    def _fill_bricks(self, mask):
        self.bricks[mask, self.BRICK_ROWS, self.BRICK_COLS] = True

    def _on_paddle(self, col):
        return (self.paddle_left <= col) & (col < self.paddle_left + self.PADDLE_WIDTH)

    def _step(self, actions):
        ids = self._env_ids
        left = self.paddle_left
        left = np.where(actions == Action.LEFT, np.maximum(PLAY_MIN, left - 1), left)
        left = np.where(actions == Action.RIGHT, np.minimum(self.PADDLE_MAX_LEFT, left + 1), left)
        self.paddle_left = left

        row, col, d_row, d_col = self.ball_row, self.ball_col, self.ball_d_row, self.ball_d_col
        ahead_col = col + d_col
        d_col = np.where((ahead_col < PLAY_MIN) | (ahead_col > PLAY_MAX), -d_col, d_col)
        d_row = np.where(row + d_row < PLAY_MIN, -d_row, d_row)
        ahead_row, ahead_col = row + d_row, col + d_col

        at_paddle_row = ahead_row == self.PADDLE_ROW
        paddle_below = at_paddle_row & self._on_paddle(col)
        paddle_clipped = at_paddle_row & ~paddle_below & self._on_paddle(ahead_col)
        lost = at_paddle_row & ~paddle_below & ~paddle_clipped

        brick_straight = self.bricks[ids, ahead_row, col]
        brick_diagonal = ~brick_straight & self.bricks[ids, ahead_row, ahead_col]
        self.bricks[ids[brick_straight], ahead_row[brick_straight], col[brick_straight]] = False
        self.bricks[ids[brick_diagonal], ahead_row[brick_diagonal], ahead_col[brick_diagonal]] = False
        broke = brick_straight | brick_diagonal
        self._fill_bricks(~self.bricks.any(axis=(1, 2)))

        bounced = broke | paddle_below | paddle_clipped  # the ball stays put this step
        self.ball_d_row = np.where(bounced, -d_row, d_row)
        self.ball_d_col = np.where(paddle_clipped, -d_col, d_col)
        self.ball_row = np.where(bounced | lost, row, ahead_row)
        self.ball_col = np.where(bounced | lost, col, ahead_col)
        reward = broke.astype(np.float32) + self.LOST_BALL_REWARD * lost
        return reward, lost

    def _paint(self, grid):
        ids = self._env_ids
        for offset in range(self.PADDLE_WIDTH):
            grid[ids, self.PADDLE_ROW, self.paddle_left + offset, Channel.AGENT] = True
        grid[ids, self.ball_row, self.ball_col, Channel.MOVING] = True
        grid[..., Channel.TARGET] = self.bricks


class Freeway(GridGame):
    """Freeway as played in the original experiment (rules read off its GIF).

    The agent starts at the bottom and scores +1 each time it steps into the
    goal row at the top, which sends it back to the start. Between them are
    six lanes of cars, CARS_PER_LANE per lane, evenly spaced and wrapping round.
    Lanes alternate direction and move one column every 1, 2 or 3 steps. Each
    step the agent moves (any of the four directions, one cell), then the cars
    move; an agent sharing a cell with a car is sent back to the start. The
    episode only ends at the step limit.
    """

    GOAL_ROW = PLAY_MIN
    START_ROW = PLAY_MAX
    START_COL = PLAY_MIN + 3
    LANE_ROWS = np.arange(PLAY_MIN + 1, PLAY_MAX)  # top lane first
    LANE_DIRECTION = np.array([1, -1, 1, -1, 1, -1])  # +1 moves right
    LANE_PERIOD = np.array([1, 2, 3, 2, 1, 3])  # steps per one-column move
    CARS_PER_LANE = 2
    CAR_SPACING = PLAY_SIZE // CARS_PER_LANE

    def __init__(self, num_envs=1, **kwargs):
        self.agent_row = np.zeros(num_envs, dtype=np.int64)
        self.agent_col = np.zeros(num_envs, dtype=np.int64)
        # column offset of each lane's cars from the left edge, in [0, CAR_SPACING)
        self.lane_offset = np.zeros((num_envs, len(self.LANE_ROWS)), dtype=np.int64)
        super().__init__(num_envs, **kwargs)

    def _reset(self, mask):
        self._send_to_start(mask)
        self.lane_offset[mask] = self.random.randint(self.CAR_SPACING, size=(int(mask.sum()), len(self.LANE_ROWS)))

    def _send_to_start(self, mask):
        self.agent_row[mask] = self.START_ROW
        self.agent_col[mask] = self.START_COL

    def _car_at(self, row, col):
        lane = row - self.LANE_ROWS[0]
        in_lane = (lane >= 0) & (lane < len(self.LANE_ROWS))
        offset = self.lane_offset[self._env_ids, np.clip(lane, 0, len(self.LANE_ROWS) - 1)]
        return in_lane & ((col - PLAY_MIN - offset) % self.CAR_SPACING == 0)

    def _step(self, actions):
        row = self.agent_row + (actions == Action.DOWN) - (actions == Action.UP)
        col = self.agent_col + (actions == Action.RIGHT) - (actions == Action.LEFT)
        self.agent_row = np.minimum(row, PLAY_MAX)
        self.agent_col = np.clip(col, PLAY_MIN, PLAY_MAX)
        scored = self.agent_row <= self.GOAL_ROW

        step_number = self.steps[:, None] + 1  # the base class counts this step after we return
        moves = step_number % self.LANE_PERIOD == 0
        self.lane_offset = (self.lane_offset + self.LANE_DIRECTION * moves) % self.CAR_SPACING

        hit = ~scored & self._car_at(self.agent_row, self.agent_col)
        self._send_to_start(scored | hit)
        return scored.astype(np.float32), np.zeros(self.num_envs, dtype=bool)

    def _paint(self, grid):
        ids = self._env_ids
        grid[ids, self.agent_row, self.agent_col, Channel.AGENT] = True
        grid[:, self.GOAL_ROW, PLAY_MIN:PLAY_MAX + 1, Channel.TARGET] = True
        for lane, row in enumerate(self.LANE_ROWS):
            for car in range(self.CARS_PER_LANE):
                col = PLAY_MIN + (self.lane_offset[:, lane] + car * self.CAR_SPACING) % PLAY_SIZE
                grid[ids, row, col, Channel.MOVING] = True


class Pong(GridGame):
    """Pong as played in the original experiment (rules read off its GIF).

    The agent's PADDLE_HEIGHT-cell paddle is on the left, an opponent's on the
    right, and behind the opponent the wall is a reward target. The ball
    travels on diagonals. Each step the agent's paddle moves (up or down, one
    cell), then the opponent's paddle moves one cell towards the ball's row
    with probability OPPONENT_FOLLOW_PROB, then the ball moves:
      - the top or bottom wall ahead reverses it vertically and it keeps moving;
      - if the cell it would enter is a paddle, it stays where it is this step
        and reverses horizontally;
      - if that cell is in a paddle's column but not on the paddle, the point
        is over: +1 if it passed the opponent, -1 if it passed the agent, and a
        new ball appears near the middle.
    An episode is POINTS_PER_EPISODE points. LEFT and RIGHT do nothing here.
    """

    PADDLE_HEIGHT = 3
    PADDLE_MAX_TOP = PLAY_MAX - PADDLE_HEIGHT + 1  # lowest position of a paddle's top cell
    AGENT_COL = PLAY_MIN
    OPPONENT_COL = PLAY_MAX
    TARGET_COL = PLAY_MAX + 1  # the wall behind the opponent
    AGENT_START_TOP = PLAY_MIN + 3
    OPPONENT_START_TOPS = (PLAY_MIN + 1, PLAY_MIN + 2)
    # Not documented. The GIF shows 57 moves in 94 chances; 0.57 also makes the original's
    # network's episodes last as long in our game as its record says (about 74 steps).
    OPPONENT_FOLLOW_PROB = 0.57
    BALL_START_ROWS = (PLAY_MIN + 2, PLAY_MAX - 2)  # inclusive range
    BALL_START_COLS = (PLAY_MIN + 3, PLAY_MIN + 4)  # inclusive range
    POINTS_PER_EPISODE = 5

    def __init__(self, num_envs=1, **kwargs):
        self.ball_row = np.zeros(num_envs, dtype=np.int64)
        self.ball_col = np.zeros(num_envs, dtype=np.int64)
        self.ball_d_row = np.zeros(num_envs, dtype=np.int64)
        self.ball_d_col = np.zeros(num_envs, dtype=np.int64)
        self.agent_top = np.zeros(num_envs, dtype=np.int64)
        self.opponent_top = np.zeros(num_envs, dtype=np.int64)
        self.points_played = np.zeros(num_envs, dtype=np.int64)
        super().__init__(num_envs, **kwargs)

    def _reset(self, mask):
        count = int(mask.sum())
        self.agent_top[mask] = self.AGENT_START_TOP
        self.opponent_top[mask] = self.random.choice(self.OPPONENT_START_TOPS, size=count)
        self.points_played[mask] = 0
        self._new_ball(mask)

    def _new_ball(self, mask):
        count = int(mask.sum())
        self.ball_row[mask] = self.random.randint(self.BALL_START_ROWS[0], self.BALL_START_ROWS[1] + 1, size=count)
        self.ball_col[mask] = self.random.randint(self.BALL_START_COLS[0], self.BALL_START_COLS[1] + 1, size=count)
        self.ball_d_row[mask] = self.random.choice([-1, 1], size=count)
        self.ball_d_col[mask] = self.random.choice([-1, 1], size=count)

    def _opponent_follows(self):
        return self.random.rand(self.num_envs) < self.OPPONENT_FOLLOW_PROB

    def _covers(self, top, row):
        return (top <= row) & (row < top + self.PADDLE_HEIGHT)

    def _step(self, actions):
        top = self.agent_top + (actions == Action.DOWN) - (actions == Action.UP)
        self.agent_top = np.clip(top, PLAY_MIN, self.PADDLE_MAX_TOP)

        centre = self.opponent_top + self.PADDLE_HEIGHT // 2
        follows = self._opponent_follows()
        self.opponent_top = np.clip(self.opponent_top + np.sign(self.ball_row - centre) * follows,
                                    PLAY_MIN, self.PADDLE_MAX_TOP)

        row, col, d_row, d_col = self.ball_row, self.ball_col, self.ball_d_row, self.ball_d_col
        ahead_row = row + d_row
        d_row = np.where((ahead_row < PLAY_MIN) | (ahead_row > PLAY_MAX), -d_row, d_row)
        ahead_row, ahead_col = row + d_row, col + d_col

        at_agent, at_opponent = ahead_col == self.AGENT_COL, ahead_col == self.OPPONENT_COL
        bounced = (at_agent & self._covers(self.agent_top, ahead_row)) | \
                  (at_opponent & self._covers(self.opponent_top, ahead_row))
        conceded, scored = at_agent & ~bounced, at_opponent & ~bounced
        moves = ~bounced & ~conceded & ~scored
        self.ball_row = np.where(moves, ahead_row, row)
        self.ball_col = np.where(moves, ahead_col, col)
        self.ball_d_row = d_row
        self.ball_d_col = np.where(bounced, -d_col, d_col)

        point_over = conceded | scored
        self.points_played += point_over
        self._new_ball(point_over)
        reward = scored.astype(np.float32) - conceded
        return reward, self.points_played >= self.POINTS_PER_EPISODE

    def _paint(self, grid):
        ids = self._env_ids
        for offset in range(self.PADDLE_HEIGHT):
            grid[ids, self.agent_top + offset, self.AGENT_COL, Channel.AGENT] = True
            grid[ids, self.opponent_top + offset, self.OPPONENT_COL, Channel.MOVING] = True
        grid[ids, self.ball_row, self.ball_col, Channel.MOVING] = True
        grid[:, PLAY_MIN:PLAY_MAX + 1, self.TARGET_COL, Channel.TARGET] = True


def _maze_distances(walls):
    """Shortest path length between every pair of open cells; cells are numbered row * width + column."""
    height, width = walls.shape
    far = height * width  # longer than any path, used for walls and unreachable cells
    distance = np.full((height * width, height * width), far, dtype=np.int64)
    for start in np.flatnonzero(~walls):
        distance[start, start] = 0
        frontier = [start]
        while frontier:
            following = []
            for cell in frontier:
                row, col = divmod(cell, width)
                for d_row, d_col in MOVES:
                    neighbour = (row + d_row) * width + col + d_col
                    if not walls[row + d_row, col + d_col] and distance[start, neighbour] == far:
                        distance[start, neighbour] = distance[start, cell] + 1
                        following.append(neighbour)
            frontier = following
    return distance


MOVES = np.array([(-1, 0), (1, 0), (0, -1), (0, 1)])  # up, down, left, right as (d_row, d_col)


class Pacman(GridGame):
    """Pac-Man as played in the original experiment (rules read off its GIF).

    A fixed maze with a pellet on every open cell except the agent's start;
    eating one gives +1. Two ghosts start in the top corners. Each step the
    agent moves one cell (a move into a wall does nothing), then each ghost
    moves one cell: with probability GHOST_CHASE_PROB the step that brings it
    closest to the agent through the maze, otherwise a random open neighbour.
    The episode ends when a ghost and the agent share a cell (reward
    CAUGHT_REWARD), or when every pellet is eaten.
    """

    MAZE = (
        "##########",
        "#........#",
        "#.##..##.#",
        "#.#....#.#",
        "#...##...#",
        "#...##...#",
        "#.#....#.#",
        "#.##..##.#",
        "#........#",
        "##########",
    )
    WALLS = np.array([[cell == "#" for cell in row] for row in MAZE])
    DISTANCE = _maze_distances(WALLS)
    AGENT_START = (PLAY_MAX, PLAY_MIN + 3)
    GHOST_STARTS = ((PLAY_MIN, PLAY_MIN), (PLAY_MIN, PLAY_MAX))
    # Neither is documented. With these, the original's network and random play both last as
    # long and score as much in our game as the original's record says they did in its own.
    GHOST_CHASE_PROB = 0.38
    CAUGHT_REWARD = -1.0

    def __init__(self, num_envs=1, **kwargs):
        self.agent_row = np.zeros(num_envs, dtype=np.int64)
        self.agent_col = np.zeros(num_envs, dtype=np.int64)
        self.ghost_row = np.zeros((num_envs, len(self.GHOST_STARTS)), dtype=np.int64)
        self.ghost_col = np.zeros((num_envs, len(self.GHOST_STARTS)), dtype=np.int64)
        self.pellets = np.zeros((num_envs, *OBS_SHAPE[:2]), dtype=bool)
        super().__init__(num_envs, **kwargs)

    def _reset(self, mask):
        self.agent_row[mask], self.agent_col[mask] = self.AGENT_START
        self.ghost_row[mask] = [row for row, _ in self.GHOST_STARTS]
        self.ghost_col[mask] = [col for _, col in self.GHOST_STARTS]
        self.pellets[mask] = ~self.WALLS
        self.pellets[mask, self.AGENT_START[0], self.AGENT_START[1]] = False

    def _caught(self):
        return ((self.ghost_row == self.agent_row[:, None]) & (self.ghost_col == self.agent_col[:, None])).any(axis=1)

    def _move_ghosts(self):
        width = OBS_SHAPE[1]
        new_row = self.ghost_row[:, :, None] + MOVES[:, 0]  # (env, ghost, move)
        new_col = self.ghost_col[:, :, None] + MOVES[:, 1]
        is_open = ~self.WALLS[new_row, new_col]
        agent_cell = (self.agent_row * width + self.agent_col)[:, None, None]
        distance = self.DISTANCE[new_row * width + new_col, agent_cell]
        tie_break = self.random.rand(*distance.shape)
        chase = np.where(is_open, distance + tie_break, np.inf).argmin(axis=2)
        wander = np.where(is_open, self.random.rand(*distance.shape), -1.0).argmax(axis=2)
        chases = self.random.rand(*chase.shape) < self.GHOST_CHASE_PROB
        move = MOVES[np.where(chases, chase, wander)]
        self.ghost_row = self.ghost_row + move[..., 0]
        self.ghost_col = self.ghost_col + move[..., 1]

    def _step(self, actions):
        ids = self._env_ids
        row = self.agent_row + (actions == Action.DOWN) - (actions == Action.UP)
        col = self.agent_col + (actions == Action.RIGHT) - (actions == Action.LEFT)
        blocked = self.WALLS[row, col]
        self.agent_row = np.where(blocked, self.agent_row, row)
        self.agent_col = np.where(blocked, self.agent_col, col)

        ate = self.pellets[ids, self.agent_row, self.agent_col]
        self.pellets[ids, self.agent_row, self.agent_col] = False

        caught = self._caught()  # walked into a ghost
        self._move_ghosts()
        caught |= self._caught()
        cleared = ~self.pellets.any(axis=(1, 2))
        reward = ate.astype(np.float32) + self.CAUGHT_REWARD * caught
        return reward, caught | cleared

    def _paint(self, grid):
        ids = self._env_ids
        grid[ids, self.agent_row, self.agent_col, Channel.AGENT] = True
        for ghost in range(len(self.GHOST_STARTS)):
            grid[ids, self.ghost_row[:, ghost], self.ghost_col[:, ghost], Channel.MOVING] = True
        grid[..., Channel.TARGET] = self.pellets
        grid[..., Channel.OBSTACLE] = self.WALLS


GAMES = {"breakout": Breakout, "freeway": Freeway, "pong": Pong, "pacman": Pacman}
