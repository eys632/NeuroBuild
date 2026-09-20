"""Aggregate saved GLM CPU receipts only. No native/model/dataset/HTTP access.

Root runs main after review. Exact input hashes and structural cross-bindings
are checked; previous tests, full GGUF hashing and tokenizer work are not rerun.
PASS means the recorded CPU contract passed, not runtime/quality eligibility.
"""
from pathlib import Path
import hashlib
import json
import os

ROOT = Path('/home/a202192020/NeuroBuild_v2')
BASE = 'var/research/native-glm47-contract/'
OUTPUT = ROOT / BASE / 'final-cpu-proof.json'
MODEL_ID = 'ggml-org/GLM-4.7-Flash-GGUF'
REVISION = '7559e96b7e324ab405897dc2b91492b0f376ad4a'
MODEL_SHA = 'b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2'
TEMPLATE_SHA = 'd63ad536c3c81880043e22ec7fd08db42b4d8fb7c89c7138bc562bfa25281375'
TOKENIZER_SHA = '19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d'
SOURCE_PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
PROFILE = 'glm47_flash_nonthinking_llama_cpp'
VARIANT = 'glm47-flash-gguf-nonthinking-v1'
SAMPLING = {'temperature': 1.0, 'top_p': 0.95, 'top_k': 0, 'min_p': 0.0,
            'presence_penalty': 0.0, 'frequency_penalty': 0.0, 'repeat_penalty': 1.0,
            'repeat_last_n': 0, 'seed': 42, 'samplers': ['temperature', 'top_k', 'top_p', 'min_p']}
REFS = {
    'public_contract': {'path': BASE + 'public-proof-v3.json', 'sha256': 'd8f8fe1faf2ee73b06f6df35d16dba3a29cb78ad41af35a8a1be6cff888ac85c'},
    'public_vocab': {'path': BASE + 'public-vocab-proof.json', 'sha256': 'f3e31a724dcec94f6d3b285a9dd793d6a8b6c91c3c8c475a63c25709c94d6cf7'},
    'vocab_context': {'path': BASE + 'vocab-context-proof.json', 'sha256': '66e2ab245e0d7c2a2760d2b98e0a191fb8b27248be6fae6d61cf922c814bb607'},
    'tokenizer_fixture': {'path': BASE + 'official-tokenizer-fixture.json', 'sha256': 'e67bd4d05462587e0466f092351ada8c8fa4efdd9a10da0b4cecb25a4d3dc8f3'},
    'header': {'path': 'var/reports/glm47-flash-gguf-header.json', 'sha256': '595a7efd19914b65e91f1d92aaee141a0457472039c7278264cc1b5d314659ef'},
}
SOURCE_PATHS = {'src/neurobuild/infrastructure/local_model.py',
                'src/neurobuild/application/requirement_generation.py',
                'src/neurobuild/application/requirements.py',
                'prompts/requirement_generation_v2_v2.txt',
                'schemas/requirement_generation_v2_decision_branches.schema.json'}
SPLITS = {'exposed120': (120, '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'),
          'v2_length80': (80, '7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40')}


def require(value, code):
    if not value:
        raise ValueError(code)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()


def read_bound(relative, expected):
    path = ROOT / relative
    require(not Path(relative).is_absolute() and '..' not in Path(relative).parts
            and not path.is_symlink() and path.resolve().is_relative_to(ROOT), 'INPUT_PATH_INVALID')
    require(path.is_file() and path.stat().st_size <= 2 * 1024**2, 'INPUT_SIZE_INVALID')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, 'INPUT_HASH_MISMATCH')
    return raw


def validate_receipts(public, vocab, context, fixture, header):
    """Pure structural checks; callers must first verify every fixed receipt hash."""
    require(header['kind'] == 'GGUF_HEADER_AUDIT' and header['status'] == 'PASS'
            and header['full_file_sha256_verified'] is True
            and header['file_sha256'] == MODEL_SHA and header['file_bytes'] == 18244193920
            and header['model_id'] == MODEL_ID and header['revision'] == REVISION
            and header['bindings']['quantization'] == 'Q4_K_M'
            and header['bindings']['embedded_template_sha256'] == TEMPLATE_SHA,
            'HEADER_BINDING_MISMATCH')
    require(public['kind'] == 'GLM47_FLASH_NATIVE_PUBLIC_TEMPLATE_CPU_PROOF'
            and public['status'] == 'PASS' and public['model_revision'] == REVISION
            and public['source_pin'] == SOURCE_PIN and public['protocol'] == 'llama_cpp_json_schema'
            and public['sampling_profile'] == PROFILE and public['enable_thinking'] is False
            and public['official_template_sha256'] == TEMPLATE_SHA
            and public['template_override_used'] is False, 'PUBLIC_BINDING_MISMATCH')
    for receipt, kind in ((vocab, 'GLM47_FLASH_NATIVE_PUBLIC_VOCAB_CPU_PROOF'),
                          (context, 'GLM47_FLASH_NATIVE_VOCAB_CONTEXT_CPU_PROOF')):
        require(receipt['kind'] == kind and receipt['status'] == 'PASS' and receipt['phase'] == 'FINISHED'
                and receipt['model_id'] == MODEL_ID and receipt['revision'] == REVISION
                and receipt['gguf_sha256'] == MODEL_SHA and receipt['header_sha256'] == REFS['header']['sha256']
                and receipt['template_sha256'] == TEMPLATE_SHA and receipt['source_pin'] == SOURCE_PIN
                and receipt['application_input_output_nfc_repair'] is False, 'CPU_BINDING_MISMATCH')
    for receipt in (public, vocab, context):
        model_key = 'model_calls' if receipt is public else 'model_inference_calls'
        for key in (model_key, 'gpu_calls', 'http_calls'):
            require(type(receipt[key]) is int and receipt[key] == 0, 'CPU_SCOPE_MISMATCH')
    require(vocab['public_contract_sha256'] == REFS['public_contract']['sha256']
            and vocab['tokenizer_fixture_sha256'] == REFS['tokenizer_fixture']['sha256']
            and context['official_vocab_proof_sha256'] == REFS['public_vocab']['sha256']
            and vocab['build_report_sha256'] == public['build_report_sha256']
            and context['context_build_sha256'] == '737234c286864486c57721007b6858fae61bb7613eee02eb007ab5be0e5795bd'
            and context['context_binary_sha256'] == '3da5aa2debc3307277eab2794194541858e384c0fcfc0cfbe79e0f5b973f3017'
            and context['helper_sha256'] == 'cf271201279b5deea15b8394faecc05eb363971255f5ea9d1c66e917c2abb2d9',
            'CPU_CHAIN_MISMATCH')
    require(fixture['reference_kind'] == 'official_pinned_tokenizer_no_normalizer_change'
            and fixture['normalizer'] is None and fixture['tokenizer_sha256'] == TOKENIZER_SHA
            and fixture['case_count'] == 20 and fixture['official_raw_roundtrip_count'] == 20,
            'OFFICIAL_FIXTURE_MISMATCH')
    native = vocab['native']
    require(native['tokenizer_cases_checked'] == native['tokenizer_id_match_count']
            == native['tokenizer_native_raw_roundtrip_count'] == 20
            and native['official_hf_equivalence'] == 'PASS'
            and vocab['official_reference_native_id_mismatch_indices'] == []
            and vocab['native_raw_roundtrip_mismatch_indices'] == [], 'OFFICIAL_PARITY_FAILED')
    require(native['resource_probe_token_id'] == 220 and native['resource_probe_token_count'] == 1
            and native['resource_probe_raw_roundtrip'] is True
            and context['resource_probe_token'] == {'text': ' ', 'token_id': 220,
                 'native_token_count': 1, 'native_roundtrip': True}, 'RESOURCE_TOKEN_MISMATCH')
    require(context['max_output_tokens'] == 768 and context['max_context_tokens'] == 4096
            and type(context['input_count']) is int and context['input_count'] == 200
            and context['public_tokenizer_cases_repeated'] == 0
            and context['input_bodies_gold_token_ids_saved'] is False
            and context['gold_fields_scored'] is False
            and set(context['splits']) == set(SPLITS) and len(context['native_checks']) == 2,
            'CONTEXT_SCOPE_MISMATCH')
    for (name, (count, sha)), check in zip(SPLITS.items(), context['native_checks']):
        row = context['splits'][name]
        require(row['dataset_sha256'] == sha and type(row['input_count']) is int and row['input_count'] == count
                and all(type(row[k]) is int for k in ('min_input_tokens', 'max_input_tokens', 'max_input_plus_output'))
                and 0 < row['min_input_tokens'] <= row['max_input_tokens']
                and row['max_input_plus_output'] == row['max_input_tokens'] + 768 <= 4096,
                'CONTEXT_LIMIT_MISMATCH')
        require(check['status'] == 'PASS' and all(check[k] == row[k] for k in
                ('input_count', 'min_input_tokens', 'max_input_tokens', 'max_input_plus_output'))
                and all(check[k] is True for k in ('all_context_system_user_bytes_exact',
                    'all_context_prompt_raw_roundtrips_exact', 'embedded_template_exact_match',
                    'native_generation_prompt_exact', 'native_schema_grammar_fixed', 'native_sampling_schema_binding'))
                and all(check[k] is False for k in ('grammar_lazy', 'model_context_created',
                    'backend_init_called', 'weight_tensors_loaded')), 'CONTEXT_NATIVE_BINDING_MISMATCH')
    source = context['source_sha256']
    require(set(source) == SOURCE_PATHS and source == vocab['source_sha256']
            and all(public['inputs'].get(p) == sha for p, sha in source.items()), 'SOURCE_BINDING_MISMATCH')
    return source


def build_aggregate():
    receipts = {name: json.loads(read_bound(ref['path'], ref['sha256'])) for name, ref in REFS.items()}
    source = validate_receipts(receipts['public_contract'], receipts['public_vocab'], receipts['vocab_context'],
                               receipts['tokenizer_fixture'], receipts['header'])
    for path, sha in source.items():
        read_bound(path, sha)
    context = receipts['vocab_context']
    return {'kind': 'GLM47_FLASH_NATIVE_CONTRACT_CPU_PROOF', 'status': 'PASS',
        'model_id': MODEL_ID, 'revision': REVISION, 'candidate_variant': VARIANT,
        'protocol': 'llama_cpp_json_schema', 'sampling_profile': PROFILE, 'sampling_request_parameters': SAMPLING,
        'source_pin': SOURCE_PIN, 'source_sha256': source, 'gguf_sha256': MODEL_SHA,
        'header_sha256': REFS['header']['sha256'], 'template_sha256': TEMPLATE_SHA,
        'tokenizer_json_sha256': TOKENIZER_SHA, 'official_tokenizer_normalizer': None,
        'official_tokenizer_parity': {'status': 'PASS', 'case_count': 20, 'id_match_count': 20,
                                      'native_original_roundtrip_count': 20},
        'max_output_tokens': 768, 'max_context_tokens': 4096, 'splits': context['splits'],
        'resource_probe_token': context['resource_probe_token'], 'proof_refs': REFS,
        'model_inference_calls': 0, 'gpu_calls': 0, 'http_calls': 0,
        'application_input_output_nfc_repair': False, 'template_override_used': False,
        'aggregation_scope': 'Saved receipt hashes and structural cross-bindings only; source5 rehashed; no CPU checks rerun',
        'aggregate_execution': {'native_calls': 0, 'model_file_opens': 0, 'dataset_file_opens': 0},
        'runtime_status': 'NOT_RUN', 'quality_status': 'NOT_MEASURED',
        'normalization_limitation': 'Official/native ID and raw roundtrip parity proved for public20 and these200 prompts; not a guarantee for all Unicode',
        'reasoning_boundary': receipts['public_contract']['reasoning_scope']}


def main():
    require(not OUTPUT.exists() and not OUTPUT.is_symlink(), 'OUTPUT_EXISTS')
    raw = encoded(build_aggregate())
    with OUTPUT.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({'status': 'PASS', 'path': str(OUTPUT.relative_to(ROOT)),
                      'sha256': hashlib.sha256(raw).hexdigest(), 'native_calls': 0}))


if __name__ == '__main__':
    main()
