from app.impact import calculate_impact
from app.matcher import generate_plan, infer_template


def test_infer_template_from_goal():
    assert infer_template("I want an indoor temperature and humidity weather station") == "weather-station"
    assert infer_template("build an automatic plant watering pump") == "plant-watering"
    assert infer_template("make a tiny lamp from old LEDs") == "desk-light"


def test_impact_calculation_multiplies_per_unit_values():
    impact = calculate_impact([
        {"quantity": 2, "mass_g": 10, "estimated_new_cost": 50, "embodied_carbon_kg": 0.1, "factor_source": "fixture"},
        {"quantity": 1, "mass_g": 5, "estimated_new_cost": 25, "embodied_carbon_kg": 0.05, "factor_source": "fixture"},
    ])
    assert impact["reused_component_count"] == 3
    assert impact["reused_mass_g"] == 25
    assert impact["avoided_purchase_cost"] == 125
    assert impact["estimated_co2e_kg"] == 0.25
    assert impact["factor_coverage"] == 1


def test_unknown_carbon_factor_is_not_reported_as_zero():
    impact = calculate_impact([
        {"quantity": 1, "mass_g": 10, "estimated_new_cost": 5, "embodied_carbon_kg": None, "factor_source": None},
    ])
    assert impact["estimated_co2e_kg"] is None
    assert impact["factor_coverage"] == 0


def test_plan_avoids_quarantined_stock_and_surfaces_testing():
    inventory = [
        {"id": 1, "name": "Arduino-compatible board", "category": "controller", "component_type": "microcontroller", "quantity": 1, "status": "verified", "condition": "good", "tags": ["arduino"], "mass_g": 20, "estimated_new_cost": 400, "embodied_carbon_kg": None, "voltage_v": 5, "interface": "GPIO"},
        {"id": 2, "name": "Capacitive soil moisture sensor", "category": "sensor", "component_type": "soil", "quantity": 1, "status": "needs_testing", "condition": "fair", "tags": ["soil", "moisture sensor"], "mass_g": 10, "estimated_new_cost": 100, "embodied_carbon_kg": None, "voltage_v": 3.3, "interface": "Analog"},
        {"id": 3, "name": "Swollen lithium battery", "category": "power", "component_type": "battery", "quantity": 10, "status": "quarantined", "condition": "unknown", "tags": ["battery"], "mass_g": 100, "estimated_new_cost": 0, "embodied_carbon_kg": 0, "voltage_v": 3.7, "interface": "Unknown"},
    ]
    plan = generate_plan("soil-monitor", inventory)
    sensor = next(item for item in plan["requirements"] if item["key"] == "sensor")
    assert sensor["status"] == "needs_testing"
    assert all(a["component_id"] != 3 for r in plan["requirements"] for a in r["allocations"])
    assert plan["can_build_now"] is False


def test_csv_formula_guard_handles_leading_whitespace():
    from app.main import _csv_safe

    assert _csv_safe("=1+1") == "'=1+1"
    assert _csv_safe("  =1+1") == "'  =1+1"
    assert _csv_safe("ordinary label") == "ordinary label"
