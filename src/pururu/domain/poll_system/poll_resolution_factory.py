from domain.exceptions import PururuException
from pururu.domain.entities import PollResolutionType
from pururu.domain.poll_system.poll_resolution_strategy import SendMessagePollResolution, PollResolutionStrategy


class PollResolutionFactory:
    def __init__(self, discord_service):
        self.discord_service = discord_service

    def get_strategy(self, resolution_type) -> PollResolutionStrategy:
        if resolution_type == PollResolutionType.SEND_MESSAGE:
            return SendMessagePollResolution(self.discord_service)
        else:
            raise PururuException(f"Unknown resolution type: {resolution_type}")
