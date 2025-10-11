from abc import ABC, abstractmethod

from pururu.domain.entities.session import Session, Type, Status


class SessionRepository(ABC):
    @abstractmethod
    def save(self, session: Session) -> Session:
        """
        Saves a session to the repository
        :param session: the session to save
        :return: the saved session
        """
        pass

    @abstractmethod
    def update(self, session: Session) -> Session:
        """
        Updates a session in the repository
        :param session: the session to update
        :return: the updated session
        """
        pass

    @abstractmethod
    def find_by_id(self, session_id: str) -> Session | None:
        """
        Gets a session by id
        :param session_id: the id of the session
        :return: the session if found, None otherwise
        """
        pass

    @abstractmethod
    def find_active_session(self) -> Session | None:
        """
        Gets the currently active session (status != COMPLETED and != DISCARDED)
        :return: the active session if found, None otherwise
        """
        pass

    def find_latest_by_type_and_status(self, session_type: Type, session_status: Status) -> Session | None:
        """
        Gets the latest session of a given type
        :param session_type: the type of the session
        :param session_status: the status of the session
        :return: the latest session of the given type if found, None otherwise
        """
        pass
