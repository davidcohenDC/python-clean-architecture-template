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

creates `src/cleanarch/orders/` with an `Order` entity (id + name), `OrderCreated` event,
`OrderRepository` port, `CreateOrder` / `GetOrder` use cases, an in-memory adapter and a router
with `POST /orders` and `GET /orders/{id}`. Wire it in `bootstrap/app.py`:

```python
from cleanarch.orders.http import get_order_repository, router as orders_router
from cleanarch.orders.infrastructure.in_memory import InMemoryOrderRepository

# inside create_app(), after wire_shared(app):
orders = InMemoryOrderRepository()
app.dependency_overrides[get_order_repository] = lambda: orders
app.include_router(orders_router, prefix="/api/v1")
```

Run `make run-memory`, open `/docs`, and `POST /api/v1/orders` works. Now replace the
placeholder fields with your model, inside-out.

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
never mutate. Errors are specific `DomainError` subclasses. Write `tests/domain/test_order.py`
now - it needs nothing.

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
Need the current time? Add a `Clock` Protocol to `ports.py`; never call `datetime.now()`
in a use case.

Write `tests/application/test_order_use_cases.py` with `InMemoryOrderRepository` and
`RecordingEventPublisher`.

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

Write `tests/integration/test_order_repository.py` (copy the tournament one).

### 4. HTTP - parse, execute, present

- `schemas.py`: `CreateOrderRequest.to_command()`, `OrderResponse.from_domain()`.
- `dependencies.py`: `get_order_repository()` placeholder + one factory per use case.
- `router.py`: every handler is three lines.

Write `tests/api/test_orders_api.py`, including one test per error mapping.

### 5. Bootstrap - choose adapters

In `bootstrap/app.py` add `wire_orders(app, settings)` next to `wire_tournaments`: pick the
repository based on `settings.use_in_memory`, subscribe event handlers if any, include the router.

### 6. Check

```bash
make check
```

`tests/architecture` will tell you if anything points the wrong way.
