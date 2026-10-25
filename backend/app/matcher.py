from __future__ import annotations

import re
import uuid
from typing import Any

from .templates import TEMPLATE_BY_ID, TEMPLATES
from .safety import is_hazardous_component

STATUS_SCORE = {"verified": 30, "needs_testing": 12, "unverified": 5, "quarantined": -100}
CONDITION_SCORE = {"excellent": 8, "good": 6, "fair": 2, "unknown": 0}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _matches_keyword(component: dict[str, Any], keyword: str) -> bool:
    haystack = " ".join([
        component.get("name", ""), component.get("component_type", ""),
        component.get("interface") or "", " ".join(component.get("tags", [])),
    ]).lower()
    return keyword.lower() in haystack


def _score(component: dict[str, Any], requirement: dict[str, Any]) -> tuple[int, bool]:
    if component.get("status") == "quarantined" or is_hazardous_component(component) or component.get("quantity", 0) <= 0:
        return -10_000, False
    name_match = any(_matches_keyword(component, keyword) for keyword in requirement.get("keywords", []))
    category_match = component.get("category") == requirement.get("category")
    if not name_match and not category_match:
        return -10_000, False

    score = STATUS_SCORE.get(component.get("status", "unverified"), 0)
    score += CONDITION_SCORE.get(component.get("condition", "unknown"), 0)
    score += 50 if name_match else 0
    score += 20 if category_match else 0
    if requirement.get("preferred_interface") and component.get("interface"):
        score += 10 if requirement["preferred_interface"].lower() in component["interface"].lower() else -10
    if component.get("voltage_v") is None:
        score -= 1
    # Matching by category alone is still surfaced, but clearly labelled as a substitute.
    return score, name_match


def generate_plan(template_id: str, components: list[dict[str, Any]], project_name: str | None = None) -> dict[str, Any]:
    template = TEMPLATE_BY_ID.get(template_id)
    if not template:
        raise ValueError(f"Unknown project template: {template_id}")

    remaining = {int(c["id"]): int(c.get("quantity", 0)) for c in components}
    requirements: list[dict[str, Any]] = []
    reused_allocations: list[dict[str, Any]] = []
    test_allocations: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    required_total = sum(1 for r in template["requirements"] if r.get("required", True))
    ready_required = 0
    covered_required = 0

    for req in template["requirements"]:
        candidates = []
        for component in components:
            score, name_match = _score(component, req)
            if score > -10_000 and remaining.get(int(component["id"]), 0) > 0:
                candidates.append((score, name_match, component))
        candidates.sort(key=lambda x: (x[0], x[2].get("name", "")), reverse=True)

        need = int(req.get("qty", 1))
        allocated: list[dict[str, Any]] = []
        unfilled = need
        for score, name_match, component in candidates:
            component_id = int(component["id"])
            amount = min(unfilled, remaining.get(component_id, 0))
            if amount <= 0:
                continue
            substitute = not name_match
            allocation = {
                "component_id": component_id,
                "name": component["name"],
                "quantity": amount,
                "status": component["status"],
                "condition": component.get("condition", "unknown"),
                "mass_g_each": component.get("mass_g"),
                "estimated_new_cost_each": component.get("estimated_new_cost"),
                "embodied_carbon_kg_each": component.get("embodied_carbon_kg"),
                "factor_source": component.get("factor_source"),
                "substitute": substitute,
                "match_score": score,
            }
            allocated.append(allocation)
            remaining[component_id] -= amount
            unfilled -= amount
            if unfilled == 0:
                break

        chosen = allocated[0] if allocated else None
        has_any = unfilled == 0
        verified_full = has_any and all(a["status"] == "verified" for a in allocated)
        needs_test = has_any and not verified_full
        if req.get("required", True) and has_any:
            covered_required += 1
            if verified_full:
                ready_required += 1

        part = {
            "key": req["key"],
            "label": req["label"],
            "required": req.get("required", True),
            "requested_quantity": need,
            "allocated_quantity": need - unfilled,
            "allocations": allocated,
            "status": "ready" if verified_full else ("needs_testing" if needs_test else "missing"),
            "substitute": any(a["substitute"] for a in allocated),
            "missing_quantity": unfilled,
            "suggestion": None,
        }
        if unfilled > 0:
            part["suggestion"] = f"Add {unfilled} {req['label'].lower()} item(s) to your inventory or choose a compatible substitute."
            missing.append({"key": req["key"], "label": req["label"], "quantity": unfilled, "required": req.get("required", True)})
        if needs_test:
            test_allocations.extend([a for a in allocated if a["status"] != "verified"])
        reused_allocations.extend([a for a in allocated if a["status"] == "verified"])
        requirements.append(part)

    optional_ready = sum(1 for p in requirements if not p["required"] and p["status"] == "ready")
    overall_required_pct = round(ready_required / required_total * 100) if required_total else 100
    coverage_pct = round(covered_required / required_total * 100) if required_total else 100
    can_build_now = ready_required == required_total and not any(p["status"] == "needs_testing" and p["required"] for p in requirements)

    # Environmental figures are potential estimates for a plan; they are not recorded outcomes.
    reused_mass_g = sum((a.get("mass_g_each") or 0) * a["quantity"] for a in reused_allocations)
    avoided_cost = sum((a.get("estimated_new_cost_each") or 0) * a["quantity"] for a in reused_allocations)
    co2_values = [a for a in reused_allocations if a.get("embodied_carbon_kg_each") is not None and a.get("mass_g_each") is not None]
    estimated_co2 = sum(a["embodied_carbon_kg_each"] * a["quantity"] for a in co2_values)
    carbon_coverage = (sum(a["mass_g_each"] * a["quantity"] for a in co2_values) / reused_mass_g) if reused_mass_g else 0
    complete_carbon_factors = bool(reused_allocations) and all(a.get("embodied_carbon_kg_each") is not None and a.get("mass_g_each") is not None for a in reused_allocations)

    steps = [
        "Inspect salvaged parts for cracks, corrosion, damaged insulation, and missing labels.",
        "Test every part marked 'Needs testing' before connecting it to the prototype.",
        "Use a current-limiting resistor for LEDs and verify all voltage and pinout requirements.",
        "Build and validate the prototype on a breadboard before permanent assembly.",
        "Log the components actually reused only after the build works; record new purchases separately.",
    ]

    return {
        "plan_id": str(uuid.uuid4()),
        "template_id": template["id"],
        "project_name": project_name.strip() if project_name and project_name.strip() else template["name"],
        "template_name": template["name"],
        "summary": template["summary"],
        "difficulty": template["difficulty"],
        "duration": template["duration"],
        "impact": template["impact"],
        "requirements": requirements,
        "missing": missing,
        "parts_needing_testing": test_allocations,
        "ready_to_reuse": reused_allocations,
        "required_readiness_pct": overall_required_pct,
        "inventory_coverage_pct": coverage_pct,
        "can_build_now": can_build_now,
        "required_items_total": required_total,
        "required_items_ready": ready_required,
        "required_items_covered": covered_required,
        "optional_items_ready": optional_ready,
        "estimated_reuse_mass_g": round(reused_mass_g, 1),
        "estimated_avoided_purchase_cost": round(avoided_cost, 2),
        "estimated_avoided_co2e_kg": round(estimated_co2, 4) if complete_carbon_factors else None,
        "carbon_factor_coverage_pct": round(carbon_coverage * 100),
        "impact_estimate_note": "Plan-stage estimates only. Actual impacts are logged only after the build is completed. Carbon values depend on user-entered factors and are not independently verified.",
        "build_steps": steps,
    }


def infer_template(goal: str | None) -> str:
    text = (goal or "").lower()
    keyword_map = [
        (("water", "watering", "pump", "irrigation"), "plant-watering"),
        (("weather", "temperature", "humidity", "air quality", "climate"), "weather-station"),
        (("motion", "alarm", "presence", "pir", "security"), "motion-alarm"),
        (("light", "lamp", "led", "desk"), "desk-light"),
        (("soil", "plant", "moisture", "garden"), "soil-monitor"),
    ]
    for keywords, template_id in keyword_map:
        if any(word in text for word in keywords):
            return template_id
    return "soil-monitor"
