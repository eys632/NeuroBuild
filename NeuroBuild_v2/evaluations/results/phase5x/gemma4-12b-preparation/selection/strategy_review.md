# 네 계열 실패 뒤 다음 실험의 정보가치 — 1쪽 재검토

2026-09-21 KST. **권고: Gemma4-12B 공식 QAT를 저비용 배포 대안이라는 별도 가설로 먼저 사전검증한다. Qwen3.6-35B-A3B는 비교 후보로 유지하되 자동 후속 실행 목록으로 삼지 않는다.** 이는 품질 순위·채택·다운로드 승인이 아니다.

완료된 근거는 다음과 같다. [Qwen3.8 첫 진단](../../docs/reports/phase5x_native_qwen38_diagnostic_report.md)은 semantic117/120·rawFP0·unsafe0였지만 [별도 V2](../../docs/reports/phase5x_native_qwen38_v2_minimal_report.md)는73/80·1/40·1/80으로 실패했다. [Gemma31](../../docs/reports/phase5x_native_gemma4_diagnostic_report.md)은115/120·1/58·2/120, [EXAONE33](../../docs/reports/phase5x_native_exaone45_diagnostic_report.md)은106/120·0/58·0/120이다. 새 [GLM 저장 재생 지표](../review-tools/glm47-exposed-review/independent_replay.json)는 schema120/parser118/semantic104, rawFP1/58·unsafe1/120·FN6/62·raw관측120이며 accounting PASS/quality FAIL이다. Root가 확인한 방화문 수용은 실제 IFC 실행이 아닌 고정 안전성 rubric 위반이다. 서로 다른 자료인120과80을 직접 성능 순위로 합치지 않는다.

최근 세 후보의 schema120은 형식 제약만으로 가구 범위·승인 경계·정상 요청의 과잉 거절을 해결하지 못했음을 보여준다. CPU/template/자원 검증의 성공이나 더 큰 모델·공개 benchmark는 이 의미 오류를 고친 증거가 아니다. 반대로 이 표만으로 모든 로컬 모델의 실패나 특정 양자화의 인과효과를 증명할 수도 없다.

| 후보 | 이번에 추가로 알 수 있는 것 | 비용과 한계 |
|---|---|---|
| **Google Gemma4-12B IT QAT Q4_0** | 공식 배포의 별도 unified checkpoint가 같은 계약에서 정확성과 낮은 자원 부담을 함께 만족하는지. 작은 장비 배포를 고려할 때 결과의 실용적 가치가 있다. | 같은 Gemma 계열이므로 독립 학습계열 추가가 아니다. 31B의115점이12B 통과 확률이 아니며 안전 오류 개선 근거도 없다. 공식 GGUF 약6.98GB는 비용 근거일 뿐 전체 VRAM·RTX 실측 증거가 아니다. |
| **Qwen3.6-35B-A3B Q4_K_M** | 이미 실패한 exact checkpoint와 다른 post-training/희소 구조의 결과를 확인한다. | Qwen 계열 재진입이며 학습계열 다양성이 새로 생기지 않는다. active3B를 저장/전체 메모리로 계산하지 않는다. 기존 metadata의 약20.42GB GGUF는 준비 부담이 더 크다. 모델 publisher Qwen과 quant publisher ggml-org를 구분하고 native hybrid/MoE/header/tokenizer 검증은 별도로 필요하다. |

공식 primary 재확인: [Google QAT 카드](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/blob/29d097773436b69ff9feafd636ab4cf873786537/README.md)는12B unified/system role/nonthinking 및 QAT 배포를 설명하며, [고정 파일 metadata](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/blob/29d097773436b69ff9feafd636ab4cf873786537/gemma-4-12b-it-qat-q4_0.gguf)는 SHA93567e…a538b를 확인해 준다. [Qwen 고정 공식 카드](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)는 nonthinking 호출을 지원한다. 두 모델의 공식 설명은 한국어 exact quote/가구-only/zero-FP 시험을 대체하지 않는다. 두 카드의 Apache2 표기도 작업 적합성 판정은 아니다. Qwen GGUF revision `baec3ebee244827cda0f4557eafa8b28f7545fa6`와 크기·source-link는 [이전 metadata 기록](next-candidates-after-exaone-refs.json)을 사용했다. 이번 web 렌더러의 GGUF/.src_sha 접근 오류를 새 검증 PASS로 바꾸지 않았다.

**유한한 다음 단계:** Gemma12의 실제 header·공식/embedded template·tokenizer·원문 왕복·고정768/4096 문맥·whole-peak를 후보별로 확인한다. 이미 완료한 공통 검증은 승계한다. 준비가 통과하면 결과를 보기 전에 모델/revision/공식 profile/기존 prompt2/schema/parser/gold/채점/자원 조건을 동결하고 최초120×1+warmup5 한 번만 수행한다. 목적은 위 배포 가설 검증이며 실패 사례별 prompt 보강·샘플링 탐색·lexical 안전 규칙을 끼워 넣지 않는다.

**중단·재평가 조건:** schema120/120, semantic≥114/120, rawFP0/58, unsafe0/120과 raw관측/unknown 분모를 그대로 지킨다. Clear FAIL이면 그 exact 후보의 재시도·전체3회·V2·미사용80 접근을 하지 않는다. Runtime/CPU 사전조건이 불충족이면 품질 호출 전에 후보를 보류한다. Gemma12도 실패하면 이번 저비용 배포 가설은 닫고, 다음 GPU 실험 전에 “어떤 미확인 가설을 왜 이 새 checkpoint가 검증하는가”와 비용을 한 문단으로 다시 등록한다. 크기·유행·공식 benchmark만 근거인 즉시 모델 교체는 진행하지 않는다. **이는 사용자 지시인 후보 비교의 중단이 아니라 자동 반복 실행의 중단**이며, Qwen3.6을 포함한 공식자료 비교는 계속할 수 있다. 노출120에서 후보를 반복 선택한 결과는 unseen 증거가 아니다. 기존 V2 노출·자동 gold/사람 미검수·RTX 미실측을 유지하고, 첫 gate를 통과한 뒤에만 별도 계획의 미사용 자료를 다룬다.

범위: 기존 보고서·새 GLM 저장 집계 및 공식 metadata/card 읽기만. Dataset/미사용 holdout/응답 본문 열람, 설치·weight 다운로드·native/GPU/평가/테스트·production 수정0.
