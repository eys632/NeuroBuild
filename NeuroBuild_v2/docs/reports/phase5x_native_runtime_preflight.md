# Phase5.x native runtime 검증 중간 보고

최신 checkpoint: 단회120개 진단은117/120·rawFP0·unsafe0으로1차 gate PASS이고125개 독립 재생을 완료했다.
모델 서버는 사용자 지시로 종료했고 GPU3 VRAM 반환을 확인했다. 자동전체3회 평가를 취소했으며
현재 판단은 [단회 진단 보고서](phase5x_native_qwen38_diagnostic_report.md)와 D036을 따른다. 아래 사전 검증 기록은 당시 상태를 보존한다.


**Qwen3.8-27B Q4_K_M / pinned llama.cpp의 GPU3 startup·공개 JSON·최대 문맥 자원 검증을 통과했다.**
품질 gate는 아직 미통과이며 최종 모델 채택이나 Phase6 시작이 아니다. 실제 노출120 진단 조건을
동결했고 commit·push 뒤에만 평가한다. 시스템 driver/CUDA/Python 환경은 변경하지 않았다.

CUDA11.8/SM80 build, source3,607개·binary/8개 library/$ORIGIN 검증, GGUF18.97GB 전체SHA와
851tensor/header/template 검증을 마쳤다. CPU-only native helper는 공개 grammar10정상/20거절,
final content·prefix·sampling을 통과했다. 공식 HF NFC tokenizer와19/20 ID 비교는FAIL이다.
원문을 보존하는 별도 raw-Unicode 후보로 기록하고 원래 실패를 유지한다. Native raw reference와
roundtrip20/20, 실제 context200개는PASS다. Input+768 최대는 노출120에서3177/v2길이80에서3133.

Native HTTP protocol과 sampling을 명시하고 공통 guard·실제 child UUID/count·core0·parent death·
자체process cleanup을 적용했다. 기존24개 vLLM wire와 canonical parser는 불변이다. Scorer11개
핵심함수 AST도 기준과 동일하다. 전체 PostgreSQL/IfcOpenShell/headless 회귀386PASS/skip0/19.652초.

첫batch1은SIGABRT로 실패했다. 같은 설정의 제한된 stderr 진단에서llama-context.cpp:1734를
확인해 내부2token 검사와의 충돌을 수정했다. Batch2/ubatch1 startup/public/resource가 통과했지만
3328token prefill은82.071초였다. 별도source/VRAM검토 후64/64 후보를 검증했다. 같은3328token
입력/768sampled 출력/4095cached boundary는PASS, prefill4.075초/decode21.594초/총25.678초다.
공개JSON1건은5.178초로PASS였다. Raw body·reasoning은 보존하지 않는다.

Epoch4는freshfree36,373MiB/util0에서wholeestimate28,672MiB+margin7,275MiB를 통과했다.
자원probe까지의lifetimeaggregatepeak18,346MiB/최소free18,028MiB였다. Per-processpeak·엄밀상한·
hardisolation은아니다. 다른사용자나GPU0/1/2는변경하지않았고GPU3에만실행했다.
첫실패2개와종료한2/1epoch3의source/config/proof/cleanup을별도보존한다.

노출진단은같은prompt/schema와strictquote/parser,120개×1+5warmup,768cap/timeout120이다.
Schema120/120,semantic≥114/120,rawFP0/58,unsafe0/120을유지한다. 원래22개완료품질실험과분모는
그대로이며public/resourceprobe는새품질run으로합산하지않는다. Gold는AUTO-GENERATED /
NOT HUMAN VERIFIED. V2는모델출력미관측이나기존root부분입력노출기록을유지한다.
RTX5090은PREDICTED_UNVERIFIED다. 공통제품scope·별도승인·immutable revision은불변이다.
