# EXAONE4.5 GPU3 사전 실행 결과

2026-09-20, 내부 비상업 연구용 `exaone45-gguf-continue-free-raw-unicode-korean-v1`의
첫 native 실행이다. **기동·공개입력·최대문맥 자원 검사 PASS이며 품질 gate는 아직 평가하지 않았다.**
공통 runtime의 완료 검사를 다시 수행하지 않고 이 새 모델에서 미실행한 세 항목만 확인했다.

공식 GGUF/고정 native f072 및 한국어 sampling 조건은 [진단 계획](../exaone45_33b_diagnostic_plan.md)과 같다.
공식 tokenizer18/20 FAIL과 별도 raw reference20/20 PASS, 전체 system 정책 보존을 연결한
[CPU 결과](phase5x_exaone45_cpu_preflight_report.md)를 실행 전 필수 조건으로 사용했다.
Application 입력·출력 정규화, 응답 repair, fallback은 없다.

## 현재 epoch와 GPU 예산

기동 직전 GPU3만5회 관찰해 모두 free36,373MiB/used3,965MiB/util0%였다.
안전 margin7,275MiB를 뺀29,098MiB 안에 예상 whole peak28,672MiB가 들어갔다.
이는 weight/KV/workspace/driver/loading 여유를 포함한 공학적 추정이며 엄격한 할당 상한은 아니다.
다른 프로세스의 존재만으로 중단하지 않되, aggregate 감시기가 자체 서버의 여유 감소를 감시한다.

Own guard3622309, child3622453/startticks478405342,
guard 시작10:33:32.120893 UTC다. PhysicalGPU3/logicalCUDA0/TP1,
loopback8003, ctx4096/seq1/batch64/ubatch64/F16KV/flashOFF/graphsOFF를 고정했다.
Config SHA `1e872da88b6d00750447dd7c39213d7a4ce19b161fa64cb4c51cab1f7b8b7761`,
guard 최대7200초다. 타인 프로세스·GPU0/1/2에는 작업하지 않았다.

## 실제 관측

| 항목 | 결과 |
| --- | --- |
| Startup | own PID/시작시각/argv/listener/source/model/header/override 연결, health/models/props GET3 PASS |
| 공개 입력 | production client 1 POST, 정확한 READY 이동 해석 PASS, 4.491796460초 |
| 자원 경계 | uncached input3328 + sampled768, cached4095, limit 종료 PASS, 27.610334212초 |
| 관측 aggregate VRAM 증가 최대 | 19,946MiB |
| 관측 최소 free | 16,428MiB, 안전 floor7,275MiB 유지 |
| 품질 평가 | 아직0회, 첫120×1+warmup5의 사전동결·push 필요 |

Resource 응답 본문은 보존하지 않았고 품질 평가에도 사용하지 않는다. VRAM 수치는 epoch 전체의
aggregate 변화이며 이 POST만의 값이나 process별 실제 peak가 아니다. 종료 때 최종값과 반환 여부를 추가한다.
Startup guard의 `ready=false`는 공통 guard가 자체 HTTP readiness를 주장하지 않는 필드다.
실제 HTTP health/models/props 성공과 공개 생성 결과는 별도 증거로 보존했다.

증거는 `evaluations/results/phase5x/exaone45-native-startup-epoch1/`,
`exaone45-native-public-smoke-epoch1/report.json`, `exaone45-native-resource-epoch1/report.json`에 있다.
Startup SHA `45033eec4a82cec67635a102f2f50ce42126c70d12131e30e90c2c39636de5c1`,
public SHA `8c70cbcc12ba9bfeb7cc38b5842e23b62010be4b07e82bb790b9872bf3fa9484`,
resource SHA `4eb66aa2351d05edb65192d1fb4b44e8427b64711c0c37a669828ef46dcb59b0`다.

Production source는 직전408개 실제 PostgreSQL/IfcOpenShell 회귀 PASS 이후 바뀌지 않았다.
새 CPU 증거 소비·변조 거절·동결/replay 보조 도구의 필요한 검증과 독립 검토만 추가한다.
품질 gate 미달이면 동일 후보 전체 반복·V2·미사용 holdout은 실행하지 않는다.
비필수 batch/flash/graphs/throughput 튜닝은 future optimization이다.
RTX5090은 PREDICTED_UNVERIFIED이며 이28,672MiB 계획은32GiB의 동일 margin 예산에 맞지 않는다.
**Phase5.x 미완료, 모델 미채택, Phase6 미시작**을 유지한다.
