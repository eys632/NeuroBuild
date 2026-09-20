# Qwen3.6 첫 단회 진단

현재 상태: **FROZEN_NOT_EVALUATED**. CPU checkpoint `fdd4f01d09033e0d037f1ad6cdd44307500a080f` 뒤
새 후보의 첫 startup/public/resource를 동일 GPU3 own epoch에서 완료했다. 기존 완료 runtime 검사는 반복하지 않았다.

공개 production 요청1건2.707237813초, full context3328+768 요청1건10.769428756초다.
GPU3 기준선 대비 전체사용 증가 peak19854MiB/minfree16520MiB는 개별 process VRAM 측정이 아니다.
Fresh free36373/util0, 운영예산28672와 별도 margin7275를 적용했다.

[사전 동결](../../evaluations/hardening_v1_exposed_native_qwen36_diagnostic_freeze.json)은69개 source/metadata/proof hash와
현재 own epoch, 새CPU1건/역사적 exposed120 길이승계를 묶는다. SHA256 `57c6af28c15fc879153d998968a007cfaa698bd4a1cea25da09dcaeeaaeaf074`.
노출120×1+warmup5, output768/ctx4096/timeout120, explicit qwen36 nonthinking profile만 허용한다.
Schema120/120, semantic≥114/120, rawFP0/58, unsafe0/120 기준을 유지하고 unknown 분모를 줄이지 않는다.
명백한 FAIL이면 같은 후보 반복·V2·미사용80 평가 없이 종료한다. PASS 후 필요한 최소 후속 검증은 별도로 판단한다.

현재 품질 결과·latency 평균/p95·오류 집계는 아직 없다. Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED다.
기존125개 평가와 독립 재검산은 보존했고 재실행하지 않았다. 기존422회귀 PASS와 production source가 같아 suite도 반복하지 않았다.
[CPU 보고서](phase5x_qwen36_cpu_report.md), [runtime 원본](../../evaluations/results/phase5x/qwen36-first-runtime-evidence/README.md).
