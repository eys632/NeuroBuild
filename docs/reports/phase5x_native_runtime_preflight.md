# Phase5.x native runtime 사전 검증 중간 보고

Qwen3.8-27B Q4_K_M과 pinned llama.cpp의 별도 local runtime을 준비했다. 기존 cu118
vLLM 환경/공통 Application을 유지하며 시스템 driver/CUDA나 Python 환경을 변경하지 않았다.
**Phase5.x 품질 gate는 미통과다. 첫 GPU startup은 실패했고 모델은 채택하지 않았다.**

CUDA11.8/SM80 build와 source3,607개·binary/library/$ORIGIN 정적 검증, GGUF18.97GB
전체SHA/851tensor/header/template 검증을 마쳤다. CPU-only native helper로 공개 grammar
정상10/거절20, final content/prefix/sampling을 확인했다. 공식 HF NFC tokenizer와의 비교는
19/20 FAIL이다. 원문 보존 raw-Unicode 후보를 D033으로 구분하고 원래 실패를 유지한다.
Native raw reference20/20/byte roundtrip20/20 및 실제 context200개를 검증했다.
최대 input+768은 노출120에서3177/v2길이80에서3133으로4096 이내다. 길이검사는 추론이 아니다.

명시 native HTTP protocol과 sampling profile, 공통 lifecycle guard, source/build/weight/header
binding, 실제 child UUID/count, core0/parent-death/자체 process cleanup을 구현했다.
기존24개 vLLM wire와 canonical parser는 불변이다. Native evaluator metadata는 실제 native
증거를 구분하며 채점 함수는 유지했다. 다운로드 atomic publication의 경쟁 덮어쓰기도 방지했다.
실제 PostgreSQL/IfcOpenShell/headless 전체 회귀382PASS/skip0/20.178초다.
독립 guard·transport·CPU·VRAM·raw variant/context 검토를 수행했다.

GPU3 fresh5회 free36373MiB/util0과 전체예상peak28672+margin7275 조건으로 첫 실행을 허용했다.
Child3527525는UUID확인후7.781초에SIGABRT(-6)로 종료됐다. Aggregatepeak18290/minfree18084,
자체group정리/reaped 후free36373복귀. HTTP평가요청0이며 시작 내부warmup 실행여부는 미확인이다.
기본stdout/stderr는폐기했고 원인은아직미상이다. 이 관측만으로OOM을단정하지 않는다.
다음은같은설정/guard하에서raw본문을저장하지않는제한된stderr진단이다. 품질평가를우회하지않는다.

MoE의 검증된 inactive weight4개만정리해16.81GB를회수하고 manifest/복원/평가자료를보존했다.
새GGUF다운로드후free약24.65GiB로20GiB+512MiB reserve를유지했다. 환경/모델/binary/cache는Git에서제외한다.
정의와CPU·실패증거는 runtime/native 및 evaluations/results/phase5x에보존한다.

공통 제품 scope/별도승인/immutable revision은불변이다. RTX5090은 PREDICTED_UNVERIFIED이며
A100 binary/측정값을승계하지않는다. Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED,
기존120은exposed, v2는모델출력미관측이나이전root입력부분노출기록을유지한다.
