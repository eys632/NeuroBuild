# Gemma4 CPU 계약 증거

공식 Gemma4-31B QAT Q4_0의 다운로드·header·CPU 계약 검사 기록이다.
모델 채택, 품질 평가, GPU startup 성공 증거가 아니다. GPU 측정은 별도 epoch1 보관본을 따른다.

- `download.json`: 공식2파일 다운로드 완료. Weight는 Git에 넣지 않았다.
- `header-v2.json`: 실제 전체 file SHA와833개 tensor 이름·shape 검증 PASS.
- `header-v1-preserved/`: 최초 Q6_K 거절, I32 진단, 원래 검사기와 검증 기록.
- `contract/final-cpu-proof.json`: 공식 공개20개 token ID/원문 roundtrip20/20 및 입력200개 길이 PASS.
- `contract/public-vocab-proof.json`: 첫 native BOS raw prompt 비교 실패.
- `contract/public-vocab-v2-proof.json`: 정확한 BOS 처리와 effective token ID 일치를 검사한 PASS.
- `contract/normalization-witness-proof.json`: 별도 literal U+2581의 원문 roundtrip **FAIL**.
- `contract/README-v2.md`: 새 C++ TU/link·검증 방법과 보존 경계.
- `runtime-cpu-consumer.json`: aggregate와 source/ref hash의 실제 CPU 소비 검사.
- `runtime-props-v3-cpu-tests.json`: raw embedded template와 마지막LF를 제거한 `/props` 표시의 구분.

V1 실패·source·build 기록은 보존했으며 결과를 덮어쓰거나 입력·출력 문자열을 보정하지 않았다.
20개 probe 통과는 모든 Unicode 보존을 뜻하지 않는다. Template BOS와 `/props` LF 처리는
고정 native source의 동작이다. 후자는 공개 synthetic CPU tests이며 실제 startup 증거와 구분한다.
공통 application/parser/adapter/gold/scorer를 변경하지 않았고 기존395개 회귀를 반복하지 않았다.

`integrity.json`은 이 보관본의 파일별 hash 및 원래 checkout 경로를 기록한다.
Source의 실행 경로는 `/home/a202192020/NeuroBuild_v2/var/...`에 고정되어 있다.
재현 시 해당 원래 경로에 복원하고 기존 `runtime/native/a100-llama-f072/` build 정의와
공식 고정 manifest를 사용한다. 새 CPU TU는 기존194개 static object/library를 재사용했다.
Executable/object/weight/32MB tokenizer/환경은 여기 포함하지 않고 각 proof의 hash로 식별한다.
이미 완료한 검사를 정상 재개 과정에서 자동 반복하지 않는다.
