# EXAONE CPU contract 준비 범위

기존 Qwen/Gemma source·binary·receipt·실패 결과는 바꾸지 않는다. 기존 pinned f072 CPU static
objects/archives 194개, 66,339,126B, inventory SHA b16b4bdbac76fe000c4c3d00553b43b6ee8a81115438f06ee7a67c7163cd0e76만 재사용한다.
새 TU compile/link를 새 폴더에 기록하고 CPU-only CMake cache/compile flags/source tree 및 기존 binary hash를 전후 확인한다.
새 executable의 ELF NEEDED allowlist와 RPATH 부재를 확인한 뒤에만 실행한다. Upstream source/full build는 변경하지 않는다.

1. 새 공개 문자열20개로 pinned 공식 tokenizer ID와 raw 원문 왕복을 기록한다. NFC 대조는 별도 진단이며 입력 수정이나 parity 완화가 아니다.
2. 새 CPP는 template/schema/stdin public bundle만 받는다. GGUF 인자와 vocab/model loading branch는 이번 버전에 포함하지 않는다.
3. 실제 native OpenAI request parser → 공식 Jinja template → generic PEG parser/GBNF 경로를 검사한다.
   현재 schema7예시+synthetic3 accept,20reject를 사용하며 dataset/model output은 읽지 않는다.
   generic parser가 허용하는 plain/fenced JSON 모두에서 final content가 같은 JSON bytes인지 검사한다.
   malformed/tool/unfinished think는 거절하고 인공 공개 thought는 final content와 분리되며 thought 본문을 receipt에 남기지 않는다.
4. Production EXAONE profile 확정 후 fake opener로 실제 payload를 capture한다. T.6/P.95/K20/presence1.5,
   minP0/frequency0/repeat1/window64/seed42, samplers penalties→top_k→top_p→min_p→temperature, thinking=false를 native sampling schema에 대조한다.
5. CORE=0, empty CUDA, sanitized env, own process group/PDEATHSIG/timeout을 유지한다.
   모델 weights, native tensor load/context/backend initialization, HTTP/GPU/model inference는 없다.

이 결과는 metadata-only grammar/transport의 공개 검사다. 실제 GGUF 내부 tokenizer/template와
metadata의 동일성, vocab token/EOG 제약, private 입력 context, CUDA kernel/VRAM 또는 품질은 증명하지 않는다.
GGUF/header가 없는 상태에서 그 후단 검사를 실행하지 않는다. 기존 prompt/schema/parser와 generation prompt 자체는 수정하지 않는다.
