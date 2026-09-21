"""Four new saved-evidence consumer controls only; no runtime/probe invocation."""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path('/home/a202192020/NeuroBuild_v2')
HELPER = ROOT / 'var/research/gemma4_12b_runtime_probe.py'
HELPER_SHA = '11f764b4c7d824220e6b308773fa285127f37f5b31fc4d18ae1c2aeef9d6d255'
CONTROLLER = ROOT / 'var/research/run_native_gemma4_12b_epoch1_probe.py'
CONTROLLER_SHA = 'dc20beda8d0b7dd301b79750c131aeb89395f13091eb126491bd699cd7323283'
CONFIG = ROOT / 'var/research/gemma4-12b-native-launch-epoch1.json'
CONFIG_SHA = '03bef49517deff1a8410625569fa7566433db31b20b381d989e275814a71b812'
REPORT = ROOT / 'var/research/gemma12-runtime-carry-consumer-controls.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    raw = HELPER.read_bytes()
    assert sha(raw) == HELPER_SHA
    assert sha(CONTROLLER.read_bytes()) == CONTROLLER_SHA
    config_raw = CONFIG.read_bytes()
    assert sha(config_raw) == CONFIG_SHA
    cfg = SimpleNamespace(**json.loads(config_raw))
    module = ModuleType('gemma12_blocked_consumer_control')
    module.__file__ = str(HELPER)
    exec(compile(raw, str(HELPER), 'exec'), module.__dict__)
    controls = []

    def rejected(name, call, code):
        try:
            call()
        except ValueError as error:
            assert str(error) == code, (name, str(error))
        else:
            raise AssertionError(name)
        controls.append({'name': name, 'status': 'REJECTED', 'code': code})

    with ExitStack() as stack:
        stack.enter_context(patch.object(module, 'require_ready', return_value=None))
        sentinels = [stack.enter_context(patch.object(module, name, side_effect=AssertionError('LIVE_PATH_FORBIDDEN')))
                     for name in ('binding', 'epoch', 'request_json', 'validate_guard')]
        stack.enter_context(patch.object(module.base, 'ProcReader', side_effect=AssertionError('PROCESS_READ_FORBIDDEN')))
        provenance, token = module.cpu_provenance(cfg, ROOT / module.CPU_CARRYFORWARD_PATH,
                                                module.CPU_CARRYFORWARD_SHA)
        assert provenance['cpu_proof_status'] == 'CARRIED_FORWARD_BY_EXACT_INPUT_EQUIVALENCE'
        assert provenance['model_id'] == 'google/gemma-4-12B-it-qat-q4_0-gguf'
        assert provenance['historical_measurements']['measured_model_id'] == 'google/gemma-4-31B-it-qat-q4_0-gguf'
        assert provenance['new_cpu_executions'] == {'native_public': 0, 'vocab': 0, 'context': 0,
                                                   'model_inference': 0, 'http': 0, 'gpu': 0}
        assert provenance['sampling_behavior']['full_sampling_equivalent'] is False
        assert token == 236743
        controls.append({'name': 'actual_saved_receipt', 'status': 'ACCEPTED_AS_CARRY_FORWARD_ONLY'})
        rejected('wrong_caller_sha', lambda: module.cpu_provenance(cfg, ROOT / module.CPU_CARRYFORWARD_PATH,
                                                                  '0' * 64), 'GEMMA12_CARRY_HASH_NOT_PINNED')
        rejected('old31_proof_path', lambda: module.cpu_provenance(
            cfg, ROOT / module.CARRY_REFS['historical_aggregate']['path'], module.CPU_CARRYFORWARD_SHA),
            'GEMMA12_CARRY_PATH_MISMATCH')
        checked = module.base.checked_file
        source = ROOT / 'src/neurobuild/infrastructure/local_model.py'

        def changed_file(path, root):
            if Path(path) == source:
                return SimpleNamespace(stat=lambda: SimpleNamespace(st_size=14),
                                       read_bytes=lambda: b'SYNTHETIC_EDIT')
            return checked(path, root)

        with patch.object(module.base, 'checked_file', side_effect=changed_file):
            rejected('current_source_mismatch', lambda: module.cpu_provenance(
                cfg, ROOT / module.CPU_CARRYFORWARD_PATH, module.CPU_CARRYFORWARD_SHA),
                'GEMMA12_REFERENCE_HASH_MISMATCH')
        for sentinel in sentinels:
            sentinel.assert_not_called()
    result = {'kind': 'GEMMA12_NEW_CARRY_CONSUMER_CONTROLS', 'status': 'PASS',
              'at_utc': datetime.now(timezone.utc).isoformat(), 'control_count': len(controls),
              'controls': controls, 'blocked_helper_sha256': HELPER_SHA,
              'blocked_controller_sha256': CONTROLLER_SHA, 'config_sha256': CONFIG_SHA,
              'test_source_sha256': sha(Path(__file__).read_bytes()),
              'carry_proof_sha256': module.CPU_CARRYFORWARD_SHA,
              'provenance': provenance, 'resource_probe_token_id': token,
              'require_ready_patched_locally_for_saved_consumer_only': True,
              'controller_main_calls': 0, 'binding_process_http_calls': 0,
              'native_gpu_model_calls': 0, 'corpus_parsing_or_replay_calls': 0,
              'old_tests_or_public_context_executions': 0}
    payload = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()
    with REPORT.open('xb') as stream:
        stream.write(payload)
    print(json.dumps({'status': 'PASS', 'controls': len(controls),
                      'report': str(REPORT.relative_to(ROOT)), 'sha256': sha(payload)}))


if __name__ == '__main__':
    main()
