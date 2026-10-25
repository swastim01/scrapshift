from __future__ import annotations

from typing import Any


def calculate_impact(parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate plan/build impact from per-unit component snapshots.

    `mass_g`, `estimated_new_cost`, and `embodied_carbon_kg` are per-unit values.
    Missing values are not silently treated as verified zero-impact values.
    """
    mass_g = 0.0
    avoided_cost = 0.0
    carbon_kg = 0.0
    mass_with_factor = 0.0
    total_count = 0
    all_cost_known = True
    all_carbon_factors_known = True
    factor_sources: set[str] = set()

    for part in parts:
        qty = int(part["quantity"])
        total_count += qty
        part_mass = part.get("mass_g")
        carbon = part.get("embodied_carbon_kg")
        cost = part.get("estimated_new_cost")
        if part_mass is not None:
            mass_g += float(part_mass) * qty
            if carbon is not None:
                mass_with_factor += float(part_mass) * qty
        else:
            all_carbon_factors_known = False
        if carbon is None:
            all_carbon_factors_known = False
        if cost is not None:
            avoided_cost += float(cost) * qty
        else:
            all_cost_known = False
        if carbon is not None:
            carbon_kg += float(carbon) * qty
        if part.get("factor_source"):
            factor_sources.add(str(part["factor_source"]))

    coverage = (mass_with_factor / mass_g) if mass_g > 0 else 0.0
    return {
        "reused_component_count": total_count,
        "reused_mass_g": round(mass_g, 2),
        "avoided_purchase_cost": round(avoided_cost, 2) if all_cost_known else None,
        "estimated_co2e_kg": round(carbon_kg, 4) if all_carbon_factors_known and coverage >= 0.999 else None,
        "factor_coverage": round(coverage, 4),
        "factor_sources": sorted(factor_sources),
    }
