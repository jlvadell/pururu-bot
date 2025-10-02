from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, Date, Boolean, ForeignKeyConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"
PLAYER_TABLE_PK = "player.player_id"
SESSION_TABLE_PK = "session.session_id"


class Base(DeclarativeBase):
    pass


class SeasonRecord(Base):
    __tablename__ = "season"

    season_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    president_id: Mapped[str] = mapped_column(String(30), ForeignKey(PLAYER_TABLE_PK), nullable=False)

    sessions: Mapped[list["SessionRecord"]] = relationship("SessionRecord", back_populates="season",
                                                           cascade=CASCADE_ALL_DELETE_ORPHAN)


class SessionRecord(Base):
    __tablename__ = "session"

    session_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    season_id: Mapped[str] = mapped_column(String(30), ForeignKey("season.season_id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    season: Mapped["SeasonRecord"] = relationship("SeasonRecord", back_populates="sessions")
    players: Mapped[list["PlayerSessionRecord"]] = relationship("PlayerSessionRecord", back_populates="session",
                                                                cascade=CASCADE_ALL_DELETE_ORPHAN)
    connections: Mapped[list["PlayerSessionIntervalRecord"]] = relationship("PlayerSessionIntervalRecord",
                                                                            back_populates="session",
                                                                            cascade=CASCADE_ALL_DELETE_ORPHAN)


class PlayerRecord(Base):
    __tablename__ = "player"

    player_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)

    sessions: Mapped[list["PlayerSessionRecord"]] = relationship("PlayerSessionRecord", back_populates="player",
                                                                 cascade=CASCADE_ALL_DELETE_ORPHAN)
    connections: Mapped[list["PlayerSessionIntervalRecord"]] = relationship("PlayerSessionIntervalRecord",
                                                                            back_populates="player",
                                                                            cascade=CASCADE_ALL_DELETE_ORPHAN)


class PlayerSessionRecord(Base):
    __tablename__ = "player_session"

    session_id: Mapped[str] = mapped_column(String(30), ForeignKey(SESSION_TABLE_PK), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(30), ForeignKey(PLAYER_TABLE_PK), primary_key=True)
    justified_absence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motive: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

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
            ["session_id", "player_id"],
            ["player_session.session_id", "player_session.player_id"],
            ondelete="CASCADE"
        ),
    )

    session_id: Mapped[str] = mapped_column(String(30), ForeignKey(SESSION_TABLE_PK), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(30), ForeignKey(PLAYER_TABLE_PK), primary_key=True)
    join_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, primary_key=True)
    leave_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    playerSession: Mapped["PlayerSessionRecord"] = relationship(
        "PlayerSessionRecord",
        back_populates="intervals",
        cascade="all",
        overlaps="connections"
    )
    session: Mapped["SessionRecord"] = relationship(
        "SessionRecord",
        back_populates="connections",
        cascade="all",
        overlaps="intervals,playerSession"
    )
    player: Mapped["PlayerRecord"] = relationship(
        "PlayerRecord",
        back_populates="connections",
        overlaps="intervals,playerSession"
    )


class PollRecord(Base):
    __tablename__ = "poll"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(30), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolution_type: Mapped[str] = mapped_column(String(30), nullable=False)
