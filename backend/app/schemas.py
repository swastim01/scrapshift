from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator

Category = Literal[
    "controller", "sensor", "passive", "power", "actuator", "wiring",
    "display", "enclosure", "mechanical", "other"
]
ComponentStatus = Literal["verified", "needs_testing", "unverified", "quarantined"]
Condition = Literal["excellent", "good", "fair", "unknown"]


class ComponentBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: Category = "other"
    component_type: str = Field(default="general", min_length=1, max_length=80)
    quantity: int = Field(ge=0, le=100_000)
    status: ComponentStatus = "unverified"
    condition: Condition = "unknown"
    source: str = Field(default="Unknown source", max_length=160)
    mass_g: float | None = Field(default=None, ge=0, le=1_000_000)
    estimated_new_cost: float | None = Field(default=None, ge=0, le=10_000_000)
    embodied_carbon_kg: float | None = Field(default=None, ge=0, le=1_000_000)
    factor_source: str | None = Field(default=None, max_length=300)
    voltage_v: float | None = Field(default=None, ge=0, le=1000)
    interface: str | None = Field(default=None, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=20)
    notes: str = Field(default="", max_length=2000)

    @field_validator("name", "component_type", "source")
    @classmethod
    def strip_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        return list(dict.fromkeys(t.strip().lower() for t in tags if t.strip()))[:20]


class ComponentCreate(ComponentBase):
    pass


class ComponentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    category: Category | None = None
    component_type: str | None = Field(default=None, min_length=1, max_length=80)
    quantity: int | None = Field(default=None, ge=0, le=100_000)
    status: ComponentStatus | None = None
    condition: Condition | None = None
    source: str | None = Field(default=None, max_length=160)
    mass_g: float | None = Field(default=None, ge=0, le=1_000_000)
    estimated_new_cost: float | None = Field(default=None, ge=0, le=10_000_000)
    embodied_carbon_kg: float | None = Field(default=None, ge=0, le=1_000_000)
    factor_source: str | None = Field(default=None, max_length=300)
    voltage_v: float | None = Field(default=None, ge=0, le=1000)
    interface: str | None = Field(default=None, max_length=80)
    tags: list[str] | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=2000)


class PlanRequest(BaseModel):
    template_id: str | None = None
    project_name: str | None = Field(default=None, max_length=140)
    goal: str | None = Field(default=None, max_length=1000)
    requested_features: list[str] = Field(default_factory=list, max_length=15)


class CompleteBuildRequest(BaseModel):
    project_name: str = Field(min_length=2, max_length=140)
    template_id: str = Field(min_length=1, max_length=80)
    parts_reused: list["BuildPartInput"] = Field(default_factory=list, max_length=80)
    parts_purchased: int = Field(default=0, ge=0, le=1000)
    notes: str = Field(default="", max_length=2000)
    is_demo: bool = False


class BuildPartInput(BaseModel):
    component_id: int
    quantity: int = Field(ge=1, le=100_000)


CompleteBuildRequest.model_rebuild()


class ComponentOut(ComponentBase):
    id: int
    created_at: str
    updated_at: str


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1500)

