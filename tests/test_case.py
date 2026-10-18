"""Ordinary public-contract tests (frozen vectors, case P2-02)."""
from delivery_app.app import handle

def test_vector_0_full_set_tie_broken_by_id_us():
    assert handle({"weight_kg": "1.250", "destination": "US", "shipment_id": "00017"}) == {"shipment_id": "00017", "services": [{"id": "saver", "charge_minor": 500, "delivery_at": "2026-01-02T21:20:00Z"}, {"id": "standard", "charge_minor": 500, "delivery_at": "2026-01-02T10:00:00Z"}, {"id": "express", "charge_minor": 780, "delivery_at": "2026-01-02T07:30:00Z"}, {"id": "overnight", "charge_minor": 1150, "delivery_at": "2026-01-02T10:45:00Z"}]}

def test_vector_1_exact_tie_pair_mx():
    assert handle({"weight_kg": "1.250", "destination": "MX", "shipment_id": "00017"}) == {"shipment_id": "00017", "services": [{"id": "saver", "charge_minor": 500, "delivery_at": "2026-01-02T21:20:00Z"}, {"id": "standard", "charge_minor": 500, "delivery_at": "2026-01-02T10:00:00Z"}]}

def test_vector_2_charge_ordered_pair_de():
    assert handle({"weight_kg": "20.000", "destination": "DE", "shipment_id": "00017"}) == {"shipment_id": "00017", "services": [{"id": "heavy", "charge_minor": 1080, "delivery_at": "2026-01-02T09:15:00Z"}, {"id": "standard", "charge_minor": 2000, "delivery_at": "2026-01-02T10:00:00Z"}]}

def test_vector_3_nonnumeric_weight_422():
    assert handle({"weight_kg": "abc", "destination": "US", "shipment_id": "00017"}) == {"status": 422, "body": {"error": "invalid_input"}}

def test_vector_4_zero_weight_422():
    assert handle({"weight_kg": "0.000", "destination": "US", "shipment_id": "00017"}) == {"status": 422, "body": {"error": "invalid_input"}}

