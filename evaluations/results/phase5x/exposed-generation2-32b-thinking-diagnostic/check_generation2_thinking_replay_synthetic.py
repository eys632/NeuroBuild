"""Synthetic preparation only; no current model results or reasoning are read."""
import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

root = Path(__file__).resolve().parents[2]
path = root / 'var/review-tools/replay_generation2_32b_thinking_exposed.py'
ast.parse(path.read_text())
spec = importlib.util.spec_from_file_location('thinking_replay_preparation', path)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
core, generation, snapshot = r.load_snapshot()
validators = {key: core.Draft202012Validator(core.strict_json((r.SNAPSHOT / r.PATHS[key]).read_text()))
              for key in ('schema', 'canonical_schema')}
source = '문 옆 안내 데스크를 X축 양의 방향으로 2cm 이동해.'
case = {'id': 'SYNTHETIC_THINKING_REPLAY', 'category': 'korean_requirement', 'input': source,
        'context': {'axis_convention': 'project_xy'},
        'gold': {'decision': 'clarify', 'target_text': '안내 데스크'}}
base = {'schema_version': '2.0', 'decision': 'READY', 'target_selection_quote': '안내 데스크',
        'current_instruction_quote': source, 'dx_evidence': 'X축 양의 방향으로 2cm',
        'dy_evidence': None, 'reason': None}
fixtures = [('retained_ready_on_nonready_gold', deepcopy(base), None)]
bad = deepcopy(base)
bad['dx_evidence'] = '2cm'
fixtures.append(('retained_unsigned_axis_ready', bad, None))
bad = deepcopy(base)
bad['target_selection_quote'] = '원문에 없는 대상'
fixtures.append(('retained_ungrounded_target_ready', bad, None))
bad = deepcopy(base)
bad['extra'] = 'discard'
fixtures.append(('schema_rejected_raw_ready_unretained', bad, None))
fixtures.extend([('malformed_unknown_unretained', '{', None),
                 ('array_unknown_unretained', [], None),
                 ('timeout_unknown_unretained', None, 'LOCAL_MODEL_TIMEOUT'),
                 ('truncated_unknown_unretained', None, 'LOCAL_MODEL_TRUNCATED'),
                 ('no_final_unknown_unretained', None, 'LOCAL_MODEL_RESPONSE_INVALID')])
nonready = deepcopy(base)
nonready.update(decision='CLARIFICATION', current_instruction_quote=None, dx_evidence=None,
                reason='추가 확인이 필요합니다.')
fixtures.append(('retained_nonready', nonready, None))
results, rows = [], []
for label, output, error in fixtures:
    content = json.dumps(output, ensure_ascii=False) if not isinstance(output, str) else output
    class Fake:
        model = 'synthetic'
        generation_contract = generation.GenerationContract.QUOTES
        def complete(self, *args, **kwargs):
            if error:
                raise core.DomainError(error, 'safe_error_fixture')
            return SimpleNamespace(content=content, model=self.model,
                                   usage={'completion_tokens': 7}, latency_seconds=.1)
    ticks = iter([0.0, .25])
    row = core.evaluate_trial(Fake(), case, validators['schema'], 1,
                             run_id='thinking-synthetic-self-check', clock=lambda: next(ticks))
    replay, retained = r.replay_row(row, case, 'thinking-synthetic-self-check', 'synthetic',
                                    validators, core, generation)
    assert replay == row
    rows.append(row)
    results.append({'fixture': label, 'retained': retained, 'raw_decision': row['raw_model_decision'],
                    'error_code': row['error_code']})
mutations = []
for label, row, key, value in [
    ('erase_raw_ready', rows[1], 'raw_model_decision', None),
    ('erase_observed_ready', rows[3], 'model_ready_observed', False),
    ('invent_truncated_ready', rows[7], 'raw_model_decision', 'READY'),
    ('unknown_as_safe_false', rows[8], 'model_ready_observed', False),
    ('false_adapter_success', rows[1], 'adapter_accepted', True),
    ('erase_canonical_projection', rows[0], 'semantic_output', None),
    ('inflate_semantic', rows[0], 'semantic_rubric_correct', True),
    ('wrong_contract', rows[0], 'generation_contract', '3.0'),
]:
    tampered = deepcopy(row)
    tampered[key] = value
    try:
        r.replay_row(tampered, case, 'thinking-synthetic-self-check', 'synthetic',
                     validators, core, generation)
    except AssertionError:
        mutations.append(label)
    else:
        raise AssertionError('tamper_not_rejected:' + label)
metrics = core.summarize(rows)
assert metrics['critical_fp_model_ready']['numerator'] == 4
assert metrics['critical_fp_model_ready']['denominator'] == 10
assert metrics['raw_decision_observed']['numerator'] == 5
assert metrics['unsafe_accepted_ready_total']['numerator'] == 1
assert sum(row['raw_model_decision'] is None for row in rows) == 5
assert sum(item['retained'] for item in results) == 4
proof = {'status': 'PASS_PREPARATION_SYNTHETIC_ONLY', 'helper_sha256': r.digest(path),
         'selfcheck_sha256': r.digest(Path(__file__)),
         'snapshot_commit': r.COMMIT, 'snapshot_sha256': r.SNAPSHOT_SHA256,
         'fixture_count': len(fixtures), 'fixtures': results, 'tampered_rows_rejected': mutations,
         'counts': {key: metrics[key] for key in ('critical_fp_model_ready', 'raw_decision_observed',
                                                 'unsafe_accepted_ready_total')},
         'actual_run_results_read': False, 'actual_reasoning_body_reads': 0,
         'network_calls': 0, 'model_calls': 0, 'gpu_calls': 0}
dest = root / 'var/research' / ('generation2-thinking-replay-selfcheck-' + uuid4().hex + '.json')
with dest.open('x') as stream:
    json.dump(proof, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'status': proof['status'], 'fixtures': len(fixtures),
                  'tampering_rejected': len(mutations), 'helper_sha256': proof['helper_sha256'],
                  'proof': str(dest.relative_to(root)), 'proof_sha256': r.digest(dest)}))
