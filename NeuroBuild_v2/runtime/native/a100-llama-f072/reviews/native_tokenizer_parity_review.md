# Qwen3.8 GGUF tokenizer의 공개 CPU 비교

공식 HF tokenizer와 고정 native runtime의 **정확한 token ID 일치는 19/20으로 실패했다**. 실패 fixture는 0-based index11이며 원문에 Unicode 결합 문자가 있다. 원래 fixture SHA `79c4448b7ee949add0a80e8a7f0fc0d73575aaf01ff6e52beb3cfae8434ea1bd`는 변경하지 않았다. 실패를 제외하거나 PASS로 바꾸지 않았다.

## 실제 관측

| 공개20개 비교 | Token ID 일치 | encode→decode 원문 bytes 일치 |
|---|---:|---:|
| Native vs 공식 HF reference | 19/20, index11 불일치 | native20/20, HF19/20 |
| Native vs 별도 HF `normalizer=None` 진단 reference | 20/20 | native20/20, 파생 reference20/20 |

Index11은 native12 tokens, 공식 HF11 tokens다. HF JSON은 `normalizer={"type":"NFC"}`이며 같은 문자열의 NFC만 끈 별도 in-memory tokenizer가 native의 ID들과 일치한다. 원본20개 문자열과 순서, 모든 나머지 tokenizer 설정을 유지했다. 파생 fixture는 `9658eb53fae81adee1b775b45f796f3484db69aea41e04a020765fa05d770514`이며 공식 HF 동등성 증거가 아니다.

Native preidentifier는 실제 GGUF header의 string length/SHA로 `qwen35`를 확인했다. 모델 vocab type은 `gpt2`다. Pinned source `src/llama-vocab.cpp:392`의 QWEN35 regex는 combining mark를 포함하고 HF regex와 같은 분할 의도를 갖지만, BPE 경로 `:3479–3513`와 `:616`는 raw text를 regex/byte-BPE에 전달하며 NFC 합성을 수행하지 않는다. `unicode.cpp`의 NFD 함수는 이 BPE 경로에서 사용되지 않는다. 잘못된 GGUF preidentifier나 손상된 weight를 원인으로 볼 증거는 없다.

Native가 원문 bytes를 손실한 결과가 아니다. 이20개에서 **HF는 NFC로 입력을 바꾸고 native는 원문을 유지하는 tokenizer 동작 차이**다. 나머지 Unicode 입력 전체에 대한 일치를 증명한 것은 아니며, 모델 학습 분포와 token sequence가 달라져 품질에 영향을 줄 가능성은 실제 inference 전 미확인이다.

## 경계와 증거

- V2 원래 binary `142e5ed957ced9b83a4389d77d79cdd518c79859bae24f2988913be914e0d32e`와 CPP/build/public proof는 `var/research/native-contract-history/v2/`에 보존했다. V3 숫자 stage 진단 build도 `.../v3/`에 보존했다. Binary payload는 ignored var에만 있고 추적 archive에는 넣지 않는다.
- V4 helper는 모든20개 token 비교를 관측한 뒤 **하나라도 다르면 여전히 FAIL**한다. 성공 집합을 완화하지 않았고 native 원문 roundtrip도 필수로 추가했다. 실패 출력에는 stage/check-line, 개수, mismatch bitmask, roundtrip boolean만 있으며 token/입력/exception 본문은 없다. 성공 keyset은 기존과 같다.
- Build V3/V4는 같은 CPU tree의 validator target만 compile했고 upstream194 object/static-library inventory, 3,607 source blob, cache/compile commands와 이전 report/log가 불변임을 확인했다. ELF dependency에 CUDA가 없고 empty CUDA/core0/own-child parent-death 보호로 공개 probe만 실행했다.
- `var/research/native-vocab-public-probe-v4.json`: 공식 HF20개 FAIL, mismatch mask2048/index11, stderr0.
- `var/research/native-vocab-public-probe-v4-raw-diagnostic.json`: 별도 raw reference20개 진단 PASS, 공개 grammar10accept/20reject와 actual vocab grammar/EOG PASS. 공개 request1개는2143 input+768 output=2911/4096.
- `var/research/prepare_native_raw_tokenizer_diagnostic.py`: metadata tokenizer NFC만 메모리에서 제거한다. Metadata JSON, 원래 fixture, application source/quote/parser는 변경하지 않는다. `probe_native_public_vocab.py`의 `--reference raw-diagnostic`은 별도 fixture/보고서에 명시된다.

## 다음 판단의 제약

공식 HF tokenizer equivalence는 계속 FAIL로 남는다. Helper만 입력을 NFC로 바꾸거나 reference를 몰래 교체해서 PASS시키는 방법은 실제 server를 검증하지 못한다. Official-equivalent runtime이 필요하다면 native tokenizer의 정규화 지원을 포함하는 새 고정 source/runtime을 별도 검토·검증해야 하며, weight 수정이나 source quote 사후 보정으로 대체하지 않는다.

Root가 raw-Unicode GGUF runtime variant를 별도 후보로 선택한다면 공식 HF와의 차이를 명시하고 실제 native context 측정과 기존 strict quote/parser/schema/semantic/rawFP/unsafe gate를 그대로 적용해야 한다. 이 문서는 후보 채택이나 품질 PASS가 아니다. 본 작업의 model inference/GPU/network 호출 및 v2/exposed 입력 열람은 모두0이다.
