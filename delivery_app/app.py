"""P2-06 old-code slice: empty availability as an empty list on the v1 API.

Behavior contract slice (spec SS3): a destination with no available services
returns a normal response with an EMPTY services list, never an exception
and never fabricated availability; valid alternatives return their real
services. Written against fixture_client 1.0.0, whose ``get_services``
returns ``[]`` for empty availability. On fixture_client 2.0.0 empty
availability is the explicit ``ABSENT`` sentinel (and the call signature
changed to grams/str), so the old falsy-list handling fails at call time
(the seeded P2-06 incompatibility: empty availability changes from empty
list to explicit absent value).
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
    if not services:
        return {"shipment_id": shipment_id, "services": []}
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
