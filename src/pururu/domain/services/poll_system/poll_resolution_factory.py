from pururu.domain.entities.poll import PollResolutionType
from pururu.domain.services.poll_system.poll_resolution_strategy import SendMessagePollResolution, PollResolutionStrategy
from pururu.domain.exceptions import PollResolutionStrategyUnsupportedException
from pururu.common import logger


class PollResolutionFactory:
    def __init__(self, discord_service):
        self.discord_service = discord_service
        self.logger = logger.get_logger(__name__)

    def get_strategy(self, resolution_type) -> PollResolutionStrategy:
        if resolution_type == PollResolutionType.SEND_MESSAGE:
            return SendMessagePollResolution(self.discord_service)
        else:
            self.logger.error(f"Unsupported Poll resolution type {resolution_type}")
            raise PollResolutionStrategyUnsupportedException(f"Unknown resolution type: {resolution_type}")
