"""P2-01 old-code slice: naive UTC datetimes from the v1 delivery API.

Behavior contract slice (spec SS3 POST /estimate): services carry fixed UTC
timestamps formatted ``...Z``. Written against fixture_client 1.0.0, whose
``get_services`` returns a plain list with NAIVE datetimes documented as UTC,
so ``strftime`` with a literal ``Z`` is correct. On fixture_client 2.0.0 the
API takes grams/str keyword arguments and returns aware datetimes across
multiple UTC offsets, so the old call fails at call time (the seeded P2-01
incompatibility: delivery datetime becomes timezone-aware).
"""

from __future__ import annotations

import fixture_client as fc


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
    services = client.get_services(
        weight_kg=weight_kg, destination=destination, shipment_id=int(shipment_id)
    )
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
