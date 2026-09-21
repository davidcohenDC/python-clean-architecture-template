from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from cleanarch.shared.application.errors import ConflictError
from cleanarch.tournaments.domain import Tournament, TournamentId
from cleanarch.tournaments.infrastructure.sqlalchemy.mapping import (
    to_domain,
    to_model,
    update_model,
)
from cleanarch.tournaments.infrastructure.sqlalchemy.models import TournamentModel


class SqlAlchemyTournamentRepository:
    """``TournamentRepository`` backed by SQLAlchemy.

    The repository never commits: the session it receives is committed (or
    rolled back) by whoever opened it - the HTTP layer, one transaction per
    request. See ``cleanarch.shared.infrastructure.database.transaction``.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, tournament: Tournament) -> None:
        self._session.add(to_model(tournament))
        await self._session.flush()

    async def get(self, tournament_id: TournamentId) -> Tournament | None:
        model = await self._session.get(TournamentModel, tournament_id)
        return None if model is None else to_domain(model)

    async def save(self, tournament: Tournament) -> Tournament:
        model = await self._session.get(TournamentModel, tournament.id)
        if model is None:
            raise LookupError(f"Tournament {tournament.id} does not exist")
        if model.version != tournament.version:
            # The aggregate was loaded from an older version than the row in this session.
            raise ConflictError(f"Tournament '{tournament.id}' was modified concurrently.")
        update_model(model, tournament)
        try:
            await self._session.flush()  # UPDATE ... WHERE version = ?; bumps version
        except StaleDataError as exc:
            # Another session committed a newer version between our load and our write.
            raise ConflictError(f"Tournament '{tournament.id}' was modified concurrently.") from exc
        return to_domain(model)

    async def list(self, *, limit: int, offset: int) -> Sequence[Tournament]:
        statement = (
            select(TournamentModel)
            .order_by(TournamentModel.created_at, TournamentModel.id)
            .limit(limit)
            .offset(offset)
        )
        models = (await self._session.scalars(statement)).all()
        return [to_domain(m) for m in models]
