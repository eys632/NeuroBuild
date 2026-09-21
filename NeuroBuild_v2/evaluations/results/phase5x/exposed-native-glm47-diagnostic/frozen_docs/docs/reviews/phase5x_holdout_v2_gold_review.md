# Phase 5.x holdout v2 독립 gold 검토

**Dataset 준비 검토 PASS. 모델 품질과 최종 candidate freeze는 미검증이다.**

80개 원문·gold를 독립 AI 검토자가 읽고 지원 범위, 대상의 공간·제외 범위, 현재/과거 지시,
조건·부정, 부호·단위, 조회/거절 구분, 한국어 표현을 확인했다. Pre-freeze 초안에서 선택 범위가
두 가지로 읽힐 수 있던1건을 작성자가 명확히 했고, 최종80개에는 남은 material gold 문제를
발견하지 못했다. 검토는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 사람 검수가 아니다.

- A–J 각8개, READY40 / CLARIFICATION20 / UNSUPPORTED20.
- Canonical schema/parser/scorer와 generation2 branch schema/parser/scorer 각각80/80 PASS.
- 두 reference 경로의 Domain 결과80/80 동등. 생성기의 데이터 serialization도 메모리에서 byte 동일.
- 내부 및 기존 v1 120개 대비 exact/NFC+공백 정규화 중복0개, 재사용 ID0개.
- Target·숫자를 가린 문자 scaffold의 v1 최근접 유사도 최대0.7556. 이 보조 검사는 의미적 독립성 증명이 아니다.
- 기존 v1 두 dataset hash는 유지했다. 새 v2 모델 호출·warmup·출력은 아직 없다.

Metadata hash를 고정한 실제 tokenizer의 CPU 길이 검사는 generation2 v2+출력768 기준
14B 최대3612token, MoE 최대3608token이다. 새14B classification v1은 입력1125+출력128=1253,
extraction v1은 입력1192+출력768=1960으로 모두4096 이내다. Extraction은 원문80개마다 가능한
세 decision을 모두 넣은240개 request의 최댓값이다. Root/현재 후보 prompt 작성자에게 source,
gold, case별 토큰 수를 공유하지 않았다. GPU mask, Torch 미import, offline/local tokenizer만
사용했으며 network·GPU·weight 읽기·모델 호출은0회다. 최종 transport와 측정 payload의 일치 및
새 prompt/source/template 변경 여부는 실제 candidate freeze에서 확인해야 한다.

[Dataset 문서](../hardening_v2_dataset.md), [독립 검토 증거](../../evaluations/results/phase5x/holdout-v2-preflight/independent_gold_review.json),
[CPU 증거](../../evaluations/results/phase5x/holdout-v2-preflight/independent_cpu_context_proof.json),
[dataset-only freeze](../../evaluations/hardening_v2_dataset_freeze.json)에 정확한 hash를 남겼다.

작성자·검토자는 v1 실패를 알고 있으며 과거 prompt 작성에 참여했다. 현재 후보 prompt 작성자와
입력/gold 공유를 제한한 절차적 분리이며 plaintext 접근 통제나 완전한 blind가 아니다.
동일한 좁은 작업 문법·rubric을 공유하고 고정 seed의 반복은 독립 표본이 아니다. 사람 검수표는
비어 있으며 외부 pilot 전에 실제 사람 검수가 필요하다. V2 결과를 본 뒤 조정하면 같은80개는
회귀 자료가 되고, 새로운 미노출 일반화 주장은 별도 사전 동결 자료가 필요하다.

첫v2 warmup 전 최종 후보와 실행환경을 별도로 동결해야 한다. 정식240 trial의 gate는
schema240/240, semantic최소228/240, raw READY FP0/120, unsafe accepted0/240이다.
이번 dataset freeze는 후보 채택, 추론 성공, Phase 완료, IFC 실행 또는 승인을 의미하지 않는다.
