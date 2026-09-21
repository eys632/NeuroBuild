# Phase5.x 4B-Instruct v3 진단 독립 검토

2026-09-20 KST. **FAIL — semantic92.5%, raw FP1건, unsafe accepted2건으로 gate를
충족하지 못했다.** Development40 × 1회 진단이며 gold는
**AUTO-GENERATED / NOT HUMAN VERIFIED**다. 최종 semantic JSON을 CPU에서 재생하고
metric·manifest·기존 prompt를 읽었다. 추가 inference/GPU 호출, CoT 열람,
source/schema/parser/scorer/gold 수정은 하지 않았다.

Run `20260919T222220Z-6df72f2113474c108c488c98faefca20`의
[결과](../../evaluations/results/phase5x/development-4b-v3-diagnostic/results.json)와
[manifest](../../evaluations/results/phase5x/development-4b-v3-diagnostic/manifest.json)를
보존한다. 로컬 `var/runs/<run_id>/` 원본과 archive의 두 파일은 byte 단위로 일치했다.

| 로컬 원본 | SHA256 |
|---|---|
| results.json | `5bd0a1d21b55fdcffb55274a840575a5552563c75d17ac6b315e56b4678f0310` |
| manifest.json | `9878d8eead3755474877c50a866bc6946d14a3efa1b0816ebbf5e1ec8ae6b42e` |

## 재검산 결과

저장된40개 최종 응답을 공통 parser에 다시 넣고 기존 scorer의 각 rubric 필드와
전체 `summarize` 결과가 원본과 일치함을 확인했다. Manifest에 기록된
dataset/prompt/schema/parser/client/scorer SHA도 검토 당시 파일과 모두 일치했다.
Latency는 재측정하지 않고 원래40개 측정값을 재집계했다.

| 지표 | 결과 |
|---|---:|
| JSON / schema | 각각40/40 |
| Parser accepted | 39/40 |
| Semantic rubric | 37/40, **92.5%** |
| Non-READY gold의 raw READY | 1/20 |
| Non-READY gold의 accepted READY | 0/20 |
| READY gold의 accepted READY 누락 | 0/20 |
| READY gold에서 accepted이지만 rubric 불일치 | 2/20 |
| `unsafe_accepted_ready_total` | 2/40 |
| READY gold의 SI 축/거리 일치 | 40/40 축 slot |
| Latency mean / p95 | 2.812 / 3.738초 |

FN0이나 SI40/40은 올바른 대상 선택을 보장하지 않는다. 기존 non-READY FP 지표에만
의존하면 아래 대상 보존 오류2건이 가려진다. 보완 지표는 기존 정의·분모를 그대로
유지한다. Warmup5개는 위40회 분모에 넣지 않았다. 1회 진단과 같은 seed 반복은
독립적인 일반화·안정성 증거가 아니며, 이번 평가에서 IFC 도구 실행이나 사람이
확인한 GlobalId 선택은 수행하지 않았다.

## 세 실패의 의미

**HD-B01 — 없는 방향을 양의 방향으로 추정했다.** 원문은 `X축으로 1m`이며
양/음 방향이 없다. 응답은 READY/value="1"/unit="m"이었다. 값의 철자와 단위는
원문 그대로지만 방향 근거가 없어 parser가 `UNGROUNDED_REQUIREMENT`로 거절했다.
이 차단을 모델의 CLARIFICATION 성공으로 바꾸어 세지 않는다. Raw FP1건은 유지한다.

**HD-F01/HD-F02 — 대상과 instruction에서 장소·제외 대상을 함께 잘랐다.**
F01의 원문 명사구는 `연구실 복도 쪽 낮은 장 말고 내벽 쪽 높은 장`인데 응답은
`내벽 쪽 높은 장`만 남겼다. F02는 반대로 선택해야 하는 짝이며 응답은
`복도 쪽 낮은 장`만 남겼다. 두 instruction도 그 양의 대상부터 시작해서 장소와
제외절을 누락했다. `-16`/`cm`와 dx=-0.16m, dy=0은 정확하다.

이 사례는 v6 F01의 조사 `을` 추가처럼 대상 명사구 끝의 표면적 차이만은 아니다.
공간 범위와 제외할 객체라는 실제 선택 제약이 사라졌다. 선택된 긍정 명사는
gold와 맞지만, 같은 이름의 다른 객체와 구별하는 정보가 제거되어 unsafe accepted
두 건으로 유지한다. 실제 잘못된 GlobalId가 선택·이동되었다고 주장하지는 않는다.

두 응답의 축 evidence와 선택된 target/instruction은 원문의 연속 부분이라 deterministic
lexical guard가 수용했다. 연속 span 확인은 **선택한 부분의 출처**를 확인할 뿐
그 밖의 의미 있는 절을 전부 보존했다는 증명은 아니다. 이 한계를 임의의 한국어
키워드 blacklist나 gold 변경으로 덮지 않았으며, 후속 별도 대상 확인·proposal
승인 경계도 유지한다. 나머지37건에는 현재 rubric의 불일치가 없었다.

## 재현 범위와 다음 비교

Manifest는 Qwen3-4B-Instruct-2507 revision
`cdbee75f17c01a7cc42f958dc650907174af0554`, BF16/quantization none,
vLLM0.8.5+cu118, v3, neutral `qwen3_nonthinking`, thinking=false/parser=null,
guided_json/xgrammar:no-fallback, context4096/output768/timeout60을 기록한다.
기록된 git commit은 `d05a000a7e19f2020c74b672f19dc3ba17ff6386`, **dirty=true**다.
이를 clean 실행으로 바꾸어 쓰지 않는다. 핵심 실행 파일 hash 일치 확인은 별도
증거이며 전체 worktree가 깨끗했다는 증거가 아니다. Weight identity도 manifest의
operator-supplied 범위를 넘겨 HTTP 원격 증명으로 표현하지 않는다.

Transport/truncation 오류는 없었고 최대 reported completion은143tokens다.
Schema100%가 의미 보존을 보장하지 않는다는 실패이며, output768 부족으로 설명할
근거는 없다. 14B와 비교하면 checkpoint·정밀도·sampling penalty가 함께 달라져
차이를 모델 크기나 instruction tuning 하나의 효과로 단정할 수 없다.

다음 비교는 **이미 존재하는 v4**를 같은4B/neutral profile에 적용하는 별도 전체
development 진단이다. V4는 방향 없는 unsigned 수치의 CLARIFICATION 예시와
제외·공간 범위를 보존하는 원문 cm 예시를 이미 포함한다. 현재 세 실패를 비교할
근거는 있으나 개선을 보장하지 않는다. 과거14B v4에서 관측된 한축 요청에 다른
축을 불필요하게 요구하는 오류, 명시 음의 방향을 없다고 보는 오류, 단일 가구의
두 축을 복수 변경으로 오분류하는 오류도 함께 확인해야 한다. 이 검토에서 v4를
고치거나 새 예시를 넣지 않았다. Holdout 결과로 조정하지 않고, strict metric과
실패 기록을 보존하며 development gate를 충족하기 전 다음 Phase로 진행하지 않는다.
