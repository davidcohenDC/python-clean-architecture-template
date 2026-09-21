"""Where each feature meets the outside world: one module per feature, listed here.

A feature module may define any of these hooks (all optional):

    wire_http(app, settings)          choose adapters, override placeholders, mount the router
    subscribe(bus)                    register event handlers
    register_cli(subparsers)          add sub-commands to ``python -m <package>``
    run_cli(args, session, events)    execute one of them; return True if handled

``scripts/new_feature.py`` generates the module and adds it to ``FEATURES``;
``scripts/init_project.py --remove-example`` removes the example's.
"""

from types import ModuleType

from cleanarch.bootstrap.features import tournaments

FEATURES: list[ModuleType] = [tournaments]
