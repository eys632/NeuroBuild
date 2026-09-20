# NeuroBuild_v2 결정 기록

갱신: 2026-09-19 KST. 사용자 지침과 공유 가능한 기술적 근거만 기록한다. chain-of-thought, secret, private key는 저장하지 않는다. 아래는 현재 선택이며 구현 완료 선언이 아니다.

| ID / 주제 | 결정과 이유 | 검토한 대안 / 선택하지 않은 이유 | 재검토 조건 |
| --- | --- | --- | --- |
| D001 자율 실행 | 최신 사용자 지침에 따라 Phase 11 Internal Technical MVP까지 단계별 승인 없이 진행. 각 Phase gate와 commit/push는 필수 | 과거 Phase마다 승인 대기 방식은 사용자가 명시적으로 대체함 | 새로운 사용자 지침, hard blocker, Phase 11 완료 |
| D002 checkpoint 선행 | Phase 0 foundation local commit을 보존하고 GitHub push를 해결한 뒤 Phase 1 설치/구현 시작. 현재 상태 문서 외부화는 복구 정보 보존 작업 | 인증 실패를 무시하고 수시간 로컬 구현 누적은 중앙 source-of-truth 및 사용자 checkpoint 요구 위반 | remote push와 원격 commit 확인 후 완료 처리 |
| D003 공통 코드 | 단일 `v2`, common Application와 profile 기반 GPU/network/resource 설정 | 서버별 backend 복제/장기 branch는 동일 commit의 기능 일치와 유지보수를 깨뜨림 | 공통 source 원칙을 변경하는 사용자 결정이 있을 때만 |
| D004 최초 capability | IFC4 single IfcFurniture, 동일 Storey 상대 XY, **canonical internal unit=metre**, Z/rotation/scale/floor 유지, GlobalId 보존, 미지원 placement 거절 | 다양한 object/geometry operation으로 즉시 확대하면 검증 범위가 늘고 첫 slice를 벗어남 | 첫 slice 검증 이후 별도 승인된 product scope 확장 |
| D005 결정론적 실행 | LLM은 semantic requirement/target description/제안만 생성. 단위 변환/산술은 코드, 실제 수정은 BIM Tool이 수행 | LLM이 GlobalId/IFC/geometry/단위 계산을 확정하는 방식은 재현성과 안전한 검증 경계를 흐림 | 모델 역할을 넓힐 실증적 근거와 별도 architecture 검토 |
| D006 review 분리 | Target Confirmation과 Proposal Approval을 별도 저장·검증. Approval은 구체적 proposal/base/content에 결합 | 대상 확인을 변경 승인으로 간주하면 잘못된 자동 Apply 가능 | 사용자 지침을 위배하는 통합은 현재 고려하지 않음 |
| D007 revision/storage | PostgreSQL metadata/state + local immutable full IFC artifact. finalize 후 DB commit, head CAS, idempotency/recovery | DB BLOB, 기존 파일 overwrite, DB/FS atomicity 가정은 사용자 요구와 crash 복구에 부적합 | Phase 2 failure/concurrency 테스트, 향후 storage adapter 필요 |
| D008 초기 durable worker | PostgreSQL Job Queue + **single workflow worker + session advisory lock**. human wait 중 Worker를 반환하고 내구 상태에서 재개 | Redis/Celery/Temporal 도입이나 다중 active worker는 현재 필요가 증명되지 않음 | Phase 7의 실제 처리량/복구 요구를 단일 worker로 만족할 수 없는 증거 |
| D009 runtime 환경 | Backend `.conda`/Python 3.12, model `.conda-vllm`/검증한 runtime Python. GPU packages는 Backend와 분리 | base/시스템 Python/`pip --user` 설치는 전역 정책 위반; 중복 test env는 기본 해법 아님 | 공식 요구 버전 및 실제 wheel/driver 호환성 검증 |
| D010 model 평가 | 공식 shortlist부터 순차 A100 GPU3 benchmark. final model은 아직 없음. 전체 pipeline의 의미/critical error와 운영 metric으로 선택 | 과거 Qwen3-4B 고정, 일반 benchmark만으로 선정, 모든 weight 동시 다운로드는 요구에 맞지 않음 | 재현 가능한 local 평가 결과 및 license/32GB 예측 검토 |
| D011 ground truth | 기존 synthetic seed와 새 자동 생성 gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**. 내부 개발은 계속하되 human 검수 자료를 분리 | 생성 gold를 사람 검증 정답 또는 외부 Pilot readiness로 표시하면 증거를 과장함 | 실제 사용자/전문가 검수 기록이 생긴 개별 dataset version |
| D012 GPU/RTX 증거 | A100 physical3 / RTX physical1, TP1, 타 GPU fallback 금지. RTX는 predicted/unverified | A100 성공을 RTX 성공으로 확장하거나 타 GPU를 쓰는 대안은 사용자 정책 위반 | RTX 재접속 시 동일 commit의 별도 compatibility validation |
| D013 내부 배포 | localhost/internal 중심 headless API/browser viewer. URL은 runtime 설정이며 public exposure는 자동 진행 범위 밖 | public internet production/pilot은 이번 Internal MVP 목표 밖이며 hard blocker 대상 | 사용자 public exposure 또는 외부 Pilot 결정 |
| D014 Git identity/auth | 사용자 제공 `eys632 <eys632@gmail.com>`을 repository-local로 설정. commit `29d4774` 생성. HTTPS 실패 후 기존 SSH 인증을 read-only 확인 | author 추측, 전역 identity 변경, token/private key 출력, SSH host checking 완화, 임의 key 생성은 필요하지 않음 | 사용자가 안전하게 GitHub 쓰기 인증을 구성한 뒤 push 재시도 |

## 구현 시 지켜야 할 구체적인 해석

Session advisory lock은 PostgreSQL **session**의 소유다. Phase 7에서 전용 연결 수명과 Worker 수명을 맞추고, transaction 종료만으로 유지 여부를 추측하지 않는다. 연결/lock 상실 시 새 job 처리를 중단하며 진행 중 Apply는 DB의 execution/head 검증으로 보호해야 한다. single-worker lock이 stale proposal, duplicate job delivery, artifact recovery 검증을 대신하지 않는다.

내부 단위 metre는 확정되었지만 XY 좌표계와 허용 Placement의 구체 범위는 Phase 1/3에서 단순하고 검증 가능한 계약으로 정한다. 자연어의 누락·모호한 방향을 편의상 양의 방향으로 추측하지 않는다. 수치/단위 원문을 추출한 다음 단위 변환을 결정론적 코드가 수행하도록 모델 평가와 production pipeline을 연결한다.

Gate 실패와 hard blocker는 다르다. 구현/test 오류는 같은 Phase에서 자율 수정한다. 필수 runtime benchmark를 수행하지 못한 상태를 mock 결과로 통과시키거나 인증 없는 push를 완료로 기록하지 않는다. 같은 실패 3회 이상이면 같은 조치를 반복하지 않고 접근을 재검토한다.

Phase 0 당시 commit에 포함된 Phase 승인 대기와 Phase 10 이후 계획은 최신 사용자 지침으로 대체되었다. 현재 문서도 자율 실행 방향으로 갱신하며 실행 권한/완료 범위는 [MASTER_PLAN.md](MASTER_PLAN.md)와 최신 사용자 지침을 따른다. 기술 불변 조건은 계속 유지한다.

## D015 — Phase1 Backend bootstrap (2026-09-20)

- GitHub SSH push 및 remote/current HEAD f131644 일치로 Phase0 remote gate를 충족했다. 사용자 변경 commit ID 및 noreply identity를 보존한다.
- Backend는 project `.conda` Python3.12.14. Miniconda 공식 installer SHA256 검증, conda-forge만 지정, base auto_activate=false. 모델 환경은 GPU runtime 요구사항이 확정될 때 만든다.
- Phase1은 stdlib Domain + unittest, package metadata/build에만 이미 환경에 포함된 setuptools84 사용. 테스트용 pytest/agent framework를 추가하지 않는다.
- 환경은 Git 제외하고 resolved Linux64 URL/SHA256 lock를 저장한다. RTX5090의 OS/ABI가 다르면 실제 환경 검증 후 공통 dependency 버전을 유지할 수 있는 lock 전략을 재검토한다.

## D016 — Phase1 좌표/값/승인 계약

- XY는 IFC project engineering/world frame으로 고정한다. 화면 오른쪽이나 객체 local axis는 의미가 확정되지 않으면 clarification한다.
- 값은 finite Decimal로 받으며 coefficient/exponent 이동으로 m/cm/mm를 metre로 변환한다. Python의 ambient Decimal precision을 낮춰도 손실이 없어야 한다.
- frozen records와 proposal fingerprint로 승인 대상을 결합한다. 동일 numeric 표기(1/1.0)는 정규화하고 원래 unit/content 변경은 새 승인을 요구한다.
- Domain pure guard의 결과를 동시성 또는 실제 IFC 존재 검증으로 간주하지 않는다. Phase2 transaction/unique constraints, Phase3 inventory validation을 추가한다.

## D017 — Phase2 persistence 경계

- 서버 PostgreSQL17.11을 project .conda로 제공하고 var/postgres 소유 cluster와 private socket만 사용한다. 시스템 service/sudo/공개 TCP를 요구하지 않는다. 공식 initdb/peer/transaction 근거: https://www.postgresql.org/docs/17/app-initdb.html , https://www.postgresql.org/docs/17/auth-peer.html , https://www.psycopg.org/psycopg3/docs/basic/transactions.html .
- Artifact identity를 durable PREPARED intent로 먼저 예약한다. 검증/file+directory fsync 후 DB head를 publish한다. 실패 orphan은 보존하며 자동 삭제나 rebase를 하지 않는다.
- Phase2 repository의 fingerprint binding은 실제 사용자 승인 검사를 대신하지 않는다. Phase4 Application에서 별도 approval guard와 actual IFC inventory를 결합한다.

## D018 — Phase3 native IFC와 좁은 배치 변경

- IfcOpenShell0.8.5 PyPI wheel의 실제 ABI가 host glibc2.31과 맞지 않아 공식 문서가 안내하는 conda-forge build로 전환했다. 시스템 glibc/driver를 바꾸거나 별도 환경을 추가하지 않았다. Native Conda lock가 필수 IFC dependency의 기준이며 pip metadata와 구분한다.
- IFC4/단일project/SI m·cm·mm/upright3D LocalPlacement/identity WCS로 지원 경계를 명시했다. 부모 XY 회전은 지원하되 tilt/grid/cycle/assembly/map conversion/불명확한 단위는 거절한다. 일부지원객체만 골라 전체파일을 암묵수용하지 않는다.
- 대상의 point/axis/localplacement3개만 새로 만들고 ObjectPlacement ref만 바꾼다. Generic geometry edit API가 재작성할 수 있는 자식/공유entity를 직접 수정하지 않는다. Serialize/reopen 후 전체원래entity와 모든product worldtransform을 재검증한다.

## D019 — Phase4 명시 서비스와 review 수명

- RenovationService가 SemanticRequirement → 실제 inventory → TargetConfirmation → Proposal → 별도 ProposalApproval → Apply를 연결한다. 메서드는 workflow ID를 받고 내부의 frozen authoritative state를 검증한다. 외부에서 바꾼 snapshot을 approval로 받아들이지 않는다.
- Phase4는 LLM 없는 synthetic service E2E다. Human review는 in-process registry이며 재시작하면 사라진다. Durable review/job queue/session advisory lock은 Phase7에서 구현한다. Revision/artifact/execution intent의 Phase2 내구성은 계속 사용한다.
- Prepare/finalize/commit 실패 후 같은 execution ID로 안전하게 재시도한다. PREPARED orphan의 예상 bytes/hash는 deterministic IFC Engine에서 다시 얻고 기존 파일을 검증한다. COMMITTED 재시도는 정확한 승인·intent binding을 검증한 뒤 기존 결과를 반환한다.

## D020 — Phase5 GPU 실행 중단 (2026-09-20 01:00 KST)

- Phase4 remote dd58b59 완료 후 GPU3만 재확인했다. Phase0부터 예상 밖 process3개/3965MiB 점유가 계속 남아 있으며 본인 소유 PID 목록에는 없다. 타인 신원/파일/명령은 조회하지 않았다.
- AGENTS의 예상 밖 GPU process 실행 중단 규칙을 적용한다. 남은 VRAM 또는 utilization0%를 사용 허가로 간주하지 않는다. 이는 측정된 OOM/메모리부족 주장이 아닌 정책 blocker다.
- GPU3 사용 가능 시 재확인하여 Phase5부터 재개한다. 모델 환경/weight를 선제 설치하거나 이후Phase를 우회 구현하지 않는다. 최종모델/benchmark/RTX는 미검증으로 유지한다.

## D021 — 사용자 변경: GPU3 가용량 기반 공존 실행

2026-09-20 최신 사용자 지침이 D020의 점유 존재만으로 중단하는 규칙을 대체한다. 다른 process를 절대 종료/변경하지 않으며 GPU3만 사용한다. nvidia-smi free VRAM/utilization 반복 측정과 후보 전체 peak+안전 margin으로 실행 가능성을 판단한다. OOM 위험이나 타인 메모리 침범 가능성이 있는 후보는 실행하지 않는다.

초기6회/10초 관측은 free36373MiB/util0%로 안정적이다. 초기예산은 margin=max(6144MiB,free×20%)를 남기며, TP1/context4096/concurrency1/eager를 우선한다. 전체디바이스90% 고정할당을 쓰지 않고 후보별 제한을 계산한다. Runtime은 공식 CUDA11.8 build부터 호환성을 실측하고 modelquality는 실제 평가로 결정한다.

## D022 — Phase5 실측 모델 및 runtime 선택

Qwen3-14B-AWQ pinned31c69ef + promptv3를 내부 개발용으로 선정한다. 20 development cases×3에서 자동의미60/60, READY오판0/33이며 같은prompt의8B-BF16은54/60이다. 실패v1/v2도 보존하고 auto-gold/small correlated seed의 한계를 기록한다. A100은driver535/glibc2.31 호환cu118 vLLM0.8.5/Torch2.6.0 환경, context4096/TP1/eager/seq1/반복VRAMguard를 사용한다. RTX5090은 동일checkpoint의공식SM120근거만검토했고실측은미검증이다.

## D023 — 명시적 structured output protocol과 localhost rendezvous

최신 vLLM은 legacyguidedfields를 무시할 수 있어 공통client에 explicit legacy_guided_json/structured_outputs dialect를 둔다. 실패시 자동전환하거나무제약retry하지않는다. 서버backendxgrammar설정은runtimeprofile의책임이고Backendparser/승인계약은공통이다. A100Torch TCPStore wildcard를 actualsocket검사로발견해FileStore world1와loopbackGloo/NCCL로수정했다. 자기child5listeners모두loopback을확인했다. RTX V1의process구조/loopback/parentdeath는별도검증대상이다.

## D024 — 확대 평가와 모델 재선정 기준

Phase5의 seed20 성공은 Phase5.x의 확대 평가 통과를 대신하지 않는다. Development40과 holdout80을 version/hash로 고정하고, schema100%·semantic95% 이상·raw READY 오판0·잘못 수용한 READY0을 유지한다. Parser가 차단한 raw 오판과 gold READY에서의 대상/축 오류도 각각 보존한다. 정식 평가는 case당3회이며 단회 진단은 후보를 좁히는 용도다.

Holdout의 첫 warmup 이전에 최종 후보 조합을 고정하고 원격 checkpoint를 남긴다. Holdout 출력으로 조정한 뒤에는 같은 자료를 새로운 unseen 성공으로 부르지 않는다. Gold는 자동 생성·사람 미검수이고, AI가 사전 입력/gold 검토에 참여했으며 split이 좁은 문법을 공유한다. 상세 절차는 [사전 검토](reviews/phase5x_holdout_protocol_review.md)를 따른다.

## D025 — 반복 prompt 수정 중단과 instruction checkpoint 비교

14B hybrid AWQ에서 prompt·sampling·thinking 비교가 gate를 충족하지 못했다. 기존 cu118 환경에서 사용할 수 있는 4B-Instruct-2507 BF16을 비교했지만 v3/v4/v8 및 v3 greedy도 통과하지 못했다. 모든 실패를 보존하고 parser/gold를 완화하지 않는다. Prompt 길이·언어·명시 규칙 추가 또는 모델 크기 하나가 원인이라고 단정할 근거는 없다.

다음 비교는 별도 instruction MoE인 제3자 `ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ` 고정 revision이다. [후보 검토](moe_instruction_candidate.md)는 출처·license provenance·설치 runtime 정적 호환성·전체 VRAM 추정·디스크 reserve를 구분한다. 기존 v3/neutral sampling과 동일한 gold/평가기를 사용하며, 실제 적재와 품질을 확인하기 전에는 채택하지 않는다. 단일 source tree, GPU3만 사용, 자신의 이전 서버 종료, fresh preflight와 runtime 감시는 유지한다. RTX 실측은 별도 미검증이다.


## D026 — 별도 quote-only generation 계약, canonical 검증 유지

MoE의 기존 v3/v4 비교도 모두 semantic34/40으로 실패했다. 더 많은 모델 다운로드나 비슷한 prompt 수정을 반복하기 전에 생성 표현을 재검토한다. Generation2는 판단과 원문 target/current instruction/axis evidence만 생성하고, 코드가 evidence의 원래 숫자 철자·단위·명시 부호를 읽는다. 새 adapter는 기존 수치/경계 helper와 변경 없는1.0 parser를 통과시킨다. 모델이 누락한 대상 범위·조건을 코드가 추측해 보충하지 않는다.

Legacy1.0은 기본값과 과거 결과를 보존한다. 계약은 caller가 명시적으로 선택하며 응답 버전으로 자동 전환하지 않는다. 평가기는 adapter보다 먼저 raw READY를 기록하고 원래 model JSON, projection, generation schema, adapter, canonical parser 판정을 구분한다. 같은 gold와 strict semantic/raw FP/unsafe gate를 유지하며 실제 품질 개선 전에는 채택하지 않는다.


## D027 — 첫 holdout 실패 보존과 명시적 두 단계 비교

MoE/2.0branch/v2/greedy의 development120/120은 첫 holdout211/240,rawFP9/114,unsafe12/240으로 일반화되지 않았다. 원본80개와 gold는 그대로 보존하고 이후 비교에서는 노출된 regression 자료로 표시한다. 별도 unused v2 80개는 prompt 작성자와 분리하여 작성·사전검토하며 사람 검수로 간주하지 않는다.

기존14B에 같은 generation2 표현을 적용한 전체120개 진단도113/120,rawFP2/58,unsafe3/120으로 실패했다. 원문 인용은 통과했지만 부정/승인우회 분류와 제외대상 보존이 실패했다. 다음 비교는 전체요청 분류 → 분류로 고정된 schema의 원문 추출이며 동일 canonical parser와 gate를 유지한다. 뒤 단계 거절로 첫 분류의 raw READY 오판을 감추지 않는다. [설계와 사전 계획](requirement_staged_pipeline_design.md)을 따른다. 최종 config 채택/Phase6 진행은 보류한다.


## D028 — 분리 호출 실패 후 공식32B 단일 호출 비교

분리14B 후보가 exposed120에서93/120,raw11/58,unsafe6/120으로 실패했다. 모든 실패와 독립 재생을 보존하고 채택하지 않는다. 기존 단일2.0/branch/promptv2/greedy를 유지하여 공식 Qwen3-32B-AWQ 모델만 바꾸는 제한된 비교를 수행한다. Canonical parser/adapter와 gold/gate는 그대로다. 모델이 더 크다는 이유로 품질을 가정하지 않는다.

공식manifest13파일18.0132GiB, 정적Qwen3/SM80Marlin 호환성, whole peak25GiB와 freshfree의20% 이상 margin을 검토했다. Torch/vLLM fraction.60은 wholecap이 아니며 peak allowance0의 GPU3 전용 guard를 사용한다. 기존4B의 복원 가능한 inactive weight만 검증 후 정리하여 disk20GiB reserve 외 여유를 확보했다. 다운로드 후 CPU/header/grammar와 actual guarded runtime 검증이 필요하다. [후보 계획](dense_32b_candidate.md)을 따른다.

V2는 model-output-unseen이지만 root 입력 노출 이력이 있다. 이 사건 뒤 모델 변경을 명시하며 완전 맹검이라고 부르지 않는다. 현재 단일prompt는 v2 작성 전부터 고정돼 있고 노출 후 source/prompt/gold는 변경하지 않았다.


## D029 — 32B 실패 보존과 한 호출 semantic facts 계약 검토

공식32B/기존single2.0의품질103/120/rawFP1/58/unsafe1/120이실패했다. 125개독립재생에서채점/metrics일치,copy/parser오류0이다. 명시방향을무시하거나원문에없는충돌·객체확정조건을추가하는FN11과현재승인우회수용1이주요문제다. 더큰모델/동일few-shot반복및span추출대안을택하지않는다.

같은32B/runtime의한호출에서원문semantic facts를명시한뒤모델이최종root decision을출력하는별도3.0계약을설계검토한다. 원문에있는조건과후속inventory/targetconfirmation/approval를분리하고,모순은거절만한다. 최종decision은projection에서바꾸지않으며rawREADY는validation전에계수한다. Canonical1.0parser는byte불변,기존2.0quoteadapter행동과기존wire를보존한다. Metadata는새3.0과2.0projection을구분한다. 새계약성공이나채택을미리주장하지않으며실제비교전CPU/회귀/독립review/동결/commit/push가필요하다. v2모델출력미노출과root입력노출이력의구분은유지한다.


## D030 — Facts 실패 보존과 예산을 제한한 thinking 비교

32B facts3.0은 raw 분류115/120이지만 semantic95/120/rawFP3/unsafe1로 실패했다.
중복 인용과 대상 선택 제외·단순 비대상 보존의 혼동이 추가 거절을 만들었고 실제 조건 누락도 남았다.
Facts 검사를 없애는 경로는 unsafe를 늘리므로 채택하지 않는다.

같은32B에서 복사/parser120/120이었던 기존single2.0을 사용하고 내부 thinking을 한 번 비교한다.
Context4096/seq1/KV256을 유지하며 총completion1024/timeout120으로 제한한다.
기존prompt의 정책·예시는 보존하고 첫 출력 지시의 적용 범위만 최종 content로 명시한다.
기존 명시 thinking sampling/parser를 사용하며 reasoning 원문은 저장하지 않는다.
잘림과 no-final도 실패 분모에 남고 retry/cap증액/decision 보정은 없다.
[고정할 조건과 한계](requirement_thinking_control_plan.md)를 실제 호출 전에 검증·동결한다.

## D031 — Thinking 실패 보존과 현대 모델의 별도 local runtime 검증

같은32B/기존2.0/thinking은 semantic109/120, rawFP2/58, unsafe1/120으로 실패했다.
READY gold62개는 모두 맞았지만 lookup 분류4건, non-READY 대상 누락2건, 분수 표현의
raw READY1건과 방화문 이동 READY 수용1건이 남았다. Truncation3건은 unknown과 원래
분모에 보존한다. 이3건을 전부 정답으로 가정해도112/120이므로 cap 증액만으로 gate를
고칠 수 있다는 근거가 없다. 같은 prompt 문구를 반복 수정하거나 parser/gold를 완화하지 않는다.

다음은 최신 Qwen3.8-27B의 ggml-org Q4_K_M 변환물과 pinned llama.cpp를 검토한다.
현재 cu118 vLLM의 architecture 제약을 application 복제나 system driver/CUDA 변경 없이
해결할 수 있는지 먼저 HOME 안의 제한된 source build로 확인한다. CMake3.23.5와
명시SM80만 사용하며 automatic dependency fetch와 GPU 탐색/실행을 빌드 단계에서 배제한다.
기존 Backend와 vLLM 환경은 보존한다. Build 성공은 모델 품질 또는 GPU 실행 허가가 아니다.

실제 weight/header, native allocator의 전체 peak, 공통 guard와 별도 HTTP grammar protocol을
검증한 뒤에만 fresh GPU3 예산에 맞는 제한 실행을 진행할 수 있다. Native runtime에 Torch
allocator cap이 없다는 차이를 숨기지 않는다. Disk20GiB reserve도 유지하며 필요한 경우
검증된 비활성·재다운로드 가능한 weight만 정리한다. 아직 설치·정리·다운로드·native GPU
실행은 하지 않았다. [후보와 검증 순서](modern_local_runtime_candidate.md)를 따른다.
이는 Phase5.x 안의 전략 변경이며 최종 모델 채택이나 Phase6 시작이 아니다.

## D032 — Native runtime의 명시적 계약과 실행 전 검증

기존 vLLM 환경과 두 HTTP dialect를 유지하고 llama.cpp용 `llama_cpp_json_schema`를
별도로 추가한다. 실패 시 schema 없는 요청이나 다른 dialect로 자동 재시도하지 않는다.
기존 generation2 branch schema/원문 prompt/quote adapter/canonical parser/품질 gate를 보존한다.
첫 실험 sampling은 T0.7/P0.8/K20/minP0/seed42, presence·frequency0/repeat1/window0,
samplers temperature→top_k→top_p→min_p다. Native runtime은 prompt token도 penalty에
포함하므로 인용문 복사를 불필요하게 억제하지 않도록 모델 출력 관측 전에 정했다.
공식 card의 presence1.5를 그대로 따랐다고 주장하지 않는다.

공통 lifecycle guard를 공유하되 native binary/source/library/GGUF/header proof를 별도로
검증한다. 다른 프로세스의 존재 자체는 거절 사유가 아니다. 허용 GPU3에서 fresh free/utilization을
측정하고 전체 startup/inference peak와 안전 margin이 맞을 때만 실행한다. 실제 child에서
노출 장치 수1과 허용 UUID를 확인한 뒤 같은 PID로 native exec한다. Parent death/core dump0,
자체 process group 정리, project lock, timeout/free-floor 감시와 localhost listener 검사를 유지한다.
다른 사용자나 GPU0/1/2는 변경하지 않는다. Native allocator의 hard cap은 검증되지 않았으며
watchdog가 사전 VRAM 예산이나 하드웨어 격리를 대신한다고 주장하지 않는다.

HOME 내 고정 source/CMake의 CUDA11.8/SM80 build 및 `$ORIGIN` relink를 통과했다.
CUDA-linked tokenize 도구를 CPU 검사에 사용하지 않고 모든 GPU backend가 꺼진 별도 helper로
실제 native chat/schema/grammar/prefix prefill/sampling을 확인한다. GGUF header/SHA 확인 후에만
vocab-only tokenization/context 검사를 추가한다. Runtime의 stdout/stderr와 reasoning 원문은
보존하지 않으며 평가기는 final content만 기존 parser로 전달한다.

평가를 끝내고 종료한 MoE의 재다운로드 가능한 가중치4개만 hash 확인 후 정리했다.
단일 새 후보 다운로드에는 기존 size/SHA 확인과 atomic no-clobber publication,
20GiB+512MiB free 감시 및 자체 curl descendant 정리를 적용한다.
새로운382개 회귀 검사 통과는 이 plumbing의 검증이며 모델 품질 gate 통과가 아니다.


## D033 — 공식 NFC 동등성 실패와 원문 보존 GGUF 후보의 구분

공식 tokenizer의 NFC 정규화와 pinned llama.cpp의 raw UTF-8 BPE 경로가 다르다.
공개20개 중 공식 HF token ID 일치는19/20으로 **FAIL**이며 원래 fixture와 실패 증거를
그대로 보존한다. Native의 원문 byte roundtrip은20/20이고, 동일20문자열과 tokenizer의
나머지 설정을 유지한 채 NFC만 메모리에서 끈 별도 진단 reference와는20/20 일치했다.
이 파생 결과를 공식 HF tokenizer 동등성 PASS라고 부르지 않는다.

다음 실험 후보를 `qwen38-gguf-raw-unicode-v1`로 명시한다. 정확한 HF token ID 동등성은
내부 호환성 가정이었고 제품의 요구사항은 원문 보존과 strict quote/schema/semantic 안전성이다.
원문을 보존하는 실제 native 경로를 별도 후보로 검증할 수 있다고 판단한다. 입력 또는 모델
출력을 NFC로 고치지 않으며, 원문 인용 검사와 canonical parser, raw READY 오판·unsafe·
semantic 품질 gate는 그대로다. 학습 시 token sequence와의 차이로 품질이 달라질 수 있고
공개20개가 전체 Unicode 동작의 증명은 아니다. 실제 평가 전 모델 채택은 하지 않는다.

이 후보의 문맥 증거는 official FAIL과 raw reference를 모두 hash로 연결하고 실제 native
vocab-only token 수를 사용한다. 기존 HF 동등성을 요구한 검사 기록을 덮어쓰지 않고 별도
helper/report에서 reference 종류를 명시한다. 공개 grammar/EOG 검증과 최대 context4096,
completion768, 원문 roundtrip 조건은 유지한다. 이후 GPU3 실행에는 D032와 전체 peak·margin
조건이 그대로 적용된다. 이번 결정은 Phase5.x의 실험 전략이며 품질 gate 통과가 아니다.


## D034 — 시작 검사에 맞는 logical batch2와 physical ubatch1

첫 native GPU startup은SIGABRT로 실패했다. 같은profile의 제한된 stderr 진단에서
`llama-context.cpp:1734`의GGML_ASSERT 실패를 실제 확인했다. 고정 source의 시작 sequence
removal 검사는2token을한 decode에 전달하며 logical batch1과충돌한다. 실패2개와그당시source/
config를보존한다. Watchdog free floor 초과나타인process변경이원인이었다고주장하지않는다.

NativeLaunchConfig에 logical batch2/physical ubatch1을명시적인고정정수로기록한다.
한 CUDA graph의물리token수·context4096·sequence1·F16KV·rollback0은유지하며GPUfallback은없다.
논리입출력배열에수MiB의host/pinned-host 증가가가능하나기존28GiB전체예상과추가margin에
이를포함한다. 실제wholeGPU peak나bitwise/품질동등성은새실행전미검증이다.

CPU vocab/template/grammar/context 증거는GPU context/decode를만들지않고동일production
wire의실제native token수를측정한것이므로유효하다. 이를새GPU실행성공증거로재사용하지않는다.
새config/argv/report의일관성과기존거절·guard검사를회귀검증한뒤freshGPU3조건으로재실행한다.
원래batch1로얻은startup실패는새epoch로덮어쓰지않는다. 품질평가는runtime검증·동결후다.


## D035 — 품질 평가 전 명시적 prefill64 성능 검증

Batch2/ubatch1의 실제 startup·공개 JSON·최대 context 검사는 통과했으나 입력 처리 지연이
크다. 공개 요청55.055초, 자원 probe의3328token prefill82.071초를 관측했다. 이 설정으로
전체 평가를 시작하기 전에 batch64/ubatch64의 성능·자원을 별도 검증한다. 모델 응답의 품질을
개선하기 위한 prompt/schema 변경은 없으며 실제 exposed/v2 품질 호출은 아직0회다.

고정 source의 MMQ/GDN/graph liveness와 전체 workspace 검토에서64/64를28GiB 예상 예산으로
제한 실행할 근거를 확인했다. 이 값은 엄밀 상한이 아니다. 기존2/1은 기본값으로 보존하고,
64/64는 명시적인 고정 pair와 최소 예상28,672MiB를 요구한다. 다른 pair나 자동 fallback은 없다.
새 epoch의 fresh GPU3 사전 검사와 최대 문맥 자원·공개 응답 증거가 필요하다. Sampling·prompt·
원문 quote/parser·품질 gate는 유지하며, batch에 따른 수치/출력 동등성을 미리 주장하지 않는다.


## D036 — 단회1차 gate PASS checkpoint와 최소 반복 원칙

2026-09-20 사용자 지시가 기존 자동120×3·V2×3 평가 순서를 대체한다. 현재 native Qwen3.8의
노출120개 단회는schema120/semantic117/rawFP0/unsafe0으로 사전4gate를 통과했다. 전체125개
저장 응답의 독립 재생도 일치했다. 세 오류는 non-READY 인용/과잉거절/대상 범위이며 원본에 보존한다.

같은120개 추가 모델 반복은0회로 판단한다. 현재 해결해야 할 미확정 안전 오판이나 경계선 gate가
없으며 같은 seed·같은 자료의 전체 반복은 새 의미 사례를 추가하지 않는다. 이는 모델 반복 출력
동일성의 증명이 아니다. CPU 재생은 저장된 응답의 처리 재현성만 검증한다. 향후 반복이 필요하면
해결할 구체적 불확실성과 최소 사례/횟수를 먼저 명시하고 사전 동결한다. 기준 미달 후보를 같은
자료로 무조건 반복하지 않는다.

완료진단 보존·자체 모델 종료·VRAM 반환·필요 회귀·commit/push 후 같은 설정의V2 80×1+warmup5를
다음 최소 검증으로 준비한다. 첫 warmup 전에 별도 freeze와 원격 checkpoint를 완료한다. 기준은
schema80/80,semantic≥76/80,rawFP0/40,unsafe0/80이며 schema100%/95%/0/0 threshold를 그대로 유지한다.
V2preview·선별 재시도·완료125개 재평가는 하지 않는다. Raw관측80/80과 모든 오류/unknown/중단을 보고한다.
이는 과거3회 계획의 완료가 아니라 사용자 지시에 따른 평가 횟수 변경이다.

Epoch5의 formal 품질 호출0을 확인하고 own guard만 pidfd SIGTERM으로 종료했다. 다른 process는
변경하지 않았다. 완료한 startup/resource/runtime suite를 처음부터 반복하지 않는다. 새 실행에서는
현재free/util·ownprocess·device·loopback 등 실제 안전 실행에 필요한 확인만 수행하고 검증된
source/config/resource 증거를 연결한다. Batch/flash/graphs/cache/throughput tuning은future optimization이며
Phase 완료를 막지 않는다. 1차PASS만으로 Phase6/모델최종채택을 선언하지 않고V2 품질결과를 확인한다.


## D037 — V2 첫 단회 실패 보존과 다음 모델 비교

1차 진단 PASS 뒤 별도 동결한 V2 80×1+warmup5가 schema80/parser79/semantic73/rawFP1/unsafe1로 실패했다.
독립85개 CPU 재생은 원본 집계와 일치했다. 저장 응답 재생 PASS를 모델 품질 PASS로 해석하지 않는다.
실제 출입문을 가구 이동으로 READY 수용한1건이 rawFP/unsafe를 동시에 위반한다. Non-READY target rubric
3건을 가정상 모두 인정해도 이 실패는 남는다. 실제 IFC 실행은 없었다. Gold/parser/출력을 보정하지 않는다.

최신 사용자 지시에 따라 명백한 실패 후보는 반복하지 않는다. 현재 Qwen3.8-27B raw GGUF 후보를 채택하지 않고
다른 모델 후보 비교를 진행한다. Phase5.x는 미완료이며 Phase6은 시작하지 않는다. 새 후보는 공식 자료와
기존 runtime의 지원 범위, 전체 VRAM+margin, 디스크 reserve를 먼저 비교한다. 같은 모델의 sampling/prompt
조정을 다른 모델 비교로 대신하지 않는다. 향후 다른 접근이 필요하면 그 근거를 별도로 기록한다.

원래125개 진단과 독립 재생은 보존만 하고 재실행하지 않았다. Epoch6 own guard를 검증해 종료하고
GPU3 시작 전 free36,373MiB/used3,965MiB/util0% 복귀를 확인했다. 다른 사용자 process 신호는 없다.
V2는 MODEL_OUTPUT_SEEN / EXPOSED로 새 record를 추가하며 원래9파일 freeze와 addenda는 수정하지 않는다.
미래 조정 뒤 같은 V2를 새 unseen 결과로 부르지 않는다. 비필수 runtime 최적화는 future optimization이다.


## D038 — 다른 공식 모델 Gemma4-31B QAT의 제한 사전 검증

보존한 Qwen3.8 V2 실패 이후 공식 후보3개를 비교하고 Gemma4-31B QAT Q4_0를 다음 사전 검증 대상으로 정했다.
한국어 품질 우위나 gate 통과를 예상한 선택이 아니라 다른 학습 계열·공식QAT·기존native지원 가능성에 근거한다.
동일 CUDA11.8/SM80 binary와 shared lifecycle은 재사용한다. 모델별 header/tokenizer/template/grammar/전체peak는
새 증거가 필요하며 이미 완료한 공통runtime검사는 반복하지 않는다. 새 환경이나 시스템변경은 없다.

공식temperature1.0/top_p.95/top_k64와 프로젝트neutralpenalty/seed42를 명시profile로 추가했다.
Native모델ID/Q4_0/profile 조합을 검증하고 final content의Gemmathoughtmarker는거절한다.
기존Qwenwire는byte동일, scorer/gold/canonicalparser/업무계약은변경하지 않는다.
샘플링·형식·모델을 구분해 기록하며 기존Qwen raw-Unicode 참조를 Gemma의동등성으로승계하지 않는다.

다음1차진단은 사전runtime/model검증·epoch동결·commit/push후 exposed120×1+warmup5다.
명백한실패는반복0회, 통과/경계선만필요한최소추가검증으로간다. 이미본V2를새unseen으로쓰지않는다.
세부 조건은 docs/gemma4_31b_diagnostic_plan.md에 기록했다. 아직runtime기동·품질통과·모델채택은없다.
