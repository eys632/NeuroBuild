# RTX5090 model runtime 계획 — UNVERIFIED

- 사용자 제공 이전 상태: RTX5090 2개 중 physical GPU1만, VRAM32GB.
- `.conda-vllm`, `CUDA_VISIBLE_DEVICES=1`, process 내부 cuda:0, TP=1.
- GPU0 사용/자동 fallback 금지. 실제 OS/driver/toolkit/free VRAM은 미확인.
- 공식 Blackwell CC12.0 지원 torch/vLLM wheel과 quant kernel을 확인해야 한다.
- 가능하면 A100과 같은 model/tokenizer/semantic contract를 사용한다. build 또는
  quantized checkpoint가 다르면 정확도/latency regression을 별도로 평가한다.
- model weight만 fit하는 것은 runtime fit이 아니다. KV cache, workspace, CUDA graph,
  비양자화층을 포함하고 context/concurrency/메모리 margin을 측정한다.
- `configs/rtx5090.json`은 계획 예제다. 실제 실행/benchmark/PASS 이력 없음.

접속 가능해지면 [compatibility gate](../../docs/runtime_compatibility.md)를 수행하고
이 디렉터리에 별도 GPU dependency lock를 남긴다. Application은 공통 코드를 그대로 사용한다.

공통 checkpoint는 Qwen/Qwen3-14B-AWQ pinned revision이다. 최신 vLLM0.29.0의 SM120 Marlin W4A16 source 및 wheel metadata를 조사했지만 설치/resolve/추론은 하지 않았다. `structured_outputs` request와 server `--structured-outputs-config.backend=xgrammar`가 필요하며 legacy guided_json을 그대로 보내지 않는다. `awq_marlin` 이름만으로 실제 kernel을 보장하지 않으므로 MarlinLinearKernel 로그/linear backend와 GPU1 메모리를 검증해야 한다. 자세한 근거와 미검증 항목은 [protocol compatibility](../../docs/model_protocol_compatibility.md)를 따른다. A100 model_server.py의 V0/uni/cu118/FileStore lifecycle은 RTX modern V1 launcher의 검증을 대신하지 않는다.
