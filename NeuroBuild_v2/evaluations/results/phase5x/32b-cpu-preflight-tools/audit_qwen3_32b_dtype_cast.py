"""CPU bounded BF16 payload scan and FP16 copy; skips all quantized I32 data."""

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
import time
from uuid import uuid4

assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
assert os.environ.get("HF_HUB_OFFLINE") == "1"
assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"
assert os.environ.get("OMP_NUM_THREADS") == "2"
import torch

torch.set_num_threads(2)
torch.set_num_interop_threads(1)
assert not torch.cuda.is_initialized()
ROOT = Path(__file__).resolve().parents[2]
REVISION = "0499c3ac83fdef8810b907a23894ba91e95eddd8"
MODEL = ROOT / "var/models/Qwen--Qwen3-32B-AWQ" / REVISION
MANIFEST = MODEL / "neurobuild-manifest.json"
CHUNK_BYTES = 8 * 1024 * 1024
manifest = json.loads(MANIFEST.read_text())
assert manifest["revision"] == REVISION
started = time.monotonic()
totals = Counter()
tensor_results = []
global_max = 0.0
for record in manifest["files"]:
    if not record["name"].endswith(".safetensors"):
        continue
    path = MODEL / record["name"]
    assert not path.is_symlink() and path.stat().st_size == record["bytes"]
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        n = struct.unpack("<Q", stream.read(8))[0]
        assert 0 < n < 16 * 1024 * 1024
        header = json.loads(stream.read(n))
        tensors = [(name, value) for name, value in header.items() if name != "__metadata__"]
        for name, value in sorted(tensors, key=lambda pair: pair[1]["data_offsets"]):
            if value["dtype"] == "I32":
                totals["i32_tensors_skipped"] += 1
                continue
            assert value["dtype"] == "BF16"
            lo, hi = value["data_offsets"]
            remaining = hi - lo
            assert remaining > 0 and remaining % 2 == 0
            stream.seek(8 + n + lo)
            row = Counter()
            maximum = 0.0
            while remaining:
                length = min(CHUNK_BYTES, remaining)
                buffer = bytearray(length)
                assert stream.readinto(buffer) == length
                source = torch.frombuffer(buffer, dtype=torch.bfloat16)
                assert source.device.type == "cpu"
                target = torch.empty(source.shape, dtype=torch.float16, device="cpu")
                target.copy_(source)  # Same cross-dtype copy operation used by loader paths.
                original = source.float()
                converted = target.float()
                absolute = original.abs()
                row["elements"] += source.numel()
                row["source_nonfinite"] += int((~torch.isfinite(original)).sum().item())
                row["outside_fp16_finite_range"] += int((absolute > 65504.0).sum().item())
                row["cast_nonfinite"] += int((~torch.isfinite(converted)).sum().item())
                row["changed_after_copy"] += int((original != converted).sum().item())
                row["nonzero_to_zero"] += int(((original != 0) & (converted == 0)).sum().item())
                if name.endswith(".scales"):
                    row["nonpositive_scales"] += int((original <= 0).sum().item())
                maximum = max(maximum, float(absolute.max().item()))
                row["payload_bytes_read"] += length
                remaining -= length
                del buffer, source, target, original, converted, absolute
            totals.update(row)
            totals["bf16_tensors_scanned"] += 1
            global_max = max(global_max, maximum)
            tensor_results.append({"name": name, "shard": path.name, "shape": value["shape"],
                                   "maximum_absolute_value": maximum, **dict(row)})
        after = os.fstat(stream.fileno())
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        assert identity(before) == identity(after)

assert totals["bf16_tensors_scanned"] == 707 and totals["i32_tensors_skipped"] == 896
assert totals["payload_bytes_read"] == 3600590848
passed = all(totals[key] == 0 for key in ("source_nonfinite", "outside_fp16_finite_range", "cast_nonfinite"))
assert not torch.cuda.is_initialized()
source_paths = [
    "vllm/model_executor/model_loader/loader.py",
    "vllm/model_executor/model_loader/weight_utils.py",
    "vllm/model_executor/parameter.py",
    "vllm/model_executor/layers/quantization/awq_marlin.py",
    "vllm/model_executor/layers/vocab_parallel_embedding.py",
    "vllm/model_executor/layers/layernorm.py",
]
package_root = ROOT / ".conda-vllm/lib/python3.12/site-packages"
proof = {
    "kind": "CPU_ONLY_BF16_TO_FP16_VALUE_SCAN_NOT_MODEL_OR_KERNEL_EXECUTION",
    "status": "PASS" if passed else "FAIL", "utc": datetime.now(timezone.utc).isoformat(),
    "model_id": manifest["model_id"], "revision": REVISION,
    "manifest_sha256": sha256(MANIFEST.read_bytes()).hexdigest(),
    "source_dtype": "BF16", "runtime_parameter_dtype": "FP16",
    "operation": "torch.empty(..., dtype=float16, device=cpu).copy_(source_bfloat16_cpu)",
    "torch_version": torch.__version__, "threads": torch.get_num_threads(),
    "interop_threads": torch.get_num_interop_threads(), "chunk_bytes": CHUNK_BYTES,
    "maximum_absolute_value": global_max, "counts": dict(totals),
    "elapsed_seconds": time.monotonic() - started, "tensor_results": tensor_results,
    "loader_source_sha256": {name: sha256((package_root / name).read_bytes()).hexdigest() for name in source_paths},
    "loader_source_review": "DefaultModelLoader sets model_config.dtype during parameter construction; AWQMarlin scales use params_dtype; parameter/default/embedding loaders copy_ loaded tensors into preallocated parameters. CPU copy proves numeric conversion for all BF16 values; actual GPU load remains unexecuted by this audit.",
    "cuda_initialized": torch.cuda.is_initialized(), "cuda_visible_devices": "",
    "network_calls": 0, "model_calls": 0, "gpu_queries": 0, "quantized_i32_payload_bytes_read": 0,
    "limitations": ["Reads BF16 payloads only under explicit authorization, in bounded chunks; header-only audit remains separate.",
                    "Finite in-range conversion does not establish quantization fidelity or language-task quality.",
                    "Small/subnormal values may round or underflow; counts are preserved, not silently excluded."]
}
out = ROOT / "var/reports" / ("qwen3_32b_dtype_cast_" + uuid4().hex + ".json")
with out.open("x") as stream:
    json.dump(proof, stream, indent=2)
    stream.write("\n")
print(json.dumps({"status": proof["status"], "proof_path": str(out.relative_to(ROOT)),
                  "proof_sha256": sha256(out.read_bytes()).hexdigest(), "counts": dict(totals),
                  "maximum_absolute_value": global_max, "elapsed_seconds": proof["elapsed_seconds"],
                  "cuda_initialized": False}))
raise SystemExit(0 if passed else 1)
