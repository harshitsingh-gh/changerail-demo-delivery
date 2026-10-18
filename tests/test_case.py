"""Ordinary public-contract tests (frozen vectors, case P2-06)."""
from delivery_app.app import handle

def test_vector_0_empty_availability_zz():
    assert handle({"weight_kg": "1.250", "destination": "ZZ", "shipment_id": "00017"}) == {"shipment_id": "00017", "services": []}

def test_vector_1_valid_alternative_ca():
    assert handle({"weight_kg": "0.750", "destination": "CA", "shipment_id": "00017"}) == {"shipment_id": "00017", "services": [{"id": "standard", "charge_minor": 460, "delivery_at": "2026-01-02T10:00:00Z"}, {"id": "saver", "charge_minor": 470, "delivery_at": "2026-01-02T21:20:00Z"}, {"id": "express", "charge_minor": 724, "delivery_at": "2026-01-02T07:30:00Z"}]}

def test_vector_2_valid_us():
    assert handle({"weight_kg": "1.250", "destination": "US", "shipment_id": "00017"}) == {"shipment_id": "00017", "services": [{"id": "saver", "charge_minor": 500, "delivery_at": "2026-01-02T21:20:00Z"}, {"id": "standard", "charge_minor": 500, "delivery_at": "2026-01-02T10:00:00Z"}, {"id": "express", "charge_minor": 780, "delivery_at": "2026-01-02T07:30:00Z"}, {"id": "overnight", "charge_minor": 1150, "delivery_at": "2026-01-02T10:45:00Z"}]}

def test_vector_3_nonnumeric_weight_422():
    assert handle({"weight_kg": "abc", "destination": "ZZ", "shipment_id": "00017"}) == {"status": 422, "body": {"error": "invalid_input"}}

def test_vector_4_zero_weight_422():
    assert handle({"weight_kg": "0.000", "destination": "ZZ", "shipment_id": "00017"}) == {"status": 422, "body": {"error": "invalid_input"}}

