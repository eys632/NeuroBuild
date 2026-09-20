# Qwen3-32B-AWQ CPU 사전 검토

2026-09-20 UTC. **CPU 구조·변환·grammar·문맥 검사 PASS, 저장 dtype/index 경고 유지.**
대상은 공식 `Qwen/Qwen3-32B-AWQ`, revision
`0499c3ac83fdef8810b907a23894ba91e95eddd8`이다. GPU 조회·모델 호출·다운로드·환경 변경은 수행하지 않았다.
이 검토는 startup, CUDA kernel, 의미 정확도 또는 Phase5.x gate 통과 증거가 아니다.

## Header와 dtype 불일치

[Header 증거](../../evaluations/results/phase5x/32b-header-audit.json)는 완료된 shard4개에서
총183,056bytes의 length/header만 읽었다. Config에서 독립 도출한 **1,603개** 이름·shape와
실제 header, 고정 index의 shard 배치가 일치하고 data offset의 중복·빈 구간·파일 경계 초과가 없다.
Quantized `qweight/qzeros` **I32 896개**, 나머지 embedding/lm_head/norm/scales **BF16 707개**다.
Group128, 4-bit packing의 projection별 input/output과 scale/zero shape·byte 크기를 대조했다.

처음에는 `config.torch_dtype=float16`을 저장 dtype으로 가정하여 검사가 실패했다.
실제 BF16 저장을 발견한 뒤 별도 loader/value 검증을 추가했으며, 이를 F16 저장 성공으로 바꾸어 보고하지 않는다.
실제 tensor data는 **19,325,298,688bytes**, 전체 shard는19,325,481,744bytes다.
공식 index의 `metadata.total_size=19,338,405,888`은 실제 data보다13,107,200bytes 크며
전체 파일 합보다도 크다. 원인은 미확정이다. 해당 scalar 대신 실제 header coverage를 확인했고
index의 이름·shard mapping 검증은 유지했다. Downloader의 전체 weight SHA 검사를 재수행한 것은 아니다.

## BF16→FP16 실제 값 검사와 loader 경계

[별도 변환 증거](../../evaluations/results/phase5x/32b-dtype-cast-audit.json)는 명시적으로 허용된
BF16 payload만8MiB씩 읽어 CPU `float16 destination.copy_(bfloat16 source)`를 실행했다.
Torch2.6.0+cu118, CPU thread2/inter-op1, CUDA 초기화false, elapsed33.307초다.
**707 tensors / 1,800,295,424 values / 3,600,590,848bytes**를 검사했고 I32 payload는 읽지 않았다.
원본 비유한 값0, FP16 유한 범위 초과0, 변환 후 비유한 값0, 최대 절댓값27.25다.

| 그룹 | Tensor 수 | 변환값 변화 | nonzero→zero | 추가 확인 |
|---|---:|---:|---:|---|
| Quantization scales | 448 | 0 | 0 | 원본 ≤0 값0이므로 변환 뒤에도 모두 양수 |
| Embedding/lm_head/norm | 259 | 392,411 | 2,335 | 작은 값 rounding/underflow 보존 |

표는 증거의 `tensor_results`를 `.scales` suffix로 나누어 합산한 값이다.
일반 tensor의 rounding/underflow를 품질 성공이나 실패로 추정하지 않는다.
설치된 loader는 `model_config.dtype` 기본값으로 destination을 생성하고, AWQMarlin scales의
`params_dtype`, norm/embedding 및 column/row/QKV loader의 `copy_`가 dtype 변환을 수행한다.
Marlin scale 재배열은 이 로딩 뒤에 수행된다. 독립 source 검토도 이 경로를 확인했다.
검토한 설치 source6개의 SHA는 변환 증거에 들어 있다. 실제 GPU 로딩·양자화 품질은 별도 검증 대상이다.

## 실제 tokenizer와 JSON grammar

[CPU preflight](../../evaluations/results/phase5x/generation2-32b-cpu-preflight.json)는 metadata9개
size/SHA와 downloader manifest를 확인하고, 실제 로컬 tokenizer 및 내장 chat template을 사용했다.
`enable_thinking=false`의 빈 `<think>` prefix는 template에서 온 것이며 모델 reasoning 출력이 아니다.
단일 generation2 branch schema + `requirement_generation_v2_v2.txt`에 대해 xgrammar0.1.18 compile,
token+EOS valid8/invalid14, prompt 예시7개의 schema→adapter→기존 parser 검증이 통과했다.
vLLM0.8.5의 unsupported-feature 검사도 통과했다. 코드·prompt·schema·gold는 변경하지 않았다.

| 입력 자료 | 입력 수 | 최대 input+output768 | Context4096 여유 |
|---|---:|---:|---:|
| 기존 development | 40 | 3,682 | 414 |
| 이미 노출된 기존 holdout regression | 80 | 3,687 | 409 |
| 미호출 holdout v2 길이만 | 80 | 3,612 | 484 |

이번 CPU 검사의 출력에는 v2 원문·case별 값·gold를 포함하지 않았고 모델에 보내지 않았다.
과거 root의 입력 부분 노출은 [별도 addendum](../../evaluations/hardening_v2_input_exposure_addendum.json)에
기록된 그대로 유지한다. 전체 작업의 완전한 blind를 주장하지 않는다. 사람 미검수 synthetic gold 한계도 유지한다.

## 보존 및 재현

세 JSON은 ignored 원본의 exact-byte 복사다. SHA-256은 순서대로
`51c1261d99c0e1a445e31b4a95fa12211ddb13bdd02f8eac45984dab18dadb04`,
`ba92dceb6dfdd208027df63178d39f418e66ccb16a8162e6498dd9343feafdb7`,
`0ba7937d289a6d19f7755287038f122f8171ab145483eb46f83760fb236e6cb0`다.
실행된 [header helper](../../evaluations/results/phase5x/32b-cpu-preflight-tools/audit_qwen3_32b_headers.py),
[dtype helper](../../evaluations/results/phase5x/32b-cpu-preflight-tools/audit_qwen3_32b_dtype_cast.py),
[tokenizer/grammar helper](../../evaluations/results/phase5x/32b-cpu-preflight-tools/verify_generation2_32b_preflight.py)도 그대로 보존했다.
이 helper들은 원래 위치를 기준으로 root를 찾는다. 보존 경로에서 직접 실행했다고 주장하지 않는다.
재현 시 첫 두 파일은 `var/review-tools/`, 마지막 파일은 `var/research/`에 동일 bytes로 복원하고
고정 metadata manifest도 원래 `var/research/qwen3-32b-awq-feasibility/<revision>/`에 두어야 한다.
프로젝트 root에서 사용한 명령은 다음과 같다.

```bash
PYTHONPATH=src:. .conda/bin/python -B var/review-tools/audit_qwen3_32b_headers.py
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .conda-vllm/bin/python -B var/review-tools/audit_qwen3_32b_dtype_cast.py
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_TORCH=0 USE_TF=0 USE_FLAX=0 PYTHONPATH=src:. .conda-vllm/bin/python -B var/research/verify_generation2_32b_preflight.py
```

Tokenizer 실행 동안 torch는 import하지 않았고 grammar 단계에서만 CPU torch를 import했다.
후속 GPU3 자원 guard·실제 startup/health/listener·고정 진단과 정식 품질 gate는 root가 별도로 확인한다.
