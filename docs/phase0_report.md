# Phase 0 완료 보고서

작성일: 2026-09-19. 작업 root: `/home/a202192020/NeuroBuild_v2`.
이 보고서의 완료 범위는 Foundation이며 Application 실행 가능 상태를 뜻하지 않는다.

후속 갱신(2026-09-19): 아래는 최초 Phase0 보고 당시 기록이다. 이후 사용자가 Phase별 승인 대기를 폐지하고 Phase11까지 자율 개발을 지시했다. Git 작성자는 제공됐고 local Phase0 commit `29d4774`가 생성됐지만 GitHub 인증 부재로 push는 실패했다. 현재 지침/진행은 [AGENTS.md](../AGENTS.md), [MASTER_PLAN.md](MASTER_PLAN.md), [STATUS.md](STATUS.md)를 따른다. 아래 과거 승인/작성자 미설정 문구는 현재 blocker를 뜻하지 않는다.

## 1. Phase 0 결과 요약

전역 지침을 읽고 read-only 환경/Git 조사를 수행했다. 공통v2 branch, 프로젝트 지침,
architecture/환경/호환성/모델 후보/평가/roadmap 문서, 설정 예제와 runtime info 도구를 준비했다.
환경/패키지/weight 설치와 Domain/IFC/DB/production LLM/frontend 구현은 수행하지 않았다.

## 2. A100 실제 환경

| 항목 | 관측값 |
|---|---|
| OS / Kernel | Ubuntu20.04.6 / 5.15.0-139-generic, glibc2.31 |
| CPU | Xeon Gold5218R ×2, 40core/80thread |
| RAM | 503GiB total / 조사 당시477GiB available |
| Disk | root1.8T, 사용96%, 여유86G |
| GPU | 허용 GPU3: A100-PCIE-40GB, CC8.0 |
| GPU3 VRAM | total40960MiB, used3965MiB, free36373MiB, reserved620MiB |
| Driver / CUDA | 535.183.01 / nvidia-smi CUDA12.2; 설치 Toolkit11.8 |
| Docker | CLI28.1.1; daemon/GPU container 미확인 |
| Python | system3.8.10, pip24.3.1; python/Conda 없음, 프로젝트 환경 없음 |
| Node | system10.19.0 / npm6.14.4 / pnpm 없음 |
| PostgreSQL | PATH/일반 설치경로/5432 listener에서 미발견 |

GPU3에 예상 밖 프로세스3개를 발견하여 즉시 보고했다. 소유자/명령행을 조사하거나 종료하지 않았다.
GPU0/1/2 process 조회는 다른 사용자/GPU 접근 금지에 따라 생략했다. [전체 조사](environment.md)

## 3. GitHub repository 상태

`origin=https://github.com/eys632/NeuroBuild.git`, 기본/유일 원격 branch `main`, HEAD `09145974c17d1a09abdd2c48863e940fe68678b9`.
이력5개, 기존v1과2-byte v2 placeholder를 확인했다. remote write 인증은 검증하지 않았다.
신규 파일의 local commit/push는 아직 없으며 GitHub 백업 완료 상태가 아니다. [Git 상세](git_workflow.md)

## 4. 선택한 공통 v2 branch 전략

기존 main을 부모로 local `v2` 생성. Application은 양 서버에서 같은 commit 사용.
기존 branch/파일/history는 보존한다. 서버별 branch와 force push를 사용하지 않는다.

## 5. 최종 project directory 구조

새 파일은 checkout 최상위 `AGENTS.md`, `README.md`, `.gitignore`, `docs/`, `configs/`, `scripts/`,
`runtime/`, `requirements/`, `evaluations/`에 있다. 기존 `NeuroBuild_v1/`, `NeuroBuild_v2/readme.md`는 보존했다.
현재 tree와 향후 구조를 구분했다. [현재 tree](../README.md), [향후 배치](architecture_blueprint.md)

## 6. A100 / RTX5090 Cross-Server 전략

Common Application/DB migration/schema/prompt/tests를 공유한다. GPU dependency와 network profile만 분리한다.
같은 source는 데이터 자동 동기화를 의미하지 않는다. runtime build/precision 차이는 별도 회귀평가 대상이다.

## 7. Runtime Profile 구조

`configs/common.json` → 명시적으로 고른 `a100.json`/`rtx5090.json` → allowlist 환경변수.
profile 자동 감지/fallback 없음. model/dtype/quant 미선정, runtime NOT_TESTED.
TP1/context8192/memory0.90은 계획값이다. [설정 안내](../configs/README.md)

## 8. Network Profile 구조

`NEUROBUILD_PROFILE`, `PUBLIC_BASE_URL`, `FRONTEND_BASE_URL`, `API_BASE_URL`, `MODEL_SERVER_URL`.
localhost3000/8000/8003 예제이며 실제 서비스/외부 주소는 미구축이다. IP를 Application에 하드코딩하지 않는다.
향후 local `.env.*.local`은 Git 제외하며 현재 도구는 .env를 읽거나 source하지 않는다.

## 9. 관리자 Runtime Info 설계

`scripts/show_runtime_info.py --profile a100 [--json]`: profile, 현재 hostname, 설정상 GPU/index,
URL/model, Git commit/dirty, 증거 수준을 출력한다. GPU/서비스 probe, 모델 로딩, 외부 호출 없음.
잘못된 GPU mask와 credential/query가 포함된 URL은 거절한다. 향후 Admin 기반이다.

## 10. Headless / Viewer 전략

서버 GUI/X/display에 의존하지 않는다. 향후 IFC→headless conversion→GLB+GlobalId metadata→Browser/Three.js.
Viewer는 IFC 변경 엔진과 분리한다. 이번에는 conversion/frontend를 구현하거나 설치하지 않았다.

## 11. GPU 정책

A100 physical3만 (`CUDA_VISIBLE_DEVICES=3`), RTX5090 physical1만 (`CUDA_VISIBLE_DEVICES=1`), process cuda:0/TP1.
다른 GPU fallback과 process 종료 금지. 할당 GPU의 VRAM 최대 사용 허용과 안정성 margin을 구분한다.

## 12. Backend environment 계획

`.conda`, Python3.12, 공통 dependency/lock. psycopg/IfcOpenShell/jsonschema는 필요한 단계에 추가한다.
환경 미생성, package 미설치. base는 환경 관리에만 사용한다. [Backend 계획](../requirements/README.md)

## 13. Model Runtime environment 계획

`.conda-vllm`, Python3.12 우선 검토 후 선택 vLLM 요구사항으로 확정. torch/vLLM/Transformers/xgrammar는 이 환경에만.
현재 driver535에서 후보용 정확한 build는 미확정이다. [A100](../runtime/a100/README.md), [RTX5090](../runtime/rtx5090/README.md)

## 14. LLM 후보 shortlist

Qwen3.8-27B, Qwen3.6-35B-A3B, Gemma4-31B-it, Gemma4-12B-it, EXAONE4.5-33B.
모두 공식 모델/vLLM/license 자료 조사에 기반하며 최종 Primary Model은 없다. [출처와 상세](model_selection_plan.md)

## 15. 각 Model 후보 비교

| 후보 | 검토 이유 | 핵심 제약 |
|---|---|---|
| Qwen3.8-27B | 복잡한 지시/reasoning 후보 | 양쪽 BF16 불가; A100용 quant/runtime 경로 확정 필요 |
| Qwen3.6-35B-A3B | MoE 처리속도 비교 | total35B weight 필요; active3B만으로 VRAM 계산 금지 |
| Gemma4-31B | 공식 QAT W4A16 CT 배포 | 공개 artifact23.3GB, runtime 여유/양쪽 kernel 미검증 |
| Gemma4-12B | BF16 메모리 비교군 | 의미 품질과 stable release/context 정보 확인 필요 |
| EXAONE4.5-33B | 한국어 연구 비교 | 비상업 라이선스 조건; 기본 제품 모델로 채택하지 않음 |

Latency/semantic/schema/VRAM/startup 자체 실측은 모두 없다. 10개 분류20개 synthetic seed와
분모·재현 조건을 정의한 [평가 계획](model_evaluation_plan.md)을 작성했다.

## 16. A100에서 우선 실제 평가할 후보

조건부1순위 Gemma4-31B 공식 QAT W4A16, 2순위 Qwen3.8-27B의 적합 quant artifact.
현재 점유/디스크/build 검토를 통과한 뒤 순차 평가한다. 다운로드는 하지 않았다.

## 17. RTX5090 예상 호환성

공식 Blackwell CC12.0/32GB 사양과 upstream 정보를 근거로 예측한다.
실제 OS/driver, model quant kernel, KV/cache/graph 포함 fit은 UNVERIFIED다. 사용자 RTX서버에 접속하지 않았다.

## 18. Runtime Compatibility Matrix

[runtime_compatibility.md](runtime_compatibility.md)에 OS/GPU/VRAM/driver/CUDA/Python/backend/IFC/PostgreSQL/
torch/vLLM/model/dtype/quant/context/TP/runtime/benchmark를 행별로 기록했다. A100의 MEASURED도 runtime PASS는 아니다.

## 19. 생성/수정 파일 목록

신규22개. 기존 tracked 파일은 변경하지 않았다.

```text
.gitignore
AGENTS.md
README.md
configs/README.md
configs/common.json
configs/a100.json
configs/rtx5090.json
configs/runtime.env.example
scripts/show_runtime_info.py
requirements/README.md
runtime/a100/README.md
runtime/rtx5090/README.md
evaluations/requirement_seed.jsonl
docs/project_context.md
docs/architecture_blueprint.md
docs/environment.md
docs/runtime_compatibility.md
docs/model_selection_plan.md
docs/model_evaluation_plan.md
docs/implementation_roadmap.md
docs/git_workflow.md
docs/phase0_report.md
```

## 20. 추가 Dependency 또는 설치

**없음.** 저장소 clone 및 기반 파일 작성만 했다. Miniconda/Conda env/torch/vLLM/model weights/
PostgreSQL/IfcOpenShell/Node/frontend packages를 설치하지 않았다. 서비스/GPU process를 시작하지 않았다.

## 21. 발견한 문제와 검증

- GPU3의 예상 밖 점유3개, root96% 사용: 향후 runtime 평가/대형 설치 전에 재확인과 해결 필요.
- driver535 + 최신 모델/runtime 조합 미확정. 시스템 변경 없이 가능한 build 검토가 남았다.
- RTX5090 현장 접근 불가. 예측을 실제 검증으로 기록하지 않았다.
- Git 작성자 이름/이메일 미설정. 사용자에게 요청했으며 추측해 commit하지 않았다. 현재 원격 backup 미완료.
- sandbox 내부 GPU/network/netlink 조회는 실패했으나 승인된 read-only 조회로 서버 값을 확인했다. 이를 실제 driver 고장으로 기록하지 않았다.
- Runtime info smoke13건(profile/외부cwd/JSON/text/override/오류경로) 통과. Application/DB/IFC/model benchmark는 실행하지 않았다.
- 추가 확인: JSON profile3개 parse, synthetic20개 ID 유일성/10개 분류, Python syntax, 문서 상대링크 모두 정상. environment/secret/cache/weight/artifact 경로11개 Git 제외를 확인했다. legacy tree는 origin/main과 동일하다. 최종 디스크도96%/86G였다.

## 22. Architecture 변경 제안

요구 방향을 유지한다. 추가로 artifact finalize→DB transaction→idempotent recovery,
approval의 proposal 내용/base 결합, lease/fencing과 stale-head 동시성, gateway 전환 시 DB/artifact 일관성을 명시했다.
상태명/좌표계/placement 허용범위는 Phase1에서 확정할 설계 초안이다.

## 23. Phase 1 진행 가능 여부

**사용자 승인 후 Domain Contract 설계부터 진행 가능**하다. GPU/DB/model 실행이 그 설계의 선행조건은 아니다.
실제 Python 개발/테스트는 먼저 Backend3.12 환경 계획과 설치 범위를 확인하고 준비한다.
이번 실행에서는 Phase1을 시작하지 않았다.

## 24. Phase 1 전에 사용자가 결정해야 할 사항

Phase1 착수 승인이 필요하다. Git milestone commit에는 작성자 이름/이메일이 필요하다.
XY 좌표계/길이 단위/지원 placement는 Phase1에서 구체안을 검토해 확정한다.
GPU 점유/디스크 budget/DB provisioning/최종 모델은 해당 후속 설치·실행 단계 전에 해결할 항목이며
모두를 지금 결정해야 Domain 계약 문서화를 시작할 수 있는 것은 아니다.

**Phase0에서 종료한다. 사용자 승인 전에는 Phase1을 자동 시작하지 않는다.**
