---
id: dependency-graph
title: Dependency graph (generated)
sidebar_position: 6
---

# Dependency graph, generated from the code

Every arrow below is a real `import` found by the same parser that enforces the
[Dependency Rule](testing#architecture-a-tool-and-optionally-a-test) - not a
drawing of intent. Regenerate with `make graph`; in the template repository
`tests/template/test_graph.py` fails when this file is stale.

```mermaid
flowchart LR
    bootstrap["bootstrap"]
    shared_application["shared.application"]
    shared_domain["shared.domain"]
    shared_http["shared.http"]
    shared_infrastructure["shared.infrastructure"]
    tournaments_application["tournaments.application"]
    tournaments_cli["tournaments.cli"]
    tournaments_domain["tournaments.domain"]
    tournaments_http["tournaments.http"]
    tournaments_infrastructure["tournaments.infrastructure"]
    bootstrap --> shared_application
    bootstrap --> shared_domain
    bootstrap --> shared_http
    bootstrap --> shared_infrastructure
    bootstrap --> tournaments_application
    bootstrap --> tournaments_cli
    bootstrap --> tournaments_domain
    bootstrap --> tournaments_http
    bootstrap --> tournaments_infrastructure
    shared_application --> shared_domain
    shared_http --> shared_application
    shared_http --> shared_domain
    shared_infrastructure --> shared_domain
    tournaments_application --> shared_application
    tournaments_application --> tournaments_domain
    tournaments_cli --> shared_application
    tournaments_cli --> tournaments_application
    tournaments_cli --> tournaments_domain
    tournaments_domain --> shared_domain
    tournaments_http --> shared_application
    tournaments_http --> shared_http
    tournaments_http --> tournaments_application
    tournaments_http --> tournaments_domain
    tournaments_infrastructure --> shared_application
    tournaments_infrastructure --> shared_infrastructure
    tournaments_infrastructure --> tournaments_domain
    style bootstrap fill:#6b7280,color:#fff,stroke:none
    style shared_application fill:#2563eb,color:#fff,stroke:none
    style shared_domain fill:#16a34a,color:#fff,stroke:none
    style shared_http fill:#d97706,color:#fff,stroke:none
    style shared_infrastructure fill:#d97706,color:#fff,stroke:none
    style tournaments_application fill:#2563eb,color:#fff,stroke:none
    style tournaments_cli fill:#d97706,color:#fff,stroke:none
    style tournaments_domain fill:#16a34a,color:#fff,stroke:none
    style tournaments_http fill:#d97706,color:#fff,stroke:none
    style tournaments_infrastructure fill:#d97706,color:#fff,stroke:none
```
