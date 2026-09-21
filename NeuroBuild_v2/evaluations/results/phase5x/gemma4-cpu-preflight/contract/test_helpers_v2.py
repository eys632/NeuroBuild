"""Pure CPU/fake tests only; no native invocation, GGUF, dataset or network."""
import copy, hashlib, importlib.util, json, unittest
from pathlib import Path
BASE=Path('/home/a202192020/NeuroBuild_v2/var/research/native-gemma4-contract')
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,BASE/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
public=module('gemma_public_tests','public_check_v2.py');vocab=module('gemma_vocab_tests','vocab_check_v2.py')
class Helpers(unittest.TestCase):
 def valid(self):
  n=json.loads((BASE/'public-proof.json').read_text())['native']
  n.update(native_tokenization='PASS_VOCAB_ONLY',native_vocab_grammar_cases_accepted=10,native_vocab_grammar_cases_rejected=20,
   native_vocab_grammar_eog_checked=True,tokenizer_metadata_parity='PASS',tokenizer_metadata_parity_cases=20,
   tokenizer_native_roundtrip_cases=20,tokenizer_expected_roundtrip_cases=20,embedded_template_exact_match=True,
   native_embedded_vs_external_effective_tokens_match=True,native_embedded_vs_external_grammar_match=True,native_generation_prompt_byte_match=True,
   native_bos_template_prefix_removed=True,native_bos_added_by_tokenizer=True,metadata_prompt_extra_bos_bytes=5,input_count=1,min_input_tokens=10,max_input_tokens=20,max_input_plus_output=788,
   resource_probe_token={'text':' ','token_id':236743})
  return n
 def test_good(self):vocab.validate_pass(0,self.valid(),1)
 def test_nonzero_exit(self):
  with self.assertRaises(ValueError):vocab.validate_pass(1,self.valid(),1)
 def test_counts_and_boolean_rejected(self):
  for key in ['input_count','tokenizer_metadata_parity_cases','tokenizer_native_roundtrip_cases','schema_cases_rejected']:
   for bad in (False,19):
    with self.subTest(key=key,bad=bad):
     value=self.valid();value[key]=bad
     with self.assertRaises(ValueError):vocab.validate_pass(0,value,1)
 def test_native_scope(self):
  for key in ('model_context_created','backend_init_called','weight_tensors_loaded','grammar_lazy'):
   value=self.valid();value[key]=True
   with self.subTest(key=key),self.assertRaises(ValueError):vocab.validate_pass(0,value,1)
 def test_context_limit(self):
  for value in (4097,789):
   native=self.valid();native['max_input_plus_output']=value
   with self.subTest(value=value),self.assertRaises(ValueError):vocab.validate_pass(0,native,1)
 def test_bad_template_parity(self):
  value=self.valid();value['native_embedded_vs_external_effective_tokens_match']=False
  with self.assertRaises(ValueError):vocab.validate_pass(0,value,1)
 def test_wrong_bos_difference(self):
  for bad in (0,4,6,True):
   value=self.valid();value['metadata_prompt_extra_bos_bytes']=bad
   with self.subTest(bad=bad),self.assertRaises(ValueError):vocab.validate_pass(0,value,1)
 def test_wrong_native_prefix_flag(self):
  for key in ('native_bos_added_by_tokenizer','native_bos_template_prefix_removed','native_generation_prompt_byte_match'):
   value=self.valid();value[key]=False
   with self.subTest(key=key),self.assertRaises(ValueError):vocab.validate_pass(0,value,1)
 def test_fake_wire_explicit(self):
  body=public.capture_request()
  self.assertEqual(body['temperature'],1.0);self.assertEqual(body['top_p'],.95);self.assertEqual(body['top_k'],64)
  self.assertEqual(body['samplers'],['temperature','top_k','top_p','min_p'])
  self.assertEqual(body['repeat_last_n'],0);self.assertEqual(body['chat_template_kwargs'],{'enable_thinking':False})
  self.assertEqual(body['response_format']['type'],'json_schema');self.assertNotIn('tools',body)
 def test_existing_public_schema_cases(self):
  cases=public.corpus();self.assertEqual(len(cases),30);self.assertEqual(sum(x['accept'] for x in cases),10)
 def test_reference_is_official_and_unrepaired(self):
  f=json.loads((BASE/'tokenizer-fixture.json').read_text())
  self.assertEqual(f['case_count'],20);self.assertEqual(f['official_original_roundtrip_count'],20)
  self.assertFalse(f['normalization_witness']['original_roundtrip'])
  self.assertEqual(f['tokenizer_sha256'],'cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f')
if __name__=='__main__':unittest.main()
