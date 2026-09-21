# Native Qwen3.8 단회 진단 — 1차 gate PASS

Run `20260920T071218Z-d9e611b184ea4f8cbb0d7369982ef361`, clean pushed `bec9000e697c6b4930d077822ae30ca484a395ba`.
기존 노출120개×1+별도 warmup5. 원본 manifest/dataset/results는 그대로 복사했다.
Schema120/120, parser119/120, semantic117/120, rawFP0/58, unsafe0/120, raw관측120/120.
Warmup5/5 정답은 평가 분모에서 제외한다. H02/HH-B05/HH-J05의 실패를 수정하지 않았다.
HTTP end-to-end 평균5.215412956초/p95 5.811240079초. TTFT/decode 속도가 아니다.

`independent_replay.json`은 고정 commit의 source_snapshot으로125개 final JSON을 모두 재생한 증거다.
`replay_native_qwen38_exposed.py`는 실제 사용한 helper의 exact copy다. 별도 reasoning은 보존하지 않았다.
원본 결과 SHA e16c753dd9701f1115a8d56445f27f68835e20b9323787316db776606769da48.
전후 guard/listener와 최종 resource/stop/반환 VRAM 증거를 함께 보존한다. Epoch4 전체의 aggregate
baseline-relative peak18346MiB/minfree18028MiB이며 정확한 process별 peak나 hard cap이 아니다.

사용자 checkpoint 지시로 동일120개 전체3회 반복을 취소했다. 이 단회 평가를 반복하거나 재채점하지 않는다.
V2 모델 호출은0이며 root의 일부 입력 노출 기록과 AUTO-GENERATED / NOT HUMAN VERIFIED를 유지한다.
공식 HF token ID19/20 FAIL과 raw-Unicode variant를 구분한다. RTX5090은 미검증이다.
이 결과는 1차 품질 gate 통과이며 Phase5.x 전체 완료나 최종 모델 채택을 뜻하지 않는다.
