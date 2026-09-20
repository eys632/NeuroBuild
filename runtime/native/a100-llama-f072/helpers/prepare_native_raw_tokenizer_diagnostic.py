"""Separate public diagnostic reference; never change the original HF fixture."""
from pathlib import Path
import hashlib
import json
import os
import resource
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
ORIGINAL = ROOT / 'var/research/native-tokenizer-public-parity.json'
ORIGINAL_SHA = '79c4448b7ee949add0a80e8a7f0fc0d73575aaf01ff6e52beb3cfae8434ea1bd'
TOKENIZER = ROOT / 'var/research/qwen38-candidate-metadata/upstream/tokenizer.json'
TOKENIZER_SHA = '0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'
OUTPUT = ROOT / 'var/research/native-tokenizer-public-parity-raw-diagnostic.json'


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    assert len(sys.argv) == 1 and Path(sys.prefix) == ROOT / '.conda-vllm'
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == ORIGINAL_SHA
    assert hashlib.sha256(TOKENIZER.read_bytes()).hexdigest() == TOKENIZER_SHA
    from tokenizers import Tokenizer, __version__
    original = json.loads(ORIGINAL.read_text())
    metadata = json.loads(TOKENIZER.read_text())
    assert metadata['normalizer'] == {'type': 'NFC'}
    hf = Tokenizer.from_file(str(TOKENIZER))
    raw = Tokenizer.from_file(str(TOKENIZER))
    raw.normalizer = None  # In-memory diagnostic only; JSON file is immutable.
    references, mismatch, hf_roundtrip, raw_roundtrip = [], [], 0, 0
    for index, row in enumerate(original['tokenizer_parity']):
        text = row['text']
        expected = hf.encode(text, add_special_tokens=False).ids
        assert expected == row['expected_token_ids']
        derived = raw.encode(text, add_special_tokens=False).ids
        references.append({'text': text, 'expected_token_ids': derived})
        if derived != expected:
            mismatch.append(index)
        hf_roundtrip += hf.decode(expected, skip_special_tokens=False) == text
        raw_roundtrip += raw.decode(derived, skip_special_tokens=False) == text
    assert len(references) == 20
    assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == ORIGINAL_SHA
    assert hashlib.sha256(TOKENIZER.read_bytes()).hexdigest() == TOKENIZER_SHA
    assert not any(name in sys.modules for name in ('torch', 'transformers'))
    record = {'kind': 'PUBLIC_RAW_UNICODE_TOKENIZER_DIAGNOSTIC_REFERENCE',
              'status': 'DERIVED_REFERENCE_NOT_OFFICIAL_HF_PARITY',
              'only_change_in_memory': 'Tokenizer.normalizer=None instead of NFC',
              'original_fixture_sha256': ORIGINAL_SHA, 'tokenizer_sha256': TOKENIZER_SHA,
              'tokenizers_version': __version__, 'case_count': 20,
              'original_hf_vs_raw_differing_indices': mismatch,
              'original_hf_roundtrip_original_cases': hf_roundtrip,
              'derived_raw_roundtrip_original_cases': raw_roundtrip,
              'tokenizer_parity': references,
              'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'application_source_or_quotes_changed': False, 'model_calls': 0, 'gpu_calls': 0}
    data = (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode()
    with OUTPUT.open('xb') as stream:
        stream.write(data)
    print(json.dumps({k: record[k] for k in ('status','case_count','original_hf_vs_raw_differing_indices',
                                           'original_hf_roundtrip_original_cases','derived_raw_roundtrip_original_cases')}
                     | {'sha256': hashlib.sha256(data).hexdigest()}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'FAIL', 'error_type': type(error).__name__}))
        raise SystemExit(1)
