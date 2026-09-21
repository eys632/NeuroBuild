**32B thinking / generation2 CPU preflight — PASS, 모델 품질 미검증**

최종 prompt `db1880ecebf697a215d4f3fedb970e0cdb1668837d0b121c92276cda8f6870e2`를
실제 로컬 32B tokenizer와 기존 client로 검증했다. 실제 모델·HTTP·GPU 호출은 없었다.
이 PASS는 제한된 진단 실행을 준비하는 계약·문맥 검증이며 후보 채택을 뜻하지 않는다.

| 자료 | 사례 수 | 최대 입력 | 입력 + 전체 출력 1024 | context 여유 |
|---|---:|---:|---:|---:|
| 기존 development | 40 | 2918 | 3942/4096 | 154 |
| 노출된 기존 holdout 회귀 자료 | 80 | 2923 | 3947/4096 | 149 |
| v2 입력 길이만 | 80 | 2848 | 3872/4096 | 224 |

시스템 prompt는 2507 tokens다. Actual client의 fake HTTP request 200개를 정확한
prompt·원문 전체·axis context·schema·sampling·thinking flags와 비교했다. V2 입력/gold,
사례 ID, 사례별 길이 또는 모델 출력은 archive에 기록하지 않았다.

- `baseline.json`: checkpoint `0fd60350b6e9df6538e5cf3d1ee1b13fa949fccc`의 `git show` bytes와 비교한 11개 파일 hash.
- `verify_cpu_preflight.py`: 실제 실행한 CPU helper. 이 archive 위치에서 그대로 실행하도록 root를 계산한다.
- `cpu_preflight.json`: 전체 측정·검증 결과와 소스/tokenizer/설치 runtime hash.
- `independent_review.md`: 검증 범위와 reasoning/grammar 호환성의 한계.
- `integrity.json`: 위 파일의 byte 수와 SHA256. 자기 자신의 hash는 포함하지 않는다.

실행 명령:

```sh
CUDA_VISIBLE_DEVICES='' USE_TORCH=0 USE_TF=0 HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
  .conda-vllm/bin/python -B evaluations/results/phase5x/32b-thinking-preflight/verify_cpu_preflight.py
```

Helper는 마지막에 `cpu_preflight.json`을 exclusive 생성하므로 기존 증거를 덮어쓰지 않는다.
재실행이 필요하면 원래 증거를 별도로 보존한 격리 checkout에서 동일한 archive 상대 경로,
기존 환경·metadata·입력 파일을 복원한다. 설치나 weight 재검증은 수행하지 않는다.
현재 proof SHA256은 `2b40e70de79b7f0224f7afd80079246c9cb2c4f34286ab89a405290915d2002c`다.

기존 2.0 branch schema의 7개 예시는 xgrammar token/EOS, 2.0 adapter 및 canonical parser를
모두 통과했다. Grammar compile은 1.885858초였다. CPU xgrammar가 Torch를 import했지만
GPU mask를 유지했고 CUDA는 초기화되지 않았다. 사용 버전은 Transformers4.51.3,
xgrammar0.1.18, Torch2.6.0+cu118, vLLM0.8.5+cu118이다.

1024 tokens는 reasoning과 최종 JSON의 합산 한도다. 문맥 적합성은 완결성·latency·GPU peak·
품질 성공을 증명하지 않는다. Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이며
v2 root 입력 노출 이력을 그대로 유지한다. RTX5090 actual 실행도 검증하지 않았다.
