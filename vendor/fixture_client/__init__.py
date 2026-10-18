"""fixture_client -- owned synthetic dependency, version 2.0.0 (the v2 API).

This is the NEW released version that the twelve seeded incompatibilities of
spec SS7 migrate to. It embeds the same self-contained, deterministic,
in-process fake upstream as 1.0.0 (fixed data, per-instance counters, no wall
clock, NO network I/O); the HTTP-server form of the upstream fixture arrives
in later build-plan tasks (Tasks 4-5).

Changed surface (old v1 code calling this package fails AT CALL TIME -- a
TypeError/AttributeError/KeyError or contract-wrong output -- never at
import, because old code reaches attributes lazily inside functions):

- P1-01: ``lookup_product`` now returns a typed ``Product`` OBJECT (no
  ``__getitem__``/``__iter__``), not a dict.
- P1-02: amounts changed from integer minor units to DECIMAL STRINGS:
  ``quote_line`` returns the exact unrounded ``Decimal`` string and the
  caller must apply the documented minor-unit half-up rounding.
- P1-03: ``list_products`` is PAGINATED and returns a typed ``ProductPage``
  (iterate ``page.items``; follow ``page.next_page``); some products exist
  only on page two.
- P1-04: the missing-product exception class is now ``UnknownProductError``
  (``ProductNotFound`` no longer exists).
- P1-05: rate-limit retry metadata is now SECONDS (``RateLimited.retry_after_s``).
- P1-06: the optional currency field moved into nested product ``metadata``.
- P2-01: ``delivery_at`` is now a TIMEZONE-AWARE datetime expressed in the
  service's local UTC offset (callers must convert to UTC).
- P2-02: the service list is now a KEYED mapping ``{"services": {id: ...}}``.
- P2-03: the weight argument is now INTEGER GRAMS (``weight_g``).
- P2-04: the upstream timeout exception class is now ``UpstreamRequestTimeout``.
- P2-05: the shipment identifier is now a STRING (an int raises TypeError).
- P2-06: empty availability is now the explicit ``ABSENT`` sentinel value.

``client.trace`` records the request trace (bounded-retry accounting) for the
protected oracle of build-plan Task 5.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

__version__ = "2.0.1"

# Module-level GLOBAL_TRACE registry (D-025 R1): mirrors EVERY instance
# trace append, so a caller that rotates fresh FixtureClient instances
# (each with its own per-instance rate-limit state and trace) is still
# observable as one combined upstream request stream. Observability-only:
# no behavior or data depends on it. PRE-FREEZE oracle support per spec
# SS7 L105; the HTTP-server form of the upstream arrives with PROD-5-ext.
GLOBAL_TRACE: list[dict[str, object]] = []

DEFAULT_CURRENCY = "USD"

_RATE_LIMIT_DELAY_S = 0.2

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


class UnknownProductError(FixtureError):
    """Raised when a product id does not exist (P1-04 v2 class)."""

    def __init__(self, product_id: str) -> None:
        super().__init__(f"unknown product: {product_id}")
        self.product_id = product_id


class RateLimited(FixtureError):
    """Upstream rate limit; retry metadata in SECONDS (P1-05 v2 form)."""

    def __init__(self, retry_after_s: float) -> None:
        super().__init__(f"rate limited; retry after {retry_after_s} s")
        self.retry_after_s = retry_after_s


class UpstreamRequestTimeout(FixtureError):
    """Upstream request timed out (P2-04 v2 class)."""


class _Absent:
    """Explicit absent-availability sentinel (P2-06 v2 form).

    Deliberately not iterable and truthy: v1 code that tested ``if not
    services`` or iterated the result fails loudly at call time instead of
    quietly fabricating availability.
    """

    _instance: "_Absent | None" = None

    def __new__(cls) -> "_Absent":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "ABSENT"


ABSENT = _Absent()


class ProductMetadata:
    """Nested product metadata (P1-06 v2 form: currency lives here, optional)."""

    __slots__ = ("currency",)

    def __init__(self, currency: str | None) -> None:
        self.currency = currency

    def __repr__(self) -> str:
        return f"ProductMetadata(currency={self.currency!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ProductMetadata) and self.currency == other.currency


class Product:
    """Typed catalog product (P1-01 v2 form; deliberately NOT subscriptable)."""

    __slots__ = ("id", "unit_price", "metadata")

    def __init__(self, product_id: str, unit_price: str, metadata: ProductMetadata) -> None:
        self.id = product_id
        self.unit_price = unit_price
        self.metadata = metadata

    def __repr__(self) -> str:
        return (
            f"Product(id={self.id!r}, unit_price={self.unit_price!r}, "
            f"metadata={self.metadata!r})"
        )


class ProductPage:
    """One page of the paginated catalog (P1-03 v2 form; not iterable itself)."""

    __slots__ = ("items", "page", "pages", "next_page")

    def __init__(
        self, items: tuple[Product, ...], page: int, pages: int, next_page: int | None
    ) -> None:
        self.items = items
        self.page = page
        self.pages = pages
        self.next_page = next_page

    def __repr__(self) -> str:
        return (
            f"ProductPage(page={self.page}, pages={self.pages}, "
            f"next_page={self.next_page}, items={len(self.items)})"
        )


# Fixed catalog data (same underlying catalog as 1.0.0).
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

# Fixed delivery data. ``utc`` is the delivery instant's UTC wall time and
# ``offset`` the timezone the v2 API presents it in (P2-01: aware datetimes
# across multiple offsets, including day boundaries in both directions).
_SERVICES: tuple[dict[str, object], ...] = (
    {"id": "standard", "base_minor": 400, "per_kg_minor": 80, "min_g": 100, "max_g": 20000,
     "utc": (2026, 1, 2, 10, 0, 0), "offset": 0},
    {"id": "express", "base_minor": 640, "per_kg_minor": 112, "min_g": 100, "max_g": 2500,
     "utc": (2026, 1, 2, 7, 30, 0), "offset": -8},
    {"id": "overnight", "base_minor": 900, "per_kg_minor": 200, "min_g": 250, "max_g": 5000,
     "utc": (2026, 1, 2, 10, 45, 0), "offset": 8},
    {"id": "saver", "base_minor": 425, "per_kg_minor": 60, "min_g": 500, "max_g": 10000,
     "utc": (2026, 1, 2, 21, 20, 0), "offset": 5.5},
    {"id": "heavy", "base_minor": 600, "per_kg_minor": 24, "min_g": 20000, "max_g": 150000,
     "utc": (2026, 1, 2, 9, 15, 0), "offset": -5},
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


def _aware(spec: dict[str, object]) -> datetime:
    offset = float(spec["offset"])  # type: ignore[arg-type]
    tz = timezone(timedelta(hours=offset))
    utc_fields = spec["utc"]  # type: ignore[arg-type]
    utc_wall = datetime(*utc_fields)
    return (utc_wall + timedelta(hours=offset)).replace(tzinfo=tz)


class FixtureClient:
    """Deterministic in-process client bound to one request's upstream state.

    Rate limiting is keyed per product id per instance (same semantics as
    1.0.0) so retry behavior is reproducible regardless of call order.
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
                    "retry_after_s": _RATE_LIMIT_DELAY_S,
                }
            )
            raise RateLimited(_RATE_LIMIT_DELAY_S)

    def _product_record(self, product_id: str) -> dict[str, object]:
        if not isinstance(product_id, str):
            raise TypeError("product_id must be a str")
        record = _PRODUCTS.get(product_id)
        if record is None:
            self._record({"call": "lookup", "product_id": product_id, "outcome": "not_found"})
            raise UnknownProductError(product_id)
        return record

    def lookup_product(self, product_id: str) -> Product:
        """Return the product as a typed ``Product`` (P1-01 v2 form).

        ``unit_price`` is the raw DECIMAL STRING (P1-02) and the optional
        currency lives at ``metadata.currency`` (P1-06; ``None`` means the
        default currency USD).
        """
        record = self._product_record(product_id)
        self._rate_gate(product_id, record)
        self._record({"call": "lookup", "product_id": product_id, "outcome": "ok"})
        currency = str(record["currency"])
        metadata = ProductMetadata(None if currency == DEFAULT_CURRENCY else currency)
        return Product(product_id, str(record["unit_price"]), metadata)

    def quote_line(self, product_id: str, qty: int) -> str:
        """Return the exact line amount as a DECIMAL STRING (P1-02 v2 form).

        The v2 SDK no longer rounds: the caller must apply the documented
        currency minor-unit scale with decimal half-up rounding.
        """
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            raise ValueError("qty must be a positive integer")
        record = self._product_record(product_id)
        self._rate_gate(product_id, record)
        self._record({"call": "quote_line", "product_id": product_id, "qty": qty, "outcome": "ok"})
        return str(Decimal(str(record["unit_price"])) * qty)

    def list_products(self, page: int = 1) -> ProductPage:
        """Return one page of the paginated catalog (P1-03 v2 form)."""
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError("page must be a positive integer")
        total = len(_PRODUCTS)
        pages = (total + _PAGE_SIZE - 1) // _PAGE_SIZE
        page = min(page, pages)
        ids = list(_PRODUCTS)
        start = (page - 1) * _PAGE_SIZE
        slice_ids = ids[start : start + _PAGE_SIZE]
        items = tuple(self._page_product(product_id) for product_id in slice_ids)
        next_page = page + 1 if page < pages else None
        self._record(
            {"call": "list_products", "page": page, "outcome": "ok", "count": len(items)}
        )
        return ProductPage(items=items, page=page, pages=pages, next_page=next_page)

    def _page_product(self, product_id: str) -> Product:
        record = _PRODUCTS[product_id]
        currency = str(record["currency"])
        metadata = ProductMetadata(None if currency == DEFAULT_CURRENCY else currency)
        return Product(product_id, str(record["unit_price"]), metadata)

    # -- delivery (P2) -------------------------------------------------------

    def get_services(
        self, weight_g: int, destination: str, shipment_id: str
    ) -> dict[str, dict[str, object]] | _Absent:
        """Return available services in the v2 envelope, or ``ABSENT``.

        ``weight_g`` is INTEGER GRAMS (P2-03; anything but a non-bool int
        raises TypeError) and ``shipment_id`` is a STRING (P2-05). The result
        is a KEYED mapping ``{"services": {id: entry}}`` (P2-02) whose
        ``delivery_at`` values are TIMEZONE-AWARE datetimes in each service's
        local offset (P2-01). Empty availability is the explicit ``ABSENT``
        sentinel (P2-06); the manifest-pinned timeout destination raises
        ``UpstreamRequestTimeout`` on every request (P2-04).
        """
        if isinstance(weight_g, bool) or not isinstance(weight_g, int):
            raise TypeError("weight_g must be integer grams (v2 API)")
        if not isinstance(shipment_id, str):
            raise TypeError("shipment_id must be a str (v2 API)")
        if not isinstance(destination, str) or not destination:
            raise TypeError("destination must be a nonempty str")
        if destination == TIMEOUT_DESTINATION:
            self._record(
                {"call": "get_services", "destination": destination, "outcome": "timeout"}
            )
            raise UpstreamRequestTimeout("upstream request timed out")
        allowed = _DESTINATIONS.get(destination)
        if allowed is None or not allowed:
            self._record(
                {"call": "get_services", "destination": destination, "outcome": "absent"}
            )
            return ABSENT
        services: dict[str, dict[str, object]] = {}
        for spec in _SERVICES:
            service_id = str(spec["id"])
            if service_id not in allowed:
                continue
            if not (int(spec["min_g"]) <= weight_g <= int(spec["max_g"])):  # noqa: PLR2004
                continue
            charge = int(spec["base_minor"]) + (weight_g * int(spec["per_kg_minor"])) // 1000
            services[service_id] = {
                "charge_minor": charge,
                "delivery_at": _aware(spec),
            }
        self._record(
            {
                "call": "get_services",
                "destination": destination,
                "weight_g": weight_g,
                "outcome": "ok",
                "services": len(services),
            }
        )
        return {"services": services}
