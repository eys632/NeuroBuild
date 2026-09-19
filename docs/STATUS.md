# NeuroBuild_v2 실행 상태

갱신: **2026-09-20 06:29 KST**. **Phase 0~5 원격 checkpoint 완료; Phase5.x 평가 확대 진행 중.**

| 항목 | 현재 상태 |
|---|---|
| 완료 Phase | 0 Foundation, 1 Domain, 2 Persistence, 3 IFC Engine, 4 Explicit Workflow, 5 Local Model |
| 마지막 완료 Phase checkpoint | `d6e39c89658c552c59a8049d7198da051290bd3b` Phase5 commit/push, remote hash 일치 |
| GitHub | 공통 `v2`, SSH push 정상; 최신 checkpoint는 git log 참조 |
| 검증 | 전체 **245 tests PASS**, skip0, 실제 PostgreSQL/IfcOpenShell, DISPLAY 없이16.377s |
| 현재 Phase | 5.x: 120개 자료·코드 freeze931c625 push확인, 개발v3 120회완료: 의미108/120,rawFP3/60(Backend차단),FN9/60. v4재평가의미96/120/FN24로FAIL;간결한영어v5도13/40으로FAIL. 기존최고v3에공식sampling설정비교준비. holdout미호출. Phase5 Qwen3-14B-AWQ/promptv3 선정, development seed20×3 의미60/60, READY오판0/33. 8B 동일prompt54/60. 실패결과포함5 run보존 |
| Hard blocker | 없음. GPU3 가용량 기반 공존 실행 실제 통과 |
| Backend | `.conda` Python3.12.14 / PostgreSQL17.11 / psycopg3.2.10 / IfcOpenShell0.8.5 |
| Model Runtime | `.conda-vllm` Python3.12.14, cu118 vLLM0.8.5/Torch2.6.0, 14B AWQMarlin FP16, TP1/context4096/seq1 |
| 다음 단계 | Phase5.x versioned dataset40development/80heldout, model/scorer 고정 후 평가 |

## 완료 근거와 실제 한계

- Phase1 `e68baa4`: Domain29. Phase2 `18c7e21`: immutable artifact/PostgreSQL intent·CAS·idempotency·실제재시작. Phase3 `56926a0`: IFC4 m/cm/mm·회전부모·headlessmesh·불변조건. Phase4 `dd58b59`: 별도대상확인/승인·ApplyV1·stale/duplicate/recovery.
- Phase5: 5 actual model runs의 결과/정확한manifest/VRAMsnapshot을 `evaluations/results/phase5/`에 보존. 독립 metric 재계산·14Bv3응답60개 재검증 PASS. Launcher20 tests 및 protocol변경후 실제추론3/3 PASS.
- 자동gold는 **AUTO-GENERATED / NOT HUMAN VERIFIED**. 같은 개발20개를반복한60회결과는 unseen/human 품질보증이 아니다. 0/33위험오판도위험0증명이아니다.
- [Phase5 report](reports/phase5_report.md), [독립 review](reviews/phase5_final_review.md), [runtime protocol/SM120](model_protocol_compatibility.md).

## 운영 상태

GPU3만 사용하며 타인process를변경하지않는다. Baselinefree36373MiB/util0%,margin7275MiB,14B예상peak18432MiB로preflight통과. 실제14Bv3구간aggregatebaseline대비peak11684MiB,최소free24690MiB다. process전용peak/hardreservation이아니다. 자신의guard+child만운영하며GPU0/1/2fallback없음. FileStore rendezvous 및loopbackGloo/NCCL로actualTCP5개모두127.0.0.1검증. Phase5 모델server는STOP_REQUESTED/childexit0/자체rendezvous정리로정상종료했다. 종료후GPU3used3965/free36373MiB/util0%복귀. Phase5.x경계검토후freshpreflight재기동/5loopbacklisteners검증완료,V3/V4/V5평가후자기guard만정상종료하고free36373MiB복귀확인. 다음실험전freshpreflight예정이다.

Private PostgreSQL은 `var/postgres` +0700Unixsocket `var/run/postgresql`, noTCP/peerauth다. root disk약62GiB free(97%), Backend1.4GiB/modelenv7.4GiB/weights9.4GiB/cache5.3GiB. 미선정8B 다운로드16.4GB는manifest/결과보존후본인project의정확한14파일+manifest만검증해정리했다. 모든환경/weight/cache는project내Git제외다. Modeldownload20GiB reserve 및설치전disk확인을유지한다.

Phase4 human review는 아직in-memory이며durable review/queue/worker는Phase7이다. Object resolution/API/browser는아직구현전이므로 **Internal Technical MVP 완료가 아니다**. RTX5090은 **PREDICTED_UNVERIFIED**. Publicexposure/pilot/민감IFC/fine-tuning은자동범위밖이다.
