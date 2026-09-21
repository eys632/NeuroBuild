"""Focused props representation checks only; no HTTP/process/native/GPU calls."""
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path('/home/a202192020/NeuroBuild_v2')
spec=importlib.util.spec_from_file_location('gemma_probe_v3',ROOT/'var/research/gemma4_runtime_probe_v3.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
TEMPLATE=ROOT/'var/research/gemma4-31b-qat-candidate-metadata/qat-unquantized/chat_template.jinja'


class PropsRepresentationTests(unittest.TestCase):
    def fixture(self):
        config=SimpleNamespace(served_model_name='gemma-owned',model_path=Path('/fixture/gemma.gguf'))
        raw=TEMPLATE.read_bytes()
        props={'model_alias':'gemma-owned','total_slots':1,'model_path':'/fixture/gemma.gguf',
            'default_generation_settings':{'n_ctx':4096},'chat_template':raw[:-1].decode(),'is_sleeping':False}
        models={'data':[{'id':'gemma-owned','meta':{'n_ctx':4096}}]}
        return config,raw,props,models

    def test_actual_template_exact_terminal_lf_derivation_and_distinct_receipt(self):
        config,raw,props,models=self.fixture()
        self.assertEqual(len(raw),18683);self.assertTrue(raw.endswith(b'\n'));self.assertNotIn(b'\r',raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),m.TEMPLATE_SHA)
        self.assertEqual(hashlib.sha256(raw[:-1]).hexdigest(),m.PROPS_TEMPLATE_SHA)
        with patch.object(m.base,'checked_file',side_effect=lambda path,root:path):
            result=m.validate_health_models_props(config,{'status':'ok'},models,props)
        self.assertEqual(result['chat_template_sha256'],m.TEMPLATE_SHA)
        self.assertEqual(result['embedded_chat_template_sha256'],m.TEMPLATE_SHA)
        self.assertEqual(result['props_reported_template_sha256'],m.PROPS_TEMPLATE_SHA)
        self.assertEqual(result['embedded_chat_template_bytes'],18683)
        self.assertEqual(result['props_reported_template_bytes'],18682)
        self.assertNotIn('chat_template',result)
        self.assertNotEqual(result['props_reported_template_sha256'],result['chat_template_sha256'])

    def test_no_broad_strip_or_arbitrary_template_acceptance(self):
        config,raw,props,models=self.fixture()
        variants=[raw,raw+b'\n',raw[:-1]+b' ',raw[:-2],b' '+raw[:-1],raw[:-2]+b'X']
        with patch.object(m.base,'checked_file',side_effect=lambda path,root:path):
            for index,value in enumerate(variants):
                with self.subTest(index=index),self.assertRaisesRegex(ValueError,'PROPS_MISMATCH'):
                    m.validate_health_models_props(config,{'status':'ok'},models,
                                                  {**props,'chat_template':value.decode()})
            for key,value in [('model_path','/other'),('total_slots',2),('model_alias','wrong')]:
                with self.subTest(field=key),self.assertRaisesRegex(ValueError,'PROPS_MISMATCH'):
                    m.validate_health_models_props(config,{'status':'ok'},models,{**props,key:value})

    def test_metadata_keeps_original_embedded_hash(self):
        config=SimpleNamespace(source_commit='f072b103714dfa1eee531f80b24512faf38e3dd2',
            binary_sha256='a'*64,source_report_sha256='b'*64,build_report_sha256='c'*64,
            model_sha256=m.MODEL_SHA,model_header_report_sha256='d'*64)
        platform={'compiler':'GCC9.5','cmake':'3.23.5','cuda':'11.8','driver':'535.183.01',
            'gpu':'A100-PCIE-40GB','gpu_uuid':'GPU-00000000-0000-0000-0000-000000000000'}
        metadata=m.make_metadata(config,platform,'1'*64,'2'*64,'3'*64)
        self.assertEqual(metadata['chat_template_sha256'],m.TEMPLATE_SHA)
        self.assertEqual(metadata['quantization'],'Q4_0')
        self.assertNotIn('props_reported_template_sha256',metadata)


if __name__=='__main__':unittest.main()
