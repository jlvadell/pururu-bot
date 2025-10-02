class InfrastructureException(Exception):
    """Base exception for infrastructure-related errors."""
    pass

# AWS exceptions
## SQS
class SQSDeserializationException(InfrastructureException):
    """Raised when there is an error deserializing a message from SQS."""
    pass

class SQSHandlerNotFoundException(InfrastructureException):
    """Raised when no handler is found for a specific SQS event."""
    pass