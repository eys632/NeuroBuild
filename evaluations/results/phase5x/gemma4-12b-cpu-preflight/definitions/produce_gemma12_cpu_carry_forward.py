"""Produce a saved-evidence carry-forward receipt, never a new CPU execution PASS.

Reads only fixed metadata/proofs and source bytes. No dataset, weight, tokenizer
execution, project import, native process, subprocess, HTTP or GPU entry points.
Root reviews this definition before its one explicit --write invocation.
"""
from pathlib import Path
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
import stat
import struct
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
OUTPUT = Path('var/research/native-gemma4-12b-contract/cpu-carry-forward.json')
STATUS = 'CARRIED_FORWARD_BY_EXACT_INPUT_EQUIVALENCE'
VARIANT = 'gemma4-12b-qat-q4_0-carried-contract-v1'
MODEL = 'google/gemma-4-12B-it-qat-q4_0-gguf'
REVISION = '29d097773436b69ff9feafd636ab4cf873786537'
WEIGHT = '93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b'
OLD_MODEL = 'google/gemma-4-31B-it-qat-q4_0-gguf'
OLD_REVISION = '59dde24573e7e61570dba08b18a2e1fe246955ed'
OLD_WEIGHT = '179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b'
NATIVE = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
TEMPLATE = 'ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4'
TOKENIZER = 'cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f'
SUPPRESSION = [258883, 258882]
SAMPLING = {'temperature': 1.0, 'top_p': 0.95, 'top_k': 64, 'min_p': 0.0,
            'presence_penalty': 0.0, 'frequency_penalty': 0.0, 'repeat_penalty': 1.0,
            'repeat_last_n': 0, 'seed': 42,
            'samplers': ['temperature', 'top_k', 'top_p', 'min_p']}
SOURCE = {
    'src/neurobuild/infrastructure/local_model.py': '7dfc3f673ba6ab4e4970055c4cbee66ae440da2d42070af959a5fe415a9ab780',
    'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198',
    'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a',
    'prompts/requirement_generation_v2_v2.txt': '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6',
    'schemas/requirement_generation_v2_decision_branches.schema.json': '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2',
}
OLD_PREFIX = 'evaluations/results/phase5x/gemma4-cpu-preflight/'
REFS = {
    'old_header': (OLD_PREFIX + 'header-v2.json', 'd867a3300b2a93534fb1b480e8e42b30321c894aaec05b5729a529e848817756'),
    'new_header': ('var/reports/gemma4-12b-gguf-header.json', '97a9bd3cb854c446edd7b534011eaceac389f76f8f6c49b1dd0ec5e06be4eac0'),
    'tokenizer_comparison': ('var/reports/gemma4-12b-saved-tokenizer-comparison.json', 'a6d70d937b44a9743735b7843b59d9ba85dca2f9db300cf13c61d108a8c5f481'),
    'source_equivalence': ('var/research/gemma12-gemma-branch-source-equivalence.json', 'c21cbd6102933e1511f51625a88471b85caf8d9192dd3fe01fcd4ac644a37f20'),
    'historical_aggregate': (OLD_PREFIX + 'contract/final-cpu-proof.json', 'a27cd1f7a37899873aac346404e1cea8d0805c8db899f03eba6e3d7d7340029d'),
    'public_contract': (OLD_PREFIX + 'contract/public-proof.json', 'd7cd7032f019af566e2d7484afed85f9dab95fcbc0da06fc2a602cf5b7a76334'),
    'vocab': (OLD_PREFIX + 'contract/public-vocab-v2-proof.json', '70886f2ad74ef3758fe839f13b4b6740e22cb749f8f0989a98ea376382cc09c6'),
    'vocab_context': (OLD_PREFIX + 'contract/vocab-context-v2-proof.json', '06ef550b4ea48b3c3c65d631dafca06c85bd3d350311888b9bc5c86630caf64a'),
    'tokenizer_fixture': (OLD_PREFIX + 'contract/tokenizer-fixture.json', '42b2a10fdc4ebc066acb878a5a9e0c9e407affe0b91bc7d32145d8d360dc13e5'),
    'normalization_witness': (OLD_PREFIX + 'contract/normalization-witness-proof.json', 'bbb9ed28cdae06bb07a3f66949c2e23e59728324f74440be82b567f0a8662e73'),
    'historical_cpu_build': (OLD_PREFIX + 'contract/build-v2.json', '1b6dce0e85790b267ec2514da8c81158c76b9d01a27aa6c2e584787a160e67ee'),
    'historical_cpp': (OLD_PREFIX + 'contract/validator_v2.cpp', 'fecf647d431a3af0137f5e9459ddd8afece4e571d4a6a240dc2f4929acf9f20d'),
}


def require(value, code):
    if not value:
        raise ValueError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def exact(left, right, code):
    # Typed JSON equality: bool must not silently compare equal to an integer.
    dump = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    require(dump(left) == dump(right), code)


def read_bound(relative, expected, cap=2 * 1024 * 1024):
    rel = Path(relative)
    require(not rel.is_absolute() and '..' not in rel.parts, 'PATH_INVALID')
    parent = ROOT
    for part in ('', *rel.parts[:-1]):
        if part:
            parent /= part
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid(), 'DIRECTORY_UNSAFE')
    path = ROOT / rel
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
                and before.st_nlink == 1 and before.st_size <= cap, 'FILE_UNSAFE')
        data = stream.read(cap + 1)
        after = os.fstat(stream.fileno())
    stable = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    require(stable(before) == stable(after) and len(data) == before.st_size and digest(data) == expected,
            'BOUND_FILE_CHANGED')
    return data


def ref_map():
    return {key: {'path': path, 'sha256': pin} for key, (path, pin) in REFS.items()}


def validate_saved(d):
    """Pure fixed metadata validator; does not read any files or execute code."""
    old, new, compare = d['old_header'], d['new_header'], d['tokenizer_comparison']
    aggregate, public, vocab, context = (d[key] for key in ('historical_aggregate', 'public_contract', 'vocab', 'vocab_context'))
    equiv, witness, build = (d[key] for key in ('source_equivalence', 'normalization_witness', 'historical_cpu_build'))
    for header, model, revision, weight, size in [
        (old, OLD_MODEL, OLD_REVISION, OLD_WEIGHT, 17651001568),
        (new, MODEL, REVISION, WEIGHT, 6975879296),
    ]:
        require(header['kind'] == 'GGUF_HEADER_AUDIT' and header['status'] == 'PASS', 'HEADER_STATUS')
        exact([header['model_id'], header['revision'], header['file_sha256'], header['file_bytes']],
              [model, revision, weight, size], 'HEADER_IDENTITY')
        require(header['runtime_source_revision'] == NATIVE, 'HEADER_SOURCE')
        require(header['source_metadata_sha256']['tokenizer'] == TOKENIZER
                and header['source_metadata_sha256']['template'] == TEMPLATE, 'HEADER_REFERENCE')
    require(new['full_file_sha256_verified'] is True and new['stat_unchanged'] is True, 'NEW_HEADER_FULL_SHA')
    exact(new['header']['tensor_count'], 667, 'NEW_HEADER_TENSORS')
    exact(new['bindings']['suppress_tokens'], SUPPRESSION, 'NEW_SUPPRESSION')
    require(new['bindings']['suppression_eog_disjoint'] is True, 'SUPPRESSION_EOG_COLLISION')
    for key, pin in [('old_header_sha256', REFS['old_header'][1]), ('new_header_sha256', REFS['new_header'][1])]:
        require(compare[key] == pin, 'COMPARISON_HEADER_LINK')
    require(compare['status'] == 'PASS_EXACT_TYPED_TOKENIZER_METADATA_EXCEPT_DECLARED_SUPPRESSION', 'COMPARISON_STATUS')
    old_tokens = {k: v for k, v in old['header']['metadata'].items() if k.startswith('tokenizer.')}
    new_tokens = {k: v for k, v in new['header']['metadata'].items() if k.startswith('tokenizer.')}
    suppress_key = 'tokenizer.ggml.suppress_tokens'
    require(suppress_key not in old_tokens and set(new_tokens) == set(old_tokens) | {suppress_key}, 'TOKENIZER_KEYSET')
    exact({k: new_tokens[k] for k in old_tokens}, old_tokens, 'TOKENIZER_TYPED_VALUES')
    exact(new_tokens[suppress_key], {'type': 9, 'element_type': 5, 'count': 2,
          'elements_wire_sha256': digest(struct.pack('<ii', *SUPPRESSION)), 'wire_bytes': 20}, 'SUPPRESSION_WIRE')
    exact(old['header']['metadata']['general.architecture'], new['header']['metadata']['general.architecture'], 'ARCHITECTURE')
    require(compare['shared_typed_metadata_sha256'] == digest(json.dumps(old_tokens, sort_keys=True, separators=(',', ':')).encode()), 'COMPARISON_CONTENT_LINK')
    require(compare['sampling_difference']['complete_effective_sampling_equivalent'] is False, 'SAMPLING_FALSE_EQUIVALENCE')
    require(equiv['status'] == 'SOURCE_REVIEW_COMPLETE_CARRY_FORWARD_PENDING_HEADER', 'SOURCE_REVIEW_STATUS')
    require(equiv['baseline_cpu_proof']['sha256'] == REFS['historical_aggregate'][1], 'SOURCE_PROOF_LINK')
    require(equiv['client']['whole_module_AST_equals_baseline_after_only_those_six_removals'] is True
            and equiv['client']['Gemma_sampling_branch_AST_exact_equal'] is True
            and equiv['client']['complete_transport_and_Gemma_inline_reasoning_rejection_AST_exact_equal'] is True,
            'GEMMA_SOURCE_EQUIVALENCE')
    exact(equiv['client']['Gemma_sampling_http_fields'], SAMPLING, 'SAMPLING_REQUEST')
    exact({k: v['current_sha256'] for k, v in equiv['five_bound_sources'].items()}, SOURCE, 'CURRENT_SOURCE_MAP')
    for proof in (aggregate, public, vocab, context, witness):
        require(proof['model_id'] == OLD_MODEL, 'HISTORICAL_MODEL')
    for proof in (aggregate, vocab, context, witness):
        exact([proof['revision'], proof['gguf_sha256'], proof['header_sha256']],
              [OLD_REVISION, OLD_WEIGHT, REFS['old_header'][1]], 'HISTORICAL_IDENTITY')
    require(public['model_revision'] == OLD_REVISION, 'PUBLIC_REVISION')
    for proof in (aggregate, public, vocab, context):
        require(proof['status'] == 'PASS', 'HISTORICAL_PROOF_STATUS')
    require(aggregate['source_pin'] == build['source_pin'] == public['source_pin'] == NATIVE, 'HISTORICAL_NATIVE_SOURCE')
    require(aggregate['cpu_build_report_sha256'] == REFS['historical_cpu_build'][1]
            and aggregate['cpu_cpp_source_sha256'] == REFS['historical_cpp'][1], 'HISTORICAL_BUILD_LINK')
    require(aggregate['cpu_binary_sha256'] == build['binary_sha256'] == vocab['binary_sha256'] == context['binary_sha256'], 'HISTORICAL_BINARY_LINK')
    for key in ('public_contract', 'vocab_context', 'tokenizer_fixture'):
        require(aggregate['proof_refs'][key]['sha256'] == REFS[key][1], 'HISTORICAL_AGGREGATE_LINK')
    require(vocab['public_contract_sha256'] == REFS['public_contract'][1]
            and vocab['tokenizer_fixture_sha256'] == REFS['tokenizer_fixture'][1], 'VOCAB_LINK')
    exact([public['native']['schema_cases_accepted'], public['native']['schema_cases_rejected']], [10, 20], 'PUBLIC_CASE_COUNTS')
    exact(aggregate['official_tokenizer_parity'], {'status': 'PASS', 'case_count': 20,
          'id_match_count': 20, 'native_original_roundtrip_count': 20}, 'HISTORICAL_PARITY')
    exact([vocab['native']['tokenizer_metadata_parity_cases'], vocab['native']['tokenizer_native_roundtrip_cases']], [20, 20], 'VOCAB_CASE_COUNTS')
    require(vocab['native']['native_vocab_grammar_eog_checked'] is True
            and vocab['native']['native_embedded_vs_external_effective_tokens_match'] is True, 'VOCAB_GRAMMAR_AND_BOS')
    exact(context['splits'], aggregate['splits'], 'CONTEXT_LINK')
    expected_splits = {'exposed120': (120, '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b', 2339, 2646, 3414),
                       'v2_length80': (80, '7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40', 2360, 2593, 3361)}
    require(set(context['splits']) == set(expected_splits), 'CONTEXT_SPLITS')
    for key, expected in expected_splits.items():
        row = context['splits'][key]
        exact([row['input_count'], row['dataset_sha256'], row['min_input_tokens'], row['max_input_tokens'], row['max_input_plus_output']], list(expected), 'CONTEXT_COUNTS')
    exact([aggregate['max_output_tokens'], aggregate['max_context_tokens']], [768, 4096], 'CONTEXT_CAPS')
    exact(aggregate['resource_probe_token'], {'text': ' ', 'token_id': 236743,
          'native_token_count': 1, 'native_roundtrip': True}, 'RESOURCE_TOKEN')
    require(aggregate['resource_probe_token']['token_id'] not in SUPPRESSION
            and not set(SUPPRESSION) & set(new['bindings']['source_eog_token_ids']), 'SUPPRESSION_COLLISION')
    require(witness['status'] == 'FAIL_NATIVE_ORIGINAL_ROUNDTRIP'
            and witness['diagnosis']['native_original_roundtrip'] is False
            and witness['diagnosis']['official_ids_match_native'] is True
            and witness['input_output_repair'] is False, 'NORMALIZATION_LIMITATION_LOST')


def produce(documents):
    validate_saved(documents)
    old = documents['historical_aggregate']
    return {
        'kind': 'GEMMA4_12B_CPU_CONTRACT_CARRY_FORWARD', 'status': STATUS,
        'candidate_variant': VARIANT, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'model_id': MODEL, 'revision': REVISION, 'gguf_sha256': WEIGHT,
        'header_sha256': REFS['new_header'][1], 'template_sha256': TEMPLATE,
        'tokenizer_json_sha256': TOKENIZER, 'source_pin': NATIVE,
        'protocol': 'llama_cpp_json_schema', 'sampling_profile': 'gemma4_nonthinking_llama_cpp',
        'source_sha256': copy.deepcopy(SOURCE), 'sampling_request_parameters': copy.deepcopy(SAMPLING),
        'enable_reasoning': False, 'enable_thinking': False,
        'max_output_tokens': 768, 'max_context_tokens': 4096,
        'application_input_output_nfc_repair': False, 'proof_refs': ref_map(),
        'historical_measurements': {
            'measured_model_id': OLD_MODEL, 'measured_revision': OLD_REVISION, 'measured_gguf_sha256': OLD_WEIGHT,
            'original_status': 'PASS', 'measurement_status_for_new_candidate': STATUS,
            'public_contract': copy.deepcopy(documents['public_contract']['native']),
            'official_tokenizer_parity': copy.deepcopy(old['official_tokenizer_parity']),
            'splits': copy.deepcopy(old['splits']),
        },
        'new_executions': {'native_public': 0, 'vocab': 0, 'context': 0, 'model_inference': 0, 'http': 0, 'gpu': 0},
        'resource_probe_token': copy.deepcopy(old['resource_probe_token']),
        'resource_probe_token_suppression_disjoint': True,
        'sampling_behavior': {'http_recipe_equal': True, 'full_sampling_equivalent': False,
            'additional_suppressed_ids': list(SUPPRESSION), 'suppression_eog_disjoint': True,
            'native_effect': 'Model-owned negative-infinity logit bias before the unchanged HTTP sampling recipe'},
        'normalization_limitation': copy.deepcopy(old['normalization_limitation']),
        'literal_u2581_witness_status': documents['normalization_witness']['status'],
        'current_dataset_hash_verified_by_producer': False,
        'future_freeze_must_bind_current_dataset_bytes_to_historical_split_hashes': True,
        'new_model_runtime_status': 'NOT_RUN', 'new_model_quality_status': 'NOT_RUN',
        'scope': 'Historical public30/vocab20/context200 CPU observations carried through exact effective-input equivalence; no fresh corpus executions.',
        'limits': [
            'Context counts apply only to the original pinned dataset bytes, generation2 prompt/schema, exact Gemma branch and template options; final freeze must verify current dataset hashes.',
            'The two additional model-owned suppressed IDs make complete effective sampling different from 31B.',
            'Literal U+2581 roundtrip failure remains; public20 observations are not a universal Unicode guarantee.',
            'This receipt is not new candidate GPU/runtime, peak VRAM, inference, semantic quality or adoption evidence.',
            'New GGUF architecture/tensor validation comes from its separate actual header audit, not from old 31B CPU measurements.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', required=True)
    parser.parse_args()
    try:
        documents = {}
        for key, (relative, pin) in REFS.items():
            data = read_bound(relative, pin)
            # Hash public fixture/source only; never parse or execute its corpus.
            if key not in ('tokenizer_fixture', 'historical_cpp'):
                documents[key] = json.loads(data)
        for relative, pin in SOURCE.items():
            read_bound(relative, pin)
        eq = documents['source_equivalence']
        for relative, record in eq['native_pinned_source']['narrow_source_blob_checks'].items():
            read_bound('var/runtime-src/llama.cpp-' + NATIVE + '/' + relative, record['sha256'])
        result = produce(documents)
        result['producer_sha256'] = digest(Path(__file__).read_bytes())
        # Fixed output, never overwrite an existing receipt or follow a symlink.
        parent = ROOT / OUTPUT.parent
        parent.mkdir(mode=0o700, exist_ok=True)
        require(stat.S_ISDIR(parent.lstat().st_mode) and parent.lstat().st_uid == os.getuid(), 'OUTPUT_DIRECTORY_UNSAFE')
        data = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
        fd = os.open(ROOT / OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps({'status': STATUS, 'path': OUTPUT.as_posix(), 'sha256': digest(data)}))
        return 0
    except Exception:
        print(json.dumps({'status': 'FAIL', 'code': 'SAVED_CARRY_FORWARD_REJECTED'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
