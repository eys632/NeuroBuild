"""Import-only override/raw-Unicode EXAONE45 v4 evidence helpers; root explicitly calls after CPU/VRAM gates.

Import checks the historical generic helper hash, but never contacts a server,
reads a process, loads a model, runs native code or creates a proof. No CLI/main.
Every live entrypoint requires the exact reviewed EXAONE raw-reference CPU proofs.
Response text, reasoning, props template and token arrays are not persisted.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import time
from types import ModuleType
from uuid import UUID

ROOT = Path('/home/a202192020/NeuroBuild_v2')
BASE_PATH = ROOT / 'var/research/native_runtime_probe.py'
BASE_SHA = 'ac100df7949b2b14a517c4568fa66369bd98c599b39507ef19f873490a0f9f63'
_base_bytes = BASE_PATH.read_bytes()
if hashlib.sha256(_base_bytes).hexdigest() != BASE_SHA:
    raise ValueError('GENERIC_HELPER_HASH_MISMATCH')
base = ModuleType('exaone45_pinned_generic_probe')
base.__file__ = str(BASE_PATH)
exec(compile(_base_bytes, str(BASE_PATH), 'exec'), base.__dict__)
del _base_bytes
# Deliberately exclude all historical Qwen provenance/template/client helpers.
require, digest, encoded, read_json = base.require, base.digest, base.encoded, base.read_json
load_config, binding, validate_guard, epoch = base.load_config, base.binding, base.validate_guard, base.epoch
request_json, resource_payload, validate_resource = base.request_json, base.resource_payload, base.validate_resource
write_bundle = base.write_bundle

MODEL_ID = 'LGAI-EXAONE/EXAONE-4.5-33B-GGUF'
REVISION = '0e969634ef24db05151b435970297a6dee634b7e'
MODEL_SHA = '5ba3839b67dcee5618ea7b2206cedc8f9e2ec90fbcec3c95a8cc8b33967f6baf'
MODEL_BYTES = 20047839424
ORIGINAL_TEMPLATE_SHA = 'e4ece7acc79ba82121d4d57791fb7ecb796e39185087197377da5d2286bec0e5'
TEMPLATE_SHA = '7de6c8ba3df6db54564c7a63385cc29572c0a616d5848961e969ecbb8c349851'
OVERRIDE_PATH = ROOT / 'runtime/templates/exaone45-continue-free.jinja'
OVERRIDE_BYTES = 5829
LAUNCHER_PATH = ROOT / 'scripts/llama_server.py'
LAUNCHER_SHA = '6a58ee1ea09636df182125da4a4a2711012e6c53f5f90c06548a63b9915369ed'
HEADER_SHA = 'fb5260c6e1e3356741f7728e4077f771763ea39affd77e8ac9772e417aa70c12'
PUBLIC_PROOF_PATH = ROOT / 'var/research/native-exaone45-contract/public-proof-v3.json'
PUBLIC_PROOF_SHA = 'fc7109fe4e9fbbe4a619ad16dc701cda01a4976ec8bd53d726aeb09f34f39408'
# f072 common/jinja/lexer.cpp:54-57 strips exactly one terminal LF.
# This official source has no CR bytes; no user text normalization is performed.
PROPS_TEMPLATE_SHA = 'b8bc1ef1b1fcd30cdd28fe7655bf79020aec666142107c01231b7b59f15cb1ef'
PROPS_TEMPLATE_BYTES = 5828
EMBEDDED_TEMPLATE_BYTES = 5930
TOKENIZER_SHA = '0bd798efa30739e209d51f36cfc2f0a636711e37ad9d69b77e4e5c8ca5f09fab'
PROFILE = 'exaone45_nonthinking_llama_cpp'
# Template history remains distinct from the newly chosen raw-Unicode experiment.
TEMPLATE_VARIANT = 'exaone45-gguf-continue-free-korean-v1'
RUNTIME_VARIANT = 'exaone45-gguf-continue-free-raw-unicode-korean-v1'
TOKENIZER_CONTRACT_STATUS = 'EXPLICIT_RAW_REFERENCE_CPU_PASS_OFFICIAL_HF_FAIL'
REFERENCE_KIND = 'official_metadata_with_only_NFC_normalizer_disabled'
OFFICIAL_VOCAB_PATH = ROOT / 'var/research/native-exaone45-contract/public-vocab-proof.json'
OFFICIAL_VOCAB_SHA = '66442010a8c4ee9f5f554bfea34273fd80659d50d42b9acdba6b2879400285d1'
RAW_VOCAB_SHA = '2ce12c5e4d93f7d3baff40da67b1f2c3b5575e117dff081c84d03835e07e8c9d'
RAW_CONTEXT_SHA = 'f450e9f0bf3a206204474ed860bc6d191597cbe6cc31a7349efe894b5d3775bb'
RAW_FIXTURE_SHA = '9a379ccf7cab7c85c23582c45f77c6b4ec481a9bb1469009564dba0fe894bf2c'
CPU_PROOF_SHA = '2a937a8adeca827f4724c9b65947291005aa34dc8ca4af823739fd09ca248209'
CPU_BINARY_SHA = '79ed8a05dbb429e774601cd8ad0d85398a5240c0a553a975d281f6d090580aea'
CPU_BUILD_SHA = '399bcaf6cb6fa3a40cb13461d8b34f8862372d4162ffa18eb4fc42b28855ad34'
PROOF_DIR = 'var/research/native-exaone45-contract/'
MANIFEST_PATH = ROOT / 'var/research/exaone45-33b-candidate-metadata/candidate_download_manifest.json'
MANIFEST_SHA = '98aa8ad498c2a55db6359754c80793e33b880f60c191ec3fbe449097833c4bb8'
OFFICIAL_FIXTURE_PATH = ROOT / 'var/research/native-exaone45-contract/official-tokenizer-fixture.json'
OFFICIAL_FIXTURE_SHA = '49b40b3390cba92f3088c22606632348ba261e69ea0b385b74aa9126be8c46cb'
OFFICIAL_REFERENCE_LIMITATION = {'case_count': 20, 'raw_original_roundtrip_count': 18,
    'raw_original_mismatch_indices': [11, 12], 'nfc_source_roundtrip_count': 20,
    'normalizer': 'NFC', 'native_parity_observed': False}

CPU_SOURCE_PATHS = {
    'src/neurobuild/infrastructure/local_model.py',
    'src/neurobuild/application/requirement_generation.py',
    'src/neurobuild/application/requirements.py',
    'prompts/requirement_generation_v2_v2.txt',
    'schemas/requirement_generation_v2_decision_branches.schema.json',
}
PUBLIC_SOURCE = '검사실 책상을 X축 양의 방향으로 1m 옮겨줘.'
CONTEXT_SPLITS = {
    'exposed120': (120, '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b'),
    'v2_length80': (80, '7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40'),
}


def require_launcher_pin():
    require(digest(base.checked_file(LAUNCHER_PATH, ROOT).read_bytes()) == LAUNCHER_SHA,
            'EXAONE_LAUNCHER_PIN_MISMATCH')


def load_config(path, expected):
    """The only extra config conversion is the required override Path field."""
    require_launcher_pin()
    data, raw = read_json(path)
    require(digest(raw) == expected, 'CONFIG_HASH_MISMATCH')
    require(type(data.get('chat_template_path')) is str
            and data.get('chat_template_sha256') == TEMPLATE_SHA, 'EXAONE_OVERRIDE_CONFIG_REQUIRED')
    for key in ('binary_path', 'build_report', 'source_report', 'model_path', 'model_header_report',
                'log_file', 'report_file', 'chat_template_path'):
        data[key] = Path(data[key])
    config = base.NativeLaunchConfig(**data)
    require(config.enable_reasoning is False, 'NONTHINKING_REQUIRED')
    require(pinned_override(config)['path'] == str(OVERRIDE_PATH.relative_to(ROOT)),
            'EXAONE_OVERRIDE_PATH_MISMATCH')
    return config, raw


def pinned_override(config):
    require_launcher_pin()
    require(isinstance(config.chat_template_path, Path)
            and config.chat_template_sha256 == TEMPLATE_SHA, 'EXAONE_OVERRIDE_CONFIG_REQUIRED')
    selected = base.checked_file(config.chat_template_path, ROOT)
    require(selected == OVERRIDE_PATH and selected.stat().st_size == OVERRIDE_BYTES,
            'EXAONE_OVERRIDE_PATH_MISMATCH')
    base.verified_hash(selected, TEMPLATE_SHA, expected_bytes=OVERRIDE_BYTES)
    return {'path': str(selected.relative_to(ROOT)), 'sha256': TEMPLATE_SHA}


def validate_override_public():
    """Consume actual public proof scalars/hash closure; never rerun native code."""
    public, raw = read_json(PUBLIC_PROOF_PATH)
    require(digest(raw) == PUBLIC_PROOF_SHA
            and public['kind'] == 'EXAONE45_NATIVE_PUBLIC_TEMPLATE_CPU_PROOF' and public['status'] == 'PASS'
            and public['runtime_variant'] == TEMPLATE_VARIANT and public['source_pin'] == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and public['protocol'] == 'llama_cpp_json_schema' and public['sampling_profile'] == PROFILE
            and public['enable_thinking'] is False
            and public['official_embedded_template_sha256'] == ORIGINAL_TEMPLATE_SHA
            and public['candidate_template_sha256'] == TEMPLATE_SHA
            and type(public['template_reference_cases']) is int and public['template_reference_cases'] == 18
            and public['official_original_derived_reference_byte_equal'] is True
            and public['gguf_loaded'] is False
            and all(type(public[key]) is int and public[key] == 0 for key in ('gpu_calls','http_calls','model_calls')),
            'EXAONE_OVERRIDE_PUBLIC_PROOF_MISMATCH')
    native = public['native']
    require(native['status'] == 'PASS' and native['public_template_reference_cases'] == 18
            and native['derived_native_system_and_user_exact'] is True
            and native['derived_native_prompt_equals_official_reference'] is True
            and native['native_request_prompt_bytes'] == 9176
            and native['original_template_native_mismatches'] == 7
            and native['original_native_system_present'] is False and native['original_native_prompt_bytes'] == 177
            and native['native_tokenization'] == 'NOT_RUN', 'EXAONE_SYSTEM_POLICY_PROOF_MISMATCH')
    require(public['production_client_sha256'] == public['inputs']['src/neurobuild/infrastructure/local_model.py'],
            'EXAONE_PUBLIC_CLIENT_BINDING_MISMATCH')
    for name, expected in public['inputs'].items():
        require(type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts,
                'EXAONE_PUBLIC_SOURCE_PATH_INVALID')
        source = base.checked_file(ROOT / name, ROOT)
        require(source.stat().st_size <= 1024 * 1024 and digest(source.read_bytes()) == expected,
                'EXAONE_PUBLIC_SOURCE_HASH_MISMATCH')
    return {'status':'PASS', 'reference_cases':18,
            'official_original_derived_reference_byte_equal':True,
            'derived_native_system_and_user_exact':True,
            'derived_native_prompt_equals_official_reference':True,
            'proof_ref':{'path':str(PUBLIC_PROOF_PATH.relative_to(ROOT)), 'sha256':PUBLIC_PROOF_SHA}}


def validate_official_hf_failure():
    """Actual public comparison failure is immutable, never a derived-reference PASS."""
    proof, raw = read_json(OFFICIAL_VOCAB_PATH)
    require(digest(raw) == OFFICIAL_VOCAB_SHA
            and proof['kind'] == 'EXAONE45_NATIVE_PUBLIC_VOCAB_CPU_PROOF'
            and proof['status'] == 'FAIL' and proof['runtime_variant'] == TEMPLATE_VARIANT
            and proof['model_id'] == MODEL_ID and proof['revision'] == REVISION
            and proof['gguf_sha256'] == MODEL_SHA and proof['header_sha256'] == HEADER_SHA
            and proof['source_pin'] == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and proof['public_contract_sha256'] == PUBLIC_PROOF_SHA
            and proof['tokenizer_fixture_sha256'] == OFFICIAL_FIXTURE_SHA
            and proof['original_template_sha256'] == ORIGINAL_TEMPLATE_SHA
            and proof['effective_template_sha256'] == TEMPLATE_SHA
            and proof['official_reference_observed_all20'] is True
            and proof['official_metadata_raw_roundtrip_count'] == 18
            and proof['application_input_output_nfc_repair'] is False
            and all(type(proof[k]) is int and proof[k] == 0
                    for k in ('model_inference_calls','http_calls','gpu_calls')),
            'EXAONE_OFFICIAL_HF_FAILURE_MISMATCH')
    native = proof['native']
    require(native['status'] == 'FAIL' and native['tokenizer_reference_parity'] == 'FAIL'
            and native['official_reference_gate_pass'] is False
            and native['tokenizer_cases_checked'] == 20 and native['tokenizer_id_match_count'] == 18
            and native['tokenizer_id_mismatch_mask'] == (1 << 11) | (1 << 12)
            and native['tokenizer_native_raw_roundtrip_count'] == 20
            and native['tokenizer_native_raw_mismatch_mask'] == 0
            and native['tokenizer_reference_ids_raw_roundtrip_count'] == 18
            and native['embedded_original_template_exact_match'] is True
            and native['effective_override_vocab_render_exact'] is True
            and native['native_request_prompt_bytes'] == 9176,
            'EXAONE_OFFICIAL_HF_OBSERVATION_MISMATCH')
    return {'status':'FAIL','case_count':20,'id_match_count':18,'mismatch_indices':[11,12],
            'native_raw_roundtrip_count':20,'official_ids_raw_roundtrip_count':18,
            'proof_ref':{'path':str(OFFICIAL_VOCAB_PATH.relative_to(ROOT)), 'sha256':OFFICIAL_VOCAB_SHA}}


def exaone_binding(config):
    manifest, manifest_raw = read_json(MANIFEST_PATH)
    require(digest(manifest_raw) == MANIFEST_SHA and manifest['model_id'] == MODEL_ID
            and manifest['revision'] == REVISION
            and [item for item in manifest['files'] if item['name'].endswith('.gguf')] == [{
                'name': 'EXAONE-4.5-33B-Q4_K_M.gguf', 'bytes': MODEL_BYTES, 'sha256': MODEL_SHA}],
            'EXAONE_MANIFEST_MISMATCH')
    require(config.model_revision == REVISION and config.model_sha256 == MODEL_SHA
            and config.source_commit == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and config.enable_reasoning is False
            and (config.batch_size, config.ubatch_size) == (64, 64)
            and config.estimated_peak_mib == 28672 and config.peak_allowance_mib == 0
            and config.model_path.name == 'EXAONE-4.5-33B-Q4_K_M.gguf', 'EXAONE_CONFIG_MISMATCH')
    override = pinned_override(config)
    artifacts = dict(binding(config), chat_template_override=override)
    header, raw = read_json(config.model_header_report)
    require(digest(raw) == config.model_header_report_sha256
            and digest(raw) == HEADER_SHA and header['file_bytes'] == MODEL_BYTES
            and header['model_id'] == MODEL_ID and header['full_file_sha256_verified'] is True
            and header['bindings']['embedded_template_sha256'] == ORIGINAL_TEMPLATE_SHA
            and header['source_metadata_sha256']['tokenizer'] == TOKENIZER_SHA, 'EXAONE_HEADER_MISMATCH')
    return artifacts


def validate_cpu_common_fields(config, proof_path, proof_sha):
    """Validate pinned aggregate common fields; live identity/resource checks are separate.

    The caller supplies the reviewed aggregate proof's exact hash. Linked small
    evidence hashes are checked again; datasets/tensors are never opened here.
    """
    override = pinned_override(config)
    render_parity = validate_override_public()
    proof, raw = read_json(proof_path)
    require(digest(raw) == proof_sha == CPU_PROOF_SHA and proof['kind'] == 'EXAONE45_NATIVE_CONTRACT_CPU_PROOF'
            and proof['status'] == 'PASS' and proof['model_id'] == MODEL_ID
            and proof['runtime_variant'] == RUNTIME_VARIANT
            and proof['template_proof_variant'] == TEMPLATE_VARIANT
            and proof['protocol'] == 'llama_cpp_json_schema' and proof['sampling_profile'] == PROFILE
            and proof['source_pin'] == config.source_commit == 'f072b103714dfa1eee531f80b24512faf38e3dd2'
            and proof['revision'] == REVISION and proof['gguf_sha256'] == MODEL_SHA == config.model_sha256
            and proof['header_sha256'] == config.model_header_report_sha256 == HEADER_SHA
            and proof['runtime_launcher_sha256'] == LAUNCHER_SHA
            and proof['original_embedded_template_sha256'] == ORIGINAL_TEMPLATE_SHA
            and proof['template_sha256'] == TEMPLATE_SHA and proof['tokenizer_json_sha256'] == TOKENIZER_SHA
            and type(proof['model_inference_calls']) is int and proof['model_inference_calls'] == 0
            and proof['application_input_output_nfc_repair'] is False
            and proof['enable_thinking'] is False
            and type(proof['gpu_or_http_calls']) is int and proof['gpu_or_http_calls'] == 0,
            'EXAONE_CPU_PROVENANCE_MISMATCH')
    official_hf_failure = validate_official_hf_failure()
    require(proof['official_hf_equivalence'] == official_hf_failure
            and proof['context_tokenizer'] == 'native_raw_unicode_no_nfc_repair',
            'EXAONE_RAW_VARIANT_OFFICIAL_FAILURE_MISSING')
    override_contract = {**override, 'bytes':OVERRIDE_BYTES,
                         'original_embedded_template_sha256':ORIGINAL_TEMPLATE_SHA,
                         'transform':'continue-free-system-message-branch-v1'}
    require(proof['chat_template_override'] == override_contract
            and proof['template_render_parity'] == render_parity, 'EXAONE_OVERRIDE_AGGREGATE_MISMATCH')
    require(type(proof['max_output_tokens']) is int and proof['max_output_tokens'] == 768
            and type(proof['max_context_tokens']) is int and proof['max_context_tokens'] == 4096,
            'EXAONE_CONTEXT_LIMIT_MISMATCH')
    # The official NFC tokenizer itself preserves only18/20 raw public strings.
    # Never replace this with a broad raw-Unicode PASS or borrow Qwen's variant.
    fixture, fixture_raw = read_json(OFFICIAL_FIXTURE_PATH)
    require(digest(fixture_raw) == OFFICIAL_FIXTURE_SHA
            and fixture['kind'] == 'EXAONE45_PUBLIC_OFFICIAL_TOKENIZER_FIXTURE'
            and fixture['status'] == 'OFFICIAL_REFERENCE_RECORDED_NATIVE_PARITY_NOT_RUN'
            and fixture['case_count'] == 20 and fixture['official_raw_roundtrip_count'] == 18
            and fixture['official_raw_mismatch_indices'] == [11, 12]
            and fixture['official_nfc_source_roundtrip_count'] == 20
            and fixture['normalizer'] == 'NFC' and fixture['tokenizer_sha256'] == TOKENIZER_SHA,
            'EXAONE_OFFICIAL_REFERENCE_MISMATCH')
    require(proof['official_reference_fixture_ref'] == {
                'path':str(OFFICIAL_FIXTURE_PATH.relative_to(ROOT)), 'sha256':OFFICIAL_FIXTURE_SHA},
            'EXAONE_OFFICIAL_LIMITATION_MISSING')
    require(set(proof['splits']) == set(CONTEXT_SPLITS), 'EXAONE_CONTEXT_SPLITS_MISMATCH')
    for name, (count, sha) in CONTEXT_SPLITS.items():
        row = proof['splits'][name]
        require(type(row['input_count']) is int and row['input_count'] == count
                and row['dataset_sha256'] == sha
                and type(row['min_input_tokens']) is int and type(row['max_input_tokens']) is int
                and 0 < row['min_input_tokens'] <= row['max_input_tokens']
                and type(row['max_input_plus_output']) is int
                and row['max_input_plus_output'] == row['max_input_tokens'] + 768 <= 4096,
                'EXAONE_CONTEXT_SPLIT_MISMATCH')
    require(set(proof['source_sha256']) == CPU_SOURCE_PATHS, 'EXAONE_CPU_SOURCE_SET_MISMATCH')
    for path, expected in proof['source_sha256'].items():
        source_file = base.checked_file(ROOT / path, ROOT)
        require(source_file.stat().st_size <= 1024 * 1024
                and digest(source_file.read_bytes()) == expected, 'EXAONE_CPU_SOURCE_HASH_MISMATCH')
    require(proof['proof_refs'] == {
        'public_contract':{'path':str(PUBLIC_PROOF_PATH.relative_to(ROOT)),'sha256':PUBLIC_PROOF_SHA},
        'vocab_context':{'path':PROOF_DIR+'vocab-context-raw-proof.json','sha256':RAW_CONTEXT_SHA},
        'tokenizer_fixture':{'path':PROOF_DIR+'raw-reference-diagnostic.json','sha256':RAW_FIXTURE_SHA}},
            'EXAONE_CPU_REFERENCES_MISMATCH')
    for ref in proof['proof_refs'].values():
        require(set(ref) == {'path', 'sha256'} and type(ref['path']) is str
                and not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts,
                'EXAONE_CPU_REFERENCE_PATH_INVALID')
        _, linked_raw = read_json(ROOT / ref['path'])
        require(digest(linked_raw) == ref['sha256'], 'EXAONE_CPU_REFERENCE_HASH_MISMATCH')
    return {'runtime_variant': RUNTIME_VARIANT, 'model_id': MODEL_ID, 'model_revision': REVISION,
            'manifest_sha256': MANIFEST_SHA, 'cpu_proof_sha256': proof_sha,
            'cpu_proof_kind': proof['kind'], 'chat_template_sha256': TEMPLATE_SHA,
            'original_embedded_template_sha256': ORIGINAL_TEMPLATE_SHA,
            'effective_chat_template_sha256': TEMPLATE_SHA, 'runtime_launcher_sha256': LAUNCHER_SHA,
            'chat_template_override': override_contract, 'template_render_parity': render_parity,
            'tokenizer_json_sha256': TOKENIZER_SHA,
            'official_reference_limitation': dict(OFFICIAL_REFERENCE_LIMITATION),
            'template_proof_variant': TEMPLATE_VARIANT, 'official_hf_equivalence': official_hf_failure,
            'context_tokenizer': 'native_raw_unicode_no_nfc_repair',
            'official_fixture_sha256': OFFICIAL_FIXTURE_SHA,
            'application_input_output_nfc_repair': False,
            'cpu_proof_refs': proof['proof_refs'], 'cpu_source_sha256': proof['source_sha256'],
            'cpu_checks_rerun': False, 'tokenizer_contract_status': TOKENIZER_CONTRACT_STATUS}


def cpu_provenance(config, proof_path, proof_sha):
    """Consume exact actual CPU evidence only; no CPU/native/model rerun here."""
    provenance = validate_cpu_common_fields(config, proof_path, proof_sha)
    proof, _ = read_json(proof_path)
    expected_raw = {'reference_kind':REFERENCE_KIND,
        'fixture_ref':{'path':PROOF_DIR+'raw-reference-diagnostic.json','sha256':RAW_FIXTURE_SHA},
        'proof_ref':{'path':PROOF_DIR+'raw-vocab-proof.json','sha256':RAW_VOCAB_SHA},
        'case_count':20,'id_match_count':20,'native_raw_roundtrip_count':20,
        'official_hf_equivalence':'NOT_ASSERTED_BY_DERIVED_REFERENCE'}
    require(proof['raw_reference'] == expected_raw
            and proof['cpu_binary_sha256'] == CPU_BINARY_SHA
            and proof['cpu_build_report_sha256'] == CPU_BUILD_SHA,
            'EXAONE_RAW_REFERENCE_AGGREGATE_MISMATCH')
    limitation = {'official_normalizer':'NFC','official_public_raw_roundtrip_count':18,
        'native_public_raw_roundtrip_count':20,'public_case_count':20,
        'global_unicode_roundtrip_guarantee':False}
    require(proof['normalization_limitation'] == limitation, 'EXAONE_UNICODE_LIMITATION_MISSING')
    fixture, fixture_raw = read_json(ROOT / expected_raw['fixture_ref']['path'])
    require(digest(fixture_raw) == RAW_FIXTURE_SHA
            and fixture['kind'] == 'EXAONE45_DERIVED_NO_NFC_PUBLIC_DIAGNOSTIC_REFERENCE'
            and fixture['status'] == 'DIAGNOSTIC_REFERENCE_ONLY_NOT_ADOPTED'
            and fixture['reference_kind'] == REFERENCE_KIND
            and fixture['official_fixture_sha256'] == OFFICIAL_FIXTURE_SHA
            and fixture['official_tokenizer_sha256'] == TOKENIZER_SHA
            and fixture['official_fixture_text_order_unchanged'] is True
            and fixture['case_count'] == fixture['raw_roundtrip_count'] == 20
            and fixture['official_id_difference_indices'] == [11,12]
            and fixture['application_input_output_nfc_repair'] is False,
            'EXAONE_RAW_FIXTURE_MISMATCH')
    public, raw = read_json(ROOT / expected_raw['proof_ref']['path'])
    require(digest(raw) == RAW_VOCAB_SHA, 'EXAONE_RAW_PUBLIC_HASH_MISMATCH')
    context, raw = read_json(ROOT / (PROOF_DIR+'vocab-context-raw-proof.json'))
    require(digest(raw) == RAW_CONTEXT_SHA, 'EXAONE_RAW_CONTEXT_HASH_MISMATCH')
    for observed, kind in ((public,'EXAONE45_NATIVE_RAW_REFERENCE_PUBLIC_CPU_PROOF'),
                           (context,'EXAONE45_NATIVE_RAW_VOCAB_CONTEXT_CPU_PROOF')):
        require(observed['kind'] == kind and observed['status'] == 'PASS'
                and observed['runtime_variant'] == RUNTIME_VARIANT
                and observed['model_id'] == MODEL_ID and observed['revision'] == REVISION
                and observed['gguf_sha256'] == MODEL_SHA and observed['header_sha256'] == HEADER_SHA
                and observed['source_pin'] == config.source_commit
                and observed['binary_sha256'] == CPU_BINARY_SHA
                and observed['build_report_sha256'] == CPU_BUILD_SHA
                and observed['official_fixture_sha256'] == OFFICIAL_FIXTURE_SHA
                and observed['official_native_failure_sha256'] == OFFICIAL_VOCAB_SHA
                and observed['raw_reference_sha256'] == RAW_FIXTURE_SHA
                and observed['reference_kind'] == REFERENCE_KIND
                and observed['official_hf_equivalence'] == 'FAIL_18_OF_20_PRESERVED'
                and observed['original_embedded_template_sha256'] == ORIGINAL_TEMPLATE_SHA
                and observed['effective_template_sha256'] == TEMPLATE_SHA
                and observed['application_input_output_nfc_repair'] is False
                and all(type(observed[k]) is int and observed[k] == 0
                        for k in ('model_inference_calls','gpu_calls','http_calls')),
                'EXAONE_RAW_ACTUAL_PROOF_MISMATCH')
    require(len(context['native_checks']) == 2 and context['splits'] == proof['splits']
            and context['raw_public_proof_ref'] == expected_raw['proof_ref']
            and context['max_output_tokens'] == 768 and context['max_context_tokens'] == 4096
            and context['input_bodies_gold_token_ids_saved'] is False
            and context['gold_fields_scored'] is False, 'EXAONE_RAW_CONTEXT_BINDING_MISMATCH')
    all_native = [public['native'], *context['native_checks']]
    for native in all_native:
        require(native['status'] == 'PASS' and native['reference_kind'] == 'derived_hf_nfc_disabled'
                and native['reference_gate_pass'] is True
                and native['official_hf_equivalence'] == 'NOT_ASSERTED_BY_DERIVED_REFERENCE'
                and all(type(native[k]) is int and native[k] == 20 for k in
                    ('tokenizer_cases_checked','tokenizer_id_match_count',
                     'tokenizer_native_raw_roundtrip_count','tokenizer_reference_ids_raw_roundtrip_count'))
                and native['tokenizer_id_mismatch_mask'] == native['tokenizer_native_raw_mismatch_mask'] == 0
                and native['tokenizer_reference_parity'] == 'PASS'
                and native['embedded_original_template_exact_match'] is True
                and native['effective_override_vocab_render_exact'] is True
                and native['derived_native_system_and_user_exact'] is True
                and native['derived_native_prompt_equals_official_reference'] is True
                and native['native_request_prompt_bytes'] == 9176
                and native['all_context_system_user_bytes_exact'] is True
                and native['native_vocab_grammar_cases_accepted'] == 20
                and native['native_vocab_grammar_cases_rejected'] == 40
                and native['native_vocab_grammar_eog_checked'] is True
                and native['model_context_created'] is False
                and native['backend_init_called'] is False
                and native['weight_tensors_loaded'] is False,
                'EXAONE_RAW_NATIVE_OBSERVATION_MISMATCH')
    for name, native in zip(CONTEXT_SPLITS, context['native_checks'], strict=True):
        row = proof['splits'][name]
        require(all(native[k] == row[k] for k in
                ('input_count','min_input_tokens','max_input_tokens','max_input_plus_output')),
                'EXAONE_RAW_CONTEXT_COUNTS_MISMATCH')
    token = {'text':' ','token_id':582,'native_token_count':1,'native_roundtrip':True}
    require(proof['resource_probe_token'] == context['resource_probe_token'] == token
            and all(type(n['resource_probe_token_id']) is int and n['resource_probe_token_id'] == 582
                    and n['resource_probe_token_count'] == 1 and n['resource_probe_raw_roundtrip'] is True
                    for n in all_native), 'EXAONE_RESOURCE_TOKEN_MISMATCH')
    provenance.update(raw_reference=expected_raw, normalization_limitation=limitation,
        tokenizer_contract='native_raw_unicode_no_nfc_repair',
        tokenizer_contract_status=TOKENIZER_CONTRACT_STATUS,
        official_reference_fixture_ref=proof['official_reference_fixture_ref'])
    return provenance, token['token_id']


def validate_health_models_props(config, health, models, props):
    require(health == {'status': 'ok'}, 'HEALTH_FAILED')
    rows = models.get('data')
    require(type(rows) is list and len(rows) == 1 and rows[0]['id'] == config.served_model_name
            and type(rows[0]['meta']['n_ctx']) is int and rows[0]['meta']['n_ctx'] == 4096,
            'MODELS_MISMATCH')
    require(props['model_alias'] == config.served_model_name and type(props['total_slots']) is int
            and props['total_slots'] == 1 and props['model_path'] == str(base.checked_file(config.model_path, ROOT))
            and type(props['default_generation_settings']['n_ctx']) is int
            and props['default_generation_settings']['n_ctx'] == 4096
            and type(props['chat_template']) is str
            and len(props['chat_template'].encode()) == PROPS_TEMPLATE_BYTES
            and digest(props['chat_template'].encode()) == PROPS_TEMPLATE_SHA
            and props['is_sleeping'] is False, 'PROPS_MISMATCH')
    return {'health_http_status': 200, 'models_http_status': 200, 'props_http_status': 200,
            'served_model': config.served_model_name, 'model_path': props['model_path'],
            'max_model_len': 4096, 'max_sequences': 1, 'chat_template_sha256': TEMPLATE_SHA,
            'embedded_chat_template_sha256': ORIGINAL_TEMPLATE_SHA, 'embedded_chat_template_bytes': EMBEDDED_TEMPLATE_BYTES,
            'effective_chat_template_sha256': TEMPLATE_SHA, 'effective_chat_template_bytes': OVERRIDE_BYTES,
            'props_reported_template_sha256': PROPS_TEMPLATE_SHA,
            'props_reported_template_bytes': PROPS_TEMPLATE_BYTES,
            'props_template_derivation': 'Pinned f072 Jinja lexer removes exactly one terminal LF from this no-CR template; no application input/output repair'}


def make_metadata(config, platform, config_sha, startup_sha, listener_sha):
    require(set(platform) == {'compiler', 'cmake', 'cuda', 'driver', 'gpu', 'gpu_uuid'}, 'PLATFORM_FIELDS_INVALID')
    return base.native_runtime_metadata({**platform, 'runtime_kind': 'llama_cpp', 'profile': 'a100',
        'llama_cpp_commit': config.source_commit, 'cuda_architecture': '80-real', 'physical_gpu': 3,
        'logical_gpu': 0, 'max_model_len': 4096, 'max_sequences': 1, 'quantization': 'Q4_K_M',
        'enable_reasoning': False, 'reasoning_parser': 'deepseek', 'binary_sha256': config.binary_sha256,
        'source_provenance_sha256': config.source_report_sha256, 'build_report_sha256': config.build_report_sha256,
        'gguf_sha256': config.model_sha256, 'gguf_header_sha256': config.model_header_report_sha256,
        'chat_template_sha256': TEMPLATE_SHA, 'launch_config_sha256': config_sha,
        'startup_report_sha256': startup_sha, 'listener_report_sha256': listener_sha})


def begin(config_path, config_sha, cpu_proof_path, cpu_proof_sha, *, timeout=0):
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    config, config_raw = load_config(config_path, config_sha)
    provenance, token_id = cpu_provenance(config, cpu_proof_path, cpu_proof_sha)
    artifacts = exaone_binding(config)
    before, before_raw = read_json(config.report_file)
    validate_guard(config, before, artifacts)
    require(type(timeout) is int and 0 <= timeout <= 1800
            and config.max_seconds - before['elapsed_seconds'] >= timeout + 30, 'INSUFFICIENT_GUARD_TIME')
    listeners = epoch(config, before['child_pid'])
    return config, config_raw, provenance, token_id, artifacts, before, before_raw, listeners


def finish(config, config_sha, artifacts, before, before_raw, first):
    listeners = epoch(config, before['child_pid'], first['process_start_ticks'])
    after, after_raw = read_json(config.report_file)
    validate_guard(config, after, artifacts)
    require((before['started_at_utc'], before['child_pid']) == (after['started_at_utc'], after['child_pid'])
            and after['elapsed_seconds'] >= before['elapsed_seconds'], 'GUARD_EPOCH_CHANGED')
    fields = {'launch_config_sha256': config_sha, 'pid': before['child_pid'],
              'process_start_ticks': first['process_start_ticks'], 'guard_started_at_utc': before['started_at_utc'],
              'guard_before_sha256': digest(before_raw), 'guard_after_sha256': digest(after_raw),
              'listener_report_sha256': digest(encoded(listeners))}
    return fields, after, after_raw, listeners


def capture_startup(config_path, config_sha, platform, *, cpu_proof_path, cpu_proof_sha):
    config, config_raw, provenance, _, artifacts, before, before_raw, first = begin(
        config_path, config_sha, cpu_proof_path, cpu_proof_sha, timeout=30)
    health, _ = request_json(config.port, '/health')
    models, _ = request_json(config.port, '/v1/models')
    props, _ = request_json(config.port, '/props')
    summary = validate_health_models_props(config, health, models, props)
    fields, _, after_raw, listeners = finish(config, config_sha, artifacts, before, before_raw, first)
    startup = {**summary, **provenance, **fields, 'kind': 'EXAONE45_NATIVE_STARTUP_HTTP_PROOF', 'status': 'PASS',
        'at_utc': datetime.now(timezone.utc).isoformat(), 'http_get_calls': 3, 'model_inference_calls': 0,
        'resource_report_sha256': digest(after_raw), 'native_identity_verified': True,
        'raw_http_bodies_saved': False, 'installed_small_artifacts_rehashed': True,
        'gguf_binding': 'Live guard full hash + pinned header + current owned file size; no second full hash',
        'platform_facts_scope': 'Root-supplied measured platform facts; HTTP is not hardware attestation'}
    startup_raw, listener_raw = encoded(startup), encoded(listeners)
    metadata = make_metadata(config, platform, config_sha, digest(startup_raw), digest(listener_raw))
    return {'launch_config.json': config_raw, 'resource_report.json': after_raw,
            'listeners.json': listener_raw, 'startup.json': startup_raw, 'runtime_metadata.json': encoded(metadata)}


def public_smoke(config_path, config_sha, *, cpu_proof_path, cpu_proof_sha, timeout=120):
    from neurobuild.infrastructure.local_model import LocalRequirementClient
    from neurobuild.domain.errors import DomainError
    config, _, provenance, _, artifacts, before, before_raw, first = begin(
        config_path, config_sha, cpu_proof_path, cpu_proof_sha, timeout=timeout)
    client = LocalRequirementClient(f'http://127.0.0.1:{config.port}', config.served_model_name,
        prompt_path=ROOT / 'prompts/requirement_generation_v2_v2.txt',
        schema_path=ROOT / 'schemas/requirement_generation_v2_decision_branches.schema.json',
        generation_contract='2.0', protocol='llama_cpp_json_schema', sampling_profile=PROFILE,
        max_tokens=768, timeout=timeout)
    started = time.monotonic()
    try:
        result = client.extract(PUBLIC_SOURCE, requirement_id=UUID(int=1), project_id=UUID(int=2),
                                base_revision_id=UUID(int=3), axis_convention='project_xy')
        ok = (result.status.value == 'READY' and result.operation.dx.metres == 1
              and result.operation.dy.metres == 0 and result.target_description == '검사실 책상')
        status, code = ('PASS', None) if ok else ('FAIL', 'PUBLIC_SEMANTIC_MISMATCH')
    except DomainError as error:
        status, code = 'FAIL', error.code
    elapsed = time.monotonic() - started
    fields, _, _, _ = finish(config, config_sha, artifacts, before, before_raw, first)
    return {**provenance, **fields, 'kind': 'EXAONE45_NATIVE_PUBLIC_PRODUCTION_SMOKE',
            'status': status, 'error_code': code, 'http_calls_attempted': 1, 'elapsed_seconds': elapsed,
            'sampling_profile': PROFILE, 'source': 'PUBLIC_SYNTHETIC_CPU_FIXTURE',
            'generated_body_retained': False, 'quality_gate_pass': False}


def run_resource_smoke(config_path, config_sha, *, cpu_proof_path, cpu_proof_sha, timeout=900):
    config, _, provenance, token_id, artifacts, before, before_raw, first = begin(
        config_path, config_sha, cpu_proof_path, cpu_proof_sha, timeout=timeout)
    payload = resource_payload(token_id)
    value, elapsed = request_json(config.port, '/completion', payload, timeout=timeout, max_bytes=8192)
    summary = validate_resource(value)
    fields, after, _, _ = finish(config, config_sha, artifacts, before, before_raw, first)
    return {**summary, **provenance, **fields, 'kind': 'EXAONE45_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE', 'status': 'PASS',
            'http_post_calls': 1, 'elapsed_seconds': elapsed,
            'request_sha256': digest(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()),
            'guard_minimum_observed_free_mib': after['minimum_observed_free_mib'],
            'guard_aggregate_peak_mib': after['observed_baseline_relative_peak_mib'],
            'guard_required_free_floor_mib': after['required_free_floor_mib'],
            'guard_aggregate_increment_limit_mib': after['aggregate_increment_limit_mib'],
            'lifetime_aggregate_values_not_probe_isolated': True}
