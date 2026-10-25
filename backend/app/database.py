from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=False)
except ImportError:
    pass

DEFAULT_DB = BASE_DIR / "data" / "scrapshift.db"
DB_PATH = Path(os.getenv("SCRAPSHIFT_DB_PATH", str(DEFAULT_DB)))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    if "tags_json" in result:
        result["tags"] = json.loads(result.pop("tags_json") or "[]")
    elif "tags" in result and isinstance(result["tags"], str):
        result["tags"] = json.loads(result["tags"] or "[]")
    return result


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'other',
                component_type TEXT NOT NULL DEFAULT 'general',
                quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                status TEXT NOT NULL DEFAULT 'unverified',
                condition TEXT NOT NULL DEFAULT 'unknown',
                source TEXT NOT NULL DEFAULT 'Unknown source',
                mass_g REAL,
                estimated_new_cost REAL,
                embodied_carbon_kg REAL,
                factor_source TEXT,
                voltage_v REAL,
                interface TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_components_category ON components(category);
            CREATE INDEX IF NOT EXISTS idx_components_status ON components(status);
            CREATE INDEX IF NOT EXISTS idx_components_name ON components(name);

            CREATE TABLE IF NOT EXISTS builds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                template_id TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                reused_component_count INTEGER NOT NULL DEFAULT 0,
                reused_mass_g REAL NOT NULL DEFAULT 0,
                avoided_purchase_cost REAL,
                estimated_co2e_kg REAL,
                factor_coverage REAL NOT NULL DEFAULT 0,
                parts_purchased INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                is_demo INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS build_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                build_id INTEGER NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
                component_id INTEGER REFERENCES components(id) ON DELETE SET NULL,
                component_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                mass_g REAL,
                avoided_purchase_cost REAL,
                estimated_co2e_kg REAL,
                factor_source TEXT
            );

            CREATE TABLE IF NOT EXISTS reuse_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                build_id INTEGER NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL DEFAULT 'completed_build',
                created_at TEXT NOT NULL,
                mass_g REAL NOT NULL DEFAULT 0,
                estimated_co2e_kg REAL,
                avoided_purchase_cost REAL,
                is_demo INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM components").fetchone()[0]
        if count == 0:
            _seed_demo(conn)


def _seed_demo(conn: sqlite3.Connection) -> None:
    now = utc_now()
    # These are deliberately labelled illustrative demo factors, not authoritative LCAs.
    items = [
        ("Arduino-compatible microcontroller board", "controller", "microcontroller", 2, "verified", "good", "Old student project", 25.0, 650.0, 0.35, "Demo-only illustrative estimate; replace with a cited LCA factor", 5.0, "USB / GPIO", ["arduino", "microcontroller", "5v", "gpio"], "Known-good low-voltage board. Test I/O before each build."),
        ("ESP32 development board", "controller", "microcontroller", 1, "verified", "good", "Donated parts box", 12.0, 500.0, 0.20, "Demo-only illustrative estimate; replace with a cited LCA factor", 5.0, "USB / GPIO / Wi-Fi", ["esp32", "microcontroller", "3.3v", "wifi"], "USB-powered development board."),
        ("Capacitive soil moisture sensor", "sensor", "soil_moisture", 2, "verified", "good", "Old plant monitor", 12.0, 180.0, 0.08, "Demo-only illustrative estimate; replace with a cited LCA factor", 3.3, "Analog", ["soil", "moisture sensor", "analog"], "Bench-tested for the demo; readings need calibration in actual soil."),
        ("DHT22 temperature / humidity sensor", "sensor", "environmental", 2, "verified", "good", "Parts drawer", 4.0, 250.0, 0.07, "Demo-only illustrative estimate; replace with a cited LCA factor", 3.3, "Digital", ["dht22", "temperature", "humidity", "environment"], "Verify pinout and logic-level compatibility."),
        ("PIR motion sensor module", "sensor", "motion", 1, "needs_testing", "fair", "Broken desk alarm", 8.0, 120.0, None, None, 5.0, "Digital", ["pir", "motion sensor", "presence"], "Needs bench test before use."),
        ("Half-size solderless breadboard", "passive", "prototyping_board", 3, "verified", "good", "Lab surplus", 8.0, 90.0, 0.03, "Demo-only illustrative estimate; replace with a cited LCA factor", None, "Breadboard", ["breadboard", "prototype board"], "Inspect rails and clips before use."),
        ("Jumper wire kit (male-to-male)", "wiring", "jumper_wires", 5, "verified", "good", "Student project leftovers", 5.0, 70.0, 0.02, "Demo-only illustrative estimate; replace with a cited LCA factor", None, "Dupont", ["jumper", "wire", "dupont"], "Reuse only wires with intact insulation and connectors."),
        ("0.96-inch OLED display module", "display", "display", 1, "needs_testing", "good", "Old sensor kit", 4.0, 220.0, None, None, 3.3, "I2C", ["oled", "display", "i2c"], "Test pixels and confirm I2C address before reuse."),
        ("LED assortment", "display", "indicator", 4, "verified", "good", "Electronics lab leftovers", 2.0, 40.0, 0.01, "Demo-only illustrative estimate; replace with a cited LCA factor", None, "Through-hole", ["led", "indicator", "light"], "Use a suitable current-limiting resistor."),
        ("Regulated USB 5V adapter", "power", "regulated_supply", 1, "verified", "good", "Retired phone accessory", 45.0, 250.0, 0.20, "Demo-only illustrative estimate; replace with a cited LCA factor", 5.0, "USB-A", ["usb 5v", "5v supply", "regulated 5v"], "Use only if casing, cable, and rating are intact; never open mains adapters."),
        ("Mini 5V water pump", "actuator", "pump", 1, "needs_testing", "fair", "Old science project", 35.0, 160.0, None, None, 5.0, "2-wire DC", ["5v pump", "mini pump", "water pump"], "Test away from electronics; use a suitable driver and avoid dry-running."),
        ("Logic-level MOSFET driver module", "passive", "driver", 1, "unverified", "good", "Unlabelled kit box", 6.0, 80.0, None, None, 5.0, "GPIO / screw terminal", ["mosfet", "driver", "transistor"], "Identify pinout and ratings before use."),
        ("USB cable with intact insulation", "wiring", "power_cable", 4, "verified", "good", "Cable drawer", 18.0, 100.0, 0.04, "Demo-only illustrative estimate; replace with a cited LCA factor", 5.0, "USB", ["usb cable", "cable", "wire"], "Inspect for fraying and verify required connector."),
        ("5V LED strip segment", "display", "led_strip", 2, "verified", "good", "Decorative lighting offcut", 15.0, 130.0, 0.05, "Demo-only illustrative estimate; replace with a cited LCA factor", 5.0, "2-wire DC", ["led strip", "led module", "led"], "Use regulated low-voltage power; check current draw."),
        ("Reusable plastic project enclosure", "enclosure", "housing", 2, "verified", "fair", "Retired prototype", 28.0, 90.0, 0.04, "Demo-only illustrative estimate; replace with a cited LCA factor", None, "Mechanical", ["enclosure", "case", "housing"], "Check fit and sharp edges before reuse."),
        ("Resistor and transistor assortment", "passive", "passive_components", 2, "needs_testing", "unknown", "Mixed components tray", 8.0, 60.0, None, None, None, "Through-hole", ["resistor", "transistor", "passive", "driver"], "Mixed assortment: identify values and test before use."),
        ("Swollen lithium-ion battery pack", "power", "battery", 0, "quarantined", "unknown", "Safety quarantine", 40.0, None, None, None, None, "Unknown", ["battery", "lithium-ion", "hazardous"], "DO NOT USE OR DISASSEMBLE. Follow local hazardous e-waste procedures."),
    ]
    ids: dict[str, int] = {}
    for item in items:
        cur = conn.execute(
            """INSERT INTO components
            (name, category, component_type, quantity, status, condition, source, mass_g, estimated_new_cost,
             embodied_carbon_kg, factor_source, voltage_v, interface, tags_json, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (*item[:13], json.dumps(item[13]), item[14], now, now),
        )
        ids[item[0]] = cur.lastrowid

    demo_date = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
    # A visible demo build provides judges a sample of the completed-reuse workflow.
    chosen = [
        ("Arduino-compatible microcontroller board", 1),
        ("Capacitive soil moisture sensor", 1),
        ("Half-size solderless breadboard", 1),
        ("Jumper wire kit (male-to-male)", 1),
        ("LED assortment", 1),
    ]
    reused_mass = 0.0
    avoided_cost = 0.0
    co2 = 0.0
    all_carbon_factors_known = True
    build_cur = conn.execute(
        """INSERT INTO builds
        (project_name, template_id, completed_at, reused_component_count, reused_mass_g, avoided_purchase_cost,
         estimated_co2e_kg, factor_coverage, parts_purchased, notes, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        ("Demo build · Soil moisture monitor", "soil-monitor", demo_date, len(chosen), 0, 0, 0, 1, 1,
         "Illustrative seed record to demonstrate the completed-build and impact ledger flows."),
    )
    build_id = build_cur.lastrowid
    for name, qty in chosen:
        component = conn.execute("SELECT * FROM components WHERE id = ?", (ids[name],)).fetchone()
        mass = (component["mass_g"] or 0) * qty
        cost = (component["estimated_new_cost"] or 0) * qty
        carbon = component["embodied_carbon_kg"]
        carbon_total = (carbon * qty) if carbon is not None else None
        if carbon_total is None:
            all_carbon_factors_known = False
        else:
            co2 += carbon_total
        reused_mass += mass
        avoided_cost += cost
        conn.execute(
            """INSERT INTO build_parts
            (build_id, component_id, component_name, quantity, mass_g, avoided_purchase_cost, estimated_co2e_kg, factor_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (build_id, component["id"], name, qty, mass, cost, carbon_total, component["factor_source"]),
        )
        # The demo build is reflected in remaining stock to keep inventory consistent.
        conn.execute("UPDATE components SET quantity = quantity - ?, updated_at = ? WHERE id = ?", (qty, now, component["id"]))
    known_co2 = co2 if all_carbon_factors_known else None
    conn.execute(
        """UPDATE builds SET reused_mass_g = ?, avoided_purchase_cost = ?, estimated_co2e_kg = ?, factor_coverage = ? WHERE id = ?""",
        (reused_mass, avoided_cost, known_co2, 1.0 if all_carbon_factors_known else 0.8, build_id),
    )
    conn.execute(
        """INSERT INTO reuse_events (build_id, created_at, mass_g, estimated_co2e_kg, avoided_purchase_cost, is_demo)
        VALUES (?, ?, ?, ?, ?, 1)""",
        (build_id, demo_date, reused_mass, known_co2, avoided_cost),
    )
