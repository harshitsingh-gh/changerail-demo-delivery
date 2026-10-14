"""Ordinary in-repo pytest suite a candidate repository would carry."""

from __future__ import annotations

from delivery_app.app import handle


def test_us_estimate_sorted_with_fixed_timestamps() -> None:
    response = handle(
        {"weight_kg": "1.250", "destination": "US", "shipment_id": "00017"}
    )
    assert response == {
        "shipment_id": "00017",
        "services": [
            {"id": "saver", "charge_minor": 500, "delivery_at": "2026-01-02T21:20:00Z"},
            {"id": "standard", "charge_minor": 500, "delivery_at": "2026-01-02T10:00:00Z"},
            {"id": "express", "charge_minor": 780, "delivery_at": "2026-01-02T07:30:00Z"},
            {"id": "overnight", "charge_minor": 1150, "delivery_at": "2026-01-02T10:45:00Z"},
        ],
    }


def test_charge_tie_broken_by_id() -> None:
    response = handle(
        {"weight_kg": "1.250", "destination": "MX", "shipment_id": "00017"}
    )
    assert [service["id"] for service in response["services"]] == ["saver", "standard"]
    assert {service["charge_minor"] for service in response["services"]} == {500}


def test_shipment_id_leading_zeros_preserved() -> None:
    response = handle(
        {"weight_kg": "0.750", "destination": "CA", "shipment_id": "000000017"}
    )
    assert response["shipment_id"] == "000000017"


def test_empty_availability_returns_empty_list() -> None:
    response = handle(
        {"weight_kg": "1.250", "destination": "ZZ", "shipment_id": "00017"}
    )
    assert response == {"shipment_id": "00017", "services": []}


def test_exhausted_upstream_timeout_is_503() -> None:
    response = handle(
        {"weight_kg": "1.250", "destination": "TIMEOUT", "shipment_id": "00017"}
    )
    assert response == {"status": 503, "body": {"error": "upstream_timeout"}}


def test_heavy_weight_boundary_service_set() -> None:
    response = handle(
        {"weight_kg": "20.000", "destination": "DE", "shipment_id": "00017"}
    )
    assert response == {
        "shipment_id": "00017",
        "services": [
            {"id": "heavy", "charge_minor": 1080, "delivery_at": "2026-01-02T09:15:00Z"},
            {"id": "standard", "charge_minor": 2000, "delivery_at": "2026-01-02T10:00:00Z"},
        ],
    }


def test_invalid_weights_rejected() -> None:
    for bad_weight in ("abc", "0.000", "-1.000"):
        response = handle(
            {"weight_kg": bad_weight, "destination": "US", "shipment_id": "00017"}
        )
        assert response == {"status": 422, "body": {"error": "invalid_input"}}


def test_invalid_shipment_ids_rejected() -> None:
    for bad_id in ("0001-7", "17A1", "1", "01234567890123"):
        response = handle(
            {"weight_kg": "1.250", "destination": "US", "shipment_id": bad_id}
        )
        assert response == {"status": 422, "body": {"error": "invalid_input"}}
