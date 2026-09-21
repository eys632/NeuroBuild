# Generation2 분기 schema MoE 진단 독립 검토

2026-09-20 KST. **Development40×1 진단 PASS: semantic40/40, raw FP0/20, unsafe0/40.**
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 정식 반복 gate 완료가 아니다.
[결과](../../evaluations/results/phase5x/development-generation2-branches-moe-diagnostic/results.json)와
[manifest](../../evaluations/results/phase5x/development-generation2-branches-moe-diagnostic/manifest.json)는
run `20260919T235318Z-504ae53e55864b4fba35c6bb108c8c05` 원본과 byte 단위로 일치했다.
Results SHA `70caf1b6e7ad209a86174676f1fc3d8e50c8431309526daae3edbf1b736d57e0`.

CPU replay는 **40 trials+5 warmups**의 retained JSON 전부를 사용했다. Raw decision을
adapter 이전 출력에서 다시 확인하고 generation schema→projection→canonical schema→기존
parser→rubric→summarize를 재생했다. 단계별 flag·오류·원문/code UUID/context·SI·전체 지표가 일치했다.
Source hash8개도 일치하며 branch schema `36d42b9f…`, prompt `99d73712…`를 실제로 사용했다.
기존 routine의 두 경로만 바꾼 `var/review-tools/replay_generation2_branches.py`의 SHA는
`9b3ad4c9178eaa9405bb2744a9c5d8b0de62abcb6b00c2a61244252a2c305383`이다.

| 지표 | 결과 |
|---|---:|
| JSON / generation schema / adapter / canonical schema / parser / semantic | 각각40/40 |
| READY / CLARIFICATION / UNSUPPORTED 정답 | 20/20 / 8/8 / 12/12 |
| Non-READY raw READY / accepted READY | 0/20 / 0/20 |
| READY FN / 잘못된 accepted move / unsafe total | 0/20 / 0/20 / 0/40 |
| Latency mean / p95 | 3.899001772888005 / 5.125592811964452초 |

Warmup은 지표 분모에서 제외했다. Latency는 원래 기록을 보존했으며 최대 completion115tokens,
오류0건이다. Manifest는 commit `29a6c776…`, dirty=false, 고정 seed42를 기록한다.
이 replay는 모델 재호출·weight/runtime 재인증이 아니며 원본 출력이나 gold를 수정하지 않았다.

분기·필드 순서·예시가 함께 바뀌었으므로 개별 변경의 인과 효과는 분리할 수 없다.
다음은 동일 설정을 고정한 **정식 development40×3**, 통과 후 **holdout80×3**이다.
동일 seed 반복은 독립 표본이 아니며, 현재 결과만으로 Phase5.x 완료·최종 모델 선택·RTX 실증을 주장하지 않는다.
