class PururuException(Exception):
    """Base class for all exceptions raised by Pururu."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class CannotStartNewGame(PururuException):
    """Raised when a new game cannot be started."""
    pass


class CannotEndGame(PururuException):
    """Raised when a game cannot be ended."""
    pass


class GameEndedWithoutPrecondition(PururuException):
    """Raised when a game ends before the minimum playtime or has less than the minimum players."""
    pass
