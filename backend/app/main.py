from __future__ import annotations

import base64
import csv
import io
import json
import os
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .database import connect, init_db, row_to_dict, utc_now
from .impact import calculate_impact
from .matcher import generate_plan, infer_template
from .schemas import AssistantRequest, BuildPartInput, ComponentCreate, ComponentUpdate, CompleteBuildRequest, PlanRequest
from .safety import is_hazardous_component, quarantine_note
from .templates import TEMPLATE_BY_ID, TEMPLATES

MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SCRAPSHIFT API",
    description="Reuse-first hardware design and environmental impact ledger.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


def _component(row: sqlite3.Row | dict[str, Any] | None) -> dict[str, Any] | None:
    return row_to_dict(row)


def _get_component(conn: sqlite3.Connection, component_id: int) -> dict[str, Any]:
    result = _component(conn.execute("SELECT * FROM components WHERE id = ?", (component_id,)).fetchone())
    if not result:
        raise HTTPException(status_code=404, detail="Component not found")
    return result


def _all_components(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [_component(row) for row in conn.execute("SELECT * FROM components ORDER BY updated_at DESC, name COLLATE NOCASE")]


def _get_template_or_400(template_id: str) -> dict[str, Any]:
    template = TEMPLATE_BY_ID.get(template_id)
    if not template:
        raise HTTPException(status_code=400, detail=f"Unknown project template '{template_id}'. Choose one from /api/templates.")
    return template


def _call_chat_completions(messages: list[dict[str, Any]], *, max_tokens: int = 900, json_mode: bool = False) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Optional AI is not configured. Add OPENAI_API_KEY to backend/.env; all inventory, planning, and impact features work without it.")
    url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        response = httpx.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as exc:
        safe_text = exc.response.text[:400]
        raise HTTPException(status_code=502, detail=f"AI provider returned HTTP {exc.response.status_code}: {safe_text}") from exc
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Could not get a valid response from the configured AI provider.") from exc


def _demo_reset_enabled() -> bool:
    default = "true" if os.getenv("ENVIRONMENT", "development").lower() == "development" else "false"
    return os.getenv("SCRAPSHIFT_ENABLE_DEMO_RESET", default).lower() in {"1", "true", "yes", "on"}


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "scrapshift-api", "version": "1.0.0", "ai_configured": bool(os.getenv("OPENAI_API_KEY")), "demo_reset_enabled": _demo_reset_enabled()}


@app.get("/api/ai/status")
def ai_status() -> dict[str, Any]:
    return {
        "configured": bool(os.getenv("OPENAI_API_KEY")),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini") if os.getenv("OPENAI_API_KEY") else None,
        "message": "Vision scan and conversational AI are enabled." if os.getenv("OPENAI_API_KEY") else "AI is optional. Rule-based matching, inventory, build logging and impact accounting are available without an API key.",
    }


@app.get("/api/templates")
def list_templates() -> list[dict[str, Any]]:
    return TEMPLATES


@app.get("/api/inventory")
def list_inventory(
    search: str | None = None,
    category: str | None = None,
    status: str | None = None,
    include_zero: bool = True,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM components WHERE 1=1"
    args: list[Any] = []
    if search:
        term = f"%{search.strip()}%"
        sql += " AND (name LIKE ? OR component_type LIKE ? OR notes LIKE ? OR tags_json LIKE ?)"
        args.extend([term, term, term, term])
    if category:
        sql += " AND category = ?"
        args.append(category)
    if status:
        sql += " AND status = ?"
        args.append(status)
    if not include_zero:
        sql += " AND quantity > 0"
    sql += " ORDER BY CASE status WHEN 'verified' THEN 0 WHEN 'needs_testing' THEN 1 WHEN 'unverified' THEN 2 ELSE 3 END, name COLLATE NOCASE"
    with connect() as conn:
        return [_component(row) for row in conn.execute(sql, args)]


@app.post("/api/inventory", status_code=201)
def create_component(payload: ComponentCreate) -> dict[str, Any]:
    now = utc_now()
    values = payload.model_dump()
    if is_hazardous_component(values):
        values["status"] = "quarantined"
        values["notes"] = quarantine_note(values.get("notes", ""))
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO components
            (name, category, component_type, quantity, status, condition, source, mass_g, estimated_new_cost,
             embodied_carbon_kg, factor_source, voltage_v, interface, tags_json, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (values["name"], values["category"], values["component_type"], values["quantity"], values["status"],
             values["condition"], values["source"], values["mass_g"], values["estimated_new_cost"],
             values["embodied_carbon_kg"], values["factor_source"], values["voltage_v"], values["interface"],
             json.dumps(values["tags"]), values["notes"], now, now),
        )
        return _get_component(conn, cur.lastrowid)


def _csv_safe(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (int, float, bool)):
        return value
    text = str(value)
    # Prefix a text marker if Excel/Sheets would treat the cell as a formula.
    # Inspect after leading whitespace/control characters so those cannot bypass the guard.
    formula_probe = text.lstrip(" \t\r\n\x00")
    if formula_probe.startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


@app.get("/api/exports/inventory.csv")
def export_inventory_csv() -> Response:
    with connect() as conn:
        rows = [_component(row) for row in conn.execute("SELECT * FROM components ORDER BY name COLLATE NOCASE")]
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["id", "name", "category", "component_type", "quantity", "status", "condition", "source", "mass_g_each", "estimated_new_cost_each_inr", "embodied_carbon_kg_each", "factor_source", "voltage_v", "interface", "tags", "notes", "created_at", "updated_at"])
    for row in rows:
        writer.writerow([_csv_safe(row.get(key)) for key in ["id", "name", "category", "component_type", "quantity", "status", "condition", "source", "mass_g", "estimated_new_cost", "embodied_carbon_kg", "factor_source", "voltage_v", "interface"]] + [_csv_safe(", ".join(row.get("tags") or [])), _csv_safe(row.get("notes")), _csv_safe(row.get("created_at")), _csv_safe(row.get("updated_at"))])
    return Response(content=output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=scrapshift-inventory.csv"})


@app.get("/api/exports/impact.csv")
def export_impact_csv() -> Response:
    with connect() as conn:
        builds = [dict(row) for row in conn.execute("SELECT * FROM builds ORDER BY completed_at DESC, id DESC")]
        parts_by_build = {build["id"]: [dict(row) for row in conn.execute("SELECT * FROM build_parts WHERE build_id = ? ORDER BY id", (build["id"],))] for build in builds}
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["build_id", "project_name", "template_id", "completed_at", "is_demo", "reused_component_count", "reused_mass_g", "avoided_purchase_cost_inr_proxy", "estimated_co2e_kg", "factor_coverage", "parts_purchased_count", "component_details", "notes"])
    for build in builds:
        component_details = "; ".join(f"{p['component_name']} x{p['quantity']}" for p in parts_by_build[build["id"]])
        writer.writerow([_csv_safe(build.get("id")), _csv_safe(build.get("project_name")), _csv_safe(build.get("template_id")), _csv_safe(build.get("completed_at")), _csv_safe(bool(build.get("is_demo"))), _csv_safe(build.get("reused_component_count")), _csv_safe(build.get("reused_mass_g")), _csv_safe(build.get("avoided_purchase_cost")), _csv_safe(build.get("estimated_co2e_kg")), _csv_safe(build.get("factor_coverage")), _csv_safe(build.get("parts_purchased")), _csv_safe(component_details), _csv_safe(build.get("notes"))])
    return Response(content=output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=scrapshift-impact-ledger.csv"})


@app.get("/api/inventory/{component_id}")
def get_component(component_id: int) -> dict[str, Any]:
    with connect() as conn:
        return _get_component(conn, component_id)


@app.patch("/api/inventory/{component_id}")
def update_component(component_id: int, payload: ComponentUpdate) -> dict[str, Any]:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    if "name" in updates and (updates["name"] is None or not updates["name"].strip()):
        raise HTTPException(status_code=422, detail="Name cannot be blank")
    if "tags" in updates and updates["tags"] is not None:
        updates["tags_json"] = json.dumps(updates.pop("tags"))
    updates = {k: v for k, v in updates.items() if v is not None or k in {"mass_g", "estimated_new_cost", "embodied_carbon_kg", "factor_source", "voltage_v", "interface"}}
    with connect() as conn:
        existing = _get_component(conn, component_id)
        if existing["status"] == "quarantined" and updates.get("status", "quarantined") != "quarantined":
            raise HTTPException(status_code=409, detail="Quarantined components cannot be released through ordinary inventory editing. Use a qualified handling process and create a new safe inventory record only if appropriate.")
        merged = {**existing, **updates}
        if "tags_json" in updates:
            merged["tags"] = json.loads(updates["tags_json"] or "[]")
        if is_hazardous_component(merged):
            updates["status"] = "quarantined"
            updates["notes"] = quarantine_note(str(merged.get("notes") or ""))
        updates["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in updates)
        conn.execute(f"UPDATE components SET {assignments} WHERE id = ?", (*updates.values(), component_id))
        return _get_component(conn, component_id)


@app.delete(
    "/api/inventory/{component_id}",
    status_code=204,
    response_class=Response,
    response_model=None,
)
def delete_component(component_id: int) -> Response:
    with connect() as conn:
        _get_component(conn, component_id)
        conn.execute(
            "DELETE FROM components WHERE id = ?",
            (component_id,),
        )

    return Response(status_code=204)


@app.post("/api/inventory/{component_id}/verify")
def verify_component(component_id: int) -> dict[str, Any]:
    with connect() as conn:
        component = _get_component(conn, component_id)
        if component["status"] == "quarantined" or is_hazardous_component(component):
            if component["status"] != "quarantined":
                conn.execute("UPDATE components SET status = 'quarantined', notes = ?, updated_at = ? WHERE id = ?", (quarantine_note(component.get("notes", "")), utc_now(), component_id))
            raise HTTPException(status_code=409, detail="Safety-gated components cannot be marked verified. Follow qualified local hazardous e-waste procedures.")
        conn.execute("UPDATE components SET status = 'verified', updated_at = ? WHERE id = ?", (utc_now(), component_id))
        return _get_component(conn, component_id)


@app.post("/api/plans")
def create_plan(payload: PlanRequest) -> dict[str, Any]:
    goal = payload.goal or ""
    template_id = payload.template_id or infer_template(goal)
    _get_template_or_400(template_id)
    with connect() as conn:
        components = _all_components(conn)
        plan = generate_plan(template_id, components, payload.project_name)
        plan["goal"] = goal
        plan["requested_features"] = payload.requested_features
        plan["goal_interpretation"] = "Selected template" if payload.template_id else "Matched your description to the closest available project template. Review the selected template before building."
        return plan


@app.post("/api/builds", status_code=201)
def complete_build(payload: CompleteBuildRequest) -> dict[str, Any]:
    _get_template_or_400(payload.template_id)
    if not payload.parts_reused:
        raise HTTPException(status_code=422, detail="Log at least one salvaged component to complete a circular build.")
    aggregated: dict[int, int] = {}
    for part in payload.parts_reused:
        aggregated[part.component_id] = aggregated.get(part.component_id, 0) + part.quantity
    now = utc_now()

    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        snapshots: list[dict[str, Any]] = []
        for component_id, qty in aggregated.items():
            component = _get_component(conn, component_id)
            if component["status"] != "verified" or is_hazardous_component(component):
                raise HTTPException(status_code=409, detail=f"{component['name']} is not eligible for reuse. Verify safe low-voltage specifications and test it before logging reuse.")
            if component["quantity"] < qty:
                raise HTTPException(status_code=409, detail=f"Only {component['quantity']} unit(s) of {component['name']} remain in stock.")
            snapshots.append({
                "component_id": component_id,
                "component_name": component["name"],
                "quantity": qty,
                "mass_g": component.get("mass_g"),
                "estimated_new_cost": component.get("estimated_new_cost"),
                "embodied_carbon_kg": component.get("embodied_carbon_kg"),
                "factor_source": component.get("factor_source"),
            })

        impact = calculate_impact(snapshots)
        cur = conn.execute(
            """INSERT INTO builds
            (project_name, template_id, completed_at, reused_component_count, reused_mass_g, avoided_purchase_cost,
             estimated_co2e_kg, factor_coverage, parts_purchased, notes, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (payload.project_name.strip(), payload.template_id, now, impact["reused_component_count"], impact["reused_mass_g"],
             impact["avoided_purchase_cost"], impact["estimated_co2e_kg"], impact["factor_coverage"],
             payload.parts_purchased, payload.notes.strip(), 1 if payload.is_demo else 0),
        )
        build_id = cur.lastrowid
        for part in snapshots:
            conn.execute(
                """INSERT INTO build_parts
                (build_id, component_id, component_name, quantity, mass_g, avoided_purchase_cost, estimated_co2e_kg, factor_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    build_id,
                    part["component_id"],
                    part["component_name"],
                    part["quantity"],
                    (part["mass_g"] * part["quantity"]) if part["mass_g"] is not None else None,
                    (part["estimated_new_cost"] * part["quantity"]) if part["estimated_new_cost"] is not None else None,
                    (part["embodied_carbon_kg"] * part["quantity"]) if part["embodied_carbon_kg"] is not None else None,
                    part["factor_source"],
                ),
            )
            conn.execute("UPDATE components SET quantity = quantity - ?, updated_at = ? WHERE id = ?", (part["quantity"], now, part["component_id"]))
        conn.execute(
            """INSERT INTO reuse_events (build_id, created_at, mass_g, estimated_co2e_kg, avoided_purchase_cost, is_demo)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (build_id, now, impact["reused_mass_g"], impact["estimated_co2e_kg"], impact["avoided_purchase_cost"], 1 if payload.is_demo else 0),
        )
        result = dict(conn.execute("SELECT * FROM builds WHERE id = ?", (build_id,)).fetchone())
        result["is_demo"] = bool(result["is_demo"])
        result["parts"] = [dict(r) for r in conn.execute("SELECT * FROM build_parts WHERE build_id = ?", (build_id,))]
        result["impact"] = impact
        return result


@app.get("/api/builds")
def list_builds(limit: int = Query(default=30, ge=1, le=100), include_demo: bool = True) -> list[dict[str, Any]]:
    sql = "SELECT * FROM builds"
    args: list[Any] = []
    if not include_demo:
        sql += " WHERE is_demo = 0"
    sql += " ORDER BY completed_at DESC, id DESC LIMIT ?"
    args.append(limit)
    with connect() as conn:
        builds = []
        for row in conn.execute(sql, args):
            build = dict(row)
            build["is_demo"] = bool(build["is_demo"])
            build["parts"] = [dict(p) for p in conn.execute("SELECT * FROM build_parts WHERE build_id = ? ORDER BY id", (build["id"],))]
            builds.append(build)
        return builds


@app.get("/api/builds/{build_id}")
def get_build(build_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM builds WHERE id = ?", (build_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Build record not found")
        result = dict(row)
        result["is_demo"] = bool(result["is_demo"])
        result["parts"] = [dict(p) for p in conn.execute("SELECT * FROM build_parts WHERE build_id = ? ORDER BY id", (build_id,))]
        return result


def _build_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    inv = conn.execute(
        """SELECT COUNT(*) AS skus, COALESCE(SUM(quantity), 0) AS units,
        COALESCE(SUM(CASE WHEN status='verified' THEN quantity ELSE 0 END), 0) AS verified_units,
        COALESCE(SUM(CASE WHEN status='needs_testing' THEN quantity ELSE 0 END), 0) AS needs_testing_units,
        COALESCE(SUM(CASE WHEN status='unverified' THEN quantity ELSE 0 END), 0) AS unverified_units,
        COALESCE(SUM(CASE WHEN status='quarantined' THEN 1 ELSE 0 END), 0) AS quarantined_skus
        FROM components WHERE quantity > 0"""
    ).fetchone()
    build = conn.execute(
        """SELECT COUNT(*) AS build_count, COALESCE(SUM(reused_component_count), 0) AS reused_units,
        COALESCE(SUM(reused_mass_g), 0) AS reused_mass_g,
        COALESCE(SUM(CASE WHEN avoided_purchase_cost IS NOT NULL THEN avoided_purchase_cost ELSE 0 END), 0) AS avoided_cost,
        COALESCE(SUM(CASE WHEN estimated_co2e_kg IS NOT NULL THEN estimated_co2e_kg ELSE 0 END), 0) AS known_co2,
        SUM(CASE WHEN estimated_co2e_kg IS NULL THEN 1 ELSE 0 END) AS builds_without_full_carbon_factors,
        SUM(CASE WHEN is_demo = 0 THEN 1 ELSE 0 END) AS real_build_count,
        SUM(CASE WHEN is_demo = 1 THEN 1 ELSE 0 END) AS demo_build_count
        FROM builds"""
    ).fetchone()
    demo_only = (build["real_build_count"] or 0) == 0 and (build["demo_build_count"] or 0) > 0
    return {
        "component_skus": inv["skus"],
        "tracked_units": inv["units"],
        "verified_units": inv["verified_units"],
        "needs_testing_units": inv["needs_testing_units"],
        "unverified_units": inv["unverified_units"],
        "quarantined_skus": inv["quarantined_skus"],
        "build_count": build["build_count"] or 0,
        "real_build_count": build["real_build_count"] or 0,
        "demo_build_count": build["demo_build_count"] or 0,
        "reused_component_count": build["reused_units"] or 0,
        "reused_mass_g": round(build["reused_mass_g"] or 0, 1),
        "reused_mass_kg": round((build["reused_mass_g"] or 0) / 1000, 3),
        "avoided_purchase_cost": round(build["avoided_cost"] or 0, 2),
        "known_estimated_co2e_kg": round(build["known_co2"] or 0, 3),
        "builds_without_full_carbon_factors": build["builds_without_full_carbon_factors"] or 0,
        "demo_only": demo_only,
    }


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    with connect() as conn:
        summary = _build_summary(conn)
        inventory = _all_components(conn)
        recent = []
        for row in conn.execute("SELECT * FROM builds ORDER BY completed_at DESC, id DESC LIMIT 5"):
            item = dict(row)
            item["is_demo"] = bool(item["is_demo"])
            recent.append(item)
        by_category = [dict(r) for r in conn.execute(
            "SELECT category, COUNT(*) AS sku_count, COALESCE(SUM(quantity), 0) AS units FROM components WHERE quantity > 0 GROUP BY category ORDER BY units DESC"
        )]
        status_counts = [dict(r) for r in conn.execute(
            "SELECT status, COUNT(*) AS count FROM components WHERE quantity > 0 GROUP BY status"
        )]
        template_recommendations = sorted(TEMPLATES, key=lambda t: sum(1 for r in t["requirements"] if r.get("required", True)), reverse=False)[:4]
        # Generate live readiness for a useful, inventory-aware dashboard recommendation.
        recommended = []
        for template in template_recommendations:
            plan = generate_plan(template["id"], inventory)
            recommended.append({"id": template["id"], "name": template["name"], "category": template["category"], "summary": template["summary"], "difficulty": template["difficulty"], "duration": template["duration"], "readiness_pct": plan["required_readiness_pct"], "can_build_now": plan["can_build_now"], "color": template["color"], "icon": template["icon"]})
        recommended.sort(key=lambda x: (x["can_build_now"], x["readiness_pct"]), reverse=True)
        return {
            "summary": summary,
            "recent_builds": recent,
            "inventory_by_category": by_category,
            "inventory_status": status_counts,
            "recommended_projects": recommended,
            "ai_configured": bool(os.getenv("OPENAI_API_KEY")),
        }


@app.get("/api/impact/summary")
def impact_summary() -> dict[str, Any]:
    with connect() as conn:
        summary = _build_summary(conn)
        rows = [dict(r) for r in conn.execute("SELECT * FROM reuse_events ORDER BY created_at ASC, id ASC")]
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            month = (row["created_at"] or "")[:7] or "Unknown"
            if month not in grouped:
                grouped[month] = {"month": month, "builds": 0, "mass_g": 0.0, "avoided_cost": 0.0, "known_co2e_kg": 0.0, "demo_builds": 0}
            grouped[month]["builds"] += 1
            grouped[month]["mass_g"] += row["mass_g"] or 0
            grouped[month]["avoided_cost"] += row["avoided_purchase_cost"] or 0
            grouped[month]["known_co2e_kg"] += row["estimated_co2e_kg"] or 0
            grouped[month]["demo_builds"] += int(bool(row["is_demo"]))
        monthly = list(grouped.values())[-6:]
        for item in monthly:
            item["mass_kg"] = round(item["mass_g"] / 1000, 3)
            item["mass_g"] = round(item["mass_g"], 1)
            item["avoided_cost"] = round(item["avoided_cost"], 2)
            item["known_co2e_kg"] = round(item["known_co2e_kg"], 3)
        events = []
        for row in conn.execute("""SELECT e.*, b.project_name, b.template_id FROM reuse_events e JOIN builds b ON b.id=e.build_id ORDER BY e.created_at DESC, e.id DESC LIMIT 10"""):
            event = dict(row)
            event["is_demo"] = bool(event["is_demo"])
            events.append(event)
        return {
            "summary": summary,
            "monthly": monthly,
            "events": events,
            "methodology": {
                "mass": "Sum of recorded per-unit component masses multiplied by the quantities logged after a completed build.",
                "purchase_cost": "A counterfactual estimate using the inventory's user-entered replacement cost; it is not audited cash savings.",
                "carbon": "Shown only for builds where every reused component with known mass has an entered embodied-carbon factor. Factors must include a source; demo factors are illustrative placeholders and are not authoritative life-cycle assessments.",
            },
        }


@app.post("/api/assistant")
def assistant(payload: AssistantRequest) -> dict[str, Any]:
    message = payload.message.strip()
    with connect() as conn:
        inventory = _all_components(conn)
    if os.getenv("OPENAI_API_KEY"):
        prompt = (
            "You are SCRAPSHIFT's circular-hardware design assistant. Prioritize reuse of inventoried components. "
            "Do not claim a part is compatible unless the inventory supports it; mark uncertainties and require bench testing. "
            "Never recommend salvaging batteries, mains power supplies, CRTs, or other hazardous components. "
            "Give concise, actionable advice, distinguish facts from assumptions, and suggest an available project template when useful.\n\n"
            f"Inventory JSON: {json.dumps([{k: c.get(k) for k in ['id','name','category','component_type','quantity','status','condition','voltage_v','interface','tags']} for c in inventory], ensure_ascii=False)}"
        )
        answer = _call_chat_completions([
            {"role": "system", "content": prompt},
            {"role": "user", "content": message},
        ], max_tokens=700)
        return {"answer": answer, "mode": "ai", "suggested_template_id": infer_template(message)}

    template_id = infer_template(message)
    template = TEMPLATE_BY_ID[template_id]
    with connect() as conn:
        plan = generate_plan(template_id, _all_components(conn))
    ready_names = [item["name"] for item in plan["ready_to_reuse"]]
    testing_names = sorted({item["name"] for item in plan["parts_needing_testing"]})
    missing_names = [item["label"] for item in plan["missing"] if item["required"]]
    answer_lines = [f"The closest match is **{template['name']}** ({template['difficulty']}, {template['duration']})."]
    answer_lines.append(f"Verified stock covers {plan['required_readiness_pct']}% of its required items; inventory category coverage is {plan['inventory_coverage_pct']}%.")
    if ready_names:
        answer_lines.append("Ready-to-reuse matches: " + ", ".join(ready_names[:8]) + ".")
    if testing_names:
        answer_lines.append("Test before use: " + ", ".join(testing_names[:8]) + ".")
    if missing_names:
        answer_lines.append("Still missing: " + ", ".join(missing_names[:8]) + ".")
    answer_lines.append("Treat the match as a starting point: confirm pinout, ratings, voltage compatibility and insulation before wiring. Log impact only after the prototype has been built and tested.")
    return {"answer": "\n\n".join(answer_lines), "mode": "local-rules", "suggested_template_id": template_id, "readiness_pct": plan["required_readiness_pct"]}


@app.post("/api/ai/scan")
async def scan_component(file: UploadFile = File(...)) -> dict[str, Any]:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPG, PNG, WEBP or GIF image.")
    contents = await file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 8 MB upload limit.")
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Image recognition needs an optional vision API key. You can still add the component manually and use every core planner feature.")
    mime = file.content_type
    encoded = base64.b64encode(contents).decode("ascii")
    prompt = """Identify the most likely reusable electronic component shown in the photo. Return a single JSON object with keys: name, category, component_type, likely_voltage_v, interface, tags (array), notes, safety_flags (array), confidence (low|medium|high), verification_required (boolean). Allowed categories: controller, sensor, passive, power, actuator, wiring, display, enclosure, mechanical, other. Do not infer exact electrical ratings from appearance alone. If identity or safety is uncertain, say so and require verification. If a battery, mains-powered device, CRT, damaged power component, or hazardous item appears, flag it and do not recommend harvesting it. This is a suggestion, not an authoritative diagnosis."""
    content = _call_chat_completions([
        {"role": "system", "content": "You are a cautious electronics inventory assistant. Never present visual guesses as verified specifications."},
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
        ]},
    ], max_tokens=500, json_mode=True)
    try:
        match = re.search(r"\{.*\}", content, re.S)
        data = json.loads(match.group(0) if match else content)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="The vision model returned an invalid structured response. Try a clearer photo or enter the item manually.") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="The vision model returned the wrong response shape. Enter the component manually.")
    allowed_categories = {"controller", "sensor", "passive", "power", "actuator", "wiring", "display", "enclosure", "mechanical", "other"}
    if not isinstance(data.get("category"), str) or data["category"] not in allowed_categories:
        data["category"] = "other"
    if not isinstance(data.get("tags"), list):
        data["tags"] = []
    data["tags"] = [str(tag)[:50].strip().lower() for tag in data["tags"][:20] if str(tag).strip()]
    if not isinstance(data.get("safety_flags"), list):
        data["safety_flags"] = ["Review component safety manually"]
    data["safety_flags"] = [str(flag)[:160] for flag in data["safety_flags"][:10]]
    if not isinstance(data.get("confidence"), str) or data["confidence"] not in {"low", "medium", "high"}:
        data["confidence"] = "low"
    likely_voltage = data.get("likely_voltage_v")
    if isinstance(likely_voltage, bool) or not isinstance(likely_voltage, (int, float)) or not 0 <= likely_voltage <= 1000:
        data["likely_voltage_v"] = None
    data["name"] = str(data.get("name") or "Unidentified electronic component")[:120]
    data["component_type"] = str(data.get("component_type") or "general")[:80]
    data["interface"] = str(data.get("interface") or "")[:80]
    data["notes"] = str(data.get("notes") or "")[:1000]
    data["verification_required"] = True
    data["verified_by_human"] = False
    return data


@app.post("/api/demo/reset")
def reset_demo() -> dict[str, str]:
    """Destructive local-demo reset; disabled by default outside development mode."""
    if not _demo_reset_enabled():
        raise HTTPException(status_code=403, detail="Demo reset is disabled outside development mode.")
    with connect() as conn:
        conn.execute("DELETE FROM reuse_events")
        conn.execute("DELETE FROM build_parts")
        conn.execute("DELETE FROM builds")
        conn.execute("DELETE FROM components")
        from .database import _seed_demo
        _seed_demo(conn)
    return {"status": "reset", "message": "The illustrative SCRAPSHIFT demo workspace has been restored."}


# In a production Docker build, the Vite bundle is copied into backend/app/static.
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        candidate = (STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and STATIC_DIR.resolve() in candidate.parents:
            return FileResponse(candidate)
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not found")
