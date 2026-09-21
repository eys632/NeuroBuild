**32B generation2 thinking exposed diagnostic — 원본 보존 및 독립 재생**

Run `20260920T034014Z-0e8af7789bbe419db3f717de65242735`, clean checkpoint
`59e9b64312e32582371553a3a243bd566a72c845`. 품질 gate는 **FAIL**이다.
Semantic 109/120, 관측된 raw READY FP 2/58, unsafe accepted 1/120이며,
truncation 3건의 raw decision은 unknown이다. 독립 replay **PASS**는
보존된 결과와 평가 집계의 일치를 뜻하며 후보 채택을 뜻하지 않는다.

- `results.json`, `manifest.json`, `dataset.json`: 원래 run의 exact bytes. 모두 이미 노출된 v1 synthetic regression 자료다.
- `freeze.json`: 실행 전에 고정한 조건의 exact bytes.
- `replay.json`: offline frozen replay의 stdout 그대로. 평가 120건과 warmup 5건을 분리한다.
- `resource_report.json`: 자체 서버 종료 전 저장한 RUNNING watchdog snapshot. SHA256 `db26887cb4d06703286b8e7f67adb920959db30a791155842d072fdb96154b1e`.
- `failure_classification.json`: root의 사후 원인 분류를 exact bytes로 보존. 평가 결과나 gold를 고친 파일이 아니다.
- `replay_generation2_32b_thinking_exposed.py`: 실제 실행한 helper 그대로.
- `check_generation2_thinking_replay_synthetic.py`, `replay_preparation_selfcheck.json`: 실제 결과를 읽기 전에 수행한 synthetic 10경로와 변조 8건 거절 증거.
- `source_snapshot/`: checkpoint의 exact 19-file snapshot과 hash record. v2 본문과 model weight는 포함하지 않는다.
- `original_copy_provenance.json`: 원본 경로, byte 수, SHA256. RUNNING 보고서는 시점 snapshot이므로 이후 바뀐 live 파일과 같은 hash라고 주장하지 않는다.
- `integrity.json`: 자기 자신을 제외한 archive 파일들의 SHA256.

**재생 범위:** final generation JSON이 남은 trial 117건과 warmup 5건은
2.0 adapter → canonical1 schema/parser 및 frozen `evaluate_trial`를 완전히
재생했다. `HD-B01`, `HH-C03`, `HH-I04`의 truncation body는 저장되지 않았으므로
원래 error/unknown/flag/분모의 일관성만 확인했다. 그 3건의 응답이나 내부 추론을
복원하거나 독립 재관측했다고 주장하지 않는다. Raw decision 관측 범위는
117/120, non-READY gold에서는 55/58이다. 미관측을 안전한 non-READY로 세지 않는다.

Timing과 token usage는 원래 관측값이며 새 성능 측정이 아니다. GPU 보고서는
허용 GPU3의 aggregate sampling이다. 다른 작업과 분리한 per-process VRAM 측정이나
hard memory isolation이 아니다. Model/runtime manifest 연결을 확인했지만 원격으로
loaded weights를 새로 증명하지 않았다. Server log와 reasoning body는 이 archive에 없다.

Helper는 원래 위치에 의존하므로 archive 안에서 바로 실행하지 않는다. 저장소 root에서
exact helper를 `var/review-tools/replay_generation2_32b_thinking_exposed.py`로,
`source_snapshot/`을 `var/review-snapshots/59e9b64312e32582371553a3a243bd566a72c845/`로
복원한 뒤 hash를 확인한다. 다른 기존 파일을 덮어쓰지 않는다. Snapshot record SHA256은
`3d73a64ce97ef67149e03add34faf2497cbe05e26c315de4d6e73a77fc41c8b5`다.
기존 backend 환경의 jsonschema dependency가 필요하다.

```sh
CUDA_VISIBLE_DEVICES='' .conda/bin/python -B var/review-tools/replay_generation2_32b_thinking_exposed.py \
  evaluations/results/phase5x/exposed-generation2-32b-thinking-diagnostic \
  --freeze evaluations/hardening_v1_exposed_generation2_32b_thinking_diagnostic_freeze.json \
  --runtime-dir evaluations/results/phase5x/32b-generation2-thinking-v1-launch
```

위 재생은 고정 repository 파일과 runtime archive의 기존 hash를 요구한다.
v2의 9개 파일은 streaming hash만 확인하며 본문을 해석하지 않는다. Model/GPU/network
호출이나 weight payload 읽기는 없다. Root가 과거 일부 v2 입력/gold를 본 exposure
addendum도 보존하므로 완전 맹검을 주장하지 않는다. Gold는
**AUTO-GENERATED / NOT HUMAN VERIFIED**이며 실제 IFC 실행은 하지 않았다.

조건·집계·비교 한계는 [독립 리뷰](../../../../docs/reviews/phase5x_generation2_32b_thinking_exposed_review.md)를 참고한다.
자체 서버의 후속 종료 증거는 [shutdown 기록](../shutdown_32b_generation2_thinking_epoch.json)이며 RUNNING snapshot과 시점을 구분한다.
