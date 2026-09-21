---
id: 001-feature-first-layout
title: "ADR-001: Feature-first layout"
---

# ADR-001: Feature-first layout, rings inside each feature

**Status:** accepted

## Context

Two layouts are common for Clean Architecture in Python:

- **Layer-first**: `domain/`, `application/`, `infrastructure/`, `presentation/` at the top,
  each containing a sub-package per feature.
- **Feature-first**: one package per feature, each containing the four rings.

The template's first job is to be replaced: a user must remove the example domain and add
their own without hunting through four trees. Its second job is to make the rings visible.

## Decision

Feature-first, with the four rings inside every feature **and** inside `shared/`:

```text
shared/{domain,application,infrastructure,http}
tournaments/{domain,application,infrastructure,http}
bootstrap/
```

Cross-feature imports are forbidden; `shared` never imports a feature. The architecture
tests enforce both, and enforce the ring order inside every package.

## Consequences

- Removing or adding a feature touches one directory plus `bootstrap` (and marked blocks).
- Each feature reads top-to-bottom as a vertical slice, which is how people learn it.
- The ring names are repeated in every feature, so the layer discipline is no less visible
  than in a layer-first tree; it is simply applied per feature.
- `shared/` is under permanent pressure to grow. The rule: something goes there only when
  two features need it *and* it has no feature-specific meaning.

## Proof

- proof:dependency-rule - every module imports inward; checked on the real package and
  falsified on synthetic packages (`tests/architecture`).
- proof:feature-isolation - no feature imports another, `shared` imports no feature.
- proof:example-removal - the layout's promise that the example is one folder plus marked
  blocks: `init_project.py --remove-example` leaves a working project (`tests/template`).
