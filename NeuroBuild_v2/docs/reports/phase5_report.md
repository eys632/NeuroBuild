# Phase 5 — Local Model Runtime / Model Selection / Requirement Pipeline

2026-09-20. **완료.** 전체215 tests PASS/skip0(15.671s), protocol 변경 후 실제3/3추론 PASS, 독립 검토 완료. Commit/push `d6e39c89658c552c59a8049d7198da051290bd3b`와 원격hash일치를확인했다. GPU3 공존 실행은 측정된 free VRAM과 후보 전체 peak+margin으로 판단하며 타인 process를 변경하지 않는다.

## 구현과 선정

Backend와 분리한 `.conda-vllm` Python3.12.14에 공식 vLLM0.8.5+cu118 / Torch2.6.0+cu118 / Transformers4.51.3 / xgrammar0.1.18을 설치했다. Linux64 Conda lock와 148개 wheel SHA256 lock, 파일별 pinned model manifest를 보존했다. Native import/pipcheck/실제 GPU 추론을 통과했으며 시스템 driver535.183.01, CUDA, glibc2.31을 변경하지 않았다.

**내부 개발 모델은 Qwen/Qwen3-14B-AWQ revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`, prompt `requirement_v3.txt`로 선정했다.** Apache2.0 공식 checkpoint, local/offline, trust_remote_code=false, actual AWQ Marlin FP16이다. 비교 후보는 Qwen/Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218`의 BF16이다. 서로 다른 크기이므로 AWQ 단독 손실을 측정한 비교라고 주장하지 않는다.

공통 Application은 loopback HTTP client → JSON Schema → 원문 grounding → deterministic Decimal SI conversion 순서다. LLM은 GlobalId/IFC/승인 권한을 받지 않는다. X/Y·부호·숫자철자·단위를 보존하지 못한 출력, duplicate key, 추가 필드, truncated/tool/reasoning 출력은 거절한다. 외부 주소/proxy/redirect/fallback을 허용하지 않는다. 이 검사만으로 자연어 의미·조건·대상 수식어의 정확성을 증명하지 않는다. 이후 target confirmation과 별도 proposal approval은 필수다.

## 실제 비교 결과

각 run은 고정 development seed20×3, warmup5 제외, temperature0/seed42, max output768, context4096/TP1/concurrency1/eager다. **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 prompt 개선에 사용한 공개 development seed다. Human 검수 또는 unseen 정확도가 아니다. 실패 run/prompt/gold를 변경하지 않고 전부 보존했다.

| Model / prompt | Schema | Parser | 자동 의미 rubric | 모델 READY 오판 / 비실행 gold | 지원 요청 누락 | Mean / p95 seconds |
|---|---:|---:|---:|---:|---:|---:|
| [14B AWQ v1](../../evaluations/results/phase5/qwen3-14b-awq-v1/results.json) |60/60|51/60|45/60|0/33|6/27|2.9605 / 4.2152|
| [14B AWQ v2](../../evaluations/results/phase5/qwen3-14b-awq-v2/results.json) |60/60|60/60|57/60|3/33|0/27|3.0032 / 4.2863|
| [8B BF16 v1](../../evaluations/results/phase5/qwen3-8b-v1/results.json) |60/60|57/60|45/60|6/33|3/27|2.6570 / 3.6554|
| [8B BF16 v3](../../evaluations/results/phase5/qwen3-8b-v3/results.json) |60/60|54/60|54/60|0/33|6/27|2.4280 / 3.6323|
| [14B AWQ v3](../../evaluations/results/phase5/qwen3-14b-awq-v3/results.json) |60/60|60/60|60/60|0/33|0/27|3.0361 / 4.2843|

14B v1은 scope/exclusion 누락, 숫자 표기·축 오류, 복수대상 재작성, 설계요청 분류 문제가 있었다. v2는 대부분 개선했지만 미확인 외부 조건을 참으로 간주한 READY 오판3건이 있어 선정하지 않았다. v3는 inventory/충돌 등의 외부 조건을 주어진 문장만으로 판단하지 않는 일반 규칙과 별도 예제를 보강했다. 같은 v3에서8B는 음의 부호/단위 추출6건이 parser에 거절됐다. 14B v3만 현재 seed gate(schema100%, semantic≥95%, criticalFP0)를 모두 만족했다.

0/33 READY 오판의 Wilson95% 상한은 약10.43%이며 repeated trials는 독립 사례가 아니다. GoldREADY의 대상/축 오류는 이 FP 정의에 포함되지 않으므로 별도 의미 점수를 함께 봐야 한다. v1 F02 대상 손실은 실제로 parser를 통과했다. TTFT/decode tokens/sec/true cold startup은 측정하지 않았다. 결과 manifest의 Gitdirty=true와 sourcehash는 당시 실행코드를 식별하며 이후 protocol 옵션 추가가 과거 결과를 소급 변경하지 않는다.

## GPU 및 운영 검증

허용 physical GPU3만 반복 query했다. Baseline free36373/used3965MiB/util0%, margin7275MiB, model budget29098MiB였다. 14B 예상 startup/inference peak18432MiB, Torch/vLLM fraction0.50; 8B 예상23552MiB/fraction0.60으로 별도 preflight 후 순차 실행했다. Weight 외 KV/workspace/context/allocator를 포함한 추정이며 hard reservation은 아니다.

14B v3 startup health 확인20.362s(2초 polling, filesystem cache 미flush), 실행 중 전체 GPU의 baseline 대비 관측peak 증가11684MiB/최소free24690MiB. 8B v1+v3 동일 서버 구간은17476MiB/최소free18898MiB였다. 타인 workload 변화와0.5초 sampling이 있어 **process 전용 peak나 OOM 불가능 보장으로 해석하지 않는다**. 관측은 [resource report](../../evaluations/results/phase5/qwen3-14b-awq-v3/resource_report.json)에 보존했다.

Guard는 정확한 mask/physical UUID/TP1을 검사하고 free floor 또는 aggregate 증가 제한을 넘거나 GPU query가 실패하면 자신의 child process group만 종료한다. Parentdeath SIGKILL은 Torch import 전 설정하며 guard는 child leader를 reap하기 전 자기 PG 정리를 완료한다. 프로젝트 launcher flock로 중복 기동을 막는다. 다른 process/PID는 종료·변경하지 않는다.

초기 vLLM auxiliary TCPStore가 wildcard bind되는 것을 자기 child socket검사에서 발견했다. 평가 종료 후 자신의 서버를 종료하고 FileStore rendezvous/world1, Gloo/NCCL loopback, IB disable로 수정했다. 수정 후 실제14B의5 TCP listener가 모두127.0.0.1인 것을 [network proof](../../evaluations/results/phase5/qwen3-14b-awq-v3/network_proof.json)로 확인했다. 외부 접속 발생을 확인한 것은 아니며 이전 bind문제를 숨기지 않는다.

## 검토·재현·한계

독립 검토는5 run metric 재계산 및14Bv3 schema/parser/semantic60개 재검증, 원본 archive 비교, launcher lifecycle/resource 경계를 확인했다. [검토 보고](../reviews/phase5_final_review.md)를 따른다. 마지막 전체 unit/real-PostgreSQL/real-IFC regression 수와 actual protocol smoke는 EXECUTION_LOG에 기록한다.

A100은 legacy `guided_json` + `xgrammar:no-fallback` 실제검증이다. 최신 vLLM의 legacy field 무시 문제를 피하도록 client에 명시적 `structured_outputs` dialect를 분리했다. 자동 추측/재시도는 없다. RTX5090은 같은 checkpoint+MarlinW4A16 SM120 공식 source 근거가 있으나 최신wheel resolver/driver/quantkernel/launcher/VRAM/품질은 **PREDICTED_UNVERIFIED**다. [protocol/SM120 검토](../model_protocol_compatibility.md)를 따른다. 이A100 cu118/V0 wrapper를RTX에서검증한것으로보지않는다.

Phase5.x는 새120개 versioned synthetic 자료를40 development/80 heldout로 고정한 뒤 오류·원문 보존·조건·부정 등을 추가 검증한다. 사람 검수가 없더라도 내부 개발은 계속하지만 external pilot 이전 검수는 필수다. Phase6 object resolution/API/browser는 이 Phase의 완료 주장이 아니다.

## 과거 01:00 중단 기록 — 현재 정책과 상태가 아님

다음은 당시 기록이며 현재 결정은 위 현황과 [STATUS](../STATUS.md), [EXECUTION_LOG](../EXECUTION_LOG.md)를 따른다.

2026-09-20 01:00 KST. **Phase5는 완료하지 않았다.** Phase4 remote checkpoint `dd58b596fab2aaa24c5aba4322d56bc5d127440c` 확인 후 허용 GPU와 환경을 조사했다. 현재 중단 조건은 **BLOCKED_GPU_OCCUPIED**다.

### 실제 관측

오직 physical GPU3을 조회했다.

```sh
nvidia-smi -i 3 --query-gpu=index,name,uuid,driver_version,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader
nvidia-smi -i 3 --query-compute-apps=pid,used_gpu_memory --format=csv,noheader
```

| 항목 | 관측 |
|---|---|
| GPU | 3 / NVIDIA A100-PCIE-40GB |
| Driver | 535.183.01 |
| Total / used / free | 40960 / 3965 / 36373 MiB |
| GPU utilization | 0% at inspection |
| Compute process | 3개; 개별 VRAM1746/1772/414MiB |
| 현재 사용자 소유 여부 | `ps -u <현재 uid> -o pid=`의 본인 PID 집합과 대조: 0/3 |
| Root disk | 96%, 약83G free |
| 기존 Backend | .conda Python3.12.14, 약1.4G |
| Cache / private PostgreSQL data | 약803M / 82M |
| Model environment | .conda-vllm 없음 |

다른 사용자의 process 소유자/명령/파일/환경을 조사하지 않았다. GPU compute 목록과 **본인 process 목록**만 비교했고 process를 종료하거나 변경하지 않았다. Phase0에서도 process3개와3965MiB를 관측했으며 이번에도 점유가 유지됐다.

기본 shell의 `python`은 없고 `python3`는 system3.8.10이며 CONDA_PREFIX는 비어 있었다. 이는 Backend 환경 부재를 뜻하지 않는다. Backend는 `.conda/bin/python`으로 실행하여 앞 단계까지 검증했고 시스템 Python은 기본 조사에만 사용했다. 모델 설치는 시작하지 않았으므로 잘못된 shell Python에 package를 설치하지 않았다.

### 정책상 중단 이유

Root AGENTS.md는 “GPU를 실행하기 전 허용 GPU만 점유 확인한다. 예상 밖 프로세스가 있으면 실행을 중단하고 보고한다”라고 정한다. 사용자 자율 실행 지침의 장기 GPU3 점유/타인 process 변경 금지 조건과 함께 적용했다.

현재 0% utilization과 남은 VRAM은 다른 작업과 동시에 모델을 실행해도 된다는 허가가 아니다. **실제 runtime OOM 또는 모든 모델의 메모리 부족을 측정한 것은 아니다.** GPU 사용 조건이 충족되지 않아 필수 실제 benchmark로 진행할 수 없다는 상태다. 다른 GPU fallback, process 종료, driver/CUDA 변경, 작은 모델/mock으로 gate 대체를 하지 않았다.

### 미실행과 재개 조건

- .conda-vllm 생성, torch/vLLM/Transformers 설치, weight 다운로드: NOT_RUN.
- Model startup/inference, schema/semantic/critical-error 평가, latency/VRAM benchmark: NOT_RUN.
- Final model 선정: NOT_SELECTED. Phase0 공식 shortlist는 조건부 계획으로 유지한다.
- Driver535/glibc2.31에서 실제로 실행 가능한 model/runtime 조합: UNVERIFIED. 시스템 변경이 필요하다고 단정하지 않는다.
- RTX5090: UNVERIFIED. Phase5.x~11은 미시작. Browser Internal MVP는 아직 완료되지 않았다.

GPU3를 사용할 수 있는 시점에 점유 상태부터 다시 확인한다. 이후 디스크와 공식 model/runtime ABI·license·quantization 조건을 검토하고 project `.conda-vllm`에 한 후보씩 준비하여 실제 평가한다. Phase1~4의 common source와 108 tests를 유지한다. 현재 상태/실행 근거/재개 조건을 commit/push하여 작업을 보존한다.
