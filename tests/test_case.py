"""Ordinary public-contract tests (frozen vectors, case P2-03)."""
from delivery_app.app import handle

def test_vector_0_exact_kg_to_g_boundary_in():
    assert handle({"weight_kg": "2.500", "destination": "US", "shipment_id": "00017"}) == {"shipment_id": "00017", "services": [{"id": "saver", "charge_minor": 575, "delivery_at": "2026-01-02T21:20:00Z"}, {"id": "standard", "charge_minor": 600, "delivery_at": "2026-01-02T10:00:00Z"}, {"id": "express", "charge_minor": 920, "delivery_at": "2026-01-02T07:30:00Z"}, {"id": "overnight", "charge_minor": 1400, "delivery_at": "2026-01-02T10:45:00Z"}]}

def test_vector_1_one_gram_over_boundary_out():
    assert handle({"weight_kg": "2.501", "destination": "US", "shipment_id": "00017"}) == {"shipment_id": "00017", "services": [{"id": "saver", "charge_minor": 575, "delivery_at": "2026-01-02T21:20:00Z"}, {"id": "standard", "charge_minor": 600, "delivery_at": "2026-01-02T10:00:00Z"}, {"id": "overnight", "charge_minor": 1400, "delivery_at": "2026-01-02T10:45:00Z"}]}

def test_vector_2_heavy_lower_boundary():
    assert handle({"weight_kg": "20.000", "destination": "US", "shipment_id": "00017"}) == {"shipment_id": "00017", "services": [{"id": "heavy", "charge_minor": 1080, "delivery_at": "2026-01-02T09:15:00Z"}, {"id": "standard", "charge_minor": 2000, "delivery_at": "2026-01-02T10:00:00Z"}]}

def test_vector_3_nonnumeric_weight_422():
    assert handle({"weight_kg": "abc", "destination": "US", "shipment_id": "00017"}) == {"status": 422, "body": {"error": "invalid_input"}}

def test_vector_4_zero_weight_422():
    assert handle({"weight_kg": "0.000", "destination": "US", "shipment_id": "00017"}) == {"status": 422, "body": {"error": "invalid_input"}}

