"""Qwen3.6 BLOCKED controller definition; root owns any later explicit activation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
from types import ModuleType

ROOT = Path('/home/a202192020/NeuroBuild_v2')
HELPER = ROOT / 'var/research/qwen36_runtime_probe.py'
HELPER_SHA = '03e3de45d58688b4cc78ac691e306e7086861014acf5de3e8126b73d324cba09'
CONFIG = ROOT / 'var/research/qwen36-native-launch-epoch1.json'
CONFIG_SHA = '4ba0534766bad9542d96f2dc08cf1a13f07d99dafb46c44a67eb2102e6d715ac'
CPU_PROOF = ROOT / 'var/research/native-qwen36-contract/final-cpu-proof.json'


def main():
    raise ValueError("QWEN36_RUNTIME_ACTIVATION_PENDING")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('startup', 'public', 'resource'))
    parser.add_argument('--cpu-proof-sha256', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.cpu_proof_sha256):
        raise ValueError('CPU_PROOF_HASH_INVALID')
    folder = ROOT / 'var/reports' / {'startup': 'qwen36-native-startup-epoch1',
        'public': 'qwen36-native-public-smoke-epoch1', 'resource': 'qwen36-native-resource-epoch1'}[args.action]
    if folder.exists() or folder.is_symlink():
        raise ValueError('PROBE_ALREADY_RECORDED')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    raw = HELPER.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HELPER_SHA:
        raise ValueError('HELPER_CHANGED')
    p = ModuleType('qwen36_epoch1_probe')
    p.__file__ = str(HELPER)
    exec(compile(raw, str(HELPER), 'exec'), p.__dict__)
    p.require_ready()
    kw = dict(cpu_proof_path=CPU_PROOF, cpu_proof_sha=args.cpu_proof_sha256)
    if args.action == 'startup':
        platform = {'compiler': 'GCC/G++ 9.5.0', 'cmake': '3.23.5', 'cuda': '11.8.89',
                    'driver': '535.183.01', 'gpu': 'NVIDIA A100-PCIE-40GB',
                    'gpu_uuid': 'GPU-e56265ed-69de-738b-d683-52fbf895e538'}
        bundle = p.capture_startup(CONFIG, CONFIG_SHA, platform, **kw)
    elif args.action == 'public':
        result = p.public_smoke(CONFIG, CONFIG_SHA, timeout=120, **kw)
        bundle = {'report.json': p.encoded(result)}
    else:
        result = p.run_resource_smoke(CONFIG, CONFIG_SHA, timeout=900, **kw)
        bundle = {'report.json': p.encoded(result)}
    hashes = p.write_bundle(folder, bundle)
    status = json.loads(bundle.get('report.json', bundle.get('startup.json')))['status']
    print(json.dumps({'action': args.action, 'report_dir': str(folder.relative_to(ROOT)),
                      'sha256': hashes, 'status': status}))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        code = str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+', str(error)) else 'PROBE_ERROR'
        print(json.dumps({'status': 'FAIL', 'code': code, 'error_type': type(error).__name__}))
        raise SystemExit(1)
