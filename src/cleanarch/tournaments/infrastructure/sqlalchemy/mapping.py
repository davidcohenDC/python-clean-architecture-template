"""Domain <-> row translation. The only place that knows both shapes."""

from datetime import UTC, datetime
from typing import Any

from cleanarch.tournaments.domain import (
    BracketPhase,
    Elimination,
    NoCut,
    PairingSystem,
    Phase,
    Phases,
    Progress,
    RoundPhase,
    TopCut,
    Tournament,
    TournamentId,
    TournamentStatus,
)
from cleanarch.tournaments.infrastructure.sqlalchemy.models import TournamentModel


def phase_to_json(phase: Phase) -> dict[str, Any]:
    cut = None if isinstance(phase.cut, NoCut) else {"players": phase.cut.players}
    match phase.config:
        case RoundPhase(rounds=rounds, pairing=pairing):
            return {"kind": "round", "rounds": rounds, "pairing": pairing.value, "cut": cut}
        case BracketPhase(elimination=elimination):
            return {"kind": "bracket", "elimination": elimination.value, "cut": cut}


def phase_from_json(data: dict[str, Any]) -> Phase:
    cut = NoCut() if data.get("cut") is None else TopCut(players=data["cut"]["players"])
    if data["kind"] == "round":
        return Phase(RoundPhase(rounds=data["rounds"], pairing=PairingSystem(data["pairing"])), cut)
    return Phase(BracketPhase(elimination=Elimination(data["elimination"])), cut)


def to_model(tournament: Tournament) -> TournamentModel:
    return TournamentModel(
        id=tournament.id,
        name=tournament.name,
        phases=[phase_to_json(p) for p in tournament.phases],
        status=tournament.progress.status.value,
        phase_index=tournament.progress.phase_index,
        round_index=tournament.progress.round_index,
        organizer_id=tournament.organizer_id,
        created_at=tournament.created_at,
        version=0,
    )


def update_model(model: TournamentModel, tournament: Tournament) -> None:
    model.name = tournament.name
    model.phases = [phase_to_json(p) for p in tournament.phases]
    model.status = tournament.progress.status.value
    model.phase_index = tournament.progress.phase_index
    model.round_index = tournament.progress.round_index


def _aware(value: datetime) -> datetime:
    """SQLite drops the timezone; the domain always works in aware UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def to_domain(model: TournamentModel) -> Tournament:
    return Tournament(
        id=TournamentId(model.id),
        name=model.name,
        phases=Phases.of(*(phase_from_json(p) for p in model.phases)),
        organizer_id=model.organizer_id,
        created_at=_aware(model.created_at),
        version=model.version,
        progress=Progress(
            status=TournamentStatus(model.status),
            phase_index=model.phase_index,
            round_index=model.round_index,
        ),
    )
