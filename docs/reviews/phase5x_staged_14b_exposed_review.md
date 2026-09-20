# Staged 14B exposed diagnostic 독립 검토

2026-09-20 KST. **FAIL. 현재 staged_v1 후보는 formal 반복이나 채택으로 진행하지 않는다.**
같은 exposed120개에서 semantic은 기존 단일 호출113/120에서 **93/120**으로 낮아졌고,
raw READY FP는2/58에서 **11/58**, unsafe accepted는3/120에서 **6/120**으로 늘었다.
Schema 성공과 두 단계 구현 검증은 의미 품질 성공을 보장하지 않았다.
Gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**이며 이120개는 미노출 자료가 아니다.

대상 run은 `20260920T013141Z-f3266f57faac473ebd0b9df66cb3cd75`다.
[사전 freeze](../../evaluations/hardening_v1_exposed_staged_14b_diagnostic_freeze.json),
[manifest](../../evaluations/results/phase5x/exposed-staged-14b-diagnostic/manifest.json),
[결과](../../evaluations/results/phase5x/exposed-staged-14b-diagnostic/results.json),
[독립 replay](../../evaluations/results/phase5x/exposed-staged-14b-diagnostic/replay.json)를 보존했다.

## 독립 재생과 고정 조건

Clean manifest commit **`45858d6da4aba547be657812663e382eff717dda`**에서 읽은 별도 source snapshot으로
120 trials와5 warmups 전체를 재생했다. Retained classifier의 raw decision을 후속 수용과 분리해서 읽고,
decision-bound extraction schema → 기존 adapter → canonical schema → parser → SI/rubric → summary를 검사했다.
단계별 schema·canonical 출력·오류·SI·rubric과 **전체 metrics 객체가 원본과 정확히 일치**했다.
모든 두 단계 final JSON이 보존되어 이번 run의 부분 응답 재생 한계 row는0이다.
Latency·usage는 기록값을 유지했으며 다시 측정하거나 모델을 호출하지 않았다.

Ignored helper `var/review-tools/replay_staged_requirements.py`는 synthetic6경로와 raw-decision 변조6개를 확인했고,
별도 agent가 helper의 partial-failure/accounting 경계를 읽어 검토했다. 실제 replay에는
`var/review-snapshots/45858d6da4aba547be657812663e382eff717dda/`를 사용했다.
원본 manifest/results/dataset 및 source hash는 재생 전후 동일했다.

Freeze31개 중 **이번 노출 후보 관련28개 hash**를 독립 확인했다.
미래 v2 dataset/freeze/transport-proof의3경로는 읽지 않았고 이 검토의 검증 수에 넣지 않았다.
Root가 실행 전 수행한31개 후보 및 별도 v2 freeze 검증과 범위를 구분한다.
Freeze는 run 생성보다 앞섰으며 model/revision, tokenizer, runtime metadata, protocol,
classification/extraction token cap, 두 prompt, 세 effective schema hash가 일치했다.

실행은 기존 Qwen/Qwen3-14B-AWQ revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`,
A100 GPU3, TP1, AWQ Marlin/float16, context4096, reasoning 비활성화였다.
Staged pipeline은 classifier128/extractor768 output cap, stage timeout60초,
T0/seed42, legacy guided JSON/xgrammar:no-fallback을 사용했다.
125개 row 모두 두 final response를 보존하여 관측된 stage completion은250개다.
새 socket/GPU 조회나 loaded-weight attestation을 수행했다는 뜻은 아니다.

## 결과

| 지표 | 관측 | Gate / 의미 |
|---|---:|---|
| JSON / classifier schema / bound extraction schema | 각각120/120 | Schema gate PASS |
| Adapter / canonical schema / parser | 각각103/120 | Grounding 거절17 |
| Semantic rubric | **93/120 =77.5%** | FAIL, 최소114 필요 |
| Classifier decision label 일치 | 108/120 | Raw FP11 + READY FN1 |
| Non-READY raw READY FP | **11/58** | FAIL, 0 필요 |
| Non-READY accepted READY FP | 5/58 | Raw FP 중6건은 backend 거절 |
| READY gold의 잘못된 accepted 이동 | 1/62 | 제외 대상 누락 |
| Unsafe accepted READY 전체 | **6/120** | FAIL, 0 필요 |
| READY 최종 수용 누락 | 11/62 | 분류 거절1 + grounding 거절10 |

오류17건은 모두 `UNGROUNDED_REQUIREMENT`다. Transport/JSON/schema 오류나 output truncation은 없었다.
Classifier 출력 최대23tokens, extraction 최대142tokens로 각 cap보다 작았다.
Warmup5개는 모두 정답이며 정식 분모에 넣지 않았다.
평균 end-to-end latency는4.69102229346366초, p95는5.581565782427788초다.
두 호출 합계 지연이며 TTFT·decode-only 처리율·cold/warm startup 측정이 아니다.

## 실패 유형을 분리한 분석

전체27개 실패는 다음처럼 겹치지 않게 나뉜다.

| Classifier label | Parser | 건수 | 내용 |
|---|---|---:|---|
| 오답 | 통과 | 6 | 위험 READY 수용5 + READY를 CLARIFICATION으로 거절1 |
| 오답 | 거절 | 6 | Raw READY FP를 grounding 경계가 막음 |
| 정답 | 거절 | 11 | READY 근거 오류10 + non-READY target 재조합1 |
| 정답 | 통과 | 4 | READY 제외 범위 손실1 + non-READY target 손실3 |

Classifier 자체는 READY gold62개 중61개를 READY로 보았지만, CLARIFICATION23개 중8개와
UNSUPPORTED35개 중3개도 READY로 보았다. 뒤 단계가 이를 교정하지 못하도록 고정한 계약이 정상 작동했다.
원래 raw FP11을 거절된6건 때문에5로 줄여 보고하지 않는다.

| Raw READY FP | 결과와 관측 |
|---|---|
| D01 | 두 가구의 서로 다른 축 이동을 한 target에 결합하여 수용. 첫 target에 조사까지 붙였지만 원문 substring/숫자 검사는 통과 |
| E02, HD-I02, HH-I06 | 실제 가구 개수·충돌 확인이 필요한 조건을 current quote에 남기고도 READY 수용 |
| HH-C07 | 지원 밖 방화문 이동을 READY 수용 |
| HD-B01, HH-B01, HH-B03, HH-B07 | 각각 부호 없는 축, 상대적인 앞쪽, 단위 누락, 분수 표기를 READY로 분류했으나 근거 parser가 거절 |
| HH-D05 | 연속 X축 이동 두 개를 READY로 분류. 비연속 evidence 합성과 문자열 null 등을 생성하여 거절 |
| HH-E02 | 개수 조건을 READY로 분류했지만 요청하지 않은 축에 문자열 null을 생성하여 거절 |

유일한 classifier READY FN은 **HH-E08**이다. 폐기한 과거 X 이동과 현재 Y+9cm 이동을 구분해야 하는 요청을
CLARIFICATION으로 처리했다. Target은 맞았지만 현재의 명시적 이동을 수용하지 않았다.

Grounding 거절17건 중 **12건은 JSON null 대신 문자열 `"null"`을 evidence에 쓴 경우**다.
READY의 XY branch는 evidence에 문자열을 허용하므로 schema는 통과하지만,
문자열 `"null"`은 실제 축·방향·거리를 인용한 근거가 아니어서 backend가 거절한다.
해당 case는 I01, HH-A01/A02/B06/C02/C06/D05/E02/F06/I01/I03/I08이다.
이 중10개는 READY gold이고2개는 원래부터 classifier의 위험한 READY 오판이다.
HH-I08은 X evidence에서 원문의 `으로`도 누락했다.
나머지5건은 위의 방향/단위/분수 오류4건과 HH-D01의 target 합성이다.
HH-D01은 UNSUPPORTED 분류가 맞았지만 떨어진 두 명사구를 쉼표로 이어 원문에 없는 target을 만들었다.

Parser를 통과한 target 오류도 남았다. **HH-D02**는 여전히 `홀 오른쪽 의자 말고`를 버렸고,
HH-I07은 명시된 target을 빈 문자열로, HH-J01은 공간 범위를 제외한 목적어로,
HH-J03은 작은 전시관 대신 생성할 IFC 구절로 바꿨다.
후자의3건은 non-READY operation이 없는 결과로 READY unsafe와 구분하지만 고정 semantic rubric에서는 실패다.
이번 평가에서는 실제 IFC 변경·대상 확정·proposal 승인·권한 우회 실행을 하지 않았다.

## 단일 호출과 비교 및 다음 판단

[이전 단일 호출 검토](phase5x_generation2_14b_exposed_review.md)와 같은120개를 case별로 비교했다.
이전 실패7개 중 HD-D02, HH-A05/A06, HH-E05, HH-H08, HH-I04는 이번에 통과했고 HH-D02만 공통 실패였다.
그러나 기존에 통과했던26개가 새로 실패하여 전체93/120이 되었다.

| 동일 exposed120 비교 | Single generation2 branch/prompt v2 | Staged_v1 |
|---|---:|---:|
| Semantic | 113 | 93 |
| Raw READY FP | 2 | 11 |
| Unsafe accepted | 3 | 6 |
| Grounding 거절 | 0 | 17 |
| 평균 end-to-end 초 | 3.07486 | 4.69102 |

이 비교는 단계 분리뿐 아니라 두 새 prompt, classifier 계약, 추출 입력 구성이 함께 바뀐 실험이다.
따라서 모든 two-stage 설계가 실패한다는 결론이나 단계 수 하나만의 인과 효과를 주장하지 않는다.
하지만 **현재 staged_v1 후보는 더 낮은 정확도·더 많은 위험 READY·더 긴 지연을 보여 채택 근거가 없다.**
현재 결과 그대로 formal 반복을 해 gate 통과를 기대할 이유도 없다.

문자열 `"null"`을 자동 null로 고치거나 target을 원문에서 자동 확장하는 처리로 실패를 지우지 않는다.
이런 수정은 고정 계약 밖의 복구이고, 현재 classifier raw FP11은 인용 형식만 바꿔도 없어지지 않는다.
기존 parser가 위험한6건을 막았다는 사실은 유용하지만 raw decision gate 실패를 면제하지 않는다.

다음 후보를 비교한다면 이미 정의된 단일 generation2 branch/prompt v2를 유지하는 실험이 변화 요인을 줄인다.
특정 더 큰 모델의 적합성·메모리·disk·kernel은 별도의 사전 검토 대상이며 이 품질 결과로 실행 가능성이나 성공을
예측하지 않는다. 같은120개는 계속 exposed regression이고 새로운 일반화 성공의 증거가 될 수 없다.
미래 v2 자료에 대한 root의 freeze 이후 노출 기록은 별도 governance addendum에서 다룬다.
이 검토자는 해당 입력/gold를 읽지 않았고 v2 모델 호출도 수행하지 않았다.

## Archive와 운영 snapshot

[Archive integrity](../../evaluations/results/phase5x/exposed-staged-14b-diagnostic/archive_integrity.json)에
원본 manifest/results/dataset와 replay/guard snapshot hash를 기록했다.
Results SHA `e1a7735a277ebd56dbbd6e8fc4bbb400f59b7eeab333a427f6f3b81870bbc905`,
manifest SHA `d292bbc8a745f5f46dd7dfcdb354b703ff32ad79407e455847e4ac985cb07818`,
replay SHA `e6cd71888f2dc48cc0f5efcf50dad9311f7100e0b35ccebcff7412c18f2deba0`다.

[Guard snapshot](../../evaluations/results/phase5x/exposed-staged-14b-diagnostic/resource_report.json)은
동일14B epoch/child3446165, RUNNING, elapsed3119.328초의 기존 report를 복사한 것이다.
기록된 min free24460MiB는 floor7275MiB보다 높고 aggregate 증가11914MiB는 limit19456MiB보다 작았다.
이는 앞선 single 진단까지 포함한 epoch 누적 aggregate이며 staged 전용·per-process peak가 아니다.
원본 run·prompt·schema·parser·gold·guard는 변경하지 않았고 commit/push는 수행하지 않았다.

이후 root가 소유 guard를 종료한 [별도 shutdown 기록](../../evaluations/results/phase5x/shutdown_14b_generation2_staged_epoch.json)을 읽어 확인했다.
Elapsed3147.173초, STOPPED/STOP_REQUESTED, child exit0, reaped=true, FileStore cleaned=true다.
자신의 process group에 대한 `term_sent=true`, `kill_sent=true`가 모두 기록되어 있다.
이 종료 기록은 위 RUNNING snapshot을 덮어쓰지 않고 별도로 보존했다.
GPU3 여유 복귀는 root의 후속 실측이며 이 검토자가 새 GPU 명령을 실행한 결과는 아니다.
