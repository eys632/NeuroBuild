# Phase5.x thinking transport 검토

2026-09-20 KST. 고정 구현 checkpoint `af2e0e201becce9483007d7ff122acac2cc7883b` push/remote 일치를 확인했다. Root가 별도 agent의 client/launcher/v6를 검토했고, Architecture agent가 root의 harness와 runtime/v6를 추가 독립 검토해 PASS했다. 실제 모델 품질은 이 검토와 별개다.

Client는 세 번째 고정 sampling recipe와 읽기 전용 enable_thinking만 추가한다. 서버 parser 이름을 common client에 고정하지 않는다. A100 launcher는 기존 V0/uni/FileStore/loopback/TP1/context4096/예산 guard를 유지하며 명시 true에서만 enable-reasoning/deepseek_r1을 추가한다. 기본 false 명령은 이전 argv와 동일하다. 기본 production 설정은 아직v3/nonthinking이며 experiment는별도alias neurobuild-thinking을 사용한다.

Evaluation runtime metadata는 enable_reasoning/reasoning_parser를 함께 받는다. 역사적인 두 필드 부재는 false/None으로 해석하며 thinking 실행 허가가 아니다. bool/parser를 검사하고 vLLM0.8.5에서는 deepseek_r1만 허용한다. client 요청 모드와 선언 runtime 모드가 다르면 첫HTTP전에실패한다. Manifest에는실제sampling8값·모드·parser·전체output2048·timeout120·prompt/launch hash를 기록한다. 이는 launcher/운영자가 제공한 metadata 일치 검사이며 endpoint가 loaded configuration을 원격 attestation한다는 주장은 아니다.

Client28 / client+harness42 / 전체251 tests PASS, skip0, 실제PG/IFC및DISPLAYunset16.683s. FakeHTTP는reasoning_content sentinel이Completion/stdout/stderr에나오지않고final만남는지, length/no-final/thinktag/bodylimit 실패와no-retry를검증한다. Reasoning과final합산한도가2048이며출력을조용히잘라수용하지않는다. 사용량은서버가주는숫자만기록한다.

실제thinkingserver도freshGPU3preflight통과,health약23.023s(별도probe시작기준/정확coldstartup아님),ownPID의TCP5listeners모두loopback을확인했다. 이실험의startup정보는evaluations/results/phase5x/thinking-v1-launch에보존했다. RTX5090의modernparser/lifecycle은여전히PREDICTED_UNVERIFIED이고A100실측으로대체하지않는다.
