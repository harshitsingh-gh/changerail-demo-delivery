"""P2-03 migrated slice: integer-grams weight argument on the v2 delivery API.

Behavior contract slice (spec SS3): weight eligibility windows and charges
are exact integer conversions of the request weight. Migrated to
fixture_client 2.0.0, whose ``get_services`` takes ``weight_g`` as INTEGER
GRAMS under a strict type check (the P2-03 change: the weight argument went
from kilograms to integer grams), so the kilogram-to-gram conversion that
1.0.0 performed inside the SDK now happens in the application. The same
call site follows the rest of the v2 envelope: ``shipment_id`` is a string,
availability comes back as the keyed ``{"services": {id: entry}}`` mapping
(or the explicit ``ABSENT`` sentinel for empty availability), and each
``delivery_at`` is a timezone-aware datetime in the service's local offset
that is normalized to UTC before rendering. The rendered response shape is
unchanged.
"""

from __future__ import annotations

from datetime import timezone
from decimal import Decimal

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


def _weight_kg_to_g(weight_kg: float) -> int:
    """Convert a validated kilogram weight to the v2 INTEGER-GRAMS argument.

    The scaling is done on the exact decimal value of the request weight
    (``str`` of the parsed weight round-trips to the decimal the caller
    sent), so whole-gram requests like ``"2.500"`` convert to exactly 2500 g
    with no binary-float drift; a sub-gram remainder truncates toward zero,
    matching the integer conversion the SDK applied in 1.0.0.
    """
    return int(Decimal(str(weight_kg)) * 1000)


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
    result = client.get_services(
        weight_g=_weight_kg_to_g(weight_kg), destination=destination, shipment_id=shipment_id
    )
    if result is fc.ABSENT:
        available: dict[str, dict[str, object]] = {}
    else:
        available = result["services"]
    entries: list[dict[str, object]] = []
    for service_id, service in available.items():
        entries.append(
            {
                "id": service_id,
                "charge_minor": service["charge_minor"],
                "delivery_at": service["delivery_at"]
                .astimezone(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    entries.sort(key=lambda entry: (entry["charge_minor"], entry["id"]))
    return {"shipment_id": shipment_id, "services": entries}
