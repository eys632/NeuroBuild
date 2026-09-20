# Gemma 4 31B QAT Q4_0: A100 사전 자원 계획

2026-09-20. **PRELIMINARY_SOURCE_ESTIMATE — 모델 미다운로드, GGUF header 미검증,
Gemma GPU 기동·inference·peak 측정 없음.** 이 검토는 source/config/기존 build
메타데이터만 읽었다. 이전 Qwen peak를 새 모델의 실측값으로 사용하지 않는다.

결론: 아래 고정 조건과 실제 GGUF 검증을 전제로 **전체 peak 계획값 28,672 MiB**는
합리적인 보수 추정이다. 큰 미계상 버퍼가 반드시 필요하다는 source 근거는 발견하지
못했다. 그러나 graph와 driver 비용은 여전히 allowance이며 수학적 상한·hard cap·
기동 PASS가 아니다. 현재 조사만으로 12B로 낮춰야 할 구체적인 자원 blocker는 없다.
header가 가정과 다르거나 남은 CPU gate가 실패하면 이 판단을 그대로 사용하지 않는다.

## 고정 범위와 입력

- GPU3 한 장만 CUDA logical0으로 노출, UUID 확인, A100 SM80, driver535/CUDA11.8.
- native `llama.cpp@f072b103714dfa1eee531f80b24512faf38e3dd2`의 기존 binary 재사용.
- context4096, sequence1, logical batch64/ubatch64, K/V F16, flash attention OFF,
  CUDA graphs OFF, `swa_full=false`, fit/context-shift OFF.
- 모든 transformer/output layer를 GPU에 요청하고 실패 시 자동 CPU/다른 GPU 전환 없음.
  native loader가 입력 token embedding을 CPU에 두는 고정 동작은 아래에 따로 설명한다.
- text-only, 별도 mmproj/vision/audio/drafter 없음. MTP/speculative/LoRA/embedding
  output/checkpoint 캐시를 켜지 않는다. 단일 요청만 처리한다.
- 외부 GGML/CUDA device/allocator/compute 환경 override는 기존 guard처럼 제거한다.

선택 metadata는 공식
`google/gemma-4-31B-it-qat-q4_0-gguf@59dde24573e7e61570dba08b18a2e1fe246955ed`,
파일 `gemma-4-31B_q4_0-it.gguf` 17,651,001,568 bytes,
원격 LFS SHA `179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b`다.
이는 실제 다운로드 hash 검증이 아니다.
[고정 artifact metadata](https://huggingface.co/api/models/google/gemma-4-31B-it-qat-q4_0-gguf/revision/59dde24573e7e61570dba08b18a2e1fe246955ed?blobs=true).

공식 QAT unquantized base
`google/gemma-4-31B-it-qat-q4_0-unquantized@1e4d8beecacb8b7590c1d8bedd7335f687bf311f`
config는 hidden5376/vocab262144/intermediate21504/60층,
SW50+global10, SW window1024, SW16 KV heads×256/global4×512,
`hidden_size_per_layer_input=0`, `num_kv_shared_layers=0`,
`attention_k_eq_v=true`, tied embedding=true, MoE=false, double-wide MLP=false다.
로컬 metadata 파일 SHA는
`95b105ad23b315067985415e721ab9c19cfcf90918b34ea0fa479a08489d86b7`.
GGUF 카드의 QAT base 관계는 확인됐지만 GGUF 변환에 사용한 exact base revision은
별도로 선언되지 않았으므로 이 config와 실제 header의 일치를 확인해야 한다.
[QAT config](https://huggingface.co/google/gemma-4-31B-it-qat-q4_0-unquantized/blob/1e4d8beecacb8b7590c1d8bedd7335f687bf311f/config.json).

## 전체 peak 계획 산술

| 항목 | 근거 | 계획 MiB |
| --- | --- | ---: |
| 모델 weight | 전체 GGUF 16,833.307 MiB를 올림; CPU input embedding 비용도 공제하지 않음 | 16,834 |
| F16 K/V | SW cache1000 + global320; K/V 공유 절감 미공제 | 1,320 |
| 가장 큰 weight의 F32 변환 임시 공간 | vocab262144 × hidden5376 × 4bytes | 5,376 |
| graph/activation/scheduler/logits | ubatch64, full context cache의 비-flash attention 포함 | 2,048 |
| CUDA driver/context/modules/handles | 실제 새 모델 비용 미측정; cuBLAS workspace 포함 | 1,024 |
| 추가 pool temporaries/정렬/로딩 버퍼 여유 | weight 변환과 동시에 사는 activation/output 변환, VMM rounding 포함 | 1,024 |
| 추가 불확실성 여유 | header·allocator fragmentation·비정형 부가 비용 | 1,046 |
| **전체 추정** | **16,834+1,320+5,376+2,048+1,024+1,024+1,046** | **28,672** |

주어진 free36,373 MiB에서 이 추정치를 빼면 7,701 MiB가 남는다.
최소 safety7,275 MiB보다 426 MiB 크며, 전체 허용 예산29,098 MiB 이하다.
이는 과거 baseline의 산술이다. 기동 직전 fresh 측정에서도 같은 정책을 통과해야 하며
다른 사용자의 이후 할당이나 짧은 peak를 polling watchdog이 선제 예약해 주지는 않는다.

## Weight 중복과 로딩

Gemma graph loader는 output tensor가 없으면 token embedding을
`TENSOR_DUPLICATED`로 output용 생성한다. 공통 loader는 그 tensor를 OUTPUT
buffer 목록으로 분류한다. 입력 embedding은 공통 model loader가 항상 CPU에 두며,
반복 layer와 output은 요청된 GPU에 배치한다. 따라서 tied 경우의 두 복사본은
CPU input + GPU output이다. 전체 GGUF bytes를 GPU weight proxy로 이미 계산했으므로
거기에 같은 embedding의 GPU 복사본 한 벌을 다시 더하는 것은 중복 계상이다.
같은 buffer-type context의 duplicate는 기존 tensor를 재사용하는 경로도 있다.
[Gemma tensor 생성](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/gemma4.cpp#L46),
[input/output 배치](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-model.cpp#L1535),
[duplicate buffer 선택](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-model-loader.cpp#L1163).

이 설명은 GPU memory에 한정된다. mmap/CPU tensor/pinned upload의 host RAM은 별도다.
업로드 코드는 chunked host staging buffer와 기존 destination tensor를 사용하며
GPU weight 전체를 한 번 더 복제하는 staging 경로는 확인되지 않았다. 해당 임시 upload
backend는 로딩 후 해제된다. per-layer embedding은 config가0인 경우 tensor 생성과 graph
분기가 실행되지 않는다. actual header가0이 아니면 이 추정은 무효다.
[upload](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-model-loader.cpp#L1509),
[per-layer embedding 분기](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/models/gemma4.cpp#L134).

## KV·graph·출력 버퍼

SW cells는 `pad256(min(4096, 1024+64))=1280`이다.
`50 × 1280 × 16 × 256 × 2(K,V) × 2bytes / 2^20 =1000 MiB`.
global은 `10 × 4096 × 4 × 512 × 2 × 2 / 2^20 =320 MiB`.
공유 key/value나 기타 절약을 주장하지 않는다. `swa_full=true`이면 SW가4096cells가 되어
KV3520 MiB로 증가하므로 **이 계획의 조건 위반**이다.
[고정 SWA allocator](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-kv-cache-iswa.cpp#L74).

startup graph reservation의 token 수는 `min(context, ubatch)=64`이며 full KV 상태에서
prefill, decode, prefill 순으로 reserve한다. single GPU의 pipeline parallel은 비활성이며
scheduler copy 수는1이다. graph allocator는 parent/view의 최종 사용 뒤 공간을 재사용하고,
더 큰 compute buffer가 필요하면 이전 buffer를 먼저 해제한다. 60층의 모든 attention
score나 세 차례 reserve의 전체 버퍼가 각각 영구 누적된다고 계산하지 않는다.
[context reservation](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-context.cpp#L582),
[lifetime allocator](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-alloc.c#L795),
[scheduler copies](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-backend.cpp#L1872).

활성 크기 점검: global attention score 한 장은
`4096×64×32×4=32 MiB`, SW score는10 MiB, 최대 FFN activation 한 장은
`21504×64×4=5.25 MiB`, residual 한 장은1.3125 MiB다.
logits를 보수적으로64행까지 잡으면 `262144×64×4=64 MiB`이며,
soft-cap/출력 복사/sampling buffers까지 graph 및 추가 pool allowance에 포함한다.
비-flash KQ는 F32 accumulation이며 softmax와 V 연산도 존재한다. 2GiB graph allowance는
이 크기와 lifetime reuse에 근거한 여유 추정이지 exact allocator dry-run 결과가 아니다.
[attention graph](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-graph.cpp#L2658),
[output buffers](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/src/llama-context.cpp#L2056).

## CUDA matmul과 retained pool

실제 기존 CMake cache는 SM80-real, CUDA graphs OFF, FORCE_MMQ OFF, NO_VMM OFF다.
cache SHA `c456e964f4bf310932fb8ace22a06ed69bf8980819f0fdbe634c2d558e5ab001`.
Q4_0는 MMQ/MMVQ 지원 type이고 A100의 MMA 경로는 일반적인 F32 activation/output에서
quantized weight를 직접 사용하며 작은 activation quantization buffer를 만든다.
하지만 dtype/view-padding 분기는 cuBLAS로 갈 수 있어 거대한 weight 변환을0으로
계산하지 않았다. 일반 quantized fallback은 A100에서F16이지만 F32 precision 경로까지
남겨 5376 MiB를 계상한다. FFN의 가장 큰 dense 행렬은5376×21504, F32로441 MiB이며,
일반 layer별 행렬은 vocabulary output보다 작다.
[dispatch](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-cuda/ggml-cuda.cu#L1824),
[MMQ](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-cuda/mmq.cu#L266),
[cuBLAS temporaries](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-cuda/ggml-cuda.cu#L1409).

graphs OFF와 단일 backend의 순차 경로에서는 compute stream0의 VMM pool high water를
재사용한다. 이전 작은 행렬의 변환본을 layer마다 별도 보존하지 않는다.
VMM `free`는 stack 위치만 되돌리므로 확보된 물리 페이지는 남으며, 가장 큰 weight와
동시에 필요한 src1/dst/pointer 임시 공간을 추가해야 한다. 그 비용·rounding을 위한
1GiB allowance는 5376 MiB 외에 별도로 둔다. source의32GiB VMM 값은 virtual address
reserve이며 실제 전체 VRAM cap이 아니다. legacy best-fit pool로 바뀌면 이 논리를
사용할 수 없으며 OOM 후 cached-buffer flush를 성공 조건으로 삼지 않는다.
[VMM allocator](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-cuda/ggml-cuda.cu#L535).

기존 동일 GPU3 metadata-only 증거는 VMM=true, granularity2MiB다:
`var/reports/gpu3-vmm-capability.json` SHA
`df019ecec2d0f07227be3612445d4893f793bd1d79af487b7eddb64795c0e2d6`,
`var/reports/gpu3-vmm-granularity.json` SHA
`6f2a34f83dcb284de6ed8451dac4e2268e60102ae381a47146d3ca2e22bb8033`.
이 검토에서는 이를 읽었을 뿐 새 driver/GPU 호출을 하지 않았다.
Ampere cuBLAS 명시 workspace4MiB 외의 context/modules/handles 비용은1GiB 항목에
포함했으며 새 모델에서 아직 측정하지 않았다.
[cuBLAS workspace](https://github.com/ggml-org/llama.cpp/blob/f072b103714dfa1eee531f80b24512faf38e3dd2/ggml/src/ggml-cuda/common.cuh#L1541).

## 기동 전에 필요한 확인

1. 실제 GGUF SHA/header: full tensor coverage·shape/type·정렬·embedding/output 저장과
   duplicate 배치, SW/global 배열, per-layer embedding0, dense/non-MTP 조건을 검증한다.
   파일명 Q4_0만으로 모든 tensor가 Q4_0라고 단정하지 않는다.
2. 동일 verified binary/dependencies, single-device VMM 경로와 설정을 bind한다.
   SWA full-cache, graph, context/ubatch/sequence, model override가 바뀌면 재산정한다.
3. 새 template/vocab/grammar CPU gate를 통과하고 fresh GPU3 preflight가
   **estimated28,672 + 당시 safety margin**을 허용해야 bounded startup을 진행할 수 있다.
4. 첫 startup 뒤 실제 own-process/aggregate peak, context/compute buffer와 최대 context
   prefill·decode probe를 확인한다. 예산 초과나 실패는 종료 사유이며 자동 축소/재시도하지 않는다.
   충분한 실제 자원 증거가 생긴 뒤에만 별도 frozen 품질 진단으로 간다.

header나 graph 증거가 위 가정을 지지하지 못하면 우선 12B의 별도 resource plan을
검토한다. guard의 추정치를 자의적으로 올려 이 모델을 맞추지 않는다.
이 문서는 모델 품질·채택·RTX5090 fit을 판단하지 않는다.
