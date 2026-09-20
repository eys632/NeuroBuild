#!/usr/bin/env python3
"""Pinned GGUF v3 audit. Stdlib only; no native/backend/model execution.

Use only AFTER the parent authorizes/full-downloads the one pinned Q4_K_M file.
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
META = Path('var/research/qwen38-candidate-metadata')
REVISION = 'efbb3b1f70a21d97fd4495240648405f7228554f'
UPSTREAM = '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'
RUNTIME = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
FILE_BYTES = 18_973_870_528
FILE_SHA = 'c600de0300ae8a0eb3a6c0b8b5561b8b96f16bd2c863c2a66c42de29d391a747'
TEMPLATE_SHA = 'c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041'
PROVENANCE_SHA = '3cf9d3ceab25e02b24373f0c7e0929b1e7fcea7eb2f511be9280bfbdb506a4bd'
CONFIG_SHA = '191e0af232104ed8b65258cf3fb2b842e288008baca7633c11b82a1ac7203aab'
LOG_SHA = '32e08befefcb1ad819a4fae187412f26973acc8f7c657bc3fd404e18980994f7'
TOKENIZER_SHA = '0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'
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


def validate_candidate(header, values, config, provenance):
    tc = config['text_config']
    expected = {
        'general.architecture':'qwen35', 'general.type':'model',
        'general.file_type':15, 'general.quantization_version':2,
        'qwen35.block_count':tc['num_hidden_layers'],
        'qwen35.context_length':tc['max_position_embeddings'],
        'qwen35.embedding_length':tc['hidden_size'],
        'qwen35.feed_forward_length':tc['intermediate_size'],
        'qwen35.attention.head_count':tc['num_attention_heads'],
        'qwen35.attention.head_count_kv':tc['num_key_value_heads'],
        'qwen35.attention.key_length':tc['head_dim'],
        'qwen35.attention.value_length':tc['head_dim'],
        'qwen35.ssm.conv_kernel':tc['linear_conv_kernel_dim'],
        'qwen35.ssm.state_size':tc['linear_key_head_dim'],
        'qwen35.ssm.group_count':tc['linear_num_key_heads'],
        'qwen35.ssm.time_step_rank':tc['linear_num_value_heads'],
        'qwen35.ssm.inner_size':tc['linear_value_head_dim']*tc['linear_num_value_heads'],
        'qwen35.full_attention_interval':tc['full_attention_interval'],
        'qwen35.attention.recurrent_layers':[x=='linear_attention' for x in tc['layer_types']],
        'qwen35.rope.dimension_count':int(tc['head_dim']*tc['partial_rotary_factor']),
        'qwen35.rope.dimension_sections':tc['rope_parameters']['mrope_section']+[0],
        'qwen35.rope.freq_base':tc['rope_parameters']['rope_theta'],
        'qwen35.attention.layer_norm_rms_epsilon':tc['rms_norm_eps'],
        'tokenizer.ggml.model':'gpt2', 'tokenizer.ggml.pre':'qwen35',
        'tokenizer.ggml.bos_token_id':248044, 'tokenizer.ggml.eos_token_id':248046,
        'tokenizer.ggml.padding_token_id':248044, 'tokenizer.ggml.add_bos_token':False,
    }
    for k, v in expected.items():
        actual = values.get(k)
        matches = (type(actual) is float and math.isclose(actual,v,rel_tol=1e-6,abs_tol=0)
                   if type(v) is float else actual == v)
        require(k in values and matches, 'CONFIG_METADATA_MISMATCH')
        if type(v) is int and not k.startswith('qwen35.rope.freq_base'):
            require(header['metadata'][k]['type'] == 4, 'CONFIG_METADATA_TYPE_MISMATCH')
    require(header['metadata']['tokenizer.ggml.add_bos_token']['type'] == 7,
            'TOKENIZER_BOOL_TYPE_MISMATCH')
    for k, subtype, count in [('qwen35.attention.recurrent_layers',7,64),
                               ('qwen35.rope.dimension_sections',5,4)]:
        meta = header['metadata'].get(k,{})
        require(meta.get('type') == 9 and meta.get('element_type') == subtype and
                meta.get('count') == count, 'CONFIG_ARRAY_TYPE_MISMATCH')
    for k in ('qwen35.rope.freq_base','qwen35.attention.layer_norm_rms_epsilon'):
        require(header['metadata'][k]['type'] == 6, 'CONFIG_FLOAT_TYPE_MISMATCH')
    for k, subtype, count in [('tokenizer.ggml.tokens',8,248320),
                               ('tokenizer.ggml.token_type',5,248320),
                               ('tokenizer.ggml.merges',8,247587)]:
        m = header['metadata'].get(k, {})
        require(m.get('type') == 9 and m.get('element_type') == subtype and m.get('count') == count,
                'TOKENIZER_METADATA_MISMATCH')
    template = header['metadata'].get('tokenizer.chat_template', {})
    require(template.get('type') == 8 and template.get('bytes') == 8952 and
            template.get('sha256') == TEMPLATE_SHA, 'EMBEDDED_TEMPLATE_MISMATCH')
    expected_rows = provenance['logged_output_tensor_rows']
    expected_map = {x['name']:(list(map(int,x['shape_text'].split(','))),x['destination_dtype'])
                    for x in expected_rows}
    require(len(expected_map) == len(expected_rows) == header['tensor_count'] == 851,
            'EXPECTED_TENSOR_COUNT_MISMATCH')
    require({t['name'] for t in header['tensors']} == set(expected_map), 'EXPECTED_TENSOR_SET_MISMATCH')
    for t in header['tensors']:
        dims, dtype = expected_map[t['name']]
        require(t['shape_padded'] == dims and t['dtype'] == dtype, 'EXPECTED_TENSOR_SHAPE_TYPE_MISMATCH')
    require(header['dtype_counts'] == {'q6_K':17,'f32':353,'q4_K':193,'q8_0':288},
            'DTYPE_COUNT_MISMATCH')
    require(header['tensor_payload_bytes'] == 18_962_876_416, 'TENSOR_PAYLOAD_SIZE_MISMATCH')
    return {'config_values_bound':len(expected), 'conversion_log_tensors_matched':851,
            'tokenizer_counts_bound':True, 'embedded_template_sha256':TEMPLATE_SHA,
            'tokenizer_content_parity':'NOT_PROVED_BY_HEADER_COUNTS',
            'tensor_payload_numeric_validity':'NOT_DECODED_OR_TESTED'}


def audit(relative: Path):
    config = json.loads(read_bound(META/'upstream/config.json', CONFIG_SHA, 64*1024))
    provenance = json.loads(read_bound(META/'template_and_conversion_provenance.json', PROVENANCE_SHA, 1024**2))
    read_bound(META/'gguf/convert.log', LOG_SHA, 1024**2)
    read_bound(META/'upstream/chat_template.jinja', TEMPLATE_SHA, 64*1024)
    # Public tokenizer identity is frozen; no printing its strings or native loading.
    read_bound(META/'upstream/tokenizer.json', TOKENIZER_SHA, 16*1024**2)
    with safe_open(ROOT, relative) as f:
        before = os.fstat(f.fileno())
        require(before.st_size == FILE_BYTES, 'PINNED_FILE_SIZE_MISMATCH')
        reader = Reader(f, before.st_size)
        header, values = parse_header(reader)
        bindings = validate_candidate(header, values, config, provenance)
        digest = finish_hash(reader, header)
        require(digest == FILE_SHA, 'PINNED_FILE_HASH_MISMATCH')
        require(stat_key(before) == stat_key(os.fstat(f.fileno())), 'FILE_CHANGED_DURING_AUDIT')
    # Reopening via no-follow chain confirms the path still names the same regular inode.
    with safe_open(ROOT, relative) as f:
        require(stat_key(before) == stat_key(os.fstat(f.fileno())), 'PATH_CHANGED_DURING_AUDIT')
    return {'kind':'GGUF_HEADER_AUDIT','status':'PASS',
            'model_path':relative.as_posix(),'model_id':'ggml-org/Qwen3.8-27B-GGUF',
            'revision':REVISION,'upstream_revision':UPSTREAM,'runtime_source_revision':RUNTIME,
            'file_sha256':digest,'file_bytes':before.st_size,
            'created_utc':datetime.now(timezone.utc).isoformat(),
            'read_mode':'SINGLE_OPEN_FD_HEADER_THEN_PAYLOAD_SHA256_STREAM',
            'stat_unchanged':True,'header':header,'bindings':bindings,
            'source_metadata_sha256':{'config':CONFIG_SHA,'template':TEMPLATE_SHA,
                'tokenizer':TOKENIZER_SHA,'conversion_log':LOG_SHA,'tensor_provenance':PROVENANCE_SHA},
            'limits':{'header_bytes':HEADER_CAP,'single_string_bytes':STRING_CAP,
                      'array_elements':ARRAY_CAP,'metadata_entries':1024,'tensors':2048},
            'gpu_or_native_execution':False,
            'limitations':['No model inference/native load/VRAM or quality verification.',
              'Full SHA binds payload bytes; quantized numbers were not decoded.',
              'Own immutable artifact assumption after audit; a later opener must bind the same digest/stat.',
              'Public converter log describes a different converter commit than the pinned runtime.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, type=Path, help='Existing project-relative pinned GGUF')
    parser.add_argument('--report', required=True, type=Path, help='NEW project-relative report; parent must exist')
    args = parser.parse_args()
    try:
        require(args.model.name == 'Qwen3.8-27B-Q4_K_M.gguf', 'PINNED_FILENAME_MISMATCH')
        result = audit(args.model)
        result['helper_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        payload = (json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
        with safe_open(ROOT,args.report,write=True) as f:
            f.write(payload)
        print(json.dumps({'kind':result['kind'],'status':'PASS','report':args.report.as_posix(),
                          'report_sha256':hashlib.sha256(payload).hexdigest(),
                          'file_sha256':FILE_SHA,'tensor_count':851}))
    except (AuditError,OSError,ValueError,KeyError,TypeError,struct.error) as exc:
        code = str(exc) if isinstance(exc,AuditError) else 'AUDIT_INPUT_OR_IO_INVALID'
        print(json.dumps({'kind':'GGUF_HEADER_AUDIT','status':'FAIL','code':code}))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
