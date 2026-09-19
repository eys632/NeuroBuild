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
