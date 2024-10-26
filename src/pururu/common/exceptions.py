# Base Exception
class PururuException(Exception):
    """Base exception for all Pururu exceptions."""

# Domain Exceptions
class CannotStartNewGame(PururuException):
    """Raised when a new game cannot be started."""
    pass

class CannotEndGame(PururuException):
    """Raised when a game cannot be ended."""
    pass

class GameEndedWithoutPrecondition(PururuException):
    """Raised when a game ends before the minimum playtime or has less than the minimum players."""
    pass

# Application Exceptions

# Infrastructure Exceptions

class DiscordServiceException(PururuException):
    """Raised when an error related to Discord service occurs."""
    pass

# Common Exceptions

class CircuitBreakerException(PururuException):
    """Raised when the circuit breaker is open."""
    pass