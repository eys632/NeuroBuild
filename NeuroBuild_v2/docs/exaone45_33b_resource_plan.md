# EXAONE4.5-33B Q4_K_M 조건부 자원·계약 계획

> 후속 결과: 사전 CPU/GPU 검증 뒤 첫120개는 semantic106/120으로 FAIL했다.
> 자체 서버를 종료하고 GPU3 반환을 확인했다. 같은 후보 반복·V2는 하지 않는다.
> [최종 진단 보고서](reports/phase5x_native_exaone45_diagnostic_report.md). 아래는 선택 당시 계획이다.

2026-09-20. **새 후보 사전 검증 단계, 미채택·품질 미검증.**

후속 상태: 다운로드/strict header와 continue-free template의 공개CPU검증을 완료했다.
원본native에서 system정책이누락되는문제를별도override로검증한근거는
[사전 보고서](reports/phase5x_exaone45_template_preflight_report.md)에보존했다. 실제vocab/context/GPU/품질은아직미검증이다.
아래다운로드전계획과공식template의원래상태는역사기록으로유지한다.
Qwen3.8 V2와 Gemma4 첫 gate 실패를 그대로 보존하고 다른 공식 계열을 비교한다.
한국어 일반 점수나 모델 크기로 이 프로젝트의 exact-quote/안전 gate 통과를 예상하지 않는다.

## 후보와 실행 범위

공식 `LGAI-EXAONE/EXAONE-4.5-33B-GGUF`, revision
`0e969634ef24db05151b435970297a6dee634b7e`, `EXAONE-4.5-33B-Q4_K_M.gguf`.
Remote20,047,839,424B/SHA `5ba3839b67dcee5618ea7b2206cedc8f9e2ec90fbcec3c95a8cc8b33967f6baf`.
원본 metadata pin은 `570aa4b15a4f45ba1133072b45f50198f6e3b4fd`다.
[Manifest](../runtime/models/exaone45-33b-q4-k-m.json),
[metadata provenance](../runtime/models/exaone45-33b-q4-k-m.provenance.json).
이 SHA는 이 문서 작성 시 원격 LFS 값이며 다운로드 후 실제 전체 payload/header 검증이 필요하다.
QAT라는 근거는 없고 공식 quantized GGUF다. Vision/mmproj/MTP 실행은 범위 밖이다.

EXAONE AI Model License1.2-NC의 연구·교육 평가/실험 범위로 제한한 **내부 비상업 연구 비교**다.
상업 제품·서비스/경쟁 모델 개발 등 제한을 우회하거나 제품 채택·외부 배포 허가로 해석하지 않는다.
공식 LICENSE/README와 attribution을 보존한다.
[고정 라이선스](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B-GGUF/blob/0e969634ef24db05151b435970297a6dee634b7e/LICENSE),
[고정 모델 카드](https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B-GGUF/blob/0e969634ef24db05151b435970297a6dee634b7e/README.md).

기존 f072 native source/build·CUDA11.8/SM80 binary를 재사용한다. 새 환경/설치/시스템 변경은 없다.
모델별 header/tokenizer/template/grammar/공개 응답/최대 문맥은 아직 검증되지 않았다.
이미 완료한 공통 runtime suite나 이전125개 진단·재생은 반복하지 않는다.

## 전체 GPU 계획

PhysicalGPU3 only/logicalCUDA0/TP1, context4096/sequence1/batch64/ubatch64,
F16 K/V, flash attention OFF, CUDA graphs OFF, speculation/MTP OFF다.
Official config는 hidden5120/vocab153600/FFN27392/main64+MTP1/Q40/KV8/head128이며
SWA는 카드128 대신 config4096을 보수적으로 사용한다. Untied output 실물도 확인해야 한다.

| 구성 | MiB | 근거·한계 |
| --- | ---: | --- |
| GGUF 전체 파일 올림 | 19,120 | MTP/CPU 잔류 부분도 제외하지 않은 전체 파일 proxy |
| F16 K/V,65층 전체4096 | 1,040 | 정상64층 기대1024보다16 추가; SWA 절감 미가정 |
| 최대 F32 행렬 전개1개 | 3,000 | vocab153600×hidden5120×4bytes |
| Graph/intermediate | 2,048 | 실측·엄밀 상한이 아닌 계획 여유 |
| Driver/module/handle | 1,024 | 계획 여유 |
| Pool/workspace/alignment | 1,024 | 최대 행렬 전개와 별도인 계획 여유 |
| Loading/fragmentation/미확정 | 1,416 | 계획 여유 |
| **전체 예상 peak** | **28,672** | hard cap/할당 상한 증명 아님 |

기준 free36,373MiB에서 safety=max(6144,ceil20%)=7,275MiB,
허용29,098MiB이므로 계획값은426MiB 아래다. 현재 용량 보장이 아니며 실제 실행 직전 fresh5표본
free/util/swing과 margin을 재계산한다. 조건 미달이면 실행하지 않으며 다른 GPU로 fallback하지 않는다.
공용 프로세스 존재만으로 중단하지 않지만 그 메모리·프로세스를 변경하지 않는다.
기존 guard의 aggregate 관측/여유감소 시 자기child 종료는 순간 OOM 방지나 process 격리의 보장이 아니다.

이 보수적 계획은 RTX32GiB에20% margin을 적용하면 들어가지 않는다. A100 검토를 RTX fit으로
승계하지 않으며 RTX는 PREDICTED_UNVERIFIED다. 공통 코드와 별개로 이후 runtime/artifact 선택이 필요하다.
실제 header나 실행경로가 다르면 먼저 계획을 재검토하고 자동 cap축소/offload/fallback하지 않는다.

## 명시할 sampling과 CPU 계약

한국어 권고 T0.6/top_p0.95/top_k20/presence1.5를 선택한다. 카드의 일반 text-only T1/P.95와 구분한다.
프로젝트 고정값은 min_p0/frequency0/repeat1/repeat_last_n64/seed42,
samplers `penalties,top_k,top_p,min_p,temperature`다.
Window64와 활성 순서는 pinned native 기본을 따른 것이며 모델 카드가 지정한 전체 preset이라고 하지 않는다.
Penalty는 **prompt와 생성의 마지막64토큰 모두**에 적용된다. Generated-only penalty가 아니다.
`enable_thinking=false`를 명시하고 원문/최종JSON 보정이나 repair는 하지 않는다.

기존 Qwen/Gemma/vLLM wire를 유지하는 별도 profile과 정확한 모델/quant tuple 검증을 추가한다.
새 모델 공개 fixture에서 공식 token ID·raw roundtrip을 비교한다. NFC normalizer가 있어 native와
decomposed Unicode가 다를 가능성은 아직 검증 전이며 기존 Qwen variant를 자동 승계하지 않는다.
Generic chat auto-parser의 empty-think prefix/final schema/EOG/reasoning 폐기 경계를 CPU에서 확인한다.
완료한 이전 모델 검증으로 대신하지 않는다. Gold/canonicalparser/semanticgate는 그대로다.

## 디스크와 진행 순서

처음 free28,136,112,128B는 manifest20,047,878,049B 후20.5GiB reserve를 충족하지 못했다.
재현 가능한 비활성 Gemma GGUF 한 파일17,651,001,568B만 exactSHA/UID/단일link/정상종료/
독점lock/ownFD·maps 확인 후 회수했다. 평가·freeze·source·metadata·복원 manifest는 보존했다.
실제 다운로드 직전 free45,774,725,120B, 완료 후 예상25,726,847,071B,
floor22,011,707,392B로 precheck PASS다. 2초 disk guard/1800초 한도/emptyCUDA/자체childcleanup을 사용한다.
이 시점은 다운로드 시작이며 완료·실제SHA·GPU·품질 PASS가 아니다.

순서: 고정 다운로드/전체SHA → strict header → 새 모델 CPU 계약 → 새 변경 회귀·검토·checkpoint →
fresh GPU3 조건부 startup/public1/resource1 → 별도 단회 품질 조건 동결·push → exposed120×1+warmup5.
Schema120/semantic≥114/rawFP0/unsafe0/raw관측120 기준은 유지한다.
명백한 실패는 추가 반복0·V2/새 holdout0으로 끝낸다. 1차 통과/경계선일 때만 미확정 사항을 위한
최소 후속 검증을 정한다. 이미 노출된 V2를 새로운 unseen 결과로 부르지 않는다.
미사용80 초안은 아직 ignored/unfrozen이며 이 문서는 그 실행을 승인하거나 시작하지 않는다.
비필수 batch/graphs/flash/throughput 최적화는 future optimization이다.
