# Native logical batch 2 / physical ubatch 1 독립 검토

2026-09-20. **제한된 새 startup 후보로 적합**하다. 실제 성공·전체 peak 측정·품질 통과를 뜻하지 않는다. 이 검토자는 production/native source를 수정하거나 GPU·HTTP·모델을 실행하지 않았고 데이터셋 본문도 읽지 않았다.

## 실패와 변경의 직접 연결

원래 batch1 epoch2의 보존된 진단은 `GGML_ASSERT_FAILED`, `llama-context.cpp:1734`를 기록한다. Report SHA는 `b9a5108da00da048605b1e3b06ec4dadadee65501ac8396c17cde6844e8d21d3`다. SIGABRT(-6), STOPPED/reaped, stderr347bytes/4lines, overflow0, EOF/thread 종료·진단완료를 확인했다. Raw stderr/assertion 내용은 저장되지 않았다.

고정 llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2`의 해당 줄은 `n_tokens_all <= cparams.n_batch` 검사다. Server load는 `common_context_can_seq_rm`을 호출하고, rollback0 경로는 논리 토큰2개를 한 번의 decode에 넣는다. 따라서 batch1은 그 검사와 충돌한다. 일반 warmup은 이미 logical batch로 clamp하므로 warmup을 비활성화하는 것으로 이 별도 검사를 제거할 수 없다.

적용된 `scripts/llama_server.py` SHA `a0d0c3c82d3a9e28b51c0c53e9b69c214e1a00e29de4160a40b59227091f74d8`와 tests SHA `29a1d7caf22f62d3e346dc9567460c67c5c25a064745c753ef500592fc79cced`는 사전 제안 patch의 candidate와 일치한다. 변경은 exact-int `batch_size=2`, `ubatch_size=1` 설정·argv·보고와 경계 테스트다. 다른 batch값/bool/float/string/null은 거절하며, 장치·source/binary·sampling·요청 계약을 바꾸지 않는다. 테스트 실행 결과는 소유자/parent의 별도 기록을 따른다.

## 전체 자원 추정 영향

- Context 초기화는 `n_ubatch=min(n_batch, requested_ubatch)`이므로 여전히1이다. Hybrid memory는 논리2개를 순차 single-token ubatch로 분리한다.
- Scheduler reserve의 token 수는 `min(ctx, n_ubatch)=1`이고 physical graph의 output 수 역시1이다. 두 토큰을 동시에 처리하는2배 graph/attention allocation으로 바뀌지 않는다.
- Weight, context4096/sequence1의256MiB K/V, recurrent state/rollback0, VMM·graph-off·flash-off·all-layers/fit-off 조건은 동일하다.
- 논리 output ID 배열은 한 항목 커진다. 추가 output row를 요구하는 경우 F32 logits는248,320×4=993,280bytes(0.9473MiB)다. Backend sampling까지 포함한 output row 추가도 수 MiB 규모이며 해당 output buffer는 CPU/device-host buffer를 선택한다. Backend sampler의 제한된 추가 공간 가능성을 무시해 메모리 완전 동일이라고 주장하지 않는다.
- 따라서 [28,672MiB 전체 예상 peak와 별도 margin](../native_qwen38_resource_plan.md)을 유지하는 것은 합리적이다. 기존 pool/graph/불확실성 allowance를 넘는 새로운 대형 할당 경로는 이 변경에서 발견하지 못했다. 엄밀한 상한·per-process hard cap은 아니며 fresh GPU3 반복 측정과 own-child watchdog가 계속 필수다. Epoch1/2가 약18,290MiB에서 실패한 관측은 전체 inference peak 증거가 아니다.

## 새 epoch 전에 유지할 경계

새 config에는2/1을 명시하고 resource consumer도2/1만 받아야 한다. 현재 계획·freeze·실제 argv/report는 이 조건으로 함께 묶는다. 이전 batch1 config/report/source revision과 실패 epoch는 보존한다. 새 기본값이 추가됐으므로 과거 필드 없는 JSON을 새 코드로 읽는 것은 당시 실행 재현이 아니다.

Vocab-only CPU proof의 GGUF·embedded template·원문 wire·native tokenizer/grammar·4096/768 검사는 GPU logical batch를 입력으로 사용하지 않아 범위 내에서 계속 유효하다. 공식 HF19/20 FAIL 및 별도 raw20/20 PASS도 바뀌지 않는다. 이 proof를 startup·decode·품질 성공으로 확대하지 않는다. 실제 새 startup, 공개 자원 probe, 동결 후 strict 품질 진단이 남아 있다.

확인한 upstream 구간: `common/common.cpp`의 warmup/seq_rm 검사, `tools/server/server-context.cpp`의 startup 호출, `src/llama-context.cpp`의 context parameters/scheduler reserve/decode/output reserve, `src/llama-memory-hybrid.cpp`의 ubatch splitting. Review 시점 full regression은 parent 진행 예정이며 여기서는 PASS로 선기록하지 않는다.
