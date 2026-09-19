"""Every handler follows the same three lines: parse -> execute -> present."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from cleanarch.shared.application.actor import Actor
from cleanarch.shared.http.auth import get_actor
from cleanarch.shared.http.schemas import ErrorResponse
from cleanarch.tournaments.application import (
    AdvanceTournament,
    CreateTournament,
    GetTournament,
    ListTournaments,
    StartTournament,
)
from cleanarch.tournaments.domain import TournamentId
from cleanarch.tournaments.http import dependencies as deps
from cleanarch.tournaments.http.schemas import CreateTournamentRequest, TournamentResponse

router = APIRouter(prefix="/tournaments", tags=["tournaments"])

Responses = dict[int | str, dict[str, Any]]
NOT_FOUND: Responses = {status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}}
RULE_VIOLATED: Responses = {status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse}}
AUTH: Responses = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
}

Caller = Annotated[Actor, Depends(get_actor)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TournamentResponse,
    responses=RULE_VIOLATED | AUTH,
    summary="Create a tournament",
    description="The caller becomes the organizer.",
)
async def create(
    body: CreateTournamentRequest,
    actor: Caller,
    use_case: Annotated[CreateTournament, Depends(deps.create_tournament)],
) -> TournamentResponse:
    tournament = await use_case.execute(body.to_command(), actor)
    return TournamentResponse.from_domain(tournament)


@router.get("", response_model=list[TournamentResponse], summary="List tournaments")
async def list_(
    use_case: Annotated[ListTournaments, Depends(deps.list_tournaments)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TournamentResponse]:
    tournaments = await use_case.execute(limit=limit, offset=offset)
    return [TournamentResponse.from_domain(t) for t in tournaments]


@router.get(
    "/{tournament_id}",
    response_model=TournamentResponse,
    responses=NOT_FOUND,
    summary="Get a tournament",
)
async def get(
    tournament_id: str,
    use_case: Annotated[GetTournament, Depends(deps.get_tournament)],
) -> TournamentResponse:
    tournament = await use_case.execute(TournamentId(tournament_id))
    return TournamentResponse.from_domain(tournament)


@router.post(
    "/{tournament_id}/start",
    response_model=TournamentResponse,
    responses=NOT_FOUND | RULE_VIOLATED | AUTH,
    summary="Start a tournament",
    description="Organizer or admin only.",
)
async def start(
    tournament_id: str,
    actor: Caller,
    use_case: Annotated[StartTournament, Depends(deps.start_tournament)],
) -> TournamentResponse:
    tournament = await use_case.execute(TournamentId(tournament_id), actor)
    return TournamentResponse.from_domain(tournament)


@router.post(
    "/{tournament_id}/advance",
    response_model=TournamentResponse,
    responses=NOT_FOUND | RULE_VIOLATED | AUTH,
    summary="Advance to the next round or phase",
    description="Organizer or admin only.",
)
async def advance(
    tournament_id: str,
    actor: Caller,
    use_case: Annotated[AdvanceTournament, Depends(deps.advance_tournament)],
) -> TournamentResponse:
    tournament = await use_case.execute(TournamentId(tournament_id), actor)
    return TournamentResponse.from_domain(tournament)
