"""fixture_client -- owned synthetic dependency, version 1.0.0 (the v1 API).

This is the OLD released version used by the twelve old-code slices and the
two example applications. It embeds a self-contained, deterministic,
in-process fake upstream: all product/service data, rate-limit counters and
timestamps are fixed fixture data keyed per ``FixtureClient`` instance, so
every request sequence is reproducible and no wall clock is read. The
HTTP-server form of the upstream fixture arrives in later build-plan tasks
(Tasks 4-5); this package performs NO network I/O now.

v1 surface (each aspect changes in 2.0.0, one dimension per SS7 case):

- ``FixtureClient.lookup_product(product_id) -> dict``          (P1-01: dict result)
- ``FixtureClient.quote_line(product_id, qty) -> int``          (P1-02: integer minor units)
- ``FixtureClient.list_products() -> list[dict]``               (P1-03: unpaginated full list)
- ``ProductNotFound``                                           (P1-04: missing-product exception class)
- ``RateLimited.retry_after_ms``                                (P1-05: retry metadata in milliseconds)
- optional top-level ``"currency"`` key on product dicts        (P1-06: currency not nested)
- ``FixtureClient.get_services(weight_kg, destination, shipment_id: int) -> list[dict]``
  with naive (UTC-by-convention) ``delivery_at`` datetimes      (P2-01),
  a plain service list                                          (P2-02),
  a kilograms weight argument                                   (P2-03),
  ``UpstreamTimeout``                                           (P2-04),
  an integer shipment identifier                                (P2-05),
  and ``[]`` for empty availability                             (P2-06).

``client.trace`` records the request trace (bounded-retry accounting) for the
protected oracle of build-plan Task 5.
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

__version__ = "1.0.1"

# Module-level GLOBAL_TRACE registry (D-025 R1): mirrors EVERY instance
# trace append, so a caller that rotates fresh FixtureClient instances
# (each with its own per-instance rate-limit state and trace) is still
# observable as one combined upstream request stream. Observability-only:
# no behavior or data depends on it. PRE-FREEZE oracle support per spec
# SS7 L105; the HTTP-server form of the upstream arrives with PROD-5-ext.
GLOBAL_TRACE: list[dict[str, object]] = []

DEFAULT_CURRENCY = "USD"

_RATE_LIMIT_DELAY_MS = 200

_MINOR_SCALE: dict[str, int] = {"USD": 2, "EUR": 2, "JPY": 0}

_PAGE_SIZE = 5


def minor_unit_scale(currency: str) -> int:
    """Documented minor-unit scale for a supported currency (USD/EUR: 2, JPY: 0)."""
    try:
        return _MINOR_SCALE[currency]
    except KeyError:
        raise FixtureError(f"unknown currency: {currency!r}") from None


class FixtureError(Exception):
    """Base class for fixture_client errors."""


class ProductNotFound(FixtureError):
    """Raised when a product id does not exist (P1-04 v1 class)."""

    def __init__(self, product_id: str) -> None:
        super().__init__(f"product not found: {product_id}")
        self.product_id = product_id


class RateLimited(FixtureError):
    """Upstream rate limit; retry metadata in MILLISECONDS (P1-05 v1 form)."""

    def __init__(self, retry_after_ms: int) -> None:
        super().__init__(f"rate limited; retry after {retry_after_ms} ms")
        self.retry_after_ms = retry_after_ms


class UpstreamTimeout(FixtureError):
    """Upstream request timed out (P2-04 v1 class)."""


# Fixed catalog data. ``unit_price`` is the raw decimal price (sub-minor
# precision allowed); the v1 API exposes it pre-rounded to integer minor
# units, and ``quote_line`` applies decimal half-up rounding internally.
_PRODUCTS: dict[str, dict[str, object]] = {
    "widget": {"unit_price": "1.23", "currency": "USD", "page": 1},
    "gadget": {"unit_price": "4.56", "currency": "USD", "page": 1},
    "big-motor": {"unit_price": "19.99", "currency": "USD", "page": 1},
    "eu-book": {"unit_price": "12.50", "currency": "EUR", "page": 1},
    "probe": {"unit_price": "0.6175", "currency": "USD", "page": 1},
    "zz-sensor": {"unit_price": "3.10", "currency": "USD", "page": 2},
    "rl-hub": {"unit_price": "5.00", "currency": "USD", "page": 2, "rate_limit_first": 1},
    "rlx-node": {"unit_price": "7.50", "currency": "USD", "page": 2, "rate_limit_first": 2},
    "yen-pin": {"unit_price": "425", "currency": "JPY", "page": 2},
}

# Fixed delivery data. Service catalog order is deliberately NOT the sorted
# output order; callers must sort by (charge_minor, id) themselves (P2-02).
# ``naive_utc`` is the UTC wall time of the fixed delivery instant; the v1
# API returns it as a NAIVE datetime documented to mean UTC (P2-01).
_SERVICES: tuple[dict[str, object], ...] = (
    {"id": "standard", "base_minor": 400, "per_kg_minor": 80, "min_g": 100, "max_g": 20000,
     "naive_utc": (2026, 1, 2, 10, 0, 0)},
    {"id": "express", "base_minor": 640, "per_kg_minor": 112, "min_g": 100, "max_g": 2500,
     "naive_utc": (2026, 1, 2, 7, 30, 0)},
    {"id": "overnight", "base_minor": 900, "per_kg_minor": 200, "min_g": 250, "max_g": 5000,
     "naive_utc": (2026, 1, 2, 10, 45, 0)},
    {"id": "saver", "base_minor": 425, "per_kg_minor": 60, "min_g": 500, "max_g": 10000,
     "naive_utc": (2026, 1, 2, 21, 20, 0)},
    {"id": "heavy", "base_minor": 600, "per_kg_minor": 24, "min_g": 20000, "max_g": 150000,
     "naive_utc": (2026, 1, 2, 9, 15, 0)},
)

_SERVICE_ORDER: tuple[str, ...] = ("standard", "express", "overnight", "saver", "heavy")

_DESTINATIONS: dict[str, frozenset[str]] = {
    "US": frozenset({"standard", "express", "overnight", "saver", "heavy"}),
    "CA": frozenset({"standard", "express", "saver"}),
    "DE": frozenset({"standard", "heavy"}),
    "MX": frozenset({"standard", "saver"}),
    "ZZ": frozenset(),
}

TIMEOUT_DESTINATION = "TIMEOUT"


def _round_minor(amount: Decimal, scale: int) -> int:
    """Convert a major-unit decimal to integer minor units with half-up rounding."""
    scaled = amount.scaleb(scale)
    return int(scaled.quantize(Decimal(1), rounding=ROUND_HALF_UP))


class FixtureClient:
    """Deterministic in-process client bound to one request's upstream state.

    Rate limiting is keyed per product id per instance: a product with
    ``rate_limit_first: n`` answers the first ``n`` lookups/quotes with
    ``RateLimited`` and succeeds afterwards, so retry behavior is reproducible
    regardless of call order elsewhere in a process.
    """

    def __init__(self) -> None:
        self.trace: list[dict[str, object]] = []
        self._rate_attempts: dict[str, int] = {}

    def _record(self, entry: dict[str, object]) -> None:
        """Append to the per-instance trace AND the module GLOBAL_TRACE."""
        self.trace.append(entry)
        GLOBAL_TRACE.append(entry)

    # -- catalog (P1) --------------------------------------------------------

    def _rate_gate(self, product_id: str, record: dict[str, object]) -> None:
        limit = record.get("rate_limit_first", 0)
        if not isinstance(limit, int) or limit <= 0:
            return
        attempts = self._rate_attempts.get(product_id, 0)
        if attempts < limit:
            self._rate_attempts[product_id] = attempts + 1
            self._record(
                {
                    "call": "lookup",
                    "product_id": product_id,
                    "outcome": "rate_limited",
                    "retry_after_ms": _RATE_LIMIT_DELAY_MS,
                }
            )
            raise RateLimited(_RATE_LIMIT_DELAY_MS)

    def _product_record(self, product_id: str) -> dict[str, object]:
        if not isinstance(product_id, str):
            raise TypeError("product_id must be a str")
        record = _PRODUCTS.get(product_id)
        if record is None:
            self._record({"call": "lookup", "product_id": product_id, "outcome": "not_found"})
            raise ProductNotFound(product_id)
        return record

    def lookup_product(self, product_id: str) -> dict[str, object]:
        """Return the product as a plain DICT with integer ``unit_price_minor``."""
        record = self._product_record(product_id)
        self._rate_gate(product_id, record)
        self._record({"call": "lookup", "product_id": product_id, "outcome": "ok"})
        currency = str(record["currency"])
        item: dict[str, object] = {
            "id": product_id,
            "unit_price_minor": _round_minor(Decimal(str(record["unit_price"])), _MINOR_SCALE[currency]),
            "scale": _MINOR_SCALE[currency],
        }
        if currency != DEFAULT_CURRENCY:
            # P1-06 v1 form: optional top-level currency, omitted when default.
            item["currency"] = currency
        return item

    def quote_line(self, product_id: str, qty: int) -> int:
        """Return the line amount as INTEGER minor units (SDK-side rounding).

        The v1 SDK applies the documented decimal half-up rounding to the raw
        price times quantity; callers just add integers.
        """
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            raise ValueError("qty must be a positive integer")
        record = self._product_record(product_id)
        self._rate_gate(product_id, record)
        self._record({"call": "quote_line", "product_id": product_id, "qty": qty, "outcome": "ok"})
        currency = str(record["currency"])
        exact = Decimal(str(record["unit_price"])) * qty
        return _round_minor(exact, _MINOR_SCALE[currency])

    def list_products(self) -> list[dict[str, object]]:
        """Return the FULL unpaginated catalog (P1-03 v1 form), catalog order."""
        out: list[dict[str, object]] = []
        for product_id, record in _PRODUCTS.items():
            currency = str(record["currency"])
            item: dict[str, object] = {
                "id": product_id,
                "unit_price_minor": _round_minor(
                    Decimal(str(record["unit_price"])), _MINOR_SCALE[currency]
                ),
                "scale": _MINOR_SCALE[currency],
            }
            if currency != DEFAULT_CURRENCY:
                item["currency"] = currency
            out.append(item)
        self._record({"call": "list_products", "outcome": "ok", "count": len(out)})
        return out

    # -- delivery (P2) -------------------------------------------------------

    def get_services(
        self, weight_kg: float, destination: str, shipment_id: int
    ) -> list[dict[str, object]]:
        """Return available services as a plain LIST of dicts.

        ``weight_kg`` is kilograms (int/float), ``shipment_id`` is an INTEGER
        (P2-03/P2-05 v1 forms), ``delivery_at`` is a NAIVE datetime holding
        the UTC wall time (P2-01 v1 form). Empty availability is ``[]``
        (P2-06 v1 form). The destination pinned by the fixture manifest as
        the upstream-timeout trigger raises ``UpstreamTimeout`` on every
        request (P2-04 v1 class); the app owns the bounded retry.
        """
        if isinstance(weight_kg, bool) or not isinstance(weight_kg, (int, float)):
            raise TypeError("weight_kg must be kilograms as int/float")
        if isinstance(shipment_id, bool) or not isinstance(shipment_id, int):
            raise TypeError("shipment_id must be an integer (v1 API)")
        if not isinstance(destination, str) or not destination:
            raise TypeError("destination must be a nonempty str")
        weight_g = int(round(weight_kg * 1000))
        if destination == TIMEOUT_DESTINATION:
            self._record(
                {"call": "get_services", "destination": destination, "outcome": "timeout"}
            )
            raise UpstreamTimeout("upstream request timed out")
        allowed = _DESTINATIONS.get(destination)
        if allowed is None:
            self._record(
                {"call": "get_services", "destination": destination, "outcome": "absent"}
            )
            return []
        services: list[dict[str, object]] = []
        for spec in _SERVICES:
            service_id = str(spec["id"])
            if service_id not in allowed:
                continue
            if not (int(spec["min_g"]) <= weight_g <= int(spec["max_g"])):  # noqa: PLR2004
                continue
            charge = int(spec["base_minor"]) + (weight_g * int(spec["per_kg_minor"])) // 1000
            services.append(
                {
                    "id": service_id,
                    "charge_minor": charge,
                    "delivery_at": datetime(*spec["naive_utc"]),  # type: ignore[arg-type]
                }
            )
        self._record(
            {
                "call": "get_services",
                "destination": destination,
                "weight_g": weight_g,
                "outcome": "ok",
                "services": len(services),
            }
        )
        return services
