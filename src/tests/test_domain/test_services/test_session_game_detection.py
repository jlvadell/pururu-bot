import pytest
from hamcrest import assert_that, equal_to, none

from pururu.domain.services.session_game_detection import infer_session_game


@pytest.mark.unit
def test_infer_session_game_empty_keeps_current():
    assert_that(infer_session_game({}, None), none())
    assert_that(infer_session_game({}, "League of Legends"), equal_to("League of Legends"))


@pytest.mark.unit
def test_infer_session_game_single_observation():
    assert_that(infer_session_game({"p1": "League of Legends"}), equal_to("League of Legends"))


@pytest.mark.unit
def test_infer_session_game_majority_wins():
    observations = {
        "p1": "League of Legends",
        "p2": "League of Legends",
        "p3": "VALORANT",
    }
    assert_that(infer_session_game(observations), equal_to("League of Legends"))


@pytest.mark.unit
def test_infer_session_game_tie_keeps_current_if_among_winners():
    observations = {"p1": "League of Legends", "p2": "VALORANT"}
    assert_that(infer_session_game(observations, "League of Legends"), equal_to("League of Legends"))
    assert_that(infer_session_game(observations, "VALORANT"), equal_to("VALORANT"))


@pytest.mark.unit
def test_infer_session_game_tie_without_current_picks_stable_winner():
    observations = {"p1": "League of Legends", "p2": "VALORANT"}
    assert_that(infer_session_game(observations, None), equal_to("League of Legends"))


@pytest.mark.unit
def test_infer_session_game_tie_where_current_is_not_a_winner():
    observations = {"p1": "League of Legends", "p2": "VALORANT"}
    assert_that(infer_session_game(observations, "Fortnite"), equal_to("League of Legends"))
