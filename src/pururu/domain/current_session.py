from datetime import datetime

from pururu.common import utils, logger
from pururu.config import settings
from pururu.domain.entities import Poll


class CurrentSession:
    def __init__(self):
        self.online_players = set()
        self.players_clock_ins = {}
        self.players_clock_outs = {}
        self.game_id = None
        self.polls = {}
        self.logger = logger.get_logger(__name__)

    def clock_in(self, player: str, time: datetime = None) -> None:
        """
        Clocks in a player
        :param player: member.name
        :param time: time of clock in
        :return: None
        """
        if time is None:
            time = datetime.now()
        time_fmt = utils.format_time(time)
        self.online_players.add(player)
        if player not in self.players_clock_ins:
            self.players_clock_ins[player] = []
            self.players_clock_outs[player] = []
        if len(self.players_clock_ins[player]) == len(self.players_clock_outs[player]):
            self.players_clock_ins[player].append(time_fmt)
        self.logger.debug(f"Player '{player}' clocked in", extra={
            "player": player,
            "time": time_fmt,
            "total_clock_ins": len(self.players_clock_ins[player]),
            "total_clock_outs": len(self.players_clock_outs[player])
        })

    def clock_out(self, player: str, time: datetime = None) -> None:
        """
        Clocks out a player
        :param player: member.name
        :param time: time of clock out
        :return: None
        """
        if time is None:
            time = datetime.now()
        time_fmt = utils.format_time(time)
        if player not in self.online_players:
            self.logger.error(f"Cannot clock out player '{player}' not online",
                              extra={"player": player, "online_players": list(self.online_players)})
            return
        self.online_players.remove(player)
        if player not in self.players_clock_outs:
            self.logger.error(f"Clock-out data missing for player '{player}'", extra={"player": player})
            return
        self.players_clock_outs[player].append(time_fmt)
        self.logger.debug(f"Player '{player}' clocked out", extra={
            "player": player,
            "time": time_fmt,
            "total_clock_ins": len(self.players_clock_ins[player]),
            "total_clock_outs": len(self.players_clock_outs[player])
        })

    def get_player_time(self, player: str) -> int:
        """
        Gets the total playtime of a player in seconds.
        :param player: member.name
        :return: int: total playtime in seconds
        """
        self.logger.debug(f"Getting player '{player}' time", extra={"player": player})
        if player not in self.players_clock_ins:
            return 0
        clock_ins = self.players_clock_ins[player]
        clock_outs = self.players_clock_outs[player]
        total_time = 0
        for i in range(len(clock_ins)):
            clock_in = utils.parse_time(clock_ins[i])
            clock_out = datetime.strptime(clock_outs[i], utils.FORMATTED_TIME_STR) if i < len(
                clock_outs) else datetime.now()
            total_time += (clock_out - clock_in).total_seconds()
        self.logger.debug(f"Total playtime for player '{player}': {total_time}",
                          extra={"player": player, "total_time": total_time})
        return int(total_time)

    def should_start_new_game(self) -> bool:
        """
        Checks if the conditions to start a new game are met
        :return: bool
        """
        return self.game_id is None and len(self.online_players) >= settings.general.min_attendance_members

    def should_end_game(self) -> bool:
        """
        Checks if the conditions to end the current game are met
        :return: bool
        """
        return self.game_id is not None and len(self.online_players) < settings.general.min_attendance_members

    def get_players(self) -> list:
        """
        Returns the list of the current players
        :return: list
        """
        return list(self.online_players)

    def __str__(self):
        return f"Game {self.game_id}, players {self.online_players}, clock_ins {self.players_clock_ins}, " \
               f"clock_outs {self.players_clock_outs}"

    def reset(self):
        """
        Resets the current game to initial state
        :return: None
        """
        self.logger.info(f"CurrentSession state reset, flushed game_id: {self.game_id}", extra={
            "game_id": self.game_id,
            "online_players_count": len(self.online_players)
        })
        self.online_players = set()
        self.players_clock_ins = {}
        self.players_clock_outs = {}
        self.game_id = None

    def adjust_players_clocking_start_time(self, start_time: datetime) -> None:
        """
        Ensures that no player has a clock_in or period before start_time
        :param start_time: Game start time
        :return: None
        """
        for player in self.players_clock_ins:
            player_clock_ins = self.players_clock_ins[player]
            player_clock_outs = self.players_clock_outs[player]
            adjusted_clock_ins = []
            adjusted_clock_outs = []
            for i, clock_in in enumerate(player_clock_ins):
                if len(player_clock_outs) > i:
                    clock_out = player_clock_outs[i]
                    clock_out_time = datetime.strptime(clock_out, utils.FORMATTED_TIME_STR)
                    if clock_out_time <= start_time:
                        self.logger.debug(
                            f"Discarding session for player '{player}' due to being earlier than start_time", extra={
                                "player": player,
                                "clock_in": clock_in,
                                "clock_out": clock_out,
                                "start_time": utils.format_time(start_time)
                            })
                        continue
                    else:
                        adjusted_clock_outs.append(clock_out)
                clock_in_time = datetime.strptime(clock_in, utils.FORMATTED_TIME_STR)
                clock_in = clock_in if clock_in_time > start_time else start_time.strftime(utils.FORMATTED_TIME_STR)
                adjusted_clock_ins.append(clock_in)

            self.players_clock_ins[player] = adjusted_clock_ins
            self.players_clock_outs[player] = adjusted_clock_outs

    def adjust_players_clocking_end_time(self, end_time: datetime) -> None:
        """
        Ensures that no player has a clock_out or period after end_time
        :param end_time: Game end time
        :return: None
        """
        for player in self.players_clock_outs:
            player_clock_ins = self.players_clock_ins[player]
            player_clock_outs = self.players_clock_outs[player]
            adjusted_clock_ins = []
            adjusted_clock_outs = []
            for i, clock_in in enumerate(player_clock_ins):
                clock_out = player_clock_outs[i] if len(player_clock_outs) > i else end_time.strftime(
                    utils.FORMATTED_TIME_STR)
                clock_in_time = datetime.strptime(clock_in, utils.FORMATTED_TIME_STR)
                if clock_in_time >= end_time:
                    self.logger.debug(f"Discarding player '{player}' session due to being posterior to end_time",
                                      extra={
                                          "player": player,
                                          "clock_in": clock_in,
                                          "clock_out": clock_out,
                                          "end_time": utils.format_time(end_time)
                                      })
                    continue
                else:
                    adjusted_clock_ins.append(clock_in)
                clock_out_time = datetime.strptime(clock_out, utils.FORMATTED_TIME_STR)
                clock_out = clock_out if clock_out_time <= end_time else end_time.strftime(utils.FORMATTED_TIME_STR)
                adjusted_clock_outs.append(clock_out)

            self.players_clock_ins[player] = adjusted_clock_ins
            self.players_clock_outs[player] = adjusted_clock_outs

    def add_new_poll(self, poll: Poll) -> None:
        """
        Unpacks the poll data and stores it in the polls attribute
        :param poll: the poll object
        :return: None
        """
        self.logger.debug(f"Adding new poll with id '{poll.message_id}' and channel: '{poll.channel_id}'",
                          extra={"poll_id": poll.message_id})
        self.polls[poll.message_id] = {'channel_id': poll.channel_id, "expires_at": poll.expires_at,
                                       "resolution": poll.resolution_type}

    def remove_poll(self, poll_id: int) -> None:
        """
        Removes a poll from the polls attribute
        :param poll_id: the message_id of the poll
        :return: None
        """
        self.logger.debug(f"Removing poll with id '{poll_id}'", extra={"poll_id": poll_id})
        self.polls.pop(poll_id, None)

    def get_expired_polls(self) -> list[Poll]:
        """
        Returns the list of expired polls
        :return: list of Poll objects
        """
        expired_polls = []
        for poll_id, poll_data in self.polls.items():
            expiration_time = poll_data["expires_at"]
            if expiration_time <= datetime.now(expiration_time.tzinfo):
                poll = Poll("", poll_data['channel_id'], [], 0)
                poll.message_id = poll_id
                poll.resolution_type = poll_data['resolution']
                expired_polls.append(poll)
        self.logger.debug(f"Expired polls retrieved; total: {len(expired_polls)}", extra={
            "count": len(expired_polls),
            "poll_ids": [poll.message_id for poll in expired_polls]
        })
        return expired_polls
