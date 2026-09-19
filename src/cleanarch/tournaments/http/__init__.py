"""HTTP adapter for tournaments: FastAPI router, schemas and dependency declarations."""

from cleanarch.tournaments.http.dependencies import get_tournament_repository
from cleanarch.tournaments.http.router import router

__all__ = ["get_tournament_repository", "router"]
