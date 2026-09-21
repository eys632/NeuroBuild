"""Synthetic scalar gate controls; no native/data/network calls."""
from pathlib import Path
import copy,hashlib,importlib.util,json,unittest
BASE=Path(__file__).resolve().parent
HELPER_SHA='481a40c8c6372aadb1e146b977f90ea61231fca81a87fd3c9ecb02f32ffd892e'
assert hashlib.sha256((BASE/'raw_context_check.py').read_bytes()).hexdigest()==HELPER_SHA
s=importlib.util.spec_from_file_location('raw_context',BASE/'raw_context_check.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Gates(unittest.TestCase):
 def good(self):
  n=copy.deepcopy(json.loads((BASE/'public-vocab-proof.json').read_text())['native'])
  n.pop('official_reference_gate_pass')
  n.update(status='PASS',tokenizer_id_match_count=20,tokenizer_id_mismatch_mask=0,tokenizer_reference_ids_raw_roundtrip_count=20,
   tokenizer_reference_parity='PASS',reference_kind='derived_hf_nfc_disabled',reference_gate_pass=True,
   official_hf_equivalence='NOT_ASSERTED_BY_DERIVED_REFERENCE',input_count=1,min_input_tokens=1910,max_input_tokens=1910,
   max_input_plus_output=2678,all_context_system_user_bytes_exact=True)
  return n
 def test_scalar_valid(self):m.validate_raw(0,self.good(),1)
 def test_original_official_failure_stays_failure(self):
  with self.assertRaises(ValueError):m.validate_raw(1,json.loads((BASE/'public-vocab-proof.json').read_text())['native'],1)
 def test_one_id_mismatch_rejected(self):
  n=self.good();n['tokenizer_id_match_count']=19
  with self.assertRaises(ValueError):m.validate_raw(0,n,1)
 def test_one_raw_loss_rejected(self):
  n=self.good();n['tokenizer_native_raw_roundtrip_count']=19
  with self.assertRaises(ValueError):m.validate_raw(0,n,1)
 def test_official_success_mislabel_rejected(self):
  n=self.good();n['official_reference_gate_pass']=True
  with self.assertRaises(ValueError):m.validate_raw(0,n,1)
 def test_wrong_reference_kind_rejected(self):
  n=self.good();n['reference_kind']='official_hf_nfc'
  with self.assertRaises(ValueError):m.validate_raw(0,n,1)
 def test_count_and_context_limit(self):
  for changes in ({'input_count':80},{'max_input_tokens':3330,'max_input_plus_output':4098}):
   n=self.good();n.update(changes)
   with self.assertRaises(ValueError):m.validate_raw(0,n,1)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Gates))
 proof={'kind':'EXAONE45_RAW_REFERENCE_GATE_SYNTHETIC_CONTROLS','status':'PASS' if result.wasSuccessful() else 'FAIL',
  'tests':result.testsRun,'helper_sha256':HELPER_SHA,'selftest_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  'native_calls':0,'evaluation_body_reads':0,'model_calls':0,'gpu_calls':0,'http_calls':0}
 p=BASE/'raw-context-selfcheck.json'
 with p.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
 print(json.dumps({'status':proof['status'],'tests':proof['tests'],'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
 raise SystemExit(not result.wasSuccessful())
