# Native runtime 사전 검증 기록

이 묶음은 Phase5.x의 Qwen3.8-27B GGUF/llama.cpp 후보 준비 증거다.
**새 모델의 품질 gate 통과 또는 채택 기록이 아니다.** 각 보고서의 시각과 scope를 구분한다.
초기 source/build 보고서의 `no_weights`/`native_binary_executed=false` 등은 해당 단계의 상태다.
이후의 다운로드나 CPU helper 실행이 과거 보고서의 범위를 소급해서 바꾸지 않는다.

- Source bootstrap: commit/tree/blob/mode와 CMake 배포물 검증.
- CUDA build/relink/static verification: SM80/CUDA11.8 컴파일, `$ORIGIN`, library/driver provider 경로 검증. 실제 CUDA kernel 실행 증거는 아님.
- CPU build-v2/public contract: 별도 GPU backend OFF executable의 공개30개 grammar 사례, final content와 sampling 처리. 초기 compile 실패는 재현 정의의 history에 보존함.
- GGUF/download: 전체 file SHA와851 tensor/header/metadata binding. 모델의 수치 품질 또는 실제 GPU placement 증거는 아님.
- GPU3 VMM reports: 허용 UUID가 노출된 단일 장치의 driver metadata 조회만 수행. Context/할당/native model 실행 없음.
- Guard/wire/Backend regression: CPU/fake lifecycle 및 실제 PostgreSQL/IfcOpenShell을 포함한382개 검사, 기존24개 wire 동등성.
- Cache cleanup: 종료된 MoE의 검증된 재다운로드 가능 가중치4개만 정리한 이력과 검사 한계·복원 명령.

실행 정의는 [runtime profile](../../../../runtime/native/a100-llama-f072/README.md)에,
전체 예상 VRAM과 실행 조건은 [자원 계획](../../../../docs/native_qwen38_resource_plan.md)에 있다.
검증 중 발견한 실패는 기록하고 원인 수정 후 별도 증거를 추가한다. 실패 결과를 덮어써서
PASS로 바꾸거나 문맥·schema·품질 조건을 완화하지 않는다.

실제 v2 본문·gold·model output·reasoning을 이 사전 검증 묶음에 추가하지 않는다.
원래 v2 입력 노출 이력과 **AUTO-GENERATED / NOT HUMAN VERIFIED** 제한을 유지한다.

D033은 원문을 유지하는 `qwen38-gguf-raw-unicode-v1` 후보를 별도로 검증한다.
공식 HF reference의19/20 FAIL은 보존하며, 동일20입력에서 NFC만 끈 파생 reference와의
20/20 PASS 및 native 원문 roundtrip20/20을 별도로 기록한다. Source/quote/parser 보정은 없다.
V3/V4의 숫자 진단은 CPU helper에만 추가했으며 pinned llama.cpp 원본과 weight는 불변이다.

실제 raw-native context200개 PASS: 노출120은2133~2409 tokens, +768 최대3177;
v2 길이80은2154~2365 tokens, +768 최대3133으로4096 이내다. Model inference0이다.
이후 첫 GPU startup은 별도 실패 archive에 보존하며 이 CPU 증거를 품질 PASS로 바꾸지 않는다.
