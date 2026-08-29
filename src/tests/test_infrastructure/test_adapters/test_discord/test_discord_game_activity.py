from unittest.mock import MagicMock

import discord
import pytest
from hamcrest import assert_that, equal_to, none

from pururu.infrastructure.adapters.discord.discord_game_activity import extract_playing_game_name


def _activity(activity_type, name):
    activity = MagicMock()
    activity.type = activity_type
    activity.name = name
    return activity


@pytest.mark.unit
def test_extract_playing_game_name_from_playing_activity():
    activities = (_activity(discord.ActivityType.listening, "Spotify"),
                  _activity(discord.ActivityType.playing, "League of Legends"))

    assert_that(extract_playing_game_name(activities), equal_to("League of Legends"))


@pytest.mark.unit
def test_extract_playing_game_name_from_streaming():
    activities = (_activity(discord.ActivityType.streaming, "VALORANT"),)

    assert_that(extract_playing_game_name(activities), equal_to("VALORANT"))


@pytest.mark.unit
def test_extract_playing_game_name_ignores_spotify_and_custom_status():
    activities = (_activity(discord.ActivityType.listening, "Spotify"),
                  _activity(discord.ActivityType.custom, "Hola"))

    assert_that(extract_playing_game_name(activities), none())


@pytest.mark.unit
def test_extract_playing_game_name_single_activity():
    activity = _activity(discord.ActivityType.playing, "Minecraft")
    assert_that(extract_playing_game_name(activity), equal_to("Minecraft"))
