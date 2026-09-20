# Generation2 greedy holdout 시작 전 runtime 검토

검토 시각: **2026-09-20 09:23 KST / 00:23 UTC**. 이 시점의 guard 기록과 실제 자체
PID listener 관측에서 holdout 실행을 막는 runtime/resource blocker는 발견하지 못했다.
현재 epoch 안에서80×3과 warmup5를 연속 수행하는 것은 관측 latency에 비추어 가능성이
충분하다. **완료 시간·메모리·품질 보장은 아니다.**

검토 대상은 [첫 holdout 동결 프로토콜](../../evaluations/hardening_v1_generation2_branches_moe_greedy_holdout_freeze.json),
[보존 launch](../../evaluations/results/phase5x/moe-instruct-v1-launch/launch_config.json),
현재 guard report, 기존 CPU proof와 자체 PID listener다. Holdout gold·model output은
읽지 않았고 추론, GPU 조회, 서버 변경·종료, weight 읽기를 수행하지 않았다.

## 같은 runtime epoch와 자원 기록

09:23:04 KST에 읽은 `var/reports/qwen3-30b-instruct-v1-server.json`의 수정 시각은
09:23:03.962 KST이며 상태는 `RUNNING`이다.

| 항목 | 관측 / 연결한 근거 |
|---|---|
| child PID / 시작 기록 | `3409891` / `2026-09-19T23:11:02.235538Z` |
| model alias / 물리 GPU | `neurobuild-moe` / GPU3, mask3 |
| mode | FP16 AWQ Marlin, non-thinking, reasoning parser null |
| context / TP / 동시 sequence | 4096 / 1 / 1 |
| watchdog 관측 횟수 | 7793 |
| epoch 전체 관측 최소 free | 18,642MiB |
| free 하한 | 7,275MiB; 관측 최소와의 차이11,367MiB |
| baseline 대비 aggregate 증가 최대 | 17,732MiB |
| aggregate 증가 중단 한도 | 25,600MiB |
| 경과 / 실행 한도 | 4317.363초 / 7200초 |
| 관측 시점 남은 시간 | 2882.637초, 약48분03초 |

시작 전5회 측정 free36,373MiB에 전체 peak 추정24,576MiB와 margin7,275MiB가 들어갔다.
이는 launch 시점의 판단이며 현재 전용 VRAM 예약이나 process별 peak가 아니다.
위18,642MiB는 epoch의 관측 최솟값이고 별도 새 GPU 조회값이 아니다. 기존 watcher의
free/증가량 검사와 query 실패 시 자체 child 중단 정책을 그대로 유지한다.

Launcher 현재 SHA256은 launch/freeze의
`6e0c84166861e9556a6be53a0e4f69f43381388d1e6d7f3feadae79f879388ab`와 일치한다.
FileStore 경로도 같은 epoch의 `model-3hu6i4db/store`, world1/GLOO lo/NCCL =lo다.
실행 중 `cleaned=false`는 정상이며 종료 후 정리 결과는 별도 확인해야 한다.

## 자체 PID의 fresh listener 확인

기존 `verify_model_listeners.py`로 guard가 지정한 PID3409891 하나만 검사했다.
**09:23:19.794 KST PASS**: IPv4 TCP listener5개가 모두127.0.0.1이며8003과
33969/34845/38333/41659다. Socket inode8개 중 다른3개는 non-TCP로 분류됐다.
UID1003, process start ticks474305056이 최초 launch proof와 같아 동일 epoch임을 확인했다.

[보존한 immutable snapshot](../../evaluations/results/phase5x/generation2-greedy-preholdout-listeners.json)의
SHA256은 `f49f07cbd7da89b9f332ce3332373aa05913a635434297a32c7d0fce1bbe2689`다.
검사 시각은 JSON의 `checked_at_utc`가 기준이다.
이는 한 PID·한 시점 TCP 관측이며 향후 listener, descendant, UDP/firewall을 보장하지 않는다.
다른 PID나 다른 사용자의 socket 주소를 조사하지 않았다.

## Context와 동결 설정

현재 source/prompt/schema/manifest 및 두 CPU proof의 지정11개 SHA, launch 설정 SHA를
holdout freeze와 대조해 일치를 확인했다. 실제 local 모델의 작은 `chat_template.jinja`도
runtime metadata의 `40c21f34cf67d8c760ef72f8ad3ae5afad514299d4b06e91dd9a8d705af7b541`과 같다.
대형 tokenizer/weight와 dataset은 이 검토에서 다시 읽지 않았다.

[보존 CPU 길이 증거](../../evaluations/results/phase5x/generation2-v2-cpu-prompt.json)는 같은
모델 revision·template·prompt에서 holdout **입력 길이만** 확인했다. 최대 입력2915에
출력 cap768을 더한3683은 context4096보다413 적다. Greedy 전환은 template/context/
출력 cap을 바꾸지 않는다. 이것은 출력이768 안에 완료된다는 보장이 아니며 truncation은
실패로 남긴다. [별도 CPU grammar 증거](../../evaluations/results/phase5x/generation2-v2-cpu-grammar.json)의
13개 수락/18개 거절/필수 backend 검사5개는 shape 경계 검증이며 의미 품질과 구분한다.

## 남은 시간과 중단 처리

Root가 제공한 development latency를 첫5 warmup과 정식240회, 총245요청에 적용하면:

| 계산 | 시간 | 의미 |
|---|---:|---|
| 245 × mean4.3943초 | 약1076.60초, 17분57초 | development 평균에 근거한 추정 |
| 245 × p955.9109초 | 약1448.17초, 24분08초 | 설명용 추정; 전체 실행의95% 상한이 아님 |
| 245 × timeout60초 | 14,700초, 4시간05분 | 호출별 timeout 수치의 단순 합; 현재 epoch에는 들어가지 않음 |

평균 추정 대비 약30분, p95 곱셈 대비 약24분의 여유가 있지만 setup/storage/scheduling,
holdout 응답 길이와 지연 분포는 다를 수 있다. 예상 guard 종료는 **10:11 KST경**이며
정확한 중단 기준은 child 생성 뒤 monotonic 경과7200초다. `started_at_utc`는 preflight
이전 기록이라 그 값에7200초만 더한 시각과 수초 차이가 있다. 첫 warmup 직전 남은 시간을
다시 읽고, guard 한도를 우회하거나 실행 중 늘리지 않는다.

Watchdog/시간 한도/서버 오류로 중단되면 **INCOMPLETE, gate 미통과**다. 계획240,
실제 완료/미완료와 원인을 보고하며, partial 성공을 전체 통과로 합성하지 않는다.
Harness가 종료 전에 durable partial result를 기록한다고 가정하지 않는다.
Timeout/truncation/schema/parser 실패가 반환된 경우에도 trial 분모에 남긴다.

Formal development 통과의 독립 재계산은 별도 담당 검토다. 본 검토는 그것을 대체하지
않는다. 첫 holdout warmup부터 노출이며, 그 뒤 후보를 수정하면 같은80개는 더 이상
새 unseen holdout이 아니라는 [기존 절차](phase5x_holdout_protocol_review.md)를 유지한다.
