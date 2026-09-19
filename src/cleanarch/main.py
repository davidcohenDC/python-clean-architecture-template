"""ASGI entrypoint: ``uvicorn cleanarch.main:app``."""

from cleanarch.bootstrap import create_app

app = create_app()
