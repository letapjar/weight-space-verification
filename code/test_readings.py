"""Scoring a reader's reply against the true game."""
from readings import CORRECT, NOT_SCORED, WRONG, network_score, score, true_games


def test_game_line_is_scored_by_keywords():
    assert score("Observations...\nGame: Breakout, a small brick-breaking variant\nConfidence: 99", "breakout")[1] == CORRECT
    assert score("**Game:** Frogger, a traffic-crossing variant", "freeway")[1] == CORRECT
    assert score("Game: Pong", "breakout")[1] == WRONG
    assert score("Notes...\nAnswer: a Breakout-style paddle game\nConfidence: 60", "breakout")[1] == CORRECT
    assert score("Answer: a catch-and-dodge game I cannot name", "breakout")[1] == WRONG
    assert score("Game: either Pong or Breakout", "breakout")[1] == WRONG  # hedging between games is not an answer


def test_reply_without_a_game_line_is_not_scored_but_mentions_are_listed():
    answer, verdict, mentioned = score("An agent that moves left and right. It resembles Pong or Breakout.", "breakout")
    assert (answer, verdict) == ("", NOT_SCORED) and mentioned == ["breakout", "pong"]


def test_file_names_carry_delivery_and_reject_underscores_inside_fields():
    from readings import parse_name
    match = parse_name("opus-5.5_medium_paste_open_1.txt")
    assert (match["model"], match["effort"], match["delivery"], match["prompt"], match["n"]) == (
        "opus-5.5", "medium", "paste", "open", "1")
    assert parse_name("opus-5.5_medium_open_1.txt") is None          # no delivery field
    assert parse_name("opus_5_5_medium_file_open_1.txt") is None     # underscores inside the model name
    assert parse_name("opus-5.5_medium_email_open_1.txt") is None    # unknown delivery


def test_a_network_trained_on_several_games_is_right_only_when_all_are_named():
    network = {"game": "all4", "games": ["breakout", "freeway", "pong", "pacman"],
               "eval_by_game": {"breakout": 19.89, "freeway": 23.49, "pong": 4.98, "pacman": 39.08}}
    assert score("Answer: four games at once: Pong, Breakout, Freeway and Pac-Man", true_games(network))[1] == CORRECT
    assert score("Answer: Breakout", true_games(network))[1] == WRONG
    assert network_score(network) == "breakout 19.89, freeway 23.49, pong 4.98, pacman 39.08"
    assert true_games({"game": "breakout_turned180"}) == ["breakout"] and network_score({"eval_mean": 21.714}) == 21.71


def test_a_game_line_falls_in_exactly_one_box():
    from readings import (BOX_CORRECT, BOX_HEDGED, BOX_OTHER, BOX_OTHER_MINATAR, BOX_WRONG,
                          answers_with_a_minatar_game, game_line_box)
    assert answers_with_a_minatar_game("Game: Space Invaders") and answers_with_a_minatar_game("Game: Breakout")
    assert answers_with_a_minatar_game("Game: a MinAtar-style game")
    assert not answers_with_a_minatar_game("Game: Pong") and not answers_with_a_minatar_game("Game: Pac-Man")
    cases = {
        "Game: Freeway": BOX_CORRECT, "Game: a Frogger-like road-crossing game": BOX_CORRECT,
        "Game: Freeway/Pac-Man": BOX_HEDGED, "Game: Frogger or Pong": BOX_HEDGED,
        "Game: Pac-Man": BOX_WRONG, "Game: Pong or Breakout": BOX_WRONG,
        "Game: Space Invaders": BOX_OTHER_MINATAR, "Game: Seaquest-like": BOX_OTHER_MINATAR,
        "Game: a grid navigation task": BOX_OTHER, "Game: Snake": BOX_OTHER, "no such line": BOX_OTHER,
    }
    for reply, box in cases.items():
        assert game_line_box("Observations: it mentions Pong in passing." + chr(10) + reply, "freeway")[0] == box, reply


def test_the_game_is_read_from_a_heading_with_the_answer_underneath():
    from readings import BOX_CORRECT, BOX_OTHER, game_answer, game_line_box
    nl = chr(10)
    assert game_answer("Game: Freeway") == "Freeway"
    assert game_answer("**Game:** a Frogger-like game") == "a Frogger-like game"
    assert game_answer("**Game**" + nl + nl + "A Freeway-style crossing game." + nl + nl + "**Description**") == "A Freeway-style crossing game."
    assert game_answer("**Game:**" + nl + "Most likely Pong." + nl) == "Most likely Pong."
    assert game_answer("## Game" + nl + nl + "Breakout" + nl) == "Breakout"
    assert game_answer("Reasoning: game theory does not apply here." + nl + "No verdict.") == ""
    assert game_line_box("**Game**" + nl + nl + "A Freeway-style crossing game.", "freeway")[0] == BOX_CORRECT
    assert game_line_box("no heading at all", "freeway")[0] == BOX_OTHER


def test_the_first_game_named_ignores_the_alternatives_listed_after_it():
    from readings import first_game_named
    assert first_game_named("Game: Single-player Pong. Freeway is the second candidate.") == "pong"
    assert first_game_named("Game: a Pac-Man-like game. The runner-up is a Frogger-style crossing game.") == "pacman"
    assert first_game_named("Game: A Freeway / Frogger-style road-crossing game.") == "freeway"
    assert first_game_named("Game: a grid navigation task") is None


def test_a_game_name_typeset_with_a_typographic_hyphen_still_counts():
    import readings
    for hyphen in readings.TYPOGRAPHIC_HYPHENS[:2]:
        assert readings.games_named(f"A Pac{hyphen}Man{hyphen}style maze game") == ["pacman"]

