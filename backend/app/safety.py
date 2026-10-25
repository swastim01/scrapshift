from __future__ import annotations

import re
from typing import Any

# Conservative exclusion list for a student-facing, low-voltage reuse prototype.
# A matched item is quarantined until handled through an appropriate qualified process.
UNSAFE_TERMS = (
    "battery", "lithium", "swollen", "crt", "mains", "high voltage", "high-voltage",
    "hazardous", "damaged mains", "ac adapter", "wall adapter", "unknown charge",
)


def is_hazardous_component(component: dict[str, Any]) -> bool:
    searchable = " ".join([
        str(component.get("name") or ""),
        str(component.get("component_type") or ""),
        " ".join(str(t) for t in (component.get("tags") or [])),
    ]).lower()
    normalized = re.sub(r"[_/]+", " ", searchable)
    return any(term in normalized for term in UNSAFE_TERMS)


def quarantine_note(existing_notes: str = "") -> str:
    notice = "SAFETY GATE: Automatically quarantined by SCRAPSHIFT's conservative text rules. Do not harvest, open, or use; follow qualified local hazardous e-waste procedures."
    if notice.lower() in (existing_notes or "").lower():
        return existing_notes or notice
    return f"{existing_notes.strip()}\n{notice}".strip() if existing_notes.strip() else notice
