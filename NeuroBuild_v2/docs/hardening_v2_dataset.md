# 새로운 합성 holdout v2

상태: **작성·독립 gold review·reference 및 CPU context 검증 완료, dataset-only freeze 완료**.
후보 선택과 실제 추론 직전의 candidate freeze는 별도이며 모델 품질을 검증한 상태가 아니다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. v2 모델 응답은 아직 생성하지 않았다.
기존 v1 development40+첫 holdout80은 노출된 regression 자료로 그대로 보존한다.

이 자료는 [generator](../evaluations/generate_requirement_hardening_v2.py)에 원문80개를 각각 작성했다.
v1 입력을 복사해 명사나 숫자만 바꾸는 생성 방식은 사용하지 않았다. 항목형 기록, 문장 앞뒤의
이동량, 짧은 대화, 인용 기록, 단일 벡터와 순차 작업, 조건의 위치, 보존할 속성과 현재 변경을
서로 다른 문장 구성으로 다룬다. 모든 요청은 기존 단일 가구·동일 층·상대 project XY 범위와
기존 CLARIFICATION/UNSUPPORTED 구분을 유지한다. 새로운 제품 기능을 정답으로 추가하지 않았다.

| 구성 | Case | 정식3회 trial |
|---|---:|---:|
| READY | 40 | 120 |
| CLARIFICATION | 20 | 60 |
| UNSUPPORTED | 20 | 60 |
| 전체 | 80 | 240 |

A–J 각8개이며 각 category의 세부 개수와 case별 scenario/layout 표지는
[manifest](../evaluations/hardening_v2_manifest.json)에 있다. 표지80개는 작성 관리를 위한 식별자이며
독립적인 의미 family80개 또는 독립 표본80개라는 통계적 주장이 아니다. 새 development split은 없다.
입력 길이는46–490자이고 긴 문맥 category8개는468–490자다. 무관한 문장 반복으로 길이만 늘리지 않았다.

[JSONL](../evaluations/requirement_hardening_v2_holdout.jsonl)의 reference는
[별도 파일](../evaluations/requirement_hardening_v2_references.json)에 보관한다. 기존 schema/parser/scorer를
변경하지 않고 canonical reference80개와 Generation2 branch reference80개의 검증·Domain 동등성을 확인했다.
같은 generator 재실행도 byte 단위로 동일했다. 이는 표현 가능성 검증이며 gold 의미의 정확성 증명은 아니다.
Non-READY의 full-source reference target은 모든 gold slot을 포함하는 검증용 값이며 이상적 모델 답변은 아니다.

| 작성 시 hash | SHA-256 |
|---|---|
| Dataset | `7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40` |
| Reference | `a7ea36bf65b0d9b643de2a4e1ed52ca94b764bc241ec25c653e5e1f29fb76c19` |
| Manifest | `7a6291fe16f9bcf5c2fce824235ba14a1698b0527c9dbdaf5f78643182ddde5e` |

v2 내부와 기존 v1 120개 사이의 exact/공백 정규화 중복은0개이며 ID도 재사용하지 않았다.
Target·숫자를 마스킹한 문장 형태도 비교했고 가까운 두 문장은 freeze 전에 구조를 다시 작성했다.
변경 전 초안은 ignored authoring archive에 보존했으며 의미 정답이나 지원 범위는 바꾸지 않았다.
이 중복 검사는 의미적 독립성 증명이 아니다. 좁은 지원 범위, 축·단위 어휘, 실패 분류는 여전히 공유된다.
작성자는 v1 실패를 알고 있고 과거 prompt 작성에 참여했다. Root/현재 후보 prompt 작성자는 v2 본문·gold 대신
개수·hash·검증 요약만 받도록 절차를 분리한다. 별도 AI 검토자는 본문·gold를 읽으므로 완전한 blind나 사람 검수가 아니다.
파일은 plaintext이므로 기술적인 접근 통제라고 주장하지 않는다.

Dataset 자체를 먼저 동결하고, 최종 후보 선택 후 **첫 v2 warmup 이전**에 dataset/reference와
model·prompt·schema·parser·adapter·scorer·runtime hash를 고정한다. Warmup5개는 정식 분모에서 제외하지만
첫 warmup부터 holdout 노출이다. Schema240/240, semantic최소228/240, raw READY FP0/120,
unsafe accepted0/240 gate를 유지한다. READY 잘못된 이동과 FN의 분모는 각각120이다.
동일 seed의 반복3회를 독립 표본으로 보지 않는다. Timeout·parser 실패를 분모에서 빼거나 성공 trial을 합치지 않는다.

v2 출력으로 조정한 뒤에는 같은 자료가 regression/development가 된다. 새로운 미관측 일반화 주장은
별도로 작성·검토·동결한 미사용 자료가 필요하며 이번 v1/v2 결과는 모두 보존한다.

## 독립 검토와 CPU 검증 증거

독립 AI 검토자가 원문 80개와 gold의 지원 범위, 대상·제외 범위, 현재/과거, 조건, 부호·단위,
조회/거절 판정을 모두 확인했다. 대상 보존과 제외 범위가 두 가지로 읽힐 수 있던 초안 1건을
freeze 전에 작성자가 수정했으며, 다른 79개와 READY40/CLARIFICATION20/UNSUPPORTED20 비율은 유지했다.
수정 전 초안은 `pre-independent-review-adjustment/`에 보존했다. 최종본의 남은 material gold 문제는
발견하지 못했으며 이는 사람 검수나 future model 정답의 보장이 아니다.

Canonical schema/parser/scorer, Generation2 branch schema/parser/scorer, Domain 결과 동등성은 각각
80/80 PASS다. NFC+공백 정규화 중복은 내부와 v1 대비 모두0개다. Target·숫자를 가린 문자 scaffold의
v1 최근접 유사도 최댓값은0.7556이며0.8이상인 항목은0개다. 이 수치는 표면 중복을 살피는 보조값이고
의미적으로 독립적인 표본임을 입증하지 않는다. 기존 v1 두 dataset hash는 그대로 유지됐다.

| 실제 tokenizer / prompt | 최대 입력 token | 출력 예산 | 합계 / context4096 |
|---|---:|---:|---:|
| Qwen3-14B-AWQ / generation2 v2 | 2844 | 768 | 3612 |
| 30B-A3B Instruct AWQ / generation2 v2 | 2840 | 768 | 3608 |
| Qwen3-14B-AWQ / classification v1 | 1125 | 128 | 1253 |
| Qwen3-14B-AWQ / extraction v1 | 1192 | 768 | 1960 |

Transformers4.51.3, local_files_only=True, trust_remote_code=False, enable_thinking=False로 각80개
원문 전체를 계산했다. Extraction은 모든 원문마다 세 classified_decision을 각각 넣은240개 request의
최댓값이다. Gold에 맞는 decision만 넣어 길이를 줄이지 않았다. Client 작성자가 확인한 기본 JSON
공백 및 source_text→axis_convention→classified_decision 순서를 반영했으며, 최종 client 구현과
일치하는지 candidate freeze에서 다시 확인해야 한다. Metadata/tokenizer는 고정 model manifest의
크기와 SHA를 대조했다. GPU를 mask하고 Torch를 import하지 않았으며 network·weight 읽기·모델 호출은0회다.
Context 적합성은 grammar/native kernel 실행, 출력 완료 또는 품질의 보장이 아니다.

검증 파일은 [독립 gold 검토 증거](../evaluations/results/phase5x/holdout-v2-preflight/independent_gold_review.json)와
[CPU context 증거](../evaluations/results/phase5x/holdout-v2-preflight/independent_cpu_context_proof.json)에 bytes 그대로 보존했다. 작성 당시 manifest의 검증 hash를
덮어쓰지 않고 독립 검토 시점의 parser/adapter/scorer와 prompt/template hash를 별도 기록했다.
Root와 현재 후보 prompt 작성자에게는 원문·gold·case별 토큰 수 없이 이 요약과 hash만 전달했다.

| 검증 증거 | SHA-256 |
|---|---|
| Independent gold review | `3dd0e61cb033470c1929bb12eaf92919e92b0f3bb753be51b0a71d4997c7bbc8` |
| Independent CPU context proof | `cc2b9b33de01f38c1ac949ffa303da3c9402edc3b04ac1d514a5126900d0cfbc` |

측정한 classification prompt SHA는 `fadecb815452f159a2dad3c1e64a5a7176aa4a361f8049b43e90fd226737c67a`,
extraction prompt SHA는 `fa459815c35f6a4b4e519763b9cf5128bf802a40fcef94f1e08569326e0b4230`이다.
Prompt/source/template bytes가 바뀌면 해당 token 검증도 갱신해야 한다.

Dataset-only freeze는 [별도 기록](../evaluations/hardening_v2_dataset_freeze.json)에 있다.
작성 당시 manifest는 당시 lifecycle과 source hash를 보존하는 역사적 기록이며 수정하지 않았다.
최종 모델·prompt·client·scorer·runtime에 대한 candidate freeze나 추론 실행을 뜻하지 않는다.
[독립 검토 요약](reviews/phase5x_holdout_v2_gold_review.md)과
[사람 검수표](../evaluations/hardening_v2_human_review.csv)를 함께 제공한다. 사람 검수 필드는80행 모두 비어 있다.

Generator는 기존 파일과 다른 bytes의 overwrite를 거절한다. Source dependency가 바뀐 뒤 재생성하면
dataset/reference가 같아도 검증 metadata hash가 달라질 수 있다. 그런 경우 기존 manifest를 바꾸지 말고
별도 임시 출력 위치에서 재생성·대조하고 새 검증 시점의 증거를 별도 기록한다.
