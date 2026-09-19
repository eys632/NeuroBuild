# Phase 5 runtime 후보의 실행 가능성 조사

조회일 **2026-09-20**. 공식 배포 metadata와 문서를 확인한 결과이며, 이 문서 자체는 설치·GPU startup·품질 평가의 성공 기록이 아니다. 모델 weight는 조사 과정에서 받지 않았다. GitHub wheel의 central directory/METADATA 약 197KB와 HF JSON metadata만 읽었다.

현재 host는 Ubuntu 20.04, glibc 2.31, driver 535.183.01, A100 SM80이다. 사용자의 최신 지침에 따라 GPU3 점유 존재만으로 중단하지 않고, GPU3의 측정 free VRAM/utilization과 예상 peak 및 안전 여유를 비교한다. 다른 GPU나 기존 프로세스를 변경하지 않는다.

## 1. 먼저 검증할 조합

**Python 3.12 + 공식 vLLM 0.8.5 CUDA 11.8 wheel + PyTorch 2.6.0+cu118 + Qwen3-14B-AWQ**를 첫 startup/한국어 요구사항 평가 후보로 권고한다. 이후 충분한 여유가 있을 때 Qwen3-8B BF16을 순차 비교한다. 14B AWQ의 실제 weight가 8B BF16보다 작다. 과거 Qwen3-4B 실험이나 parameter 수만으로 최종 모델을 선정하지 않는다.

- [vLLM 0.8.5 공식 release](https://github.com/vllm-project/vllm/releases/tag/v0.8.5)에 cu118/cu121/default wheel이 실제 존재한다. cu118 asset 크기는 **213,618,745 bytes**다. GitHub asset digest는 조회 시 `null`이므로 설치 담당자가 다운로드 후 SHA256을 기록해야 한다.
- 실제 cu118 wheel METADATA: Python `>=3.9,<3.13`, torch 2.6.0, torchvision 0.21.0, torchaudio 2.6.0, xformers 0.0.29.post2, transformers >=4.51.1, xgrammar 0.1.18, compressed-tensors 0.9.3.
- [Qwen 공식 배포 지침](https://qwen.readthedocs.io/en/latest/deployment/vllm.html)은 Qwen3에 vLLM >=0.8.5를 안내한다. 최신 Transformers 5.x가 자동 선택되지 않도록 **4.51.3**을 고정하는 조합을 우선 검토한다.
- [PyTorch 공식 이전 버전 지침](https://pytorch.org/get-started/previous-versions/)은 2.6.0의 cu118 wheel을 제공한다. [NVIDIA 호환성 문서](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)의 backward compatibility에 따라 driver 535에서 CUDA 11.8 경로가 합리적이다. 시스템 nvcc를 바꿀 필요가 없다.
- wheel tag/문서는 ELF import나 실제 kernel 실행의 증거가 아니다. 설치 후 import, dependency check, GPU3 제한 startup과 추론을 별도로 검증한다. CUDA 12.x minor compatibility 표만으로 최신 PTX/JIT 경로가 모두 실행된다고 판단하지 않는다.

## 2. 정확한 wheel 출처와 constraints

[vLLM cu118 wheel](https://github.com/vllm-project/vllm/releases/download/v0.8.5/vllm-0.8.5%2Bcu118-cp38-abi3-manylinux1_x86_64.whl)을 사용한다. 문서의 cu118 설치 예제에는 과거 0.6.1.post1 버전이 남아 있으므로 예제 문자열을 그대로 사용하지 않는다.

다음 SHA256은 [공식 cu118 index](https://download.pytorch.org/whl/cu118/)에 게시된 값이다. 실제 파일 다운로드 검증은 별도로 필요하다.

| Python 3.12 wheel | SHA256 |
| --- | --- |
| [torch 2.6.0+cu118](https://download.pytorch.org/whl/cu118/torch-2.6.0%2Bcu118-cp312-cp312-linux_x86_64.whl) | `9f7d170d6c78726945d95fcc3a3d7601f36aed0e6e0dc9ca377a64d6a8fd7b3a` |
| [torchvision 0.21.0+cu118](https://download.pytorch.org/whl/cu118/torchvision-0.21.0%2Bcu118-cp312-cp312-linux_x86_64.whl) | `5d3679e0df9ab1725eaa7300d550cf8fe0a477119483bef12673957f30c768dc` |
| [torchaudio 2.6.0+cu118](https://download.pytorch.org/whl/cu118/torchaudio-2.6.0%2Bcu118-cp312-cp312-linux_x86_64.whl) | `e77fe770130b54fdbcecda829024fbd4235075e905f5c6019c19664577c70e1d` |
| [xformers 0.0.29.post2 cu118](https://download.pytorch.org/whl/cu118/xformers-0.0.29.post2-cp312-cp312-manylinux_2_28_x86_64.whl) | `2072f98dbeea10aebbc69e0e4551a153961c20b544d2ef7e57800395095b8c91` |

xformers의 manylinux_2_28 tag는 host glibc 2.31 범위 안이다. PyTorch cu118 METADATA는 CUDA runtime/nvrtc 11.8.89, cuDNN-cu11 9.1.0.70, NCCL-cu11 2.21.5, Triton 3.2.0, SymPy 1.13.1 등을 고정한다. CUDA 12/13용 torch가 resolver에서 섞이지 않도록 CUDA local version을 포함해 고정한다.

Resolver 후보 constraints는 다음과 같다. **설치 확인을 마친 lock file이 아니며**, 실제 설치 담당자가 dependency resolution/pip check 후 확정한다.

```text
torch==2.6.0+cu118
torchvision==0.21.0+cu118
torchaudio==2.6.0+cu118
xformers==0.0.29.post2
transformers==4.51.3
tokenizers==0.21.1
huggingface-hub==0.31.1
safetensors==0.5.3
xgrammar==0.1.18
compressed-tensors==0.9.3
outlines==0.1.11
outlines_core==0.1.26
numba==0.61.2
numpy==1.26.4
ray==2.43.0
cupy-cuda12x==13.4.1
mistral_common==1.5.4
opencv-python-headless==4.11.0.86
```

vLLM의 `ray[cgraph]` dependency는 `cupy-cuda12x`를 끌어온다. V0/단일 GPU/uni executor에서는 cgraph를 사용하지 않지만 resolver 결과에서 이 부가 패키지를 누락해 기록하면 안 된다. CuPy 13.4.1 metadata의 직접 dependency는 numpy<2.3와 fastrlock이다. 이 패키지가 있다는 이유로 CUDA 12 cgraph가 현재 host에서 검증됐다고 표시하지 않는다. Backend `.conda`와 이 runtime 환경을 분리한다.

## 3. 모델 pin과 실제 weight manifest

두 모델은 공식 Qwen 배포이며 API metadata에서 `apache-2.0`, `gated=false`를 확인했다. Weight 외 tokenizer/config/license도 동일 revision으로 고정한다. 아래 값은 HF 게시 manifest이며 내려받은 byte를 직접 hash한 결과가 아니다.

| 모델 | full revision | 실제 safetensors bytes / GiB | 실행 precision |
| --- | --- | ---: | --- |
| [Qwen3-14B-AWQ](https://huggingface.co/Qwen/Qwen3-14B-AWQ) | `31c69efc29464b6bb0aee1398b5a7b50a99340c3` | 9,976,690,240 / 9.292 | W4A16, group 128, zero-point, FP16 activation |
| [Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) | `b968826d9c46dd6066d109eabc6255188de91218` | 16,381,516,776 / 15.256 | BF16 |

14B AWQ의 HEAD lastModified는 2025-05-21, 8B는 2025-07-26이었다. 두 config의 `model_type`은 `qwen3`, architecture는 `Qwen3ForCausalLM`, `head_dim=128`, KV heads=8이다. 14B는 40층, 8B는 36층이다. 두 config의 max_position_embeddings=40960을 초기 serving 길이로 그대로 사용하지 않는다.

| 모델 / safetensors 파일 | bytes | 게시 SHA256 |
| --- | ---: | --- |
| 14B `model-00001-of-00002.safetensors` | 4,988,339,832 | `668eb0f1356638310db286f4819b223c12e3916934123f1a81b2b2c0e148c6a2` |
| 14B `model-00002-of-00002.safetensors` | 4,988,350,408 | `c3c1625df80fe01211038bfa520629ebde6adf776556aa80cd49696d986d6657` |
| 8B `model-00001-of-00005.safetensors` | 3,996,250,744 | `31d6a825ae35f11fb85b195b4c42c146c051e446433125a215336abdf95cbf5f` |
| 8B `model-00002-of-00005.safetensors` | 3,993,160,032 | `5991236cea6fe21f3d43cab0f0e84448734fbbe0789816202989f2ddc9d18282` |
| 8B `model-00003-of-00005.safetensors` | 3,959,604,768 | `c5185c4794be2d8a9784d5753c9922db38df478ce11f9ed0b415b7304d896836` |
| 8B `model-00004-of-00005.safetensors` | 3,187,841,392 | `b5ee7de71fbf17db3d5704e0c8f2bc7d005ca9e1d7ca2aeb19827b0cfcaa917a` |
| 8B `model-00005-of-00005.safetensors` | 1,244,659,840 | `20c2d6366ab85c90786ccdd829cd2b9e7d30ef3b2ebbb998280e7e4014b542ff` |

Metadata 출처: [14B blobs API](https://huggingface.co/api/models/Qwen/Qwen3-14B-AWQ?blobs=true), [8B blobs API](https://huggingface.co/api/models/Qwen/Qwen3-8B?blobs=true). 이 API의 main 응답은 변할 수 있으므로 위 full revision과 실제 다운로드 manifest를 함께 보존한다.

## 4. 첫 실행 예산과 옵션

KV 계산은 `2 × layers × KV_heads × head_dim × 2bytes × tokens × sequences`다. FP16/BF16 KV, TP1, 4096 tokens, seq1일 때 14B는 **640MiB**, 8B는 **576MiB**다. 2048 tokens에서는 각각 절반이다. Weight-only 크기와 이 KV 계산에는 CUDA context, activation, kernel workspace, quant repack, PyTorch allocator 및 로딩 중 peak가 빠져 있다.

현재 **추정 peak**는 14B AWQ 약 14–18GiB, 8B BF16 약 19–23GiB다. 보장값이 아니며 실행 직전 free/util 측정과 별도 안전 여유가 필요하다. Root 실행 계획은 14B의 peak 18432MiB에 여유 7275MiB를 더해 측정 free 36373MiB와 비교하는 것이다. 이 수치는 특정 측정 시점의 계획이며 다음 실행 때 재검사한다.

[v0.8.5 engine arguments](https://docs.vllm.ai/en/v0.8.5/serving/engine_args.html)와 [CLI source](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/entrypoints/openai/cli_args.py)에서 아래 옵션의 존재를 확인했다. 다운로드·startup을 수행한 명령이 아니라 설치 후 검증할 설정이다.

```text
CUDA_VISIBLE_DEVICES=3
VLLM_USE_V1=0
VLLM_ATTENTION_BACKEND=FLASH_ATTN
VLLM_FLASH_ATTN_VERSION=2

--tensor-parallel-size 1
--distributed-executor-backend uni
--disable-frontend-multiprocessing
--enforce-eager
--dtype half
--max-model-len 4096
--max-num-seqs 1
--max-num-batched-tokens 4096
--block-size 16
--num-gpu-blocks-override 256
--gpu-memory-utilization 0.50
--swap-space 0
--no-enable-prefix-caching
--guided-decoding-backend xgrammar
--host 127.0.0.1
```

`half`는 AWQ용이며 8B 비교 시 `bfloat16`으로 바꾼다. quant kernel은 실제 log에 기록하고 AWQ/Marlin 자동 선택 결과를 검증한다. [v0.8.5 hardware 표](https://docs.vllm.ai/en/v0.8.5/features/quantization/supported_hardware.html)는 Ampere의 AWQ/Marlin 지원을 명시한다. Qwen3의 block-FP8는 이 버전에서 A100 대안으로 선택하지 않는다.

SM80에서는 [공식 fa_utils](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/attention/utils/fa_utils.py)가 FlashAttention2를 선택하며, [build 정의](https://github.com/vllm-project/vllm/blob/v0.8.5/cmake/external_projects/vllm_flash_attn.cmake)에 따라 vLLM 내부에 번들된다. 별도 flash-attn 패키지를 설치할 필요가 없다. 이는 import/kernel smoke test를 대체하지 않는다.

`gpu_memory_utilization=0.50`은 전체 메모리의 runtime 예산이며 모든 외부 allocation의 hard cap이 아니다. eager로 CUDA graph를 없애고 KV block 수를 제한하더라도 startup peak를 별도로 감시한다. Root 계획은 free<6144MiB 또는 자기 프로세스의 예산 초과 시 **자기가 시작한 service process group만** 중단하는 것이다. 기존 GPU 프로세스를 종료하거나 다른 GPU로 이동하지 않는다.

## 5. JSON·tool protocol과 비교 범위

v0.8.5에서는 요청의 `guided_json` 및 `chat_template_kwargs={"enable_thinking": false}`를 사용한다. 최신 vLLM의 `structured_outputs` 필드를 그대로 보내지 않는다. Qwen 공식 문서는 0.8.5에서 non-thinking과 reasoning parser의 동시 사용을 지원하지 않는다고 명시하므로 초기 JSON 평가에는 reasoning parser를 켜지 않는다. 자동 tool calling을 별도로 평가할 때의 Qwen3 parser는 `hermes`다. [Qwen 배포 문서](https://qwen.readthedocs.io/en/latest/deployment/vllm.html), [v0.8.5 structured output](https://docs.vllm.ai/en/v0.8.5/features/structured_outputs.html)

Schema 강제는 JSON 구조를 제한한다. 한국어 부정/조건, target 제외 구문, 복수 변경, 단위와 수치의 source grounding, 모호성 판단은 별도 의미 평가가 필요하다. 품질 순위·critical-error rate·latency는 아직 이 조사에서 측정하지 않았다. [평가 계획](model_evaluation_plan.md)에 따라 동일 prompt/schema/dataset으로 14B AWQ와 8B BF16을 비교한다.

| 이전 shortlist | 이번 구형 driver 첫 실행 후보와의 관계 |
| --- | --- |
| Qwen3.8-27B | [최신 recipe](https://recipes.vllm.ai/Qwen/Qwen3.8-27B)는 Qwen3_5 architecture, Transformers>=5.8, 최신 parser/build를 사용한다. vLLM0.8.5 registry에 해당 architecture가 없다. 현재 cu118 조합에 바로 얹을 수 없다. |
| Gemma4-31B QAT | 공식 QAT artifact가 있다는 장점은 유지되지만 Gemma4 architecture/parser가 0.8.5에 없다. 이전 추정 peak 26–32GiB와 별개로 실행 가능한 최신 build 검증이 선행돼야 한다. |
| Gemma4-12B | [최신 recipe](https://recipes.vllm.ai/Google/gemma-4-12B-it)는 unified architecture와 cu129/nightly 또는 CUDA13 경로를 안내한다. 작은 모델 크기만으로 현재 driver에서 실행 가능하다고 판단하지 않는다. |

최신 후보를 품질 때문에 탈락시키는 결정은 아니다. 시스템 변경 없는 구체적인 첫 실행 경로와 후속 비교 후보를 구분한다. RTX5090은 SM120이므로 이 cu118 runtime을 그대로 재사용할 대상으로 보지 않는다. Application/schema/prompt/model identity는 공통으로 유지하고, RTX용 runtime build는 별도 검증한다.
