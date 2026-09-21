# Generation2 greedy 정식 development 독립 검토

2026-09-20 KST. **정식 development40×3의 네 gate PASS. 첫 holdout 후보 freeze로 진행 가능하다.**
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 Phase5.x 전체 완료를 뜻하지 않는다.
[결과](../../evaluations/results/phase5x/development-generation2-branches-moe-greedy-formal/results.json)와
[manifest](../../evaluations/results/phase5x/development-generation2-branches-moe-greedy-formal/manifest.json)는
run `20260920T001240Z-7daf0ae403de40cfa9043c628abf9d8d` 원본과 byte 단위로 일치했다.
Results SHA `b47a63f0927e90290e334b3a81e15b5fff71b25f49d2f88f84a0a4560d748d99`.

CPU routine `var/review-tools/replay_generation2_branches.py`로 **120 trials+5 warmups**를 재생했다.
원문/code UUID/context와 raw decision→generation schema→adapter→canonical schema→기존 parser→
SI/rubric/전체 summary가 exact match다. 원본을 수정하지 않았고 모델 호출은 수행하지 않았다.
[Greedy freeze](../../evaluations/hardening_v1_generation2_branches_moe_greedy_development_freeze.json)의
**21개 파일 hash**, manifest와 runtime/protocol16개 비교, weight manifest·runtime metadata hash가 일치했다.
Routine SHA `9b3ad4c9178eaa9405bb2744a9c5d8b0de62abcb6b00c2a61244252a2c305383`.

| 사전 gate / 보조 지표 | 결과 |
|---|---:|
| Generation schema100% / semantic≥95% | 각각120/120, PASS |
| Non-READY raw READY FP0 / unsafe accepted0 | 0/60 / 0/120, PASS |
| Adapter / canonical schema / parser | 각각120/120 |
| Accepted non-READY FP / READY FN / 잘못된 accepted 이동 | 각각0/60 |
| READY / CLARIFICATION / UNSUPPORTED 정답 | 60/60 / 24/24 / 36/36 |

Manifest는 **legacy_greedy, 명시 sampling `{temperature: 0, seed: 42}`**를 기록한다. 나머지
sampling 값은 server/model defaults이며 전부 명시한 실험이나 temperature만 분리한 비교가 아니다.
Generation2·branch schema·prompt v2·768tokens·timeout60초·concurrency1·thinking=false가 freeze와 같다.
결과 기록은125개이며 모두 오류가 없다. Warmup5개는 정식120회와 latency 통계에서 제외했다.
Latency mean4.39429099104212초/p955.910858407616615초, 최대 completion115tokens다.
40case 모두3회 semantic 결과가 같았다. 동일 seed/greedy의 보편적 결정성이나 독립120표본은 주장하지 않는다.
Commit `468f6f0e…`, dirty=false다. 실행 중 실제 wire를 별도 캡처하거나 loaded weight를 재인증한 검토는 아니다.

[앞선 neutral 정식 FAIL](phase5x_generation2_branches_formal_review.md)의 results/manifest hash는 그대로다.
그 unsafe1건을 지우거나 새 성공과 합치지 않았다. 현재 통과는 이 고정된 합성 development 조합에 한정된다.
첫 holdout warmup 전에 동일 후보·설정·gold·80×3/5warmups·네 gate를 별도 freeze/checkpoint로 고정해야 한다.
[기존 holdout 절차](phase5x_holdout_protocol_review.md)에 따라 첫 노출 이후 출력 기반 튜닝은 금지한다.
GPU 자원·남은 시간 확인은 실행 담당자의 별도 gate다. Holdout·사람 검수·실제 IFC 적용·RTX 실증은 아직 남아 있다.
