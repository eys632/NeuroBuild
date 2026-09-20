# Qwen3.6-35B-A3B metadata 사전 준비

지정된 공식 원본/GGUF revision의 공개 metadata **13개,13,530,452B**를 보존하고 소스·조건부 자원을 검토했다. **Weight 다운로드·actual header·새 CPU 계약·GPU runtime·품질은 모두 대기**다. 이 보고서는 metadata 준비 범위이며 별도 production profile 구현이나 회귀 실행 결과를 포함하지 않는다. [후보 계획](../qwen36_candidate.md).

## 원본과 재현 정보

원본 `Qwen/Qwen3.6-35B-A3B@995ad96eacd98c81ed38be0c5b274b04031597b0`와 GGUF `ggml-org/Qwen3.6-35B-A3B-GGUF@baec3ebee244827cda0f4557eafa8b28f7545fa6`의 pinned API, cards, 원본 LICENSE/config/index/generation/tokenizer metadata와 template, GGUF `.src_sha`/convert.log를 수집했다. 파일마다 크기와 Git blob 또는 LFS SHA를 검증했고 개별64MiB/총128MiB 제한을 지켰다. 첫 tokenizer CDN DNS 실패는0B 수신으로 ledger에 남겼고 공식 pinned URL의 `?download=true` 요청으로 완료했다. 인증·설치·weight/range 요청은 없었다.

선택한 Q4_K_M의 API상20,419,565,568B/SHA `671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7`를 manifest에 고정했다. 이 값은 실제 payload 검증 결과가 아니다. `.src_sha`의 PRIMARY는 pinned 원본과 일치하며 quantizer의 공개 short commit은 `b15ca93`이다. 로컬 f072 build와 동일성을 주장하지 않는다. 공개 로그의733개 tensor shape/type 합은20,408,576,512B이며 나머지10,989,056B의 실제 metadata/alignment도 header 단계에서 확인해야 한다.

[재현 아카이브](../../evaluations/results/phase5x/qwen36-metadata/README.md)는 작은 원본·분석·독립 검토의 exact copies와 source→archive integrity를 보존한다. Tokenizer 본문12,807,982B는 Git 아카이브에서 제외했다. 원본 경로 `var/research/qwen36-candidate-metadata/upstream/tokenizer.json`, SHA `5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42`, pinned URL/크기는 보존한다. 원래 local integrity는 이 제외 파일까지 포함하므로 archive 자체의 integrity와 구분한다.

## 독립 검토와 한계

Base BPE/NFC metadata가 Qwen3.8과 같아도 added tokens26/33과 template 차이가 남는다. 현 단일 system/user/nonthinking 경로의 정적 동등성 검토는 actual native render/tokenizer PASS가 아니다. 기존 공식 reference의 NFC 한계도 지우지 않는다. 새 presence1.5 request는 기존 중립 profile과 다르므로 sampling 검증을 그대로 승계하지 않는다. 완료 public30/parity20/oldcontext200을 반복하는 wrapper는 사용하지 않는다. 향후 필요한 context 검사는 승인된 exposed120 범위만 대상으로 하며, 이번에는 corpus를 읽지 않았다.

독립 source 검토의 whole-VRAM 합27,808.427734MiB를27,904MiB로 올림했고 운영 계획28,672MiB를 제안한다. Driver/pool/graph/loading 여유는 방어적 추정이며 실제 상한 증명이 아니다. GDN snapshot0, 별도 MTP 없음,733개 예상 tensor/shape/dtype, source/build/backend/launch 조건이 달라지면 재검토한다. Metadata 종료 시점 free36,671,741,952B만으로는 새 weight 후20.5GiB reserve를 유지할 수 없었다. 원본 기록은 그 시점 그대로 보존한다.

최종 [runtime manifest](../../runtime/models/qwen36-35b-a3b-q4-k-m.json)는 raw draft에서 `.src_sha` 한 항목만 제외한3-file projection이며 SHA `70d4c0f73f763e10d17b0bad75acda2079dff6d49a9e2ed25575a86cff62b76c`다. 영숫자로 시작하는 파일명만 허용하는 generic downloader는 그대로 두었다. 원래4-file draft SHA `8a76837977b190b6e516fe7ed9cbf877f8890a086685b222c4bf7c1f790938cd`와 `.src_sha` 원본은 불변이며 [projection receipt](../../evaluations/results/phase5x/qwen36-metadata/manifest_projection.json)에 대응을 보존했다.

Metadata 수집 이후 root가 별도로 완료한 inactive Gemma12 한 파일 정리는6,975,879,296B 회수/free43,039,641,600B를 기록했다. 원본 cleanup receipt SHA는 `1509a5bb62e42655f14802e8d36ee1132b615114e8e1fd39df159a0ff0edb01a`, 종료시각은2026-09-20T16:30:03.380473Z다. 최종 manifest 전체20,420,045,894B를 받으면 단순 잔량22,619,595,706B/floor 여유607,888,314B이며 실제 다운로드 전 다시 확인해야 한다. Cleanup·회귀·후속 다운로드 증거는 root의 별도 보존 범위로, 이 metadata 아카이브에서 수행했다고 주장하지 않는다.

Metadata 담당 작업에서는 설치/compile/native/encode/render/tests/평가·replay/모델·GPU 호출, weight 다운로드·삭제, heldout 접근과 gold 변경이0이다. Runtime 또는 품질 PASS를 새로 주장하지 않는다.
