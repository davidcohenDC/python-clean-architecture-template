"""``python -m cleanarch tournaments <command>``.

``register`` declares the sub-commands on an ``argparse`` parser; ``run``
executes one of them against the ports it is given. ``bootstrap/cli.py``
provides the ports (real database, real clock) and the transaction.
"""

import argparse
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from cleanarch.shared.application.actor import Actor
from cleanarch.shared.application.ports import Clock, EventPublisher
from cleanarch.tournaments.application import (
    AdvanceTournament,
    CreateTournament,
    CreateTournamentCommand,
    GetTournament,
    ListTournaments,
    StartTournament,
    TournamentRepository,
)
from cleanarch.tournaments.domain import (
    BracketPhase,
    Phase,
    Phases,
    RoundPhase,
    TopCut,
    Tournament,
    TournamentId,
)


@dataclass(frozen=True, slots=True)
class Ports:
    repository: TournamentRepository
    events: EventPublisher
    clock: Clock
    actor: Actor


Printer = Callable[[str], None]
Handler = Callable[[argparse.Namespace, Ports, Printer], Coroutine[Any, Any, None]]


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser("tournaments", help="manage tournaments")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="create a tournament")
    create.add_argument("name")
    create.add_argument("--rounds", type=int, default=3, help="Swiss rounds in phase 1")
    create.add_argument("--top", type=int, default=None, help="add a top-N bracket phase")
    create.set_defaults(handler=_create)

    commands.add_parser("list", help="list tournaments").set_defaults(handler=_list)
    for name, handler in (("get", _get), ("start", _start), ("advance", _advance)):
        sub = commands.add_parser(name, help=f"{name} a tournament")
        sub.add_argument("id")
        sub.set_defaults(handler=handler)


async def run(args: argparse.Namespace, ports: Ports, out: Printer = print) -> None:
    handler: Handler = args.handler
    await handler(args, ports, out)


# -- commands: parse -> execute -> present, exactly like the HTTP router -------------


async def _create(args: argparse.Namespace, ports: Ports, out: Printer) -> None:
    phases = [Phase(RoundPhase(rounds=args.rounds))]
    if args.top:
        phases.append(Phase(BracketPhase(), cut=TopCut(players=args.top)))
    command = CreateTournamentCommand(name=args.name, phases=Phases.of(*phases))
    tournament = await CreateTournament(ports.repository, ports.events, ports.clock).execute(
        command, ports.actor
    )
    out(_line(tournament))


async def _list(args: argparse.Namespace, ports: Ports, out: Printer) -> None:
    for tournament in await ListTournaments(ports.repository).execute(limit=100):
        out(_line(tournament))


async def _get(args: argparse.Namespace, ports: Ports, out: Printer) -> None:
    out(_line(await GetTournament(ports.repository).execute(TournamentId(args.id))))


async def _start(args: argparse.Namespace, ports: Ports, out: Printer) -> None:
    use_case = StartTournament(ports.repository, ports.events)
    out(_line(await use_case.execute(TournamentId(args.id), ports.actor)))


async def _advance(args: argparse.Namespace, ports: Ports, out: Printer) -> None:
    use_case = AdvanceTournament(ports.repository, ports.events)
    out(_line(await use_case.execute(TournamentId(args.id), ports.actor)))


def _line(t: Tournament) -> str:
    progress = t.progress
    where = (
        f"phase {progress.phase_index}"
        + (f" round {progress.round_index}" if progress.round_index is not None else "")
        if progress.phase_index is not None
        else ""
    )
    return f"{t.id}  {t.name!r}  {t.status.value} {where}".rstrip()
