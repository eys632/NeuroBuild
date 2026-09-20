# 공개 웹페이지 provenance 정리 — 2026-09-21 KST

사용자는 GitHub Secret Scanning의 Google API Key 패턴 9건이 NeuroBuild credential이 아니라
공식 `ai.google.dev` 공개 페이지의 client configuration에서 유입됐음을 확인했다.
그 값은 출력·복사·사용하지 않고, 현재 tree의 불필요한 raw snapshot을 제거했다.

## 변경과 보존

- Tracked `gemma4-12b-preparation/metadata/official-license/gemma4-license.html`을 삭제했다.
- 같은 공개 페이지 자료를 포함하던 ignored 연구용 HTML 3개도 제거했다. 경로·파일 전체 SHA·크기·패턴 건수만 [제거 기록](provenance_cleanup_20260921.json)에 남겼다.
- [최소 license provenance](../../evaluations/results/phase5x/gemma4-12b-preparation/metadata/official-license/license-source.md)에 공식 URL, 원래 확인 날짜, 모델/revision, Apache-2.0 표기와 필요한 결론을 남겼다. 공식 Apache-2.0 텍스트는 보존했다.
- 원래 integrity/ledger/provenance 기록은 역사적 수집 증거로 유지하고 [retention amendment](../../evaluations/results/phase5x/gemma4-12b-preparation/retention-amendment.json)로 현재 삭제 예외를 명시했다.
- 독립 검토에서 삭제 예외 외 원본 42개 파일의 SHA/크기와 기존 index 4개의 SHA가 일치했다. 평가 결과·freeze·source snapshot 변경 및 완료 평가/재검산 반복은 0회다.

## 다른 파일 조사와 예방

정리 전 tracked 1,955개 파일(26,269,211 bytes) 전체를 값 비노출 방식으로 조사했다.
문제 HTML 외에는 이전 README의 X-only Hugging Face 예시 placeholder 1건만 검출됐으며
실제 credential이 아니므로 `YOUR_HUGGING_FACE_TOKEN`으로 바꿨다.
나머지 tracked raw HTML은 기존 앱의 `index.html` 2개였고 알려진 패턴이 없었다.
별도 tracked raw JS snapshot은 없었다. 저장된 JSON/text/HTTP 관련 증거도 전체 파일 검사 범위에 포함했다.

[AGENTS.md](../../AGENTS.md)는 provenance 목적의 전체 외부 HTML/JavaScript/raw HTTP response commit을 금지한다.
필수 원본은 Git ignored evidence/research storage에 두며, 새 검사기로 commit 전 **전체 index**를 검사한다.
검사기는 Google/Hugging Face/GitHub/AWS/private-key/Slack/Stripe/OpenAI 패턴의 경로·규칙명·건수만 출력한다.
Symlink target을 따라가지 않고, 읽기 실패·충돌 index·대형 파일 등 불완전 검사는 실패로 처리한다.
정상 앱 HTML/JS는 허용하지만 secret 패턴 검사는 동일하게 적용한다.
알려진 패턴 검사이므로 모든 형태의 credential 부재를 보장하지는 않는다.

## 검증

- 신규 scanner 테스트 최초 14개 중 13개 PASS. 나머지 1개는 임시 저장소 바깥의 상위 Git 탐색을 허용한 fixture 문제였다.
- 테스트의 `GIT_CEILING_DIRECTORIES`를 임시 저장소 부모로 고정하고 실패한 테스트만 재실행해 PASS했다. Scanner 본체는 수정하지 않았다. 완료한 backend/model 검사는 반복하지 않았다.
- 핵심 정리 staged 후 `CUDA_VISIBLE_DEVICES='' .conda/bin/python -B scripts/check_repository_secrets.py --staged`: **1,960/1,960 files, findings 0, errors 0**.
- 이 보고서와 실행 기록을 추가한 최종 index도 commit 전에 검사한다. 삭제 diff의 원문은 출력하지 않는다.

검증 receipt: `var/research/repository-secrets-focused-proof.json`,
SHA `78fce10db3a97f7e8e9510a37be9a65cdbd7a68ada9004c77b984b34611c9915`.
보존 독립 검토 receipt SHA `3472a815a9107c0216b09e607fe5ac385e77e48ff6113569ded01b8e185a8e90`.

이번 정리는 일반 commit/push로 현재 tree에 반영한다. History rewrite, force push 및 과거 GitHub alert 조작은 수행하지 않는다.
기존 모델 서버 종료 상태를 유지했으며, 진행 중이던 다음 후보의 별도 변경은 이 보안 정리 commit에 포함하지 않는다.
