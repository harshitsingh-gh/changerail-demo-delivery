"""P2-02 old-code slice: service filtering and stable ordering on the v1 list.

Behavior contract slice (spec SS3): the destination's eligible services come
back as a plain LIST which this slice sorts by (charge_minor, id) -- the
stable ordering the public contract pins, including ties broken by id.
Written against fixture_client 1.0.0. On fixture_client 2.0.0 the service
list is a KEYED mapping (and the call signature changed to grams/str), so
the old list-oriented code fails at call time (the seeded P2-02
incompatibility: service list changes into keyed entries).
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
    eligible = [service for service in services if service["charge_minor"] > 0]
    entries = [
        {
            "id": service["id"],
            "charge_minor": service["charge_minor"],
            "delivery_at": service["delivery_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        for service in eligible
    ]
    entries.sort(key=lambda entry: (entry["charge_minor"], entry["id"]))
    return {"shipment_id": shipment_id, "services": entries}
