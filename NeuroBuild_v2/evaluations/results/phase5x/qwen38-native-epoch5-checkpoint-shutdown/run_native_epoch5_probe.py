"""Explicit single-step root probe; no launch, fallback, retry or raw-body logs."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import resource

ROOT = Path('/home/a202192020/NeuroBuild_v2')
HELPER = ROOT / 'var/research/native_runtime_probe.py'
HELPER_SHA = 'ac100df7949b2b14a517c4568fa66369bd98c599b39507ef19f873490a0f9f63'
CONFIG = ROOT / 'var/research/qwen38-native-launch-epoch5-formal.json'
CONFIG_SHA = '076eccea41937e24555ce8132cf492617d3b8cefccac2514b374802a8040a4d7'
CONTEXT = ROOT / 'var/reports/native-contract-raw-cpu-context.json'
CONTEXT_SHA = '5d37568d7b51d1b689b168f0e9fa6fb46ac487b70f451c82611c146f978e59be'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('startup', 'public', 'resource'))
    args = parser.parse_args()
    folder = ROOT / 'var/reports' / {'startup': 'qwen38-native-startup-epoch5',
        'public': 'qwen38-native-public-smoke-epoch5', 'resource': 'qwen38-native-resource-epoch5'}[args.action]
    if folder.exists() or folder.is_symlink():
        raise ValueError('PROBE_ALREADY_RECORDED')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if hashlib.sha256(HELPER.read_bytes()).hexdigest() != HELPER_SHA:
        raise ValueError('HELPER_CHANGED')
    spec = importlib.util.spec_from_file_location('native_epoch5_probe', HELPER)
    p = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(p)
    kw = dict(runtime_variant=p.RUNTIME_VARIANT, context_proof_path=CONTEXT, context_proof_sha=CONTEXT_SHA)
    config, _ = p.load_config(CONFIG, CONFIG_SHA)
    if args.action == 'startup':
        platform = {'compiler': 'GCC/G++ 9.5.0', 'cmake': '3.23.5', 'cuda': '11.8.89',
                    'driver': '535.183.01', 'gpu': 'NVIDIA A100-PCIE-40GB',
                    'gpu_uuid': 'GPU-e56265ed-69de-738b-d683-52fbf895e538'}
        bundle = p.capture_startup(CONFIG, CONFIG_SHA, platform, **kw)
        folder = ROOT / 'var/reports/qwen38-native-startup-epoch5'
    elif args.action == 'public':
        artifacts = p.binding(config)
        before, before_raw = p.read_json(config.report_file)
        p.validate_guard(config, before, artifacts)
        first = p.epoch(config, before['child_pid'])
        result = p.public_smoke(config, timeout=120, **kw)
        p.epoch(config, before['child_pid'], first['process_start_ticks'])
        after, after_raw = p.read_json(config.report_file)
        p.validate_guard(config, after, artifacts)
        p.require((before['started_at_utc'], before['child_pid']) ==
                  (after['started_at_utc'], after['child_pid']), 'GUARD_EPOCH_CHANGED')
        result.update(launch_config_sha256=CONFIG_SHA, pid=before['child_pid'],
            process_start_ticks=first['process_start_ticks'], guard_started_at_utc=before['started_at_utc'],
            guard_before_sha256=p.digest(before_raw), guard_after_sha256=p.digest(after_raw))
        bundle = {'report.json': p.encoded(result), 'guard_before.json': before_raw, 'guard_after.json': after_raw}
        folder = ROOT / 'var/reports/qwen38-native-public-smoke-epoch5'
    else:
        result = p.run_resource_smoke(CONFIG, CONFIG_SHA, timeout=900, **kw)
        bundle = {'report.json': p.encoded(result)}
        folder = ROOT / 'var/reports/qwen38-native-resource-epoch5'
    hashes = p.write_bundle(folder, bundle)
    status = json.loads(bundle.get('report.json', bundle.get('startup.json')))['status']
    print(json.dumps({'action': args.action, 'report_dir': str(folder.relative_to(ROOT)), 'sha256': hashes,
                      'status': status}))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        code = str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+', str(error)) else 'PROBE_ERROR'
        print(json.dumps({'status': 'FAIL', 'code': code, 'error_type': type(error).__name__}))
        raise SystemExit(1)
