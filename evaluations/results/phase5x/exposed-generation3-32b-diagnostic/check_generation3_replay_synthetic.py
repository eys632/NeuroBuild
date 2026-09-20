"""Preparation-only checks: no actual run results or evaluation datasets read."""
import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

root = Path(__file__).resolve().parents[2]
path = root / 'var/review-tools/replay_generation3_32b_exposed.py'
ast.parse(path.read_text())
spec = importlib.util.spec_from_file_location('generation3_replay_preparation', path)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
core, generation, facts, snapshot = r.load_snapshot()
validators = {key: core.Draft202012Validator(core.strict_json((r.SNAPSHOT / r.PATHS[key]).read_text()))
              for key in ('schema', 'quote_projection_schema', 'canonical_schema')}
source = '문 옆 안내 데스크를 X축 양의 방향으로 2cm 이동해.'
case = {'id': 'SYNTHETIC_REPLAY', 'category': 'korean_requirement', 'input': source,
        'context': {'axis_convention': 'project_xy'},
        'gold': {'decision': 'clarify', 'target_text': '안내 데스크'}}
base = {'schema_version': '3.0', 'facts': {
    'intent': 'CURRENT_MOVE', 'condition': 'NONE', 'target_class': 'FURNITURE',
    'target_count': 'ONE', 'motion': 'ONE_RELATIVE_XY_VECTOR', 'axis_completeness': 'EXPLICIT',
    'authority': 'NONE', 'condition_quote': None, 'authority_quote': None,
    'selection_scope_quote': None, 'selection_exclusion_quote': None},
    'decision': 'READY', 'target_selection_quote': '안내 데스크',
    'current_instruction_quote': source, 'dx_evidence': 'X축 양의 방향으로 2cm',
    'dy_evidence': None, 'reason': None}
fixtures = [('schema_valid_ready_on_nonready_gold', deepcopy(base), None)]
bad = deepcopy(base)
bad['facts']['selection_scope_quote'] = '문 옆'
fixtures.append(('facts_grounding_rejected_ready', bad, None))
bad = deepcopy(base)
bad['dx_evidence'] = '2cm'
fixtures.append(('quote_axis_rejected_ready', bad, None))
bad = deepcopy(base)
bad['extra'] = 'discard'
fixtures.append(('schema_rejected_raw_ready_unretained', bad, None))
fixtures.extend([('malformed_unknown_unretained', '{', None),
                 ('array_unknown_unretained', [], None),
                 ('transport_unknown_unretained', None, 'LOCAL_MODEL_TIMEOUT')])
nonready = deepcopy(base)
nonready.update(decision='CLARIFICATION', current_instruction_quote=None, dx_evidence=None,
                reason='추가 확인이 필요합니다.')
fixtures.append(('valid_nonready', nonready, None))
results, rows = [], []
for label, output, error in fixtures:
    content = json.dumps(output, ensure_ascii=False) if not isinstance(output, str) else output
    class Fake:
        model = 'synthetic'
        generation_contract = generation.GenerationContract.FACTS
        def complete(self, *args, **kwargs):
            if error:
                raise core.DomainError(error, 'sentinel_must_not_leak')
            return SimpleNamespace(content=content, model=self.model,
                                   usage={'completion_tokens': 7}, latency_seconds=.1)
    ticks = iter([0.0, .25])
    row = core.evaluate_trial(Fake(), case, validators['schema'], 1,
                             run_id='synthetic-replay-self-check', clock=lambda: next(ticks))
    replay, retained = r.replay_row(row, case, 'synthetic-replay-self-check', 'synthetic',
                                    validators, core, generation, facts)
    assert replay == row
    rows.append(row)
    results.append({'case': label, 'retained': retained, 'raw_decision': row['raw_model_decision'],
                    'error_code': row['error_code']})
mutations = []
for label, row, key, value in [
    ('erase_raw_ready', rows[1], 'raw_model_decision', None),
    ('erase_observed_ready', rows[3], 'model_ready_observed', False),
    ('invent_unknown_ready', rows[4], 'raw_model_decision', 'READY'),
    ('false_facts_success', rows[1], 'facts_projection_accepted', True),
    ('change_projection', rows[0], 'projected_quote_output', None),
    ('inflate_semantic', rows[0], 'semantic_rubric_correct', True),
]:
    tampered = deepcopy(row)
    tampered[key] = value
    try:
        r.replay_row(tampered, case, 'synthetic-replay-self-check', 'synthetic',
                     validators, core, generation, facts)
    except AssertionError:
        mutations.append(label)
    else:
        raise AssertionError('tamper_not_rejected:' + label)
metrics = core.summarize(rows)
assert metrics['critical_fp_model_ready']['numerator'] == 4
assert metrics['raw_decision_observed']['numerator'] == 5
assert metrics['unsafe_accepted_ready_total']['numerator'] == 1
proof = {'status': 'PASS_PREPARATION_SYNTHETIC_ONLY', 'helper_sha256': r.digest(path),
         'selfcheck_sha256': r.digest(Path(__file__)),
         'snapshot_commit': r.COMMIT, 'snapshot_sha256': r.SNAPSHOT_SHA256,
         'fixture_count': len(fixtures), 'fixtures': results, 'tampered_rows_rejected': mutations,
         'counts': {key: metrics[key] for key in ('critical_fp_model_ready', 'raw_decision_observed',
                                                 'unsafe_accepted_ready_total')},
         'actual_run_results_read': False, 'network_calls': 0, 'model_calls': 0, 'gpu_calls': 0}
dest = root / 'var/research' / ('generation3-replay-preparation-selfcheck-' + uuid4().hex + '.json')
with dest.open('x') as stream:
    json.dump(proof, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'status': proof['status'], 'fixtures': len(fixtures),
                  'tampering_rejected': len(mutations), 'helper_sha256': proof['helper_sha256'],
                  'proof': str(dest.relative_to(root)), 'proof_sha256': r.digest(dest)}))
