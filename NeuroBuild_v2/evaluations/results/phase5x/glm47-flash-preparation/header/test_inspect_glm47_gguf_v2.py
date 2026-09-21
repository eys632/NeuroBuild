"""Observed GLM artifact contract controls; saved metadata only, real GGUF never read."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

P=Path(__file__).with_name('inspect_glm47_gguf_v2.py')
s=importlib.util.spec_from_file_location('glm2',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


class ObservedArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.idx,cls.bind,cls.pins=m.load_reference()
        raw=(m.ROOT/m.FIRST_DIAGNOSTIC).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==m.FIRST_DIAGNOSTIC_SHA
        saved=json.loads(raw);cls.header=saved['header'];cls.values=dict(saved['architecture_metadata_values'])
        for key,entry in cls.header['metadata'].items():
            if 'value' in entry:cls.values[key]=entry['value']
        # Parser intentionally retained only hashes for many strings. Recover a
        # known expected scalar only if its saved exact-byte digest verifies it.
        for key,value in m.expected_metadata(cls.cfg,15).items():
            if key not in cls.values and type(value) is str:
                assert cls.header['metadata'][key]['sha256']==hashlib.sha256(value.encode()).hexdigest()
                cls.values[key]=value

    def fixture(self):return copy.deepcopy(self.header),copy.deepcopy(self.values)
    def validate(self,h,v,idx=None):return m.validate_candidate(h,v,self.cfg,idx or self.idx,self.bind)

    def test_saved_observation_matches_explicit_variant_without_fullhash_claim(self):
        h,v=self.fixture();out=self.validate(h,v)
        self.assertEqual(out['quantization'],'Q4_K_M')
        self.assertEqual(out['expected_tensor_names_shapes_matched'],844)
        self.assertEqual(out['represented_upstream_main_names'],9491)
        self.assertEqual(out['omitted_upstream_mtp_names'],212)
        self.assertEqual(out['exact_tensor_payload_bytes']+out['exact_header_and_alignment_bytes'],m.FILE_BYTES)
        self.assertEqual(out['nextn_layer_count'],0)
        self.assertEqual(out['actual_role_dtype_counts'],{'f32':281,'q8_0':48,'q4_K':470,'q6_K':45})
        self.assertEqual(out['main_kv_f16_context4096_seq1_mib'],211.5)

    def test_generic_parser_and_tokenizer_validator_ast_preserved(self):
        old=(m.ROOT/m.V1_HELPER).read_bytes();self.assertEqual(hashlib.sha256(old).hexdigest(),m.V1_HELPER_SHA)
        a,b=ast.parse(old),ast.parse(P.read_bytes())
        for name in ('AuditError','require','safe_open','read_bound','stat_key','Reader','parse_header','finish_hash','tokenizer_bindings'):
            self.assertEqual(ast.dump(next(x for x in a.body if getattr(x,'name',None)==name)),
                ast.dump(next(x for x in b.body if getattr(x,'name',None)==name)),name)
        # Ensure original strict v1 has NOT silently been relaxed for the artifact.
        spec=importlib.util.spec_from_file_location('glm1',m.ROOT/m.V1_HELPER)
        v1=importlib.util.module_from_spec(spec);spec.loader.exec_module(v1)
        h,v=self.fixture()
        with self.assertRaisesRegex(v1.AuditError,'CONFIG_METADATA_MISMATCH'):
            v1.validate_candidate(h,v,self.cfg,self.idx,self.bind)

    def test_ftype_and_no_mtp_boundary_not_generic_model_variants(self):
        for value in (14,14.0,True,16):
            h,v=self.fixture();v['general.file_type']=value
            with self.assertRaisesRegex(m.AuditError,'FILE_TYPE_UNSUPPORTED'):self.validate(h,v)
        for value in (0,1):
            h,v=self.fixture();h['metadata']['deepseek2.nextn_predict_layers']={'type':4};v['deepseek2.nextn_predict_layers']=value
            with self.assertRaisesRegex(m.AuditError,'UNEXPECTED_MTP_METADATA'):self.validate(h,v)
        h,v=self.fixture();v['deepseek2.block_count']=48
        with self.assertRaisesRegex(m.AuditError,'CONFIG_METADATA_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['tensors'][0]['name']='blk.47.nextn.eh_proj.weight'
        with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SET_MISMATCH'):self.validate(h,v)

    def test_exact_q8_roles_and_47_layer_down_pattern(self):
        for name,typ in [('output.weight',14),('blk.0.attn_k_b.weight',6),
                         ('token_embd.weight',8),('blk.1.attn_v_b.weight',8),
                         ('blk.5.ffn_down_exps.weight',14),('blk.7.ffn_down_exps.weight',12),
                         ('blk.41.ffn_down_shexp.weight',12),('blk.1.ffn_gate_inp.weight',8)]:
            h,v=self.fixture();r=next(x for x in h['tensors'] if x['name']==name)
            r.update(type_id=typ,dtype=m.TYPES[typ][0])
            with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH'):self.validate(h,v)

    def test_only_exact212_mtp_upstream_names_may_be_omitted_from_export(self):
        for name in ('model.layers.47.hnorm.weight','model.layers.46.mlp.experts.63.up_proj.weight'):
            h,v=self.fixture();idx=copy.deepcopy(self.idx);idx['weight_map'].pop(name)
            with self.assertRaisesRegex(m.AuditError,'UPSTREAM_MTP_INDEX_MISMATCH'):self.validate(h,v,idx)
        h,v=self.fixture();idx=copy.deepcopy(self.idx);idx['weight_map']['model.layers.48.extra.weight']='unknown'
        with self.assertRaisesRegex(m.AuditError,'UPSTREAM_MTP_INDEX_MISMATCH'):self.validate(h,v,idx)

    def test_exact_shapes_packed_bytes_padding_and_untied_presence(self):
        for name in ('output.weight','token_embd.weight','blk.46.attn_k_b.weight','blk.1.ffn_down_exps.weight'):
            h,v=self.fixture();r=next(x for x in h['tensors'] if x['name']==name);r['shape'][0]+=32
            with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH'):self.validate(h,v)
        for key in ('tensor_payload_bytes','tensor_padding_bytes','data_offset','alignment'):
            h,v=self.fixture();h[key]+=32
            with self.assertRaisesRegex(m.AuditError,'ARTIFACT_BYTE_LAYOUT_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['tensors']=[x for x in h['tensors'] if x['name']!='output.weight']
        with self.assertRaisesRegex(m.AuditError,'EXPECTED_TENSOR_SET_MISMATCH'):self.validate(h,v)

    def test_mla_and_template_content_not_relaxed_for_recipe_difference(self):
        for key,value in [('deepseek2.attention.head_count_kv',20),('deepseek2.attention.key_length_mla',192)]:
            h,v=self.fixture();v[key]=value
            with self.assertRaisesRegex(m.AuditError,'CONFIG_METADATA_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['metadata']['tokenizer.chat_template']['sha256']='0'*64
        with self.assertRaisesRegex(m.AuditError,'EMBEDDED_TEMPLATE_MISMATCH'):self.validate(h,v)
        h,v=self.fixture();h['metadata']['tokenizer.ggml.tokens']['elements_wire_sha256']='0'*64
        with self.assertRaisesRegex(m.AuditError,'TOKENIZER_CONTENT_MISMATCH'):self.validate(h,v)


if __name__=='__main__':unittest.main(verbosity=2)
