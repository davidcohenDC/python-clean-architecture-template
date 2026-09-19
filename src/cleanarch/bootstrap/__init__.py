"""Composition root: the only place that knows every concrete class.

``settings``  - configuration from environment variables
``app``       - builds the FastAPI application and wires ports to adapters
"""

from cleanarch.bootstrap.app import create_app
from cleanarch.bootstrap.settings import Settings, get_settings

__all__ = ["Settings", "create_app", "get_settings"]
