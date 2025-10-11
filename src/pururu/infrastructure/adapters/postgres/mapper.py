from datetime import datetime

from pururu.domain.entities.player import Player
from pururu.domain.entities.poll import PollReference, PollResolutionType
from pururu.domain.entities.season import Season
from pururu.domain.entities.session import (Session, Status, Type, PlayerSession, Interval, SessionMetadataKey)
from pururu.infrastructure.adapters.postgres.entities import (SessionRecord, PlayerSessionRecord,
                                                              PlayerSessionIntervalRecord, PlayerRecord, SeasonRecord,
                                                              PollRecord, SessionMetadataRecord)


class PostgresMapper:
    # ---------------------------------------
    # Session mappings
    # ---------------------------------------
    @staticmethod
    def map_session_to_record(session: Session) -> SessionRecord:
        session_record = SessionRecord(
            session_id=session.id,
            season_id=session.season_id,
            start_time=session.start_time,
            end_time=session.end_time,
            type=session.type.value,
            status=session.status.value,
            version=session.version,
            last_updated=datetime.now(),
            custom_metadata=[PostgresMapper.map_metadata_to_record(key.value, value, session.id) for (key, value) in
                             session.metadata.items()]
        )
        session_record.players = [PostgresMapper.map_player_session_to_record(ps, session.id) for ps in session.players]
        return session_record

    @staticmethod
    def update_record_from_session(existing_record: SessionRecord, session: Session) -> SessionRecord:
        """Update an existing SessionRecord with all its children from a Session domain object."""
        existing_record.season_id = session.season_id
        existing_record.start_time = session.start_time
        existing_record.end_time = session.end_time
        existing_record.type = session.type.value
        existing_record.status = session.status.value
        existing_record.version = session.version
        existing_record.last_updated = datetime.now()
        existing_record.custom_metadata = [PostgresMapper.map_metadata_to_record(key.value, value, session.id) for
                                           (key, value) in
                                           session.metadata.items()]
        for existing_player_session in existing_record.players:
            player_session = next((ps for ps in session.players if ps.player_id == existing_player_session.player_id),
                                  None)
            if player_session:
                PostgresMapper._update_player_session_record(existing_player_session, player_session)
        return existing_record

    @staticmethod
    def _update_player_session_record(existing_record: PlayerSessionRecord, player_session: PlayerSession):
        """Update an existing PlayerSessionRecord with its intervals."""
        existing_record.attended = player_session.attended
        existing_record.justified_absence = player_session.justified_absence
        existing_record.motive = player_session.motive
        existing_intervals = {interval.join_time: interval for interval in
                              existing_record.intervals}
        # Update existing and add new intervals
        existing_intervals_keys = list(existing_intervals.keys())
        for interval in player_session.intervals:
            if interval.start in existing_intervals_keys:
                existing_intervals[interval.start].leave_time = interval.end
            else:
                new_interval_record = PostgresMapper.map_interval_to_record(
                    interval, existing_record.session_id, existing_record.player_id
                )
                existing_record.intervals.append(new_interval_record)

    @staticmethod
    def map_player_session_to_record(player_session: PlayerSession, session_id: str) -> PlayerSessionRecord:
        player_session_record = PlayerSessionRecord(
            session_id=session_id,
            player_id=player_session.player_id,
            attended=player_session.attended,
            justified_absence=player_session.justified_absence,
            motive=player_session.motive,

        )
        player_session_record.intervals = [
            PostgresMapper.map_interval_to_record(interval, session_id, player_session.player_id)
            for interval in player_session.intervals]
        return player_session_record

    @staticmethod
    def map_interval_to_record(interval: Interval, session_id: str, player_id: str
                               ) -> PlayerSessionIntervalRecord:
        return PlayerSessionIntervalRecord(
            session_id=session_id,
            player_id=player_id,
            join_time=interval.start,
            leave_time=interval.end,
        )

    @staticmethod
    def map_metadata_to_record(key: str, value: str, session_id: str) -> SessionMetadataRecord:
        return SessionMetadataRecord(
            session_id=session_id,
            key=key,
            value=value
        )

    @staticmethod
    def map_record_to_session(record: SessionRecord) -> Session:
        session = Session(
            id=record.session_id,
            season_id=record.season_id,
            start_time=record.start_time,
            end_time=record.end_time,
            type=Type(record.type),
            status=Status(record.status),
            players=[PostgresMapper.map_record_to_player_session(ps) for ps in record.players],
            version=record.version,
            metadata={SessionMetadataKey(md.key): md.value for md in record.custom_metadata}
        )
        return session

    @staticmethod
    def map_record_to_player_session(record: PlayerSessionRecord) -> PlayerSession:
        player_session = PlayerSession(
            player_id=record.player_id,
            attended=record.attended,
            justified_absence=record.justified_absence,
            motive=record.motive,
            intervals=[PostgresMapper.map_record_to_interval(interval) for interval in record.intervals]
        )
        return player_session

    @staticmethod
    def map_record_to_interval(record: PlayerSessionIntervalRecord) -> Interval:
        return Interval(
            start=record.join_time,
            end=record.leave_time
        )

    # ---------------------------------------
    # Player mappings
    # ---------------------------------------

    @staticmethod
    def map_record_to_player(record: PlayerRecord) -> Player:
        return Player(
            id=record.player_id,
            name=record.display_name,
            birthday=record.birthday
        )

    @staticmethod
    def map_player_to_record(player: Player) -> PlayerRecord:
        return PlayerRecord(
            player_id=player.id,
            display_name=player.name,
            birthday=player.birthday
        )

    # ---------------------------------------
    # Season mappings
    # ---------------------------------------
    @staticmethod
    def map_record_to_season(record: SeasonRecord) -> Season:
        return Season(
            id=record.season_id,
            president_id=record.president_id,
            start_date=record.start_date,
            end_date=record.end_date
        )

    @staticmethod
    def map_season_to_record(season: Season) -> SeasonRecord:
        return SeasonRecord(
            season_id=season.id,
            president_id=season.president_id,
            start_date=season.start_date,
            end_date=season.end_date
        )

    # ---------------------------------------
    # Poll mappings
    # ---------------------------------------
    @staticmethod
    def map_record_to_poll(record: PollRecord) -> PollReference:
        from pururu.domain.entities.poll import PollReference
        return PollReference(
            id=record.id,
            channel_id=record.channel_id,
            expires_at=record.expires_at,
            resolution_type=PollResolutionType(record.resolution_type)
        )

    @staticmethod
    def map_poll_to_record(poll: PollReference) -> PollRecord:
        return PollRecord(
            id=poll.id,
            channel_id=poll.channel_id,
            expires_at=poll.expires_at,
            resolution_type=poll.resolution_type.value
        )
