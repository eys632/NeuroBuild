# Prefill64 최대 문맥 자원 관측

고정3328token 입력+768sampled 출력/4095cached/no-shift boundary의 resource-only probe PASS다.
실제 input/output timing과 guard lifetime aggregate는 report에 있다. Generated body는 서버의
response_fields로 제외했고 source·token·reasoning 본문은 저장하지 않았다. 이 관측은 모델
품질, 모든 입력의 peak 상한, per-process peak 또는 RTX 성공을 뜻하지 않는다.
