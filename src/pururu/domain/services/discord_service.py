from abc import ABC, abstractmethod

from pururu.domain.entities.poll import PollReference, Poll


class DiscordService(ABC):
    @abstractmethod
    async def fetch_poll(self, poll: PollReference) -> Poll | None:
        """
        Fetch a poll from Discord using its reference.
        :param poll: the poll reference
        :return: a Poll object if found, None otherwise
        """
        pass

    @abstractmethod
    async def send_simple_message(self, channel_id: str, content: str) -> bool:
        """
        Send a simple message to a Discord channel.
        :param channel_id: the ID of the channel where to send the message
        :param content: the content of the message
        :return: bool indicating if the message was sent successfully
        """
        pass
