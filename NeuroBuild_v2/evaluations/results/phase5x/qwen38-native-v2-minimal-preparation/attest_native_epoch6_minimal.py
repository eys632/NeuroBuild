"""Explicit epoch6 attestation: one health GET, zero model or GPU calls.

Historical CPU/startup/public/resource/regression evidence is checked and reused,
never rerun or relabelled as a fresh suite. No dataset body is read by this helper.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import stat

ROOT = Path('/home/a202192020/NeuroBuild_v2')
CONFIG = 'var/research/qwen38-native-launch-epoch6-minimal-v2.json'
CONFIG_SHA = '5ceebfc420edf9b262208c7afdd9511a00132f1d7221e4a91bb3c636c93b7b31'
OUT = ROOT / 'var/reports/qwen38-native-minimal-epoch6'
HELPER = 'var/research/native_runtime_probe.py'
HELPER_SHA = 'ac100df7949b2b14a517c4568fa66369bd98c599b39507ef19f873490a0f9f63'
FREEZE = 'evaluations/hardening_v1_exposed_native_qwen38_diagnostic_freeze.json'
FREEZE_SHA = '7a1f67bd71c65f0c2d2aacc2b03cb765d7c38ac8eaa31bf7618847c4a5380fd9'
START = 'evaluations/results/phase5x/qwen38-native-startup-epoch4/'
PUBLIC = 'evaluations/results/phase5x/qwen38-native-public-smoke-epoch4/report.json'
RESOURCE = 'evaluations/results/phase5x/qwen38-native-resource-epoch4/report.json'
REGRESSION = 'evaluations/results/phase5x/native-runtime-batch64-preflight/backend-regression.json'
CPU = 'var/reports/native-contract-raw-cpu-context.json'
ALLOWED_CHANGES = ['max_seconds', 'log_file', 'report_file']


def require(ok, code):
    if not ok:
        raise ValueError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_local(name, expected=None):
    path = ROOT / name
    info = path.lstat()
    require(not path.is_symlink() and path.resolve().is_relative_to(ROOT)
            and stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
            and info.st_size <= 2 * 1024 * 1024, 'INPUT_PATH_INVALID')
    raw = path.read_bytes()
    require(expected is None or digest(raw) == expected, 'INPUT_HASH_MISMATCH')
    return raw


def config_equivalence(old, new):
    require(set(old) == set(new), 'INFERENCE_CONFIG_CHANGED')
    changed = sorted(key for key in old if old[key] != new[key])
    require(changed == sorted(ALLOWED_CHANGES), 'INFERENCE_CONFIG_CHANGED')
    require(type(new['max_seconds']) is int and new['max_seconds'] == 3600
            and old['max_seconds'] == 10800
            and new['log_file'] == 'var/logs/qwen38-native-epoch6-minimal-v2.log'
            and new['report_file'] == 'var/reports/qwen38-native-epoch6-minimal-v2.json',
            'OPERATIONAL_CONFIG_CHANGED')
    return changed


def historical_contract(probe, config, config_raw, artifacts):
    frozen = json.loads(read_local(FREEZE, FREEZE_SHA))
    hashes = frozen['sha256']
    require(frozen['candidate_variant'] == probe.RUNTIME_VARIANT, 'VARIANT_CHANGED')
    # Only source/evidence hashes are opened here; neither exposed nor v2 data.
    sources = {name: sha for name, sha in hashes.items()
               if name.startswith(('scripts/', 'src/', 'schemas/', 'prompts/', 'runtime/models/'))
               or name in (HELPER, 'var/research/run_native_context_raw_cpu.py')}
    require(sources.get(HELPER) == HELPER_SHA, 'HELPER_BINDING_CHANGED')
    for name, sha in sources.items():
        read_local(name, sha)
    paths = [START + name for name in ('launch_config.json', 'startup.json', 'runtime_metadata.json',
                                       'listeners.json', 'resource_report.json')]
    paths += [PUBLIC, RESOURCE, CPU, REGRESSION]
    historical = {name: json.loads(read_local(name, hashes[name])) for name in paths}
    old = historical[START + 'launch_config.json']
    changes = config_equivalence(old, json.loads(config_raw))
    old_config, _ = probe.load_config(ROOT / START / 'launch_config.json', hashes[START + 'launch_config.json'])
    startup, metadata = historical[START + 'startup.json'], historical[START + 'runtime_metadata.json']
    public, resource_proof = historical[PUBLIC], historical[RESOURCE]
    provenance = frozen['tokenizer_contract']
    for proof in (startup, public, resource_proof):
        require(proof['status'] == 'PASS', 'HISTORICAL_PROOF_NOT_PASS')
        for key, value in provenance.items():
            require(proof[key] == value, 'HISTORICAL_TOKENIZER_CHANGED')
    require(startup['kind'] == 'NATIVE_STARTUP_HTTP_PROOF'
            and startup['http_get_calls'] == 3 and startup['model_inference_calls'] == 0
            and startup['resource_report_sha256'] == hashes[START + 'resource_report.json'],
            'HISTORICAL_STARTUP_INVALID')
    require(public['http_calls_attempted'] == 1 and public['quality_gate_pass'] is False
            and public['generated_body_retained'] is False, 'HISTORICAL_PUBLIC_INVALID')
    require(resource_proof['kind'] == 'NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE'
            and resource_proof['http_post_calls'] == 1, 'HISTORICAL_RESOURCE_INVALID')
    probe.validate_resource({key: resource_proof[key] for key in probe.RESOURCE_FIELDS})
    old_guard = historical[START + 'resource_report.json']
    probe.validate_guard(old_config, old_guard, artifacts)
    listeners = historical[START + 'listeners.json']
    require(listeners['verdict'] == 'PASS' and listeners['all_loopback'] is True
            and listeners['snapshot_complete'] is True and listeners['uid'] == os.getuid()
            and listeners['pid'] == startup['pid'] == old_guard['child_pid']
            and listeners['process_start_ticks'] == startup['process_start_ticks'],
            'HISTORICAL_EPOCH_CHANGED')
    for proof in (public, resource_proof):
        require(proof['launch_config_sha256'] == hashes[START + 'launch_config.json']
                and proof['pid'] == startup['pid']
                and proof['process_start_ticks'] == startup['process_start_ticks']
                and proof['guard_started_at_utc'] == old_guard['started_at_utc'],
                'HISTORICAL_EPOCH_CHANGED')
    platform = {key: metadata[key] for key in ('compiler', 'cmake', 'cuda', 'driver', 'gpu', 'gpu_uuid')}
    require(probe.make_metadata(old_config, platform, hashes[START + 'launch_config.json'],
            hashes[START + 'startup.json'], hashes[START + 'listeners.json']) == metadata,
            'HISTORICAL_METADATA_CHANGED')
    regression = historical[REGRESSION]
    require(regression['status'] == 'PASS' and regression['tests'] == 386
            and all(regression[key] == 0 for key in ('skipped', 'failures', 'errors')),
            'HISTORICAL_REGRESSION_CHANGED')
    # Explicitly carry the known official-HF mismatch; do not normalize it away.
    require(provenance['hf_equivalence']['status'] == 'FAIL'
            and provenance['hf_equivalence']['id_match_count'] == 19
            and provenance['raw_reference']['id_match_count'] == 20
            and provenance['application_input_output_nfc_repair'] is False,
            'TOKENIZER_LIMIT_CHANGED')
    carry = {'kind': 'NATIVE_HISTORICAL_CONTRACT_CARRY_FORWARD',
        'status': 'VERIFIED_REUSED_NOT_RERUN', 'historical_freeze_path': FREEZE,
        'historical_freeze_sha256': FREEZE_SHA,
        'historical_paths': {name: hashes[name] for name in paths},
        'unchanged_source_sha256': sources,
        'current_launch_config_sha256': digest(config_raw),
        'historical_launch_config_sha256': hashes[START + 'launch_config.json'],
        'inference_config_equivalent': True, 'allowed_operational_changes': ALLOWED_CHANGES,
        'actual_changed_fields': changes, 'historical_epoch': {
            'pid': startup['pid'], 'process_start_ticks': startup['process_start_ticks'],
            'guard_started_at_utc': old_guard['started_at_utc']},
        'historical_test_count': 386, 'tests_rerun': 0, 'cpu_probe_calls': 0,
        'public_model_calls': 0, 'resource_model_calls': 0,
        'scope': 'Historical contract/resource/regression only; current process and health are attested separately.',
        'platform_facts_scope': 'Historical same-host platform record; versions are not remeasured by this helper.',
        **provenance}
    return carry, platform, provenance


def attest(probe, config, config_raw, artifacts, carry, platform, provenance):
    require(carry['current_launch_config_sha256'] == digest(config_raw)
            and carry['historical_freeze_path'] == FREEZE
            and carry['historical_freeze_sha256'] == FREEZE_SHA
            and carry['status'] == 'VERIFIED_REUSED_NOT_RERUN', 'CARRY_FORWARD_CHANGED')
    before, before_raw = probe.read_json(config.report_file)
    probe.validate_guard(config, before, artifacts)
    first = probe.epoch(config, before['child_pid'])
    require(config.max_seconds - before['elapsed_seconds'] >= 40, 'INSUFFICIENT_HEALTH_TIME')
    health, elapsed = probe.request_json(config.port, '/health', timeout=10, max_bytes=1024)
    require(health == {'status': 'ok'}, 'HEALTH_FAILED')
    listeners = probe.epoch(config, before['child_pid'], first['process_start_ticks'])
    after, after_raw = probe.read_json(config.report_file)
    probe.validate_guard(config, after, artifacts)
    require((before['started_at_utc'], before['child_pid']) ==
            (after['started_at_utc'], after['child_pid']), 'GUARD_EPOCH_CHANGED')
    carry_raw, listener_raw = probe.encoded(carry), probe.encoded(listeners)
    observation = {'kind': 'NATIVE_MINIMAL_EPOCH_ATTESTATION', 'status': 'PASS',
        'at_utc': datetime.now(timezone.utc).isoformat(), **provenance,
        'launch_config_sha256': digest(config_raw), 'pid': before['child_pid'],
        'process_start_ticks': first['process_start_ticks'], 'guard_started_at_utc': before['started_at_utc'],
        'guard_before_sha256': digest(before_raw), 'guard_after_sha256': digest(after_raw),
        'listener_report_sha256': digest(listener_raw), 'carry_forward_sha256': digest(carry_raw),
        'http_get_calls': 1, 'health_http_status': 200, 'health_status': 'ok',
        'health_elapsed_seconds': elapsed, 'model_inference_calls': 0, 'gpu_query_calls': 0,
        'raw_http_bodies_saved': False, 'full_startup_probe_calls': 0,
        'public_model_calls': 0, 'resource_model_calls': 0, 'cpu_tests_rerun': 0,
        'native_identity_verified': True, 'installed_small_artifacts_rehashed': True,
        'gguf_binding': 'Current guard full hash plus pinned header and current owned size; no second full hash.',
        'current_guard_elapsed_seconds': after['elapsed_seconds'],
        'current_guard_remaining_seconds': config.max_seconds - after['elapsed_seconds'],
        'max_seconds': config.max_seconds,
        'scope': 'Fresh own-process/whole-argv/loopback/resource snapshot and one health GET; historical contract tests are reused.',
        'metadata_scope': 'Current config/listener/attestation hashes; template and platform fields carried from pinned epoch4 contract.'}
    observation_raw = probe.encoded(observation)
    metadata = probe.make_metadata(config, platform, digest(config_raw), digest(observation_raw), digest(listener_raw))
    return {'launch_config.json': config_raw, 'guard_before.json': before_raw, 'guard_after.json': after_raw,
        'listeners.json': listener_raw, 'attestation.json': observation_raw,
        'contract_carry_forward.json': carry_raw, 'runtime_metadata.json': probe.encoded(metadata)}


def validate_saved_bundle(probe, folder):
    """Read-only root/freezer check. No live PID, HTTP, GPU or dataset access.

    The caller separately checks that this recorded own epoch remains current.
    Accepts the fresh var bundle or its exact-byte project archive.
    """
    folder = Path(folder)
    require(folder.is_absolute() and folder.resolve().is_relative_to(ROOT)
            and not folder.is_symlink(), 'BUNDLE_PATH_INVALID')
    names = ('launch_config.json', 'guard_before.json', 'guard_after.json', 'listeners.json',
             'attestation.json', 'contract_carry_forward.json', 'runtime_metadata.json')
    raw = {name: read_local(str((folder / name).relative_to(ROOT))) for name in names}
    values = {name: json.loads(blob) for name, blob in raw.items()}
    require(digest(raw['launch_config.json']) == CONFIG_SHA, 'CONFIG_HASH_MISMATCH')
    config, config_raw = probe.load_config(folder / 'launch_config.json', CONFIG_SHA)
    artifacts = probe.binding(config)
    carry, platform, provenance = historical_contract(probe, config, config_raw, artifacts)
    require(values['contract_carry_forward.json'] == carry, 'CARRY_FORWARD_CHANGED')
    before, after = values['guard_before.json'], values['guard_after.json']
    for report in (before, after):
        probe.validate_guard(config, report, artifacts)
    a, listeners = values['attestation.json'], values['listeners.json']
    require(a['kind'] == 'NATIVE_MINIMAL_EPOCH_ATTESTATION' and a['status'] == 'PASS'
            and a['health_http_status'] == 200 and a['health_status'] == 'ok'
            and a['http_get_calls'] == 1 and a['native_identity_verified'] is True
            and a['raw_http_bodies_saved'] is False
            and all(a[key] == 0 for key in ('model_inference_calls', 'gpu_query_calls',
                'full_startup_probe_calls', 'public_model_calls', 'resource_model_calls', 'cpu_tests_rerun')),
            'ATTESTATION_SCOPE_CHANGED')
    require(listeners['verdict'] == 'PASS' and listeners['snapshot_complete'] is True
            and listeners['all_loopback'] is True and listeners['uid'] == os.getuid()
            and any(item['address'] == '127.0.0.1' and item['port'] == config.port
                    for item in listeners['listeners'])
            and a['pid'] == listeners['pid'] == before['child_pid'] == after['child_pid']
            and a['process_start_ticks'] == listeners['process_start_ticks']
            and a['guard_started_at_utc'] == before['started_at_utc'] == after['started_at_utc'],
            'ATTESTATION_EPOCH_CHANGED')
    for key, value in provenance.items():
        require(a[key] == value, 'ATTESTATION_TOKENIZER_CHANGED')
    for field, name in {'launch_config_sha256': 'launch_config.json',
            'guard_before_sha256': 'guard_before.json', 'guard_after_sha256': 'guard_after.json',
            'listener_report_sha256': 'listeners.json', 'carry_forward_sha256': 'contract_carry_forward.json'}.items():
        require(a[field] == digest(raw[name]), 'ATTESTATION_HASH_CHANGED')
    require(a['max_seconds'] == 3600
            and a['current_guard_elapsed_seconds'] == after['elapsed_seconds']
            and a['current_guard_remaining_seconds'] == 3600 - after['elapsed_seconds'],
            'ATTESTATION_TIME_CHANGED')
    require(values['runtime_metadata.json'] == probe.make_metadata(config, platform, CONFIG_SHA,
            digest(raw['attestation.json']), digest(raw['listeners.json'])), 'CURRENT_METADATA_CHANGED')
    return {'status': 'PASS', 'scope': 'Saved evidence only; no new liveness, HTTP or inference assertion.',
        'pid': a['pid'], 'process_start_ticks': a['process_start_ticks'],
        'guard_started_at_utc': a['guard_started_at_utc'], 'historical_tests_rerun': 0,
        'sha256': {name: digest(blob) for name, blob in raw.items()}}


def main():
    # Reject all repeat/output collisions before any process read or HTTP call.
    base = ROOT / 'var/reports'
    require(not OUT.exists() and not OUT.is_symlink() and OUT.parent == base
            and base.resolve() == base and base.is_dir(), 'OUTPUT_ALREADY_EXISTS_OR_UNSAFE')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    helper_raw = read_local(HELPER, HELPER_SHA)
    config_raw = read_local(CONFIG, CONFIG_SHA)
    spec = importlib.util.spec_from_file_location('minimal_epoch6_probe', ROOT / HELPER)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    config, loaded_raw = probe.load_config(ROOT / CONFIG, CONFIG_SHA)
    require(loaded_raw == config_raw and digest(helper_raw) == HELPER_SHA, 'INPUT_CHANGED')
    artifacts = probe.binding(config)
    carry, platform, provenance = historical_contract(probe, config, config_raw, artifacts)
    bundle = attest(probe, config, config_raw, artifacts, carry, platform, provenance)
    hashes = probe.write_bundle(OUT, bundle)
    print(json.dumps({'status': 'PASS', 'path': str(OUT.relative_to(ROOT)), 'sha256': hashes,
                      'model_inference_calls': 0, 'http_get_calls': 1, 'historical_tests_rerun': 0}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+', str(error)) else 'ATTESTATION_ERROR'
        print(json.dumps({'status': 'FAIL', 'code': code, 'error_type': type(error).__name__}))
        raise SystemExit(1)
