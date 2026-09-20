# Gemma 4 31B QAT CPU contract preflight

현재 실제 완료 범위는 새 C++ translation unit의 CPU 전용 compile/link 및 공개 template/grammar/parser 검증이다. GGUF vocab 로드, 200개 입력 길이 검증, GPU 실행, HTTP, 모델 생성, 품질 평가는 아직 실행하지 않았다. 기존 Qwen C++/binary/build/proof는 변경하지 않았다.

- Native source: `f072b103714dfa1eee531f80b24512faf38e3dd2`.
- 공식 GGUF: `google/gemma-4-31B-it-qat-q4_0-gguf` / `59dde24573e7e61570dba08b18a2e1fe246955ed`.
- QAT metadata: `google/gemma-4-31B-it-qat-q4_0-unquantized` / `1e4d8beecacb8b7590c1d8bedd7335f687bf311f`. GGUF 변환 시점의 정확한 원본 revision은 게시되지 않았다.
- `build.py`는 기존 CPU build의 194개 object/archive, 66,339,126 B, inventory SHA `b16b4bdbac76fe000c4c3d00553b43b6ee8a81115438f06ee7a67c7163cd0e76`와 원본 source 전체를 검사한다. 기존 compile/link flags를 그대로 사용해 새 파일만 GCC 9.5로 빌드했다. 재구성/CMake 실행/상위 라이브러리 재빌드/설치/다운로드는 없다.
- `build.json`: compile/link PASS, CUDA/모든 GPU backend OFF, static libs, ELF 의존성 allowlist 확인, RPATH 없음. 원래 Qwen object/archive/CPP/binary 변경 없음.
- `public-proof.json`: 공개 JSON 10개 수락/20개 거절, 잘못된 fence/tool/미완료 thought 4개 거절, 합성 thought 분리 1개. Native parser가 fence를 제거한 **최종 JSON 10개는 원본 byte 그대로**이다. 공개 fixture는 grammar/transport 경계를 시험하며 semantic 품질이나 backend grounding PASS가 아니다.
- 실제 Gemma generation prefill은 41 B이다. Eager grammar(`grammar_lazy=false`)이며 native가 기록한 tool trigger 메타데이터 1개를 허용한다. 이 값은 lazy/tool 실행 허용을 뜻하지 않는다.
- Native `server_schema`로 T=1.0/P=.95/K=64/minP=0/presence=0/frequency=0/repeat=1/repeat_last_n=0/seed42와 sampler 순서 `temperature,top_k,top_p,min_p`를 확인했다. T/P/K는 공식 권고, 나머지는 별도 실험의 neutral 설정이다.

## 공개 tokenizer fixture

`tokenizer-fixture.json`은 공식 QAT tokenizer JSON(`cc8d3a0c…bfe0f`)에서 변경 없이 만든 **새 Gemma corpus**다. 이전 Qwen 20개 중 일반 문자열 17개를 유지하고 special-marker 문자열 3개만 Gemma marker로 바꿨다. 이전 Qwen corpus와 동일하다고 주장하지 않는다. 20개 text list compact JSON SHA는 `2e6ccfb167702df0e40d51d4b7b18f8b982d443571383546ee9d6e07f78071d6`이다.

공식 HF encode/decode 원문 roundtrip은 20/20이다. 별도의 공개 `literal U+2581` witness는 공식 tokenizer 자체에서 해당 문자가 ASCII space로 복원되어 원문 roundtrip FAIL이다. 이 witness를 없애거나 문자열을 normalize/strip/repair하지 않았다. 이는 전체 Unicode 원문 보존을 보장할 수 없다는 실제 한계이며, native GGUF에서도 별도로 확인해야 한다. 공개 20개 PASS는 모든 입력의 tokenizer 동등성이나 semantic 정확성을 입증하지 않는다.

## 재현과 다음 검사

모든 경로는 이 A100 checkout `/home/a202192020/NeuroBuild_v2`에 고정되어 있다. 기존 CPU source/build와 두 Python 환경을 먼저 재현해야 한다. 이미 존재하는 결과 파일은 x-mode로 거절하므로 이전 proof를 덮어쓰지 않는다. 새 checkout/빈 후보 출력 경로에서 아래 정의를 사용한다.

```bash
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-gemma4-contract/build.py
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-gemma4-contract/public_check.py
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false .conda-vllm/bin/python var/research/native-gemma4-contract/prepare_tokenizer.py
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-gemma4-contract/test_helpers.py
```

`vocab_check.py --header <project-relative proof> --header-sha <SHA>`와 `context_check.py ... --run-length-only-200`는 **header PASS 및 root 실행 지시 이후** 사용할 준비만 했다. 전자는 공개 30+20 fixture/입력 1개, 후자는 exposed120과 V2의 input/context만 메모리에서 실제 client fake opener와 native template/tokenizer로 처리한다. Gold 점수/모델 출력은 읽지 않는다. 결과에는 split별 count/min/max 및 hash만 저장한다. Native는 `vocab_only/no_alloc/LOAD_MODE_NONE/empty devices`로 열며 context/tensor/backend 실행을 하지 않는다.

Native stderr는 C++에서 count-only로 폐기하고 warning이 있으면 실패한다. RLIMIT_CORE=0, 빈 CUDA mask, 단일 CPU thread 환경, owned child group/parent-death 및 timeout을 사용한다. 모델/사용자 thought 본문을 저장하지 않는다. 공개 합성 thought fixture는 parser 경계만 시험한다.
