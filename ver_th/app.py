from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from neurobuild import config
from neurobuild.orchestrator import generate
from neurobuild.render import completion_sound_html, department_world_html, inject_global_css, metrics_html, plan_svg, report_card, viewer_html

st.set_page_config(page_title="Neurobuild", page_icon="NB", layout="wide", initial_sidebar_state="collapsed")
st.markdown(inject_global_css(), unsafe_allow_html=True)

if "result" not in st.session_state:
    st.session_state.result = None
if "brief_text" not in st.session_state:
    st.session_state.brief_text = config.DEFAULT_BRIEF
if "modify_text" not in st.session_state:
    st.session_state.modify_text = ""
if "active_team" not in st.session_state:
    st.session_state.active_team = None
if "sound_event" not in st.session_state:
    st.session_state.sound_event = 0

left, right = st.columns([0.34, 0.66], gap="large")

with left:
    components.html(department_world_html(st.session_state.active_team), height=785, scrolling=False)

with right:
    st.markdown(
        """
        <div class="brand-hero">
          <div class="brand-orbit" aria-hidden="true">
            <span class="brand-core">NB</span>
            <i class="ring ring-a"></i>
            <i class="ring ring-b"></i>
          </div>
          <div class="brand-copy">
            <div class="brand-kicker"><span></span>AI ARCHITECTURE AGENT</div>
            <div class="brand-title" data-text="Neurobuild">Neurobuild</div>
            <div class="brand-subline">
              <i></i><b>REAL-TIME BIM AGENT</b><i></i>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    token_state = "연결 준비됨" if config.USE_HF_LLM and bool(config.HF_TOKEN) else "미설정: fallback 동작"
    st.caption(f"Hugging Face LLM 상태: {token_state} · 결과 저장 폴더: {config.OUTPUT_DIR}")

    with st.form("command_form", clear_on_submit=False):
        brief_text = st.text_area(
            "새 도면 조건 입력",
            height=138,
            placeholder="예: 남자 4명이서 살기 좋은 총 비용 3억원 이하의 집...",
            key="brief_text",
        )

        modify_text = st.text_area(
            "현재 도면 수정 요청",
            height=74,
            placeholder="예: 방 하나 추가해줘. 예산은 2억원으로 낮춰줘.",
            key="modify_text",
        )

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            new_clicked = st.form_submit_button("새 도면 생성", use_container_width=True)
        with c2:
            modify_clicked = st.form_submit_button("현재 도면 수정", use_container_width=True)
        with c3:
            clear_clicked = st.form_submit_button("결과 초기화", use_container_width=True)
    if st.session_state.result is not None:
        st.caption("수정 예시: `방을 5개로 늘려줘`, `방 하나 추가해줘`, `예산을 2억원으로 낮춰줘`, `2층집으로 바꿔줘`")

    if clear_clicked:
        st.session_state.result = None
        st.session_state.active_team = None
        st.rerun()

    if new_clicked or modify_clicked:
        mode = "modify" if modify_clicked else "new"
        previous_result = st.session_state.result if mode == "modify" else None
        if mode == "modify" and previous_result is None:
            st.warning("수정할 기존 도면이 없어 새 도면 생성으로 처리합니다.")
            mode = "new"
        request_text = modify_text.strip() if mode == "modify" else brief_text.strip()
        if mode == "modify" and not request_text:
            st.warning("수정 요청을 입력해 주세요.")
            st.stop()
        if mode == "new" and not request_text:
            st.warning("새 도면 조건을 입력해 주세요.")
            st.stop()
        progress_box = st.empty()
        try:
            with st.spinner("AI 직원들이 스탠드업 회의 중입니다..."):
                for team in ["기획팀", "법무팀", "디자인팀", "예산팀", "설계팀"]:
                    st.session_state.active_team = team
                    progress_box.info(f"{team}: 작업 중")
                result = generate(request_text, mode=mode, previous_result=previous_result)
                st.session_state.result = result
                st.session_state.sound_event = time.time_ns()
                st.session_state.active_team = None
                if mode == "modify":
                    progress_box.success("수정 완료. 기존 도면 조건에 요청 변경분을 반영했습니다.")
                else:
                    progress_box.success("CEO 보고 완료. IFC/BIM 도면을 생성했습니다.")
        except Exception as exc:  # noqa: BLE001
            st.session_state.active_team = None
            progress_box.error(f"생성 실패: {exc}")

    components.html(
        completion_sound_html(st.session_state.sound_event, message="대표님, 도면 설계가 완료되었습니다."),
        height=1,
        scrolling=False,
    )

    result = st.session_state.result

    if result is None:
        st.markdown(
            """
            <div style="margin-top:16px;padding:18px;border-radius:8px;background:#111820;border:1px solid #2b3b48;color:#cbd5e1;">
              <b style="color:#5eead4;">대기 중</b>
              <div style="margin-top:7px;">요청을 입력하면 팀별 검토, 2D 평면, 3D BIM 뷰어, IFC 다운로드가 생성됩니다.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(metrics_html(result), unsafe_allow_html=True)
        tab_bim, tab_plan, tab_reports, tab_files, tab_raw = st.tabs(["BIM 뷰어", "2D 평면", "AI 직원 보고", "다운로드", "Raw JSON"])
        with tab_bim:
            components.html(viewer_html(result.plan, result.ifc_text), height=820, scrolling=False)
        with tab_plan:
            components.html(plan_svg(result.plan), height=760, scrolling=True)
            st.markdown("#### 방 구성")
            room_rows = [r.to_dict() for r in result.plan.rooms]
            st.dataframe(room_rows, use_container_width=True, hide_index=True)
        with tab_reports:
            for report in result.reports:
                st.markdown(report_card(report), unsafe_allow_html=True)
                if report.rag_hits:
                    with st.expander(f"{report.team} RAG 근거 보기"):
                        for hit in report.rag_hits:
                            st.markdown(f"**{hit.title}**  ")
                            st.caption(f"source={hit.source} · score={hit.score}")
                            st.write(hit.text)
        with tab_files:
            ifc_bytes = result.ifc_text.encode("utf-8")
            st.download_button("IFC 파일 다운로드", data=ifc_bytes, file_name=Path(result.ifc_path).name, mime="application/octet-stream", use_container_width=True)
            report_bytes = json.dumps(result.to_dict(), ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button("보고서 JSON 다운로드", data=report_bytes, file_name=Path(result.report_path).name, mime="application/json", use_container_width=True)
            st.info(f"서버에도 저장됨: {result.ifc_path}")
        with tab_raw:
            st.json(result.to_dict())
