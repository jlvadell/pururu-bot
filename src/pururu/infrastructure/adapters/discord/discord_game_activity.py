import discord

PLAYING_ACTIVITY_TYPES = {discord.ActivityType.playing, discord.ActivityType.streaming}


def extract_playing_game_name(activities) -> str | None:
    """
    Returns the name of the game Discord reports as currently being played or streamed.
    Ignores Spotify, custom status and other non-game activities.
    """
    if not activities:
        return None
    if not isinstance(activities, (list, tuple, set)):
        activities = (activities,)
    for activity in activities:
        activity_type = getattr(activity, "type", None)
        if activity_type not in PLAYING_ACTIVITY_TYPES:
            continue
        name = getattr(activity, "name", None)
        if name and name.strip():
            return name.strip()
    return None
