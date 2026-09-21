# GLM-4.7-Flash native CPU vocabulary·길이 증거

공식 공개 tokenizer 20개의 native ID와 원문 roundtrip이 모두 일치했고, 기존 노출 입력 200개에서 전체 system/user prompt 바이트와 native token 길이 검증이 통과했다. 이는 CPU 계약 검사이며 모델 품질이나 GPU 실행의 증거가 아니다.

| 검사 | 입력 수 | 최대 입력 tokens | 출력 768 포함 |
|---|---:|---:|---:|
| 공개 vocabulary용 요청 | 1 | 2,827 | 3,595 |
| exposed120 | 120 | 3,257 | 4,025 |
| 이미 노출된 v2_length80 | 80 | 3,164 | 3,932 |

[공개 vocabulary proof](vocabulary/public-vocab-proof.json)는 원본 공식20 ID·native raw roundtrip·reference ID의 raw roundtrip 20/20, 원본 embedded template와 model-aware full prompt, token grammar 20 accept/40 reject 및 3 EOG를 묶는다. 공개 공백 token은 ID220이며 1 token/raw roundtrip을 확인했다. 원본 normalizer는 null이고 application 입력·출력 정규화나 파생 reference를 적용하지 않았다. 이 20개 결과를 모든 Unicode에 대한 보장으로 일반화하지 않는다.

[Context proof](context/vocab-context-proof.json)는 실제 vocabulary PASS를 먼저 검증한 후 노출120과 이미 노출된 기존 V2 80의 길이만 처리했다. 새 context TU는 actual client request의 원래 system/user 전체와 native template bytes, generation prefix, schema grammar, sampler, native prompt roundtrip을 확인했다. 원문·gold·token ID 배열은 이 archive에 없다. Gold를 채점하거나 quality/replay를 실행하지 않았으며, 미사용 새 holdout은 접근하지 않았다. 공개20 tokenizer 검사는 context 단계에서 반복하지 않았다.

두 단계 모두 CPU-only ELF를 확인한 binary와 empty CUDA, CORE0, own-child cleanup을 사용했다. GGUF는 vocabulary-only/no_alloc/LOAD_MODE_NONE/empty devices/GPU layers0/MTP false로 열었다. Model context·backend init·weight tensor decoding·model inference·HTTP·GPU 호출은 없었다. 파일 전체 SHA를 읽어 확인한 행위는 tensor 추론과 구분한다.

공식20 fixture, native v3 public grammar/render proof, 최초 두 실패 및 원본 template/header는 기존 [preparation public archive](../glm47-flash-preparation/public_cpu/README_ARCHIVE.md)와 [header proof](../glm47-flash-preparation/header/glm47-flash-gguf-header.json)에 보존돼 있다. 첫 실패는 다른 prefix에 대한 잘못된 positive 기대였고, 두 번째는 configured prefix에서도 optional reasoning을 금지해야 한다는 잘못된 negative 기대였다. v3는 실제 prefix에서 native parser가 JSON을 그대로 final content에, reasoning을 별도 필드에 두는 경계를 검증했다. 실제 모델이 reasoning을 생성했다고 주장하지 않는다. 이전 FAIL 파일은 수정하지 않았다.

[manifest.json](manifest.json)은 이 archive의 각 파일을 원래 ignored 경로·byte 수·SHA256에 연결한다. `.log`와 stderr는 `.log.txt` 이름으로 **원본 바이트 그대로** 복사했다. `context_preparation.json`의 wrapper SHA `6fda606b…6998d`는 실제 proof pin을 채우기 전 이력이다. 포함된 최종 `context_check.py` SHA `cf271201…b2d9`는 root가 실제 vocab/build/binary의 세 pin만 채운 버전이며, 실제 context proof가 이 최종 SHA를 참조한다. 준비 영수증을 실제 실행 결과로 바꾸지 않았다.

[Context build proof](context/context-build.json)는 기존 CPU inventory 194개 / 66,339,126 B의 전후 불변과 새 TU만의 compile/link 및 CPU ELF를 기록한다. 바이너리·object·static library·가상환경·weight·대형 tokenizer JSON은 넣지 않았다. 재현 시 이 정의를 manifest의 원래 `var/research/native-glm47-contract/` 경로에 복원하고, 기존 [public source closure](../glm47-flash-preparation/public_cpu/source-closure.json)와 [metadata provenance](../glm47-flash-preparation/metadata/provenance.json)의 pinned 원본을 준비해야 한다. 절대 경로와 기존 A100 toolchain/cache 정의에 의존하므로 복사된 Python 파일만 독립 실행 가능한 패키지라고 주장하지 않는다.

실제 실행 명령은 프로젝트 root의 기존 `.conda`에서 다음과 같았다. 현재 증거를 보존하기 위한 기록이며 동일 검사를 다시 실행하라는 지시는 아니다.

```sh
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-glm47-contract/vocab_check.py
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-glm47-contract/build_context.py
CUDA_VISIBLE_DEVICES='' .conda/bin/python var/research/native-glm47-contract/context_check.py
```

[Independent preparation-index review](review/glm47-preparation-index-independent-review.json)는 이전 preparation index 검토 영수증이다. 이를 후속 context 실행의 별도 독립 재생으로 표현하지 않는다. Archive 작업에서는 어떤 검증이나 모델 호출도 재실행하지 않았다. Runtime 최종 aggregate와 GPU/품질 결과는 이 archive의 범위 밖이다.
