"""Freeze the user-directed V2 80x1 evaluation; no model calls or data parsing."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/home/a202192020/NeuroBuild_v2')
OUT = 'evaluations/hardening_v2_native_qwen38_minimal_freeze.json'
BASE = 'evaluations/hardening_v1_exposed_native_qwen38_diagnostic_freeze.json'
BASE_SHA = '7a1f67bd71c65f0c2d2aacc2b03cb765d7c38ac8eaa31bf7618847c4a5380fd9'
ADD = 'evaluations/hardening_v2_minimal_execution_addendum.json'
ADD_SHA = '2f68f0dc224b937b597f8e2e7ec82e120edc1f0daf400d6f6ea5bca0aa40fd98'
DATASET = 'evaluations/requirement_hardening_v2_holdout.jsonl'
DATASET_SHA = '7416f05613b1490358672f3926770dbd8653e676577eeee6ba65f863b27cec40'
DIAGNOSTIC = 'evaluations/results/phase5x/exposed-native-qwen38-diagnostic/'
BUNDLE = 'evaluations/results/phase5x/qwen38-native-minimal-epoch6/'
ATTESTER = 'var/research/attest_native_epoch6_minimal.py'
ATTESTER_SHA = '1ef8accbe06fe683d7e953d61dd928e925371269a37ece6cb830755b97ba7930'
CONFIG_SHA = '5ceebfc420edf9b262208c7afdd9511a00132f1d7221e4a91bb3c636c93b7b31'
PROBE_SHA = 'ac100df7949b2b14a517c4568fa66369bd98c599b39507ef19f873490a0f9f63'
PLAN = 'docs/native_qwen38_v2_minimal_plan.md'
REPLAY = 'var/review-tools/replay_native_qwen38_v2_minimal.py'
REPLAY_SHA = '9bc2ec91b085d680f20cd3c2663e599e8cb1a446e376c40c546c4e9808125866'
REPLAY_PROOF = 'var/research/native-v2-minimal-replay-selfcheck-9eed62037c75400785a81da09004c988.json'
REPLAY_PROOF_SHA = '41c9a274c1e8ede37a26b00e12cac37722e6f7a0a4817b5baee8dc17c2150c58'
ATTESTER_PROOF = 'var/research/native-epoch6-minimal-attestation-cpu-proof.json'
ATTESTER_PROOF_SHA = '93997fc095f5ee90bb854e6244e8d6bf6c39ddcf7219c13c85d71c28468c10a6'
GATES = {'schema_required': 80, 'schema_denominator': 80,
         'semantic_required_at_least': 76, 'semantic_denominator': 80,
         'critical_model_ready_fp_required': 0, 'critical_model_ready_fp_denominator': 40,
         'unsafe_accepted_ready_total_required': 0, 'unsafe_accepted_ready_total_denominator': 80,
         'raw_decision_observation_required': 80}


def require(ok, code):
    if not ok:
        raise ValueError(code)


def file(name):
    p = ROOT / name
    require(not p.is_symlink() and p.resolve().is_relative_to(ROOT) and p.is_file(), 'PATH_INVALID')
    return p


def digest(name):
    return hashlib.sha256(file(name).read_bytes()).hexdigest()


def load(name):
    return json.loads(file(name).read_bytes())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, file(path))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def validate_current(*, required_remaining_seconds=3150):
    require(type(required_remaining_seconds) is int and required_remaining_seconds in (0, 3150),
            'INVALID_REMAINING_TIME_CHECK')
    require(digest('var/research/native_runtime_probe.py') == PROBE_SHA, 'PROBE_CHANGED')
    p = module('v2_freeze_native_probe', 'var/research/native_runtime_probe.py')
    require(digest(ATTESTER) == ATTESTER_SHA, 'ATTESTER_CHANGED')
    a = module('v2_freeze_attester', ATTESTER)
    require(a.validate_saved_bundle(p, ROOT / BUNDLE)['status'] == 'PASS', 'SAVED_BUNDLE_INVALID')
    config, raw = p.load_config(file(BUNDLE + 'launch_config.json'), CONFIG_SHA)
    artifacts = p.binding(config)
    carry, platform, provenance = a.historical_contract(p, config, raw, artifacts)
    saved_carry = load(BUNDLE + 'contract_carry_forward.json')
    require(carry == saved_carry, 'CARRY_FORWARD_CHANGED')
    observed = load(BUNDLE + 'attestation.json')
    require(observed['kind'] == 'NATIVE_MINIMAL_EPOCH_ATTESTATION' and observed['status'] == 'PASS'
            and observed['http_get_calls'] == 1 and observed['health_http_status'] == 200
            and observed['health_status'] == 'ok' and observed['native_identity_verified'] is True,
            'CURRENT_ATTESTATION_INVALID')
    for key in ('model_inference_calls', 'full_startup_probe_calls', 'public_model_calls',
                'resource_model_calls', 'cpu_tests_rerun'):
        require(observed[key] == 0, 'UNEXPECTED_TEST_REPEAT')
    require(observed['raw_http_bodies_saved'] is False and observed['launch_config_sha256'] == CONFIG_SHA
            and observed['carry_forward_sha256'] == digest(BUNDLE + 'contract_carry_forward.json')
            and observed['listener_report_sha256'] == digest(BUNDLE + 'listeners.json')
            and observed['guard_before_sha256'] == digest(BUNDLE + 'guard_before.json')
            and observed['guard_after_sha256'] == digest(BUNDLE + 'guard_after.json'), 'CURRENT_HASH_BINDING_FAILED')
    for key, value in provenance.items():
        require(observed[key] == value, 'CURRENT_TOKENIZER_CHANGED')
    for suffix in ('guard_before.json', 'guard_after.json'):
        report = load(BUNDLE + suffix)
        p.validate_guard(config, report, artifacts)
        require(report['child_pid'] == observed['pid']
                and report['started_at_utc'] == observed['guard_started_at_utc'], 'CURRENT_EPOCH_CHANGED')
    listeners = load(BUNDLE + 'listeners.json')
    require(listeners['verdict'] == 'PASS' and listeners['all_loopback'] is True
            and listeners['snapshot_complete'] is True and listeners['uid'] == os.getuid()
            and listeners['pid'] == observed['pid']
            and listeners['process_start_ticks'] == observed['process_start_ticks'], 'CURRENT_LISTENER_CHANGED')
    metadata = load(BUNDLE + 'runtime_metadata.json')
    require(p.make_metadata(config, platform, CONFIG_SHA, digest(BUNDLE + 'attestation.json'),
            digest(BUNDLE + 'listeners.json')) == metadata, 'CURRENT_METADATA_CHANGED')
    live, live_raw = p.read_json(config.report_file)
    p.validate_guard(config, live, artifacts)
    require(live['child_pid'] == observed['pid'] and live['started_at_utc'] == observed['guard_started_at_utc'],
            'LIVE_EPOCH_CHANGED')
    current_listeners = p.epoch(config, observed['pid'], observed['process_start_ticks'])
    require(config.max_seconds == 3600 and config.max_seconds - live['elapsed_seconds'] >= required_remaining_seconds,
            'INSUFFICIENT_PLANNED_TIME')
    return config, carry, provenance, observed, live, live_raw, current_listeners


def validate_prerequisites():
    require(digest(REPLAY) == REPLAY_SHA and digest(REPLAY_PROOF) == REPLAY_PROOF_SHA
            and digest(ATTESTER) == ATTESTER_SHA and digest(ATTESTER_PROOF) == ATTESTER_PROOF_SHA,
            'PREPARATION_SOURCE_OR_PROOF_CHANGED')
    replay_proof, attester_proof = load(REPLAY_PROOF), load(ATTESTER_PROOF)
    require(replay_proof['status'] == 'PASS_SYNTHETIC_PREPARATION_ONLY'
            and replay_proof['helper_sha256'] == REPLAY_SHA
            and attester_proof['status'] == 'PASS' and attester_proof['tests'] == 10
            and attester_proof['errors'] == attester_proof['failures'] == 0,
            'PREPARATION_TESTS_REQUIRED')
    for name, sha in attester_proof['sha256'].items():
        require(digest(name) == sha, 'ATTESTER_TEST_SOURCE_CHANGED')
    require(digest(BASE) == BASE_SHA and digest(ADD) == ADD_SHA and digest(DATASET) == DATASET_SHA,
            'PREREQUISITE_CHANGED')
    base, add = load(BASE), load(ADD)
    for name, sha in base['sha256'].items():
        require(digest(name) == sha, 'DIAGNOSTIC_FROZEN_INPUT_CHANGED')
    require(add['gate_targets'] == GATES and add['checkpoint_commit'] == '704e9f6eaacadeb445c70a09ea5e1a07db0778f5'
            and add['replacement_execution_protocol']['expected_http_calls'] == 85
            and add['replacement_execution_protocol']['trials_per_case'] == 1, 'USER_OVERRIDE_CHANGED')
    v2 = load('evaluations/hardening_v2_dataset_freeze.json')
    require(len(v2['sha256']) == 9 and digest('evaluations/hardening_v2_dataset_freeze.json') ==
            add['prior_dataset_freeze_sha256'], 'V2_FREEZE_CHANGED')
    for name, sha in v2['sha256'].items():
        require(digest(name) == sha, 'V2_ARTIFACT_CHANGED')
    require(digest(DIAGNOSTIC + 'results.json') == 'e16c753dd9701f1115a8d56445f27f68835e20b9323787316db776606769da48'
            and digest(DIAGNOSTIC + 'independent_replay.json') ==
            '6a9ce259b60348504cfa1afec9ddb7838d30190e46b88f2b1ab33917e46836ab', 'DIAGNOSTIC_PROOF_CHANGED')
    replay = load(DIAGNOSTIC + 'independent_replay.json')
    require(replay['status'] == replay['diagnostic_gate'] == 'PASS' and replay['trials'] == 120
            and replay['warmups'] == 5 and replay['source_snapshot_commit'] ==
            'bec9000e697c6b4930d077822ae30ca484a395ba'
            and replay['native_freeze_sha256'] == BASE_SHA
            and replay['retained_generation_json_replayed'] == {'warmups': 5, 'trials': 120},
            'FIRST_QUALITY_GATE_REQUIRED')
    return base, v2


def main():
    require(not (ROOT / OUT).exists(), 'FREEZE_ALREADY_EXISTS')
    base, v2 = validate_prerequisites()
    config, carry, provenance, observed, live, _, _ = validate_current()
    files = set(base['sha256']) | set(v2['sha256']) | {BASE, ADD, DATASET, PLAN, REPLAY, ATTESTER,
        'var/research/freeze_native_qwen38_v2_minimal.py', DIAGNOSTIC + 'results.json',
        DIAGNOSTIC + 'independent_replay.json', DIAGNOSTIC + 'checkpoint_regression.json'}
    files.update({REPLAY_PROOF, ATTESTER_PROOF})
    files.update(carry['historical_paths'])
    files.update(carry['unchanged_source_sha256'])
    for folder in (BUNDLE, 'evaluations/results/phase5x/qwen38-native-v2-minimal-preparation/'):
        require((ROOT / folder).is_dir(), 'PREPARATION_ARCHIVE_REQUIRED')
        files.update(str(p.relative_to(ROOT)) for p in (ROOT / folder).rglob('*') if p.is_file())
    frozen = {key: base[key] for key in ('candidate_variant', 'gold_status', 'pipeline', 'generation_contract',
        'model_id', 'model_revision', 'tokenizer_revision', 'served_model', 'prompt', 'generation_schema',
        'canonical_schema', 'protocol', 'sampling_profile', 'sampling_request_parameters', 'enable_thinking',
        'reasoning_parser', 'max_tokens', 'timeout_seconds', 'max_model_len', 'concurrency',
        'maximum_calls_per_case', 'decision_policy')}
    frozen.update(lifecycle='FROZEN_BEFORE_NATIVE_QWEN38_V2_MINIMAL_HOLDOUT',
        frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        source_ancestor_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        tokenizer_contract=provenance, dataset=DATASET, split='heldout', cases=80, ready_gold=40,
        nonready_gold=40, warmups_per_run=5, trials_per_case=1, expected_http_calls=85,
        gate_targets=GATES, minimal_execution_addendum=ADD,
        runtime_metadata=BUNDLE + 'runtime_metadata.json', launch_config=BUNDLE + 'launch_config.json',
        current_attestation=BUNDLE + 'attestation.json', current_carry_forward=BUNDLE + 'contract_carry_forward.json',
        runtime_epoch_snapshot={'pid': observed['pid'], 'start_ticks': observed['process_start_ticks'],
                                'guard_started_at_utc': observed['guard_started_at_utc']},
        time_budget={'model_calls': 85, 'planned_seconds_per_call': 30, 'reserve_seconds': 600,
            'required_remaining_seconds': 3150, 'guard_max_seconds': 3600,
            'elapsed_seconds_at_freeze': live['elapsed_seconds'],
            'remaining_seconds_at_freeze': 3600 - live['elapsed_seconds'],
            'must_recheck_after_push_immediately_before_first_warmup': True,
            'notice': 'Operational estimate, not a latency or completion guarantee.'},
        first_gate_reference={'results': DIAGNOSTIC + 'results.json',
            'independent_replay': DIAGNOSTIC + 'independent_replay.json', 'status': 'PASS'},
        historical_runtime_validation='Epoch4 contract/public/resource proofs reused; no new public/resource or CPU suite calls.',
        limits=['User-directed80x1 replaces historical80x3 without changing threshold percentages.',
            'V2 model outputs unseen before firstwarmup; priorroot input exposure remains.',
            'No input/outputNFC repair,selective retry,preview,or gold/parser/scorer/prompt change.',
            'No claim of repeated model-output identity,human verification,or RTX5090 validation.'],
        sha256={name: digest(name) for name in sorted(files)})
    with (ROOT / OUT).open('x') as stream:
        json.dump(frozen, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'status': 'FROZEN_NOT_EVALUATED', 'path': OUT, 'sha256': digest(OUT),
                      'frozen_files': len(files), 'runtime_pid': observed['pid']}))


if __name__ == '__main__':
    main()
