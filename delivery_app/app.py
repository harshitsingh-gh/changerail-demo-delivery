"""P2-04 old-code slice: bounded retry and the terminal 503 on v1 timeouts.

Behavior contract slice (spec SS3): an exhausted upstream timeout maps to the
fixed HTTP 503 body ``{"error": "upstream_timeout"}`` after the bounded retry
allowance (at most three upstream requests). Written against fixture_client
1.0.0, which raises ``UpstreamTimeout``. On fixture_client 2.0.0 the timeout
exception class is ``UpstreamRequestTimeout`` (and the call signature changed
to grams/str), so the old handler fails at call time (the seeded P2-04
incompatibility: upstream timeout exception changes).
"""

from __future__ import annotations

import fixture_client as fc

MAX_UPSTREAM_ATTEMPTS = 3


def _invalid() -> dict[str, object]:
    return {"status": 422, "body": {"error": "invalid_input"}}


def _parse_weight_kg(raw: object) -> float | None:
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def handle(request: dict) -> dict:
    weight_kg = _parse_weight_kg(request.get("weight_kg"))
    if weight_kg is None:
        return _invalid()
    shipment_id = request.get("shipment_id")
    if not isinstance(shipment_id, str) or not shipment_id.isdigit() or not 3 <= len(shipment_id) <= 12:
        return _invalid()
    destination = request.get("destination")
    if not isinstance(destination, str) or not destination:
        return _invalid()

    client = fc.FixtureClient()
    services: list[dict[str, object]] | None = None
    for attempt in range(1, MAX_UPSTREAM_ATTEMPTS + 1):
        try:
            services = client.get_services(
                weight_kg=weight_kg, destination=destination, shipment_id=int(shipment_id)
            )
            break
        except fc.UpstreamTimeout:
            if attempt == MAX_UPSTREAM_ATTEMPTS:
                return {"status": 503, "body": {"error": "upstream_timeout"}}
    assert services is not None
    entries: list[dict[str, object]] = []
    for service in services:
        entries.append(
            {
                "id": service["id"],
                "charge_minor": service["charge_minor"],
                "delivery_at": service["delivery_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    entries.sort(key=lambda entry: (entry["charge_minor"], entry["id"]))
    return {"shipment_id": shipment_id, "services": entries}
