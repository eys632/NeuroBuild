# Gemma4-12B 실제 header와 CPU 증거 승계

공식12B QAT의 실제 GGUF header 감사와31B의 저장 tokenizer metadata 비교를 각각 한 번 완료했다.
새 모델의 runtime·품질 성공이나 채택을 의미하지 않는다. Phase5.x 미완료, Phase6 미시작이다.

## 실제 파일 구조

`google/gemma-4-12B-it-qat-q4_0-gguf@29d097773436b69ff9feafd636ab4cf873786537`의
6,975,879,296B 파일 SHA는93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b다.
같은 file descriptor와 변경 없는 stat 아래 전체 SHA, layout/alignment, config·고정 converter/loader의
기대 역할을 검증했다. 48층/hidden3840, SWA40층/global8층, softcap30,
tensor667개(F32 338/Q6_K embedding1/Q4_0 matrix328)가 사전 고정 조건을 만족했다.
Payload 수치 검산이나 미공개 source tensor index와의 대조는 수행하지 않았다.
공식 저장소에는 단일 safetensors만 있고 정확한 conversion revision/log도 공개되지 않았다.

Header proof97a9bd3cb854c446edd7b534011eaceac389f76f8f6c49b1dd0ec5e06be4eac0,
저장 비교 proofa6d70d937b44a9743735b7843b59d9ba85dca2f9db300cf13c61d108a8c5f481.
기존 tokenizer.*13키 전체 typed summary/value/count/wire hash와 architecture가 같다.
새 suppression258883/258882는 INT32 배열로 확인했고 EOG와 겹치지 않는다.
Native 모델의 negative-infinity bias가 추가되므로 HTTP recipe가 같아도 전체 sampling 동작은 다르다.

## 재사용 범위

기존31B의 public30, official tokenizer parity20, 노출120+과거V2의 길이80 관측은 과거 실행 결과로 보존한다.
새 후보로 이름만 바꾸거나 재실행한 PASS로 표시하지 않는다. 새 header 비교와 현재 Gemma 요청 경로의
source 동등성을 별도 승계 receipt로 연결했다. 최종 freeze는 현재 데이터 파일 SHA도 원래 길이 proof에 묶어야 한다.
과거V2는 이미 노출된 데이터이며 미사용 holdout과 다르다. 미사용80개에는 접근하지 않았다.
Literal U+2581의 원문 왕복 실패, 입력·출력 NFC 보정 없음, 모든 Unicode의 보편적 보증이 아님을 유지한다.

후보별 auditor의 새 합성 경계8개는 PASS/0.183초다. 실제 header·비교도 각각 한 번만 실행했다.
기존 native public/vocab/context corpus, 완료125개 진단·재생, 변경 없는418회귀는 반복하지 않았다.
실제 모델 기동, HTTP 추론, 품질 평가는 아직0회다.

승계 receipt `cb2370d7a012b40fe62dae039551d9f8d37f4961aaaccc7a9845dd8bfdee0a2f`의
상태는 `CARRIED_FORWARD_BY_EXACT_INPUT_EQUIVALENCE`다. 고정된 원본 proof12개,
현재 생산 source5개, native source10개를 읽고 hash 연결을 확인하는 producer를 한 번 실행했다.
새 saved-metadata 경계5개는0.062초에 PASS했다. 잘못된 header 연결·숨긴 tokenizer 변화·
전체 sampling 동등성 오표기·과거 분모 변경을 거절한다. 이5개는 기존 corpus 재실행이 아니다.
보관 integrity는f33fa11f659eb0238ae3af330aab8f847bb2f060e4e09411dfb90446bb649d56,
19개 entry/18개 원본 exact copy/302,164B다.

## 자원과 다음 실행

Metadata 기반 조건부 전체 peak18,432MiB와 운영 admission 예산28,672MiB를 구분한다.
기존 검증된 batch64/ubatch64 runtime 정책을 유지해10,240MiB의 추가 보수 여유를 둔다.
낮은 예산으로 정책을 완화하는 작업은 현재 Phase를 막지 않는 future optimization이다.
기동 직전 physicalGPU3만 fresh free/utilization을 측정하고 safety margin까지 들어갈 때 실행한다.
이는 메모리 하드 격리나 다른 프로세스 사용량의 보증이 아니다. Guard는 자신의 모델만 중단한다.

원본 구조·비교·정의·합성 경계·CLI는
[`gemma4-12b-cpu-preflight`](../../evaluations/results/phase5x/gemma4-12b-cpu-preflight/)에 보관한다.
현재 생산 코드의418회귀 PASS는 직전 준비 checkpoint00c5a2fb593fff30fe5239781200a9b135fa94ab에 보존돼 있다.
