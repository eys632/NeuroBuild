# Local Model shortlist — Phase 0

조사일: **2026-09-19**. 범위는 공식 자료 기반 shortlist이며 최종 모델 선정이 아니다.
설치, weight 다운로드, GPU 추론, NeuroBuild benchmark는 수행하지 않았다.
A100 서버 정보는 실측이지만 **모든 후보의 이 서버 runtime 검증은 NOT_RUN**이다.
RTX5090은 사용자 제공 과거 정보에 근거한 **PREDICTED / UNVERIFIED** 환경이다.
평가 절차와 synthetic 사례는 [model_evaluation_plan.md](model_evaluation_plan.md)를 따른다.

## 1. 선택 조건과 현재 실행 제약

- 공통 Application과 API/schema/prompt를 유지하고 가능하면 양쪽에서 같은 모델을 사용한다.
- A100은 physical GPU3 하나, RTX5090은 physical GPU1 하나만 사용한다. TP=1이며 다른 GPU로 fallback하지 않는다.
- A100 실측: A100-PCIE-40GB, 40960MiB, compute capability 8.0, driver 535.183.01, glibc 2.31.
- `nvidia-smi`의 CUDA 12.2 표시는 driver의 CUDA 호환성 정보이고, 설치 toolkit은 nvcc 11.8이다. 둘을 PyTorch wheel의 CUDA runtime과 구분한다.
- 조사 시 GPU3에 예상 밖 프로세스 3개와 약 3965MiB 점유가 관찰되었다. 이를 종료하거나 피해서 모델을 실행하지 않는다.
- root filesystem 사용률 96%, 가용 약 86GB였다. 숫자만 보고 다운로드를 허용하지 않고 필요한 cache/환경/weight/임시공간과 서버 여유 정책을 먼저 검토한다.
- 최신 vLLM의 model registry 등재는 현재 driver/glibc에서 배포 wheel이 실행된다는 증거가 아니다. **현재 서버에서 확인된 실행 가능 build는 없다.**
- driver, 시스템 CUDA, OS를 변경하여 맞추지 않는다. 실제 설치 조합은 [runtime_compatibility.md](runtime_compatibility.md)의 검토를 통과한 뒤 고정한다.

## 2. 후보 5개 비교

아래 context는 모델의 명목 한도다. single GPU에서 그 전체 길이를 사용할 수 있다는 의미가 아니다.
parameter 수는 card의 표기이며 active parameter를 전체 weight 크기로 착각하지 않는다.

| 후보 / 공식 ID | Parameter와 architecture | License | Context | 한국어·제품 적합성 근거와 한계 |
| --- | --- | --- | --- | --- |
| Qwen3.8-27B — `Qwen/Qwen3.8-27B` | 언어모델 27B dense; 64층 중 48 Gated DeltaNet + 16 attention; vision encoder | Apache-2.0 | native 262,144; 확장 1M | 복잡한 instruction/agent 작업을 위한 최신 후보. 해당 card에서 한국어 개별 성능이나 BIM benchmark는 확인하지 못함. [S1] |
| Qwen3.6-35B-A3B — `Qwen/Qwen3.6-35B-A3B` | 언어모델 total 35B / active 3B MoE; DeltaNet/attention hybrid; vision encoder | Apache-2.0 | native 262,144; 확장 1,010,000 | MoE의 계산량 이점을 속도 비교에 활용할 후보. 한국어 BIM·모호성 처리 품질은 미측정. [S2] |
| Gemma4-31B-it — `google/gemma-4-31B-it` | dense; card 표의 30.7B 및 vision encoder 약 550M; sliding/global attention | Apache-2.0 | card 256K | 일반 reasoning/tool use 및 공식 QAT 배포 경로가 장점. 다국어 주장은 한국어 BIM 검증을 대체하지 못함. [S3, S4] |
| Gemma4-12B-it — `google/gemma-4-12B-it` | 11.95B dense; 별도 vision/audio encoder 없는 unified 구조 | Apache-2.0 | card 256K; vLLM recipe config는 128K | BF16 메모리 비교군. 작은 크기만으로 우선 선택하지 않으며 복잡한 의미 해석을 큰 후보와 비교. [S5, S6] |
| EXAONE4.5-33B — `LGAI-EXAONE/EXAONE-4.5-33B` | 약 33B dense: LM 31.7B + vision 1.29B; sliding/global attention | EXAONE AI Model License 1.2-NC | 262,144 | 한국어 KMMLU-Pro/KoBALT 등 공식 결과가 있어 연구 비교 가치. 제품의 기본 후보로 채택하지 않음. [S7, S8] |

Gemma4의 공식 card는 35+ 언어 지원 및 140+ 언어 사전학습을 설명한다. 이를 한국어 요구사항의 정확도 보증으로 해석하지 않는다. [S3]
EXAONE의 license는 연구·교육 목적을 허용하고 상업 사용에는 별도 계약을 요구한다. Apache-2.0 후보와 동일한 사용 조건으로 표시하지 않는다. [S8]
Qwen3-4B-Instruct-2507의 과거 실험은 historical baseline이며 새 환경의 재현 결과나 최종 선택 근거로 재사용하지 않는다.

## 3. 우선 평가 순서 — 실행 조건 충족 후

1. **Gemma4-31B 공식 QAT W4A16**: `google/gemma-4-31B-it-qat-w4a16-ct`를 우선 검토한다.
   Google이 vLLM용 compressed-tensors checkpoint를 제공하므로 양쪽 서버에 동일 artifact를 사용하는 경로가 명확하다.
   실제 A100/SM120 kernel 지원, driver/glibc, parser, 짧은 context의 메모리 검증을 먼저 통과해야 한다. [S4]
2. **Qwen3.8-27B**: 복잡한 지시와 설계 reasoning 후보로 비교한다.
   A100에서 실행할 정확한 quant checkpoint와 kernel 경로가 확인된 뒤 평가한다.
   공식 FP8 checkpoint가 있으나 A100 native FP8 연산을 의미하지 않는다.
   RTX5090의 NVFP4와 다른 precision을 사용한다면 quantization별 의미 정확도를 따로 비교한다. [S1, S9, S10]

Qwen3.6 MoE는 이후 latency/처리량 비교 후보다. Gemma12는 메모리 부담이 작은 비교군으로 남기되 vLLM release/context 불일치를 해소한다.
EXAONE은 비상업 연구 목적과 라이선스 조건에 부합하는 경우에만 후순위로 검토한다.
이 순서는 조사자의 조건부 제안이며 benchmark 순위나 최종 Primary Model 선정이 아니다.
현재 GPU 점유·디스크·runtime build 미확인 상태에서는 위 순서로도 다운로드나 실행을 시작하지 않는다.

## 4. Weight 하한, 실제 artifact, VRAM

이상적인 weight-only 크기는 `parameter 수 × bytes_per_weight / 2^30`으로 계산했다.
아래 GiB는 **계산에 의한 하한**이며 quant metadata, 미양자화 층, vision, recurrent state,
activation, workspace, CUDA graph 및 KV cache를 포함하지 않는다. 명목 parameter 수의 반올림 오차도 있다.

| 규모 | BF16 하한 GiB | 8bit 하한 GiB | 4bit 하한 GiB | A100 40GiB | RTX5090 32GB |
| --- | ---: | ---: | ---: | --- | --- |
| Qwen27B | 50.3 | 25.1 | 12.6 | BF16 불가; quant 필요 | BF16 불가; quant 필요 |
| Qwen35B MoE | 65.2 | 32.6 | 16.3 | BF16 불가; 8bit 여유 협소 | 8bit도 weight만으로 초과; 4bit 필요 |
| Gemma31B | 57.7 | 28.9 | 14.4 | BF16 불가; 공식 W4A16 검토 | BF16 불가; 공식 W4A16 검토 |
| Gemma11.95B | 22.3 | 11.1 | 5.6 | BF16 fit 가능성, 미검증 | BF16 fit 가능성, context/concurrency 제한 필요 |
| EXAONE33B | 61.5 | 30.7 | 15.4 | BF16 불가; quant 필요 | BF16 불가; 8bit 실행 여유 부족 |

**Gemma31 공식 QAT artifact의 실제 공개 파일 크기는 23.3GB, 약 21.7GiB**다.
공식 config는 INT4 group-size 32, symmetric, `compressed-tensors/pack-quantized`이며 quantization 제외층이 있다.
따라서 이상적인 14.4GiB를 실제 다운로드 크기나 VRAM으로 보고하면 안 된다. [S11, S12]
짧은 text context/concurrency 1에서 총 VRAM 약 **26–32GiB를 검증할 계획 범위**로 볼 수 있지만,
이는 21.7GiB artifact에 여유를 더한 추정일 뿐 측정치·보장값이 아니다. 로딩 시 재배치와 kernel workspace에 따라 달라진다.

다른 후보의 정확한 quant artifact 크기는 선택한 revision의 manifest로 다시 확인한다.
모든 후보의 startup/peak VRAM, latency mean/p95, tokens/sec, startup time은 **NOT_MEASURED**다.
초기 비교는 text-only, 짧은 context, concurrency 1부터 시작하고 필요에 따라 점진적으로 늘린다.
128K/256K/1M이라는 card 수치를 runtime 기본값으로 그대로 채택하지 않는다.

## 5. vLLM, structured output, tool calling

| 후보 | 공식 지원 근거 | Tool / reasoning parser | 버전·운영 주의점 |
| --- | --- | --- | --- |
| Qwen3.8-27B | 공식 recipe, `Qwen3_5ForConditionalGeneration` | 현재 recipe `qwen3_xml` / `qwen3` | 최소버전 badge와 특정 GPU에서 검증한 dev build가 다름. badge만으로 설치 버전을 정하지 않음. [S9] |
| Qwen3.6-35B-A3B | card 권장 vLLM >=0.19.0, 공식 recipe | card `qwen3_coder` / `qwen3`; 최신 docs의 XML parser 이름은 `qwen3_xml` | 설치 release에서 지원하는 이름·chat template을 확인. 서로 다른 버전의 옵션을 혼합하지 않음. [S2, S13, S14] |
| Gemma31 | registry, 공식 recipe, Google CT checkpoint | `gemma4` / `gemma4`, recipe의 전용 chat template | MTP/assistant 없이 단일 모델 기본 decoding부터 검증. [S4, S15, S16] |
| Gemma12 | 최신 registry `Gemma4UnifiedForConditionalGeneration` | Gemma4 tool/reasoning 프로토콜 | recipe에 `0.23.0+` badge와 nightly required 문구가 공존. release 및 context를 재확인. [S6, S15] |
| EXAONE4.5 | 최신 registry `Exaone4_5_ForConditionalGeneration` | card `hermes` / `qwen3` | card의 `vllm >=0.5.8` 표기는 모델 발표 시기와 맞지 않아 설치 근거로 채택하지 않음. [S7, S15] |

vLLM의 `response_format: json_schema` / `structured_outputs`와 xgrammar 등의 backend를 검토한다.
구 `guided_*` 필드는 v0.12.0에 제거되었으므로 새 contract에 넣지 않는다.
schema-constrained decoding은 구조를 제한하며 의미 정확도·객체 정합성·안전한 실행을 보장하지 않는다. [S17]
Tool parser 존재 역시 한국어 tool selection 성능의 보증이 아니다.
최신 tool-calling 문서는 auto mode의 schema 강제가 parser의 structural-tag 지원,
per-tool `strict: true` 및 서버 strictness 설정에 좌우됨을 설명한다. 버전별 동작을 테스트한다. [S14]

평가에서는 JSON만 생성하는 parsing contract와 tool-call protocol을 각각 검증한다.
thinking on/off에 따른 latency와 품질을 비교하되 chain-of-thought를 저장하지 않는다.
Qwen의 `preserve_thinking` 기본값이나 card의 reasoning 출력 예제를 그대로 제품 로그에 도입하지 않는다.
Backend는 모든 출력을 재검증하며 GlobalId를 생성하거나 raw IFC를 수정할 권한을 LLM에 주지 않는다.

## 6. A100과 RTX5090의 precision 차이

- A100 Ampere는 native FP8 W8A8을 지원하지 않는다. FP8 weight의 Marlin 등 weight-only 실행 경로와 native FP8을 구분한다. [S18]
- AWQ/GPTQ/Marlin의 Ampere 지원은 모든 새로운 모델·quant artifact·kernel 조합의 지원을 뜻하지 않는다. [S18, S19]
- vLLM overview의 quantization matrix에는 Blackwell 열이 없다. 이 표만으로 RTX5090 PASS를 기록하지 않는다. SM120별 kernel 경로를 확인한다. [S18, S20]
- Qwen3.8 공식 recipe는 단일 5090에서 NVFP4가 `--enforce-eager`, 32K context 조건으로 fit한 사례와 graph capture OOM을 설명한다.
  이는 upstream의 특정 checkpoint/build 검증이며 사용자 서버 실측이 아니다. TP2 결과를 GPU1 하나의 결과로 재사용하지 않는다. [S9]
- Qwen3.6 recipe에는 SM120 NVFP4의 별도 kernel/backend 요구사항과 5090의 64K context 설정이 있다.
  NVIDIA NVFP4 card의 지원 대상은 Hopper/Blackwell이며 이 artifact를 A100 공통 checkpoint로 즉시 채택하지 않는다. [S13, S21]
- 서로 다른 precision을 쓰더라도 모델 계열·API/schema/prompt는 공통으로 유지한다. precision별 회귀평가를 통과하기 전 동일 품질이라고 기록하지 않는다.

## 7. 비교 결과와 재현 정보의 기록

한국어 이해, 복잡한 부정/조건문, BIM 해석, hallucination, 설계 reasoning, 운영 안정성은 전 후보에서 NeuroBuild 평가가 남아 있다.
공개 일반 benchmark의 높은 점수로 모호성 탐지나 잘못된 객체 선택 위험을 추정하여 PASS 처리하지 않는다.
실제 점수와 통과 기준은 [model_evaluation_plan.md](model_evaluation_plan.md)에서 관리한다.

향후 기록할 항목: model/quant repo ID와 full commit SHA, weight manifest 크기/checksum,
tokenizer/chat-template revision, Python/PyTorch/vLLM/CUDA build, parser, quant kernel,
schema/prompt revision, decoding mode, context/concurrency, GPU, startup/VRAM/latency 및 평가 dataset revision.
`model-card 주장`, `upstream 특정 환경 검증`, `NeuroBuild A100 실측`, `RTX5090 예측`을 구분한다.

아래 링크는 조사일에 열람한 mutable 문서다. URL의 `main/latest/stable`을 reproducible version pin으로 취급하지 않는다.
Gemma31 QAT 파일 목록에서 HEAD 축약 SHA `52f3f65`, config 페이지에서 파일 변경 축약 SHA `ca9d525`를 확인했다.
이는 metadata 관찰이며 배포용 full revision pin은 아니다. 다른 후보의 immutable revision과 weight manifest는 아직 확정하지 않았다.

## 8. 공식 출처 — 조회 2026-09-19

- [S1 — Qwen3.8-27B model card](https://huggingface.co/Qwen/Qwen3.8-27B)
- [S2 — Qwen3.6-35B-A3B model card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)
- [S3 — Google Gemma4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
- [S4 — Google Gemma31 QAT W4A16 model card](https://huggingface.co/google/gemma-4-31B-it-qat-w4a16-ct)
- [S5 — Google Gemma12 model card](https://huggingface.co/google/gemma-4-12B-it)
- [S6 — vLLM Gemma12 recipe](https://recipes.vllm.ai/Google/gemma-4-12B-it)
- [S7 — LG EXAONE4.5 model card](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B)
- [S8 — EXAONE4.5 LICENSE](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B/blob/main/LICENSE)
- [S9 — vLLM Qwen3.8-27B recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B)
- [S10 — Qwen3.8-27B official FP8 checkpoint](https://huggingface.co/Qwen/Qwen3.8-27B-FP8)
- [S11 — Google Gemma31 QAT files / 23.3GB listing](https://huggingface.co/google/gemma-4-31B-it-qat-w4a16-ct/tree/main)
- [S12 — Google Gemma31 QAT quantization config](https://huggingface.co/google/gemma-4-31B-it-qat-w4a16-ct/blob/main/config.json)
- [S13 — vLLM Qwen3.6-35B-A3B recipe](https://recipes.vllm.ai/Qwen/Qwen3.6-35B-A3B)
- [S14 — vLLM tool calling / strictness / parsers](https://docs.vllm.ai/en/latest/features/tool_calling/)
- [S15 — vLLM supported models](https://docs.vllm.ai/en/latest/models/supported_models/)
- [S16 — vLLM Gemma4 tool/reasoning recipe](https://docs.vllm.ai/projects/recipes/en/stable/Google/Gemma4.html)
- [S17 — vLLM structured outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/)
- [S18 — vLLM quantization hardware matrix](https://docs.vllm.ai/en/latest/features/quantization/)
- [S19 — vLLM GPTQModel / Ampere kernels](https://docs.vllm.ai/en/latest/features/quantization/gptqmodel/)
- [S20 — vLLM SM120/121 optional kernels](https://docs.vllm.ai/en/latest/features/quantization/b12x/)
- [S21 — NVIDIA Qwen3.6 NVFP4 card](https://huggingface.co/nvidia/Qwen3.6-35B-A3B-NVFP4)
