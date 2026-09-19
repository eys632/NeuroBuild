# Phase5.x — Requirement Quality Hardening

IN PROGRESS. Phase5remote d6e39c8 gate후진행한다. 120 synthetic examples를40development/80heldout로고정하고gold는AUTO-GENERATED / NOT HUMAN VERIFIED로표시한다. 첫development전에v3/modelrevision/contract를freeze했고,새prompt는각실험전별도로version/hash고정한다. 공개seed20은development에만둔다. source의조건/부정/targetexclusion/숫자/장문/미지원subset을검증하며결과를본뒤gold를조용히수정하지않는다.

기존criticalFP(비실행gold→READY)와지원gold의잘못된target/axis이동을분리해보고한다. Dataset/prompt최적화의영향과동일case3회의상관을명시하고사람검수표를별도로제공한다. GPU3만현재guard예산으로사용하며listenercheck/원격checkpoint와선행236regression을유지한다.

## 평가 전 검증과 재현

Freeze checkpoint `931c6258f0f9471fdac9ff1ee3b29cbb23308e2d`는push와remotehash를확인했다. [freeze](../../evaluations/hardening_v1_freeze.json)는모델호출전에dataset/prompt/schema/client/parser/scorer/weightmanifest를고정한다. 기존seed20+새100개로구성된120개는두AI검토자와참조출력schema/parser/scorer검증을통과했으나human검수가아니다. Wholebackend236PASS/skip0,independent수치경계악성19거절/정상4controls와listener15tests도PASS다.

Unicode분수·곱셈·특수공백·구분자·수치modifier및축부호잘림을발견했고,개별기호보강반복후접근을재검토했다. 최종검사는원문의동일evidence위치에서숫자/축의전체token을함께비교하고Unicode숫자·공백·문장부호·기호·결합기호·control인접영역을검사한다. 유한한구분자만허용하며지원표현을암묵정규화하지않는다. 이는숫자/축lexical검증이며조건/부정/대상의자연어의미를입증하지않는다.

초기서버를자기guard만정상종료해GPU3baselineused3965/free36373MiB/util0%복귀후freshpreflight로재기동했다. 새서버도actualTCP5개모두127.0.0.1이며원격/public노출없도록확인했다(onePIDsnapshot한계). 관측로그는정확한perprocesspeak보장이아니다. Development v3/v4의실제실패결과는아래에보존한다.

## Development v3 — gate 미충족

고정40개×3: schema120/120, parser111/120, 의미108/120(90%), rawREADY FP3/60, acceptedFP0/60, 지원gold잘못된수용이동0/60, 전체unsafeaccepted0/120, FN9/60. Mean3.3225s/p954.6700s. 실패4case는매회동일하다. HD-B01은부호가없는X축1m을양수로추측했다(Backend거절). HD-D02는한가구의XY두성분을복수대상으로오인해UNSUPPORTED했다. HD-F01/F02는올바른대상범위와물리적SI값을보존했지만,모델이16cm를-.16m로선변환하여원문literal보존계약을위반했고Backend가거절했다. 산술결과나이동값자체가틀린것으로집계하지않는다.

기존seed20은60/60을유지했고새development20은48/60이므로작은seed성공을일반화하지않는다. [결과](../../evaluations/results/phase5x/development-v3/results.json)·동결manifest·VRAMsnapshot을보존했다. Holdout80은아직호출하지않았다. Promptv3/gold/parser를변경하지않고새v4의일반규칙/독립예제로development오류개선을시도했으나아래와같이실패했다. 같은오류가반복되면단순prompt추가를계속하지않고evidence-only추출등계약을재검토하며기존parser를완화하지않는다.


## 2026-09-20 — Development v4 실패와 전략 재검토

Run20260919T211340Z-cebc5bbdaeea46b188caf6d27c4ff804: schema/parser120/120, semantic96/120(80%), raw/acceptedFP0/60, unsafeaccepted0/120, FN24/60, mean2.96099s/p955.05258s. 8case×3 모두불필요한거절: A01/A02/H01/HD-A02/B02/C02/H02는명시된방향이나미요청축을추가질문했고HD-D02는단일가구XY를미지원으로오인했다. 원문unit복사는개선됐지만전체gateFAIL. 결과/manifest/resources를development-v4에보존하며heldout은미호출이다.

긴예제prompt보강반복을재검토하여V5는847token English policy로전환,한축/두축지원과미요청축null을명시한다. 같은T0/runtime/model/schema/parser/gold로40development×1진단을먼저실행한다. 이는최종3회gate가아니며,개선시동일설정정식평가가필요하다. Qwen공식decoding지침은별도로검토하며무조건T0가원인이라고단정하지않는다.


## V5 간결한 영어 prompt 진단 실패

Run20260919T212748Z-bba084e02f46432aab7f11883d625467, development40×1/warmup5: schema40/40, parser16/40, semantic13/40, rawFP5/20, acceptedFP0/20, unsafeaccepted0/40, FN19/20. Mean4.18646s/p955.94240s. 지원gold20개는모두rawREADY였으나19개는숫자원문표기변경(1→1.00),단위선변환,미요청축의0/fake-null삽입등으로거절됐다. 단순길이축소/영어화는품질개선으로이어지지않았다. 이진단을3회반복gate로표시하지않으며모든실패결과를보존한다.

다음실험은기존development최고성능v3prompt를고정하고공식Qwen AWQ nonthinking sampling profile만변경한다(T.7/top_p.8/top_k20/min_p0/presence1.5/frequency0/repetition1/seed42). Legacy기본요청은그대로유지하며실제요청값을manifest에기록한다. Gold/parser/지원범위는유지하고heldout은계속미호출이다. 설정구현동안자기모델guard만정상종료했으며GPU3used3965/free36373MiB/util0%복귀를확인했다.


## V3 공식 non-thinking sampling 진단

Run20260919T213630Z-f42a9eb2a41d4368942b0575dda2893d:40×1,warmup5. Schema40/parser37/semantic36(90%),rawFP1/20,acceptedunsafe0/40,FN3/20,mean3.19669s/p954.46478s. V3/T0와같은4case오류(HD-B01방향추정,D02단일가구XY복수오인,F01/F02모델단위선변환)가남아gateFAIL. 공식권고만으로품질이해결된다는가정은성립하지않았으며기존실패를보존했다.

다음실험은짧은policy와명시적thinking/deepseek_r1/V0/xgrammar의문서화된경로를검증한다. Reasoning은일시메모리만경유하고finalJSON만평가/보존한다. Context4096/전체출력2048/timeout120을미리검증하고기존parser/gold/승인계약은변경하지않는다. v3는긴입력으로동일출력2048이4096을초과하므로그대로사용하지않는다.


## V6 짧은영어policy+thinking 진단 실패

Run20260919T214743Z-27a340f0e04343be8be10a062a6eb25d:40×1,warmup5. Schema40/parser20/semantic17,rawFP4/20,unsafeaccepted2/40,FN17/20,mean13.23336s/p9520.61753s. 전체stop종료이며truncation/timeout없음,completion243–971(mean462.275). 숫자원문표기변경(1→1.00)과target손실,외부조건판단오류가남았다. Acceptedunsafe2는F01대상span에조사추가와HD-I02충돌조건무시이며같은심각도라고단정하지않지만고정exacttarget/criticalgate에서둘다실패다. 실제IFC실행이나승인은수행하지않았다.

추론모드자체가계약준수를보장하지않는다. 짧은영어policy는nonthinking/thinking모두실패했으며가장좋았던한국어v3지시/예제는유지한비교가필요하다. v7은v3출력형식문장하나만internalthinking/finalJSON구분으로명확히하고같은thinkingserver에서명시출력1280으로비교한다. Context4096CPU검증후40개진단하며gold/parser/게이트는유지한다.


## V7 한국어정책복원+thinking 진단 실패 / 모델후보재검토

Run20260919T220158Z-72efdc2dad274cb98b1d61b669597b75:40×1,warmup5,allstop. Schema40/parser35/semantic30(75%),rawFP0/20,unsafeaccepted0/40,FN8/20,mean14.55889s/p9528.66420s. HD-B01방향누락과HD-D02단일가구XY분류는개선됐으나5개수치lexical거절,3개불필요외부조건확인,2개조회분류오류가남았다. Thinking자체는최고nonthinkingv3의90%를넘지못했고고정gateFAIL이다. 결과/manifest/resource를보존하고자기모델guard만정상종료했다.

프롬프트·샘플링·추론모드반복실패후instruction전용post-trainingcheckpoint로모델선정을재검토한다. Qwen3-4B-Instruct-2507공식cdbee75f17c01a7cc42f958dc650907174af0554/Apache2.0/BF16은공식최소버전및로컬소스검토상기존runtime에서시험근거가있다. 크기만으로채택하지않고동일dev40자료/기존최고v3prompt/고정schema-parser-gold로순차평가한다. Fullpeak16384MiB추정+freshmargin,각파일다운로드와20GiB디스크reserve를확인한다. BF16비교sampling은.7/.8/K20/min0/presence0/frequency0/repetition1/seed42로명시하고AWQpenalty를자동재사용하지않는다. 실제quality/startup은아직미검증이다.


## 4B Instruct v3 진단 — 개선됐으나 gate 미충족

Run20260919T222220Z-6df72f2113474c108c488c98faefca20:40×1,warmup5. Schema40/parser39/semantic37(92.5%),rawFP1/20,unsafeaccepted2/40,FN0/20,mean2.81185s/p953.73833s. HD-B01은명시방향없이READY라Backend거절,HD-F01/F02는16cm원문단위를올바르게복사했으나target와instruction에서연구실scope/제외대상을잘라냈다. 모든지원gold가READY로수용되었다는것이대상보존성공을뜻하지않는다. 기존14B에서실패했던동일가구XY와단위변환은개선됐으나고정gate는FAIL이다.

다음은이미고정된v4prompt를동일4B/runtime/neutral sampling/dev40×1에적용한다. 14B에서v4가과잉거절했던결과는보존하며새instructioncheckpoint에서도같을지실제로비교한다. 새prompt/gold/검증기준수정이나heldout호출은하지않는다.


## 4B Instruct v4 diagnostic failure

Run20260919T223253Z-6038073ec36044adb6251920c5d6b285, development40×1/warmup5: schema/parser40, semantic34/40(85%), rawFP1/20, acceptedFP1/20, wrongacceptedtarget2/20, unsafeaccepted3/40, FN3/20. Mean2.35471s/p953.56743s. HD-B01 unsigned direction is fixed, but E01 preservation clauses and HD-F02 exclusion cause incorrect UNSUPPORTED, HD-A02 explicit negative direction causes CLARIFICATION, F02/HD-F01 lose target scope, and HD-I02 ignores an unverified collision condition. All responses completed without transport/parser errors. This does not pass the fixed gate; all outputs/resources are retained.

V4 replaced many instructions and examples simultaneously and regressed relative to 4B/v3. The next bounded experiment will retain v3 in full and clarify only direction/extraction reminders after examples, using general rules and unrelated sample nouns/numbers. No gold/parser/schema/scoring change or heldout inference. This is a development-driven prompt revision, not blind selection.


## 4B v8 failure and decoding reassessment

Run20260919T223831Z-af6ebcd137394488a0adc427bd63edcf: development40×1/warmup5, schema40/parser39/semantic36(90%), rawFP1/20, unsafeaccepted2/40, FN1/20, mean2.57006s/p953.45012s. HD-B01 still guesses unsigned direction and is blocked; HD-D02 regresses to multiple-furniture refusal; HD-F01/02 retain wrong short targets despite full instructions. All failures retained. V8 is not selected and heldout remains uncalled.

Three 4B prompt variants did not satisfy the unchanged gate. Stop expanding prompts. Compare the best existing v3 using existing legacy_greedy (temperature0/seed42) versus prior neutral sampling, all40 cases once. Other legacy sampling fields are omitted and inherit pinned server/model defaults; this is not an all-parameters-controlled ablation. Non-thinking greedy is an experiment, not an official quality guarantee. No source changes or validation weakening. If it fails, reconsider model/representation rather than repeat reminders.


## 4B v3 greedy control failure and model reassessment

Run20260919T224246Z-64a5648ea1b546c78b1f961bf3b6c094: schema40/parser38/semantic36(90%), rawFP1/20, unsafeaccepted2/40, FN1/20, mean2.57311s/p953.40377s. I01 changes750mm to-.75m and is rejected; HD-B01 guesses unsigned direction and is rejected; HD-F01/02 still drop location/exclusion in both target and instruction. Summary replay matches all recorded metrics. Changing decoding does not meet the gate. No holdout calls or IFC execution.

Stop 4B prompt/decoding trials and reassess a distinct instruction MoE checkpoint. Own 4B guard was verified by UID, cmdline and starttime before SIGTERM; child exited normally and rendezvous was cleaned. An initial attempt to use os.pidfd_open stopped without signalling because this Python build lacks that API; the existing verified-own-guard procedure completed shutdown. Other processes were untouched. Candidate metadata/static reviews and new GPU3 preflight are required before any new launch.


## MoE v3 diagnostic failure

Run20260919T231243Z-194bbb3212944ebcb8e0e54bfa1b28b5, development40×1/warmup5: schema40/parser36/semantic34(85%), rawFP1/20, unsafeaccepted1/40, FN4/20; mean4.24096s/p956.07952s. F02 changes a source character, I02 fails source grounding, HD-A02 loses the negative sign, HD-B01 guesses unsigned direction, HD-D02 misclassifies one furniture's XY as multiple furniture, HD-F02 loses the scope/excluded target. Startup success does not satisfy semantic gate. Full results/resource/manifest preserved.

Next: reuse existing v4 with identical checkpoint/runtime/neutral sampling, all40 development once. If copying/interpretation failure persists, revisit the redundant generation representation rather than download more models or weaken gold/parser/gates. Existing1.0 parser/domain remains frozen throughout this comparison. Holdout still uncalled.


## MoE existing v4 control and generation representation review

Run `20260919T232550Z-fb632f6b5f1d405f9618dfe892b0f42a`, same checkpoint/runtime/neutral sampling, development40×1: schema40/parser37/semantic34, rawFP1/20, unsafe accepted2/40, FN2/20, mean3.995633s/p955.909745s. A01/F02 alter 책상 to 책장 in instruction and fail grounding. H02 lookup is misclassified UNSUPPORTED. HD-F01/F02 preserve full instructions but shorten target to the positive noun, losing scope/exclusion and passing the lexical parser; these remain unsafe errors. HD-I02 ignores an unverified collision condition, outputs READY and also corrupts target characters; parser rejection does not erase raw FP. Full failure outputs and resource snapshot are preserved. No holdout calls.

Twelve completed expanded comparisons have not met the gate. Next is a versioned generation2 wire contract that asks the model for classification and exact quotations only; code derives original lexical number/unit/sign and projects through unchanged canonical1.0 parser. This targets duplicated value/unit generation, does not solve semantic scope/conditions by itself, and does not authorize repair, gold changes or weaker scoring. Separate schema/adapter/client/harness tests and pre-inference freeze are required.

Generation2 backend/transport/evaluation regression:290PASS/skip0/17.329s with real private PostgreSQL and IfcOpenShell, no DISPLAY. Legacy schema/parser unchanged; history replay640trials exact. This proves implementation boundaries, not model quality. The next evaluation uses the existing MoE launch, same neutral sampling/output768/context4096, all40development×1 after prompt/schema/adapter/client/evaluator hash freeze and independent CPU grammar/context checks.

Cross-server review: generation2 adapter/strict parser runs only in the common Backend and adds no GPU dependency or hardware branch. Explicit generation schema is independent of legacy/modern HTTP dialect. A100 xgrammar0.1.18 CPU grammar and source boundaries are verified; RTX runtime and actual same-checkpoint inference remain PREDICTED_UNVERIFIED.


## Generation2 first actual diagnostic — FAIL

Run `20260919T233958Z-5e2143732d36479ab880ab2fc32dfbb3` after pushed91b464e, development40×1/warmup5. Generation schema40/40, adapter/canonical schema/parser29/40, semantic29/40; rawFP1/20, unsafe0/40, FN0/20. Mean4.132092s/p955.313616s. All20 READY gold cases preserve exact target scope/current instruction/axis SI and pass. Ten otherwise correctly classified non-READY responses retain prohibited instruction/evidence fields and are rejected as INVALID_MODEL_OUTPUT; they remain full-denominator failures. HD-B01 still guesses readiness with unsigned X1m and fails grounding, preserving rawFP1. No output repair or retrospective score change.

This mixed result motivates a narrower generation-constraint correction: preserve7-field2.0 adapter/canonical1.0, add a separately versioned schema with explicit READY vs non-READY branches, decision before quotations, null constraints at generation, and a prompt version with one independent unsigned-direction clarification example for the already-existing rule. Schema/property order/example changes are one documented configuration experiment, not an isolated causal claim. Existing files and failed results remain immutable; all gates and holdout procedure remain unchanged.


## Generation2 decision branches/v2 — first diagnostic PASS

Run `20260919T235318Z-504ae53e55864b4fba35c6bb108c8c05`, frozen and pushed29a6c77 before requests: development40×1 plus5warmups. JSON/generation schema/adapter/canonical schema/parser/semantic all40/40. RawFP0/20,unsafe0/40,FN0/20; mean3.899002s/p955.125593s. No transport/truncation errors. This is the first successful expanded diagnostic; all13 earlier failures remain preserved. Schema/order/example changed together, so improvement is not attributed to a single factor.

Next: freeze identical model/revision/runtime/prompt/schema/adapter/parser/client/scorer/sampling/output/timeout and run development40×3/warmup5. No source changes or tuning from heldout results. First heldout warmup remains prohibited until formal development passes, independent review and new candidate checkpoint are pushed. Diagnostic success is not the Phase5.x gate or human verification.
