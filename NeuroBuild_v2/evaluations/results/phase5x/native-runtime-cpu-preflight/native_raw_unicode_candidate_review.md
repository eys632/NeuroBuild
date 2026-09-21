# Raw-Unicode GGUF runtime 후보 독립 검토

2026-09-20. 범위는 공개 tokenizer fixture/CPU proof와 고정 source의 읽기 검토다. 이 검토자는 GPU, native executable, HTTP, inference를 실행하지 않았고 private/exposed/v2 dataset 본문을 읽지 않았다. Production source, prompt, gold, schema 또는 원래 fixture도 수정하지 않았다.

**판정: 명시적으로 구분된 raw-Unicode GGUF runtime 후보로 후속 CPU context·제한된 runtime·품질 검증을 진행하는 것은 기술적으로 타당하다.** 공식 HF token ID 동등성은 계속 FAIL이며, 이를 PASS로 바꾸거나 모델 채택을 승인하는 판정은 아니다. 사용자 요구는 원문 기반 제품 계약과 고정 품질 gate이며, 모든 runtime의 HF token ID 동일성 자체는 필수 요구가 아니다. 확인된 차이를 숨기지 않고 별도 후보의 preprocessing 특성으로 고정하는 것은 source/gold/semantic gate 완화와 다르다.

## 확인한 증거

- 공식 metadata `tokenizer.json`은 `normalizer={"type":"NFC"}`이다. 고정 native source의 QWEN35 분기는 combining-mark-aware regex를 사용하지만 BPE raw fragment 경로에서 NFC 합성을 하지 않는다 (`src/llama-vocab.cpp:392,616,3479–3513`). `unicode.cpp`의 NFD 함수는 이 경로에서 호출되지 않는다. 두 경로의 정적 차이는 실제 공개 비교와 일치한다.
- 원래 공식-HF reference20개는 **19/20 ID 일치로 FAIL**, index11에서 native12/HF11 tokens다. Native encode→decode는20/20 원문을 복원하고, HF reference는19/20이다. 공개 `native-vocab-public-probe-v4.json` SHA `b537545d26a876a1496c2f85ad979330eba938f2880aae49190640b2404c63e0`에 exit1/FAIL/mismatch mask2048이 보존된다.
- 별도 파생 reference는 동일한20개 문자열·순서를 유지하고 **메모리상의 HF normalizer만 None**으로 바꾼다. 이 검토자가 두 fixture를 직접 비교해 문자열·순서20/20 동일, ID 차이 index11 하나를 확인했다. 원본 tokenizer 파일과 원래 fixture는 그대로다. Native vs 파생 reference는20/20 ID 일치·원문 roundtrip20/20이다. 이는 원인을 좁히는 진단이며 공식 HF 동등성 증거가 아니다.
- 같은 v4 CPU binary에서 actual vocab grammar10accept/20reject/EOG, embedded-vs-external template/prompt/grammar, final-content10개 exact, sampling binding과 generation-prefix41bytes 검사가 PASS다. 파생 public proof `native-vocab-public-probe-v4-raw-diagnostic.json` SHA `12a5ebeafc16969f36435d9bb9e933ba12197d01ba05e8f26df41114f4e01d2d`는 공개 request1개의 native input2143 + output768 =2911/4096도 기록한다. 이것만으로 전체 평가 입력의 context fit을 주장할 수 없다.
- GGUF 전체 파일 SHA `c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747`,851개 tensor/header/type/shape coverage, actual `qwen35` preidentifier와 embedded template는 별도 header audit에 연결된다. 잘못된 preidentifier나 weight 파일 손상이 NFC 차이의 원인이라는 증거는 없다.

## 이 후보가 허용하는 것과 허용하지 않는 것

모델이 보는 token sequence가 공식 NFC tokenizer와 일부 달라지는 **추론 구현 변형**이다. 이는 성능·품질에 영향을 줄 수 있어 inference 검증이 필요하다. 모든 Unicode에서 native와 NFC-disabled reference가 같거나, 원문을 잘 복사하거나, 더 우수하다는 결론은20개로 도출하지 않는다. Quantization/새 runtime 차이도 있으므로 이후 점수는 이 정확한 복합 후보의 결과다.

Native가 원문 bytes를 유지하는 것은 현재 exact-quote 계약과 모순되지 않는다. 하지만 이를 이유로 quote validation을 바꾸지 않는다. 원문/input·target/evidence/output에 NFC/NFKC를 적용하거나 모델 응답을 사후 복원하는 처리는 추가하지 않는다. Model이 다른 정규화 철자로 답하면 기존 parser가 그대로 판정하고 실패는 그대로 계수한다. 기존 canonical parser SHA `a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a`를 확인했다.

원래 실패 fixture/reference/proof를 삭제하거나 파생 reference로 덮어쓰지 않는다. 원래 tokenizer 동등성 gate는 여전히 FAIL이다. 앞으로의 후보 preflight가 파생 reference 검사를 요구한다면 **새 후보 기준을 사전에 명시하고 reference_kind를 구분**해야 한다. 범용 필드 `tokenizer_metadata_parity=PASS`만 떼어 공식 parity 성공처럼 기록하지 않는다.

## 다음 freeze에 필요한 연결

1. 후보 provenance에 `raw_unicode_no_nfc` 같은 명시적인 tokenizer behavior를 기록한다. Original HF tokenizer SHA, GGUF revision/file/header SHA, llama.cpp commit, 최종 CUDA binary/libs/build, CPU helper source/binary/build/proof를 모두 연결한다. Official HF parity19/20 FAIL과 별도 raw20/20 PASS를 같이 보존한다. A100 결과를 RTX로 승계하지 않는다.
2. Production HTTP messages는 변경되지 않은 원문·axis와 고정 prompt/schema를 그대로 전달한다. CPU 검증에서 **실제 native embedded template와 native tokenizer**로 이 wire를 측정한다. Exposed120 및 v2 길이80은 별도 집계하며 root에는 count/max/hash만 반환한다. Input+768≤4096, special/BOS/EOS/prefix, false-thinking/deepseek final split, eager grammar/EOG 검사가 필요하다. HF 길이를 native 길이 대신 사용하지 않는다.
3. Context proof에 `reference_kind=raw-unicode-no-nfc`와 원본/파생 fixture/proof hashes를 붙인다. 기존 공식-HF mode를 자동 fallback하지 않는다. Startup/resource helper가 새로운 mode를 받는다면 이 명시 provenance와 전체 native context PASS에 연결해야 하며, 아직 실패한 공식-HF proof를 성공처럼 받아들이면 안 된다.
4. 기존 domain/approval/revision, generation2→canonical1, schema100%, semantic≥95%, raw READY FP0, unsafe accepted0, unknown/length/timeout 실패 분모를 유지한다. Resource-only 공개 probe는 품질 점수를 생성하지 않는다. Exposed diagnostic→별도 formal→unused holdout의 기존 절차를 유지한다.
5. 실제 native startup은 CPU context gate, [자원 계획](../../docs/native_qwen38_resource_plan.md)의28GiB 예상 peak+fresh margin과 own-child guard를 만족한 뒤 root만 수행한다. Raw tokenizer variant는 weight/context/sequence/VRAM 설정을 바꾸지 않으므로 기존 자원 산술을 약화할 이유가 없다. 품질 채택 여부는 아직 미결이다.

## 문서 정합성 참고

읽은 `docs/modern_local_runtime_candidate.md`의 현재 상태는 vocab 진단 중/미실행으로 정직하게 남아 있다. 새 variant를 확정하면 이 상태와 tokenizer 차이를 갱신해야 한다. 같은 문서 하단의 “실제 GGUF header … 아직 미검증”은 위 현재 상태와 달리 오래된 문구이므로 “헤더 PASS, CUDA placement 미검증”으로 분리하는 것이 정확하다. 이 검토는 해당 문서를 편집하지 않았다.

재현 fixture: 원래 SHA `79c4448b7ee949add0a80e8a7f0fc0d73575aaf01ff6e52beb3cfae8434ea1bd`, 파생 SHA `9658eb53fae81adee1b775b45f796f3484db69aea41e04a020765fa05d770514`; upstream tokenizer SHA `0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3`; CPU v4 binary SHA `49a57a9630bd89e03940c07621d896d51efa32d502cca3d0736de48366563e5e`. 모든 gold의 AUTO-GENERATED / NOT HUMAN VERIFIED 제한은 그대로다.
