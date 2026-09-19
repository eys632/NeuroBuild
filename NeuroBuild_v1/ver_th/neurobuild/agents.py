from __future__ import annotations

import json

from . import config
from .llm import HFChatClient, bulletize
from .models import LayoutPlan, RagHit, TeamReport, UserBrief
from .rag import hits_to_context


def _safe_plan_context(plan: LayoutPlan) -> str:
    data = plan.to_dict().copy()
    data["walls"] = f"{len(plan.walls)} walls"
    data["openings"] = f"{len(plan.openings)} openings"
    return json.dumps(data, ensure_ascii=False, indent=2)


def planning_report(brief: UserBrief, plan: LayoutPlan) -> TeamReport:
    client = HFChatClient()
    model = config.TEAM_MODELS.planning
    fallback_summary = (
        f"CEO 요청을 {brief.occupants}명 거주, 침실 {brief.room_count}개, {brief.floors}층, "
        f"예산 {brief.budget_krw:,}원 기준으로 구조화했습니다. 현재안은 연면적 {plan.gross_area:.1f}㎡, "
        f"예상 공사비 {plan.estimated_cost_krw:,}원입니다."
    )
    actions = ["대지 주소 입력", "법무 검토 조건 확정", "면적/방/예산 수정 옵션 검토"]
    if not client.enabled:
        return TeamReport("기획팀", model, False, "fallback", fallback_summary, actions)

    system = "너는 Neurobuild 기획팀장이다. CEO의 주거 요구를 경영진 보고체로 간결하게 정리한다."
    user = f"""
브리프:
{json.dumps(brief.to_dict(), ensure_ascii=False, indent=2)}

생성된 개념 평면:
{_safe_plan_context(plan)}

보고 형식:
- 3문장 요약
- CEO에게 요청할 추가 정보 2개
"""
    resp = client.chat(model, system, user, temperature=0.25, max_tokens=700)
    if not resp.used:
        return TeamReport("기획팀", model, False, "llm_failed", fallback_summary, actions, warnings=[resp.error or "LLM 실패"])
    return TeamReport("기획팀", model, True, "ok", resp.text, bulletize(resp.text, 5), raw_model_output=resp.text)


def legal_report(brief: UserBrief, plan: LayoutPlan, hits: list[RagHit]) -> TeamReport:
    client = HFChatClient()
    model = config.TEAM_MODELS.legal
    warnings = ["대지 주소, 지번, 용도지역 정보가 없어 최종 인허가 적합성은 판정하지 않았습니다."]
    fallback_summary = (
        "법무팀은 용도지역, 건폐율, 용적률, 도로 접도, 주차, 채광 및 환기 조건을 우선 체크했습니다. "
        "현재 입력에는 대지 정보가 없어 법적 가능 여부는 조건부 검토로 표시합니다."
    )
    actions = ["대지 주소 입력", "관할 지자체 조례 확인", "도로 폭과 주차 기준 확인"]
    if not client.enabled:
        return TeamReport("법무팀", model, False, "fallback", fallback_summary, actions, hits, warnings)

    system = """
너는 한국 단독주택 개념설계를 검토하는 Neurobuild 법무팀 AI다.
법률 자문이 아니라 RAG 기반 체크리스트를 제공한다.
근거가 없는 최종 인허가 판정은 하지 말고 필요한 추가 정보를 명확히 말한다.
"""
    user = f"""
사용자 브리프:
{json.dumps(brief.to_dict(), ensure_ascii=False, indent=2)}

평면 정보:
{_safe_plan_context(plan)}

RAG 근거:
{hits_to_context(hits)}

출력:
1. 검토 결과 요약
2. 위험 항목
3. CEO가 입력해야 하는 대지 정보
"""
    resp = client.chat(model, system, user, temperature=0.15, max_tokens=900)
    if not resp.used:
        return TeamReport("법무팀", model, False, "llm_failed", fallback_summary, actions, hits, warnings + [resp.error or "LLM 실패"])
    return TeamReport("법무팀", model, True, "ok", resp.text, bulletize(resp.text, 6), hits, warnings, raw_model_output=resp.text)


def design_report(brief: UserBrief, plan: LayoutPlan, hits: list[RagHit]) -> TeamReport:
    client = HFChatClient()
    model = config.TEAM_MODELS.design
    floor_phrase = "단층" if plan.floors == 1 else f"{plan.floors}층"
    fallback_summary = (
        f"디자인팀은 개인 침실 {brief.room_count}개와 큰 공유 라운지/다이닝/키친을 분리한 코리빙형 {floor_phrase} 주택을 제안합니다. "
        "입면은 단순한 박스 매스, 수평 지붕선, 큰 창호, 스마트홈 코어를 권장합니다."
    )
    actions = ["공유 라운지 남향 창 확보", "개인실 방음 보강", "데크 또는 마당 연결 검토"]
    if not client.enabled:
        return TeamReport("디자인팀", model, False, "fallback", fallback_summary, actions, hits)

    system = "너는 Neurobuild 디자인팀 AI다. 트렌드 RAG를 바탕으로 실제 건축 콘셉트와 공간 경험을 제안한다."
    user = f"""
브리프:
{json.dumps(brief.to_dict(), ensure_ascii=False, indent=2)}

평면:
{_safe_plan_context(plan)}

트렌드 RAG:
{hits_to_context(hits)}

출력: 공간 콘셉트, 입면 콘셉트, UX 개선점, 수정 옵션을 한국어로 제안.
"""
    resp = client.chat(model, system, user, temperature=0.35, max_tokens=900)
    if not resp.used:
        return TeamReport("디자인팀", model, False, "llm_failed", fallback_summary, actions, hits, warnings=[resp.error or "LLM 실패"])
    return TeamReport("디자인팀", model, True, "ok", resp.text, bulletize(resp.text, 6), hits, raw_model_output=resp.text)


def budget_report(brief: UserBrief, plan: LayoutPlan, hits: list[RagHit]) -> TeamReport:
    client = HFChatClient()
    model = config.TEAM_MODELS.budget
    delta = brief.budget_krw - plan.estimated_cost_krw
    fallback_summary = (
        f"예산팀 추정: 연면적 {plan.gross_area:.1f}㎡ × {plan.cost_per_sqm_krw:,}원/㎡ = "
        f"{plan.estimated_cost_krw:,}원입니다. 예산 차이는 {delta:,}원이고 상태는 '{plan.budget_status}'입니다."
    )
    warnings = [] if delta >= 0 else ["예산 초과 위험: 면적 축소 또는 마감/외부공간 범위 조정이 필요합니다."]
    actions = ["예비비 7~15% 별도 확보", "습식공간 집중 배치 유지", "단순 장방형 매스로 구조비 절감"]
    if not client.enabled:
        return TeamReport("예산팀", model, False, "fallback", fallback_summary, actions, hits, warnings)

    system = "너는 Neurobuild 예산팀 AI다. 개념설계 비용을 현실적으로 추정하고 리스크와 절감안을 보고한다."
    user = f"""
브리프:
{json.dumps(brief.to_dict(), ensure_ascii=False, indent=2)}

평면/비용:
{_safe_plan_context(plan)}

예산 RAG:
{hits_to_context(hits)}

출력: 비용 요약, 예산 리스크, 절감 옵션, CEO 의사결정 항목.
"""
    resp = client.chat(model, system, user, temperature=0.2, max_tokens=900)
    if not resp.used:
        return TeamReport("예산팀", model, False, "llm_failed", fallback_summary, actions, hits, warnings + [resp.error or "LLM 실패"])
    return TeamReport("예산팀", model, True, "ok", resp.text, bulletize(resp.text, 6), hits, warnings, raw_model_output=resp.text)


def architecture_report(brief: UserBrief, plan: LayoutPlan) -> TeamReport:
    client = HFChatClient()
    model = config.TEAM_MODELS.architecture
    layout_phrase = "좌측 공용 라운지, 우측 4개 개인실, 후면 서비스 코어" if plan.floors == 1 else "1층 공용부와 상층 침실/가족 라운지"
    fallback_summary = (
        f"설계팀은 단순 장방형 매스 안에 {layout_phrase}를 배치했습니다. "
        "IFC에는 슬래브, 벽체, 문, 창, 공간, 기본 가구 프록시가 포함됩니다."
    )
    actions = ["IFC 다운로드", "수정 요청 입력", "대지 정보 입력 후 법규 재검토"]
    if not client.enabled:
        return TeamReport("설계팀", model, False, "fallback", fallback_summary, actions)

    system = "너는 BIM/IFC에 능숙한 Neurobuild 설계팀 AI다. 생성된 평면의 설계 의도와 수정 방향을 보고한다."
    user = f"""
브리프:
{json.dumps(brief.to_dict(), ensure_ascii=False, indent=2)}

생성 평면 JSON:
{_safe_plan_context(plan)}

출력: 설계 의도, IFC 포함 요소, 수정 가능한 옵션을 한국어로 보고.
"""
    resp = client.chat(model, system, user, temperature=0.25, max_tokens=900)
    if not resp.used:
        return TeamReport("설계팀", model, False, "llm_failed", fallback_summary, actions, warnings=[resp.error or "LLM 실패"])
    return TeamReport("설계팀", model, True, "ok", resp.text, bulletize(resp.text, 6), raw_model_output=resp.text)
