"""CPU-only actual transport capture; no network/model calls or gold access."""
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sys
from datetime import datetime, timezone
from email.message import Message
from unittest.mock import patch

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'src'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

paths = [
    'src/neurobuild/infrastructure/staged_requirement.py',
    'src/neurobuild/infrastructure/local_model.py',
    'src/neurobuild/application/requirement_generation.py',
    'src/neurobuild/application/requirements.py',
    'prompts/requirement_classification_v1.txt',
    'prompts/requirement_extraction_v1.txt',
    'schemas/requirement_classification.schema.json',
    'schemas/requirement_generation_v2_decision_branches.schema.json',
]
source_before = {name: digest(ROOT / name) for name in paths}
from neurobuild.infrastructure.staged_requirement import LocalStagedRequirementClient
import transformers
from transformers import AutoTokenizer

proofdir = ROOT / 'evaluations/results/phase5x/holdout-v2-preflight'
priorpath = proofdir / 'independent_cpu_context_proof.json'
prior = json.loads(priorpath.read_text())
data = ROOT / 'evaluations/requirement_hardening_v2_holdout.jsonl'
assert digest(data) == prior['dataset_sha256']
rows = json.loads('[' + ','.join(data.read_text().splitlines()) + ']')
freeze_path = ROOT / 'evaluations/hardening_v2_dataset_freeze.json'
freeze_bytes = freeze_path.read_bytes()
freeze = json.loads(freeze_bytes)
for name, expected in freeze['sha256'].items():
    assert digest(ROOT / name) == expected
assert source_before['prompts/requirement_classification_v1.txt'] == prior['prompt_sha256']['classification_v1']
assert source_before['prompts/requirement_extraction_v1.txt'] == prior['prompt_sha256']['extraction_v1']
modelproof = next(m for m in prior['models'] if m['model_id'] == 'Qwen/Qwen3-14B-AWQ')
modelpath = ROOT / modelproof['tokenizer_local_path']
for name, expected in modelproof['metadata_sha256'].items():
    assert digest(modelpath / name) == expected
with patch.object(socket, 'socket', side_effect=AssertionError('Network forbidden in CPU proof')):
    tok = AutoTokenizer.from_pretrained(modelpath, local_files_only=True, trust_remote_code=False)
assert hashlib.sha256(tok.chat_template.encode()).hexdigest() == modelproof['selected_chat_template_sha256']

class Response(io.BytesIO):
    status = 200
    def __init__(self, output, model):
        content = {'model': model, 'choices': [{'index': 0, 'finish_reason': 'stop',
                   'message': {'role': 'assistant', 'content': json.dumps(output, ensure_ascii=False)}}]}
        data = json.dumps(content, ensure_ascii=False).encode()
        super().__init__(data)
        self.headers = Message()
        self.headers['Content-Type'] = 'application/json'
        self.headers['Content-Length'] = str(len(data))

class Capture:
    def __init__(self, output):
        self.output = output
        self.requests = []
    def open(self, request, timeout):
        self.requests.append((request.data, timeout))
        return Response(self.output, 'transport-binding-fixture')

classifier_lengths = []
extractor_lengths = {d: [] for d in ('READY', 'CLARIFICATION', 'UNSUPPORTED')}
body_digest = hashlib.sha256()
unique_classifier_request_hashes = set()
request_count = 0
with patch.object(socket, 'socket', side_effect=AssertionError('Network forbidden in CPU proof')):
    client = LocalStagedRequirementClient('http://127.0.0.1:1', 'transport-binding-fixture')
    for row in rows:
        for decision in ('READY', 'CLARIFICATION', 'UNSUPPORTED'):
            # Fixed shape-only fixtures, independent of input/gold. Not scored or persisted.
            classification = {'schema_version': 'classification-1.0', 'decision': decision}
            extraction = {'schema_version': '2.0', 'decision': decision,
                          'target_selection_quote': 'fixture',
                          'current_instruction_quote': 'fixture' if decision == 'READY' else None,
                          'dx_evidence': 'fixture' if decision == 'READY' else None,
                          'dy_evidence': None, 'reason': None if decision == 'READY' else 'fixture'}
            classifier = Capture(classification)
            extractor = Capture(extraction)
            client._classifier._opener = classifier
            client._extractor._opener = extractor
            trace = client.complete_staged(row['input'], axis_convention=row['context'].get('axis_convention'))
            assert trace.error_code is None
            assert len(classifier.requests) == len(extractor.requests) == 1
            for stage, capture, prompt_key, cap in (
                ('classification', classifier, 'classification_v1', 128),
                ('extraction', extractor, 'extraction_v1', 768),
            ):
                request_bytes, timeout = capture.requests[0]
                request_count += 1
                body_digest.update(len(request_bytes).to_bytes(8, 'big') + request_bytes)
                payload = json.loads(request_bytes)
                original = {'source_text': row['input'], 'axis_convention': row['context'].get('axis_convention')}
                if stage == 'extraction':
                    original['classified_decision'] = decision
                expected_messages = [
                    {'role': 'system', 'content': (ROOT / ('prompts/requirement_' + prompt_key + '.txt')).read_text()},
                    {'role': 'user', 'content': json.dumps(original, ensure_ascii=False)},
                ]
                assert payload['messages'] == expected_messages
                assert payload['messages'][1]['content'].encode() == json.dumps(original, ensure_ascii=False).encode()
                schema = client.classification_schema if stage == 'classification' else client.schema_for_decision(decision)
                if stage == 'extraction':
                    assert all(b['properties']['decision']['enum'] == [decision] for b in schema['anyOf'])
                    assert len(schema['anyOf']) == (3 if decision == 'READY' else 1)
                expected_payload = {'model': 'transport-binding-fixture', 'messages': expected_messages,
                                    'temperature': 0, 'seed': 42, 'max_tokens': cap, 'stream': False,
                                    'chat_template_kwargs': {'enable_thinking': False},
                                    'guided_json': schema, 'guided_decoding_backend': 'xgrammar:no-fallback'}
                assert request_bytes == json.dumps(expected_payload, ensure_ascii=False).encode()
                assert timeout == 60.0
                length = len(tok.apply_chat_template(payload['messages'], tokenize=True,
                                                    add_generation_prompt=True,
                                                    **payload['chat_template_kwargs']))
                if stage == 'classification':
                    classifier_lengths.append(length)
                    unique_classifier_request_hashes.add(hashlib.sha256(request_bytes).hexdigest())
                else:
                    extractor_lengths[decision].append(length)
assert len(rows) == 80 and request_count == 480 and len(unique_classifier_request_hashes) == 80
max_classifier = max(classifier_lengths)
max_extractor = max(v for values in extractor_lengths.values() for v in values)
assert max_classifier == modelproof['measurements']['classification_v1']['maximum_input_tokens']
assert max_extractor == modelproof['measurements']['extraction_v1']['maximum_input_tokens']
assert max_classifier + 128 <= 4096 and max_extractor + 768 <= 4096
assert 'torch' not in sys.modules
source_after = {name: digest(ROOT / name) for name in paths}
assert source_before == source_after, 'Source changed during capture; rerun after source readiness'
assert freeze_path.read_bytes() == freeze_bytes
for name, expected in freeze['sha256'].items():
    assert digest(ROOT / name) == expected
proof = {
    'kind': 'UNUSED_V2_ACTUAL_STAGED_TRANSPORT_CPU_BINDING',
    'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
    'dataset_sha256': digest(data), 'dataset_cases': 80,
    'source_sha256_before_and_after': source_after, 'source_unchanged_during_capture': True,
    'previous_context_proof_sha256': digest(priorpath), 'dataset_freeze_sha256': digest(freeze_path),
    'source_bound_review_script_sha256': digest(Path(__file__)),
    'gold_status': 'AUTO-GENERATED / NOT HUMAN VERIFIED',
    'payload': {'method': 'Actual LocalStagedRequirementClient.complete_staged through in-memory fake openers',
                'cycles': 240, 'captured_fake_http_requests': 480,
                'classifier_requests': 240, 'unique_classifier_request_bytes': 80,
                'extractor_requests': 240, 'decision_variants_per_source': 3,
                'all_request_bytes_match_manual_payload': True,
                'source_text_whole_unchanged': True, 'axis_convention_unchanged': True,
                'classifier_input_has_no_extraction_decision': True,
                'extractor_decision_bound_schema_matches_user_field': True,
                'fixture_model_name': 'transport-binding-fixture',
                'captured_request_sequence_sha256': body_digest.hexdigest(),
                'request_or_reply_bodies_persisted': False,
                'fixture_output_note': 'Fixed shape-only fake replies select each branch independently of gold; no semantic model output or quality scoring.'},
    'model_tokenizer': modelproof['model_id'], 'model_revision': modelproof['revision'],
    'tokenizer_metadata_sha256': modelproof['metadata_sha256'],
    'selected_chat_template_sha256': modelproof['selected_chat_template_sha256'],
    'transformers': transformers.__version__, 'max_model_len': 4096,
    'classification': {'maximum_input_tokens': max_classifier, 'max_output_tokens': 128,
                       'maximum_input_plus_output': max_classifier + 128},
    'extraction': {'maximum_input_tokens': max_extractor, 'max_output_tokens': 768,
                   'maximum_input_plus_output': max_extractor + 768,
                   'by_decision': {d: {'count': len(v), 'maximum_input_tokens': max(v)} for d, v in extractor_lengths.items()}},
    'matches_previous_input_maxima': True, 'frozen_dataset_and_nine_artifact_hashes_unchanged': True,
    'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'), 'torch_imported': False,
    'network_calls': 0, 'model_calls': 0, 'gpu_calls': 0, 'weights_read': False,
    'limits': ['Payload bytes and context fit only; not grammar/kernel correctness, model quality, or staged failure-trace review.',
               'No input/gold or case-specific token counts supplied to current candidate prompt author.',
               'Any later source/prompt/schema/template change requires checking binding again before candidate freeze.'],
}
output = proofdir / 'staged_transport_binding.json'
with output.open('x') as stream:
    json.dump(proof, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'proof_path': str(output.relative_to(ROOT)), 'proof_sha256': digest(output),
                  'dataset_cases': 80, 'fake_requests': 480,
                  'classification': proof['classification'], 'extraction': proof['extraction'],
                  'source_sha256': source_after, 'source_unchanged': True}, ensure_ascii=False, indent=2))
