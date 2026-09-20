# NeuroBuild_v2 실행 상태

갱신: **2026-09-20 11:21 KST**. **Phase 0~5 원격 checkpoint 완료. Phase 5.x 평가 확대 진행 중이며, Internal Technical MVP는 아직 완료되지 않았다.**

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation, 1 Domain, 2 Persistence, 3 IFC Engine, 4 Explicit Workflow, 5 Local Model |
| 마지막 완료 Phase checkpoint | `d6e39c89658c552c59a8049d7198da051290bd3b`: Phase 5 commit/push 및 remote hash 일치 |
| GitHub | 공통 `v2`, SSH push 정상. 마지막 확인 checkpoint `049ab13` |
| 회귀 검증 | 전체 **314 tests PASS**, skip 0. 실제 PostgreSQL/IfcOpenShell, DISPLAY 없이 16.945초 |
| 현재 작업 | **두 단계14B 진단도93/120,rawFP11/58,unsafe6/120으로 FAIL. 기존 단일 호출113/120보다 악화되어 채택하지 않음. 공식32B AWQ는 CPU 검사와 GPU3 기동 PASS. 기존 단일 호출 계약을 유지한120×1 진단 후보를 동결하고 checkpoint 준비**. 기존1.0 parser/domain 및 gold/gate는 유지 |
| 잠정 모델 | Phase 5 범위의 **Qwen3-14B-AWQ + v3**. 확대 평가 gate 통과 전 최종 채택으로 보지 않음 |
| Hard blocker | 없음. GPU 3 가용량을 측정한 공존 실행 조건 통과 |
| Backend | `.conda`: Python 3.12.14 / PostgreSQL 17.11 / psycopg 3.2.10 / IfcOpenShell 0.8.5 |
| Model Runtime | `.conda-vllm`: Python 3.12.14 / cu118 vLLM 0.8.5 / Torch 2.6.0. MoE와14B 서버 종료. 현재32B AWQ/FP16 자체 서버만 GPU3에서 기동. TP1 / context4096 / sequence1 / fraction.60 / wholepeak25GiB / allowance0 |
| 다음 검증 | 기존120개는 노출된 regression 자료. 기존 single2.0/branch/promptv2를 유지한32B의 exposed120×1 품질 진단. 자원 계획은 [후보 문서](dense_32b_candidate.md). V2 데이터80개 동결/모델 미호출 |

## Phase 5.x 평가 상태

120개 자료를 development 40개와 holdout 80개로 고정했다. **첫 holdout80×3을 완료했으며 gate FAIL이다. 이후 같은80개는 노출된 regression/development 자료로 취급한다.** Neutral 단회40/40 후 정식119/120에서 잘못 수용한 대상1건이 발견됐다. 같은 구성의 greedy 정식development는120/120으로 통과했다. 첫 holdout은211/240,raw9/114,unsafe12/240로 실패했다. Development 성공을 일반화할 수 없다.

| 최근 development 진단 | 의미 정확도 | Raw READY 오판 | 잘못 수용된 출력 | 판단 |
|---|---:|---:|---:|---|
| 4B Instruct + v3 | **37/40 (92.5%)** | 1/20 | 2/40 | 이전 후보, gate 미충족 |
| 4B Instruct + v4 | 34/40 (85%) | 1/20 | 3/40 | gate 미충족 |
| 4B Instruct + v8 | 36/40 (90%) | 1/20 | 2/40 | gate 미충족 |
| 4B Instruct + v3 greedy | 36/40 (90%) | 1/20 | 2/40 | gate 미충족 |
| 30B-A3B Instruct AWQ + v3 | 34/40 (85%) | 1/20 | 1/40 | gate 미충족 |
| 30B-A3B Instruct AWQ + v4 | 34/40 (85%) | 1/20 | 2/40 | gate 미충족 |
| MoE + generation2/v1 | 29/40 (72.5%) | 1/20 | 0/40 | gate 미충족 |
| MoE + generation2/branch/v2 진단 | 40/40 (100%) | 0/20 | 0/40 | 단회 진단 PASS |
| 같은 구성 neutral 정식 | 119/120 (99.17%) | 0/60 | 1/120 | unsafe0 기준 FAIL |
| 같은 구성 greedy 정식 | 120/120 (100%) | 0/60 | 0/120 | Development gate PASS |

Raw READY 오판의 분모는 진단 non-READY gold20개/정식60개이고, 잘못 수용된 출력의 분모는 전체 진단40개/정식120개다. Backend가 수용한 결과에도 대상 범위 손실 등 의미 오류가 남아 있다. 40개 단회 진단은 정식 3회 평가를 대신하지 않는다. Gate는 **schema 100% / 의미 정확도 95% 이상 / raw READY 오판 0 / 잘못 수용된 출력 0**을 유지한다.

V8 run `20260919T223831Z-af6ebcd137394488a0adc427bd63edcf`는 schema 40/40, parser 39/40, FN 1/20이다. 세 프롬프트 비교 후 추가 prompt 수정을 중단했다. 기존 v3의 `legacy_greedy` profile 비교도 실패했다. 새 MoE 후보는 파일 검증과 fresh GPU3 예산 검사, 실제 기동 및 loopback 검증을 통과했다. [후보 근거](moe_instruction_candidate.md)와 고정 v3/neutral 진단 기록을 사용한다. 채택 전 실제 runtime·품질 검증이 남아 있다.

기존 14B의 prompt·sampling·thinking 실험과 4B 비교 결과는 실패를 포함해 보존했다. 상세 수치와 판단은 [Phase 5.x 보고서](reports/phase5x_report.md), [4B v3 독립 검토](reviews/phase5x_4b_v3_diagnostic_review.md), [v4 실패 및 v8 사전 검토](reviews/phase5x_4b_v4_v8_review.md)를 따른다.

V2는 아직 모델 출력 미노출 상태다. 다만 후보 파일 동결 뒤 Git의 CRLF CSV 공백 검사 출력에서 root/prompt 작성자에게 일부 입력·gold가 노출됐다. 이후 후보31개 파일 hash는 불변이며 완전 맹검으로 해석하지 않는다. [노출 이력](../evaluations/hardening_v2_input_exposure_addendum.json)을 보존했다.

## 완료 근거와 실제 한계

- Phase 1 `e68baa4`: Domain 검증. Phase 2 `18c7e21`: immutable artifact, PostgreSQL intent/CAS/idempotency 및 실제 재시작 검증.
- Phase 3 `56926a0`: IFC4 단위·회전 부모·headless mesh·불변 조건 검증. Phase 4 `dd58b59`: 대상 확인과 별도 승인, Apply V1, stale/duplicate/recovery 검증.
- Phase 5: 공개 seed 20×3에서 14B/v3 의미 정확도 60/60, READY 오판 0/33. 비교 8B는 54/60. 실제 5개 run의 결과·manifest·VRAM snapshot을 `evaluations/results/phase5/`에 보존했으며 독립 재계산을 통과했다. [Phase 5 보고서](reports/phase5_report.md), [독립 검토](reviews/phase5_final_review.md).
- Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. 반복 측정은 독립 표본이 아니며, 개발 자료와 holdout은 좁은 작업 문법을 공유한다. AI의 사전 gold 검토는 사람 검수나 맹검 평가가 아니다. [Holdout 해석과 절차](reviews/phase5x_holdout_protocol_review.md).

## 운영 상태

**GPU3만 사용한다.** 마지막14B epoch는 자신의 guard/child 소유권·시작 시각·실행 인자를 확인한 뒤 종료했다. STOPPED/child exit0/reaped/FileStore 정리를 확인했고, guard의 TERM→KILL escalation도 기록에 남겼다. 관측 최소 free24,460MiB, GPU 전체의 baseline 대비 증가 최대11,914MiB였으며 정확한 process별 peak로 해석하지 않는다. 종료 후 GPU3 free36,373MiB/used3,965MiB/util0%로 돌아왔다. 다른 사용자의 프로세스나 GPU0/1/2는 변경하지 않았다.

다음 모델 다운로드를 검토하기 위해, 평가를 마친4B의 재다운로드 가능한 weight3개를 전체 SHA/소유권/regular-file/single-link 검증 뒤 정리했다. 8,044,982,000 bytes를 확보했고 manifest/metadata/평가 결과는 보존했다. [정리 기록](../evaluations/results/phase5x/unused_4b_weight_cache_cleanup.json)으로 같은 checkpoint를 다시 받을 수 있다. 14B와 MoE weight는 아직 보존한다.

Private PostgreSQL은 `var/postgres`에 있으며, `0700` 권한의 `var/run/postgresql` 디렉터리 내 Unix socket과 peer 인증만 사용한다. TCP는 비활성이다. 마지막 디스크 확인에서 root filesystem 여유는 약 **27.6GiB (df 표시28G, 사용률99%)**다. 환경·weight·cache는 프로젝트 내부에 두고 Git에서 제외하며, 다운로드 시 **20GiB reserve**와 설치 전 디스크 확인을 유지한다.

Phase 4의 human review 상태는 아직 메모리에만 보존한다. 영속 review/queue/worker는 Phase 7 예정이며 object resolution/API/browser도 아직 구현 전이다. **RTX5090은 PREDICTED_UNVERIFIED**이며 현장 검증이 필요하다. [Runtime protocol 및 SM120 검토](model_protocol_compatibility.md). Public exposure/pilot/민감 IFC/fine-tuning은 자동 범위 밖이다.

32B 실제 기동은 AWQMarlin/FP16, weight18.1453GiB/activation profile0.76GiB였다.
초기 관측 aggregate 증가20,332MiB, minfree16,042MiB로 floor7,275MiB를 유지했다.
이는 startup부터의 GPU 전체 baseline 상대 관측이며 정확한 process peak나 품질 성공이 아니다.
자체 child의5개 TCP listener는 모두127.0.0.1이었다.
