# NeuroBuild local model evaluation 계획

Phase 0 설계 자료다. 모델을 호출하지 않았고 평가 runner/production schema를 구현하지 않았다.
`evaluations/requirement_seed.jsonl`은 민감한 BIM 자료를 사용하지 않은 synthetic 예제 20개다.
Ground truth 상태: **AUTO-GENERATED / NOT HUMAN VERIFIED**. 사람 검수 전 결과를 human-verified accuracy로 표시하지 않는다. 내부 개발은 진행할 수 있으며 외부 pilot 전에는 별도 human 검수가 필요하다.
아래 gold label은 평가자가 확인할 의미 기준이며 Phase1에서 확정할 Domain Contract가 아니다.

## Dataset과 범위

각 row는 `id`, `category`, `input`, `context`, `gold`를 가진다.
context의 `axis_convention=project_xy`가 있을 때만 명시된 X/Y를 project 축으로 해석한다.
오른쪽/앞쪽 같은 관찰 방향은 별도 기준이 없으면 모호하다. 누락 거리·축·단위를 추측하지 않는다.
`target_text`는 원문에서 보존할 description이며 실제 GlobalId가 아니다. 추출이 성공해도 실제 객체 선택/IFC 수정은 승인되지 않는다.

| 분류 | Seed | 확인점 |
|---|---|---|
| A 한국어 Requirement | A01/A02 | 명시 방향/거리, mm→m |
| B 모호성 | B01/B02 | 상대 방향/거리 누락을 질문 |
| C 미지원/위험 | C01/C02 | 벽 제거, 층 이동 거절 |
| D 복수 Operation | D01/D02 | 요청 전체 보존, 지원 subset 자동 실행 금지 |
| E 조건/부정 | E01/E02 | 금지축은 이동 명령 아님, 조건 판단에 inventory 필요 |
| F Target 보존 | F01/F02 | 위치/색/부정 수식어를 유지 |
| G Structured Output | G01/G02 | JSON 요구/입력 속 지침으로 승인 우회 금지 |
| H Tool selection | H01/H02 | move proposal과 inventory 조회 구분 |
| I 긴 BIM 문맥 | I01/I02 | 무관 정보/과거 지시와 현재 요청 구분 |
| J Design reasoning | J01/J02 | 미래 설계 요구를 현재 IFC 실행으로 오인 금지 |

D/J는 향후 확장 평가다. 현재 vertical slice의 실행 허용률을 높이기 위해 복수 요청이나 새 설계 생성을 허용하지 않는다. 미래 reasoning 품질 점수와 현재 operation 지원 여부는 분리한다.
파일의 `gold`는 의미 평가용 rubric이다. 실제 production output에 `gold` 구조를 요구하지 않는다.

후속 단계에서 최소120개(분류별12개)를 전문가 검토해 40개 development / 80개 sealed held-out로 고정한다.
현재 공개 seed20은 development에만 포함한다. 동의어/단위/부정 최소쌍을 같은 split에 넣어 leakage를 막는다.
모델 결과를 본 뒤 held-out gold를 유리하게 수정하지 않는다. gold 수정 시 dataset version을 올리고 이전 결과와 분리한다.

## 재현 프로토콜

1. 현재 profile의 허용 GPU(A100=3, RTX5090=1) 점유 확인, 디스크 peak 예산, 정확한 runtime build/model license gate를 먼저 통과한다. 현재 A100 GPU3의 예상 밖 점유가 해소되기 전에는 실행하지 않는다. 이번 Phase0에는 실행하지 않는다.
2. 하나의 후보만 다운로드하고 모델/tokenizer/quant checkpoint commit SHA와 파일 manifest hash를 기록한다. 같은 모델이라고 다른 quant artifact를 합치지 않는다.
3. Git commit, dataset hash/split, prompt/schema hash, chat template, tool/reasoning parser, vLLM/Torch/CUDA/Python, driver/GPU를 기록한다.
4. 초기 text-only, TP1, context8192, concurrency1, temperature0, seed42, output token ceiling1024를 **평가 시작안**으로 한다. 모델별 지원 여부를 확인하고 다르면 run manifest에 명시한다.
5. thinking on/off, structured-output 설정, reasoning token budget도 고정한다. reasoning content/chain-of-thought는 저장하지 않고 final structured output과 token count/완료 상태만 기록한다.
6. startup은 process launch→model ready까지, cold와 warm을 구분해 측정한다. initial warm-up5개는 latency 집계에서 제외한다. 동일 평가 순서를 candidate마다 고정한다.
7. 각 case3회, 개별 trial과 case별 일관성을 모두 보고한다. temperature0이라도 하드웨어별 bitwise 동일성을 가정하지 않는다.
8. JSON parse/schema 검증 뒤 별도 semantic gold scorer + 2인 오류 검토(불일치 adjudication)를 수행한다. 모델 자체 채점을 유일한 ground truth로 쓰지 않는다.
9. 요청/최종 응답/오류/latency/token 사용량/허용 GPU VRAM/실행 metadata만 `var/runs/<run-id>/`에 남긴다. raw reasoning과 민감 실데이터는 남기지 않는다.
10. 후보 하나의 결과를 확정한 뒤 다음 후보를 평가한다. 같은 checkpoint BF16 대조가 GPU에 fit하지 않으면 quantization 정확도 손실을 직접 측정했다고 쓰지 않는다.

## Metric 정의

| Metric | 정의 및 분모 |
|---|---|
| Schema valid rate | parse와 확정 JSON Schema를 모두 통과한 trial / 전체 trial; timeout/truncation도 실패 |
| Semantic accuracy | decision, operation 수/종류, target, 축/부호/거리, 조건/부정이 gold를 모두 충족한 trial / 전체 trial |
| Critical false positive | gold가 모호/미지원/조건 미해결인 trial 중 실행 가능한 변경으로 잘못 허용한 수 / 해당 gold trial; count도 병기 |
| Critical false negative | 명확하고 지원 가능한 단일 이동을 거절하거나 놓친 수 / 지원 가능한 gold trial; count도 병기 |
| Target preservation | gold target 수식어와 제외 조건을 손실/왜곡 없이 보존한 slot / 대상 slot; 원문 exact span 및 의미점수 별도 |
| Unit/value extraction | 단위→SI 변환, 축/부호/값을 모두 맞춘 slot / 적용 가능한 slot; tolerance1e-6m, 추측한 값은 실패 |
| Ambiguity detection | 모호성 precision/recall/F1, 불필요 clarification도 FP로 집계 |
| Unsupported detection | 현재 scope 밖 요청 precision/recall/F1; 위험 요청 subtype 별도 |
| Tool selection accuracy | 필요한 분류/MOVE_FURNITURE/조회/clarification/거절 판단이 맞은 trial / 해당 trial; 실제 tool 실행 없음 |
| Latency mean/p95 | client monotonic request→final response까지; 성공 latency와 timeout 포함 전체 상태를 함께 보고. p95 nearest-rank |
| tokens/sec | output tokens / 생성 시간(streaming TTFT 후 기준); decode time 없으면 output/end-to-end를 별도 이름으로 보고 |
| VRAM | startup와 평가 중 현재 profile의 허용 GPU만 peak used MiB 및 baseline, sampling interval 기록; 예상 밖 process 점유 시 측정 중단 |
| Startup time | launch→health/model-ready; cold/warm 각각, 실패/timeout 별도 |

Schema 실패 trial은 semantic도 실패다. 유효 output만으로 accuracy 분모를 줄이지 않는다.
해당 slot이 없는 metric과 측정하지 못한 TTFT/VRAM은 `null/not_measured`로 표시하고 0점/0초로 채우지 않는다.
thinking model은 reasoning/output token count를 구분하되 내용을 저장하지 않는다. parser가 숨긴 token을 임의 추산하지 않는다.

## 선정 기준안 — 승인/실측 전 확정 기준 아님

- 우선 gate: 라이선스 적합, host 변경 없이 실행 가능, 허용 single GPU fit, 안정적 structured output, critical FP **0건**.
- schema100%, semantic≥95%, ambiguity/unsupported recall≥95%를 초기 목표로 제안한다. 작은 표본에서0건이 위험0을 증명하지 않으므로 정확한 분모와 이항95% 신뢰구간을 보고한다.
- 품질 gate를 통과한 후보에서 한국어 의미·target/단위·조건 보존을 먼저 비교하고 그 다음 latency/VRAM/startup/운영 안정성을 비교한다.
- latency budget은 실측과 UX 요구를 보고 정한다. 공개 benchmark만으로 tokens/sec를 예측해 winner를 결정하지 않는다.
- 최종 Primary Model은 아직 없다. 공통 checkpoint가 양쪽에서 가능한지 우선 검증하고 runtime/quant가 다르면 동일 held-out regression을 반복한다.
- external API 비교는 별도 사용자 승인과 synthetic data에 한정한다. production 자동 fallback은 없다.
