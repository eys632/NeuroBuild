from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class UserBrief:
    raw_text: str
    mode: str = "new"
    occupants: int = 4
    budget_krw: int = 300_000_000
    room_count: int = 4
    floors: int = 1
    living_room_preference: str = "large"
    style_keywords: List[str] = field(default_factory=lambda: ["미래지향", "코리빙", "단층", "가성비"])
    location_hint: Optional[str] = None
    special_requirements: List[str] = field(default_factory=list)
    confidence: float = 0.72
    source: str = "regex"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Room:
    id: str
    name: str
    kind: str
    x: float
    y: float
    width: float
    depth: float
    floor: int = 1

    @property
    def area(self) -> float:
        return round(self.width * self.depth, 2)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["area"] = self.area
        return data


@dataclass
class Wall:
    name: str
    x1: float
    y1: float
    x2: float
    y2: float
    thickness: float = 0.18
    height: float = 2.8
    wall_type: str = "internal"
    floor: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Opening:
    name: str
    kind: str
    x: float
    y: float
    width: float
    height: float
    sill_height: float
    rotation_deg: float = 0.0
    floor: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LayoutPlan:
    title: str
    width: float
    depth: float
    floors: int
    rooms: List[Room]
    walls: List[Wall]
    openings: List[Opening]
    gross_area: float
    net_room_area: float
    estimated_cost_krw: int
    cost_per_sqm_krw: int
    budget_status: str
    notes: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "width": self.width,
            "depth": self.depth,
            "floors": self.floors,
            "rooms": [r.to_dict() for r in self.rooms],
            "walls": [w.to_dict() for w in self.walls],
            "openings": [o.to_dict() for o in self.openings],
            "gross_area": self.gross_area,
            "net_room_area": self.net_room_area,
            "estimated_cost_krw": self.estimated_cost_krw,
            "cost_per_sqm_krw": self.cost_per_sqm_krw,
            "budget_status": self.budget_status,
            "notes": self.notes,
            "metrics": self.metrics,
        }


@dataclass
class RagHit:
    source: str
    title: str
    text: str
    score: float
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TeamReport:
    team: str
    model: str
    used_llm: bool
    status: str
    summary: str
    action_items: List[str] = field(default_factory=list)
    rag_hits: List[RagHit] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    raw_model_output: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["rag_hits"] = [hit.to_dict() for hit in self.rag_hits]
        return data


@dataclass
class GenerationResult:
    brief: UserBrief
    plan: LayoutPlan
    reports: List[TeamReport]
    ifc_text: str
    ifc_path: Path
    report_path: Path
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brief": self.brief.to_dict(),
            "plan": self.plan.to_dict(),
            "reports": [r.to_dict() for r in self.reports],
            "ifc_path": str(self.ifc_path),
            "report_path": str(self.report_path),
            "created_at": self.created_at,
        }
