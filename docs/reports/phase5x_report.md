# Phase 5.x — Requirement Quality Hardening

**현재 상태: 정식 development는 통과했지만 첫 holdout gate FAIL. 후보 미채택이며 Phase 5.x는 완료되지 않았다.**

현재 검증 후보는 `ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ`와 generation 2, decision-branch schema, prompt v2, `legacy_greedy` 조합이다. Development 40개 × 3회에서 schema/parser/semantic **120/120**, raw READY false positive **0/60**, unsafe accepted **0/120**을 기록했다. 직전 neutral sampling의 정식 평가는 119/120이었지만 unsafe 1건으로 실패했으며, 그 결과도 보존했다. 아직 최종 모델을 채택하지 않았다.

공통 코드 회귀는 실제 PostgreSQL·IfcOpenShell을 포함한 **290 tests PASS, skip 0**이다. 첫 holdout은 설정을 동결하고 commit `64040dee5e83a2966d7f4fff7de558e64fdc902c`를 push한 뒤 시작했다. 첫 holdout은240회 모두 완료했으나 semantic211/240, raw FP9/114, unsafe12/240으로 실패했다. 아래에 전체 결과를 보존한다.

## 목표와 고정된 평가 범위

Phase 5의 작은 seed 평가 성공이 한국어 요구사항 추출 전반에 적용되는지 확인하고, 반복 실패의 원인을 prompt·decoding·모델·출력 표현으로 나누어 검토한다. 지원 범위는 단일 가구의 상대 XY 이동이다. 명시되지 않은 방향, 미확인 조건, 복수 대상·작업, 지원 밖 변경을 실행 가능한 요구사항으로 추측해서는 안 된다.

평가 자료는 synthetic 120개이며 development 40개와 holdout 80개로 분리했다. 공개 seed 20개는 development에만 포함했다. 대상 범위와 제외 조건, 과거 지시와 현재 지시, 방향·거리·단위, 단일 대상의 두 축 이동, 부정·조건·장문·미지원 요청을 다룬다. 모든 gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이다. 원본 hash와 참조 출력 검증은 [dataset 문서](../hardening_dataset.md), [최초 freeze](../../evaluations/hardening_v1_freeze.json), [사람 검수표](../../evaluations/hardening_v1_human_review.csv)에 남겼다.

평가 기준은 schema 100%, semantic rubric 95% 이상, raw READY false positive 0건, unsafe accepted 0건이다. Raw READY는 adapter/parser가 거절하기 **전** 모델 출력을 기준으로 집계한다. Unsafe accepted에는 비실행 gold의 잘못된 READY 수용과, 실행 gold에서 대상 또는 이동값이 틀린 READY 수용을 포함한다. Backend가 위험한 raw 출력을 차단해도 모델의 false positive를 지우지 않는다. 오류·거절·실패 trial은 분모에서 제외하지 않는다.

## 구현과 architecture 판단

기존 generation 1은 모델이 숫자·단위와 그 근거 문구를 중복 생성했다. 반복 실험에서 원문 단위를 미리 환산하거나 숫자 표기를 바꾸는 계약 위반, 대상의 공간 범위·제외 조건 누락, 조건 무시, 불필요한 clarification이 관측됐다. 예를 들어 16 cm를 0.16 m로 바꾼 출력은 물리적으로 같은 거리라도 원문 literal 보존 계약을 위반한다. 이를 잘못된 기하 계산과 혼동하지 않았다.

Generation 2는 모델의 출력 표현을 원문 인용 중심으로 바꾸고, 숫자·단위·부호의 추출을 코드에 맡긴다. 공통 Application으로 전달하는 canonical 1.0 계약과 동결된 parser, gold, semantic rubric 및 gate는 유지했다.

```text
원문 + 코드가 제공한 문맥
  → LLM generation 2 JSON (raw decision 먼저 기록)
  → generation schema 검증
  → 원문 quote 검증 + literal 추출 adapter
  → canonical 1.0 schema/parser
  → SemanticRequirement
  → 후속 workflow의 대상 확인 → 별도 proposal 승인 → IFC Engine
```

Generation 2의 필드는 `schema_version`, `decision`, `target_selection_quote`, `current_instruction_quote`, `dx_evidence`, `dy_evidence`, `reason`이다. READY는 전체 대상 선택 범위와 현재 지시를 원문에서 인용하고, 적어도 한 축의 명시적 방향·거리·단위 evidence를 제공한다. Non-READY는 현재 지시와 축 evidence를 null로 두며 이유를 제공한다. Adapter는 누락된 대상을 확장하거나 전체 원문으로 대체하지 않고, 의미를 추측하거나 잘못된 출력을 자동 보정하지 않는다.

Client는 generation contract `1.0` 또는 `2.0`을 명시적으로 선택하고, 설정한 schema version이 다르면 HTTP 요청 전에 거절한다. 응답 내용으로 계약을 자동 감지하거나 다른 계약으로 fallback하지 않는다. Legacy contract의 기본 prompt/schema는 유지했다. 대상·조건의 의미적 완전성은 여전히 모델과 평가의 책임이며, 원문 인용 검증만으로 입증되지 않는다. LLM은 GlobalId·승인·IFC 변경을 만들지 않는다. 설계와 경계는 [generation 2 설계](../requirement_generation_v2_design.md)와 [독립 검토](../reviews/phase5x_generation2_review.md)를 따른다.

첫 generation 2 진단에서는 실행 gold 20개가 모두 정확했지만, non-READY 출력의 null 규칙 위반이 남았다. 새 decision-branch schema는 READY의 X만/Y만/XY와 non-READY를 네 분기로 제한한다. Prompt v2는 decision을 quote보다 먼저 배치하고 독립적인 방향 누락 예제 하나를 추가했다. 표현·schema·순서·예제가 함께 바뀌었으므로 개선을 한 요인의 효과로 단정하지 않는다. 초안의 nonempty 정규식은 xgrammar가 유효한 한국어 토큰을 거절하여 제거했고, nonempty 검사는 Backend에 유지했다.

## Development 결과와 실패 보존

완료된 development 실험은 **16개 run, 평가 960 trial, warmup 80회**다. 정식 40개 × 3회와 진단 40개 × 1회를 구분한다. 960회를 독립 표본으로 해석하지 않는다. 모든 실패 출력, manifest, 자원 관측과 run ID는 [전체 실험 목록](../phase5x_experiment_register.md)에 연결되어 있고, 명령·판단·변경 이력은 [EXECUTION_LOG](../EXECUTION_LOG.md)에 보존되어 있다.

| 주요 비교 | 평가 수 | Semantic | Raw READY FP | Unsafe accepted | 판단 |
|---|---:|---:|---:|---:|---|
| 14B AWQ / v3 / greedy | 120 | 108/120 | 3/60 | 0/120 | 실패 |
| 4B Instruct BF16 / v3 / neutral | 40 | 37/40 | 1/20 | 2/40 | 진단 실패 |
| 30B-A3B AWQ / v3, v4 / neutral | 각 40 | 각각 34/40 | 각각 1/20 | 각각 1/40, 2/40 | 두 진단 모두 실패 |
| Generation 2 / v1 / neutral | 40 | 29/40 | 1/20 | 0/40 | 진단 실패 |
| Generation 2 / v2 + branches / neutral | 40 | 40/40 | 0/20 | 0/40 | 진단 통과, 정식 검증 필요 |
| 동일 계약 / neutral 정식 | 120 | 119/120 | 0/60 | 1/120 | 안전 gate 실패 |
| 동일 계약 / greedy 정식 | 120 | 120/120 | 0/60 | 0/120 | Development gate 통과 |

Neutral 정식 run은 schema/parser 120/120이었지만 HD-F02의 세 번째 응답에서 공간 범위와 제외 대상을 빠뜨렸다. 전체 의미 정확도가 95%를 넘어도 unsafe 1건이므로 실패다. [결과](../../evaluations/results/phase5x/development-generation2-branches-moe-formal/results.json)와 [독립 검토](../reviews/phase5x_generation2_branches_formal_review.md)를 보존했다.

Greedy 정식 run `20260920T001240Z-7daf0ae403de40cfa9043c628abf9d8d`은 generation schema, adapter, canonical schema, parser, semantic 모두 120/120이며 FN 0/60, 오류 0건이다. HTTP end-to-end 평균은 **4.3943초**, p95는 **5.9109초**다. 이는 TTFT나 순수 decode 속도가 아니다. [결과](../../evaluations/results/phase5x/development-generation2-branches-moe-greedy-formal/results.json), [manifest](../../evaluations/results/phase5x/development-generation2-branches-moe-greedy-formal/manifest.json), [독립 검토](../reviews/phase5x_generation2_greedy_formal_review.md)에 근거한다.

Greedy 요청은 temperature 0과 seed 42를 명시한다. 나머지는 고정된 서버·모델 기본값을 사용하므로 모든 sampling 변수를 통제한 temperature 단독 실험은 아니다. 고정 seed와 greedy도 응답의 byte 단위 동일성이나 의미적 정답을 보장하지 않는다. 앞선 공식 sampling·thinking·영어/한국어 prompt·작은 instruction 모델 비교 실패 역시 전체 실험 목록에 남겼다.

## 테스트와 재현 근거

- **회귀:** DISPLAY/WAYLAND_DISPLAY를 해제한 headless 환경에서 290 tests PASS, skip 0, 17.329초. 실제 PostgreSQL과 IfcOpenShell을 포함한다. 이는 공통 소스의 회귀 검증이며 모델 품질 PASS를 대신하지 않는다.
- **Application 경계:** 별도 고정 generation 2 응답을 실제 PostgreSQL·IfcOpenShell workflow에 연결한 probe 4/4 PASS, 거절 경로 18개를 확인했다. 대상 확인과 proposal 승인은 분리되어 있으며 모든 probe 종료 때 V0·원본 IFC가 보존됐다. 모델 추론을 사용하지 않은 [독립 검토](../reviews/phase5x_generation2_application_review.md)다.
- **기존 결과 재생:** generation 2 구현 뒤 이전 12개 run의 640 trial을 새 평가기로 CPU 재생하여 parser 판정·오류·SI 값·semantic 및 집계가 동일함을 확인했다. 실험 목록 등록 시 저장된 trial의 metrics도 재집계했다. 새 모델 추론이나 사람의 의미 검수는 아니다.
- **Prompt/schema:** 최종 prompt의 예제 7개가 schema/adapter/canonical parser를 통과했다. xgrammar 0.1.18 CPU 검증은 유효 예제 13개를 EOS까지 수락하고 잘못된 구조 18개를 거절했다. Grammar가 허용해도 Backend가 거절해야 하는 통제 사례 5개도 확인했다.
- **Context:** 실제 tokenizer로 development 최대 입력+출력 예산 3,678 token, holdout은 내용 길이만 계산해 최대 3,683 token으로 4,096 이내다. 출력 예산은 768 token이다. 이 계산은 생성 완료나 정답을 보장하지 않는다.

정확한 소스·prompt·schema·dataset·model manifest hash, CPU 검증 파일, runtime 설정은 [첫 holdout freeze](../../evaluations/hardening_v1_generation2_branches_moe_greedy_holdout_freeze.json)에 함께 고정했다. Generation 2 도입 전 동결한 canonical parser SHA는 `a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a`, canonical schema SHA는 `dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94`이며 그대로 유지했다. Phase 5.x 초기 Unicode 숫자·축 경계 보강과 이후 검증 기록은 실행 로그에 남아 있다.

## 모델 출처, A100 실행, RTX5090 한계

후보는 공식 Qwen 원본의 **제3자 AWQ 배포본**이며 revision은 `9f41ff709102dbe73e614f9365f8280170db268e`다. [다운로드 manifest](../../runtime/models/qwen3-30b-a3b-instruct-2507-awq.json)로 파일 크기와 SHA-256을 고정했다. 배포 저장소는 Apache-2.0을 표기하지만 자체 LICENSE 파일이 없어 공식 upstream의 고정 revision LICENSE를 [license 출처 기록](../../runtime/licenses/README.md)과 함께 보존했다. 다운로드 artifact의 재현성과 quantization calibration 과정의 재현성은 다르며, 후자는 입증하지 않았다.

A100 GPU3에서 vLLM 0.8.5 + cu118의 native AWQ Marlin, FP16으로 실제 기동·평가했다. 약 30B 전체 weight가 상주하며 active 3B는 연산 참여량이다. Weight 파일은 약 15.655 GiB이고 runtime은 model weight 15.7406 GiB를 보고했다. TP 1, context 4,096, sequence 1, GPU KV block 256, eager/V0/uni, CPU offload 0으로 실행했다. GPU memory utilization과 Torch fraction은 각각 0.60이다. 이는 GPU의 60%를 독점 예약한다는 의미가 아니다.

허용 GPU3의 반복 측정, 예상 peak 24,576 MiB와 여유 7,275 MiB를 사용한 preflight 후 자신의 프로세스만 guard로 관리했다. Holdout freeze 시점까지 관측한 최소 free VRAM은 18,642 MiB였으며 free floor는 7,275 MiB다. 이는 GPU 전체 관측이며 **정확한 process별 VRAM peak는 측정하지 않았다**. 다른 사용자 프로세스나 GPU0/1/2를 변경하지 않았다. 자신의 TCP listener 5개가 모두 127.0.0.1인 snapshot도 검증했다. 최근 디스크 여유는 약 39 GiB이며 다운로드의 20 GiB reserve 정책을 유지한다. 세부 수치와 시점은 [실행 증거 및 후보 문서](../moe_instruction_candidate.md), [launch archive](../../evaluations/results/phase5x/moe-instruct-v1-launch/launch_config.json), [직전 listener 검증](../../evaluations/results/phase5x/generation2-greedy-preholdout-listeners.json)을 따른다.

**RTX5090은 PREDICTED_UNVERIFIED다.** A100의 cu118 환경을 그대로 이식할 수 있다고 주장하지 않는다. SM120의 dense linear와 MoE expert kernel 지원은 별도로 확인해야 하며, BF16 emulation fallback을 허용한 채 AWQ 메모리 예산에 맞는다고 판단해서는 안 된다. 현대 vLLM의 `structured_outputs`와 현재 legacy `guided_json`은 명시적 protocol 설정으로 분리했고 공통 Application 계약을 공유한다. Fake HTTP 검증은 RTX native kernel·VRAM·실제 grammar 실행 검증을 대체하지 않는다. [protocol 및 cross-server 근거](../model_protocol_compatibility.md)를 따른다.

## 첫 holdout — 240회 완료, gate FAIL

후보 선택은 development 결과만 사용했다. 첫 holdout은 warmup 5회 뒤 **80개 × 3회 = 240 trial**로 고정했다. READY gold 42개와 non-READY gold 38개이므로 실행 gold 분모는 126, non-READY 분모는 114다. 첫 warmup부터 holdout에 모델이 노출된 것으로 취급한다.

| 고정 gate | 필요한 결과 | 현재 판정 |
|---|---:|---|
| Schema | 240/240 | 240/240 PASS |
| Semantic rubric | 228/240 이상 | 211/240 FAIL |
| Raw READY false positive | 0/114 | 9/114 FAIL |
| Unsafe accepted | 0/240 | 12/240 FAIL |

중단되거나 일부만 완료된 평가는 INCOMPLETE이며 PASS로 처리하지 않는다. 실패 응답을 재시도해 대체하거나 분모에서 빼지 않는다. 완료 후 원본·manifest·자원 관측을 보존하고 독립적으로 집계와 실패 원인을 확인한다. 모든 gate를 만족해야 다음 채택 판단을 진행하며, 그 전까지 최종 선택과 Phase 완료를 선언하지 않는다. [사전 holdout 검토](../reviews/phase5x_holdout_protocol_review.md)와 [이번 실행 검토](../reviews/phase5x_generation2_holdout_launch_review.md)에 절차를 고정했다.

Holdout 입력과 gold는 생성·사전 품질 검토 과정에서 AI에게 공개되었고, development와 좁은 작업 문법을 공유한다. 따라서 완전한 맹검 또는 사람이 만든 독립 평가로 주장하지 않는다. 동일 seed의 세 번 반복도 독립 표본이 아니다. Holdout 결과를 본 뒤 후보를 조정하면 같은 80개는 회귀·development 자료가 되며, 새로운 미노출 일반화 주장은 별도로 사전 동결한 자료가 필요하다. 사람 검수표는 아직 미작성이고 외부 pilot 전 사람이 검수해야 한다.

이번 모델 평가는 semantic JSON 추출까지다. 실제 IFC 변경, 대상 GlobalId 확정, 사용자 대상 확인이나 proposal 승인은 수행하지 않았다. Backend의 기존 IFC·승인 경계 테스트와 모델 평가를 구분하며, Phase 11 Internal Technical MVP 완료를 의미하지 않는다.


정식 run `20260920T002629Z-6742bb1a50b44acd9e02228d83e2747d`의 schema240/240, adapter/canonical/parser231/240, semantic211/240(87.92%), raw/accepted FP9/114, 잘못된 accepted target3/126, unsafe12/240, FN6/126이다. Mean4.215746s/p955.308297s, 정식 오류는 UNGROUNDED_REQUIREMENT9건이다. Warmup5는 별도이며 통계에 합치지 않는다. [결과](../../evaluations/results/phase5x/heldout-generation2-branches-moe-greedy-formal/results.json)·manifest·resource와 [독립 검토](../reviews/phase5x_generation2_first_holdout_review.md)를 보존했다.

10개 case의29개 실패를 구분한다. 의자의 원문에 없는 공백6건과 비연속 다중 대상 합성3건은 grounding 거절이다. 방화문 이동3건, 짧은 승인 우회3건, 장문 최신 승인 우회3건은 실제 raw/accepted READY 오판이다. 대상 제외 조건 손실3건은 지원 gold에서 잘못 수용했다. 나머지8건은 CLARIFICATION/UNSUPPORTED 오분류다. 이 결과를 gold 오류나 parser의 과잉 거절만으로 설명할 수 없다.

자체 MoE guard만 정상 종료했고(exit0/FileStore 정리), GPU3는 free36,373MiB/used3,965MiB/util0%로 복귀했다. A100/RTX 최종 채택용 설정 초안은 ignored var에 미적용 상태로 남겼다. 다음 bounded 비교는 이미 보존된14B-AWQ에 같은 generation2 branch/promptv2/greedy를 적용하는 것이다. 이 표현은14B에서 아직 시험하지 않았으며 더 큰 dense 연산량이 품질을 보장한다고 주장하지 않는다. 기존120개를 노출된 regression으로 사용하고, 새 일반화 평가는 별도로 작성·검토·동결한 미사용 holdout v2에서만 수행한다. 기존 gold/gate/parser를 약화하지 않는다.
