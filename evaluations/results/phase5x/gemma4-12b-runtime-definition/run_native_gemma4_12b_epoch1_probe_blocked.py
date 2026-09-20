"""BLOCKED Gemma12 controller definition; root finalizes exact pins before use."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
from types import ModuleType

ROOT = Path('/home/a202192020/NeuroBuild_v2')
HELPER = ROOT / 'var/research/gemma4_12b_runtime_probe.py'
HELPER_SHA = '11f764b4c7d824220e6b308773fa285127f37f5b31fc4d18ae1c2aeef9d6d255'
CONFIG = ROOT / 'var/research/gemma4-12b-native-launch-epoch1.json'
CONFIG_SHA = '03bef49517deff1a8410625569fa7566433db31b20b381d989e275814a71b812'
CPU_PROOF = ROOT / 'var/research/native-gemma4-12b-contract/cpu-carry-forward.json'
CPU_PROOF_SHA = 'cb2370d7a012b40fe62dae039551d9f8d37f4961aaaccc7a9845dd8bfdee0a2f'


def require_ready():
    raise ValueError('GEMMA12_CONTROLLER_FINAL_REVIEW_PENDING')


def main():
    require_ready()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('startup', 'public', 'resource'))
    parser.add_argument('--cpu-proof-sha256', required=True)
    args = parser.parse_args()
    if args.cpu_proof_sha256 != CPU_PROOF_SHA:
        raise ValueError('CPU_PROOF_HASH_INVALID')
    folder = ROOT / 'var/reports' / {'startup': 'gemma4-12b-native-startup-epoch1',
        'public': 'gemma4-12b-native-public-smoke-epoch1', 'resource': 'gemma4-12b-native-resource-epoch1'}[args.action]
    if folder.exists() or folder.is_symlink():
        raise ValueError('PROBE_ALREADY_RECORDED')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    raw = HELPER.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HELPER_SHA:
        raise ValueError('HELPER_CHANGED')
    p = ModuleType('gemma4_12b_epoch1_probe')
    p.__file__ = str(HELPER)
    exec(compile(raw, str(HELPER), 'exec'), p.__dict__)
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
