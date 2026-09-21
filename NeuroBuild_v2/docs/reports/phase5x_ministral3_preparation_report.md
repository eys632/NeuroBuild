# Ministral3 준비와 새로운 CPU 계약

공식 Ministral3-14B Instruct Q4_K_M을 다른 계열 후보로 준비했다.
현재 채택 또는 품질 PASS는 없으며 Phase5.x 미완료·Phase6 미시작이다.
고정 모델 identity, sampling 선택과 조건부 자원 계획은 [후보 문서](../ministral3_candidate.md)에 기록했다.

완료한 Qwen3.6 실패 결과와 종료 증거를 보존한 뒤 비활성 weight 한 파일만 전체 SHA·소유권·단일 link·사용 여부를 확인해 회수했다.
20,419,565,568 bytes를 회수했고 다른 사용자 파일/프로세스에는 접근하거나 신호를 보내지 않았다.
Ministral 다운로드는 기존 프로젝트 환경과 20.5GiB disk floor를 사용했으며 2개 고정 파일의 bytes/SHA가 일치했다.
최저 free34,738,761,728 bytes, 새 설치0회다. 이 다운로드와 profile 회귀는 공개 HTML 보안 정리 전에 완료한 증거를 승계한다.
원본 download receipt의 `download-qwen36` phase label은 이전 이름이 남은 것이며 실제 command/model/manifest/path는 Ministral이다.
원본 receipt를 수정하지 않는다.

Production 변경은 native sampling profile과 정확 model ID/quant 허용 조합 추가다.
기존 9개 sampling branch, transport, prompt/schema/scorer는 유지했다.
실제 PostgreSQL/IfcOpenShell/headless/빈 CUDA 환경의 **430 tests PASS, skip0, 21.501초**를 한 번 수행했다.
독립 source 검토도 이 변경 범위를 확인했으며, 이후 동일 suite를 반복하지 않았다.
추가 보안 scanner 테스트는 [별도 보고서](provenance_cleanup_20260921.md)의 13개 최초 PASS와 fixture 수정 후 1개 PASS다.

[최소 준비 archive](../../evaluations/results/phase5x/ministral3-14b-preparation/README.md)는
license URL/date/revision/identifier, 필요한 Apache/config/template, 파생 자원·tensor 계획 및 완료 receipt를 보존한다.
전체 외부 HTML/JS/API response, 모델 weight, canonical Tekken 전체 파일은 반입하지 않는다.
현재 FP8/BF16 참고 revision을 정확 GGUF conversion 원본으로 주장하지 않는다.

## 실제 구조 검사에서 확인한 차이

단회 header+전체 payload SHA 검사에서 파일8,239,593,024 bytes/SHA824e0f33…cc613이 일치했다.
실제363 tensors, F32 81/Q4_K 241/Q6_K 41, payload8,231,178,240 bytes다.
최초 결과는 **STRUCTURAL_FAIL / TOKENIZER_SCORES_METADATA_MISMATCH**였으며 원본을 보존했다.
`tokenizer.ggml.scores`는 FLOAT32로 가정한 검사기와 달리 INT32이고 count131072다.
고정 `llama-vocab.cpp`는 INT32/FLOAT32를 모두 허용하고 INT32를 float로 변환한다.
따라서 사전 가정의 오류를 별도 검증 기록으로 해결하며 최초 결과를 덮어쓰지 않는다.

Actual embedded template는7,754 bytes/SHA `6cc0f8c0cfbafcfd8b146d60e947a1b2511ace4db907b0a73f6a474d04bdca9b`다.
현재 공식 참고 template11,913 bytes와 다르므로 대체하지 않고 실제 embedded bytes를 CPU 계약에 연결한다.
명시적인 nonempty system/single user/no tools 경로는 전체 원문을 보존하며 metadata 렌더에서 BOS를 포함하고 generation prefix는 비어 있다.
모델 인식 BOS 처리는 후속 실제 vocab 검사에서 별도로 검증한다.

저장된 canonical 배열 비교의 첫 completion도 token 문자열 hash 차이로 실패했으며 이 정의와 CLI 결과를 보존했다.
원인을 구분하기 위해 헤더 metadata8,393,191 bytes만 한 번 더 읽었다. Tensor payload 읽기는0 bytes였다.
모든 저장 배열 fingerprint가 원래 감사 결과와 일치했다. Ordinary130072개는 모두 같고,
special34/35만 현재 참고 자료의 unused 이름과 달리 실제 GGUF에서 `[THINK]`/`[/THINK]`였다.
BOS/EOS/INST/SYSTEM 등 필요한 다른 special10개의 문자열·ID도 같았다.
이 차이를 정확히 명시한 별도 구조 보완과 실제 wire 참조를 준비하며, 전체 canonical 동등성으로 바꾸지 않는다.
이미 통과한12개 ordinary 참조는 그대로 승계하고 해당 wire control1개의 기대값만 실제 metadata에 맞춰 별도 파생한다.

## CPU 작업 범위

새 public1 native validator는 기존 CPU objects194개를 재사용해 compile/link에 성공했다.
이는 native validator 실행이나 모델 품질 성공이 아니다. GPU dependency가 없고 기존 source/object/binary는 불변이다.
최저 free34,724,286,464 bytes, own child cleanup 완료이며 stderr0이다.

Canonical Tekken v13의 고정 공식 encode 알고리즘을 기존 tiktoken0.14.0으로 명시적으로 재현했다.
새 공개 문자열12개의 원래 UTF-8 bytes 복원은12/12 PASS, 같은 문자열 중2개의 wire special-token 조합은 별도로 구분했다.
설치된 구버전 mistral-common을 성공적으로 실행했다고 주장하지 않는다.
NFC 변환, 추가 regex unescape, 입력/출력 보정 및 기존 public corpus 반복은0회다.
이 참조 결과는 **PASS_REFERENCE_RAW_BYTES_ONLY**이며 native token-ID 일치나 모든 Unicode 입력의 동등성을 보장하지 않는다.

실제 tokenizer/public contract PASS 전에는 노출120 길이를 읽지 않는다.
후속 CPU 검사는 새 공개 사례 통과 뒤 동일 process에서 노출120 입력 길이만 측정하며, V2와 미사용80은 읽지 않는다.
4096 적합 여부를 먼저 측정하고 초과하면 별도 자원 판단 없이 context를 자동 증가시키지 않는다.
GPU3 runtime 및 첫 품질 평가는 아직 실행하지 않았다.

| 완료 증거 | SHA256 |
|---|---|
| 최초 구조 결과 | `587e2f3b56d70184496554ddd642d7487dbbe9ccd74e6dd0db02f57139928d58` |
| public CPU build | `756a80718e9dbc2ec655d836ac0ddde27b16cc366ad2b636bb1d30f4485672cf` |
| 새로운 tokenizer 참조 | `35287c1908001ff38a10f43508175f1d0448b7c862b2e6ffac73bb14fb042baa` |

앞선 모델들의 결과/latency/VRAM/실패와 종료 기록은 그대로 유지한다.
첫 품질 gate를 우회하거나 완료한 평가·재검산·runtime 검사를 재시작하지 않는다.
