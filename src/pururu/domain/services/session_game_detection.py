from collections import Counter


def infer_session_game(observations: dict[str, str], current_game: str | None = None) -> str | None:
    """
    Infers the session game from per-player observations.

    Each player votes with the last game they were seen playing. The game with the most
    distinct players wins. On a tie, the current game is kept when it is one of the
    winners; otherwise a stable winner is chosen.
    """
    if not observations:
        return current_game
    counts = Counter(observations.values())
    max_count = max(counts.values())
    winners = [game for game, count in counts.items() if count == max_count]
    if len(winners) == 1:
        return winners[0]
    if current_game in winners:
        return current_game
    return sorted(winners)[0]
