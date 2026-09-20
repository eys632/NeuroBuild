# 현대 모델의 별도 local runtime 후보 검증 계획

2026-09-20. **Qwen3.8-27B GGUF + llama.cpp는 다음 실행 경로를 조사할 후보이며 아직 채택하지 않았다.** 이 문서는 공식 metadata/source 조사와 사전 검증 순서를 고정한다. 이 후보의 weight 다운로드, build, GPU startup, inference, 품질 평가는 모두 **NOT_RUN**이다. Phase5.x gate를 통과하지 않았으며 Phase6도 시작하지 않는다.

직전 Qwen3-32B thinking 비교는 schema117/120, parser116/120, 의미109/120, raw READY 오판2/58, 잘못 수용한 READY1/120으로 실패했다. 잘린3개를 모두 정답으로 가정해도112/120으로 기존114/120 기준에 못 미친다. 따라서 이번에는 출력 cap 증액이나 같은 prompt 예시 추가를 이어가기보다, [Phase0 shortlist](model_selection_plan.md)에 있던 현대 모델의 실행 경로를 검증한다. 이 판단은 기존32B의 모든 설정이 실패한다는 증명도 새 모델의 우위 주장도 아니다. [보존 결과](../evaluations/results/phase5x/exposed-generation2-32b-thinking-diagnostic/results.json), [실험 기록](phase5x_experiment_register.md).

## 후보와 재현 기준

| 항목 | 고정 metadata / 계획 |
|---|---|
| 원본 모델 | `Qwen/Qwen3.8-27B` |
| 원본 revision | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` |
| GGUF publisher / repository | `ggml-org/Qwen3.8-27B-GGUF` |
| GGUF revision | `efbb3b1f70a21d97fd4495240648405f7228554f` |
| 파일 | `Qwen3.8-27B-Q4_K_M.gguf` |
| 공개 크기 / SHA256 | `18,973,870,528` bytes =17.670794GiB / `c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747` |
| llama.cpp commit | `f072b103714dfa1eee531f80b24512faf38e3dd2` |
| Build tool 계획 | HOME/project 전용 CMake **3.23.5**, 기존 GCC9.5.0 / nvcc11.8.89 |
| CMake 배포물 | `cmake-3.23.5-linux-x86_64.tar.gz`,46,031,464B; SHA256 `bbd7ad93d2a14ed3608021a9466ae63db76a24efd1fae7a5f7798c1de7ab9344` |
| 시작 scope | Text-only, context4096, parallel1, speculative/MTP/draft/vision projector 없음 |
| Hardware | A100 physical GPU3만; 내부 CUDA0, TP/split 없음 |

원본과 GGUF의 공개 metadata는 Apache-2.0/ungated이며, llama.cpp는 MIT다. GGUF `.src_sha`의 PRIMARY는 위 원본 revision과 일치한다. **ggml-org 변환물이 Qwen 자체의 quantization 검증 결과라는 뜻은 아니다.** 공개 LFS digest는 실제 받은 파일의 검증을 대체하지 않는다. 실제 다운로드 시 LICENSE와 전체 manifest도 보존한다. [원본](https://huggingface.co/Qwen/Qwen3.8-27B/tree/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0), [GGUF 파일 목록](https://huggingface.co/ggml-org/Qwen3.8-27B-GGUF/tree/efbb3b1f70a21d97fd4495240648405f7228554f), [conversion provenance](https://huggingface.co/ggml-org/Qwen3.8-27B-GGUF/blob/efbb3b1f70a21d97fd4495240648405f7228554f/.src_sha), [llama.cpp license](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/LICENSE).

## 다른 runtime을 조사하는 이유

A100의 실제 제약은 Ubuntu20.04/glibc2.31, driver535.183.01, system toolkit11.8이다. 현재 vLLM0.8.5+cu118의 기존 Qwen3 실행 성공은 Qwen3.8의 hybrid architecture 지원 증거가 아니다. 반대로 최신 vLLM registry/recipe의 지원 표기도 현재 host에서 해당 wheel·kernel이 동작함을 보장하지 않는다. llama.cpp의 고정 소스에는 `qwen35` graph, Gated DeltaNet CUDA 연산과 CUDA11.x 분기가 있어, system driver/CUDA를 바꾸지 않는 source-build 경로를 검증할 근거가 있다. **CUDA12+ 또는 driver 변경이 필수로 확인되면 이 경로는 중단하며 libcuda 대체/compat 주입으로 우회하지 않는다.** [현재 환경](runtime_compatibility.md), [모델 graph](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/qwen35.cpp), [CUDA build 조건](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-cuda/CMakeLists.txt).

CUDA backend의 CMake minimum은3.18이므로 PATH의3.16.3은 부족하다. 계획한3.23.5는 `80-real` 명시를 지원한다. 이전 비추적 조사 메모의3.24+ 권고는 필수조건이 아니며 이번 계획은3.23.5다. `native`/`all` GPU architecture 탐색을 사용하지 않고 SM80만 compile한다. CUDA11.8의 Hopper PDL compile 실패 보고가 있으므로 명시SM80로 그 코드 생성 경로를 제외할 수 있는지는 실제 빌드로 확인한다. Runtime의 PDL off만으로 compile 실패가 해결된다고 가정하지 않는다. [CMake3.23.5 architecture 문서](https://cmake.org/cmake/help/v3.23/prop_tgt/CUDA_ARCHITECTURES.html), [upstream CUDA11.8 issue](https://github.com/ggml-org/llama.cpp/issues/26591).

## 디스크와 VRAM 사전 조건

문서 작성 중 read-only `df -B1 /`는 available29,562,568,704B, 약27.5GiB/사용률99%였다. 새 GGUF17.67GiB와20GiB reserve만으로도 현재 공간을 초과하므로 그대로 다운로드하지 않는다. 비활성 MoE의 정확한 revision 디렉터리는 `var/models/ELVISIO--Qwen3-30B-A3B-Instruct-2507-AWQ/9f41ff709102dbe73e614f9365f8280170db268e`이고, `du -s -B1`의 allocated bytes는16,830,500,864B(약15.67GiB)였다. **회수 가능성을 검토한 것이며 아직 삭제하지 않았다.** 향후 정리 전 자기 process가 사용하지 않는지, 재다운로드 manifest와 평가 증거가 보존됐는지 확인한다. 다른 사용자 파일, 환경, 공용 cache는 정리 대상이 아니다. 회수 후에도 source/build/tool/임시파일과20GiB reserve를 다시 산정한다.

원본 config와 allocator 소스의 **계산값**은 다음과 같다. 실제 GGUF header 및 CUDA placement는 아직 미검증이다.

| 구성 | ctx4096 / sequence1에서의 조건부 크기 |
|---|---|
| GGUF file proxy | 18,094.893MiB; GPU resident와 동일하다는 뜻은 아님 |
| F16 full-attention KV | 16층 ×4096 ×4 KV heads ×256 head dim ×K/V2 ×2bytes =256MiB |
| F32 DeltaNet state | 48층 ×128 ×6144 ×4bytes =144MiB |
| F32 conv state | 48층 ×3 ×(6144+2×16×128) ×4bytes =5.625MiB |
| 위 항목 합계 | **18,500.518MiB**, 전체 peak 상한이 아님 |

Recurrent rollback은 `n_rs_seq=0`을 고정해야 위149.625MiB이며 speculative 슬롯을 늘리면 복제된다. 일반 server prompt checkpoint는 host vector 경로이므로 이를 GPU32배로 계산하지 않는다. 초기 검사에서는 checkpoint0/RAM cache0/idle cache off와 CUDA graph off, 최소 batch/ubatch부터 검토한다. Batch1은 prefill 지연에 불리할 수 있어 최종 profile의 성능을 예단하지 않는다. [config](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/config.json), [hybrid cache](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-model.cpp#L2634), [state rows](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-memory-recurrent.cpp#L101), [host checkpoint](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/common/common.cpp#L2282).

GPU3의 이전 baseline free36373MiB/reserve7275MiB를 단순 비교하면 후보 전체 허용량은29098MiB지만 fresh 값이 아니다. 기존 vLLM 후보의25600MiB peak 계획을 자동 승계하지 않는다. Weight padding, graph 생존 tensor, driver/module, cuBLAS 및 stream별 pool의 고수위까지 포함한 별도 상한 근거가 필요하다. Metadata `no_alloc` estimator도 CUDA 연산 내부 pool 전부를 보장하지 않으며 CPU backend 수치를 CUDA 값으로 대신할 수 없다. Watchdog는 사전 예산이나 hard memory isolation을 대체하지 않는다.

`GGML_CUDA_FORCE_MMQ=ON`/FORCE_CUBLAS off는 검토할 build 설정이나 전역 cuBLAS 금지 장치가 아니다. 지원 K-quant/F32 경로는 A100에서 이미 MMVQ/MMQ를 선택할 수 있지만, 비지원 type·non-F32 activation/destination·일부 view/padding·비양자화 연산의 fallback은 남는다. 큰 output matrix의 전체 변환은 조건에 따라 FP16 2425MiB/F32 4850MiB를 추가할 수 있어 실제 tensor와 dispatch로 배제 여부를 확인한다. [matmul 분기](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-cuda/ggml-cuda.cu#L1823), [MMQ 조건](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-cuda/mmq.cu#L266), [dtype와 임시 변환](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-cuda/ggml-cuda.cu#L1622).

## 검증 순서와 중단 경계

1. **HOME 내 build를 먼저 검증한다.** 기존 환경·디스크를 재확인하고 pinned CMake3.23.5/source를 준비한다. CPU에서 낮은 병렬도로 SM80 CUDA 소스를 compile하되 GPU/model 실행은 하지 않는다. `GGML_NATIVE=OFF`, 명시 nvcc/SM80, 불필요 NCCL/CCCL 자동 fetch/graph/SSL 의존을 제한한 설정, binary hash와 linkage를 기록한다. 기존 `.conda` Backend에 GPU dependency를 섞지 않는다. Build/link가 host 정책에서 불가능하면 weight를 받지 않는다.
2. **Artifact/header/tokenizer/grammar와 전체 peak 계획을 확인한다.** 디스크 조건 충족 후 정확한 한 GGUF만 받아 size/SHA를 검증한다. 전체 tensor type/shape/offset/byte coverage와 padding, SSM/KV metadata, embedded tokenizer/template를 확인한다. 원문 정책과 generation2 branch schema의 실제 grammar를 CPU에서 정상·거절 예제로 검증한다. 실제 template의 input+completion이4096 이내인지 측정하고 해당 profile의 startup/prefill/decode 전체 메모리를 보수적으로 계산한다. Runtime estimator에 GPU 초기화가 필요하면 별도 허용 GPU 사전 점검 없이 실행하지 않는다.
3. **Guard와 transport 경계를 검증한다.** Binary만 기존 vLLM launcher에 바꾸지 않는다. 자기 child/process group 종료, parent death, lock, timeout, logging, loopback listener, 허용 UUID 및 free-floor 감시를 fake/CPU 테스트로 검증한다. `CUDA_VISIBLE_DEVICES=3`, 내부CUDA0, main-gpu0/split none/layers all, fit off/parallel1/ctx4096/no-context-shift/offline/local model/no-mmproj를 명시한다. `GGML_CUDA_ENABLE_UNIFIED_MEMORY`는 변수 자체를 없애고 cuBLAS dtype override도 정리한다. 다른 GPU, 외부 모델, CPU spill을 자동 fallback으로 사용하지 않는다.
4. **정확한 profile을 동결한 뒤 실제 제한 평가한다.** Fresh GPU3 free/utilization/swing과 전체 peak+margin을 통과한 경우만 startup·최대길이 prefill/decode·loopback·최종 JSON 검증을 수행한다. Source/model/template/schema/prompt/sampling/예산/서버 epoch와 검토를 freeze→commit→push한 다음 exposed120×1+warmup5를 수행한다. 기존 진단 gate(schema120, 의미≥114, raw READY FP0/58, unsafe accepted READY0/120)를 유지한다. 잘림·timeout·parse 실패·unknown decision은 분모에서 빼거나 non-READY 성공으로 고치지 않는다. 통과해도 별도 동결한 exposed120×3 및 unused v2 평가가 남으며 즉시 채택하지 않는다.

새 runtime의 JSON wire는 명시 profile로 구분한다. 고정 llama-server의 OpenAI 경로는 `response_format: {type: "json_schema", json_schema: {schema: ...}}`를 읽으므로 기존 vLLM `guided_json`/`structured_outputs`를 자동 재시도하지 않는다. Jinja thinking 설정과 `reasoning-format deepseek` 분리를 고정하고 content만 기존 adapter/parser로 보낸다. Reasoning 원문은 저장·열람하지 않으며 usage/종료 상태만 기록한다. Debug HTTP logger가 request/response body를 출력하므로 낮은 verbosity, verbose-prompt 금지와 실제 무누출 검증이 필요하다. [server request parser](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/tools/server/server-common.cpp), [JSON schema 범위](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/grammars/README.md), [body logging](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/tools/server/server-http.cpp).

## 공통 제품 계약과 검증 한계

Application/Domain/IFC 코드는 A100과 RTX5090에서 하나다. 서버별 business logic 복제 없이 build/runtime profile과 명시 wire adapter만 분리한다. 단일 IfcFurniture의 같은층 상대XY 범위, 원문 grounding, generation2→canonical1 parser, 대상 확인과 별도 proposal 승인, immutable revision은 변경하지 않는다. Gold/기존 출력/scorer/품질 gate도 수정하지 않는다. Runtime 구현 후 기존 회귀 suite와 cross-layer 승인 분리 검사를 다시 통과해야 한다.

RTX5090 physical GPU1의 실제 toolkit/driver/build/전체 peak/품질은 **PREDICTED_UNVERIFIED**다. A100의SM80/CUDA11.8 binary와 free 수치를 승계하지 않는다. 새 runtime은 RTX의 필수 현장 검증을 대체하지 않는다.

모든 evaluation gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. 기존120은 exposed regression이고 v2는 모델 호출 전이라는 제한을 유지한다. V2의 과거 root 부분 노출 사건도 보존하여 완전 맹검이라고 부르지 않는다. 이번 후보 계획에 v2 사례별 내용이나 모델 출력을 사용하지 않았다. [v2 자료 경계](hardening_v2_dataset.md), [평가 절차](evaluation_harness.md).
