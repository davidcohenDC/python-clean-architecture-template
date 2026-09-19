"""Request/response models and their translation to/from the domain.

Pydantic validates *shape* (types, required fields, discriminators). Business
rules (name length, power-of-two cuts, first phase without cut...) stay in the
domain, which is why a bad payload can produce either a 422 from Pydantic or
a 422 from ``DomainError`` - both with a clear message.
"""

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import Field

from cleanarch.shared.http.schemas import Schema
from cleanarch.tournaments.application import CreateTournamentCommand
from cleanarch.tournaments.domain import (
    BracketPhase,
    Elimination,
    NoCut,
    PairingSystem,
    Phase,
    Phases,
    RoundPhase,
    TopCut,
    Tournament,
    TournamentStatus,
)

# -- phases ---------------------------------------------------------------------


class RoundPhaseSchema(Schema):
    kind: Literal["round"] = "round"
    rounds: int = Field(examples=[3])
    pairing: PairingSystem = PairingSystem.SWISS


class BracketPhaseSchema(Schema):
    kind: Literal["bracket"] = "bracket"
    elimination: Elimination = Elimination.SINGLE


class TopCutSchema(Schema):
    players: int = Field(examples=[8])


class PhaseSchema(Schema):
    config: Annotated[RoundPhaseSchema | BracketPhaseSchema, Field(discriminator="kind")]
    cut: TopCutSchema | None = Field(default=None, description="Required from the second phase on")

    def to_domain(self) -> Phase:
        cut = NoCut() if self.cut is None else TopCut(self.cut.players)
        match self.config:
            case RoundPhaseSchema(rounds=rounds, pairing=pairing):
                return Phase(RoundPhase(rounds=rounds, pairing=pairing), cut)
            case BracketPhaseSchema(elimination=elimination):
                return Phase(BracketPhase(elimination=elimination), cut)

    @classmethod
    def from_domain(cls, phase: Phase) -> Self:
        cut = None if isinstance(phase.cut, NoCut) else TopCutSchema(players=phase.cut.players)
        match phase.config:
            case RoundPhase(rounds=rounds, pairing=pairing):
                return cls(config=RoundPhaseSchema(rounds=rounds, pairing=pairing), cut=cut)
            case BracketPhase(elimination=elimination):
                return cls(config=BracketPhaseSchema(elimination=elimination), cut=cut)


# -- requests -------------------------------------------------------------------


class CreateTournamentRequest(Schema):
    name: str = Field(examples=["Spring Cup"])
    phases: list[PhaseSchema]

    def to_command(self) -> CreateTournamentCommand:
        return CreateTournamentCommand(
            name=self.name,
            phases=Phases.of(*(p.to_domain() for p in self.phases)),
        )


# -- responses ------------------------------------------------------------------


class ProgressSchema(Schema):
    status: TournamentStatus
    phase_index: int | None
    round_index: int | None


class TournamentResponse(Schema):
    id: str
    name: str
    phases: list[PhaseSchema]
    progress: ProgressSchema
    created_at: datetime

    @classmethod
    def from_domain(cls, tournament: Tournament) -> Self:
        return cls(
            id=tournament.id,
            name=tournament.name,
            phases=[PhaseSchema.from_domain(p) for p in tournament.phases],
            progress=ProgressSchema.model_validate(tournament.progress),
            created_at=tournament.created_at,
        )
