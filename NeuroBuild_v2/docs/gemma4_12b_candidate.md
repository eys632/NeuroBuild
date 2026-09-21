# Gemma4-12B QAT 후보와 최소 사전검증

GLM 실패 checkpoint `95ebee297ab4e5a50d2a2c702b6e78be17b3fb0f` 이후,
공식 Gemma4-12B QAT가 기존 계약을 더 작은 자원으로 만족하는지 검토한다.
31B의 점수나 공개 benchmark를12B의 품질 통과 근거로 사용하지 않는다.
여러 후보의 schema 통과에도 의미·안전 오류가 남았으므로 형식·runtime 최적화만으로 해결된다고 가정하지 않는다.
12B도 명백히 실패하면 그 후보의 반복·V2를 하지 않고 다음 실험의 새 가설·비용을 먼저 재검토한다.

## 공식 고정 자료

공식 [GGUF](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/tree/29d097773436b69ff9feafd636ab4cf873786537),
[QAT 원본](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-unquantized/tree/b6ed86275a6a5735884e208bfed95b445a684ca2),
[IT 참조](https://huggingface.co/google/gemma-4-12B-it/tree/707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7)를 구분한다.
Cards/API는 Apache2를 선언한다. Repository에 별도 LICENSE가 있다고 꾸미거나,
공개되지 않은 정확한 GGUF conversion 원본 revision을 추정하지 않는다.
QAT 원본은 단일 safetensors이며 index/변환 로그/src_sha가 없다.
Commit 제목의 “280 sequence length”를 모델 context 한도라고 해석하지 않는다.

파일 `gemma-4-12b-it-qat-q4_0.gguf`는6,975,879,296B,
SHA `93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b`다.
[Manifest](../runtime/models/gemma4-12b-qat-q4-0.json) SHA는
`7c14b3edaa691341c8759300e81825a8b0c9bf4924dec240df35be648c7b3990`다.

Text 구조는48층/hidden3840/FFN15360, attention heads16,
SWA40층의 KV8×256 및 global8층의 KV1×512다. MoE/per-layer embedding/sharedKV는0이고
embedding/output을 공유한다. 고정 f072 converter에 Unified→GEMMA4 등록이 있으며 generic loader/graph를 사용한다.
48층의 size label UNKNOWN만으로 지원 불가나 실행 성공을 주장하지 않는다. 실제 header 검사는 별도다.

## 재사용과 새 검증의 경계

공식 tokenizer SHA `cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f`와
template SHA `ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4`는31B와 byte-identical이다.
Literal U+2581과 공백의 비가역성 한계를 보존하며 모든 Unicode 원문 왕복을 보증하지 않는다.
새 GGUF의 모든 tokenizer 관련 metadata 및 template/특수 토큰/옵션이 기존 실제 header와 같고,
같은 Gemma 요청·transport·prompt/schema 코드 경로임을 입증할 때만 완료 public/vocab/context 증거를 승계한다.
이 경우 **CARRIED_FORWARD_BY_EXACT_INPUT_EQUIVALENCE**로 표시하며 새로 실행한 PASS라고 쓰지 않는다.

새 model-specific 조건은 generation config의 **suppress_tokens=[258883,258882]**다.
고정 converter→vocab loader→native sampling의 -INF bias 경로가 있으나 실제 GGUF key와 유효 ID,
EOG 비충돌은 아직 확인해야 한다. 전체 sampling이31B와 같다는 주장은 하지 않는다.
공식 T1/P.95/K64와 project neutral penalties/seed42/4개 sampler 순서를 사용한다.
`gemma4_nonthinking_llama_cpp`를 공유하되 evaluator는 공식12B/Q4_0 조합만 새로 허용한다.

새 payload 전체 SHA/header/tensor coverage와48층 shape·dtype·softcap은 후보별로 감사한다.
QAT index가 없으므로 source index 독립 대조를 수행했다고 주장하지 않는다.
실제 GPU3 startup/inference/resource와 첫 품질 평가는 아직 수행하지 않았다.
완료한 공통 runtime 검사를 다시 구축하거나 재실행하지 않는다.

## 조건부 자원 계획과 실행 순서

Context4096/seq1/batch64/ubatch64/F16KV/flashOFF/graphsOFF 기준 예상 whole peak는 **18,432MiB**다.
Weights6912 + KV1536 + dequant4096 + graph2048 + driver1024 + pool1024 + loading256 + uncertainty1536으로 잡았다.
보수적으로 전체4096토큰에 K/V를 모두 배정한 KV는1344MiB, 최대 F32 vocabulary matrix는3840MiB다.
이는 측정이나 하드 상한이 아니다. 기동 직전 GPU3 free/util을 다시 측정해 margin과 함께 비교하고
own guard로만 여유를 감시한다. GPU0/1/2 fallback은 없다.

먼저 CPU 증거 연결과 실행/종료/평가 정의를 준비하고 GPU를 사용한다.
첫 품질 호출 전 clean commit/push와 현재 실행 신원을 동결한다.
준비를 마치지 않은 채 모델 서버를 오래 유지하지 않는다.
첫 진단은 기존 노출120×1+warmup5이며 schema120/semantic≥114/rawFP0/unsafe0 기준을 유지한다.
기존125개 진단·독립 재생과 완료 평가를 반복하지 않는다. 명백한 FAIL은 같은 후보 추가 반복·V2·미사용80개 접근0이다.
첫 gate PASS 이후에만 후속 최소 검증을 별도로 결정한다. Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED다.

현재 download·회귀·disk 증거는 [준비 보고서](reports/phase5x_gemma4_12b_preparation_report.md)에 있다.
Phase5.x 미완료·미채택·Phase6 미시작이며 RTX5090은 PREDICTED_UNVERIFIED다.
