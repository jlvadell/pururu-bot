from datetime import datetime

import pururu.config as config
from pururu.application.events.entities import (EndGameIntentEvent, GameStartedEvent, PururuEvent, GameEndedEvent,
                                                MemberJoinedChannelEvent, MemberLeftChannelEvent, NewGameIntentEvent,
                                                CheckExpiredPollsEvent, FinalizePollEvent)
from pururu.common import logger
from pururu.common.exceptions import (CannotStartNewGame, CannotEndGame, GameEndedWithoutPrecondition,
                                      EventTooEarlyException)
from pururu.domain.entities import MemberStats
from pururu.domain.services.event_service import EventService
from pururu.domain.services.pururu_service import PururuService


class PururuHandler:
    def __init__(self, domain_service: PururuService, event_service: EventService):
        self.domain_service = domain_service
        self.event_service = event_service
        self.logger = logger.get_logger(__name__)

    # ---------------------------
    # DISCORD EVENT HANDLERS
    # ---------------------------

    def handle_voice_state_update_dc_event(self, member: str, before_channel: str | None,
                                           after_channel: str | None) -> None:
        """
        Handles the Discord voice state update event
        :param member: member name
        :param before_channel: before_state channel name
        :param after_channel: after_state channel name
        :return: None
        """
        self.logger.info(f"Member voice state changed, player: {member}, from {before_channel} to {after_channel}",
                         extra={"member": member, "before_channel": before_channel, "after_channel": after_channel})
        if member not in config.PLAYERS:
            self.logger.warning(f"Non-tracked player ignored: {member}", extra={"member": member})
            return
        event = None
        if before_channel is None:
            event = MemberJoinedChannelEvent(member, after_channel, datetime.now())
        elif after_channel is None:
            event = MemberLeftChannelEvent(member, before_channel, datetime.now())
        if event:
            self.__emit_event(event)

    def handle_on_ready_dc_event(self) -> None:
        """
        Handles the Discord on_ready event
        :return: None
        """
        self.logger.info("Application Started and connected to Discord")

    # ---------------------------
    # DISCORD COMMAND HANDLERS
    # ---------------------------

    def retrieve_player_stats(self, player: str) -> MemberStats:
        """
        Retrieves the attendance stats of a player
        :param player: player name
        :return: MemberStats
        """
        self.logger.info(f"Retrieving player stats for player: {player}", extra={"player": player})
        return self.domain_service.calculate_player_stats(player)

    # ---------------------------
    # PURURU EVENT HANDLERS - GAME EVENTS
    # ---------------------------

    def handle_member_joined_channel_event(self, event: MemberJoinedChannelEvent) -> None:
        """
        Handles the MemberJoinedChannelEvent; emits NewGameIntentEvent if conditions are met
        :param event: MemberJoinedChannelEvent
        :return: None
        """
        self.logger.info(f"Player '{event.member}' joined channel '{event.channel}' at {event.joined_at}",
                         extra={"member": event.member, "channel": event.channel, "time": event.joined_at})
        self.domain_service.add_player(event.member, event.joined_at)
        if self.domain_service.should_start_new_game_session():
            session_info = self.domain_service.get_session_info()
            self.logger.debug(f"Emitting new game intent, players: {len(session_info.players)}",
                              extra={"players": session_info.players, "player_count": len(session_info.players)})
            event = NewGameIntentEvent(session_info.players, datetime.now())
            self.__emit_event(event)

    def handle_member_left_channel_event(self, event: MemberLeftChannelEvent) -> None:
        """
        Handles the MemberLeftChannelEvent; emits EndGameIntentEvent if conditions are met
        :param event: MemberLeftChannelEvent
        :return: None
        """
        self.logger.info(f"Player '{event.member}' left channel '{event.channel}' at {event.left_at}",
                         extra={"member": event.member, "channel": event.channel, "time": event.left_at})
        self.domain_service.remove_player(event.member, event.left_at)
        if self.domain_service.should_end_game_session():
            session_info = self.domain_service.get_session_info()
            self.logger.debug(
                f"Emitting end game intent, for game_id {session_info.game_id}, players: {len(session_info.players)}",
                extra={"game_id": session_info.game_id, "players": session_info.players})
            event = EndGameIntentEvent(session_info.game_id, session_info.players, datetime.now())
            self.__emit_event(event)

    def handle_new_game_intent_event(self, event: NewGameIntentEvent) -> None:
        """
        Handles the NewGameIntentEvent
        :param event: NewGameIntentEvent
        :return: None
        """
        self.logger.info(f"Handling new game intent, players: {event.players}, start time: {event.start_time}",
                         extra={"players": event.players, "player_count": {len(event.players)},
                                "start_time": event.start_time})
        if event.get_age() < config.ATTENDANCE_CHECK_DELAY:
            self.logger.debug("Ignoring new game intent (Too Early)", extra={"event": event})
            raise EventTooEarlyException(f"New game intent is too early: {event}")
        try:
            session = self.domain_service.start_new_game(event.start_time)
            event = GameStartedEvent(session.game_id, session.players)
            self.__emit_event(event)
        except CannotStartNewGame as e:
            self.logger.warning(f"Cannot start new game, {str(e)}", extra={"reason": str(e)})

    def handle_end_game_intent_event(self, event: EndGameIntentEvent) -> None:
        """
        Handles the EndGameIntentEvent
        :param event: EndGameIntentEvent
        :return: None
        """
        self.logger.info(
            f"Handling end game intent for game_id {event.game_id}, players: {event.players}, end time: {event.end_time}",
            extra={
                "game_id": event.game_id, "players": event.players, "end_time": event.end_time
            })
        if event.get_age() < config.ATTENDANCE_CHECK_DELAY:
            self.logger.debug("Ignoring end game intent (Too Early)", extra={"event": event})
            raise EventTooEarlyException(f"End game intent is too early: {event}")
        try:
            attendance = self.domain_service.end_game(event.end_time)
            event = GameEndedEvent.from_attendance(attendance)
            self.__emit_event(event)
        except CannotEndGame as e:
            self.logger.debug(f"Cannot end game, {str(e)}", extra={"reason": str(e)})
        except GameEndedWithoutPrecondition as e:
            self.logger.warning(f"Game ended without precondition, {str(e)}", extra={"reason": str(e)})

    def handle_game_started_event(self, event: GameStartedEvent) -> None:
        """
        Handles the GameStartedEvent
        :param event: GameStartedEvent
        :return: None
        """
        self.logger.info(f"Game started with id {event.game_id} and players: {event.players}",
                         extra={"game_id": event.game_id, "players": event.players, "player_count": len(event.players)})

    def handle_game_ended_event(self, event: GameEndedEvent) -> None:
        """
        Handles the GameEndedEvent
        :param event: GameEndedEvent
        :return: None
        """
        attendance = event.to_attendance()
        self.logger.info(
            f"Game with id {attendance.game_id} ended, absences: {[m.member for m in attendance.members if not m.attendance]}",
            extra={
                "game_id": attendance.game_id,
                "players": [m.member for m in attendance.members],
                "absences": [m.member for m in attendance.members if not m.attendance]
            })

    # ---------------------------
    # PURURU EVENT HANDLERS - POLL EVENTS
    # ---------------------------

    async def handle_check_expired_polls_event(self, event: CheckExpiredPollsEvent) -> None:
        """
        Handles the CheckExpiredPollsEvent
        :param event: PururuEvent
        :return: None
        """
        expired_polls = await self.domain_service.get_expired_polls()
        for poll in expired_polls:
            self.__emit_event(FinalizePollEvent.from_poll(poll))
        self.logger.info(f"Consumed CheckExpiredPollsEvent, total polls {len(expired_polls)}", extra={"expired_count": len(expired_polls)})

    async def handle_finalize_poll_event(self, event: FinalizePollEvent) -> None:
        """
        Handles the FinalizePollEvent
        :param event: PururuEvent
        :return: None
        """
        poll = event.to_poll()
        await self.domain_service.finalize_poll(poll)
        self.logger.debug(f"Poll with id {poll.message_id} finalized, winner/s: {poll.get_winners()}", extra={
            "poll_id": poll.message_id,
            "winners": poll.get_winners()
        })

    # ---------------------------
    # TIMED JOBS
    # ---------------------------

    def trigger_check_expired_polls_flow(self) -> None:
        """
        Triggers the flow to check for expired polls
        :return: None
        """
        self.logger.debug("Emitting CheckExpiredPollsEvent")
        self.__emit_event(CheckExpiredPollsEvent())

    # ---------------------------
    # PRIVATE METHODS
    # ---------------------------
    def __emit_event(self, event: PururuEvent) -> None:
        bot_event = event.as_bot_event()
        self.event_service.publish(bot_event)
        self.domain_service.register_bot_event(bot_event)
