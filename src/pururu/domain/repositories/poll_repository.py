from abc import ABC

from pururu.domain.entities.poll import PollReference


class PollRepository(ABC):
    def save(self, poll: PollReference) -> PollReference:
        """
        Saves a poll to the repository.
        :param poll: The poll to save.
        :return: The saved poll with any updates (e.g., assigned ID).
        """
        pass

    def delete(self, poll_id: str) -> bool:
        """
        Deletes a poll from the repository by its ID.
        :param poll_id: The ID of the poll to delete.
        :return: True if the poll was deleted, False if it was not found.
        """
        pass

    def find_by_id(self, poll_id: str) -> PollReference | None:
        """
        Finds a poll by its ID.
        :param poll_id: The ID of the poll to find.
        :return: The found poll or None if not found.
        """
        pass

    def find_all_expired(self) -> list[PollReference]:
        """
        Finds all expired polls.
        :return: A list of expired polls.
        """
        pass
