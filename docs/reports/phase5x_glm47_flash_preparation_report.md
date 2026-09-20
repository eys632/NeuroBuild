# GLM-4.7-Flash 후보 준비

EXAONE의 의미 정확도106/120 gate 실패는 `daeccac`으로 원격 보존했다.
같은 후보의 반복과 V2는 수행하지 않는다. 다음 후보 GLM-4.7-Flash의 고정 자료와
실행 가능성을 검토한다. **GLM 품질 결과는 아직 없으며 Phase5.x 미완료·Phase6 미시작이다.**
현재는 **다운로드·실제 header·공개 CPU 계약·416 회귀 PASS**까지 완료했다.
실제 native vocabulary20 및 문맥 길이·GPU/runtime·품질 검증은 아직 남아 있다.

## 후보와 출처

- 원본: `zai-org/GLM-4.7-Flash@7dd20894a642a0aa287e9827cb1a1f7f91386b67`.
- GGUF: `ggml-org/GLM-4.7-Flash-GGUF@7559e96b7e324ab405897dc2b91492b0f376ad4a`.
- 파일: `GLM-4.7-Flash-Q4_K.gguf`, 18,244,193,920B,
  SHA256 `b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2`.

원저자와 양자화 배포자를 구분한다. 원본 card는 MIT를 선언하지만 두 고정 저장소에
별도 LICENSE 파일이 없고, GGUF card는 license와 정확한 변환 원본 revision을 명시하지 않는다.
이 빈칸을 추정으로 채우지 않는다. 파일명만으로 Q4_K_M이라고 판단하지 않고 실제 header를 확인한다.
[원본 card](https://huggingface.co/zai-org/GLM-4.7-Flash/blob/7dd20894a642a0aa287e9827cb1a1f7f91386b67/README.md),
[GGUF card](https://huggingface.co/ggml-org/GLM-4.7-Flash-GGUF/blob/7559e96b7e324ab405897dc2b91492b0f376ad4a/README.md).

고정 API2개와 작은 파일8개, 합계21,133,497B를 Git blob 또는 LFS size/SHA와 대조했다.
원본 tokenizer는 normalizer가 null이다. 이전 후보의 NFC-off reference를 승계하지 않는다.
공식 template3120B는 f072 source의 GLM template와 바이트가 같지만,
실제 GGUF embedded template와 native render·token ID·EOG·grammar 검사는 별도로 필요하다.
모델별 새 검사는 완료된 이전 후보의 startup/resource/125개 재생 반복과 구분한다.

## 실행 설정과 자원 조건

공식 일반 평가 설정의 temperature1.0/top_p0.95를 사용한다. 한국어 nonthinking에 특화된
공식 권고는 확인되지 않았다. top_k0/min_p0/presence0/frequency0/repeat1/repeat_last_n0,
seed42, samplers `temperature → top_k → top_p → min_p`, thinking false는 프로젝트 선택이다.
기존 prompt/schema/원문 인용/거절/채점 기준을 유지하고 명시 profile로만 선택한다.

MLA/MoE 전체 가중치를 포함한 예상 whole peak는28,672MiB다. 이전 GPU3 baseline
free36,373MiB에서 별도 safety7,275MiB를 제외한29,098MiB 이내이며426MiB를 남긴다.
이것은 정적 공학 추정이고 allocator cap이나 실측 PASS가 아니다.
Header 전에는 실제 compressed MLA 예상211.5MiB 대신 expanded48층 KV3,840MiB를 계상했다.
Weights/padding17,536, KV3,840, 최대 dequant1,536, graph2,048, driver/modules1,024,
추가 pool1,024, loading256, uncertainty1,408MiB다.

동일 f072/SM80/CUDA11.8 binary와 ctx4096/seq1/batch64/ubatch64/F16KV/flashOFF/graphsOFF,
MTPoff/TP1/GPU3만 계획한다. 실제 빌드 FORCE_MMQ는 OFF이며 지원 quant dtype의 자동 MMQ 경로를
검토했다. Untied vocab 양쪽 tensor, expert shape/dtype, MLA metadata, MTP, VMM 경로가 예상과
다르면 예산을 다시 검토한다. 기동 직전에는 GPU3 free/util을 새로 측정해야 한다.
현재 다른 사용자의 process는 변경하지 않는다. RTX5090 실행은 PREDICTED/UNVERIFIED다.

## 디스크와 보존

EXAONE 서버 STOPPED/exit0/reaped와 고정 평가·header·manifest를 확인했다.
자기 소유 regular/single-link 가중치 한 개의 전체 SHA와 열린 descriptor/mapping을 검사한 뒤
20,047,839,424B만 정리했다. Metadata·평가 결과·source·재다운로드 manifest는 보존했다.
Cleanup receipt SHA256은 `8258aa8628740c6f3427f00f49263690666ac040b098d6a14e7e4ae7103d2756`이다.
직후 free45,663,219,712B였으며 타인 파일/process 변경은0이다.
검사 전후 모두 같은 UID의27개 process에서 mapping/FD를 확인했다. 접근이 제한된
별도2개 session infrastructure process는 해당 검사를 수행하지 못했으며 원본 receipt에 구분했다.

GLM 다운로드는 고정 manifest의2파일 size/SHA 검증으로 완료했다. 기존 CPU supervisor/종료 절차를 재사용하고
2초 간격으로 disk floor22,011,707,392B(20.5GiB)를 감시한다. 이는 공간 예약이 아니다.
최종 다운로드 receipt SHA는 `2427b4c1be87ad5717613c55ef47d429cad85defabf9fad79378ca8d6f4daf62`다.
실제 header·새 CPU 계약과 필요한 regression 검증 전에는 GPU 기동하지 않는다.

## 다음 판단

실제 header와 CPU 계약·자원 검증을 통과할 때만 새 후보의 startup/public/resource를 최소 실행한다.
그 뒤 첫120×1+warmup5를 별도로 동결·commit·push하고 실행 여부를 결정한다.
첫 gate 실패 시 반복0/V2 미실행, 통과 또는 경계선일 때만 남은 불확실성을 해소하는 최소 후속 검증을 한다.
미사용80개 초안에는 접근하지 않는다. 비필수 runtime 최적화는 future optimization이다.

## 실제 header 진단과 새 회귀

첫 metadata-only 진단 SHA는 `e97d4d6412ea35295961e024476d6c43b4ac9a7fc593e4d57c031b7a9a8e961b`다.
결과는 **DIAGNOSTIC_NOT_PASS / CONFIG_METADATA_MISMATCH**로 보존했다.
기본 full-MTP 변환 가정은868 tensors였으나 실제는47개 main block/844 tensors이며 MTP가 없다.
GGUF file_type15는 Q4_K_M이고, 실제 dtype은 Q8_0 48개/F32 281개/Q4_K 470개/Q6_K 45개다.
Q8_0는 global output과47개 attention K_B에 사용됐다. 템플릿3120B는 공식 SHA와 일치한다.
이 진단은 payload 전체를 다시 읽지 않았다. 완전한 파일 SHA는 앞선 다운로드 receipt가 검증했다.
현재 native source가 지원하는 실제47층·split MLA·Q8 역할을 별도 감사하며,
이 형식이 현재 converter 기본값과 같거나 변환 command가 확인됐다고 주장하지 않는다.

명시 GLM profile과 `(ggml-org/GLM-4.7-Flash-GGUF, Q4_K_M)` 평가 기록 연결을 추가했다.
기존 채점·분모·parser·adapter·prompt·schema는 불변이다.
416 regression tests PASS/skip0/19.398초, 실제 PostgreSQL·IfcOpenShell과 empty CUDA/headless다.
Log SHA `c342132012c9d6192164b09ddf3c806b82faaaaec3cc8be99379f2cea2e0463d`,
[회귀 기록](../../evaluations/results/phase5x/glm47-flash-preparation/regression/regression.json).
독립 source 검토는 GLM 추가분을 제외한 원래 client/evaluator bytes와19개 평가 함수 AST 보존을 확인했다.

공식 tokenizer 공개20개의 원문 왕복20/20, added literal36개 왕복36/36을 기록했다.
이는 native token ID 비교가 아니다. 새로운 CPU validator 한 파일만 compile/link하고 기존194 objects를 재사용했다.
첫 public native 검사는 **FAIL**이며 receipt는 `7eba381e83c09f14d9dcfaf898e20dd02badc3cc02362ac5e8eab5d9eb9b5b43`다.
실패 위치는 stage70/line307로, 검사 코드가 production nonthinking prefix를 다른 값으로 바꾼 뒤
합성 thinking 출력을 허용해야 한다고 가정한 보조 항목이다. 그 앞의 template20/full system·user/sampling/JSON
검사를 지난 제어 흐름과 완전한 public PASS를 구분한다. 원본 코드·실패를 보존하고 기대값의 타당성을 검토한다.
Production 설정이나 품질 gate를 바꾸지 않으며, 아직 GLM GPU/runtime/품질 평가를 수행하지 않았다.

후속 v2도 configured prefix 뒤 complete reasoning을 거절해야 한다는 보조 기대에서 실패했다.
Receipt `534f6aba740056ea8f959a1834bf6ce66f299952bfbe26c35d19b9f71385ae01`과 소스를 보존했다.
고정 native source는 DEEPSEEK parser에서 optional reasoning을 허용하며, `enable_thinking=false`는
그 문법을 제거하는 조건이 아니다. 따라서 원래 prefix로 parse한 최종 JSON과 reasoning 분리를 검증했다.
별도 v3 실제 **PASS** SHA는 `d8f8fe1faf2ee73b06f6df35d16dba3a29cb78ad41af35a8a1be6cff888ac85c`다.
Template20/system·user exact, sampling, schema10허용/20거절, final JSON20, protocol거절4,
동일 prefix의 reasoning 분리1을 확인했다. 다른 runtime mode 실행이나 모델 사고 생성 관측은 아니다.
새 build SHA `befeeb0c258f9c570b6c148e78e426979811a1b628090bf0ad1bc25ceac2cbef`와
binary SHA `19e5641f0e6051348a96f06fe6986cb40c5228e83bb352a2c21ea9317fcad3cb`를 고정했다.

실제 header 전체 감사도 **PASS**이며 SHA는 `595a7efd19914b65e91f1d92aaee141a0457472039c7278264cc1b5d314659ef`다.
자료는 [header archive](../../evaluations/results/phase5x/glm47-flash-preparation/header/integrity.json)와
[공개 CPU archive](../../evaluations/results/phase5x/glm47-flash-preparation/public_cpu/README_ARCHIVE.md)에 보존한다.
독립 공개 계약 검토 `59c9fded41f02f991a3a8aee52217ebef7eb2d2eeb1f740ddf4cac92f144eba8`도 범위 한정 PASS다.
실제 native vocab·context·품질 PASS를 이 결과로 대신하지 않는다. Production 변경이 없어416 회귀를 반복하지 않았다.
