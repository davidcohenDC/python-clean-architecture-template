"""Adapters implementing the tournament ports.

Two implementations of the same ``TournamentRepository`` port:

* ``in_memory``  - a dict. Used by application/API tests and by ``DATABASE_URL=memory``.
* ``sqlalchemy`` - a real table. Used by default and by integration tests.

Being able to swap them without touching a use case is the whole point.
"""
