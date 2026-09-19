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
