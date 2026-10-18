"""Ordinary public-contract tests (frozen vectors, case P2-05)."""
from delivery_app.app import handle

def test_vector_0_leading_zeros_preserved():
    assert handle({"weight_kg": "1.250", "destination": "US", "shipment_id": "00017"}) == {"shipment_id": "00017", "services": [{"id": "saver", "charge_minor": 500, "delivery_at": "2026-01-02T21:20:00Z"}, {"id": "standard", "charge_minor": 500, "delivery_at": "2026-01-02T10:00:00Z"}, {"id": "express", "charge_minor": 780, "delivery_at": "2026-01-02T07:30:00Z"}, {"id": "overnight", "charge_minor": 1150, "delivery_at": "2026-01-02T10:45:00Z"}]}

def test_vector_1_long_id_preserved():
    assert handle({"weight_kg": "0.750", "destination": "CA", "shipment_id": "000000017"}) == {"shipment_id": "000000017", "services": [{"id": "standard", "charge_minor": 460, "delivery_at": "2026-01-02T10:00:00Z"}, {"id": "saver", "charge_minor": 470, "delivery_at": "2026-01-02T21:20:00Z"}, {"id": "express", "charge_minor": 724, "delivery_at": "2026-01-02T07:30:00Z"}]}

def test_vector_2_special_character_id_422():
    assert handle({"weight_kg": "1.250", "destination": "US", "shipment_id": "0001-7"}) == {"status": 422, "body": {"error": "invalid_input"}}

def test_vector_3_alphanumeric_id_422():
    assert handle({"weight_kg": "1.250", "destination": "US", "shipment_id": "17A1"}) == {"status": 422, "body": {"error": "invalid_input"}}

