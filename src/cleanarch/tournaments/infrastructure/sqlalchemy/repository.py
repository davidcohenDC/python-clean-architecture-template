from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def save(self, tournament: Tournament) -> None:
        model = await self._session.get(TournamentModel, tournament.id)
        if model is None:  # pragma: no cover - defensive; use cases load before saving
            raise LookupError(f"Tournament {tournament.id} does not exist")
        update_model(model, tournament)
        await self._session.flush()

    async def list(self, *, limit: int, offset: int) -> Sequence[Tournament]:
        statement = select(TournamentModel).order_by(TournamentModel.id).limit(limit).offset(offset)
        models = (await self._session.scalars(statement)).all()
        return [to_domain(m) for m in models]
