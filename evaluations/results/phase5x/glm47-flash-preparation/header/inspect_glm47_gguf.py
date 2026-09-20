#!/usr/bin/env python3
"""GLM4.7 Flash pinned text GGUF audit, stdlib CPU only.

Preparation does not read model bytes. Root must authorize each real invocation.
Default: exact header/layout/metadata then one streaming full SHA256; no numeric
weight decoding. --metadata-only: bounded header diagnosis, NEVER a PASS receipt.
Unknown dtypes and unsupported layouts fail closed; no automatic policy widening.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
META = Path('var/research/glm47-flash-candidate-metadata/upstream')
MODEL_ID = 'ggml-org/GLM-4.7-Flash-GGUF'
REVISION = '7559e96b7e324ab405897dc2b91492b0f376ad4a'
UPSTREAM_MODEL_ID = 'zai-org/GLM-4.7-Flash'
UPSTREAM_REVISION = '7dd20894a642a0aa287e9827cb1a1f7f91386b67'
RUNTIME = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
FILENAME = 'GLM-4.7-Flash-Q4_K.gguf'
FILE_BYTES = 18_244_193_920
FILE_SHA = 'b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2'
MODEL_RELATIVE = Path('var/models/ggml-org--GLM-4.7-Flash-GGUF')/REVISION/FILENAME
CONFIG_SHA = 'dc9b97c7c9bed726a2e6939da4234d5c43abb3edec8812068c9a1af1dbc13acb'
TOKENIZER_SHA = '19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d'
TOKENIZER_CONFIG_SHA = '31a173e2797ddc8b72ac996803513e627fc28d7aad02cfcce321a431d865c86d'
TEMPLATE_SHA = 'd63ad536c3c81880043e22ec7fd08db42b4d8fb7c89c7138bc562bfa25281375'
TEMPLATE_BYTES = 3120
INDEX_SHA = '91e6e95ca21700f50904a680c8c4212f5aa16dc7c10a013f01c906957c889791'
VOCAB_EXPECTATION = Path('var/research/native-glm47-contract/static_vocab_expectation.json')
VOCAB_EXPECTATION_SHA = '60278f9c4379d3fea820ecfd852015bdeadcf5071e39da1846b89bc1ebdedf28'
BASE_HELPER_SHA = 'cb8ef9e58aea7066c050d3e96da24708b4be4eae0c7c7498f879e2dddc41940c'
# Known byte formats for bounded description only; tensor_spec independently
# restricts every accepted role. F16/Q8_0/BF16 never satisfy this v1 policy.
TYPES = {0:('f32',1,4), 1:('f16',1,2), 6:('q5_0',32,22), 8:('q8_0',32,34),
         12:('q4_K',256,144), 13:('q5_K',256,176), 14:('q6_K',256,210), 30:('bf16',1,2)}
FTYPES = {14:'Q4_K_S',15:'Q4_K_M'}
SOURCE_PINS = {'conversion/glm.py': 'cbc38cb64a414079233b8ce10b9eb63c1f4814ab53f06ce578c44969dad7c377', 'conversion/deepseek.py': '09ba15cefd9448d13f27eb0b46462d1a845d7576a6b401f0bf81d73e0419d655', 'conversion/base.py': 'e0ae8621e67e8b8ea2682177b1f16adbe95b2c154ee8e2de975e942148d66575', 'src/models/deepseek2.cpp': '56b30a535507bc299a5128c076c01c4c3097230d4a6ad934015d4186745ed6ed', 'src/llama-quant.cpp': 'a33dea76120a10b2eac8b5d81b9425dcd401e2c8ae4bb04f59b00922f0355fdd', 'src/llama-hparams.cpp': 'ef6fbef7d12a23441b42cfac8e3a3a3045c7d3123402351ba98e69702e193301', 'src/llama-model.cpp': '530dff0cd544382346cc18520cbdb7d7a6f6743c35f7af52aae0bec11d18992a', 'src/llama-kv-cache.cpp': '16b40ff274e5aed3827f0d1c13a04f4f44c4d800c4eecbb5294b04127ab213c3', 'gguf-py/gguf/constants.py': 'df0078c283a48061260ca4b3f35df36611230c3e7c2ac271bb8a11d2632839ba', 'gguf-py/gguf/tensor_mapping.py': 'df97c2291dc1d8e8992ae91b800e0cf139f94d5173b9ed4705f5ef75a371d924', 'gguf-py/gguf/vocab.py': '16cddd93700f86c8b72e6f9e741e2362189155b9f96aa9e3bbb0995060095f1a', 'gguf-py/gguf/gguf_writer.py': '7e3ff8d04b290dde083ae30d1091b67c95299f6865958fe1cdcb7e35dd201766', 'ggml/include/ggml.h': '12ee71f99db7db9b353bc02b1fbb57c344ee17c01ac5fb7952b41a637a747ea9', 'ggml/src/ggml-common.h': '0061131b615c5721fc88a78feeb22c1f8c450f1c2646a317d80796a653bf595c', 'ggml/src/ggml-cuda/mmq.cu': 'a35bb96dfc917c9026023482e24dcf47539fc08ccee1bb4236f40932e9fe540e', 'src/llama-vocab.cpp': '82e8996cbbd81c1648b1f4946b5f481138aa897a1343dcd8b1a4abe8cff0b5fc'}
SCALARS = {0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'B',10:'Q',11:'q',12:'d'}
HEADER_CAP = 32*1024**2
STRING_CAP = 1024**2
ARRAY_CAP = 1_000_000
NAME = re.compile(r'[A-Za-z0-9_.-]{1,127}\Z')


class AuditError(Exception):
    """Only fixed error codes are surfaced, never metadata text/token strings."""


def require(condition, code):
    if not condition:
        raise AuditError(code)


@contextmanager
def safe_open(root: Path, relative: Path, *, write=False):
    require(not relative.is_absolute() and relative.parts and
            all(x not in ('', '.', '..') for x in relative.parts), 'PATH_INVALID')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        require(os.fstat(fd).st_uid == os.getuid(), 'PATH_NOT_OWNED')
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            require(os.fstat(fd).st_uid == os.getuid(), 'PATH_NOT_OWNED')
        flags = os.O_NOFOLLOW | (os.O_WRONLY | os.O_CREAT | os.O_EXCL if write else os.O_RDONLY | os.O_NONBLOCK)
        leaf = os.open(relative.name, flags, 0o600, dir_fd=fd)
        with os.fdopen(leaf, 'wb' if write else 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode), 'NOT_REGULAR')
            require(info.st_uid == os.getuid(), 'PATH_NOT_OWNED')
            require(info.st_nlink == 1, 'FILE_MULTIPLE_LINKS')
            yield stream
            if write:
                stream.flush()
                os.fsync(stream.fileno())
        if write:
            os.fsync(fd)
    finally:
        os.close(fd)


def read_bound(relative, digest, cap):
    with safe_open(ROOT, relative) as f:
        before = os.fstat(f.fileno())
        require(before.st_size <= cap, 'METADATA_TOO_LARGE')
        data = f.read(cap + 1)
        require(len(data) == before.st_size, 'METADATA_CHANGED')
        require(stat_key(before) == stat_key(os.fstat(f.fileno())), 'METADATA_CHANGED')
    require(hashlib.sha256(data).hexdigest() == digest, 'METADATA_HASH_MISMATCH')
    return data


def stat_key(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


class Reader:
    def __init__(self, stream, size):
        self.stream, self.size, self.offset = stream, size, 0
        self.sha = hashlib.sha256()

    def read(self, n, *, header=True):
        require(type(n) is int and n >= 0 and n <= self.size-self.offset, 'TRUNCATED')
        require(not header or self.offset+n <= HEADER_CAP, 'HEADER_TOO_LARGE')
        result = self.stream.read(n)
        require(len(result) == n, 'TRUNCATED')
        self.offset += n
        self.sha.update(result)
        return result

    def num(self, fmt):
        return struct.unpack('<'+fmt, self.read(struct.calcsize('<'+fmt)))[0]

    def string(self, cap=STRING_CAP):
        n = self.num('Q')
        require(n <= cap, 'STRING_TOO_LARGE')
        raw = self.read(n)
        try:
            text = raw.decode('utf-8', 'strict')
        except UnicodeDecodeError:
            raise AuditError('INVALID_UTF8') from None
        return text, raw

    def value(self, typ):
        if typ == 8:
            return self.string()[0]
        require(typ in SCALARS, 'UNKNOWN_METADATA_TYPE')
        value = self.num(SCALARS[typ])
        if typ == 7:
            require(value in (0, 1), 'INVALID_BOOL')
            return bool(value)
        if typ in (6, 12):
            require(math.isfinite(value), 'NONFINITE_METADATA')
        return value


def parse_header(r: Reader):
    require(r.read(4) == b'GGUF', 'MAGIC_INVALID')
    require(r.num('I') == 3, 'VERSION_UNSUPPORTED')
    count, kvcount = r.num('Q'), r.num('Q')
    require(0 < count <= 2048 and 0 < kvcount <= 1024, 'COUNT_INVALID')
    metadata, values = {}, {}
    for _ in range(kvcount):
        key, _raw = r.string(256)
        require(NAME.fullmatch(key) is not None, 'METADATA_KEY_INVALID')
        require(key not in metadata, 'DUPLICATE_METADATA')
        typ = r.num('I')
        start = r.offset
        # Keep only small scalar values/numeric arrays. Never retain token/merge strings.
        if typ == 9:
            subtype, n = r.num('I'), r.num('Q')
            require(subtype in SCALARS or subtype == 8, 'UNKNOWN_ARRAY_TYPE')
            require(n <= ARRAY_CAP, 'ARRAY_TOO_LARGE')
            arr = [] if subtype != 8 and n <= 128 else None
            digest = hashlib.sha256()
            for _ in range(n):
                if subtype == 8:
                    _s, raw = r.string()
                    digest.update(struct.pack('<Q', len(raw)))
                    digest.update(raw)
                else:
                    v = r.value(subtype)
                    digest.update(struct.pack('<'+SCALARS[subtype], v))
                    if arr is not None:
                        arr.append(v)
            summary = {'type': typ, 'element_type': subtype, 'count': n,
                       'elements_wire_sha256': digest.hexdigest()}
            if arr is not None:
                values[key] = arr
        elif typ == 8:
            v, raw = r.string()
            summary = {'type': typ, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            if not key.startswith('tokenizer.chat_template') and len(raw) <= 128:
                values[key] = v
        else:
            v = r.value(typ)
            summary = {'type': typ, 'value': v}
            values[key] = v
        summary['wire_bytes'] = r.offset-start
        metadata[key] = summary
    alignment = values.get('general.alignment', 32)
    require('general.alignment' not in metadata or metadata['general.alignment']['type'] == 4,
            'ALIGNMENT_TYPE_INVALID')
    require(type(alignment) is int and 0 < alignment <= 4096 and alignment & (alignment-1) == 0,
            'ALIGNMENT_INVALID')
    tensors, names = [], set()
    for _ in range(count):
        name, raw = r.string(127)
        require(NAME.fullmatch(name) is not None, 'TENSOR_NAME_INVALID')
        require(name not in names, 'DUPLICATE_TENSOR')
        names.add(name)
        nd = r.num('I')
        require(1 <= nd <= 4, 'DIMENSIONS_INVALID')
        dims = [r.num('Q') for _ in range(nd)]
        require(all(0 < n <= 2**31-1 for n in dims), 'SHAPE_INVALID')
        typ, offset = r.num('I'), r.num('Q')
        require(typ in TYPES, 'TENSOR_TYPE_UNSUPPORTED')
        dtype, block, blockbytes = TYPES[typ]
        require(dims[0] % block == 0, 'QUANT_ROW_INVALID')
        elems = math.prod(dims)
        nbytes = (elems//block)*blockbytes
        require(0 < elems < 2**63 and 0 < nbytes <= r.size, 'TENSOR_SIZE_INVALID')
        require(offset % alignment == 0, 'OFFSET_ALIGNMENT_INVALID')
        tensors.append({'name':name, 'shape':dims, 'shape_padded':dims+[1]*(4-nd),
                        'type_id':typ, 'dtype':dtype, 'offset':offset, 'bytes':nbytes})
    header_bytes = r.offset
    data_offset = (header_bytes+alignment-1)//alignment*alignment
    require(not any(r.read(data_offset-header_bytes)), 'NONZERO_HEADER_PADDING')
    # Candidate is a single packed GGUF. Arbitrary gaps/overlap/trailing data are rejected.
    end = 0
    for row in sorted(tensors, key=lambda t:t['offset']):
        require(row['offset'] == end, 'TENSOR_GAP_OR_OVERLAP')
        end += (row['bytes']+alignment-1)//alignment*alignment
        require(data_offset+end <= r.size, 'TENSOR_OUT_OF_BOUNDS')
    require(data_offset+end == r.size, 'FILE_COVERAGE_MISMATCH')
    return {'version':3, 'tensor_count':count, 'metadata_count':kvcount,
            'header_bytes':header_bytes, 'data_offset':data_offset, 'alignment':alignment,
            'tensor_payload_bytes':sum(t['bytes'] for t in tensors),
            'tensor_padding_bytes':end-sum(t['bytes'] for t in tensors),
            'dtype_counts':dict(Counter(t['dtype'] for t in tensors)),
            'metadata':metadata, 'tensors':tensors}, values


def finish_hash(r: Reader, header):
    for row in sorted(header['tensors'], key=lambda t:t['offset']):
        remaining = row['bytes']
        while remaining:
            n = min(4*1024**2, remaining)
            r.read(n, header=False)
            remaining -= n
        padding = (-row['bytes']) % header['alignment']
        require(not any(r.read(padding, header=False)), 'NONZERO_TENSOR_PADDING')
    require(r.offset == r.size and not r.stream.read(1), 'FILE_COVERAGE_MISMATCH')
    return r.sha.hexdigest()


def require_config(config):
    expected = {'architectures':['Glm4MoeLiteForCausalLM'],'model_type':'glm4_moe_lite',
        'hidden_size':2048,'intermediate_size':10240,'moe_intermediate_size':1536,
        'num_hidden_layers':47,'num_nextn_predict_layers':1,'num_attention_heads':20,
        'num_key_value_heads':20,'q_lora_rank':768,'kv_lora_rank':512,
        'qk_nope_head_dim':192,'qk_rope_head_dim':64,'v_head_dim':256,
        'n_routed_experts':64,'num_experts_per_tok':4,'n_shared_experts':1,
        'first_k_dense_replace':1,'n_group':1,'topk_group':1,'topk_method':'noaux_tc',
        'routed_scaling_factor':1.8,'norm_topk_prob':True,'tie_word_embeddings':False,
        'vocab_size':154880,'max_position_embeddings':202752,'rms_norm_eps':1e-5,
        'hidden_act':'silu','attention_bias':False,'rope_scaling':None,'rope_theta':1000000}
    require(all(type(config.get(k)) is type(v) and config[k]==v for k,v in expected.items()),
            'UPSTREAM_CONFIG_UNEXPECTED')
    return config


def down_type(layer, ftype):
    """Exact default f072 quantizer policy; unpublished custom overrides not inferred."""
    require(type(ftype) is int and ftype in FTYPES, 'FILE_TYPE_UNSUPPORTED')
    if ftype == 14:
        return 13 if layer < 48//8 else 12
    more = layer < 48//8 or layer >= 7*48//8 or (layer-48//8)%3 == 2
    return 14 if more else 12


def tensor_spec(config, index, ftype):
    """All 9703 official source names -> default full-MTP, split-MLA 868 tensors.

    No --no-mtp, legacy unsplit MLA, fused gate/up, or per-tensor override is
    silently accepted. A real mismatch needs a preserved diagnostic and review.
    """
    require_config(config)
    require(type(ftype) is int and ftype in FTYPES, 'FILE_TYPE_UNSUPPORTED')
    spec = {'token_embd.weight':([2048,154880],{12}),
            'output.weight':([2048,154880],{14}), 'output_norm.weight':([2048],{0})}
    source = {'model.embed_tokens.weight','lm_head.weight','model.norm.weight'}
    roles = {
      'input_layernorm.weight':('attn_norm',[2048],0),
      'post_attention_layernorm.weight':('ffn_norm',[2048],0),
      'self_attn.q_a_layernorm.weight':('attn_q_a_norm',[768],0),
      'self_attn.kv_a_layernorm.weight':('attn_kv_a_norm',[512],0),
      'self_attn.q_a_proj.weight':('attn_q_a',[2048,768],12),
      'self_attn.q_b_proj.weight':('attn_q_b',[768,5120],12),
      'self_attn.kv_a_proj_with_mqa.weight':('attn_kv_a_mqa',[2048,576],12),
      'self_attn.o_proj.weight':('attn_output',[5120,2048],12)}
    for layer in range(48):
        prefix=f'model.layers.{layer}'; out=f'blk.{layer}'
        for hf,(role,dims,typ) in roles.items():
            source.add(f'{prefix}.{hf}');spec[f'{out}.{role}.weight']=(dims,{typ})
        source.add(f'{prefix}.self_attn.kv_b_proj.weight')
        # K transposed by converter: ne0=192 cannot use 256-element K block.
        # OTHER-category Q4_K -> Q5_0 is the exact pinned fallback.
        spec[f'{out}.attn_k_b.weight']=([192,512,20],{6})
        spec[f'{out}.attn_v_b.weight']=([512,256,20],{12})
        down=down_type(layer,ftype)
        if layer==0:
            for hf,dims,typ in [('gate',[2048,10240],12),('up',[2048,10240],12),
                                ('down',[10240,2048],down)]:
                source.add(f'{prefix}.mlp.{hf}_proj.weight')
                spec[f'{out}.ffn_{hf}.weight']=(dims,{typ})
        else:
            source.update((f'{prefix}.mlp.gate.weight',f'{prefix}.mlp.gate.e_score_correction_bias'))
            spec[f'{out}.ffn_gate_inp.weight']=([2048,64],{0})
            spec[f'{out}.exp_probs_b.bias']=([64],{0})
            for hf,dims,typ in [('gate',[2048,1536],12),('up',[2048,1536],12),
                                ('down',[1536,2048],down)]:
                source.add(f'{prefix}.mlp.shared_experts.{hf}_proj.weight')
                spec[f'{out}.ffn_{hf}_shexp.weight']=(dims,{typ})
                spec[f'{out}.ffn_{hf}_exps.weight']=(dims+[64],{typ})
                source.update(f'{prefix}.mlp.experts.{e}.{hf}_proj.weight' for e in range(64))
    for hf,role,dims,typ in [
      ('embed_tokens','embed_tokens',[2048,154880],12),
      ('shared_head.head','shared_head_head',[2048,154880],12),
      ('shared_head.norm','shared_head_norm',[2048],0),
      ('eh_proj','eh_proj',[4096,2048],12),
      ('enorm','enorm',[2048],0),('hnorm','hnorm',[2048],0)]:
        source.add(f'model.layers.47.{hf}.weight')
        spec[f'blk.47.nextn.{role}.weight']=(dims,{typ})
    require(type(index.get('weight_map')) is dict and set(index['weight_map'])==source
            and len(source)==9703 and len(spec)==868, 'UPSTREAM_MTP_INDEX_MISMATCH')
    return spec


def strings_wire_sha(strings):
    digest=hashlib.sha256()
    for value in strings:
        require(type(value) is str,'TOKENIZER_SOURCE_INVALID')
        raw=value.encode('utf-8');digest.update(struct.pack('<Q',len(raw)));digest.update(raw)
    return digest.hexdigest()


def tokenizer_bindings(tokenizer, tokenizer_config, expectation):
    model=tokenizer['model'];vocab=model['vocab']
    require(model['type']=='BPE' and model['byte_fallback'] is False
            and tokenizer['normalizer'] is None and len(vocab)==154820
            and all(type(x) is int for x in vocab.values())
            and set(vocab.values())==set(range(154820)), 'TOKENIZER_SOURCE_INVALID')
    ordered=[None]*154880;types=[1]*154820+[5]*60
    for token,idx in vocab.items(): ordered[idx]=token
    added=tokenizer['added_tokens'];seen=set()
    require(len(added)==36,'TOKENIZER_SOURCE_INVALID')
    for row in added:
        idx,token=row['id'],row['content']
        require(type(idx) is int and idx not in seen and 154820<=idx<154856
                and type(token) is str and '\u2581' not in token
                and row['normalized'] is False and type(row['special']) is bool,
                'TOKENIZER_SOURCE_INVALID')
        seen.add(idx);ordered[idx]=token
        looks_special=(token in ('<pad>','<mask>','<2mass>','[@BOS@]')
                       or token.startswith('<|') and token.endswith('|>')
                       or token.startswith('<｜') and token.endswith('｜>')
                       or token.startswith('<unused') and token.endswith('>'))
        types[idx]=3 if row['special'] or looks_special else 4
    require(seen==set(range(154820,154856)),'TOKENIZER_SOURCE_INVALID')
    for i in range(154856,154880): ordered[i]=f'[PAD{i}]'
    merges=model['merges']
    require(len(merges)==321649 and all(type(p) is list and len(p)==2
            and all(type(x) is str for x in p) for p in merges), 'TOKENIZER_SOURCE_INVALID')
    special={'bos':154822,'eos':154820,'pad':154820,'unk':154820,'eot':154827,'eom':154829}
    require(ordered[special['bos']]=='[gMASK]' and ordered[special['eot']]=='<|user|>'
            and ordered[special['eom']]=='<|observation|>'
            and ordered[154820]=='<|endoftext|>'
            and tokenizer_config['eos_token']=='<|endoftext|>'
            and tokenizer_config['pad_token']=='<|endoftext|>', 'TOKENIZER_SOURCE_INVALID')
    binding={'tokens':strings_wire_sha(ordered),'merges':strings_wire_sha(
        ' '.join(x.replace(' ',chr(288)) for x in p) for p in merges),
        'token_type':hashlib.sha256(b''.join(struct.pack('<i',x) for x in types)).hexdigest(),
        'special':special}
    require(Counter(types)=={1:154820,3:25,4:11,5:24}
        and expectation['status']=='METADATA_DERIVED_NOT_ENCODED_OR_NATIVE_VERIFIED'
        and binding['tokens']==expectation['tokens']['string_wire_sha256']
        and binding['token_type']==expectation['types']['i32_wire_sha256']
        and binding['merges']==expectation['merges']['string_wire_sha256']
        and special==expectation['special_token_ids'], 'TOKENIZER_EXPECTATION_MISMATCH')
    return binding


def expected_metadata(config, ftype):
    require_config(config)
    require(type(ftype) is int and ftype in FTYPES,'FILE_TYPE_UNSUPPORTED')
    return {'general.architecture':'deepseek2','general.type':'model',
        'general.file_type':ftype,'general.quantization_version':2,
        'deepseek2.block_count':48,'deepseek2.nextn_predict_layers':1,
        'deepseek2.context_length':202752,'deepseek2.embedding_length':2048,
        'deepseek2.feed_forward_length':10240,'deepseek2.vocab_size':154880,
        'deepseek2.attention.head_count':20,'deepseek2.attention.head_count_kv':1,
        'deepseek2.attention.q_lora_rank':768,'deepseek2.attention.kv_lora_rank':512,
        'deepseek2.attention.key_length':576,'deepseek2.attention.value_length':512,
        'deepseek2.attention.key_length_mla':256,'deepseek2.attention.value_length_mla':256,
        'deepseek2.attention.layer_norm_rms_epsilon':1e-5,
        'deepseek2.leading_dense_block_count':1,'deepseek2.expert_feed_forward_length':1536,
        'deepseek2.expert_count':64,'deepseek2.expert_used_count':4,
        'deepseek2.expert_shared_count':1,'deepseek2.expert_group_count':1,
        'deepseek2.expert_group_used_count':1,'deepseek2.expert_weights_scale':1.8,
        'deepseek2.expert_weights_norm':True,'deepseek2.rope.dimension_count':64,
        'deepseek2.rope.freq_base':1000000.0,'tokenizer.ggml.model':'gpt2',
        'tokenizer.ggml.pre':'glm4','tokenizer.ggml.bos_token_id':154822,
        'tokenizer.ggml.eos_token_id':154820,'tokenizer.ggml.padding_token_id':154820,
        'tokenizer.ggml.unknown_token_id':154820,'tokenizer.ggml.eot_token_id':154827,
        'tokenizer.ggml.eom_token_id':154829}


def check_metadata_value(meta, actual, expected):
    if type(expected) is float:
        return (meta.get('type')==6 and type(actual) is float
                and math.isclose(actual,expected,rel_tol=1e-6,abs_tol=0))
    typ={bool:7,int:4,str:8}[type(expected)]
    return meta.get('type')==typ and type(actual) is type(expected) and actual==expected


def validate_candidate(header, values, config, index, token_bind):
    ftype=values.get('general.file_type');expected=expected_metadata(config,ftype)
    optional={'deepseek2.rope.scaling.type':'none','deepseek2.expert_gating_func':2,
              'tokenizer.ggml.add_bos_token':False,'tokenizer.ggml.add_eos_token':False}
    for key,value in expected.items():
        require(key in header['metadata'] and key in values,'CONFIG_METADATA_MISSING')
        require(check_metadata_value(header['metadata'][key],values[key],value),'CONFIG_METADATA_MISMATCH')
    for key,value in optional.items():
        if key in header['metadata']:
            require(key in values and check_metadata_value(header['metadata'][key],values[key],value),
                    'OPTIONAL_METADATA_MISMATCH')
    require(not {k for k in header['metadata'] if k.startswith('deepseek2.')} - set(expected) - set(optional),
            'ARCHITECTURE_METADATA_UNEXPECTED')
    allowed_token_keys={'tokenizer.ggml.'+k for k in ('tokens','token_type','merges')}
    allowed_token_keys.update(k for k in set(expected)|set(optional) if k.startswith('tokenizer.ggml.'))
    require(not {k for k in header['metadata'] if k.startswith('tokenizer.ggml.')} - allowed_token_keys,
            'TOKENIZER_METADATA_UNEXPECTED')
    for key,subtype,count in [('tokens',8,154880),('token_type',5,154880),('merges',8,321649)]:
        meta=header['metadata'].get('tokenizer.ggml.'+key,{})
        require(meta.get('type')==9 and meta.get('element_type')==subtype and meta.get('count')==count,
                'TOKENIZER_ARRAY_MISMATCH')
        require(meta.get('elements_wire_sha256')==token_bind[key],'TOKENIZER_CONTENT_MISMATCH')
    template=header['metadata'].get('tokenizer.chat_template',{})
    require(template.get('type')==8 and template.get('bytes')==TEMPLATE_BYTES
            and template.get('sha256')==TEMPLATE_SHA,'EMBEDDED_TEMPLATE_MISMATCH')
    spec=tensor_spec(config,index,ftype)
    require(header['tensor_count']==len(spec)==868 and len(header['tensors'])==868
            and {t['name'] for t in header['tensors']}==set(spec),'EXPECTED_TENSOR_SET_MISMATCH')
    for row in header['tensors']:
        dims,types=spec[row['name']]
        require(row['shape']==dims and row['type_id'] in types
                and row['dtype']==TYPES[row['type_id']][0], 'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH')
    counts=dict(Counter(t['dtype'] for t in header['tensors']))
    require(header['dtype_counts']==counts and counts.get('f32')==290 and counts.get('q5_0')==48,
            'ROLE_DTYPE_DISTRIBUTION_MISMATCH')
    largest_dense=max(math.prod(t['shape'])*4 for t in header['tensors'] if len(t['shape'])==2)
    largest_all=max(math.prod(t['shape'])*4 for t in header['tensors'])
    require(largest_dense==1210*1024**2 and largest_all==largest_dense,'MAX_MATRIX_MISMATCH')
    return {'quantization':FTYPES[ftype],'general_file_type':ftype,
        'upstream_index_names_matched':9703,'expected_tensor_names_shapes_matched':868,
        'main_layer_count':47,'nextn_layer_count':1,'stored_layer_count':48,
        'generated_rope_tensor_count':0,'nextn_execution':'SKIPPED_BY_PINNED_NORMAL_LOADER',
        'mla_layout':'SPLIT_K_B_V_B_COMPRESSED_K_ONLY_CACHE',
        'main_kv_f16_context4096_seq1_mib':211.5,'stored_48_layer_kv_f16_mib':216,
        'defensive_expanded_48_layer_kv_f16_mib':3840,
        'untied_output':'Separate global token_embd/output required; nextn embed/head also inventoried',
        'largest_dense_matrix_f32_bytes':largest_dense,'largest_tensor_f32_bytes':largest_all,
        'role_type_policy':'Pinned default S/M policy: F32 norms/router/bias; Q5_0 split K_B only; Q4_K ordinary matrices; Q6_K global output; subtype/layer-specific ffn_down',
        'actual_role_dtype_counts':counts,
        'exact_per_tensor_quant_recipe':'UNPUBLISHED; checked against pinned default policy plus whole-file SHA',
        'embedded_template_sha256':TEMPLATE_SHA,'vocabulary_order_wire_sha256':token_bind['tokens'],
        'merges_order_wire_sha256':token_bind['merges'],'token_type_wire_sha256':token_bind['token_type'],
        'tokenizer_pretype':'glm4','tokenizer_source_normalizer':None,
        'tokenizer_content_parity':'Stored arrays only; added literal encode/decode, native IDs and raw roundtrip NOT_PROVED',
        'tensor_payload_numeric_validity':'NOT_DECODED_OR_TESTED'}


def load_reference():
    pins={}
    for name,digest in SOURCE_PINS.items():
        p=Path('var/runtime-src')/('llama.cpp-'+RUNTIME)/name
        read_bound(p,digest,1024**2);pins[p.as_posix()]=digest
    config=json.loads(read_bound(META/'config.json',CONFIG_SHA,65536))
    index=json.loads(read_bound(META/'model.safetensors.index.json',INDEX_SHA,1024**2))
    tok=json.loads(read_bound(META/'tokenizer.json',TOKENIZER_SHA,24*1024**2))
    tokconfig=json.loads(read_bound(META/'tokenizer_config.json',TOKENIZER_CONFIG_SHA,65536))
    read_bound(META/'chat_template.jinja',TEMPLATE_SHA,65536)
    expectation=json.loads(read_bound(VOCAB_EXPECTATION,VOCAB_EXPECTATION_SHA,65536))
    return config,index,tokenizer_bindings(tok,tokconfig,expectation),pins


def audit(relative, *, metadata_only=False):
    require(relative==MODEL_RELATIVE,'PINNED_MODEL_PATH_MISMATCH')
    config,index,token_bind,pins=load_reference()
    with safe_open(ROOT,relative) as stream:
        before=os.fstat(stream.fileno())
        require(before.st_size==FILE_BYTES,'PINNED_FILE_SIZE_MISMATCH')
        reader=Reader(stream,before.st_size);header,values=parse_header(reader)
        bindings,error=None,None
        try:
            bindings=validate_candidate(header,values,config,index,token_bind)
        except AuditError as exc:
            if not metadata_only: raise
            error=str(exc)
        header_read_bytes=reader.offset
        digest=None if metadata_only else finish_hash(reader,header)
        require(metadata_only or digest==FILE_SHA,'PINNED_FILE_HASH_MISMATCH')
        require(stat_key(before)==stat_key(os.fstat(stream.fileno())),'FILE_CHANGED_DURING_AUDIT')
    with safe_open(ROOT,relative) as stream:
        require(stat_key(before)==stat_key(os.fstat(stream.fileno())),'PATH_CHANGED_DURING_AUDIT')
    return {'kind':'GGUF_METADATA_DIAGNOSTIC' if metadata_only else 'GGUF_HEADER_AUDIT',
        'status':'DIAGNOSTIC_NOT_PASS' if metadata_only else 'PASS',
        'model_id':MODEL_ID,'revision':REVISION,'model_path':relative.as_posix(),
        'upstream_model_id':UPSTREAM_MODEL_ID,'upstream_revision':UPSTREAM_REVISION,
        'gguf_conversion_upstream_revision':'NOT_PUBLISHED','runtime_source_revision':RUNTIME,
        'file_bytes':before.st_size,'file_sha256':digest,'full_file_sha256_verified':not metadata_only,
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'read_mode':'BOUNDED_HEADER_ONLY' if metadata_only else 'SINGLE_OPEN_FD_HEADER_THEN_PAYLOAD_SHA256_STREAM',
        'bytes_read':header_read_bytes if metadata_only else before.st_size,
        'stat_unchanged':True,'header':header,'bindings':bindings,
        'candidate_validation_error':error,
        'architecture_metadata_values':{k:v for k,v in values.items() if k.startswith('deepseek2.')
            or k in ('general.architecture','general.file_type','tokenizer.ggml.pre')},
        'source_metadata_sha256':{'config':CONFIG_SHA,'template':TEMPLATE_SHA,'tokenizer':TOKENIZER_SHA,
            'tokenizer_config':TOKENIZER_CONFIG_SHA,'upstream_index':INDEX_SHA,
            'static_tokenizer_expectation':VOCAB_EXPECTATION_SHA},
        'runtime_source_files_sha256':pins,'copied_generic_parser_source_sha256':BASE_HELPER_SHA,
        'limits':{'header_bytes':HEADER_CAP,'single_string_bytes':STRING_CAP,
                  'array_elements':ARRAY_CAP,'metadata_entries':1024,'tensors':2048},
        'gpu_or_native_execution':False,
        'limitations':['Metadata-only diagnosis never verifies the payload or authorizes a launcher.',
            'Header/full SHA do not prove numeric tensor validity, native loading, grammar, quality, or VRAM.',
            'Source index metadata.total_size disagrees with shard API sizes; names only are used.',
            'GGUF conversion source revision/command and per-tensor quantization recipe are unpublished.',
            'Checks require the pinned converter default full-MTP/split-MLA layout and default S/M quantizer rules.',
            'Static tokenizer arrays do not prove runtime token IDs or arbitrary Unicode roundtrip.',
            'All 48 stored layers including MTP are inventoried; normal loader skips MTP execution.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True,type=Path)
    parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--metadata-only',action='store_true')
    args=parser.parse_args()
    try:
        require(args.model==MODEL_RELATIVE,'PINNED_MODEL_PATH_MISMATCH')
        require(args.report.parts[:2]==('var','reports'),'REPORT_PATH_INVALID')
        result=audit(args.model,metadata_only=args.metadata_only)
        result['helper_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        payload=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
        with safe_open(ROOT,args.report,write=True) as stream: stream.write(payload)
        print(json.dumps({'kind':result['kind'],'status':result['status'],
            'report':args.report.as_posix(),'report_sha256':hashlib.sha256(payload).hexdigest(),
            'tensor_count':result['header']['tensor_count'],
            'quantization':(result['bindings'] or {}).get('quantization'),
            'candidate_validation_error':result['candidate_validation_error']}))
    except (AuditError,OSError,ValueError,KeyError,TypeError,struct.error) as exc:
        code=str(exc) if isinstance(exc,AuditError) else 'AUDIT_INPUT_OR_IO_INVALID'
        print(json.dumps({'kind':'GGUF_METADATA_DIAGNOSTIC' if args.metadata_only else 'GGUF_HEADER_AUDIT',
                          'status':'FAIL','code':code}))
        return 1
    return 0


if __name__=='__main__':
    sys.exit(main())
