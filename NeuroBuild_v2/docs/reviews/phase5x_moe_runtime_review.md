# 30B-A3B AWQ header 및 runtime 독립 검토

2026-09-20 KST. **구조 감사 PASS / 실제 startup 로그 검토 PASS / 의미 정확도 gate 미판정.**
검토자는 CPU 파일 읽기만 수행했다. HTTP 추론·health 요청, GPU 조회, socket 조회,
프로세스 변경, package 설치 또는 tensor 데이터 로딩은 수행하지 않았다.

## 고정 artifact의 실제 header

대상은 제3자 `ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ`, revision
`9f41ff709102dbe73e614f9365f8280170db268e`다.
[후보와 정적 검토](../moe_instruction_candidate.md),
[manifest](../../runtime/models/qwen3-30b-a3b-instruct-2507-awq.json)를 기준으로
완료된 safetensors 4개에서 8-byte length와 제한된 JSON header만 읽었다.
`.part`, tensor 본문, torch는 읽거나 import하지 않았다.

Config로 독립 생성한 **56,115개 tensor**와 실제 header 및 고정 index가 일치했다.
Expert qweight/qzeros/scales55,296개, attention576개, layer norm192개,
router48개, embedding/final norm/lm_head3개를 포함한다. F16/I32 dtype과
input/output·group128·4-bit packing 기반 shape, byte size, 연속적이며 겹치지 않는
data offset 및 shard 배치를 검사했다. 누락·추가·중복·불일치 **0개**다.

| Shard | 실제 tensor 수 | 읽은 length+header bytes |
|---|---:|---:|
| 1 | 15,777 | 1,902,576 |
| 2 | 18,042 | 2,190,272 |
| 3 | 18,020 | 2,187,312 |
| 4 | 4,276 | 515,024 |
| 합계 | **56,115** | **6,795,184** |

예상·실제 tensor data는16,802,672,640bytes로 index metadata와 같다.
Config/index SHA 및 4개 shard의 파일 크기도 manifest와 대조했다.
보존된 [header 보고서](../../evaluations/results/phase5x/moe-instruct-v1-launch/safetensors_header_audit.json)의 SHA-256은
`d9d03a9c1c5e9e2b566b357f44949d2e88f1ad9855d2527c74a81a160cbc24ab`다.
이 검토는 downloader의 전체 weight SHA 검증을 재수행하거나 tensor 값·양자화
정확도를 증명한 것이 아니다. Quantized loader의 missing-weight 검사 생략 가능성을
보완하는 저장 구조 검사다.

## 실제 startup 관측

관측 파일은 `var/logs/qwen3-30b-instruct-v1-server.log`와 guard 보고서다.
[실행 설정](../../evaluations/results/phase5x/moe-instruct-v1-launch/launch_config.json)과
[초기 guard snapshot](../../evaluations/results/phase5x/moe-instruct-v1-launch/initial_resource_report.json)을 보존했다. Child PID3409891,
guard 시작2026-09-19T23:11:02.235538Z, launcher SHA-256은
`6e0c84166861e9556a6be53a0e4f69f43381388d1e6d7f3feadae79f879388ab`다.

로그는 physical GPU3→logical0 UUID 확인, FileStore/world_size1,
**auto AWQ→awq_marlin** 선택과 engine `quantization=awq_marlin`을 기록한다.
FP16, V0/uni, TP1, sequence1, context/batched-token cap4096,
FlashAttention, eager 실행, CPU offload0/swap0, reasoning 비활성이다.
KV는 자동 계산5161 blocks를 **256 blocks×16 tokens**로 낮췄고 CPU blocks는0,
4096-token concurrency는1.00이다. 08:11:44 KST에 application startup 완료가 기록됐다.
이 관측 범위에 OOM, traceback, kernel 비호환 또는 plain-AWQ fallback 로그는 없다.

Model load는15.7406GiB·23.799536초였다. vLLM 프로파일은 자신이 관측한
total39.39GiB×.60=23.64GiB, weight15.74GiB, non-torch0.09GiB,
activation peak0.24GiB를 보고했다. Nominal board40GiB×.60=24GiB와 실제 vLLM
프로파일23.64GiB를 구분한다. 실제 KV가7.56GiB 적재됐다는 뜻도 아니다.
KV block override가 뒤따른다.
Runtime utilization과 torch allocator fraction은 모두.60이다.

보존된 guard **elapsed95.993초 / 176 samples** snapshot은 RUNNING,
baseline 대비 aggregate 최대 증가17,126MiB, 최소 free19,248MiB였다.
이는 증가 한도25,600MiB와 free floor7,275MiB 안이다. Baseline free36,373MiB와
추정24,576MiB에 대해 preflight5개 표본이 통과했다. 이 값들은 GPU 전체의 시간별
표본이며 특정 process의 정확한 peak, 이후 추론 peak 또는 강한 격리를 보장하지 않는다.

## 경고의 해석과 남은 검증

`packed_modules_mapping` 부재 경고를 무시하거나 숨기지 않았다. 설치 소스에서
AWQ skip은 prefix substring 기반이고, router는 quant_config=None,
lm_head_quantized는 기본 false이며 Qwen3MoE loader 자체가 QKV와 expert를 매핑한다.
현재 제외 대상 `mlp.gate`/`lm_head`와 실제 header·성공한 load를 대조했을 때
이 경고가 현재 구성의 로딩을 차단한다는 증거는 없다. 다른 quantization 설정으로
일반화하지 않는다.

최적화된 MoE tuning JSON 부재는 default tuning config 사용 경고다.
설치된 `fused_marlin_moe` 경로도 이 공통 config 선택 함수를 호출하므로 경고만으로
plain AWQ 또는 CPU emulation으로 바뀌었다고 볼 수 없다. Eager의 async-output
비활성 경고도 설정과 일치한다. HF generation config는 서버 기본값에 반영되지만,
평가의 명시적인 sampling profile 요청값과 manifest를 별도로 확인해야 한다.

이 검토는 source와 startup 로그의 일치 확인이며 kernel tracing, HTTP health,
loopback listener 검사 또는 structured-output/한국어 BIM 정확도 평가를 대신하지 않는다.
후속 진단·정식 development·holdout gate와 guard 종료 증거가 필요하며,
RTX5090는 계속 **PREDICTED_UNVERIFIED**다.
