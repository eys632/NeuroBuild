# Qwen3.6-35B-A3B 후보와 최소 사전검증

Gemma12 첫 gate FAIL 뒤, Qwen3.8 dense와 다른 35B total/3B active MoE checkpoint가 같은 한국어 추출·원문 인용·가구 범위·승인 경계를 만족하는지 검토한다. 같은 Qwen 계열의 새 checkpoint 비교이며, 구조 효과를 분리하는 실험이나 품질 개선 예측은 아니다. 공개 benchmark와 active3B를 품질 또는 전체 메모리 근거로 사용하지 않는다. 현재는 **metadata만 확보했으며 다운로드·header·CPU 계약·GPU·품질 검증은 대기**다.

## 고정 후보

원본은 [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/995ad96eacd98c81ed38be0c5b274b04031597b0), revision `995ad96eacd98c81ed38be0c5b274b04031597b0`다. 변환 배포자는 [ggml-org](https://huggingface.co/ggml-org/Qwen3.6-35B-A3B-GGUF/tree/baec3ebee244827cda0f4557eafa8b28f7545fa6)이며 revision은 `baec3ebee244827cda0f4557eafa8b28f7545fa6`이다. `.src_sha`의 PRIMARY가 원본 revision을 연결한다. 두 카드의 Apache-2.0 표기와 원본 LICENSE를 보존했다. 변환 로그는 quantizer `b15ca93`의 짧은 commit만 공개하며, 로컬 runtime f072와 동일한 빌드라고 주장하지 않는다.

유일한 weight 후보는 `Qwen3.6-35B-A3B-Q4_K_M.gguf`, **20,419,565,568B**, SHA256 `671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7`다. [최종 manifest](../runtime/models/qwen36-35b-a3b-q4-k-m.json)는 README·convert.log·weight3개이며 SHA256은 `70d4c0f73f763e10d17b0bad75acda2079dff6d49a9e2ed25575a86cff62b76c`다. 기존 downloader의 영숫자 시작 파일명 규칙 때문에 raw draft에서 `.src_sha` 항목만 제외했다. 원래 draft와 이미 검증한 `.src_sha` 원본·URL·SHA는 [변경 기록](../evaluations/results/phase5x/qwen36-metadata/manifest_projection.json)과 metadata 아카이브에 그대로 남긴다. Generic downloader는 변경하지 않았다. MTP·DFLASH·mmproj는 제외하며 새 weight 다운로드는 아직 대기다.

## 재사용 범위와 새 차이

Config는 hidden2048/vocab248320, 40층 중 GDN30+full attention10, routed256개 중8개와 shared expert를 지정한다. 고정 f072에 QWEN35MOE converter/loader/graph가 있다. 공개 변환 로그의 PRIMARY는 `--no-mtp`이며 733 tensors를 기록한다: F32 301/Q4_K121/Q8_0310/Q6_K1. 이 수는 실제 GGUF header 감사 결과가 아니다.

Qwen3.8과 base BPE vocab/merges·NFC normalizer·pre-tokenizer·decoder는 같지만 tokenizer JSON added tokens는26개 대33개로 다르다. 양쪽 tokenizer_config의 decoder 목록은33개여서 실제 변환 metadata 확인이 필요하다. Template도7764B 대8952B로 다르다. 명시 nonthinking, 비어 있지 않은 system 하나와 string user 하나, tools/history 없음의 현재 경로는 소스상 같은 출력식을 선택하지만 이번에는 render/encode를 실행하지 않았다.

기존 native build·194개 CPU 객체·guard·transport·schema/parser/scorer 정의를 재사용한다. 실제 typed tokenizer/template/flags와 유효 입력 경로가 같다고 입증한 부분만 과거 CPU 증거를 승계하고 새 PASS로 표현하지 않는다. 원래 wrapper는 완료 public/parity 및120/80 corpus를 함께 반복하므로 그대로 실행하지 않는다. 필요할 경우 새 profile/wire/template의 최소 공개 검사와 **노출120 입력 길이만** 검증한다. 기존 V2 길이80과 미사용80을 자동으로 열지 않는다. 과거 NFC 차이나 raw-reference variant를 새 후보의 관측 없이 자동 승계하거나 원문을 정규화하지 않는다.

## 명시 요청과 자원 조건

[공식 card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/995ad96eacd98c81ed38be0c5b274b04031597b0/README.md)의 nonthinking 값은 T0.7/P0.8/K20/minP0/presence1.5/repetition1이다. 새 이름 `qwen36_nonthinking_llama_cpp`로 구분한다. Window64/frequency0/seed42 및 `penalties,top_k,top_p,min_p,temperature` 순서는 기존 native presence profile에 따른 **프로젝트 선택**이다. Prompt도 penalty history에 포함되므로 원문 인용에 영향을 줄 수 있다. Window0은 presence 자체를 끄므로 사용하지 않는다. Generic generation_config의 T1/P0.95나 이전 Qwen3.8 neutral profile을 공식 nonthinking recipe로 대체하지 않는다.

Context4096/seq1/batch64/ubatch64/F16KV/flashOFF/graphsOFF, MTP·speculation·checkpoint0 조건에서 whole-VRAM 추정은 **27,808.427734MiB → 모델 계획27,904MiB**다. 운영 계획28,672MiB를 두면 더 보수적이다. Full weight19473.615234 + KV80 + GDN62.8125 + dequant2048 + graph2048 + driver1024 + pool1024 + loading1024 + uncertainty1024다. Dequant2048은 최대 vocabulary F32확장1940의 반올림이며 전체 expert pack 동시 확장을 주장하지 않는다. 일부 항은 방어적 allowance로, 측정값이나 하드 상한이 아니다.

Metadata 종료 때 free36,671,741,952B로는20.5GiB disk floor가 부족했다. 이후 root의 별도 exact own inactive Gemma12 weight 정리가6,975,879,296B를 회수했고 free43,039,641,600B를 기록했다. 최종3-file manifest20,420,045,894B를 뺀 조건부 잔량은22,619,595,706B로 floor보다607,888,314B 많다. 이는 다운로드 완료나 현재 공간 보장이 아니므로 직전 fresh disk/GPU 확인과 감시가 필요하다. Metadata 원본의 과거 disk 부족 기록은 수정하지 않는다. 새 actual header와 source/build/config 조건, own startup/resource 근거가 필요하며 다른 GPU·자동 offload·작은 cap으로 우회하지 않는다.

사전조건과 clean commit/push/freeze 뒤에만 최초 노출120×1+warmup5를 별도 실행한다. Schema120/120, semantic≥114/120, rawFP0/58, unsafe0/120, raw observation/unknown 분모를 유지한다. 명백한 FAIL이면 같은 후보 반복·V2·미사용80 접근은0이다. PASS 뒤 후속 최소 검증은 따로 결정한다. Gold의 AUTO-GENERATED / NOT HUMAN VERIFIED 한계와 기존 V2 노출 상태는 변하지 않는다.

[Metadata 준비 보고서](reports/phase5x_qwen36_preparation_report.md)와 [재현 아카이브](../evaluations/results/phase5x/qwen36-metadata/README.md)에 원본·크기·SHA·독립 소스 검토를 보존했다. 모델 미채택, Phase5.x 미완료, Phase6 미시작이며 RTX 실행도 검증하지 않았다.
