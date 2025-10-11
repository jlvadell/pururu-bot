from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, Date, Boolean, ForeignKeyConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"
PLAYER_TABLE_PK = "player.player_id"
SESSION_TABLE_PK = "session.session_id"
ON_DELETE_CASCADE = "CASCADE"


class Base(DeclarativeBase):
    pass


class SeasonRecord(Base):
    __tablename__ = "season"

    season_id: Mapped[str] = mapped_column(String, primary_key=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    president_id: Mapped[str] = mapped_column(String, ForeignKey(PLAYER_TABLE_PK), nullable=False)

    sessions: Mapped[list["SessionRecord"]] = relationship("SessionRecord", back_populates="season",
                                                           cascade=CASCADE_ALL_DELETE_ORPHAN)


class SessionRecord(Base):
    __tablename__ = "session"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    season_id: Mapped[str] = mapped_column(String, ForeignKey("season.season_id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    season: Mapped["SeasonRecord"] = relationship("SeasonRecord", back_populates="sessions")
    players: Mapped[list["PlayerSessionRecord"]] = relationship("PlayerSessionRecord", back_populates="session",
                                                                cascade=CASCADE_ALL_DELETE_ORPHAN)
    connections: Mapped[list["PlayerSessionIntervalRecord"]] = relationship("PlayerSessionIntervalRecord",
                                                                            back_populates="session",
                                                                            cascade=CASCADE_ALL_DELETE_ORPHAN)
    custom_metadata: Mapped[list["SessionMetadataRecord"]] = relationship("SessionMetadataRecord",
                                                                          back_populates="session",
                                                                          cascade=CASCADE_ALL_DELETE_ORPHAN)


class PlayerRecord(Base):
    __tablename__ = "player"

    player_id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)

    sessions: Mapped[list["PlayerSessionRecord"]] = relationship("PlayerSessionRecord", back_populates="player",
                                                                 cascade=CASCADE_ALL_DELETE_ORPHAN)
    connections: Mapped[list["PlayerSessionIntervalRecord"]] = relationship("PlayerSessionIntervalRecord",
                                                                            back_populates="player",
                                                                            cascade=CASCADE_ALL_DELETE_ORPHAN)


class PlayerSessionRecord(Base):
    __tablename__ = "player_session"

    session_id: Mapped[str] = mapped_column(String, ForeignKey(SESSION_TABLE_PK, ondelete=ON_DELETE_CASCADE),
                                            primary_key=True)
    player_id: Mapped[str] = mapped_column(String, ForeignKey(PLAYER_TABLE_PK, ondelete=ON_DELETE_CASCADE),
                                           primary_key=True)
    attended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    justified_absence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motive: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    intervals: Mapped[list["PlayerSessionIntervalRecord"]] = relationship(
        "PlayerSessionIntervalRecord",
        back_populates="playerSession",
        cascade=CASCADE_ALL_DELETE_ORPHAN,
        foreign_keys="[PlayerSessionIntervalRecord.session_id, PlayerSessionIntervalRecord.player_id]",
        overlaps="connections"
    )
    session: Mapped["SessionRecord"] = relationship("SessionRecord", back_populates="players", cascade="all")
    player: Mapped["PlayerRecord"] = relationship("PlayerRecord", back_populates="sessions")


class PlayerSessionIntervalRecord(Base):
    __tablename__ = "player_session_interval"

    __table_args__ = (
        ForeignKeyConstraint(
            ['session_id', 'player_id'],
            ['player_session.session_id', 'player_session.player_id'],
            ondelete=ON_DELETE_CASCADE
        ),
    )

    session_id: Mapped[str] = mapped_column(String, ForeignKey(SESSION_TABLE_PK, ondelete=ON_DELETE_CASCADE),
                                            primary_key=True)
    player_id: Mapped[str] = mapped_column(String, ForeignKey(PLAYER_TABLE_PK, ondelete=ON_DELETE_CASCADE),
                                           primary_key=True)
    join_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, primary_key=True)
    leave_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    playerSession: Mapped["PlayerSessionRecord"] = relationship(
        "PlayerSessionRecord",
        back_populates="intervals",
        foreign_keys="[PlayerSessionIntervalRecord.session_id, PlayerSessionIntervalRecord.player_id]",
        overlaps="connections,session,player"
    )
    session: Mapped["SessionRecord"] = relationship(
        "SessionRecord",
        back_populates="connections",
        foreign_keys=[session_id],
        overlaps="intervals,playerSession,connections"
    )
    player: Mapped["PlayerRecord"] = relationship(
        "PlayerRecord",
        back_populates="connections",
        foreign_keys=[player_id],
        overlaps="intervals,playerSession,connections"
    )


class PollRecord(Base):
    __tablename__ = "poll"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    channel_id: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolution_type: Mapped[str] = mapped_column(String, nullable=False)


class SessionMetadataRecord(Base):
    __tablename__ = "session_metadata"

    session_id: Mapped[str] = mapped_column(String, ForeignKey(SESSION_TABLE_PK, ondelete=ON_DELETE_CASCADE),
                                            primary_key=True)
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)

    session: Mapped["SessionRecord"] = relationship("SessionRecord", back_populates="custom_metadata", cascade="all")
