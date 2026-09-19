# Generation2 MoE 첫 진단 독립 검토

2026-09-20 KST. **FAIL: semantic29/40(72.5%), raw READY FP1건.**
Development40×1, **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 전체 품질 gate 통과가 아니다.
[결과](../../evaluations/results/phase5x/development-generation2-moe-diagnostic/results.json)와
[manifest](../../evaluations/results/phase5x/development-generation2-moe-diagnostic/manifest.json)는
run `20260919T233958Z-5e2143732d36479ab880ab2fc32dfbb3` 원본과 byte 단위로 일치했다.

CPU 읽기 전용 routine `var/review-tools/replay_generation2.py`로 **40 trials+5 warmups**의
원래 generation output/decision→adapter projection→기존 parser→scorer를 재생했다.
각 단계 flag·오류·SI·rubric과 전체 summarize가 exact match이고 source hash8개도 일치했다.
원본 source/code-owned UUID/context를 사용하고 latency와 안전한 오류 기록을 유지했다.
Artifact를 덮어쓰지 않았으며 warmup5개는 아래 분모에서 제외했다.
Routine SHA: `9f08f93c17e2cd7259a7ffe5e968b0be255a4a28e3f5fa672c43193fd7a6f391`.

| 지표 | 결과 |
|---|---:|
| JSON / generation schema | 각각40/40 |
| Adapter / canonical schema / final parser / semantic | 각각29/40 |
| READY gold exact target·축·거리 성공 | **20/20** |
| Non-READY gold raw READY / accepted READY | **1/20 / 0/20** |
| READY FN / 잘못된 accepted move | **0/20 / 0/20** |
| Unsafe accepted total | **0/40** |
| Latency mean / p95 | 4.132092 / 5.313616초 |

**10개는 raw decision은 맞지만 금지된 nonnull instruction/evidence를 남겼다.**
B01/B02/D02/G02/HD-C01/HD-D01/HD-E02/HD-G02/HD-H01/HD-I02이며
`INVALID_MODEL_OUTPUT`으로 거절됐다. HD-E02는 instruction=null이지만 dx가 nonnull이다.
이 필드를 지우거나 정답으로 재채점하지 않는다. **HD-B01**은 방향 없는 `X축으로 1m`를
READY로 판단해 grounding에서 거절됐고 raw FP1건으로 유지한다. 유효한 non-READY 정답은9/20이다.
최대 completion135tokens, transport/truncation 오류 없음. Commit91b464e, dirty=false다.

다음 계획은 **adapter/gold를 그대로 두고 별도 stricter generation schema**로 이미 요구한
READY/non-READY null 관계를 생성 단계에서도 제한하는 것이다. Null-stripping·자동 상태
변경·무제약 재시도는 추가하지 않는다. **Decision을 먼저 생성**하도록 권고했다:
quotes를 먼저 nonnull로 생성하면 grammar가 READY branch만 남겨 오판을 강제할 수 있다.
방향 누락의 새 일반 예시는 별도 prompt 버전으로 기록하며, schema만으로 source의 방향
모호성이 해결됐다고 주장하지 않는다. 이전 schema/prompt/출력은 모두 보존한다.

READY20/20은 단회 합성 development의 부분 성공이다. 새 schema·순서·예시의 효과는
미검증이며 CPU branch/token proof 후 별도 frozen 전체 진단이 필요하다. Semantic95% 이상,
raw FP0/unsafe0과 정식 development40×3·holdout80×3 gate를 그대로 유지한다.

후속 분기 검토: schema `36d42b9f…`와 prompt `99d73712…`의 **CPU 준비 검토 PASS**.
2.0의 7개 필드와 상태별 null 조건을 유지하고, prompt/branch 속성 순서를 decision→quotes로 맞췄다.
[최종 grammar 증거](../../evaluations/results/phase5x/generation2-v2-cpu-grammar.json)는 한국어 포함13개 수락·18개 거절을 기록한다.
버전 단독 객체·잘못된 버전·추가 approval·non-READY evidence·READY 양축 null이 거절됐다.
한국어를 거절한 regex 초안은 제외했다. 빈 문자열·공백·unsigned 축의 거절은 기존 backend가 계속 담당한다.
[최종 prompt 증거](../../evaluations/results/phase5x/generation2-v2-cpu-prompt.json)는 예시7개 schema→adapter→parser 통과를 기록한다.
기존6개 예시의 의미는 같고 방향 누락 예시1개만 추가됐다. 입력+출력768의 최대값은 dev3678/holdout3683<4096이다.
Holdout은 입력 길이만 확인했다. 두 증거와 최종 파일의 SHA가 일치하며 adapter/parser hash도 불변이다.
이 검토는 증거 읽기와 hash 대조이며 재실행하지 않았다. 분기·순서·예시를 함께 바꾸므로 개별 효과나 품질 통과를 주장하지 않는다.
