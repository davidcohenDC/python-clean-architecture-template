"""python-clean-architecture-template.

Package layout (see docs/ for the long version):

    cleanarch/
    ├── shared/        TEMPLATE  - building blocks every feature reuses
    ├── <feature>/     one package per feature, same four rings each
    ├── bootstrap/     TEMPLATE  - composition root: settings + wiring
    └── main.py        TEMPLATE  - ASGI entrypoint

Each feature (and ``shared``) is split into the four Clean Architecture rings:
``domain`` → ``application`` → ``infrastructure`` / ``http``. Dependencies only
point inward; ``tests/architecture`` fails the build if they don't.
"""

__version__ = "0.5.1"
