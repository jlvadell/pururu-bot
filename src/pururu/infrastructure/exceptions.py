class PururuInfrastructureException(Exception):
    """Base class for all exceptions raised by Pururu infrastructure."""
    pass


class DiscordServiceException(PururuInfrastructureException):
    """Raised when an error related to Discord service occurs."""
    pass
