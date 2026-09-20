"""Future public-only official tokenizer recording. Preparation is not execution."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json, os, resource, sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
BASE = ROOT / 'var/research/native-glm47-contract'
META = ROOT / 'var/research/glm47-flash-candidate-metadata'
TOKENIZER = META / 'upstream/tokenizer.json'
DESIGN = META / 'public_tokenizer_cases_design.json'
PIN = '19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d'
DESIGN_PIN = '5c0e50fbd63b1b1c05883bbd96381f48237293a3c5cec9c6d48ffe1ad257dc13'

def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    assert len(sys.argv) == 1 and Path(sys.prefix) == ROOT / '.conda-vllm'
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
    assert not any(x in sys.modules for x in ('torch', 'transformers'))
    target = BASE / 'official-tokenizer-fixture.json'
    assert not target.exists() and not target.is_symlink()
    data, design_bytes = TOKENIZER.read_bytes(), DESIGN.read_bytes()
    assert len(data) == 20217442 and sha256(data).hexdigest() == PIN
    assert sha256(design_bytes).hexdigest() == DESIGN_PIN
    metadata = json.loads(data)
    assert metadata['normalizer'] is None
    design = json.loads(design_bytes)
    texts = [row['text'] for row in design['cases']]
    assert len(texts) == len(set(texts)) == 20
    from tokenizers import Tokenizer, __version__
    tok = Tokenizer.from_file(str(TOKENIZER))
    cases, observations = [], []
    for i, text in enumerate(texts):
        ids = tok.encode(text, add_special_tokens=False).ids
        decoded = tok.decode(ids, skip_special_tokens=False)
        cases.append({'text': text, 'expected_token_ids': ids})
        observations.append({'index': i, 'token_count': len(ids),
                             'raw_original_roundtrip': decoded == text,
                             'source_sha256': sha256(text.encode()).hexdigest(),
                             'decoded_sha256': sha256(decoded.encode()).hexdigest()})
    # Independently test the converter's added-token encode/decode assumption.
    # These 36 public metadata literals are separate from the 20 parity corpus.
    added_checks = []
    for row in metadata['added_tokens']:
        literal = row['content']
        ids = tok.encode(literal, add_special_tokens=False).ids
        added_checks.append({'id': row['id'], 'expected_single_id': ids == [row['id']],
                             'raw_roundtrip': tok.decode(ids, skip_special_tokens=False) == literal})
    assert len(added_checks) == 36
    assert sha256(TOKENIZER.read_bytes()).hexdigest() == PIN
    assert sha256(DESIGN.read_bytes()).hexdigest() == DESIGN_PIN
    assert not any(x in sys.modules for x in ('torch', 'transformers'))
    value = {'kind': 'GLM47_FLASH_PUBLIC_OFFICIAL_TOKENIZER_FIXTURE',
             'status': 'OFFICIAL_REFERENCE_RECORDED_NATIVE_PARITY_NOT_RUN',
             'at_utc': datetime.now(timezone.utc).isoformat(),
             'model_id': 'zai-org/GLM-4.7-Flash',
             'revision': '7dd20894a642a0aa287e9827cb1a1f7f91386b67',
             'tokenizer_path': str(TOKENIZER.relative_to(ROOT)), 'tokenizer_sha256': PIN,
             'design_path': str(DESIGN.relative_to(ROOT)), 'design_sha256': DESIGN_PIN,
             'reference_kind': 'official_pinned_tokenizer_no_normalizer_change',
             'tokenizers_version': __version__, 'normalizer': None,
             'add_special_tokens': False, 'decode_skip_special_tokens': False,
             'native_expected_options': {'add_special': False, 'parse_special': True},
             'case_count': 20,
             'official_raw_roundtrip_count': sum(x['raw_original_roundtrip'] for x in observations),
             'official_raw_mismatch_indices': [x['index'] for x in observations if not x['raw_original_roundtrip']],
             'tokenizer_parity': cases, 'observations': observations,
             'added_literal_checks': added_checks,
             'added_literal_single_id_count': sum(x['expected_single_id'] for x in added_checks),
             'added_literal_raw_roundtrip_count': sum(x['raw_roundtrip'] for x in added_checks),
             'corpus_text_sha256': sha256(json.dumps(texts, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
             'helper_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
             'model_calls': 0, 'native_calls': 0, 'gpu_calls': 0, 'http_calls': 0,
             'application_input_output_nfc_repair': False,
             'scope': 'Public synthetic strings and public tokenizer literals only. Every observed mismatch is retained. No global Unicode guarantee.'}
    with target.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')
    print(json.dumps({k: value[k] for k in ('status', 'case_count', 'official_raw_roundtrip_count', 'official_raw_mismatch_indices', 'added_literal_raw_roundtrip_count')}
                     | {'fixture_sha256': sha256(target.read_bytes()).hexdigest()}))

if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'status': 'FAIL', 'error_type': type(exc).__name__}))
        raise SystemExit(1)
