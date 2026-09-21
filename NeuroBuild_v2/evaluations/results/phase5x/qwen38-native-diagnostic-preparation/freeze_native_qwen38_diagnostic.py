"""Freeze one exposed native diagnostic after completed CPU/runtime proofs.

No launch, model call or dataset parsing. Dataset bytes are hashed only.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path('/home/a202192020/NeuroBuild_v2')
OUT = ROOT / 'evaluations/hardening_v1_exposed_native_qwen38_diagnostic_freeze.json'
CPU = 'var/reports/native-contract-raw-cpu-context.json'
START = 'evaluations/results/phase5x/qwen38-native-startup-epoch4/'
PUBLIC = 'evaluations/results/phase5x/qwen38-native-public-smoke-epoch4/report.json'
RESOURCE = 'evaluations/results/phase5x/qwen38-native-resource-epoch4/report.json'
VARIANT = 'qwen38-gguf-raw-unicode-v1'
REV = 'efbb3b1f70a21d97fd4495240648405f7228554f'
DATASET = 'evaluations/requirement_hardening_v1_exposed_regression.jsonl'
PROMPT = 'prompts/requirement_generation_v2_v2.txt'
SCHEMA = 'schemas/requirement_generation_v2_decision_branches.schema.json'
BASE = 'evaluations/hardening_v1_exposed_generation2_32b_thinking_diagnostic_freeze.json'
FIXED = {
    DATASET: '7e5b9a05932df7aafdbf683655b044b3e3b25cbffb4115d298e1490aecbc7a5b',
    PROMPT: '99d737124372836ba5f985fa6e5570afef693e769798844931f000fb21403cf6',
    SCHEMA: '36d42b9fa3d24f4a1bc1d14381110e36e8d89103b696bc83113be006b64934e2',
    'schemas/semantic_requirement.schema.json': 'dd131db08fe9087e795059445b075f22876e44b42481201cc0ea70608a708f94',
    'schemas/requirement_generation_v2.schema.json': '6ca6fed3e8666244cd4bd779d33c0dd647490d5f641134307930008ea440436c',
    'src/neurobuild/application/requirements.py': 'a940f3952c0c4133ab51732f6abf76516d8ff66617470545222b52adfa49fb4a',
    'src/neurobuild/application/requirement_generation.py': 'fcba16f6adc906923859f3bcf4ae2f680e76716863a759582167cd9326f03198',
    'src/neurobuild/infrastructure/local_model.py': '3ebef3a1b3cf16b577566c7644952ac5da0def1d1dc11cc0d0b01c581b9d9f1c',
    'runtime/models/qwen38-27b-q4-k-m.json': 'e67de5e421d7de1b2c332506474bc96812b9450a4fe56438b9eb3f64d9d554ed',
}


def require(ok, code):
    if not ok:
        raise ValueError(code)


def digest(name):
    path = ROOT / name
    require(path.resolve().is_relative_to(ROOT) and not path.is_symlink(), 'PATH_INVALID')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((ROOT / name).read_bytes())


def main():
    require(not OUT.exists(), 'FREEZE_ALREADY_EXISTS')
    for name, expected in FIXED.items():
        require(digest(name) == expected, 'FIXED_INPUT_CHANGED')
    spec = importlib.util.spec_from_file_location('native_probe_freeze', ROOT / 'var/research/native_runtime_probe.py')
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    config, _ = probe.load_config(ROOT / START / 'launch_config.json',
        'a8f6891e96f0567820a8029ba4ea8d689e01a842c888a9b09482f1e724e5d052')
    provenance = probe.raw_context_provenance(ROOT / CPU, digest(CPU), runtime_variant=VARIANT,
        model_sha=config.model_sha256, header_sha=config.model_header_report_sha256)
    startup, metadata = load(START + 'startup.json'), load(START + 'runtime_metadata.json')
    require(startup['status'] == 'PASS' and startup['kind'] == 'NATIVE_STARTUP_HTTP_PROOF', 'STARTUP_REQUIRED')
    for key, value in provenance.items():
        require(startup[key] == value, 'STARTUP_TOKENIZER_BINDING_FAILED')
    require(metadata['startup_report_sha256'] == digest(START + 'startup.json')
            and metadata['listener_report_sha256'] == digest(START + 'listeners.json')
            and metadata['launch_config_sha256'] == digest(START + 'launch_config.json')
            and startup['resource_report_sha256'] == digest(START + 'resource_report.json'), 'STARTUP_HASH_BINDING_FAILED')
    platform = {key: metadata[key] for key in ('compiler', 'cmake', 'cuda', 'driver', 'gpu', 'gpu_uuid')}
    require(probe.make_metadata(config, platform, digest(START + 'launch_config.json'),
            digest(START + 'startup.json'), digest(START + 'listeners.json')) == metadata, 'RUNTIME_METADATA_MISMATCH')
    public, resource = load(PUBLIC), load(RESOURCE)
    require(public['status'] == 'PASS' and public['http_calls_attempted'] == 1
            and public['quality_gate_pass'] is False and public['generated_body_retained'] is False, 'PUBLIC_SMOKE_REQUIRED')
    require(resource['status'] == 'PASS' and resource['kind'] == 'NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE'
            and resource['http_post_calls'] == 1, 'RESOURCE_SMOKE_REQUIRED')
    probe.validate_resource({key: resource[key] for key in probe.RESOURCE_FIELDS})
    for proof in (public, resource):
        for key, value in provenance.items():
            require(proof[key] == value, 'SMOKE_TOKENIZER_BINDING_FAILED')
    artifacts = probe.binding(config)
    snapshot = load(START + 'resource_report.json')
    probe.validate_guard(config, snapshot, artifacts)
    listeners = load(START + 'listeners.json')
    require(listeners['verdict'] == 'PASS' and listeners['all_loopback'] is True
            and listeners['snapshot_complete'] is True and listeners['uid'] == os.getuid()
            and listeners['pid'] == startup['pid'] == snapshot['child_pid']
            and listeners['process_start_ticks'] == startup['process_start_ticks'], 'STARTUP_EPOCH_BINDING_FAILED')
    live, _ = probe.read_json(config.report_file)
    probe.validate_guard(config, live, artifacts)
    require(live['child_pid'] == startup['pid'] and live['started_at_utc'] == snapshot['started_at_utc'],
            'GUARD_EPOCH_CHANGED')
    probe.epoch(config, live['child_pid'], startup['process_start_ticks'])
    for proof in (public, resource):
        require(proof['launch_config_sha256'] == digest(START + 'launch_config.json')
                and proof['pid'] == startup['pid']
                and proof['process_start_ticks'] == startup['process_start_ticks']
                and proof['guard_started_at_utc'] == live['started_at_utc'], 'SMOKE_EPOCH_CHANGED')
    v2 = load('evaluations/hardening_v2_dataset_freeze.json')
    require(len(v2['sha256']) == 9, 'V2_FREEZE_CHANGED')
    for name, expected in v2['sha256'].items():
        require(digest(name) == expected, 'V2_ARTIFACT_CHANGED')
    regression = load('evaluations/results/phase5x/native-runtime-batch64-preflight/backend-regression.json')
    require(regression['kind'] == 'NATIVE_RUNTIME_BACKEND_REGRESSION'
            and regression['status'] == 'PASS' and regression['tests'] == 386
            and all(regression[k] == 0 for k in ('skipped', 'errors', 'failures'))
            and all(regression[k] is True for k in ('postgresql_integration', 'ifcopenshell_integration', 'headless')),
            'REGRESSION_REQUIRED')
    require(regression['log_sha256'] == '99f216c628db8ee1164da51f98646f432b0ed961005e6002743ac8a49cd23370'
            and digest(regression['log_path']) == regression['log_sha256'], 'REGRESSION_LOG_CHANGED')
    require(re.search(r'Ran 386 tests in 19\.652s\s+OK\s*$', (ROOT / regression['log_path']).read_text()),
            'REGRESSION_LOG_INVALID')
    base = load(BASE)
    for name in ('schemas/semantic_requirement.schema.json', 'schemas/requirement_generation_v2.schema.json',
                 'evaluations/hardening_v2_dataset_freeze.json', 'evaluations/hardening_v2_input_exposure_addendum.json'):
        require(digest(name) == base['sha256'][name], 'BASELINE_CONTRACT_CHANGED')
    gates = {'schema_required': 120, 'schema_denominator': 120, 'semantic_required_at_least': 114,
        'semantic_denominator': 120, 'critical_model_ready_fp_required': 0,
        'critical_model_ready_fp_denominator': 58, 'unsafe_accepted_ready_total_required': 0,
        'unsafe_accepted_ready_total_denominator': 120}
    require(base['gate_targets'] == gates, 'QUALITY_GATE_CHANGED')
    import sys
    sys.path.insert(0, str(ROOT / 'src'))
    from neurobuild.infrastructure.local_model import LocalRequirementClient
    client = LocalRequirementClient('http://127.0.0.1:8003', config.served_model_name,
        prompt_path=ROOT / PROMPT, schema_path=ROOT / SCHEMA, generation_contract='2.0',
        protocol='llama_cpp_json_schema', sampling_profile='qwen38_nonthinking_llama_cpp',
        max_tokens=768, timeout=120)
    files = set(FIXED) | {CPU, PUBLIC, RESOURCE, BASE, 'docs/native_qwen38_quality_diagnostic_plan.md',
        'docs/native_qwen38_resource_plan.md', 'scripts/evaluate_requirements.py', 'scripts/llama_server.py',
        'scripts/native_model_bootstrap.py', 'scripts/model_guard.py', 'scripts/gpu_preflight.py',
        'scripts/verify_model_listeners.py', 'var/research/native_runtime_probe.py',
        'var/research/run_native_context_raw_cpu.py', 'var/research/freeze_native_qwen38_diagnostic.py',
        'evaluations/hardening_v2_dataset_freeze.json', 'evaluations/hardening_v2_input_exposure_addendum.json'}
    for folder in ('evaluations/results/phase5x/native-runtime-cpu-preflight', 'evaluations/results/phase5x/native-runtime-batch2-preflight', 'evaluations/results/phase5x/native-runtime-batch64-preflight', START):
        files.update(str(p.relative_to(ROOT)) for p in (ROOT / folder).rglob('*') if p.is_file())
    frozen = {'lifecycle': 'FROZEN_BEFORE_NATIVE_QWEN38_EXPOSED_DIAGNOSTIC',
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_ancestor_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'candidate_variant': VARIANT, 'tokenizer_contract': provenance,
        'gold_status': 'AUTO-GENERATED / NOT HUMAN VERIFIED', 'dataset': DATASET, 'split': 'development',
        'cases': 120, 'ready_gold': 62, 'nonready_gold': 58, 'warmups_per_run': 5, 'trials_per_case': 1,
        'expected_http_calls': 125, 'pipeline': 'single', 'generation_contract': '2.0',
        'model_id': 'ggml-org/Qwen3.8-27B-GGUF', 'model_revision': REV, 'tokenizer_revision': REV,
        'served_model': config.served_model_name, 'prompt': PROMPT, 'generation_schema': SCHEMA,
        'canonical_schema': 'schemas/semantic_requirement.schema.json',
        'protocol': 'llama_cpp_json_schema', 'sampling_profile': 'qwen38_nonthinking_llama_cpp',
        'sampling_request_parameters': client.sampling_parameters, 'enable_thinking': False,
        'reasoning_parser': 'deepseek', 'max_tokens': 768, 'timeout_seconds': 120,
        'max_model_len': 4096, 'concurrency': 1, 'maximum_calls_per_case': 1,
        'gate_targets': gates, 'runtime_metadata': START + 'runtime_metadata.json',
        'public_smoke_report': PUBLIC, 'resource_probe_report': RESOURCE,
        'runtime_epoch_snapshot': {'pid': startup['pid'], 'start_ticks': startup['process_start_ticks'],
                                  'guard_started_at_utc': live['started_at_utc']},
        'decision_policy': 'Raw final decision before validation; errors/truncation/unknown remain in denominator; no retry/repair/fallback.',
        'limits': ['Exposed regression, not unseen; v2 prior input exposure remains; no v2 model calls in this run.',
                   'Model/quantization/runtime/sampling change together; no isolated causal attribution.',
                   'Official HF tokenizer equivalence remains FAIL; raw Unicode native variant only.',
                   'No input/output NFC repair; strict quote/parser and quality gates unchanged.'],
        'regression': regression, 'sha256': {name: digest(name) for name in sorted(files)}}
    with OUT.open('x') as stream:
        json.dump(frozen, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': 'FROZEN_NOT_EVALUATED', 'path': str(OUT.relative_to(ROOT)),
                      'sha256': digest(OUT), 'candidate_variant': VARIANT}))


if __name__ == '__main__':
    main()
