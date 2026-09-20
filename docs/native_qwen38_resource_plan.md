# Qwen3.8-27B native 후보의 GPU3 자원 검증 계획

2026-09-20. Phase5.x의 제한된 자원 검증이다. 모델 채택, 품질 gate 또는 RTX5090
실행 성공을 뜻하지 않는다. 사용자 지침에 따라 다른 프로세스 존재 자체로 거절하지 않고,
허용 GPU3의 현재 free VRAM/utilization과 후보 전체 예상 peak 및 안전 margin을 비교한다.

## 고정 조건과 예상 peak

고정 llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2`, 실제 확인한 GGUF
`c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747`를 쓴다.
전체 파일18,973,870,528 bytes와851개 tensor의 형상/type/offset/packed coverage를 확인했다.
GPU3→논리CUDA0만, split 없음, all layers/fit OFF, context4096/sequence1,
batch1/ubatch1, K/V F16, recurrent F32/rollback0, CUDA graphs OFF,
prompt/context checkpoint 및 RAM cache OFF다. 상속된 allocator/device override는 제거한다.

현재 binary의 VMM 경로를 compile flags와 symbol로 확인했다. GPU3의 별도 UUID 검사와
드라이버 metadata 조회에서 VMM 지원 및 권장 allocation granularity **2MiB**를 확인했다.
이 조회에는 context 생성, 메모리 할당 또는 모델 실행이 없었다. 이 source는 VMM 실패 시
legacy allocator로 자동 전환하지 않는다. Binary/device/capability가 바뀌면 아래 산정은 무효다.

| 예상 항목 | 예산 MiB | 근거와 한계 |
|---|---:|---|
| 전체 weight proxy | 18,095 | 실제 GGUF 전체 파일을 올림. CPU embedding 배치로 줄여 계산하지 않음 |
| Full-attention K/V | 256 | 16층×4096×4 KV heads×256×K/V×F16 |
| DeltaNet/conv state | 150 | 계산149.625MiB를 올림, sequence1/rollback0 |
| 큰 weight 역양자화 | 4,850 | 최대 output matrix 전체 F32 변환을 방어적으로 포함. 정상 batch1 MMVQ 경로의 예상 비용은 이보다 작음 |
| Graph live buffers | 2,048 | 초기16-token GDN support graph reserve와 이후4096 context의 batch1 graph를 포함하는 보수적 allowance |
| Driver/context/module/handles | 1,024 | 실제 초기화 전 계획 여유. CUDA library의 host 파일 크기를 GPU 사용량으로 등치하지 않음 |
| 추가 pool workspace/alignment | 1,024 | 단일 VMM high-water, 동시 activation/output 임시 버퍼와2MiB rounding을 포함하는 계획 여유 |
| 나머지 불확실성·fragmentation | 1,225 | 위 고정 조건의 미측정 allocator 비용 여유 |
| **전체 예상 peak** | **28,672 (28GiB)** | 실측치·엄밀한 상한·프로세스 hard cap이 아님 |

Graph/module/fragmentation 항목은 실행 전의 보수적 예상이다. 소스 검토의 규모 비교에서
16-token probe의 attention score/logits는 각각6/15.16MiB이며, DeltaNet 출력48개를
모두 더해도 약162MiB다. 이는 완전한 graph liveness 계산이 아니므로2GiB allowance를
두고 별도의 미측정 비용 여유와 free VRAM 안전 margin도 유지한다. 출력 역양자화4,850MiB와
동시 임시 버퍼를 포함하며 단순 weight 크기만으로 적합 판정을 하지 않는다.

## 실행 직전 판단과 제한 실행

D033의 `qwen38-gguf-raw-unicode-v1` 후보에 대해 CPU grammar/final-content/sampling과
실제 vocab/template/raw-reference/context 검증을 모두 마친 뒤 native guard가 파일 hash 확인을 끝내고 GPU3를5회 반복 측정한다.
최대 utilization≤10%, free 변동≤256MiB, margin=`max(6144MiB, ceil(min_free×0.20))`다.
**28,672MiB + margin≤현재 최소 free**일 때만 이 고정 profile의 제한 실행을 허용한다.
과거 free36,373MiB에서는 margin7,275MiB를 더하고426MiB가 남지만, 이 과거 수치가
실행 허가는 아니다. 별도 guard가 실행 직전에 다시 측정해야 한다.

Startup, 공개 합성 최대 문맥 prefill/decode, 반복 요청을 순서대로 확인한다. 자원 probe와
정식 품질 평가는 구분하며 probe로 점수나 실패 분모를 바꾸지 않는다. Child의 실제 UUID와
localhost listener, health/model identity, final JSON 계약을 확인한다. Stdout/stderr 및
reasoning 원문은 버리고 aggregate 자원 수치·latency·token count·status만 보존한다.

Guard는 baseline 대비 전체 GPU used 증가28,672MiB와 free floor를 감시하고, 초과·시간 제한·
오류·parent 종료 시 자신의 child/process group만 정리한다. 외부 할당과 짧은 spike를
완전히 격리하는 장치는 아니므로 감시를 사전 예산의 대체물로 쓰지 않는다.
타인 VRAM/프로세스와 GPU0/1/2는 변경하지 않는다. 조건이 맞지 않거나 OOM 위험을 나타내는
증거가 생기면 이 후보를 실행하지 않으며 다른 GPU/설정으로 자동 우회하지 않는다.

관측한 최대 증가량은 공용 GPU 전체 변화이며 per-process peak라고 부르지 않는다.
자원 검사에 성공해도 source/model/prompt/schema/sampling/runtime evidence를 동결하고
commit/push한 뒤 기존 노출120 진단 및 후속 품질 gate를 별도로 수행한다.
