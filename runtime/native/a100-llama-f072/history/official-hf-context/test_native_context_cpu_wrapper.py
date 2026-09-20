"""Pure/synthetic wrapper checks only. Never main execution with actual model/data."""
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from neurobuild.infrastructure.local_model import LocalRequirementClient
spec=importlib.util.spec_from_file_location('cpu_context_subject',ROOT/'var/research/run_native_context_cpu.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ContextWrapperTests(unittest.TestCase):
 def test_actual_production_capture_uses_only_synthetic_input_context_not_gold(self):
  client=LocalRequirementClient('http://127.0.0.1:8003','neurobuild-qwen38-27b-q4-k-m',
      prompt_path=ROOT/'prompts/requirement_generation_v2_v2.txt',
      schema_path=ROOT/'schemas/requirement_generation_v2_decision_branches.schema.json',
      generation_contract='2.0',protocol='llama_cpp_json_schema',sampling_profile='qwen38_nonthinking_llama_cpp')
  raw=json.dumps({'id':'synthetic','input':'검사실 책상을 X축 +1m 옮겨줘.','context':{'axis_convention':'project_xy'},
                  'gold':{'PRIVATE_SYNTHETIC_GOLD_MARKER':'not used'}}).encode()
  requests=m.capture_requests(client,raw,1)
  self.assertEqual(len(requests),1)
  self.assertNotIn('PRIVATE_SYNTHETIC_GOLD_MARKER',json.dumps(requests))
  body=json.loads(requests[0]['messages'][1]['content'])
  self.assertEqual(body,{'source_text':'검사실 책상을 X축 +1m 옮겨줘.','axis_convention':'project_xy'})
  self.assertEqual(requests[0]['max_tokens'],768)
  self.assertEqual(requests[0]['chat_template_kwargs'],{'enable_thinking':False})
  self.assertIn('response_format',requests[0])

 def test_count_failure_prevents_even_fake_client_request(self):
  with patch.object(m,'require',wraps=m.require),patch('neurobuild.infrastructure.local_model.LocalRequirementClient.complete') as complete:
   with self.assertRaisesRegex(ValueError,'SPLIT_COUNT_MISMATCH'):
    m.capture_requests(SimpleNamespace(),b'',80)
   complete.assert_not_called()

 def test_header_failure_precedes_any_evaluation_dataset_read_or_child(self):
  def read(path,*args):return b'{}'
  with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':''}),patch.object(m.resource,'setrlimit'), \
       patch.object(m,'read_bound',side_effect=read) as reads,patch.object(m,'bind_model',side_effect=ValueError('HEADER_AUDIT_REQUIRED')), \
       patch.object(m.subprocess,'run',side_effect=AssertionError('No subprocess allowed')) as run:
   with self.assertRaisesRegex(ValueError,'HEADER_AUDIT_REQUIRED'):
    m.main(['--header-report-sha256','0'*64,'--cpu-build-report-sha256','1'*64,'--public-runner-sha256','2'*64])
   opened=[call.args[0] for call in reads.call_args_list]
   self.assertFalse(any(ROOT/row[0] in opened for row in m.SPLITS.values()))
   run.assert_not_called()

 def test_context_response_rejects_raw_output_unknown_fields_and_partial_results(self):
  with self.assertRaisesRegex(ValueError,'NATIVE_OUTPUT_SHAPE_INVALID'):
   m.validate_native({'status':'PASS','token_ids':[1,2],'source':'not allowed'},120,10,20)
  with self.assertRaisesRegex(ValueError,'NATIVE_OUTPUT_SHAPE_INVALID'):
   m.validate_native({'status':'PASS','input_count':119},120,10,20)

 def test_complete_fixed_metadata_is_accepted_only_with_full_coverage_and_context_fit(self):
  value={key:True for key in ('native_grammar_generation_prompt_prefilled','core_dump_limit_zero',
        'native_sampling_schema_binding','native_request_grammar_nonempty','native_vocab_grammar_eog_checked',
        'embedded_template_exact_match','native_embedded_vs_external_prompt_grammar_match')}
  value.update({key:False for key in ('grammar_lazy','model_context_created','backend_init_called','weight_tensors_loaded')})
  value.update(status='PASS',kind='NATIVE_CONTRACT_CPU_PREFLIGHT',native_tokenization='PASS_VOCAB_ONLY',
      tokenizer_metadata_parity='PASS',schema_cases_accepted=10,schema_cases_rejected=20,
      native_final_content_exact_cases=10,native_vocab_grammar_cases_accepted=10,native_vocab_grammar_cases_rejected=20,
      tokenizer_metadata_parity_cases=20,input_count=120,min_input_tokens=100,max_input_tokens=3328,max_input_plus_output=4096,
      native_grammar_prefill_bytes=1,native_grammar_bytes=100,standalone_grammar_bytes=100,native_request_prompt_bytes=100,
      grammar_triggers=0,discarded_stderr_bytes=0)
  self.assertEqual(m.validate_native(value,120,10,20),value)
  for changed in ({'input_count':119},{'model_context_created':True},{'schema_cases_accepted':True},
                  {'max_input_tokens':3329,'max_input_plus_output':4097},{'discarded_stderr_bytes':1}):
   with self.subTest(changed=changed),self.assertRaises(ValueError):
    m.validate_native(dict(value,**changed),120,10,20)


if __name__=='__main__':unittest.main()
