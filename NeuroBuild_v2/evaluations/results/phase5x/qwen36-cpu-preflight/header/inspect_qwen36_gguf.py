#!/usr/bin/env python3
"""Pinned GGUF v3 audit. Stdlib only; no native/backend/model execution.

Use only AFTER the parent authorizes/full-downloads the one pinned Qwen3.6 Q4_K_M file.
One open fd: parse/hash header, stream/hash remaining bytes once, compare fstat.
Tensor payload is hashed, not decoded. This does not prove numerical finiteness,
native loading, tokenizer parity, VRAM peak, or semantic model quality.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import sys
from datetime import datetime, timezone

ROOT = Path('/home/a202192020/NeuroBuild_v2')
META = Path('var/research/qwen36-candidate-metadata')
MODEL_ID = 'ggml-org/Qwen3.6-35B-A3B-GGUF'
FILE_NAME = 'Qwen3.6-35B-A3B-Q4_K_M.gguf'
REVISION = 'baec3ebee244827cda0f4557eafa8b28f7545fa6'
UPSTREAM = '995ad96eacd98c81ed38be0c5b274b04031597b0'
RUNTIME = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
FILE_BYTES = 20_419_565_568
FILE_SHA = '671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7'
TEMPLATE_SHA = 'e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259'
INVENTORY_SHA = '3ff6982c5e43040975a7daea3cefe8e0e9709a82df16b5651ad819f81608c196'
CONFIG_SHA = '93a4693fa9d8392fbfccd4b3c9873f4bfdcb14fdede978b123d07d19675efe99'
LOG_SHA = '8dc2a7f833e7421fa1bae8e206930bf4ab3dda9d1f705ed4b7294abc98c5db22'
TOKENIZER_SHA = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
TOKENIZER_CONFIG_SHA = '5186f0defcd7f232382c7f0aebcd2252d073bb921ab240e407b7ae8745d2b29b'
# Pinned ggml/include/ggml.h enum + ggml/src/ggml-common.h block definitions.
TYPES = {0: ('f32', 1, 4), 8: ('q8_0', 32, 34),
         12: ('q4_K', 256, 144), 14: ('q6_K', 256, 210)}
SCALARS = {0:'B', 1:'b', 2:'H', 3:'h', 4:'I', 5:'i',
           6:'f', 7:'B', 10:'Q', 11:'q', 12:'d'}
HEADER_CAP = 32 * 1024**2
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


def validate_candidate(header, values, config, inventory):
    """Exact published final quantization rows, not the override command's intent."""
    tc = config['text_config']
    require(config['architectures'] == ['Qwen3_5MoeForConditionalGeneration']
            and tc['num_hidden_layers'] == 40 and tc['vocab_size'] == 248320
            and tc['tie_word_embeddings'] is False, 'OFFICIAL_CONFIG_IDENTITY_MISMATCH')
    arch = 'qwen35moe'
    expected = {
        'general.architecture':arch, 'general.type':'model',
        'general.file_type':15, 'general.quantization_version':2,
        f'{arch}.block_count':tc['num_hidden_layers'],
        f'{arch}.context_length':tc['max_position_embeddings'],
        f'{arch}.embedding_length':tc['hidden_size'],
        f'{arch}.expert_count':tc['num_experts'],
        f'{arch}.expert_used_count':tc['num_experts_per_tok'],
        f'{arch}.expert_feed_forward_length':tc['moe_intermediate_size'],
        f'{arch}.expert_shared_feed_forward_length':tc['shared_expert_intermediate_size'],
        f'{arch}.attention.head_count':tc['num_attention_heads'],
        f'{arch}.attention.head_count_kv':tc['num_key_value_heads'],
        f'{arch}.attention.key_length':tc['head_dim'],
        f'{arch}.attention.value_length':tc['head_dim'],
        f'{arch}.ssm.conv_kernel':tc['linear_conv_kernel_dim'],
        f'{arch}.ssm.state_size':tc['linear_key_head_dim'],
        f'{arch}.ssm.group_count':tc['linear_num_key_heads'],
        f'{arch}.ssm.time_step_rank':tc['linear_num_value_heads'],
        f'{arch}.ssm.inner_size':tc['linear_value_head_dim']*tc['linear_num_value_heads'],
        f'{arch}.full_attention_interval':tc['full_attention_interval'],
        f'{arch}.rope.dimension_count':int(tc['head_dim']*tc['partial_rotary_factor']),
        f'{arch}.rope.dimension_sections':tc['rope_parameters']['mrope_section']+[0],
        f'{arch}.rope.freq_base':tc['rope_parameters']['rope_theta'],
        f'{arch}.attention.layer_norm_rms_epsilon':tc['rms_norm_eps'],
        'tokenizer.ggml.model':'gpt2', 'tokenizer.ggml.pre':'qwen35',
        'tokenizer.ggml.bos_token_id':248044, 'tokenizer.ggml.eos_token_id':248046,
        'tokenizer.ggml.padding_token_id':248044, 'tokenizer.ggml.add_bos_token':False,
    }
    floats = {f'{arch}.rope.freq_base',f'{arch}.attention.layer_norm_rms_epsilon'}
    for key, wanted in expected.items():
        actual = values.get(key)
        matches = (type(actual) is float and math.isclose(actual,wanted,rel_tol=1e-6,abs_tol=0)
                   if key in floats else type(actual) is type(wanted) and actual == wanted)
        require(key in values and matches, 'CONFIG_METADATA_MISMATCH')
        meta = header['metadata'][key]
        if key in floats:
            require(meta['type'] == 6, 'CONFIG_FLOAT_TYPE_MISMATCH')
        elif type(wanted) is int:
            require(meta['type'] == 4, 'CONFIG_METADATA_TYPE_MISMATCH')
        elif type(wanted) is bool:
            require(meta['type'] == 7, 'CONFIG_METADATA_TYPE_MISMATCH')
        elif type(wanted) is str:
            require(meta['type'] == 8, 'CONFIG_METADATA_TYPE_MISMATCH')
    # Published primary has no MTP. Pinned loader defaults missing nextn to zero.
    nextn = f'{arch}.nextn_predict_layers'
    require(nextn not in values or (type(values[nextn]) is int and values[nextn] == 0
            and header['metadata'][nextn]['type'] == 4), 'UNEXPECTED_MTP_LAYERS')
    # Published input metadata omits recurrent_layers. f072 qwen35moe.cpp:19-27
    # derives it from interval=4. An explicit array must equal that exact config.
    recurrent = f'{arch}.attention.recurrent_layers'
    recurrent_expected = [x == 'linear_attention' for x in tc['layer_types']]
    require(recurrent_expected == [(i+1)%4 != 0 for i in range(40)], 'RECURRENT_CONFIG_MISMATCH')
    if recurrent in values:
        m = header['metadata'][recurrent]
        require(m.get('type') == 9 and m.get('element_type') == 7 and m.get('count') == 40
                and values[recurrent] == recurrent_expected, 'RECURRENT_METADATA_MISMATCH')
    for key, subtype, count in [(f'{arch}.rope.dimension_sections',5,4),
                              ('tokenizer.ggml.tokens',8,248320),
                              ('tokenizer.ggml.token_type',5,248320),
                              ('tokenizer.ggml.merges',8,247587)]:
        m = header['metadata'].get(key,{})
        require(m.get('type') == 9 and m.get('element_type') == subtype and m.get('count') == count,
                'ARRAY_METADATA_MISMATCH')
    template = header['metadata'].get('tokenizer.chat_template',{})
    require(template.get('type') == 8 and template.get('bytes') == 7764
            and template.get('sha256') == TEMPLATE_SHA, 'EMBEDDED_TEMPLATE_MISMATCH')
    require(inventory['kind'] == 'QWEN36_PUBLIC_CONVERSION_LOG_TENSOR_INVENTORY'
            and inventory['status'] == 'EXPECTED_FROM_PUBLISHED_LOG_NOT_ACTUAL_GGUF'
            and inventory['source_sha256'] == LOG_SHA, 'INVENTORY_SOURCE_MISMATCH')
    rows = inventory['tensor_rows']
    expected_map = {x['name']:(x['shape'],x['destination_dtype']) for x in rows}
    require(len(expected_map) == len(rows) == header['tensor_count'] == inventory['tensor_count'] == 733,
            'EXPECTED_TENSOR_COUNT_MISMATCH')
    require({t['name'] for t in header['tensors']} == set(expected_map), 'EXPECTED_TENSOR_SET_MISMATCH')
    for tensor in header['tensors']:
        dims,dtype = expected_map[tensor['name']]
        require(tensor['shape_padded'] == dims and tensor['dtype'] == dtype,
                'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH')
    require(header['dtype_counts'] == {'q6_K':1,'f32':301,'q4_K':121,'q8_0':310},
            'DTYPE_COUNT_MISMATCH')
    require(header['tensor_payload_bytes'] == 20_408_576_512, 'TENSOR_PAYLOAD_SIZE_MISMATCH')
    return {'config_values_bound':len(expected),'conversion_log_tensors_matched':733,
            'quantization':'Q4_K_M','mtp_layers':0,'recurrent_layers':30,'full_attention_layers':10,
            'recurrent_metadata_mode':'EXPLICIT_MATCH' if recurrent in values else 'PINNED_LOADER_INTERVAL_FALLBACK',
            'tokenizer_counts_bound':True,'embedded_template_sha256':TEMPLATE_SHA,
            'tokenizer_content_parity':'PENDING_SAVED_TYPED_METADATA_COMPARISON',
            'tokenizer_added_tokens_json26_config33':'ACTUAL_ARRAY_DIGESTS_RECORDED_NOT_RESOLVED_BY_COUNTS',
            'tensor_payload_numeric_validity':'NOT_DECODED_OR_TESTED'}


def audit(relative: Path):
    require(relative == Path('var/models')/'ggml-org--Qwen3.6-35B-A3B-GGUF'/REVISION/FILE_NAME,
            'PINNED_MODEL_PATH_MISMATCH')
    config = json.loads(read_bound(META/'upstream/config.json',CONFIG_SHA,64*1024))
    inventory = json.loads(read_bound(META/'conversion_tensor_inventory.json',INVENTORY_SHA,1024**2))
    read_bound(META/'gguf/convert.log',LOG_SHA,1024**2)
    read_bound(META/'upstream/chat_template.jinja',TEMPLATE_SHA,64*1024)
    read_bound(META/'upstream/tokenizer.json',TOKENIZER_SHA,16*1024**2)
    read_bound(META/'upstream/tokenizer_config.json',TOKENIZER_CONFIG_SHA,64*1024)
    with safe_open(ROOT,relative) as f:
        before = os.fstat(f.fileno())
        require(before.st_size == FILE_BYTES,'PINNED_FILE_SIZE_MISMATCH')
        reader = Reader(f,before.st_size)
        header,values = parse_header(reader)
        bindings = validate_candidate(header,values,config,inventory)
        digest = finish_hash(reader,header)
        require(digest == FILE_SHA,'PINNED_FILE_HASH_MISMATCH')
        require(stat_key(before) == stat_key(os.fstat(f.fileno())),'FILE_CHANGED_DURING_AUDIT')
    with safe_open(ROOT,relative) as f:
        require(stat_key(before) == stat_key(os.fstat(f.fileno())),'PATH_CHANGED_DURING_AUDIT')
    return {'kind':'GGUF_HEADER_AUDIT','status':'PASS','model_path':relative.as_posix(),
            'model_id':MODEL_ID,'revision':REVISION,'upstream_revision':UPSTREAM,
            'runtime_source_revision':RUNTIME,'file_sha256':digest,'file_bytes':before.st_size,
            'full_file_sha256_verified':True,'created_utc':datetime.now(timezone.utc).isoformat(),
            'read_mode':'SINGLE_OPEN_FD_HEADER_THEN_PAYLOAD_SHA256_STREAM','stat_unchanged':True,
            'header':header,'bindings':bindings,
            'source_metadata_sha256':{'config':CONFIG_SHA,'template':TEMPLATE_SHA,
                'tokenizer':TOKENIZER_SHA,'tokenizer_config':TOKENIZER_CONFIG_SHA,
                'conversion_log':LOG_SHA,'tensor_inventory':INVENTORY_SHA},
            'gpu_or_native_execution':False,
            'limits':{'header_bytes':HEADER_CAP,'single_string_bytes':STRING_CAP,
                      'array_elements':ARRAY_CAP,'metadata_entries':1024,'tensors':2048},
            'limitations':['Header/payload audit only; no native load, tokenizer equivalence, runtime or quality PASS.',
                'Full SHA binds payload bytes; quantized numbers were not decoded.',
                'Published converter b15ca93/GNU14.2 is not the pinned f072 runtime build.',
                'Official config MTP1 is absent from this exact published primary733 inventory.',
                'Added token content/type parity and raw/NFC variant choice require separate saved evidence.',
                'Production client/evaluator hashes are intentionally not pinned before root finalizes the new profile.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True,type=Path)
    parser.add_argument('--report',required=True,type=Path)
    args=parser.parse_args()
    try:
        require(args.report.parts[:2] == ('var','reports') and args.report.suffix == '.json',
                'REPORT_PATH_INVALID')
        result=audit(args.model)
        result['helper_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        payload=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
        with safe_open(ROOT,args.report,write=True) as f:f.write(payload)
        print(json.dumps({'kind':result['kind'],'status':'PASS','report':args.report.as_posix(),
                          'report_sha256':hashlib.sha256(payload).hexdigest(),
                          'file_sha256':FILE_SHA,'tensor_count':733}))
        return 0
    except (AuditError,OSError,ValueError,KeyError,TypeError,struct.error) as exc:
        code=str(exc) if isinstance(exc,AuditError) else 'AUDIT_INPUT_OR_IO_INVALID'
        print(json.dumps({'kind':'GGUF_HEADER_AUDIT','status':'FAIL','code':code}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
