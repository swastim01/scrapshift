from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

init_db()
client = TestClient(app)


def test_health_and_templates():
    assert client.get("/api/health").status_code == 200
    templates = client.get("/api/templates").json()
    assert any(t["id"] == "soil-monitor" for t in templates)


def test_inventory_and_plan_flow():
    inventory = client.get("/api/inventory").json()
    assert len(inventory) >= 10
    plan = client.post("/api/plans", json={"template_id": "soil-monitor"})
    assert plan.status_code == 200
    data = plan.json()
    assert "requirements" in data
    assert "required_readiness_pct" in data


def test_quarantined_component_cannot_be_verified():
    inventory = client.get("/api/inventory", params={"status": "quarantined"}).json()
    if inventory:
        response = client.post(f"/api/inventory/{inventory[0]['id']}/verify")
        assert response.status_code == 409


def test_build_completion_records_reuse_and_decrements_stock():
    verified = client.get("/api/inventory", params={"status": "verified", "include_zero": False}).json()
    assert verified
    item = verified[0]
    before = item["quantity"]
    result = client.post("/api/builds", json={
        "project_name": "Test reuse event",
        "template_id": "soil-monitor",
        "parts_reused": [{"component_id": item["id"], "quantity": 1}],
        "parts_purchased": 0,
        "notes": "API test only",
        "is_demo": False,
    })
    assert result.status_code == 201, result.text
    data = result.json()
    assert data["reused_component_count"] == 1
    refreshed = client.get(f"/api/inventory/{item['id']}").json()
    assert refreshed["quantity"] == before - 1


def test_hazardous_component_is_auto_quarantined_and_cannot_be_released():
    created = client.post("/api/inventory", json={
        "name": "Lithium-ion battery pack",
        "category": "power",
        "component_type": "battery",
        "quantity": 1,
        "status": "verified",
        "condition": "unknown",
        "source": "test",
        "tags": ["power"],
    })
    assert created.status_code == 201
    item = created.json()
    assert item["status"] == "quarantined"
    assert "SAFETY GATE" in item["notes"]
    update = client.patch(f"/api/inventory/{item['id']}", json={"status": "verified"})
    assert update.status_code == 409


def test_health_payload_includes_demo_reset_flag():
    payload = client.get("/api/health").json()
    assert payload["service"] == "scrapshift-api"
    assert "demo_reset_enabled" in payload


def test_csv_exports_have_headers_and_download_names():
    inventory = client.get("/api/exports/inventory.csv")
    assert inventory.status_code == 200
    assert "attachment; filename=scrapshift-inventory.csv" in inventory.headers["content-disposition"]
    assert "mass_g_each" in inventory.text.splitlines()[0]

    impact = client.get("/api/exports/impact.csv")
    assert impact.status_code == 200
    assert "attachment; filename=scrapshift-impact-ledger.csv" in impact.headers["content-disposition"]
    assert "estimated_co2e_kg" in impact.text.splitlines()[0]


def test_completed_build_keeps_unknown_impact_unknown():
    created = client.post("/api/inventory", json={
        "name": "Test salvaged GPIO module",
        "category": "controller",
        "component_type": "microcontroller",
        "quantity": 1,
        "status": "verified",
        "condition": "good",
        "source": "Test fixture",
        "mass_g": None,
        "estimated_new_cost": None,
        "embodied_carbon_kg": None,
        "factor_source": None,
        "voltage_v": 3.3,
        "interface": "GPIO",
        "tags": ["test-only"],
        "notes": "Safe low-voltage part for API test.",
    })
    assert created.status_code == 201, created.text
    item = created.json()
    completed = client.post("/api/builds", json={
        "project_name": "Unknown-impact test build",
        "template_id": "soil-monitor",
        "parts_reused": [{"component_id": item["id"], "quantity": 1}],
        "parts_purchased": 0,
        "notes": "Unknown factors must stay unknown.",
        "is_demo": False,
    })
    assert completed.status_code == 201, completed.text
    impact = completed.json()["impact"]
    assert impact["reused_component_count"] == 1
    assert impact["reused_mass_g"] == 0
    assert impact["avoided_purchase_cost"] is None
    assert impact["estimated_co2e_kg"] is None


def test_build_part_snapshot_values_are_line_totals():
    created = client.post("/api/inventory", json={
        "name": "Verified test resistor module",
        "category": "passive",
        "component_type": "resistor",
        "quantity": 3,
        "status": "verified",
        "condition": "good",
        "source": "Test fixture",
        "mass_g": 2,
        "estimated_new_cost": 10,
        "embodied_carbon_kg": 0.015,
        "factor_source": "Test-only illustrative factor",
        "voltage_v": 3.3,
        "interface": "Through-hole",
        "tags": ["resistor", "test-only"],
        "notes": "Low-voltage test component.",
    })
    assert created.status_code == 201, created.text
    item = created.json()
    completed = client.post("/api/builds", json={
        "project_name": "Build line total test",
        "template_id": "soil-monitor",
        "parts_reused": [{"component_id": item["id"], "quantity": 2}],
        "parts_purchased": 0,
        "notes": "Check snapshots multiply per-unit values by quantity.",
        "is_demo": False,
    })
    assert completed.status_code == 201, completed.text
    part = next(p for p in completed.json()["parts"] if p["component_id"] == item["id"])
    assert part["mass_g"] == 4
    assert part["avoided_purchase_cost"] == 20
    assert part["estimated_co2e_kg"] == 0.03
