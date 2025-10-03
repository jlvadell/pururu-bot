from pururu.common import logger
from pururu.domain.entities.poll import Poll, PollReference
from pururu.domain.services.discord_service import DiscordService
from pururu.domain.services.poll_system.poll_resolution_factory import PollResolutionFactory
from pururu.domain.repositories.poll_repository import PollRepository as PollRepository

class PollSystemService:
    def __init__(self, poll_repository: PollRepository, discord_service: DiscordService, poll_resolution_factory: PollResolutionFactory):
        self.poll_repository = poll_repository
        self.discord_service = discord_service
        self.poll_resolution_factory = poll_resolution_factory
        self.logger = logger.get_logger(__name__)

    def get_expired_polls(self) -> list[PollReference]:
        """
        Checks if any polls have expired and ends them
        :return: list of expired polls
        """
        polls: list[PollReference] = self.poll_repository.find_all_expired()
        self.logger.debug(f"Found {len(polls)} expired polls", extra={"expired_count": len(polls)})
        return polls

    async def finalize_poll(self, poll_id: str) -> None:
        """
        Handles the poll resolution
        :param poll_id: the id of the poll to finalize
        :return: None
        """
        poll: PollReference | None = self.poll_repository.find_by_id(poll_id)
        if not poll:
            self.logger.error(f"Poll with id '{poll_id}' not found; ignoring", extra={"poll_id": poll_id})
            return
        expired_poll: Poll | None = await self.discord_service.fetch_poll(poll)
        if not expired_poll:
            self.logger.error(f"Poll with id '{poll_id}' could not be fetched from Discord; ignoring", extra={"poll_id": poll_id})
            self.poll_repository.delete(poll.id)
            return
        strategy = self.poll_resolution_factory.get_strategy(poll.resolution_type)
        await strategy.resolve(expired_poll)
        self.poll_repository.delete(poll.id)
        self.logger.debug(f"Poll with id '{poll.id}' has been resolved", extra={"poll_id": poll.id})