"""EXAMPLE FEATURE — tournaments.

This package is the demo domain. It exists to show every layer of the
template working together on a realistic problem. When you build your own
service, delete this directory and follow docs/guides/replace-example-domain.

Layout (the same for every feature):

    tournaments/
    ├── domain/          entities, value objects, events, domain errors
    ├── application/     use cases, commands, ports (interfaces)
    ├── infrastructure/  adapters that implement the ports (DB, in-memory)
    └── http/            FastAPI router + request/response schemas
"""
