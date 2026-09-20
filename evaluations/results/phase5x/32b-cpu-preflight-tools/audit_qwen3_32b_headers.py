"""Pinned Qwen3-32B AWQ CPU-only structure audit; never reads tensor payloads."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import stat
import struct
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
REVISION = "0499c3ac83fdef8810b907a23894ba91e95eddd8"
RESEARCH = ROOT / "var/research/qwen3-32b-awq-feasibility" / REVISION
MODEL = ROOT / "var/models/Qwen--Qwen3-32B-AWQ" / REVISION
MANIFEST = RESEARCH / "qwen3-32b-awq.json"
MAX_HEADER = 16 * 1024 * 1024
DTYPE_BYTES = {"BF16": 2, "I32": 4}


def pairs(values):
    result = {}
    for key, value in values:
        assert key not in result, "duplicate JSON key"
        result[key] = value
    return result


def parse(data):
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def small_file(path, record):
    assert not path.is_symlink() and path.is_file(), path.name
    assert record["bytes"] <= MAX_HEADER
    data = path.read_bytes()
    assert len(data) == record["bytes"] and sha256(data).hexdigest() == record["sha256"], path.name
    return parse(data)


def expected_tensors(config):
    assert config["architectures"] == ["Qwen3ForCausalLM"]
    assert config["model_type"] == "qwen3" and config["torch_dtype"] == "float16"
    assert config["attention_bias"] is False and config["tie_word_embeddings"] is False
    q = config["quantization_config"]
    assert q == {"bits": 4, "group_size": 128, "modules_to_not_convert": None,
                 "quant_method": "awq", "version": "gemm", "zero_point": True}
    h, m, d = config["hidden_size"], config["intermediate_size"], config["head_dim"]
    n, k, layers, vocab = (config[key] for key in ("num_attention_heads", "num_key_value_heads", "num_hidden_layers", "vocab_size"))
    assert (h, m, d, n, k, layers, vocab) == (5120, 25600, 128, 64, 8, 64, 151936)
    result = {"model.embed_tokens.weight": ([vocab, h], "BF16"),
              "lm_head.weight": ([vocab, h], "BF16"), "model.norm.weight": ([h], "BF16")}
    projections = {"self_attn.q_proj": (h, n * d), "self_attn.k_proj": (h, k * d),
                   "self_attn.v_proj": (h, k * d), "self_attn.o_proj": (n * d, h),
                   "mlp.gate_proj": (h, m), "mlp.up_proj": (h, m), "mlp.down_proj": (m, h)}
    for layer in range(layers):
        prefix = f"model.layers.{layer}."
        for name, width in (("input_layernorm", h), ("post_attention_layernorm", h),
                            ("self_attn.q_norm", d), ("self_attn.k_norm", d)):
            result[prefix + name + ".weight"] = ([width], "BF16")
        for name, (inputs, outputs) in projections.items():
            assert inputs % 128 == 0 and outputs % 8 == 0
            result[prefix + name + ".qweight"] = ([inputs, outputs // 8], "I32")
            result[prefix + name + ".qzeros"] = ([inputs // 128, outputs // 8], "I32")
            result[prefix + name + ".scales"] = ([inputs // 128, outputs], "BF16")
    assert len(result) == 1603
    return result


def inspect_shard(path, record, expected, assignment):
    assert path.name.endswith(".safetensors") and not path.name.endswith(".part")
    assert not path.is_symlink() and path.parent == MODEL
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
        assert before.st_size == record["bytes"], path.name
        with os.fdopen(fd, "rb", closefd=False) as stream:
            prefix = stream.read(8)
            assert len(prefix) == 8
            length = struct.unpack("<Q", prefix)[0]
            assert 0 < length <= MAX_HEADER and length + 8 < before.st_size
            header_bytes = stream.read(length)
            assert len(header_bytes) == length
        header = parse(header_bytes)
        assert type(header) is dict
        metadata = header.pop("__metadata__", {})
        assert type(metadata) is dict and all(type(k) is str and type(v) is str for k, v in metadata.items())
        payload_bytes = before.st_size - 8 - length
        intervals = []
        for name, entry in header.items():
            assert name in expected and assignment[name] == path.name, name
            assert type(entry) is dict and set(entry) == {"dtype", "shape", "data_offsets"}
            shape, dtype = expected[name]
            assert entry["dtype"] == dtype and entry["shape"] == shape, name
            assert all(type(v) is int and v > 0 for v in entry["shape"]), name
            offsets = entry["data_offsets"]
            assert type(offsets) is list and len(offsets) == 2 and all(type(v) is int for v in offsets)
            begin, end = offsets
            assert 0 <= begin < end <= payload_bytes, name
            assert end - begin == math.prod(shape) * DTYPE_BYTES[dtype], name
            intervals.append((begin, end, name))
        position = 0
        for begin, end, name in sorted(intervals):
            assert begin == position, "overlap or uncovered tensor-data bytes: " + name
            position = end
        assert position == payload_bytes
        after = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
        assert identity(before) == identity(after)
        result = {"tensor_count": len(header), "file_bytes": before.st_size,
                  "header_bytes": length, "header_sha256": sha256(header_bytes).hexdigest(),
                  "tensor_data_bytes": payload_bytes, "stat_identity": identity(after),
                  "shape_dtype_shard_offsets_coverage": "PASS"}
        return set(header), result
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    manifest = parse(MANIFEST.read_bytes())
    assert manifest["model_id"] == "Qwen/Qwen3-32B-AWQ" and manifest["revision"] == REVISION
    records = {entry["name"]: entry for entry in manifest["files"]}
    source = RESEARCH if args.metadata_only else MODEL
    config = small_file(source / "config.json", records["config.json"])
    index = small_file(source / "model.safetensors.index.json", records["model.safetensors.index.json"])
    expected = expected_tensors(config)
    assignment = index["weight_map"]
    assert set(expected) == set(assignment), "config/index tensor keys differ"
    total_data = sum(math.prod(shape) * DTYPE_BYTES[dtype] for shape, dtype in expected.values())
    # The pinned publisher index scalar is inconsistent even with aggregate
    # complete-file lengths. Keep its exact value as a disclosed warning, not
    # an authority overriding config-derived sizes and real header coverage.
    assert index["metadata"]["total_size"] == 19338405888
    assert total_data == 19325298688
    shards = sorted(set(assignment.values()))
    assert len(shards) == 4 and set(shards) == {name for name in records if name.endswith(".safetensors")}
    proof = {"kind": "CPU_HEADER_ONLY_NOT_WEIGHT_HASH_OR_KERNEL_VERIFICATION",
             "status": "METADATA_ONLY_PASS_WITH_STORAGE_DTYPE_AND_INDEX_SIZE_WARNINGS" if args.metadata_only else "PASS_WITH_STORAGE_DTYPE_AND_INDEX_SIZE_WARNINGS",
             "utc": datetime.now(timezone.utc).isoformat(), "model_id": manifest["model_id"], "revision": REVISION,
             "manifest_sha256": sha256(MANIFEST.read_bytes()).hexdigest(),
             "config_sha256": records["config.json"]["sha256"], "index_sha256": records["model.safetensors.index.json"]["sha256"],
             "expected_tensor_count": len(expected), "index_tensor_count": len(assignment),
             "expected_tensor_data_bytes": total_data,
             "config_runtime_dtype": "float16", "observed_storage_float_dtype": "BF16",
             "cast_value_validation": "Separate CPU dtype-cast proof required; header audit cannot establish numeric convertibility.",
             "index_claimed_tensor_data_bytes": index["metadata"]["total_size"],
             "index_size_discrepancy_bytes": index["metadata"]["total_size"] - total_data,
             "warnings": ["Initial float16 storage assumption failed: actual707 noninteger tensors use BF16 while config torch_dtype=float16. Loader and numeric cast validation are separate.", "Pinned index metadata.total_size differs from config-derived and manifest file sizes; exact cause unproved. Actual per-tensor sizes, shard mapping and byte coverage are mandatory."],
             "dtype_counts": dict(Counter(dtype for _, dtype in expected.values())),
             "tensor_payload_read": False, "torch_imported": "torch" in sys.modules,
             "network_calls": 0, "model_calls": 0, "gpu_calls": 0,
             "scope": "Config/index/actual headers do not verify numerical weights, full weight SHA, model quality, or CUDA kernels."}
    if args.metadata_only:
        print(json.dumps(proof))
        return
    missing = [name for name in shards if not (MODEL / name).is_file()]
    if missing:
        print(json.dumps({"status": "WAITING_FOR_COMPLETED_SHARDS", "missing": missing}))
        return
    assert (MODEL / "neurobuild-manifest.json").read_bytes() == MANIFEST.read_bytes()
    seen = set()
    results = {}
    for name in shards:
        names, result = inspect_shard(MODEL / name, records[name], expected, assignment)
        assert not seen.intersection(names), "duplicate tensor across shards"
        seen.update(names)
        results[name] = result
    assert seen == set(expected) == set(assignment)
    assert sum(item["tensor_data_bytes"] for item in results.values()) == total_data
    proof.update(actual_tensor_count=len(seen), shards=results,
                 observed_tensor_data_bytes=total_data,
                 total_header_bytes_read=sum(item["header_bytes"] + 8 for item in results.values()))
    out = ROOT / "var/reports" / ("qwen3_32b_header_audit_" + uuid4().hex + ".json")
    with out.open("x") as stream:
        json.dump(proof, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": proof["status"], "proof_path": str(out.relative_to(ROOT)),
                      "proof_sha256": sha256(out.read_bytes()).hexdigest(), "actual_tensors": len(seen),
                      "tensor_data_bytes": total_data, "headers_only_bytes_read": proof["total_header_bytes_read"]}))


if __name__ == "__main__":
    main()
