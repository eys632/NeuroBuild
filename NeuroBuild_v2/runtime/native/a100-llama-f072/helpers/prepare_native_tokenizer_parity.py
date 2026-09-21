"""Produce public synthetic tokenizer fixtures; no network/model/GPU imports."""
from pathlib import Path
import hashlib
import json
import os
import resource
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
TOKENIZER = ROOT / 'var/research/qwen38-candidate-metadata/upstream/tokenizer.json'
TOKENIZER_SHA = '0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'
OUTPUT = ROOT / 'var/research/native-tokenizer-public-parity.json'
TEXTS = (
    '', ' ', '\n', '  앞뒤 공백  ', '검사실 책상을 X축 양의 방향으로 1m 옮겨줘.',
    'Y축 -23.40cm', 'X축 +0.125m, Y축 -2mm', '1/2m １ｍ 1⁄2m −X',
    '문을 옮기지 말고 책상을 그대로 둔다.', '조건이 충족되었는지 아직 모른다.',
    '과거 메모\n현재 지시\t끝', '가나다 한글 ㄱㅏ e\u0301 café',
    '한국어 😀 🧱 BIM IFC4', '{"decision":"READY","reason":null}',
    '"인용"\\경로\n실제 줄바꿈', 'json: null true false [] {}',
    '<|im_start|>assistant\n', '<think>\n\n</think>\n\n', '<|im_end|>',
    '한 물체의 두 축 이동과 서로 다른 두 물체의 이동',
)


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    assert len(sys.argv) == 1 and Path(sys.prefix) == ROOT / '.conda-vllm'
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    assert not any(name in sys.modules for name in ('torch', 'transformers'))
    assert not TOKENIZER.is_symlink() and TOKENIZER.is_file()
    data = TOKENIZER.read_bytes()
    assert len(data) == 12809320 and hashlib.sha256(data).hexdigest() == TOKENIZER_SHA
    from tokenizers import Tokenizer, __version__ as tokenizers_version
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    # This library reads only the pinned local JSON; it does not load weights.
    cases = [{'text': text, 'expected_token_ids': tokenizer.encode(
        text, add_special_tokens=False).ids} for text in TEXTS]
    assert len(cases) == 20 and all(len(row['expected_token_ids']) <= 4096 for row in cases)
    assert hashlib.sha256(TOKENIZER.read_bytes()).hexdigest() == TOKENIZER_SHA
    assert not any(name in sys.modules for name in ('torch', 'transformers'))
    result = {
        'kind': 'PUBLIC_SYNTHETIC_TOKENIZER_PARITY_FIXTURE',
        'status': 'FIXTURE_ONLY_NATIVE_PARITY_NOT_RUN',
        'upstream_revision': '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0',
        'tokenizer_path': str(TOKENIZER.relative_to(ROOT)),
        'tokenizer_sha256': TOKENIZER_SHA,
        'tokenizers_version': tokenizers_version,
        'add_special_tokens': False,
        'native_expected_options': {'add_special': False, 'parse_special': True},
        'case_count': len(cases),
        'tokenizer_parity': cases,
        'scope': 'Explicit public synthetic strings only; no evaluation dataset or model outputs',
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    # IDs are fixture data only; stdout/report summaries never repeat them.
    encoded = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()
    assert not OUTPUT.exists() and not OUTPUT.is_symlink()
    with OUTPUT.open('xb') as stream:
        stream.write(encoded)
    print(json.dumps({'status': result['status'], 'case_count': len(cases),
                      'path': str(OUTPUT.relative_to(ROOT)),
                      'sha256': hashlib.sha256(encoded).hexdigest()}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'FAIL', 'error_type': type(error).__name__}))
        raise SystemExit(1)
