# GLM-4.7-Flash CPU 계약 준비

현재 상태는 **정의 준비 완료 / 실행 전**이다. 이 폴더를 만들면서 tokenizer encode, Jinja render, C++ compile, native 실행, GGUF 접근, 평가 입력 읽기, HTTP/GPU/model 호출을 수행하지 않았다. 실제 PASS 증거는 아직 없다.

원본 모델은 `zai-org/GLM-4.7-Flash@7dd20894a642a0aa287e9827cb1a1f7f91386b67`, 후보 GGUF는 `ggml-org/GLM-4.7-Flash-GGUF@7559e96b7e324ab405897dc2b91492b0f376ad4a`다. 원본 template 3120 B의 SHA256은 `d63ad536c3c81880043e22ec7fd08db42b4d8fb7c89c7138bc562bfa25281375`이며 pinned llama.cpp `f072b103714dfa1eee531f80b24512faf38e3dd2`의 GLM template와 바이트가 같다. 실제 native render가 같다는 뜻은 아니다. Override와 다른 후보의 NFC-off reference는 사용하지 않는다.

`prepare_tokenizer.py`는 별도 승인 후 공식 tokenizer JSON만 기존 `.conda-vllm`의 tokenizers로 읽어 공개 20개 문자열의 ID와 raw byte roundtrip을 기록한다. 원본 normalizer는 null이다. 36개 added literal의 converter encode/decode 가정도 별도 count로 기록하며, 실패 사례를 삭제하거나 입력을 정규화하지 않는다. 원본 JSON과 공개 설계 파일은 `../glm47-flash-candidate-metadata/`의 고정 파일이다.

`build.py`는 이전 CPU static inventory 194개 / 66,339,126 B / SHA256 `b16b4bdbac76fe000c4c3d00553b43b6ee8a81115438f06ee7a67c7163cd0e76`를 실행 시 재확인한다. 새 `validator.cpp` 한 파일만 기존 compiler/link flags로 컴파일하고 링크한다. 기존 native source, 194개 object/archive, 원래 CPU binary는 전후 hash로 보존한다. CUDA OFF 설정과 CPU ELF dependencies를 확인하며 binary는 build 단계에서 실행하지 않는다. 기존 bounded guardian을 재사용하고 각 단계 600초, 새 파일 할당 512 MiB, 디스크 reserve 20 GiB로 제한한다.

`public_check.py`는 실제 client의 GLM profile을 fake opener로 잡아 원래 system과 공개 user JSON 전체를 확인한다. `render_official.py`가 공식 Jinja2로 20개 공개 role/history/tools/empty/thinking matrix를 렌더한 결과는 pipe 안에서만 native와 비교한다. Generation2 공개 예제 7개를 포함한 10 accept / 20 reject schema corpus, native plain/fenced grammar 및 byte-exact final JSON, synthetic thought 분리와 도구·미완료 출력 거절을 각각 검증하도록 준비했다. Native grammar가 fence를 허용하는 것과 application이 inline fence를 거절하는 것은 별개다. 기존 prompt/schema/parser/client의 문자열 repair는 없다.

선택된 profile은 `glm47_flash_nonthinking_llama_cpp`이며 T1 / P0.95는 공식 일반 benchmark 값이다. K0, minP0, presence0, frequency0, repeat1, repeat window0, seed42와 sampler 순서 `temperature, top_k, top_p, min_p`는 프로젝트의 명시적 중립 선택이다. Korean nonthinking 품질 또는 공식 benchmark와의 동등성을 주장하지 않는다.

다음 명령은 **준비된 실행 인터페이스**이며 이 문서 작성 시 실행하지 않았다. 프로젝트 root와 기존 환경을 사용하고 설치하지 않는다.

```sh
CUDA_VISIBLE_DEVICES='' .conda-vllm/bin/python var/research/native-glm47-contract/prepare_tokenizer.py
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-glm47-contract/build.py
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-glm47-contract/public_check.py
```

새 출력은 각각 `official-tokenizer-fixture.json`, `build.json`/`build.log`/새 object와 binary, `public-proof.json`이다. 기존 출력이 있으면 덮어쓰지 않는다. 최초 실패도 보존한 뒤 원인에 따라 별도 버전을 만든다. 성공 여부와 관계없이 public native receipt는 단계·수치·hash만 남기며 stderr/실제 reasoning body는 보존하지 않는다. CORE0와 parent-death/own process-group cleanup을 적용한다.

CPP의 optional vocabulary 분기는 아직 실행하지 않는다. 별도 wrapper가 실제 full-file SHA와 승인된 header를 확인한 뒤에만 GGUF 경로를 전달해야 한다. 이 분기는 empty devices, GPU layers0, vocab_only, no_alloc, LOAD_MODE_NONE, MTP false이며 backend/context/tensor/decode를 생성하지 않는다. 실제 vocab 20 ID/raw parity, model-aware full template, 3 EOG, grammar per-token, 공개 space 1-token과 공개 입력 길이를 검사한다. 현재 actual header/ftype/dtypes는 가정하지 않으며 wrapper가 없으므로 후단 실행 인터페이스도 아직 공개하지 않는다. 기존 200개 입력 및 미사용 holdout 80개는 이 정의에 포함하지 않았다.

`preparation.json`은 AST/source pin 점검의 준비 영수증일 뿐 실행 증거가 아니다. `integrity.json`은 이 폴더 정의의 SHA256과 재현에 필요한 외부 정의/메타데이터 경로를 기록한다. 절대 경로는 이 A100 프로젝트 기준이므로 다른 위치에서는 기존 build 정의 전체의 경로와 pinned receipt를 일관되게 재생성해야 한다. 바이너리나 가상환경을 복사해 재현했다고 주장하지 않는다.
