# Phase5 runtime 및 평가 증거 최종 검토

검토일: 2026-09-20 KST. 판정: **검토 범위 PASS — 추가 중대 blocker 없음**.
이는 아래 runtime guard와 보존된 development 평가 증거의 판정이다. 전체 Phase5
문서 갱신·최종 회귀·commit/push나 후속 MVP gate 완료를 대신하지 않는다.

Runtime 담당 agent가 소스/증거를 다시 검토하고 평가 집계를 독립 재계산했다.
검토 중 실행 중인 모델 서버를 시작·종료하거나 GPU를 조회하지 않았다. 요청된
launcher 테스트의 fake child와 자체 CPU-only lifecycle/Gloo probe만 실행했다.

## 실행기와 자원 경계

`PYTHONPATH=src .conda/bin/python -B -m unittest tests.test_model_server -v`:
**20 tests PASS, skip0, 2.255s**.

- Profile/mask 불일치, 현재 RTX runtime 미검증, preflight 부족, 잘못된 측정값과
  GPU total 변경이 fail closed다. 예상 peak와 여유, allocator/vLLM fraction은
  측정 budget을 넘을 수 없다. 감시 중 free-floor 또는 aggregate 증가량 초과는
  자체 생성 group 종료로 이어진다.
- 프로젝트 owned regular file에 no-follow/nonblocking flock을 얻은 뒤 GPU를
  조회한다. 동시 own guard는 거절하며 기존 active report를 덮어쓰지 않는다.
- Parent-death SIGKILL은 torch import 전 설정된다. 종료 시 waitid(WNOWAIT)로
  리더 ID를 유지한 상태에서 자체 group TERM/KILL 후 회수하며, 확인 실패는
  STOP_FAILED다. 실제 CPU test가 parent 소멸과 TERM 무시 descendant를 검증했다.
- FileStore는 실행마다 새0700 directory와 미사용 경로를 사용한다. 단일 rank
  NCCL 초기화를 vLLM 전에 수행하고 DP/rank/loopback 환경을 명시한다. 자체 child
  회수 후 해당 store와 directory만 정리하며 실패/이전 run을 재사용하지 않는다.
- 별도 model Python에서 CUDA 장치를 숨긴 실제 Gloo FileStore+4 subgroup probe가
  자기 `/proc/self/fd`의 listener만 검사했다. 모두 loopback이었다. Backend에는
  Torch dependency를 추가하지 않았다.

검토한 실행기 SHA256은
`5d027f97527aecdbab23830edb9c2060f3b5f6d82ac3d543f98d701f6acd4dc2`이며,
14B v3 launch 정의의 launcher hash와 같다.

## 보존된 실제 평가와 재계산

각 archive의 `manifest.json`/`results.json`은 해당 원본 `var/runs/<run_id>/`
JSON과 동일했다. 모든 trial에서 집계 함수를 다시 실행한 결과가 보존된 metrics와
완전히 일치했다. 14B v3는 최종 semantic output 60개를 schema→현재 parser→gold
scorer로 다시 검증해 각 row의 판정과 일치함을 확인했다. Warmup5개는60회 분모에
포함하지 않았다.

| 실제 run | Schema | Parser | 자동 semantic rubric | Accepted READY critical FP |
|---|---:|---:|---:|---:|
| [14B AWQ v1](../../evaluations/results/phase5/qwen3-14b-awq-v1/results.json) | 60/60 | 51/60 | 45/60 | 0/33 |
| [14B AWQ v2](../../evaluations/results/phase5/qwen3-14b-awq-v2/results.json) | 60/60 | 60/60 | 57/60 | 3/33 |
| [8B BF16 v1](../../evaluations/results/phase5/qwen3-8b-v1/results.json) | 60/60 | 57/60 | 45/60 | 6/33 |
| [8B BF16 v3](../../evaluations/results/phase5/qwen3-8b-v3/results.json) | 60/60 | 54/60 | 54/60 | 0/33 |
| [14B AWQ v3](../../evaluations/results/phase5/qwen3-14b-awq-v3/results.json) | 60/60 | 60/60 | 60/60 | 0/33 |

8B/14B v3의 prompt/parser/scorer hash가 동일하다. 14B v3의 dataset, prompt,
schema, client, parser, scorer, runtime metadata hash는 동결 당시 파일과 일치했다.
동결 evaluator/client/parser는 Git `51a07d5`의 해당 파일 SHA256과도 일치해 이전
코드가 보존돼 있다. 이후 추가된 명시적 HTTP protocol adapter와 evaluator의
protocol/split 기록은 이 과거60회 run을 다시 실행한 것으로 취급하지 않는다.
그 변경의 회귀와 legacy 실제 smoke는 별도 검증 대상이다.

Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**, 공개 development seed20개다.
Prompt v1→v2→v3 개선이 이 자료를 이용했으므로60/60은 새로운 heldout 정확도나
실제 사용자 위험도 보장이 아니다.0/33의 저장된 Wilson 상한은 약10.43%이며,
동일 case 반복3회는 독립 사용자 표본도 아니다. 실패한 v1/v2 결과를 함께
보존했고 schema 성공만으로 semantic 성공을 대신하지 않았다.

## 네트워크·측정 해석·서버 간 한계

Root가 자체 모델 process socket에 한정해 수집한
[14B v3 network proof](../../evaluations/results/phase5/qwen3-14b-awq-v3/network_proof.json)는
FileStore 사용 시 TCP listener5개가 모두127.0.0.1이라고 기록한다. 본 검토에서
실행 중인 서버의 socket을 다시 조사한 것은 아니다. 이전 TCPStore wildcard
관측은 수정 전 문제로 보존하고 현재 FileStore 경로와 구분한다.

[14B v3 resource snapshot](../../evaluations/results/phase5/qwen3-14b-awq-v3/resource_report.json)의
baseline used3965MiB 대비 관측 증가11684MiB, 최소 free24690MiB는 전체 GPU
aggregate 관측이다. 계산된 여유7275MiB를 유지했고 증가량 한계19456MiB 아래다.
`per_process_measurement=false`, `memory_fit_guaranteed=false`가 명시돼 있다.
이 값은 개별 모델 peak나 sample 사이 순간 peak, hard isolation을 증명하지 않는다.
해당 snapshot은 RUNNING 상태이므로 자체 종료/VRAM 해제 완료의 증거도 아니다.

Startup 약20.362초는 health 관측까지의 근사 시간이다. Cold cache를 통제한
측정으로 취급하지 않는다. Evaluator의 cold/warm startup·TTFT·process peak는
null로 남아 있으며 output tokens/end-to-end second를 decode throughput으로
바꾸어 해석하지 않았다.

공통 Domain/Application/semantic contract에는 GPU별 business 분기와 GPU library
import가 없다. Backend에서 torch/vLLM/Transformers module 부재를 이전 읽기 전용
검사로 확인했다. A100 실측과 RTX5090 PREDICTED_UNVERIFIED를 분리하며, 현재
cu118 launcher는 RTX 실행을 차단한다. 현대 structured-output dialect의 fake HTTP
통과나 SM120 source 조사만으로 RTX 설치·추론·VRAM 검증 성공을 주장할 수 없다.

현재 integration 한계는 유지된다: prompt/schema는 checkout resource이며 standalone
wheel 배포는 검증하지 않았고, natural-language resolver/API/worker/browser 연결은
후속 Phase다. LLM READY 결과는 actual target 확인이나 proposal 적용 승인이 아니다.

## 추가 검토 — 명시적 HTTP protocol 및 manifest 변경

판정: **소스/계약 검토 PASS, 추가 blocker 없음**. `local_model.py`, 두 관련
테스트 파일, evaluator의 manifest/CLI 변경과 common/A100/RTX profile을 읽었다.
Root가 전체 회귀를 수행 중이므로 본 추가 검토에서 테스트를 중복 실행하지 않았다.

Protocol은 enum 또는 정확한 문자열로 정하며 unknown 값은 HTTP 전에 거절한다.
Legacy 요청에는 `guided_json`/`xgrammar:no-fallback`, modern 요청에는
`structured_outputs.json`만 들어간다. 두 경로는 동일 schema와 parser/Domain을
사용한다. 실패 후 dialect 추측·schema 제거·자동 재시도 경로는 없다. 추가 테스트는
두 payload의 상호 배제, 동일 Domain 결과, invalid protocol, HTTP400/잘못된200 뒤
단일 요청 유지와 기본 prompt v3를 검사한다. 현대 server의 실제 grammar backend는
별도 launch 검증 책임이며 fake HTTP로 입증했다고 주장하지 않는다.

Manifest는 `client.protocol.value`와 해당 backend 요구를 기록한다. `split`은
development_seed/development/heldout 중 명시한 값을 보존하고 모르는 이름을
거절한다. 이는 운영자가 제공한 split label이며 자료 비노출이나 사람 검수 여부를
자동 증명하지 않는다. Gold 검수 상태는 여전히 AUTO-GENERATED / NOT HUMAN VERIFIED다.
CLI의8003/prompt v3/768-token 기본값은 공통 설정과 맞고, A100의 legacy 실제검증
상태와 RTX의 modern PREDICTED_UNVERIFIED 상태가 구분돼 있다.

변경 후 root가 기록한 `var/phase5-protocol-smoke.json`을 읽고 집계를 다시 계산했다.
A01/E02/F02 **3/3 schema/parser/semantic PASS**, protocol은 legacy_guided_json이다.
본 검토가 모델에 새 요청을 보낸 것은 아니다. 이3개 actual smoke는 앞 절의 동결
evaluator/client로 수행한60회 평가와 별도 증거이며, modern runtime 또는 RTX5090
실측의 증거가 아니다. 실제 모델 원문/내부 추론을 새로 저장하지 않았다.
