"""Only numeric timeout representation + frozen-parent preservation, no result replay."""
import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path('/home/a202192020/NeuroBuild_v2')
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=module('var/review-tools/replay_native_exaone45_exposed_v4.py','exaone_timeout_v4')
old=module(m.FROZEN_PARENT_PATH,'exaone_timeout_parent')
def read(path):return json.loads((ROOT/path).read_bytes())
class TimeoutRepresentationTests(unittest.TestCase):
    def setUp(self):
        self.manifest=read('var/runs/20260920T104448Z-10236a5d12bd48f099a4a4688ef29515/manifest.json')
        self.freeze=read('evaluations/hardening_v1_exposed_native_exaone45_diagnostic_freeze.json')
        self.runtime=read(self.freeze['runtime_metadata'])
        self.launch=read(str(Path(self.freeze['runtime_metadata']).parent/'launch_config.json'))
    def call(self,manifest=None,freeze=None,mod=m):
        mod.validate_identity(self.manifest if manifest is None else manifest,self.freeze if freeze is None else freeze,
            self.runtime,self.launch,self.manifest['git']['commit'],expected_variant=m.VARIANT)
    def test_observed_original_failure_and_only_equal_numeric_forms_pass(self):
        self.assertIs(type(self.manifest['protocol']['timeout_seconds']),float)
        self.assertIs(type(self.freeze['timeout_seconds']),int)
        with self.assertRaisesRegex(AssertionError,'protocol_timeout_seconds'):self.call(mod=old)
        self.call()
        for a,b in ((120,120),(120.0,120),(120,120.0),(120.0,120.0)):
            manifest=deepcopy(self.manifest);freeze=deepcopy(self.freeze)
            manifest['protocol']['timeout_seconds']=a;freeze['timeout_seconds']=b
            with self.subTest(manifest=a,freeze=b):self.call(manifest,freeze)
    def test_boolean_nonfinite_strings_and_other_values_rejected_on_both_sides(self):
        for bad in (True,False,119,120.001,0,float('nan'),float('inf'),float('-inf'),'120',None,10**400):
            for side in ('manifest','freeze'):
                manifest=deepcopy(self.manifest);freeze=deepcopy(self.freeze)
                (manifest['protocol'] if side=='manifest' else freeze)['timeout_seconds']=bad
                with self.subTest(side=side,value=repr(bad)),self.assertRaisesRegex(AssertionError,'protocol_timeout_seconds'):
                    self.call(manifest,freeze)
        # Other integer protocol fields retain their original exact types.
        manifest=deepcopy(self.manifest);manifest['protocol']['max_tokens']=768.0
        with self.assertRaisesRegex(AssertionError,'protocol_max_tokens'):self.call(manifest)
    def test_original_parent_remains_required_and_three_cores_ast_exact(self):
        m.validate_frozen_parent(self.freeze)
        freeze=deepcopy(self.freeze);freeze['sha256'][m.FROZEN_PARENT_PATH]='0'*64
        with self.assertRaisesRegex(AssertionError,'original_frozen_replay_parent_changed'):m.validate_frozen_parent(freeze)
        with patch.object(m,'digest',return_value='0'*64),self.assertRaisesRegex(AssertionError,'original_frozen_replay_parent_changed'):
            m.validate_frozen_parent(self.freeze)
        before=ast.parse((ROOT/m.FROZEN_PARENT_PATH).read_text())
        after=ast.parse((ROOT/'var/review-tools/replay_native_exaone45_exposed_v4.py').read_text())
        for name in ('load_snapshot','replay_row','replay_groups','validate_evidence'):
            get=lambda t:next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(get(before),include_attributes=False),ast.dump(get(after),include_attributes=False),name)
if __name__=='__main__':unittest.main()
