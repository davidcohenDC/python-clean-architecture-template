"""The building blocks in ``shared``, on their own."""

from dataclasses import dataclass
from datetime import UTC, datetime

from cleanarch.shared.application.errors import ApplicationError, NotFoundError
from cleanarch.shared.domain.errors import DomainError
from cleanarch.shared.domain.events import DomainEvent
from cleanarch.shared.domain.result import DomainResult
from cleanarch.shared.infrastructure.clock import FixedClock, SystemClock


class OrderAlreadyShipped(DomainError):
    message = "Order has already been shipped."


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderShipped(DomainEvent):
    order_id: str


def test_errors_carry_a_default_message_per_type_and_accept_an_override():
    assert str(OrderAlreadyShipped()) == "Order has already been shipped."
    assert str(OrderAlreadyShipped("Shipped on Monday.")) == "Shipped on Monday."
    assert str(DomainError()) == "Domain rule violated."
    assert str(NotFoundError()) == "Resource not found."
    assert str(ApplicationError("custom")) == "custom"


def test_events_compare_by_payload_not_by_metadata():
    first, second = OrderShipped(order_id="o-1"), OrderShipped(order_id="o-1")
    assert first == second
    assert first.event_id != second.event_id
    assert first.occurred_at.tzinfo is UTC


def test_domain_result_pairs_the_new_state_with_its_events():
    result = DomainResult.of("shipped-order", OrderShipped(order_id="o-1"))
    assert result.aggregate == "shipped-order"
    assert result.events == (OrderShipped(order_id="o-1"),)
    assert DomainResult.of("untouched").events == ()


def test_clocks():
    assert SystemClock().now().tzinfo is UTC
    at = datetime(2026, 1, 1, tzinfo=UTC)
    assert FixedClock(at).now() == at
