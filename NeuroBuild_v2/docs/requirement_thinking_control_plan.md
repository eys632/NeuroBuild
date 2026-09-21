# 같은32B의 내부 thinking 제한 비교

Facts3.0은 raw 분류115/120이었지만 의미 정확도95/120, raw READY 오판3,
잘못 수용한 READY1로 실패했다. 중복된 facts 인용은 별도의 오류를 만들었다.
검사를 삭제하면 잘못 수용한 출력이 늘므로 현재 검증을 완화하지 않는다.
[원본과 독립 검토](reviews/phase5x_generation3_32b_exposed_review.md)를 보존한다.

다음 가설은 외부 facts 표현을 더 늘리는 대신 **같은32B가 내부 thinking을 사용하고
기존2.0 원문 인용 계약을 반환하는 한 번의 제한 비교**다. 기존32B single2.0은
원문 복사와 parser120/120을 통과했으므로 이 경계를 다시 사용한다.
이는 성공 증거가 아니며 Phase5.x 완료나 모델 채택을 뜻하지 않는다.

| 항목 | 고정할 조건 |
|---|---|
| 모델 | Qwen/Qwen3-32B-AWQ, revision0499c3ac83fdef8810b907a23894ba91e95eddd8 |
| 호출 | single, 사례당1회, retry/repair/fallback 없음 |
| 외부 계약 | generation2.0 branch schema → 기존2.0 adapter → canonical1.0 parser |
| Prompt | 기존generation2/v2의 정책·예시 보존. 첫 출력 지시만 최종 content에 적용됨을 명시한 별도 파일 |
| Thinking | enable_thinking=true, A100 V0의 명시 deepseek_r1 parser |
| Sampling | 기존 qwen3_thinking_awq: T0.6/P0.95/K20/minP0/presence1.5/frequency0/repetition1/seed42 |
| 출력·시간 | 전체 completion1024 tokens, timeout120초. Reasoning과 최종 JSON이 이 예산을 공유 |
| Runtime | GPU3 only, FP16/AWQMarlin, TP1/eager/context4096/seq1/KV256, fraction.60/.60 |
| 메모리 | whole peak 추정25600MiB, allowance0, fresh preflight와 실행 중 free floor 감시 |
| 자료·gate | exposed120×1+warmup5; schema120, semantic≥114, rawFP0/58, unsafe0/120 |

기존prompt의 thinking template를 실제 로컬32B tokenizer로 CPU 측정한 최대 입력은2915다.
1024 cap을 더하면3939/4096이며,2048 cap은4963으로 범위를 넘는다.
최종 prompt 파일의 정확한 bytes로 문맥·schema·runtime mode를 다시 검증하고 동결한다.
Context/KV 확대, prompt 예시 추가·축약, 새 dependency/model 다운로드는 이 비교에 포함하지 않는다.

이전14B thinking 실행에서 completion1241 사례가 있었으므로1024 cap은 잘릴 위험이 있다.
잘림·timeout·최종 JSON 부재도 원래 분모의 실패로 보존한다. 이를 non-READY 성공으로
대체하지 않고 같은 후보에서 재시도하거나 예산을 늘리지 않는다. Raw decision은 기존처럼
최종 JSON을 읽은 직후 backend 검증 전에 계수하며, 관측되지 않은 decision은 unknown이다.
Reasoning 원문은 열람·로그·평가 artifact에 저장하지 않는다. 토큰 수와 종료 상태만 기록한다.

Thinking, sampling, 출력 지시의 범위와 예산이 함께 바뀌므로 순수 thinking의 인과 효과라고
주장하지 않는다. 1024 예산에서의 실패가 모든 reasoning 설정의 한계를 증명하지도 않는다.
실제 호출 전 CPU/독립 검토, 새 runtime 기동·loopback 확인, freeze/commit/push를 수행한다.
성공해도 별도 동결한 exposed120×3 및 v2 평가가 남는다. 실패하면 결과를 보존하고
다음 접근을 다시 검토한다. 같은 facts 문구나 사례별 예시를 이어 붙이는 반복으로 넘어가지 않는다.

V2는 모델 호출0이지만 root의 일부 입력/gold 노출 이력을 유지한다.
이번 후보 변경은 그 사건 이후이며 완전 맹검이라고 부르지 않는다.
Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED, RTX5090은 PREDICTED_UNVERIFIED다.
