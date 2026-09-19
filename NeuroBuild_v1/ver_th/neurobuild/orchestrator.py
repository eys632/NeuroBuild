from __future__ import annotations

import json
from datetime import datetime

from . import config
from .agents import architecture_report, budget_report, design_report, legal_report, planning_report
from .ifc_writer import write_ifc
from .layout_engine import create_layout
from .models import GenerationResult
from .planner import parse_brief, parse_brief_update
from .rag import NeurobuildKnowledge


def generate(user_text: str, mode: str = "new", previous_result: GenerationResult | None = None) -> GenerationResult:
    created_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    if mode == "modify" and previous_result is not None:
        brief = parse_brief_update(user_text, previous_result.brief, mode=mode)
    else:
        brief = parse_brief(user_text, mode=mode)
    plan = create_layout(brief)
    kb = NeurobuildKnowledge()
    rag_query = f"{user_text} 단독주택 건축법 예산 코리빙 방 {brief.room_count}개"

    legal_hits = kb.legal_search(rag_query, top_k=5)
    design_hits = kb.design_search(rag_query, top_k=5)
    budget_hits = kb.budget_search(rag_query, top_k=5)

    reports = [
        planning_report(brief, plan),
        legal_report(brief, plan, legal_hits),
        design_report(brief, plan, design_hits),
        budget_report(brief, plan, budget_hits),
        architecture_report(brief, plan),
    ]

    ifc_text = write_ifc(plan)
    safe_title = "Neurobuild_" + "_".join(plan.title.replace("/", " ").split())
    ifc_path = config.OUTPUT_DIR / f"{safe_title}_{created_at}.ifc"
    report_path = config.OUTPUT_DIR / f"{safe_title}_{created_at}.report.json"
    ifc_path.write_text(ifc_text, encoding="utf-8")

    result = GenerationResult(
        brief=brief,
        plan=plan,
        reports=reports,
        ifc_text=ifc_text,
        ifc_path=ifc_path,
        report_path=report_path,
        created_at=created_at,
    )
    report_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return result
