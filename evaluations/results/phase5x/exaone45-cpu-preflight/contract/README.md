# EXAONE CPU raw Unicode 계약 기록

이 보관본은 `exaone45-gguf-continue-free-raw-unicode-korean-v1`의 CPU 준비 증거다.
공식 HF token ID 동등성은 **18/20 FAIL**로 보존하며, 별도 NFC-off 진단 기준은 **20/20 PASS**다.
이는 모델 품질·GPU 실행·VRAM 검증이나 채택을 뜻하지 않는다.

| 증거 | 결과 |
|---|---|
| [공식 기준 실제 비교](public-vocab-proof.json) | IDs 18/20; 불일치 0-based 11·12; native raw 왕복 20/20 |
| [별도 raw 기준](raw-vocab-proof.json) | 같은 공개 문자열 20개에서 IDs·raw 왕복 20/20 |
| [길이 전용 검사](vocab-context-raw-proof.json) | 노출120 최대 2,122 + 768 = 2,890; 기존 V280 최대 2,088 + 768 = 2,856; 한도 4,096 |
| [최종 CPU aggregate](final-cpu-proof.json) | 공식 실패와 별도 기준 PASS, template/header/source/launcher를 각각 연결 |
| [합성 검증](raw-context-selfcheck.json) | 7개 통과; mismatch·원본 실패·공식 성공 오라벨·분모·context 초과 거절 |

공식 tokenizer·fixture·GGUF·입출력은 수정하지 않았다. NFC-off는 별도 메모리 내 진단 reference에만 적용한다.
20개 공개 문자열의 일치가 전체 Unicode 보존을 보장하지 않는다. 길이 검사에는 gold 평가나 모델 출력이 없다.
새 미사용 holdout은 읽지 않았다.

공식 template의 nested `continue`가 pinned native Jinja에서 system 출력을 잃는 실패와, 단일 `if/elif`
등가변환 후 공식 Jinja2와 native 렌더링 18개가 바이트 단위로 일치한 증거는
[기존 template/header 보관본](../../exaone45-template-header-preflight/README.md)에 그대로 있다.
그 보관본의 v1–v3 source/receipt와 공식 fixture는 중복 복사하지 않았다.
최종 vocab 검사에서도 embedded 원본과 effective override를 분리하고 전체 system/user 렌더링을 확인했다.
Native grammar는 plain/fenced JSON을 허용하며 native PEG가 반환한 final JSON bytes를 검사한다.
Application의 inline fence 거절, strict quote 검사, 입력·응답 수리 금지는 그대로다.

여기에는 v4 공식 비교 실패, v5 명시적 raw reference 비교 및 길이 검사, 해당 C++/Python 정의와 실제 receipt를
원본 bytes로 보존했다. 바이너리·object·환경·tokenizer.json·weights·평가 입력은 포함하지 않는다.
[Source closure](source-closure.json)는 원래 프로젝트 경로, 정확한 SHA, 기존 보관본 위치, 공식 metadata URL을 연결한다.
[Integrity](integrity.json)는 이 보관본의 파일 bytes를 검증한다.

재현 시 source closure를 따라 파일을 원래 `var/research/native-exaone45-contract/` 등에 복원한다.
기반 tool/source/CPU static archive 생성 정의는 [기존 native 재현 문서](../../../../../runtime/native/a100-llama-f072/README.md)에 있다.
기존 CPU objects 194개를 고정 inventory로 확인한 뒤 새 TU만 compile/link한다. 새 binary는 CUDA 의존성이 없는 ELF인지 확인한다.
`raw_context_check.py`는 공개 raw20 strict 검사가 먼저 통과해야 기존 입력200의 길이를 읽는다.
이 문서는 재실행·다운로드·설치 지시가 아니다. 새 실행은 별도 evidence tree에 기록하고 과거 실패/receipt를 덮어쓰지 않는다.
도구체계가 달라 binary hash가 바뀌면 조용히 과거 pin을 수정하거나 같은 실행이라고 주장해서는 안 된다.
