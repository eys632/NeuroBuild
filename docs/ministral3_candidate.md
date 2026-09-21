# Ministral 3 14B Instruct 후보

Qwen3.6의 첫 의미 gate 실패 후, 아직 이 과업에서 측정하지 않은 Mistral 계열의 공식 배포본을 비교한다.
다른 계열과 원저자 GGUF라는 점이 새 비교의 근거이며, 한국어 지원이나 공개 benchmark가 과업 품질을 보장하지 않는다.
현재 모델 미채택, Phase5.x 미완료, Phase6 미시작이다.

| 항목 | 고정값 |
|---|---|
| 배포 | `mistralai/Ministral-3-14B-Instruct-2512-GGUF` |
| Revision | `74fac473c43357d7fb2671713608183cc72496d0` |
| 파일 | `Ministral-3-14B-Instruct-2512-Q4_K_M.gguf` |
| 크기 / SHA256 | 8,239,593,024 bytes / `824e0f3373e69b84f2cae46fdcb9bd1ebc6ab3bfc7acc125d818b7b8178cc613` |
| 게시자 license 표기 | Apache-2.0, 2026-09-21 KST 확인 |
| 현재 FP8 참고 revision | `29439f81c2be264d8d393273f99e7db9c0961120` |
| 현재 BF16 참고 revision | `3cea74c1ebaf5ce5f5a2553de470e2ceab825142` |
| Native runtime | llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2` |

[공식 GGUF](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512-GGUF/tree/74fac473c43357d7fb2671713608183cc72496d0)와
[공식 FP8 카드](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512/blob/29439f81c2be264d8d393273f99e7db9c0961120/README.md),
[BF16 설정](https://huggingface.co/mistralai/Ministral-3-14B-Instruct-2512-BF16/blob/3cea74c1ebaf5ce5f5a2553de470e2ceab825142/config.json)을 확인했다.
GGUF의 정확 conversion source revision/log와 tensor별 quantization recipe는 공개 자료로 확정하지 못했다.
위 현재 참고 revision을 실제 변환 원본으로 주장하지 않는다. 별도 모델 저장소 LICENSE 파일을 확보했다고도 주장하지 않는다.
공식 license text 출처는 [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0.txt)다.
외부 전체 HTML/JS/API response는 새 Git provenance에 반입하지 않는다.

공식 카드의 권고는 temperature <0.1이다. 명시 profile `ministral3_nonthinking_llama_cpp`는
T0.05/P1/K0/minP0/presence0/frequency0/repeat1/window0/seed42,
samplers `temperature,top_k,top_p,min_p`를 사용한다. 온도 외 세부 recipe는 프로젝트 선택이다.
평가기는 정확한 model ID/quant 조합에만 profile을 허용하고, revision은 다운로드 manifest와 후속 freeze로 고정한다.
기존 9개 sampling branch와 prompt/schema/scorer는 유지한다.
이 변경의 backend 회귀 **430 PASS, skip0**는 완료했으며 모델 품질 PASS와 구분한다.

40층 dense text model, hidden5120/FFN16384/32heads/KV8/head128/vocab131072이며,
BF16 index에서 text tensor363개를 기대한다. Vision/projector는 이번 text-only 범위에 포함하지 않는다.
실제 GGUF의 구조·전체 SHA·embedded template와 tokenizer는 별도 검사 대상이다.
Canonical Tekken v13와 고정 공식 tokenizer source에 따른 새로운 CPU 비교가 필요하며,
기존 Qwen/Gemma corpus나 normalization 결론을 그대로 가져오지 않는다.
현재 설치된 `mistral-common 1.5.4`는 v13을 받지 못하므로 성공한 공식 loader 실행으로 표시하지 않는다.
기존 `tiktoken 0.14.0`으로 공식 source의 규칙을 명시적으로 재현하는 참조를 준비한다. 추가 패키지 설치는 없다.

초기 context4096/seq1/F16 KV/batch64/ubatch64/flash OFF/graphs OFF 조건에서
전체 weight+KV+workspace+driver+loading+uncertainty 합은 약21,298MiB, 올림21,504MiB다.
운영 guard 예산은28,672MiB로 유지하여7,168MiB의 추가 여유를 둔다.
이는 정확 allocation 상한이 아니며, 실행 직전 GPU3 free/util과 별도 안전 margin을 통과해야 한다.
새 tokenizer로 노출120개 입력 길이를 측정한 후에만 context4096의 적합성을 확정한다.
Context가 커지면 자원 계획을 재검토한다. RTX5090은 **PREDICTED / UNVERIFIED**다.

품질 평가 전 실제 header/CPU 계약, 첫 GPU3 startup/public/resource, 고정 source와 평가 freeze가 필요하다.
실행할 경우 첫 평가는 기존 노출120×1+warmup5이며 schema100%, semantic≥114/120,
rawREADY FP0/58, unsafe0/120 및 raw 관측120을 유지한다.
명백한 실패이면 같은 후보 반복·V2·미사용80 접근 없이 종료한다.
통과/경계선일 때만 남은 불확실성에 맞춰 최소 재현성 검증을 판단한다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 사람이 검수한 정답으로 바꾸지 않는다.
