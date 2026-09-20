"""EXAONE public metadata tokenizer reference; no model/native/network calls."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json, os, resource, sys, unicodedata

ROOT = Path('/home/a202192020/NeuroBuild_v2')
BASE = ROOT / 'var/research/native-exaone45-contract'
TOKENIZER = ROOT / 'var/research/exaone45-33b-candidate-metadata/upstream/tokenizer.json'
PIN = '0bd798efa30739e209d51f36cfc2f0a636711e37ad9d69b77e4e5c8ca5f09fab'
TEXTS = (
    '', ' ', '\n\t', '  공개 문자열의 앞뒤 공백  ',
    '가구 하나의 상대 이동은 아직 적용하지 않습니다.',
    'X축 -14.70cm; Y축 +0.035m',
    '0 01 123456789 0.0005 +7mm',
    '1/3m １ｍ 1⁄3m −Y',
    '선택 범위: 왼쪽 물건을 제외한 오른쪽 물건',
    '공개\n줄바꿈\t탭\\경로 "인용"',
    '가나다와 한글 완성형',
    '\u1100\u1161\u1102\u1161\u1103\u1161',
    'e\u0301 cafe\u0301',
    'é café',
    'literal ▁ and spaces',
    '한국어·日本語·中文 😀 👩\u200d🔬',
    '{"decision":"CLARIFICATION","reason":null}',
    '<|system|>\n<|user|>\n<|assistant|>\n',
    '<think>\n\n</think>\n\n',
    '[BOS][PAD][UNK]<|endofturn|>',
)

def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    assert len(sys.argv) == 1 and Path(sys.prefix) == ROOT / '.conda-vllm'
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    assert not any(x in sys.modules for x in ('torch', 'transformers'))
    assert len(TEXTS) == len(set(TEXTS)) == 20
    data = TOKENIZER.read_bytes()
    assert len(data) == 12160205 and sha256(data).hexdigest() == PIN
    from tokenizers import Tokenizer, __version__
    tok = Tokenizer.from_file(str(TOKENIZER))
    cases, observations = [], []
    for i, text in enumerate(TEXTS):
        ids = tok.encode(text, add_special_tokens=False).ids
        decoded = tok.decode(ids, skip_special_tokens=False)
        normalized = unicodedata.normalize('NFC', text)
        cases.append({'text': text, 'expected_token_ids': ids})
        observations.append({'index': i, 'token_count': len(ids), 'raw_original_roundtrip': decoded == text,
                             'decoded_equals_nfc_source': decoded == normalized,
                             'source_changed_by_nfc': text != normalized,
                             'source_sha256': sha256(text.encode()).hexdigest(),
                             'decoded_sha256': sha256(decoded.encode()).hexdigest()})
    assert sha256(TOKENIZER.read_bytes()).hexdigest() == PIN
    assert not any(x in sys.modules for x in ('torch', 'transformers'))
    value = {'kind': 'EXAONE45_PUBLIC_OFFICIAL_TOKENIZER_FIXTURE',
             'status': 'OFFICIAL_REFERENCE_RECORDED_NATIVE_PARITY_NOT_RUN',
             'at_utc': datetime.now(timezone.utc).isoformat(),
             'model_id': 'LGAI-EXAONE/EXAONE-4.5-33B',
             'revision': '570aa4b15a4f45ba1133072b45f50198f6e3b4fd',
             'tokenizer_path': str(TOKENIZER.relative_to(ROOT)), 'tokenizer_sha256': PIN,
             'tokenizers_version': __version__, 'normalizer': 'NFC',
             'add_special_tokens': False, 'decode_skip_special_tokens': False,
             'native_expected_options': {'add_special': False, 'parse_special': True},
             'case_count': 20, 'official_raw_roundtrip_count': sum(x['raw_original_roundtrip'] for x in observations),
             'official_raw_mismatch_indices': [x['index'] for x in observations if not x['raw_original_roundtrip']],
             'official_nfc_source_roundtrip_count': sum(x['decoded_equals_nfc_source'] for x in observations),
             'tokenizer_parity': cases, 'observations': observations,
             'corpus_text_sha256': sha256(json.dumps(TEXTS, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
             'helper_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
             'model_calls': 0, 'native_calls': 0, 'gpu_calls': 0, 'http_calls': 0,
             'application_input_output_repair': False,
             'scope': 'New public synthetic corpus; no private/evaluation input or output. NFC diagnostic is separate from raw roundtrip and changes no application source.'}
    target = BASE / 'official-tokenizer-fixture.json'
    with target.open('x') as f: json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')
    print(json.dumps({k: value[k] for k in ('status', 'case_count', 'official_raw_roundtrip_count', 'official_raw_mismatch_indices', 'official_nfc_source_roundtrip_count')}
                     | {'fixture_sha256': sha256(target.read_bytes()).hexdigest()}))

if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'status': 'FAIL', 'error_type': type(exc).__name__}))
        raise SystemExit(1)
