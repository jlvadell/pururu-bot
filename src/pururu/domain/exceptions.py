class BaseDomainException(Exception):
    """Base exception for domain-related errors."""
    pass


# -----------------------------------------------
# Session exceptions
# -----------------------------------------------

class SessionNotFoundException(BaseDomainException):
    """Raised when a session is not found."""
    pass


class SessionAlreadyConcludedException(BaseDomainException):
    """Raised when trying to modify a session that is already concluded."""
    pass


class CannotConcludeSessionException(BaseDomainException):
    """Raised when a session cannot be concluded due to business rules."""
    pass


class PlayerNotConnectedException(BaseDomainException):
    """Raised when you try to register a disconnection of an already disconnected player."""
    pass


class NoPlayerIntervalsException(BaseDomainException):
    """Raised when trying to do player operations in a session without players intervals registered (e.g., get first joiner)."""
    pass


# -----------------------------------------------
# Concurrency exceptions
# -----------------------------------------------

class OptimisticLockingFailureException(BaseDomainException):
    """Raised when an optimistic locking conflict occurs."""
    pass


# -----------------------------------------------
# Invalid state exceptions
# -----------------------------------------------
class PollResolutionStrategyUnsupportedException(BaseDomainException):
    """Raised when an unsupported poll resolution strategy is encountered."""
    pass


# -----------------------------------------------
# Event exceptions
# -----------------------------------------------
class EventPublishException(BaseDomainException):
    """Raised when the event publishing fails."""
    pass
