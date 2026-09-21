# Gemma native profile 준비 증거

이 archive는 새 모델의 명시 client/evaluator profile과 공식 QAT metadata를 보존한다.
395개 실제 PostgreSQL/IfcOpenShell headless 회귀 PASS/skip0/19.339초다. GPU 추론 검증은 아니다.
기존 Qwen wire 불변과 native 모델ID/quantization/profile 혼용 거절을 포함한다.

`qat_reference/`는 공식 QAT unquantized metadata의 exact bytes다. GGUF 변환의 exact source revision은
공개되지 않았고, 실제 GGUF header/template/tokenizer와의 일치는 별도 gate다.
대형tokenizer32MB와weight는 Git에서 제외했으며 재현 URL/SHA는 model provenance에 기록했다.
`APACHE-2.0.txt`는 Apache 공식 license 원문이다. 모델 repository의 LICENSE 파일로 가장하지 않는다.

두 Python helper는 검증된 이전 disk-guard/자체 child lifecycle 코드에서 후보·hash·경로를 고정한 복사본이다.
Cache 정리 원본 증거는 ../unused_32b_weight_cache_cleanup.json이다. Download helper는 실행 전
pinned build/manifest/cleanup과20GiB+512MiB reserve를 확인하고,2초마다 디스크를 감시한다.
Partial은 유지하며 원본 SHA/size 확인 후 atomic no-clobber로 게시한다.
이 archive 자체는 download 완료나 새모델 startup/품질 PASS를 뜻하지 않는다.

[계획](../../../../docs/gemma4_31b_diagnostic_plan.md),
[manifest](../../../../runtime/models/gemma4-31b-qat-q4-0.json),
[provenance](../../../../runtime/models/gemma4-31b-qat-q4-0.provenance.json).
