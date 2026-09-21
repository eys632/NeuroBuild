# Native guard 독립 검토

2026-09-20. **검토에서 찾은 증거 파일 덮어쓰기 문제를 수정한 뒤 focused CPU 재검증 PASS. 현재 범위의 추가 material blocker는 발견하지 않았다.** 실제 native executable/GPU/model/weight 호출은 하지 않았으며 v2 입력·골드도 읽지 않았다. 이것은 runtime launch/VRAM/semantic 품질 PASS가 아니다.

## 발견 및 수정 확인

이전 구현은 `report_file`이 `model_path`와 겹치는 것만 차단했다. Source/build/header 증거 파일이 정상적으로 `var/reports` 안에 있으면, 같은 경로를 runtime report로 지정했을 때 검증 직후 원본 증거를 STARTING/STOPPED report로 바꿀 수 있었다.

독립 재현은 모두 직접 만든 temporary directory에서 실행했다. 실제 query/Popen/killpg는 전부 fake였다. Source/build/header 3경로 모두 원본 hash 변경을 확인했으며 기존 실제 증거 파일은 변경하지 않았다. 수정 전 증거: `var/research/native_guard_before_fix_probe.json`.

담당 agent가 `_NativeRuntime.validate`에 output/input 충돌 검사를 추가했다. Log/report 양쪽의 canonical path를 binary/model/proof3/각 dependency/SONAME alias와 resolved target에 대조한다. `main`은 실제 CLI launch-config 경로도 run_guard 진입 전에 보호한다. 실패는 output open/write 및 GPU preflight/child launch 이전이다.

수정 후 동일 3재현 모두 `INVALID_PATH`, query0/launch0/signal0, 증거 bytes 불변이다. 추가 3개 회귀 테스트도 직접 실행해 통과했다: proof3×report/log, binary+libraries+alias, CLI launch-config 자체. 기록: `var/research/native_guard_after_fix_probe.json`.

## 핵심 경계

| 경계 | 확인 결과 및 실질적 한계 |
|---|---|
| 허용 GPU | Native config는 A100만 허용한다. Child env는 `CUDA_VISIBLE_DEVICES=3`, `CUDA_DEVICE_ORDER=PCI_BUS_ID` 고정. Bootstrap은 `/usr/bin/nvidia-smi -i 3` UUID만 읽고 CUDA driver의 visible count1 및 logical0 UUID와 비교한다. GPU0/1/2 query나 process 목록을 사용하지 않는다. |
| Allocation 전 baseline | Binary/library/model/proof 검증은 CPU 파일 읽기이며 driver를 로드하지 않는다. 공통 lock 획득 후 새 5-sample preflight가 허용해야 Popen에 도달한다. Bootstrap의 cuInit/device metadata 확인은 그 이후며 사용자 CUDA context 생성 API를 호출하지 않는다. |
| Same PID 및 parent death | Python bootstrap이 expected parent를 확인하고 SIGKILL PDEATHSIG 설정 후 parent를 다시 확인한다. `os.execve`로 동일 PID를 유지한다. Setuid/setgid binary는 거절하며 core RLIMIT0이 exec 전에 설정된다. Pipe의 PID/index/성공 event를 parent가 exact match한다. |
| Own cleanup | `start_new_session=True`로 만든 child PID의 group만 TERM/KILL한다. `waitid(...WNOWAIT)`로 leader를 reap하지 않고 유지하여 group ID 재사용 위험을 줄인 뒤 wait한다. 이미 reaped PID에는 signal하지 않는다. Parent가 죽었을 때 descendants 전체를 추적하는 일반 supervisor라는 주장은 하지 않는다. 현재 native subprocess build는 OFF다. |
| Budget | Fresh free 및 최소6GiB/20% margin, utilization/swing gate, baseline-relative rise, 0.5초 watchdog, duration을 공통 경로에서 유지한다. Native에는 Torch/전체 allocation hard cap이 없다. Aggregate 감소가 per-process peak를 숨길 수 있는 한계를 report에 명시한다. 따라서 보수적인 전체 peak 계획이 별도 필요하다. |
| Native 선택 | `--device CUDA0 --main-gpu 0 --split-mode none --gpu-layers all --fit off`; source `common/arg.cpp:1116`은 없는 device/CPU device 이름을 거절한다. 용량 부족 시 layer 재배치·타 GPU 전환 코드가 없다. 고정 CPU embedding/미지원 op가 존재할 수 있으므로 모든 tensor의 GPU residency는 false/unverified로 남긴다. |
| 환경 | Native child는 작은 allowlist로 시작하므로 LD_PRELOAD/LD_LIBRARY_PATH, Python/proxy, GGML/LLAMA override는 상속하지 않는다. Offline·loopback·cache경로·GPU mask를 고정한다. `.conda-vllm` Python bootstrap을 쓰며 Backend에 GPU dependency를 섞지 않는다. |
| 파일/재현 | Exact source/build/header hashes, source pin/inventory, reviewed CUDA80-real/DL OFF/subprocess OFF/graphs OFF settings, binary SHA, project library hashes/size 및 별도 SONAME symlink inventory를 검사한다. 실제 GGUF SHA와 size를 재검증한다. Proof는 operator가 고정한 증거이며 live process의 원격 attestation이 아니다. |
| CoT/로그 | Native stdout/stderr는 DEVNULL, stdin도 DEVNULL; `--log-disable`, no-reasoning-preserve, deepseek splitter, no-skip-chat-parsing. Bootstrap pipe에는 bounded enum/PID/index만 들어간다. 일반 exception본문과 원시 model body는 report에 넣지 않는다. 현재 모델 inference가 없으므로 실제 런타임 출력 검증은 별도 gate다. |
| Ready 의미 | Guard RUNNING/identity verified는 HTTP/model readiness가 아니다. 초기 `ready=false`, `inference_validation=NOT_ESTABLISHED`, memory_fit=false를 유지한다. 실제 health/listener/contract 검증은 root 단계다. |

## 기존 vLLM 보존

Checkpoint `52ffb5a2847e15ef79678fce54625dfb7f59841e`의 `model_server.py`와 현재 AST를 비교했다. `LaunchConfig`, `launch_command`, `child_environment` 및 공유 모듈로 옮긴 `require`, `local_path`, `runtime_output_path`, `acquire_project_lock`, `write_report`, `peek_child_exit`, `stop_owned_child` 10개가 모두 동일하다.

공통 lifecycle의 순서는 기존 validate→project lock→env/report metadata→preflight→budget→unique rendezvous→Popen→watchdog→own cleanup을 유지한다. Runtime별 methods는 기존 vLLM FileStore/allocator/CLI/env 처리를 그대로 수행한다. Native observe/status pipe만 새 adapter에 추가되며 vLLM observe는 no-op다. 기존 public injection points와 wrapper를 유지한다. AST 동일은 모든 runtime 동등성 증명은 아니므로 기존 회귀 결과와 함께 해석한다.

수정 전 전체 회귀 로그를 읽기 확인했다: `var/phase5x-native-runtime-regression.log`, **376 tests / 19.473s / OK**, SHA256 `1d069d1136cd5fdc5a2abc6f09084ab07df696c04bc2356ede1269990a234ac5`. 이 전체 실행은 root가 수행했으며 덮어쓰기 수정 이후 전체 회귀를 의미하지 않는다. 수정 후 독립 focused3 및 재현3은 위에 별도로 기록했다. 최종 전체 suite는 root가 후속 수행한다.

## 검토한 최종 source hashes

- `scripts/model_guard.py`: `cc95f6cccf9ca5b749bea2fc8c82d2af9d56d55b94a6aee947379b3a2f4de528`
- `scripts/model_server.py`: `4d734424f2d6b766f8fb8ed303d1320425f0297c32a8bc7d9e848bca8b82352a`
- `scripts/llama_server.py`: `c87f52735d620adc839102b2a68ebb2844b5608a711f83c4f127fdbaf16af2b1`
- `scripts/native_model_bootstrap.py`: `22e56159a6496aabf52dc6b567c800c54822c9def9713eb8a4ff0fac4183c2bf`
- `tests/test_llama_server.py`: `e774a1a7c5e547deb1e40ab178eff75f71b2d54023481958bb328b08db6b11b9`

현재 파일 검사와 추후 path 재open/exec 사이에는 신뢰하는 사용자 소유 immutable checkout/artifact 가정이 남는다. 적대적 same-UID 동시 파일 교체를 막는 완전한 fd-exec attestation은 아니다. 실제 launch 직전 source·binary·proof freeze를 유지하고 변경 시 다시 검증해야 한다. RTX5090 native build/실행도 아직 미검증이다.
