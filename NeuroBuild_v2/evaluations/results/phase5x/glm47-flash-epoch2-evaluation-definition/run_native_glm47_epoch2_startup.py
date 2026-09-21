"""Root-owned epoch2 startup GETs only; no public/resource POST implementation.

--check-cpu-only reuses saved small CPU receipts without process or HTTP access.
Neither mode launches a server. Existing epoch1 definitions are unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
from types import ModuleType

ROOT = Path('/home/a202192020/NeuroBuild_v2')
HELPER = ROOT / 'var/research/glm47_flash_runtime_probe_v2.py'
HELPER_SHA = '4399c90d32e0e472455bae5e907c8a479fdac550fed46978d8001c6d894d69ea'
CONFIG = ROOT / 'var/research/glm47-flash-native-launch-epoch2.json'
CONFIG_SHA = 'd0a5ae9663d9caf4420651a018ce687325b0e8fc7fb154963e948b4251e56994'
CPU_PROOF = ROOT / 'var/research/native-glm47-contract/final-cpu-proof.json'
CPU_SHA = '54ab0062c5d22112ed3349e0021391a4dd17f6d5f8698ac8a02cc096b08a1847'
OUTPUT = ROOT / 'var/reports/glm47-flash-native-startup-epoch2'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-cpu-only', action='store_true')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    raw = HELPER.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HELPER_SHA:
        raise ValueError('HELPER_CHANGED')
    p = ModuleType('glm47_flash_epoch2_startup')
    p.__file__ = str(HELPER)
    exec(compile(raw, str(HELPER), 'exec'), p.__dict__)
    p.require_ready()
    if args.check_cpu_only:
        config, _ = p.load_config(CONFIG, CONFIG_SHA)
        p.cpu_provenance(config, CPU_PROOF, CPU_SHA)
        print(json.dumps({'status': 'SAVED_CPU_BINDING_PASS', 'config_sha256': CONFIG_SHA,
                          'cpu_proof_sha256': CPU_SHA, 'http_calls': 0, 'native_calls': 0,
                          'scope': 'Saved small receipts only; no new CPU tests or runtime attestation'}))
        return 0
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise ValueError('PROBE_ALREADY_RECORDED')
    platform = {'compiler': 'GCC/G++ 9.5.0', 'cmake': '3.23.5', 'cuda': '11.8.89',
                'driver': '535.183.01', 'gpu': 'NVIDIA A100-PCIE-40GB',
                'gpu_uuid': 'GPU-e56265ed-69de-738b-d683-52fbf895e538'}
    bundle = p.capture_startup(CONFIG, CONFIG_SHA, platform,
                              cpu_proof_path=CPU_PROOF, cpu_proof_sha=CPU_SHA)
    hashes = p.write_bundle(OUTPUT, bundle)
    status = json.loads(bundle['startup.json'])['status']
    print(json.dumps({'action': 'startup', 'report_dir': str(OUTPUT.relative_to(ROOT)),
                      'sha256': hashes, 'status': status}))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        code = str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+', str(error)) else 'PROBE_ERROR'
        print(json.dumps({'status': 'FAIL', 'code': code, 'error_type': type(error).__name__}))
        raise SystemExit(1)
