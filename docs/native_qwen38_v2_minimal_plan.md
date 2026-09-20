# Native Qwen3.8 V2 최소 평가 사전 계획

상태: **PLANNED_NOT_EVALUATED**. 사용자 checkpoint `704e9f6` 뒤의 다음 품질 검증이다.
현재 모델은 노출120개 단회1차 gate와125개 저장 응답 독립 재생을 통과했다. 완료 평가를 반복하지 않는다.
D036과 [실행 횟수 변경 기록](../evaluations/hardening_v2_minimal_execution_addendum.json)이 과거80×3 계획을
80×1로 명시적으로 대체한다. 원래 dataset freeze와9개 파일, 입력 노출 addendum는 수정하지 않는다.

## 고정 실행 범위

`requirement_hardening_v2_holdout.jsonl`의 기존80개를 원래 순서로1회 실행한다. Manifest split은heldout이다.
처음5개 warmup을 별도로 실행하므로 총85호출이며 첫 warmup부터 최초 모델 노출이다. 사전 일부 미리보기,
선별 재시도, 다른 run의 성공 응답 합치기, 완료125개 재평가를 하지 않는다. Gold READY40/non-READY40이다.
Schema80/80, semantic≥76/80(95%), raw READY FP0/40, unsafe accepted READY0/80을 요구한다.
Raw decision은80/80 관측되어야 PASS를 선언한다. 오류·잘림·unknown은 분모에 남고 미완료는PASS가 아니다.
이전3회 계획의 완료나 모델 반복 출력 동일성을 주장하지 않는다. 추가 반복은 실제로 남은 불확실성이 있을 때만
그 목적·최소 사례·횟수를 새로 정한다. 명백한 gate 실패를 같은 설정으로 무조건 반복하지 않는다.

후보는 단회 진단과 동일하다: ggml-org/Qwen3.8-27B-GGUF의revision
`efbb3b1f70a21d97fd4495240648405f7228554f`, Q4_K_M, llama.cpp
`f072b103714dfa1eee531f80b24512faf38e3dd2`, raw-Unicode variant.
Single generation2.0, 기존promptv2·decision-branch schema·canonical parser·quote adapter·scorer를 유지한다.
Native JSON-schema/GBNF, qwen38_nonthinking_llama_cpp, T0.7/P0.8/K20/minP0/seed42,
presence0/frequency0/repeat1/window0, samplers temperature→top_k→top_p→min_p,
thinkingfalse/deepseek, max_tokens768/timeout120초/concurrency1/retry0을 고정한다.
GPU3/internalCUDA0,context4096/sequence1,batch64/ubatch64,F16KV,flash/graphs/fit OFF다.

## 실행 전 최소 확인과 증거 재사용

완료한 CPU grammar/template/tokenizer/context, startup contract, 공개 응답과 최대 문맥 resource 검사를
처음부터 반복하지 않는다. Epoch4의 실제 PASS 증거를 역사적 검증으로 연결하고 새 process의 측정이라고 쓰지 않는다.
Source/build/GGUF/template·추론 인자의 동일성을 확인한 뒤 현재 epoch에는 freshGPU3 free/util 사전 검사,
own UID/PID/startticks/전체argv/device/loopback·guard와 health readiness만 확인한다. 공개 생성이나 resource
모델 호출은 추가하지 않는다. 실행 전후 같은 own epoch와 변하지 않은 source/prompt/schema를 확인한다.

예상 전체 peak28,672MiB와 실제 fresh margin을 기존 guard가 적용한다. 다른 사용자 process와 GPU0/1/2는
변경하지 않는다. 새 epoch의 사전 시간 한도는3600초이며85×30초+600초=3150초를 보수적 운영 예산으로 둔다.
단회 평균5.215초/p95 5.811초와 과거 최대 문맥25.678초를 참고하되30초를 엄밀 상한이나 완료 보장으로 쓰지 않는다.
실행 전 guard.elapsed_seconds 기준 잔여≥3150초를 확인한다. 부족하면 평가를 시작하지 않으며 실행 중 한도를 늘리지 않는다.
평가 후 증거를 보존하고 NeuroBuild가 시작한 모델 서버만 종료해 GPU3 반환을 확인한다.

첫 요청 전에 plan/addendum/dataset·9파일 hash/source/설정·현재epoch와 역사적 runtime 증거를 candidate freeze에
묶어 commit·push·remote 일치를 확인한다. V2 본문은 실행 준비 중 파싱하거나 출력하지 않고 hash-only로 검증한다.
실행 후 final 응답과 고정 source snapshot을 사용한 독립 재생으로 전체80+5,단계별 결과·분모·metrics를 확인한다.
원래 dataset/gold/scorer/gate를 모델 출력에 맞추어 수정하지 않는다. 별도 reasoning 본문은 보존하지 않는다.

## 한계와 후속 판단

V2는 모델 출력 미관측 자료지만 root가 일부 입력/gold를 본 이력을 그대로 공개한다. 완전 맹검이 아니다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. HF tokenizer 동등성19/20 FAIL과 raw reference20/20을
구분하고 입력/출력 NFC 보정을 하지 않는다. RTX5090은 **PREDICTED_UNVERIFIED**다.
통과하면 이 고정 조합의 내부 후보 채택과 Phase6 진입을 검토한다. 실제 IFC 변경·별도 승인·불변성 검증은
후속 Phase에서 수행한다. 실패하면 원본 결과와 실패를 보존하고 원인을 검토한다.
Batch/flash/graphs/cache/throughput 등 비필수 runtime 최적화는 future optimization이며 품질 gate 조건이 아니다.
