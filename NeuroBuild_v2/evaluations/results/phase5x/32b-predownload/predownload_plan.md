# 공식 Qwen3-32B-AWQ: 다운로드 전 제한 비교 계획

**PREDICTED_UNVERIFIED. 모델 선정·품질 통과·32B 실행 성공 기록이 아니다.**
기존 14B의 single generation 2 / decision-branch schema / prompt v2 / greedy 비교를
공식 dense 32B checkpoint로만 바꾸는 후보다. Staged 실험의 실패가 모델 크기 효과를
입증하지 않으며, 새 prompt·gold 수정으로 비교 조건을 바꾸지 않는다.

## 재현 파일과 정적 지원

- 공식 저장소: [Qwen/Qwen3-32B-AWQ](https://huggingface.co/Qwen/Qwen3-32B-AWQ).
  고정 revision은 `0499c3ac83fdef8810b907a23894ba91e95eddd8`이다.
- 같은 디렉터리 `qwen3-32b-awq.json`은 기존 downloader 형식의 13파일 manifest다.
  SHA256 `fbb3d1c98f3ceeeceb2fd5306dde9439d1be12516dd5054c0b2f5a299a260e03`.
  `.gitattributes`만 제외했고 inference 파일·README·LICENSE를 포함했다.
- 4개 safetensors의 SHA256은 [고정 Hub LFS metadata](https://huggingface.co/api/models/Qwen/Qwen3-32B-AWQ/revision/0499c3ac83fdef8810b907a23894ba91e95eddd8?blobs=true)를 사용했다.
  Weight 내용은 다운로드하거나 읽지 않았다. Index의 1,603 tensor가 참조하는 shard 집합은
  이 4파일과 정확히 같다. Index `metadata.total_size`는 실제 shard 합계보다 12,924,144 bytes
  크므로 다운로드 계산에는 실제 Hub/LFS 파일 크기를 사용했다. 해당 upstream 차이는 보존한다.
- 모든 파일 합계 **19,341,523,989 bytes / 18.013198 GiB**,
  weight 합계 **19,325,481,744 bytes / 17.998257 GiB**다.
- [Apache-2.0 LICENSE 원본](https://huggingface.co/Qwen/Qwen3-32B-AWQ/blob/0499c3ac83fdef8810b907a23894ba91e95eddd8/LICENSE)은
  로컬 `LICENSE`에 그대로 보존했다. 11,544 bytes,
  SHA256 `5de36594c10839788a8c589443a8ef9d8b8d17c65a1b5807206ae037fc36c6bd`.
  공식 Qwen quantization artifact이며 제삼자 MoE quantizer의 calibration 재현 주장과 구분한다.
- `tokenizer.json`, `tokenizer_config.json`, `vocab.json`, `merges.txt`는 기존 공식 14B
  tokenizer의 bytes가 32B의 고정 size 및 LFS SHA256 또는 Git blob SHA1과 모두 일치한다.
  `tokenizer_config.json` 내 chat template도 동일하며 별도 `.jinja` 파일은 없다.
  전체 tokenizer 추가 다운로드 없이 확인했다. 상세 근거는 `manifest_provenance.json`과
  `static_feasibility.json`에 있다.
- [실제 config](https://huggingface.co/Qwen/Qwen3-32B-AWQ/blob/0499c3ac83fdef8810b907a23894ba91e95eddd8/config.json)는
  `Qwen3ForCausalLM`, dense 64 layers, hidden 5120, intermediate 25600,
  Q heads 64 / KV heads 8 / **명시 head_dim 128**, vocab 151936이다.
  AWQ GEMM 4-bit, group 128, zero-point true이며 embedding과 LM head는 비양자화다.
  MoE active parameter 수와 무관하게 모든 weight가 GPU에 상주한다.
- 설치된 Transformers 4.51.3 / vLLM 0.8.5 cu118는 Qwen3를 등록하고,
  [AWQMarlin 경로](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/layers/quantization/awq_marlin.py)는 SM80,
  이 quantization 형식과 TP1의 q/k/v/qkv/o/gate_up/down shape 7종을 정적으로 지원한다.
  `trust_remote_code`가 필요한 custom architecture나 `auto_map`은 없다.
  실제 적재 시 AWQMarlin 선택과 kernel 실행을 확인해야 한다. Unoptimized AWQ나 전체 FP16
  weight로 조용히 바뀌어도 같은 예산이라고 간주하지 않는다.

## 25 GiB 전체 peak 예산의 근거와 한계

가정은 FP16 activation/KV, TP1, seq1, context 및 최대 batch tokens 4096,
KV 256 blocks × 16 tokens, eager, FlashAttention2, V0, no LoRA/offload/swap/graphs다.
파일 크기는 상주 메모리의 근사 근거이며 실제 allocation 상한은 아니다.

| 구성 | 계획 예산 MiB | 근거 |
|---|---:|---|
| Weight·scale·zero·embedding/head·상주 workspace | 18,560 | 파일 18,430.22 MiB + 약 129.8 MiB 여유 |
| FP16 KV | 1,024 | 2 × 64 × 8 × 128 × 2 × 4096 bytes |
| Prefill activation·kernel scratch | 2,048 | 아래 tensor 산술보다 넓은 계획 여유 |
| 추가 repack 임시 공간 | 512 | 가장 큰 packed linear의 새 qweight 125 MiB + permutation 등 |
| CUDA context·비 Torch library | 1,024 | 측정 전 가정, 실제 초기화 시 재확인 |
| Allocator cache·fragmentation·rounding | 1,408 | 고정 보장이 없는 보수적 계획 여유 |
| 전체 peak 추정의 추가 불확실성 여유 | 1,024 | 기존 24 GiB 세부 예산 위에 추가, guard allowance와 중복하지 않음 |
| 합계 | **25,600** | **측정값이나 증명된 최대치가 아닌 실행 전 추정치** |

[기본 loader](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/model_loader/loader.py)는
모듈별로 후처리하며 [safetensors iterator](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/model_loader/weight_utils.py)는
CPU tensor를 순차 공급한다. AWQMarlin은 layer별 packed weight를 새 packed weight로
교체하므로 GPU에 전체 checkpoint 두 벌을 의도적으로 보존하는 경로가 아니다.
가장 큰 gate_up qweight의 추가 복사본은 125 MiB, scale 3.90625 MiB,
unpacked int32 zero-point 한 벌은 7.8125 MiB다. 모든 64 layers의 고정 Marlin lock
workspace 합은 약 4.375 MiB다. 해제된 tensor의 allocator cache는 별도 예산에 포함했다.

4096-token gate_up 출력은 400 MiB, SiLU 출력은 200 MiB, hidden 한 벌은 40 MiB,
QKV 출력은 80 MiB다. 공식 [Marlin kernel](https://github.com/vllm-project/vllm/blob/v0.8.5/csrc/quantization/gptq_marlin/gptq_marlin.cu#L2157)의
FP32 reduction scratch는 이 shape에서 200 MiB다. 이는
[max_par=16](https://github.com/vllm-project/vllm/blob/v0.8.5/csrc/quantization/gptq_marlin/marlin.cuh#L30)으로
1024 × 51200 × 4 bytes를 계산한 값이다. 모든 tensor의 수명이 완전히 겹친다는 주장은
아니며, prefill 2 GiB는 이 주요 항목과 attention/normalization 등의 추가 비용을 위한 추정 예산이다.
`prompt_logprobs`를 요청하지 않는 현재 단일 생성에서는 sampling용 hidden을 먼저 잘라
logits를 계산한다. 이 계산을 모든 prompt token의 full-vocabulary logits 생성으로 확대하면 안 된다.

설치본 [V0 profiler](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/worker/worker.py#L239)는
적재 후 cache를 비우고 최대 batch/seq의 dummy forward로 activation peak를 확인한다.
기존 **14B** 보고서 `var/reports/qwen3-14b-generation2-v2-server.json`에서는 aggregate 증가
11,914 MiB, 로그에서는 weight 9.36 GiB / activation 0.57 GiB / non-Torch 증가 0.09 GiB였다.
이는 32B 측정도, 타 프로세스 변동을 제거한 per-process peak도 아니다.

따라서 최종 25 GiB는 제한된 설정의 **조건부 계획 예산으로 방어 가능한 추정**이다.
CUDA/allocator 예산이 수학적으로 보장되지는 않으며 실제 startup profile과 inference
관측이 필요하다. 추정 실패 시 자신의 작업만 중단하고 결과를 보존하며 다른 GPU나
unquantized fallback을 시도하지 않는다. Watchdog은 polling 방식이며 하드웨어 메모리 격리가 아니다.

## 실행 전 자원 조건

부모가 제공한 A100 GPU3 free 36,373 MiB에서 margin은 7,275 MiB다.
25,600 + 7,275 = **32,875 MiB**, 계획상 잔여는 **3,498 MiB**다.
이 문서는 GPU를 재측정하지 않았다. 기존 모델을 중단한 뒤 root가 새 free/utilization
preflight와 실행 중 free floor를 확인해야 한다.

최종 권고는 A100의 **vLLM utilization / Torch fraction 각 0.60**, **estimated peak
25,600 MiB / allowance 0**이다. 제공된 CUDA total 약 39.39 GiB에서 Torch cap은
약 **23.63 GiB**이며, **전체 프로세스의 25 GiB hard cap은 아니다.**
non-Torch 예산 1 GiB를 더한 약 24.63 GiB는 전체 25 GiB 계획 안에 있다.
실제 설정 결정·변경은 root가 담당한다.
`gpu_memory_utilization`은 profiling/KV 계획 값이고 전체 프로세스 격리 상한이 아니다.
추정 peak와 aggregate 증가 중단선을 모두 **25,600 MiB**로 맞추며 추가 1 GiB allowance를
더하지 않는다. 본 조사에서는 실행 설정을 바꾸지 않았다.

RTX5090 physical GPU1은 **PREDICTED_UNVERIFIED**다. 같은 25,600 MiB 가정에는 새 측정
free **32,000 MiB 이상**이 필요하다(그 지점의 margin 6,400 MiB).
0.60은 A100 전용 계획 분율이며 RTX에는 실제 total과 필요 allocation에 맞는 별도 cap이 필요하다.
현 A100 cu118 환경을 그대로 사용할 수 없으며 SM120 native runtime이 필요하다.
현대 [SM12.x build](https://github.com/vllm-project/vllm/blob/v0.29.0/CMakeLists.txt#L609)와
[dense Marlin backend](https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/kernels/linear/mixed_precision/marlin.py)의
정적 근거는 있으나 실제 RTX memory/kernel/quality 검증은 없다. 이 dense 모델에
MoE emulation을 적용할 이유가 없고 SM100 datacenter 지원만으로 SM120 성공을 추정하지 않는다.

다운로드 전 디스크는 **전체 18.013198 GiB + 20 GiB reserve + 운영 여유**가 필요하다.
최종 root 제공 usable disk는 **48,954,236,928 bytes**다. 전체 다운로드 후
**29,612,712,939 bytes / 약 27.58 GiB**, reserve 초과 여유 약 **7.58 GiB**다.
이전의 reserve 초과 여유 92.39 MiB는 개인 미사용 4B weight 정리 전 관측이며 최신 예산이 아니다.
이번 작업은 cache/weight 삭제, 설치, weight 다운로드, GPU/model 호출을 수행하지 않았다.

산술·소스 hash·설정 가정은 `predownload_memory_plan.json`, 파일별 출처는
`manifest_provenance.json`, 초기 조사와 정적 shape 검증은 기존 파일에 보존했다.

## 부모의 후속 자원 확인에 대한 검토

최종 전달 직전 root는 기존 14B 종료 후 GPU3 free 36,373 MiB / utilization 0,
검증한 개인 미사용 4B weight 정리 후 usable disk **48,954,236,928 bytes**라고 제공했다.
이번 reviewer가 재측정하거나 삭제한 값은 아니다. 단일 다운로드 후 약 **27.58 GiB**,
20 GiB reserve를 제외한 약 **7.58 GiB**가 남는 산술이다.

초기 검토의 0.575는 CUDA total 약 39.39 GiB에서 Torch 약 22.65 GiB다.
주요 live tensor 예산 21.125 GiB에는 여유가 있으나, allocator와 repack 여유까지 포함한
기존 Torch 세부 계획 23 GiB보다 약 0.35 GiB 낮다. Repack의 수명과 profile 전
`empty_cache()`만으로 allocator fragmentation을 보장할 수 없으므로, 불필요한 self-cap OOM
위험을 줄이기 위해 **0.60과 전체 25 GiB 계획으로 최종 변경했다.** 이전 0.575 권고는 채택하지 않는다.
실제 library/allocator 동작은 측정 전이므로 cap 내 성공을 보장하지 않는다. Cap 오류나 profile
예산 초과가 나면 해당 자기 실행을 중단·기록하고 공용 GPU의 안전 여유를 소모하도록 자동 증액하지 않는다.
