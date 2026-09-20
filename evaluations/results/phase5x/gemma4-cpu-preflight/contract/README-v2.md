# Gemma 4 CPU preflight: model-aware BOS correction and measured results

새 Gemma GGUF에 대한 CPU 검증을 완료했다. Native 공개 tokenizer ID 일치/원문 roundtrip 20/20 및 입력 200개의 길이 한도는 PASS이다. **별도 literal U+2581 원문 roundtrip은 FAIL**이며 이를 없애거나 입력을 보정하지 않았다. 모델 추론/HTTP/GPU 실행·tensor/context 생성은 0회다. 이 문서는 semantic 품질·VRAM·모델 선정 PASS가 아니다.

## 최초 실패와 수정 범위

원래 v1의 metadata-only template grammar/parser 공개 검사는 PASS였지만, 첫 GGUF vocab 검사에서는 stage12/line331의 prompt raw equality가 실패했다. `public-vocab-proof.json` SHA `162136e4f1280f11262f5305381056345cab1ba04d904806127efec0125cdf32`를 보존했다. v1 17개 원본 파일/CPP/object/binary/build/receipt의 exact copy와 integrity는 `v1-preserved/`에 있고 원래 경로의 bytes도 불변이다.

Pinned `common/chat.cpp`는 실제 model의 `add_bos=true`이면 template 선두 `<bos>` 5 B를 제거한다. Native server의 tokenizer가 `add_special=true`로 BOS를 추가한다. 모델 없는 template 초기화는 이 flag가 없으므로 선두 literal BOS를 남긴다. v2는 다음 조건을 모두 요구한다.

- GGUF `add_bos=true`, `add_eos=false`, BOS ID2 및 piece `<bos>`.
- metadata prompt가 정확히 `<bos>` + actual model-aware prompt와 동일.
- `tokenize(metadata_prompt,false,true)`와 `tokenize(actual_prompt,true,true)`의 **전체 token ID 배열 동일**.
- Embedded template, JSON grammar, generation prompt는 기존 byte equality 유지.

이는 native template/tokenizer의 BOS 처리를 검증하는 수정이며 사용자 원문·JSON·tokenizer normalizer를 보정하지 않는다. `validator_v2.cpp`만 새로 컴파일하고 기존 CPU archive 194개/66,339,126 B는 재빌드하지 않았다. Architecture 독립 source review PASS 후 실행했다.

## 실제 증거

| Artifact | 관측 |
|---|---|
| `build-v2.json` | 새 TU/link PASS, CPU ELF allowlist, GPU backend OFF, 194개 기존 파일 및 Qwen binary 불변 |
| `public-vocab-v2-proof.json` | 공개30 schema/native-token grammar: 10 수락·20 거절/EOG 확인, fence 오류4 거절, 합성 thought 분리1, final JSON byte 동일10 |
| `tokenizer-fixture.json` | 새로운 Gemma 공개20: 이전 Qwen17개 일반 문자열 유지 + marker3개 변경; 공식 normalizer 변경 없음 |
| `public-vocab-v2-proof.json` | 공식/native ID20/20 + native 원문 roundtrip20/20; 공개 space1 token ID236743 및 roundtrip 확인 |
| `vocab-context-v2-proof.json` | Exposed120 및 V2 length80를 실제 client fake opener → native model-aware template → GGUF vocab tokenizer로 검사; source/gold/output은 저장하지 않음 |
| `final-cpu-proof.json` | 위 범위의 aggregate PASS. Protocol/profile/source/header/template/tokenizer 및 code5개 SHA 연결 |
| `normalization-witness-proof.json` | 별도 literal U+2581에서 공식/native ID 일치지만 native 원문 roundtrip FAIL. Quality/20-case 결과와 분리 |

Context 출력 cap은 768, 전체 한도는 4096이다.

| 입력 | Count | Min input | Max input | Max input + output |
|---|---:|---:|---:|---:|
| Exposed regression | 120 | 2339 | 2646 | 3414 |
| V2 length only | 80 | 2360 | 2593 | 3361 |

`native_request_prompt_bytes=9171`은 모델 없는 metadata render 길이이고, 실제 model-aware render는 BOS 5 B를 제거한다. Context token 수는 실제 model-aware prompt와 add_special 동작으로 측정했다.

## Normalization 한계

추가 공개 witness의 공식 tokenizer encode/decode에서 literal U+2581이 공백으로 복원되는 현상을 먼저 기록했다. 같은 원문과 **변경 없는 공식 token IDs**를 native에도 넣었다. 고정된 C++의 한 사례 흐름에서 ID mismatch guard가 통과하고 바로 다음 raw-roundtrip guard(stage101/line400)가 실패했다. 따라서 ID 일치와 원문 roundtrip 실패를 구분할 수 있다. Native decode 문자열 자체는 출력·보존하지 않았으므로 실패 보고는 raw original과의 비동일성을 입증하며 모든 변환 byte 내용을 관측했다고 주장하지 않는다.

공개20 PASS를 모든 Unicode의 tokenizer 동등성이나 원문 보존 보장으로 확대할 수 없다. Application input/output normalize/strip/repair는 0이다. Aggregate `a27cd1f7a37899873aac346404e1cea8d0805c8db899f03eba6e3d7d7340029d`를 뒤늦게 덮어쓰지 않고 이 witness를 별도 receipt로 연결한다. Root runtime consumer의 `cpu_provenance()`는 aggregate에 한 번 호출되어 PASS했으며 HTTP/GPU/model 실행은 없었다.

## 재현 정의

모든 경로와 compiler는 A100의 이 checkout에 고정된다. 기존 CPU source/build와 역사적 proof가 필요하고 새 결과를 기존 결과 위에 덮어쓰지 않는다. 재현에는 새 checkout 또는 결과가 없는 출력 경로, 같은 fixed source/build flags 및 provenance를 사용한다. 실제 수행한 명령은 다음과 같다.

```bash
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-gemma4-contract/build_v2.py
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-gemma4-contract/test_helpers_v2.py
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-gemma4-contract/vocab_check_v2.py --header var/reports/gemma4-gguf-header-v2.json --header-sha d867a3300b2a93534fb1b480e8e42b30321c894aaec05b5729a529e848817756
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-gemma4-contract/context_check_v2.py --header var/reports/gemma4-gguf-header-v2.json --header-sha d867a3300b2a93534fb1b480e8e42b30321c894aaec05b5729a529e848817756 --run-length-only-200
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-gemma4-contract/normalization_witness_v2.py --header var/reports/gemma4-gguf-header-v2.json --header-sha d867a3300b2a93534fb1b480e8e42b30321c894aaec05b5729a529e848817756
```

권한/지시 없이 위 명령을 자동 반복하지 않는다. 이미 완료한125회 평가/재생은 수행하지 않았다. 체크 실행은 stdlib parent-death/same child group/timeout/core0/empty CUDA 및 CPU ELF 확인 하에서 이뤄졌으며 raw reasoning을 저장하지 않았다.
