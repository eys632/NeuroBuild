# Requirement hardening v1 데이터

Gold 상태는 **AUTO-GENERATED / NOT HUMAN VERIFIED**다. 120개 모두 민감한 IFC나 실제 사용자 자료 없이 작성한 synthetic case다. 독립 에이전트 검토와 참조 응답 검증은 사람의 전문 검수를 대신하지 않는다. 외부 pilot 전에 [human review 양식](../evaluations/hardening_v1_human_review.csv)을 사람이 검수해야 한다.

Phase5 checkpoint `d6e39c89658c552c59a8049d7198da051290bd3b` 이후 Phase5.x용으로 작성했다. 이 문서는 데이터 작성·검증 기록이며 모델 평가 통과를 뜻하지 않는다. 작성 당시 새 데이터에 대한 모델 호출과 출력 열람은 없었다. 실행 결과는 별도 run manifest와 Phase 보고에 남긴다.

## 구성과 재현

| Split | Case | READY | CLARIFICATION | UNSUPPORTED | 3회 평가 시 trial |
|---|---:|---:|---:|---:|---:|
| Development | 40 | 20 | 8 | 12 | 120 |
| Holdout | 80 | 42 | 15 | 23 | 240 |
| 전체 | 120 | 62 | 23 | 35 | 360 |

A–J의 각 분류는 development 4개, holdout 8개, 총 12개다. 분류와 기존 rubric은 [평가 계획](model_evaluation_plan.md)을 따른다. 명시 XY 이동, 부호·단위, 누락 정보, 회전·Z·층 이동, 복수 대상·operation, 조건·부정·취소, 제외 대상, 승인 우회, 조회, 긴 문맥, 향후 설계 요청을 포함한다.

- [Development](../evaluations/requirement_hardening_v1_development.jsonl): 공개 seed20을 row 값 그대로 유지하고 새 20개를 추가했다. 이전 prompt 개발에 사용한 seed20은 새 미관측 표본으로 집계하지 않는다.
- [Holdout](../evaluations/requirement_hardening_v1_holdout.jsonl): 새 80개다. Seed 입력을 복사하지 않았으며, 전체 입력의 exact/공백 제거 비교에서 중복은 0개다.
- [결정적 generator](../evaluations/generate_requirement_hardening_v1.py): 무작위 추출, 모델 호출, 외부 전송, GPU 사용 없이 고정 문장과 골드를 작성한다.
- [작성 manifest](../evaluations/hardening_v1_manifest.json): split·분류·decision 수, 60개 그룹, source hash, 작성 시점과 검증 dependency hash를 보존한다. 작성 lifecycle은 `AUTHORING_COMPLETE_PENDING_REVIEW`로 유지하고 검토·freeze는 별도 `hardening_v1_freeze.json`에 기록한다.

프로젝트 root에서 다음 명령으로 동일 파일을 재생성·검증한다. 해당 환경에는 backend dependency만 필요하다.

```sh
PYTHONPATH=. .conda/bin/python evaluations/generate_requirement_hardening_v1.py
```

기존 파일이 byte 단위로 같으면 재사용하며, 다른 내용이면 덮어쓰지 않고 실패한다. Parser/scorer/schema가 바뀌면 dataset이 같더라도 manifest의 검증 hash가 달라질 수 있다. Freeze 이전에는 이전 manifest를 보존하고 재검증하며, freeze 이후에는 변경 이유와 새 검증 기록을 별도로 남긴다. 모델 결과를 본 후 gold를 바꾸려면 dataset version을 올리고 이전 결과와 분리한다.

| 데이터 | SHA-256 |
|---|---|
| 공개 seed20 | `ae0adad9b8113397fb7559969b3f12070d806982fb2d71b4ea024504d73af648` |
| Development40 | `85734d7c5845bbc52af43941631adfa66f3b43cc7494177e1230de6dfb18ff88` |
| Holdout80 | `12c08e85a3b64c459fe7385e1cab35a4a036c6ceb3bc1d27d137ba3515e74d78` |

## 골드 계약

READY는 현재 지원하는 단일 IfcFurniture의 같은 층 상대 XY 이동 요청이다. 대상 description은 실제 객체의 존재·고유성을 증명하지 않으며, requirement 추출 후에도 inventory 확인, target confirmation, 별도 proposal approval이 필요하다. Gold의 `apply_authorized`는 항상 false다.

단위·숫자·부호의 원문 표기를 추출하고 metre 변환은 코드가 한다. 현재 계약은 원문에서 경계가 확인되는 십진 표기만 지원한다. 분수 표기는 수학적 의미가 명확해도 모델이 십진수로 계산해 출력하지 않으며 CLARIFICATION으로 분류한다. 이는 자연어 자체의 모호성과 구분되는 **현재 표현 형식의 제한**이다. 새 READY 53개와 기존 READY 9개는 모두 현 schema/parser로 표현 가능한 참조 응답이 있다.

일반 READY의 `target_text`는 gold의 대상 description을 정확히 보존한다. 제외 구문은 positive noun만 남기지 않고 scope·제외 대상·`말고` 연결을 포함한 원문의 최소 연속 span을 유지한다. 층·색·위치·따옴표 이름 등의 수식어를 버리지 않는다. Non-READY는 지정된 target slot 보존을 확인하며 READY와 같은 exact target 길이를 강제하지 않는다.

`instruction_text`와 축별 `evidence_text`는 현재 유효한 지시의 정확한 원문 span이다. 취소·철회·과거 인용된 이동 값은 현재 displacement에 섞지 않는다. 현재 이동 자체의 금지, 아직 확인하지 않은 충돌·통로·개수 조건은 CLARIFICATION이다. 높이·회전·층을 유지하라는 조건, 제외 대상, 과거에 거절된 우회 요청을 인용했다는 사실만으로 정상 단일 XY 요청을 거절하지 않는다. 새로 활성화된 승인 우회 요청은 UNSUPPORTED다.

`source_grounding`은 새 READY gold의 검토·참조 검증용 부가정보이며 모델 입력에 넣지 않는다. 모델에는 원문과 code가 제공하는 axis context만 전달한다. 참조 응답은 schema, backend parser, 현재 rubric scorer를 통과하는지 확인하기 위해 작성했다. Non-READY 참조는 필요한 slot을 보존하려고 긴 target span을 사용할 수 있으며 모범 응답 길이나 모델 품질 기준을 추가하지 않는다.

## 긴 문맥과 토큰 한도

새 I 분류 10개에는 행정·도면·열람·기획·보관 문서의 무관한 설명을 붙였다. 설명에 새 현재 이동이나 조건을 추가하지 않았으며, 최종 현재 지시와 gold 값은 유지했다. 새 development I 입력은 585–599자, holdout I 입력은 553–594자다. 기존 seed의 I01/I02는 원본 보존을 위해 늘리지 않았다.

기존 로컬 Qwen3-14B-AWQ tokenizer revision `31c69efc29464b6bb0aee1398b5a7b50a99340c3`와 prompt v3를 CPU에서만 검사했다. `USE_TORCH=0`, `USE_TF=0`, `USE_FLAX=0`, offline 모드로 실행했고 `torch`가 import되지 않았음을 확인했다. Client와 같은 system/user JSON, `add_generation_prompt=True`, `enable_thinking=False`를 사용했다.

| Split | Chat 입력 token 범위 | 최대 입력 + output ceiling 768 |
|---|---:|---:|
| Development | 2399–2774 | 3542 / 4096 |
| Holdout | 2405–2779 | 3547 / 4096 |

측정 prompt SHA-256은 `716137f3e275cb0030f1f497f8e23bbeeefd8a62eae757378231b7d910db3c3e`다. 이는 context 길이 확인이며 추론 성공·응답 길이·품질·다른 tokenizer의 적합성을 보장하지 않는다. 로컬 측정 원본은 `var/hardening-draft/final_token_budget.json`에 있다.

## 평가 분모와 freeze 절차

[Harness](evaluation_harness.md)는 5회 warm-up을 제외하고 case당 3회 평가한다. Parse/schema/backend 실패와 timeout을 전체 trial 분모에 유지한다. Development의 gold READY/non-READY 분모는 각각 60/60 trial, holdout은 126/114 trial이다. 같은 case의 반복과 같은 그룹의 최소쌍은 독립 표본이 아니므로 단순 trial 수만으로 일반화 신뢰도를 과장하지 않는다.

기존 critical false positive는 **gold non-READY를 READY로 허용한 trial**이다. Parser 전 모델 READY와 parser 후 accepted READY를 별도로 보고한다. 여기에 **gold READY이고 accepted READY이지만 target 또는 XY 값이 틀린 trial**을 별도 critical move error로 추가해 잘못된 이동 추출을 숨기지 않는다. 이 추가 metric은 기존 semantic 판정·gold·FP 분모를 바꾸지 않으며, 두 종류의 unsafe accepted READY를 구분해 보고한다.

Freeze 전에 독립 검토자가 development와 holdout gold를 검토하고, 참조 응답 120개의 schema/parser/scorer 통과 및 token 한도를 확인한다. 검토자는 holdout 입력·gold를 볼 수 있지만 그 내용을 prompt 변경에 사용하지 않는다. Root는 최종 dataset/manifest/prompt/schema/parser/scorer hash와 Git checkpoint를 별도 freeze record에 기록한 뒤 평가한다. Holdout 호출은 해당 독립 검토가 끝난 뒤에만 시작한다. 사람 검수 필드는 사람이 검수하기 전까지 비워 둔다.

## 해석의 한계

새 scenario 최소쌍·동의 변형은 각각 같은 split에 묶었다. 공개 seed 10그룹, 새 development 10쌍, holdout 40쌍의 membership을 manifest에 기록했다. 그러나 좁은 XY 작업 grammar, 대상·숫자 치환, 조건 분류 원칙, generator scaffold는 split 사이에 공유된다. 이 분리는 **시나리오별 미관측 출력 평가**이며 완전히 독립된 의미 family나 새로운 설계 추론 능력의 검증이 아니다.

Holdout은 plaintext JSONL과 generator에 있으므로 봉인은 파일 접근 제어가 아닌 평가 절차다. 출력에 맞춘 prompt 조정·유리한 gold 수정·성공 trial 선택을 금지하고 작성·검토·실행 hash로 순서를 남긴다. Synthetic rubric 자체의 오류, 실제 사용자 표현·IFC 분포 차이, 비정형 긴 문서, A100/RTX runtime 차이는 남는다. 자동 점수와 에이전트 검토만으로 human-verified accuracy, 안전한 실제 IFC 적용, RTX 실측 통과를 주장하지 않는다.
