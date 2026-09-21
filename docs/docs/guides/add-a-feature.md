---
id: add-a-feature
title: Add a feature
sidebar_position: 1
---

# Add a feature

Two ways: scaffold it, or walk the rings by hand. Both end with the same eight files.

## Scaffold

```bash
uv run python scripts/new_feature.py orders
```

creates:

- `src/cleanarch/orders/` - an `Order` entity (id, name, created_at), `OrderCreated` event,
  `OrderRepository` port, `CreateOrder` / `GetOrder` use cases, an in-memory adapter and a
  router with `POST /orders` and `GET /orders/{id}`;
- `src/cleanarch/bootstrap/features/orders.py` - the wiring, already listed in `FEATURES`;
- `tests/test_orders.py` - a use-case test with fakes and an HTTP round trip.

`make check` is green and `make run-memory` serves `POST /api/v1/orders` before you change a
line. Now replace the placeholder fields with your model, inside-out.

## By hand, inside-out

### 1. Domain - what is true regardless of I/O

```python title="orders/domain/order.py"
@dataclass(frozen=True, slots=True)
class Order:
    id: OrderId
    customer: str
    lines: tuple[OrderLine, ...]
    status: OrderStatus = OrderStatus.DRAFT

    def __post_init__(self) -> None:
        if not self.lines:
            raise EmptyOrder

    def submit(self) -> DomainResult["Order"]:
        if self.status is not OrderStatus.DRAFT:
            raise OrderAlreadySubmitted
        return DomainResult.of(replace(self, status=OrderStatus.SUBMITTED), OrderSubmitted(self.id))
```

Rules in `__post_init__` and methods. Methods return `DomainResult` (new state + events) and
never mutate. Errors are specific `DomainError` subclasses. Write the domain tests now -
they need nothing (see `tests/tournaments/test_tournament.py` for the shape).

### 2. Application - one class per operation, ports for the outside

```python title="orders/application/ports.py"
class OrderRepository(Protocol):
    async def add(self, order: Order) -> None: ...
    async def get(self, order_id: OrderId) -> Order | None: ...
    async def save(self, order: Order) -> None: ...
```

```python title="orders/application/use_cases.py"
class SubmitOrder:
    def __init__(self, repository: OrderRepository, events: EventPublisher) -> None: ...

    async def execute(self, order_id: OrderId) -> Order:
        order = await self._repository.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        result = order.submit()
        await self._repository.save(result.aggregate)
        await self._events.publish(result.events)
        return result.aggregate
```

Need a command object? Only when there are several input fields (`CreateOrderCommand`).
Need the current time? Take the shared `Clock` port in the constructor (as `CreateTournament`
does) and pass `clock.now()` into the domain; never call `datetime.now()` in a use case or
an entity.

Test use cases with `InMemoryOrderRepository` and `RecordingEventPublisher` (from
`tests/conftest.py`); the scaffolded `tests/test_orders.py` already does.

### 3. Infrastructure - implement the ports

Start with `in_memory.py` (a dict). Add `sqlalchemy/` when you need persistence:

- `models.py` - the row (`OrderModel(Base)`), *not* the entity;
- `mapping.py` - `to_model` / `to_domain` / `update_model`;
- `repository.py` - the port implementation on an `AsyncSession`, `flush()` not `commit()`.

Then `alembic/env.py`: import the model module, and

```bash
make migration m="create orders"   # autogenerate
make migrate
```

Copy `tests/tournaments/test_repository_contract.py`: the same tests must pass on
your in-memory and SQL adapters, including the stale-write conflict (ADR-010).

### 4. HTTP - parse, execute, present

- `schemas.py`: `CreateOrderRequest.to_command()`, `OrderResponse.from_domain()`.
- `dependencies.py`: `get_order_repository()` placeholder + one factory per use case.
- `router.py`: every handler is three lines.

Add an HTTP test per error mapping (`client` fixture, see `tests/tournaments/test_api.py`).

### 5. Bootstrap - choose adapters

`bootstrap/features/orders.py` is where the feature meets the outside world. Its optional
hooks: `wire_http(app, settings)` (pick the repository from `settings.use_in_memory`, include
the router), `subscribe(bus)` (event handlers; they run after the request committed),
`register_cli(subparsers)` / `run_cli(args, session, events)`. The example's module shows all
four. The module must be listed in `bootstrap/features/__init__.py`.

### 6. Check

```bash
make check
```

`scripts/archcheck.py check` (part of it) tells you if anything points the wrong way.
