# EXAONE header·공개 template 사전 검증

2026-09-20. **Strict header와 공개 template/grammar CPU 검증 PASS. 실제 vocab/context/GPU/품질은 미검증.**
Phase5.x 미완료·후보 미채택·Phase6 미시작이며 기존 Qwen/Gemma 실패를 보존한다.

## 원본 artifact와 header

공식 Q4_K_M weight20,047,839,424B/SHA5ba3839b67dcee5618ea7b2206cedc8f9e2ec90fbcec3c95a8cc8b33967f6baf와
LICENSE/README 다운로드3파일을 검증했다. 자체 download child exit0/reaped,
GPU/native inference0. Guard receiptSHA b2ac226eb068a2d788564f37304ccebc742f1d54aee058b3987389b3817f048c.
20.5GiB disk reserve를 유지했고 가중치·환경·native binary는 Git에서 제외한다.

첫 header auditor는 main64개 SWA패턴을 예상해 CONFIG_METADATA_MISMATCH였다.
Bounded6,587,328B 진단에서 실제 패턴은 main64+MTP True1의65개이며 나머지723개 tensor
이름·shape·역할dtype/tokenizer wire/template는 일치했다. 고정 로더는 main64층만 실행하고 MTP는 SKIP한다.
현재 upstream config의 layer_types64와 publisher가 넣은65개의 정확한 변환 revision은 미공개다.
이 차이를 숨기지 않고 원본 helper/실패/진단을 남겼다. v2는 정확히 끝 True1개만 요구한다.

V2 합성20개 검증 뒤 실제 strict header+전체SHA PASS,
reportSHA **fb5260c6e1e3356741f7728e4077f771763ea39affd77e8ac9772e417aa70c12**.
F32 265/Q4_K391/Q6_K67, tensor723, untied output/embedding과 원래 공식template5930B를 확인했다.
수치tensor decode나 inference 검증은 아니다. 보수적65층KV1040MiB/최대F32행렬3000MiB/
전체28672MiB 계획을 유지하며 실제 peak나 RTX fit을 주장하지 않는다.

## 시스템 정책 누락과 동등한 분기 표현

공개 production fake request는 system8974B/user121B다. 고정 minja가 공식 template의 첫system분기에서
continue를 처리할 때 중첩 if의 누적출력을 버려 nativeprompt177B에서 시스템 정책이 빠졌다.
실제 GPU/품질 평가 전에 발견한 호환성 차단 요인이다. 원래 GGUF/template/native source/binary는 그대로다.

최초 CPU 공개 검사는 synthetic thought whitespace 기대에서 실패했다. 별도 v2는 이 기대를
소스에 맞춰 고쳤지만 system전체동등성 검사가 빠져 부분 grammar PASS를 내었다.
그 receipt를 최종 runtime 적격 증거로 사용하지 않는다. 원래 실패·v2부분PASS·systemloss진단을 모두 보존했다.

별도 [continue-free template](../../runtime/templates/exaone45-continue-free.jinja)는 첫system분기와
다음assistant분기를 if/elif로 연결한다. Message 원문·role순서·policy내용을 변경하지 않는다.
Effective5829B/SHA **7de6c8ba3df6db54564c7a63385cc29572c0a616d5848961e969ecbb8c349851**.
공식embedded5930B/e4ece7…c0e5와 구분하고 명시한 실행variant에서만 override를 선택한다.

V3 공개18개에서 공식 Jinja원본=derived Jinja=derived native 출력이 byte-exact다.
현재 production fake wire의 nativeprompt9176B도 공식reference와 같고 system8974/user121을 그대로 포함한다.
원본native의7/18 불일치와177B 정책소실은 별도 control로 재현했다.
V3 proofSHA **fc7109fe4e9fbbe4a619ad16dc701cda01a4976ec8bd53d726aeb09f34f39408**.
모든 가능한 Jinja입력의 동등성을 증명한 것은 아니며 공개18개와 현재 고정 single-request계약의 증거다.

CPU native eager grammar는 JSON10수락/20거절, protocol4거절을 확인했다.
Plain/fenced JSON을 grammar가 허용하고 native PEG가 원래 JSON payload와 byte동일한 finalcontent를 추출했다(20건).
이는 native response 구성 경계다. Application의 inlinefence거절·no-repair·no-retry는 유지한다.
Synthetic thought의 별도channel분리1건을 확인했으며 실제 모델 reasoning은 생성·보존하지 않았다.
세 버전 모두 새CPP TU만 기존194개 CPU object와 연결했다. GPU backend/context/tensorload/inference0이다.

## Launcher와 회귀

선택적 template path+SHA쌍을 명시하지 않으면 기존argv 그대로다. 지정하면 owned regular/singlelink/
no-symlink/64KiB이하/UTF8/noNUL/hash/runtimeoutput충돌 검증을 GPU조회 전 수행하고 spawn직전에 다시 확인한다.
Guard는 override path/hash를 기록한다. Model/gold/parser/scorer/prompt 또는 GPU선택 정책의 변경은 없다.

Focused nativeguard22개 PASS0.230s, root 전체 **408 tests PASS/skip0/21.330s**.
실제 PostgreSQL/IfcOpenShell과 headless 조건을 포함하고 GPU/모델 호출은 없다.
독립 읽기 검토는 launcher선택/기존경로보존/거절경계와 v3 source·proof binding을 확인했다.
이전403 회귀와 그 최초 test누락 실패도 보존했으며 새launcher변경 때문에 필요한 회귀만 수행했다.

## 남은 gate와 재현

[원본 보관본](../../evaluations/results/phase5x/exaone45-template-header-preflight/README.md),
[override provenance](../../runtime/templates/exaone45-continue-free.provenance.json),
[전체 자원 계획](../exaone45_33b_resource_plan.md), [단회 계획](../exaone45_33b_diagnostic_plan.md).

공식 tokenizer 공개20개 자체의 rawroundtrip은18/20, NFC대조20/20이다.
실제 GGUF vocab/BOS/native token ID/원문 roundtrip/context는 별도 CPU 검사 중이다.
기존 Qwen raw-Unicode variant를 승계하거나 입력을 NFC로 보정하지 않는다.
이후 freshGPU3/새모델공개1·최대context1/단회조건동결·push를 통과해야 첫120×1+5를 시작한다.
명백한 품질 실패 후보 반복·V2·미사용 holdout0, 자동전체3회 반복금지 원칙은 그대로다.
NC 내부 비상업 연구 범위이며 제품채택·상업배포허가나 RTX실측은 아니다.
비필수 최적화는 future optimization이며 이 작업은 실제 정책누락 호환성 문제를 해결한 것이다.
