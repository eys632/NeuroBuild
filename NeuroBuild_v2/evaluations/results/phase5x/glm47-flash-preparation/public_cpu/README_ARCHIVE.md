# GLM 실제 공개 CPU 계약 기록

첫 public 검사 두 번은 서로 다른 helper 기대값 오류로 FAIL했다. 원본 정의·빌드·실패는 그대로 보존한다.
v3는 동일한 configured prefix에서 native가 optional reasoning을 별도 필드로 분리하고 final JSON을 바꾸지 않음을 실제로 확인해 PASS했다.
준비 문서의 NOT_RUN은 각 문서 작성 당시 상태다. 실제 결과는 public-proof-v3.json과 build-v3.json이다.

원본 template20/system/user/full prompt, sampling, schema10accept/20reject, plain/fenced final20,
미완료·도구 출력 거절4, 공개 synthetic reasoning 분리1을 검사했다. 다른 모델/다른 runtime mode/품질 평가가 아니다.
공식 HF 공개20 원문 왕복은20/20이다. 실제 GGUF vocabulary token ID 비교는 이 archive 시점에 아직 실행하지 않았다.

기존194 CPU objects를 재사용했다. 바이너리·object·weight·환경은 Git에 포함하지 않는다.
빌드/CLI log는 `.txt` 확장자만 붙이고 원래 bytes를 유지했다. 외부 재사용 정의와 SHA는 source-closure.json에 연결했다.
원본 timestamp receipt를 덮어써 같은 실행처럼 만들지 않는다. 전역 환경/GPU 정책과 STATUS의 다음 gate를 따른다.
