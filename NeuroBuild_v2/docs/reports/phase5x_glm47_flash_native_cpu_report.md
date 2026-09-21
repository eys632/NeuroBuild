# GLM-4.7-Flash 실제 vocabulary와 문맥 길이

2026-09-20. Phase5.x 미완료, 모델 미채택, Phase6 미시작이다.
준비 checkpoint `cba4830762ae4d5bd310987604e0f31dfc4d8eb1`은 GitHub `v2`에 push하고 원격 일치를 확인했다.
본 검사는 새 GLM 후보의 CPU 계약 증거이며 품질 gate 통과를 뜻하지 않는다.
정의와 실제 결과는 [CPU 보관본](../../evaluations/results/phase5x/glm47-flash-native-cpu/README.md)에 있다.

## 실제 vocabulary

고정 GGUF `b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2`를
단일 FD 전체 SHA와 전후 stat로 연결했다. 기존 CPU 전용 v3 binary의 vocab-only 경로에서
공식 공개20개 token ID, native 원문 왕복, 공식 ID의 native 원문 복원이 모두20/20 일치했다.
공식 tokenizer normalizer는 null이며 template override·NFC 보정·reference 재인코딩은 없다.

Proof `f3e31a724dcec94f6d3b285a9dd793d6a8b6c91c3c8c475a63c25709c94d6cf7`,
wrapper `aafeaa2d9bf6ef7b5ceccfac1d4e4b0e1f70ef34cd17c2d34e8df4035e124d70`.
[실제 vocabulary proof](../../evaluations/results/phase5x/glm47-flash-native-cpu/vocabulary/public-vocab-proof.json)를 보존했다.
Vocabulary154880, BOS154822/EOS154820/EOT154827/PAD154820,
EOG154820/154827/154829, add-BOS/EOS=false다.
모델 vocabulary를 사용하는 grammar20허용/40거절과 EOG, embedded template 원문 일치를 확인했다.
공개 입력2827+출력768=3595/4096이며 resource probe의 공백은 ID220 한 토큰으로 복원된다.

## 이미 노출된 입력의 길이

새 context 전용 TU만 컴파일하고 기존194개 CPU object/archive66,339,126B는 변경 없이 재사용했다.
Build proof `737234c286864486c57721007b6858fae61bb7613eee02eb007ab5be0e5795bd`,
binary `3da5aa2debc3307277eab2794194541858e384c0fcfc0cfbe79e0f5b973f3017`.
공식20개 PASS의 정확한 hash와 현재 source/header/model/build를 먼저 확인한 뒤
허용된 기존120·80개 파일만 열었다. 이 경로는 공개20개를 재실행하지 않는다.

| 기존 split | 입력 수 | 최소 입력 | 최대 입력 | 최대 입력+출력768 |
|---|---:|---:|---:|---:|
| 노출 hardening120 | 120 | 2811 | 3257 | 4025 |
| 기존 V2, 현재 노출 상태 | 80 | 2833 | 3164 | 3932 |

두 split 모두4096 한도 안에 든다. 실제 Application client 요청을 native OpenAI parser로 처리해
공식 template·전체 system/user·generation prefix·원문 왕복·schema grammar·sampling 연결을 확인했다.
입력 본문/gold/token 배열은 보고서에 저장하지 않았고 채점하지 않았다.
Proof `66e2ab245e0d7c2a2760d2b98e0a191fb8b27248be6fae6d61cf922c814bb607`,
wrapper `cf271201279b5deea15b8394faecc05eb363971255f5ea9d1c66e917c2abb2d9`.
[실제 context proof](../../evaluations/results/phase5x/glm47-flash-native-cpu/context/vocab-context-proof.json)를 보존했다.
Preparation receipt의 None pin 상태는 과거 준비 기록이며, 실행 전 실제 vocab/build/binary hash3개만 채웠다.

## 범위와 다음 판단

모든 native 실행은 empty devices, GPU layer0, vocab_only/no_alloc/LOAD_MODE_NONE/MTP off다.
모델 context·backend initialization·tensor weight load·decode·HTTP·GPU·모델 품질 호출은0이다.
미사용 미래80개 초안은 읽지 않았다. 기존 평가125개·85개 및 독립 재검산은 반복하지 않았다.
앞서 발생한 두 public helper 기대값 FAIL은 기존 보관본에 그대로 남아 있다.

Production source는416개 regression PASS 이후 변경되지 않았다. 현재 private CPU helper 작업 때문에
전체 regression을 반복하지 않는다. 실제 CPU 증거를 소비하는 runtime 설정을 검토하고,
GPU3의 현재 free/utilization과 예상 whole peak28672MiB+margin을 비교한 뒤 실행 여부를 정한다.
전체 peak는 공학적 추정이며 하드 메모리 격리 보장은 아니다. 비필수 runtime 최적화는 future optimization이다.
