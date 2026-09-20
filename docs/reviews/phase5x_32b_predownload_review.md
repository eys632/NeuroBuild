# 32B AWQ 다운로드 전 독립 검토

2026-09-20 KST. **최종 25GiB / fraction0.60 / allowance0 계획에 정적 blocker를 발견하지 못했다.**
이는 고정 manifest 다운로드와 이후 검증을 위한 조건부 계획 검토다.
32B 적재·kernel·메모리 peak·품질은 **PREDICTED_UNVERIFIED**이며 실행 성공을 승인한 기록이 아니다.
모델 weight·GPU·타 사용자 프로세스에 접근하지 않았고 설치·다운로드·실행·종료를 수행하지 않았다.

검토 대상은 [공식 32B 후보 계획](../dense_32b_candidate.md),
[manifest](../../runtime/models/qwen3-32b-awq.json),
[메모리 산정](../../evaluations/results/phase5x/32b-predownload/predownload_memory_plan.json),
[정적 검토](../../evaluations/results/phase5x/32b-predownload/static_feasibility.json),
그리고 현재 [launcher](../../scripts/model_server.py)와 [preflight](../../scripts/gpu_preflight.py)다.
초기 파일의 .575/24,576MiB는 최종 계획과 상충했지만, 담당자가 아래 값으로 갱신한 파일을 다시 확인했다.

| 최종 고정 대상 | 값 |
|---|---:|
| GPU / dtype / TP | A100 physical3 / FP16 / 1 |
| Whole startup/inference peak 추정 | 25,600MiB |
| 추가 guard allowance | **0MiB** |
| vLLM / Torch fraction | 0.60 / 0.60 |
| Context / 최대 batch tokens / sequence | 4096 / 4096 / 1 |
| KV blocks / FP16 KV bytes | 256×16tokens / 1,073,741,824bytes |
| 실행 방식 | eager, V0/uni, AWQ Marlin, CPU offload0, swap0 |

64layers·8KV heads·명시 head_dim128의 KV 산술은1GiB와 일치한다.
Hidden5120/attention heads64에서 head_dim80을 추정하면 잘못된 산정이 된다.
Weight4개19,325,481,744bytes, 전체13파일19,341,523,989bytes 합계를 재계산했다.
Index metadata.total_size와 실제 shard 크기가 다른 점을 계획이 보존하고 있으며,
다운로드 예산에는 pinned LFS 실제 파일 크기를 쓴다. Weight shape/content 확인은 아직 수행하지 않았다.
계획에 인용한 설치본 소스12개 hash도 현재 환경 파일과 일치했다.

## Guard의 실제 처리

`LaunchConfig`는 allowance0을 허용하고 CLI가 이를 그대로 전달한다.
실제 aggregate 증가 중단선은 `min(estimated_peak + allowance, available_budget)`이다.
**`--estimated-peak-mib 25600 --peak-allowance-mib 0`을 함께 명시해야 한다.**
현재 기본 allowance1024를 생략하면 중단선이26,624MiB가 되어 이번25GiB 계획과 달라진다.
Source 변경 없이 명시 인자로 최종 계획을 표현할 수 있다.

Root 제공 free36,373MiB를 입력한 순수 budget 계산은 다음과 같다. GPU를 새로 측정한 값이 아니다.

- Margin=`max(6144,ceil(36373×0.20))`=7,275MiB.
- Model budget=29,098MiB, 계획 peak+margin=32,875MiB, 추가 잔여=3,498MiB.
- 두 fraction의 nominal40GiB 기준 cap24,576MiB는 budget29,098MiB보다 작다.
- Allowance0의 aggregate 증가 중단선은25,600MiB이며, 별도의 free floor는7,275MiB다.

순수 Python 계산과 launch command 구성으로 위 값 및 context4096/seq1/KV256/FP16/eager 인자를 확인했다.
구성한 명령은 실행하지 않았다. 설치본 vLLM에서 CPU offload 기본값은0이며 launcher는 swap0을 명시한다.
현재 checkpoint의 AWQ 자동 감지는 정적 Marlin 조건에 부합한다는 선행 검토를 전제로 한다.
실제 적재 로그에서 `awq_marlin`을 확인하기 전에는 kernel 경로를 검증했다고 기록하지 않는다.

Torch fraction은 CUDA가 보고하는 실제 total에 적용된다. 제공된 약39.39GiB에서는 약23.63GiB이고,
이것이 전체 프로세스의25GiB hard cap은 아니다. vLLM fraction도 profiling/KV 계획값이다.
전체 추정에는 CUDA/non-Torch와 fragmentation·repack·prefill 및 추가 불확실성 여유가 포함되지만
그 항목들이 증명된 최대치라는 근거는 없다. 기존14B 실측을32B 실측으로 대체하지 않는다.

Launcher는 허용 GPU3만 반복 조회하며 free floor 또는 증가 중단선을 넘으면 자신의 새 process group을 중단한다.
0.5초 polling은 순간 overshoot를 완전히 차단하지 못하고, 다른 workload의 해제가 aggregate 증가를 가릴 수 있다.
따라서 이를 per-process upper bound나 hard GPU isolation으로 표현하지 않는다.
실제 기동 직전 fresh preflight를 다시 수행해야 하며 추정 실패를 다른 GPU·자동 cap 증액으로 해결하지 않는다.

## Disk·다른 서버·남은 검증

Root 제공 usable disk48,954,236,928bytes에서 manifest 전체를 빼면29,612,712,939bytes,
약27.579GiB다. 20GiB reserve 위의 여유는 약7.579GiB다. 이 계산은 단일 저장본 가정이며
다른 형식·중복 모델 copy를 추가하는 예산이 아니다. 기존4B 정리나 free disk를 독립 실행한 검토는 아니다.

같은25,600MiB 추정에20% free margin을 적용하면 RTX5090의 최소 fresh free는32,000MiB,
그 지점의 margin은6,400MiB다. 기존30,720MiB는 이전24GiB 계획에만 해당한다.
현재 A100 cu118 launcher는 RTX profile을 실행하지 않으며 RTX runtime/driver/kernel/실제 메모리는 미검증이다.
A100의0.60을 RTX에 그대로 복사하지 않는다는 최종 계획의 구분은 적절하다.

다운로드 후 각 shard SHA/size와 header/shape, 실제 tokenizer/template와 grammar/context를 확인하고,
fresh GPU3 budget 아래 startup profile·loopback·기본 추론을 관측해야 한다.
기동과 메모리 조건을 통과해도 single generation2/promptv2의 exposed120 품질 gate는 별도로 남는다.
Staged 실패가 dense32B의 품질 우위를 입증하지 않는다.

검토한 최종 plan SHA는 `f01fa2d7baeb5be24ec69566187ee19ed4577723322d20a70440edd015714ebc`,
memory JSON은 `bc0bb646c2a5572d4ccdd01f89f199cce3fbafed126f1746d6630276f4c93dce`,
manifest는 `fbb3d1c98f3ceeeceb2fd5306dde9439d1be12516dd5054c0b2f5a299a260e03`다.
공용 source/계획 파일은 수정하지 않았고 이 독립 검토 문서만 작성했다.
