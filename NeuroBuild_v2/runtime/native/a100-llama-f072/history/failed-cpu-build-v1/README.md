# A100 native runtime 재현 정의

검토한 로컬 helper의 **원본 바이트 스냅샷**이다. 보존 시점에는 CUDA native build의 compile/static-link 검사가 완료됐고 native CPU contract-validator build와 GGUF 다운로드는 `RUNNING`이었다. Native CPU validator 실행, GPU 모델 실행, peak VRAM, 의미 품질은 이 묶음으로 검증하지 않았다. 이 시점의 상태와 관측 시간은 [provenance.json](provenance.json)에 있으며 후속 실제 결과는 별도 실험 archive에서 확인한다.

바이너리, 도구 배포본, upstream source tree, weight, 환경, cache, 평가 입력·골드·모델 출력은 포함하지 않는다. 변경 중인 `run_native_contract_cpu.py`와 context invocation wrapper도 제외했다. Source MIT LICENSE의 정확한 원문은 [llama-f072.LICENSE](../../licenses/llama-f072.LICENSE)에 있다.

## 대상과 의존

- A100 root는 `/home/a202192020/NeuroBuild_v2`다. Helper의 절대 경로, 환경 검사와 출력 위치를 그대로 보존했다. `runtime/native/`에서 직접 실행하지 말고 아래 원래 `var/` 경로로 복원한다. RTX에서 검증한 정의가 아니며 root/SM/도구가 다른 곳에서 임의 경로 치환으로 실행하지 않는다.
- Build 및 감사 helper는 기존 `.conda` Python 3.12, 공개 tokenizer fixture 생성기는 기존 `.conda-vllm` Python과 `tokenizers`를 사용한다. 새 환경/패키지 설치를 수행하는 archive가 아니다.
- llama.cpp source는 [`f072b103714dfa1eee531f80b24512faf38e3dd2`](https://github.com/ggml-org/llama.cpp/tree/f072b103714dfa1eee531f80b24512faf38e3dd2), CMake는 [3.23.5 Linux x86_64 배포본](https://github.com/Kitware/CMake/releases/download/v3.23.5/cmake-3.23.5-linux-x86_64.tar.gz)이다. CMake tarball은 46,031,464 bytes / SHA256 `bbd7ad93d2a14ed3608021a9466ae63db76a24efd1fae7a5f7798c1de7ab9344`이며 [공식 checksum 목록](https://github.com/Kitware/CMake/releases/download/v3.23.5/cmake-3.23.5-SHA-256.txt)과 연결된다.
- 관측된 source tarball SHA256은 `016e1eb898fbf045d764d7e0140857de384a7fb7d6d00fee93fd8199c6f6712e`다. Bootstrap은 단순 tarball 이름을 믿지 않고 고정 commit/tree의 Git blob SHA1·size·mode 3,607개/172,243,701 bytes를 추출 후 전부 확인한다. GitHub API의 JSON 포장 바이트가 변할 수 있어 Git object identity와 실제 다운로드 SHA를 구분한다.
- GCC/G++ 9.5.0, system nvcc 11.8, CUDA SM80-only native build를 전제로 한다. 시스템 도구/driver를 바꾸지 않는다. CPU validator는 별도의 static CPU-only target으로 build하며 GPU backend/dynamic loading을 끈다. CPU compile과 GPU 실행은 별개다.
- `scripts/model_guard.py`, `scripts/download_model.py`, `runtime/models/qwen38-27b-q4-k-m.json`은 같은 checkout의 tracked 의존이다. 중복 복사하지 않았으며 정확한 SHA는 provenance에 있다. Helper 내부 pin도 유지했다. 다른 버전이면 조용히 pin을 바꾸지 말고 변경을 검토한다.

## 바이트 검증과 복원

[integrity.json](integrity.json)의 `files`는 archive의 project-relative 경로 → 원래 경로 → SHA256/bytes를 연결한다. `restore_path`가 있는 파일만 원래 위치로 복원한다. LICENSE와 archive 자체 설명·provenance는 복원 대상이 아니다. Integrity 파일 자신의 SHA는 별도 checkpoint 기록으로 확인한다.

아래는 **검증과 누락된 helper 복원만** 수행한다. 기존 파일은 바이트가 같아야 하며 덮어쓰지 않는다. 다운로드/build/테스트를 자동 시작하지 않는다.

```python
from pathlib import Path
import hashlib, json

root = Path('/home/a202192020/NeuroBuild_v2')
index = json.loads((root / 'runtime/native/a100-llama-f072/integrity.json').read_text())
for archived, item in index['files'].items():
    data = (root / archived).read_bytes()
    assert len(data) == item['bytes']
    assert hashlib.sha256(data).hexdigest() == item['sha256']
    if item['restore_path'] is None:
        continue
    target = root / item['restore_path']
    assert not target.is_symlink()
    if target.exists():
        assert target.read_bytes() == data
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
```

복원 후 실행 순서는 기존 source/tool bootstrap → CUDA compile → 필요한 RPATH relink → 정적 ELF/source 재검증이다. 별도 CPU validator는 `build_native_contract_cpu.py`가 고정 CMake/CPP와 shared guardian을 사용해 target만 build한다. Resource budget, exclusive report/temp 위치, 환경·source pin 검사를 우회하지 않는다. 성공·실패한 과거 출력 경로가 이미 있으면 helper가 중단할 수 있으며 이 archive는 이를 자동 삭제하지 않는다. 재현 시 새 실행 기록과 경로 조정은 별도 검토 대상이다.

GGUF downloader는 실제 postcompile proof와 정확한 SHA, 실행 시점의 disk reserve를 요구한다. 과거 proof를 새 machine의 성공 증거로 재사용하지 않는다. Header inspector와 tokenizer fixture에는 pinned public metadata가 추가로 필요하다. 작은 [metadata inventory](support-metadata/metadata_inventory.json)와 [conversion provenance](support-metadata/template_and_conversion_provenance.json)를 보존했다. `tokenizer.json`, `config.json`, `chat_template.jinja`, `convert.log` 등 누락된 원문은 inventory의 고정 revision URL에서 다시 확보하고 size/SHA를 확인해야 한다. 이 묶음은 큰 tokenizer/vocab/merge 파일을 복제하지 않는다.

## 검증 기록의 범위

`selftests/`는 synthetic/fake resource·parser·header controls다. `prior-proofs/`는 각각 기록된 시점의 원문을 보존한 **과거 CPU preparation 증거**다. 일부 proof는 최종 CPP pin 변경 전 runner SHA를 담으므로 이를 현재 executable 검증이라고 읽지 않는다. Actual process cleanup을 다룬 guardian selftest도 GPU/model 실행을 뜻하지 않는다. 최종 정적 검토는 [review](reviews/native_contract_cpu_independent_review.md)에 있으며 실행 전 실제 ELF dependency 확인과 core/body logging 경계를 별도로 요구한다.

공개 tokenizer fixture의 예상 token ID는 synthetic 문자열에서만 생성한다. 향후 실제 vocab와 비교한 결과가 있어야 parity PASS다. Context 길이 검사나 schema 문법 통과는 모델의 조건·대상·제외 범위 판단을 증명하지 않는다. Canonical parser, 고정 evaluation gate, 사람 미검수 gold 표시를 변경하지 않는다.
