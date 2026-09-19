# 30B-A3B instruction AWQ 조건부 후보 준비

2026-09-20 KST. **다음 실측 비교 준비 / 최종 모델 미선정 / GPU 및 한국어 BIM 품질 미검증.**
처음에는 4B 비교와 별개의 contingency로 같은 Qwen3-30B-A3B-Instruct-2507의 공개
AWQ 파일을 조사했다. 4B v3 greedy 비교 종료 후 root가 이 후보의 다음 실험 준비를
결정했다. 다른 모델 목록으로 확대하지 않았다.
작은 metadata만 조회·보존했으며 weight 다운로드, 환경 설치, 모델 실행, GPU 조회,
진행 중인 서버 종료 또는 Application 코드 변경은 수행하지 않았다.

## 출처와 고정 파일

후보는 **제3자 배포본** `ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ`, revision
**`9f41ff709102dbe73e614f9365f8280170db268e`**다. Public/ungated이며 Qwen 공식
AWQ 배포로 부르면 안 된다. 조사한 Qwen HF namespace에는 원본 BF16 및 FP8만
확인됐고 공식 AWQ는 찾지 못했다. 배포자는 ms-swift AWQ INT4 사용과
`swift/Chinese-Qwen3-235B-2507-Distill-data-110k-SFT` calibration512개,
max_length12000을 설명한다. 이 설명은 양자화 실행을 독립 재현했다는 뜻이 아니다.
[고정 배포본](https://huggingface.co/ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ/tree/9f41ff709102dbe73e614f9365f8280170db268e),
[배포자 README](https://huggingface.co/ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ/blob/9f41ff709102dbe73e614f9365f8280170db268e/README.md).

[Downloader manifest](../runtime/models/qwen3-30b-a3b-instruct-2507-awq.json)의
SHA-256은 **`32ff8e507fb4b25f5e67da2d03ba898d52467d653eb55c4c1cc906ee2738939c`**다.
README, config/generation config, tokenizer 파일, 별도 chat template, weight index,
weight shard4개를 포함한 **15개 파일, 16,830,441,067bytes = 15.674570GiB**다.
`.gitattributes`, `.mdl`, `.msc`, `.mv`, 불필요한 `configuration.json`은 제외했다.
추가 모델 포맷이나 중복 weight를 받는 manifest가 아니다.

| Weight file | Bytes | Hub LFS SHA-256 |
|---|---:|---|
| model-00001-of-00004.safetensors | 5,001,815,024 | `dded37cd3936271f93655917a55634553c41679a467d97ce2004cdfff20a718e` |
| model-00002-of-00004.safetensors | 5,002,166,720 | `28c8065b1f3fe82bceae32aece99b404ef4f06e9be7d93e1a5028b7dd330c591` |
| model-00003-of-00004.safetensors | 5,001,879,600 | `53ef6b077e5bc0bd3cd4d799ac839a79a2688b3242384c129e781934cd6e9462` |
| model-00004-of-00004.safetensors | 1,803,606,480 | `df81a01f3d039cdc0b7d212608590884404b85825438078fce2e8cf7d68c6ecf` |
| 합계 | **16,809,467,824** | **15.655037GiB** |

Weight hash/size는 [고정 Hub API](https://huggingface.co/api/models/ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ/revision/9f41ff709102dbe73e614f9365f8280170db268e?blobs=true)의
LFS metadata를 사용했다. 아직 실제 weight bytes를 받거나 hash를 계산하지 않았다.
작은 파일은 고정 revision URL에서 읽어 size와 Hub Git blob SHA-1 또는 LFS SHA-256을
대조한 뒤 각 SHA-256을 계산했다. Index의 56,115개 key는 48층·128 experts와 attention의
예상 AWQ qweight/qzeros/scales 및 비양자화 parameter key 집합과 정확히 일치했다.
Index가 참조하는 shard 집합도 위 4개와 같다. Tensor shape·값·양자화 품질의 검증은 아니다.
Index metadata.total_size16,802,672,640bytes와 실제 blob 합의 차이는 별도로 유지하며,
디스크 계산에는 blob 합을 사용한다.

| Metadata | SHA-256 |
|---|---|
| config.json | `efb6d69fb62380d96f24c170ff0cc1ea57f1d168c19d73e42874a2432c83380c` |
| model.safetensors.index.json | `f5b4f889fe28ee7965333f4d8a14a357b81b9a0b7b3331217061342a791844d2` |
| chat_template.jinja | `40c21f34cf67d8c760ef72f8ad3ae5afad514299d4b06e91dd9a8d705af7b541` |

작은 metadata와 API 응답은 Git에서 제외되는
`var/research/qwen3-30b-a3b-instruct-2507-awq/9f41ff709102dbe73e614f9365f8280170db268e/`에
보존했다. Metadata와 원본 license 본문은 합계20,984,586bytes이며 weight는 포함하지 않는다.

## License provenance

배포본 README metadata는 Apache-2.0과 원본 Qwen LICENSE 링크를 표기하지만, 이
ELVISIO revision 자체에는 **LICENSE 파일이 없다**. 따라서 downloader의 `files`에
존재하지 않는 LICENSE를 넣지 않았다. Manifest의 추가 `license_provenance`는
아래 고정 원본 LICENSE의 출처·bytes·hash를 기록하며, 기존 downloader는 이 설명
필드를 다운로드 목록으로 취급하지 않는다. Downloader 소스는 변경하지 않았다.

원본 `Qwen/Qwen3-30B-A3B-Instruct-2507` revision
`0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe`의 LICENSE는11,343bytes이고 SHA-256은
**`05cab46843576551502bfdf712f84e93e6e9590d9997306ed4f6635ef82811d9`**다.
Apache License2.0 본문과 Git blob hash를 확인했으며 위 evidence directory의
`UPSTREAM_LICENSE`로 보존했다. Manifest 파일 합은 이 별도 provenance 본문을
다운로드 대상으로 포함하지 않는다.
[고정 원본 LICENSE](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe/LICENSE).

## 설치된 런타임의 정적 호환성

현재 `.conda-vllm`은 Python3.12.14, vLLM0.8.5+cu118, Torch2.6.0+cu118,
Transformers4.51.3이다. 원본의 공식 안내는 vLLM≥0.8.5와 Transformers≥4.51.0이지만,
제3자 AWQ 배포자의 구체적인 컨테이너 예시는 **vLLM0.10.0**이다. 원본 architecture
지원과 이 양자화본의 구버전 실행 실증은 다르다. 이 검토는 현재 버전을 바꾸지 않고
읽은 소스에 기반하며 0.8.5에서 로딩·kernel 실행이 성공했다고 주장하지 않는다.
[공식 원본 Quickstart](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507#quickstart),
[배포자 실행 예시](https://huggingface.co/ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ#inference).

| 설정 | 고정 checkpoint 값과 설치 소스 대조 |
|---|---|
| architecture/model_type | Qwen3MoeForCausalLM / qwen3_moe; vLLM registry와 Transformers config 존재 |
| layers / hidden / MoE intermediate | 48 / 2048 / 768 |
| experts / activated experts | 128 / 8; 전체 expert weight를 적재하므로 3B만 VRAM에 놓는 모델이 아님 |
| Q heads / KV heads / head_dim | 32 / 4 / **128**; hidden÷heads=64로 계산하면 틀림 |
| quantization | `awq`, GEMM, bits4, group_size128, zero_point=true; compressed-tensors 포맷 아님 |
| activation dtype / 제외 모듈 | float16 / mlp.gate 및 lm_head 비양자화 |
| RoPE | theta10,000,000, scaling=null, max_position_embeddings262144 |
| remote custom code | config와 tokenizer config에 auto_map 없음 |

설치 소스의 `AWQMarlinConfig`는 위 설정을 AWQ Marlin으로 선택할 수 있고,
FusedMoE에는 `AWQMoEMethod`를 사용한다. SM80 이상과 group128이 지원 범위이며
hidden2048%128=0, intermediate768%128=0 조건도 맞는다. `_C.abi3.so`의
`awq_marlin_repack` 및 `_moe_C.abi3.so`의 `moe_wna16_marlin_gemm`, `topk_softmax`,
`moe_align_block_size` native symbol을 파일에서 확인했다. Symbol 존재는 해당
checkpoint의 실제 CUDA 실행 검증을 대신하지 않는다. AutoAWQ 재양자화 도구 설치는
이 저장 형식을 읽는 데 선행 조건으로 확인되지 않았다.
[v0.8.5 Qwen3MoE](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/models/qwen3_moe.py),
[AWQ Marlin](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/layers/quantization/awq_marlin.py),
[shape 검사](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/layers/quantization/utils/marlin_utils.py).

같은 모델명에 AWQ를 붙인 cyankiwi/stelterlab 파일은 실제 config가 compressed-tensors다.
이 manifest와 혼용하거나 그쪽 실행 사례를 ELVISIO 검증으로 대체하지 않는다.

Architecture 담당자의 독립 source·수치 검토에서도 중대 blocker는 발견되지 않았다.
`decoder_sparse_step=1`과 빈 `mlp_only_layers`로 48층 모두 MoE intermediate768을
사용하며, dense intermediate6144 경로를 사용하는 구성은 아니다. Explicit head128의
QKV output5120/O input4096도 Marlin 분할 조건에 맞는다. 정적 검토대로라면 기존
auto AWQ→Marlin 선택을 유지해야 하며 `--quantization awq`로 강제해 다른 커널 경로를
택하면 안 된다. Quantized loader의 strict missing-weight 검사가 생략되는 경로가 있어
index 대조는 유용하지만 실제 tensor shape/dtype/내용 검증과 kernel 실행을 대신하지 못한다.

## Non-thinking template와 CPU 확인

이 배포본은 tokenizer_config에 template를 넣지 않고 **별도 chat_template.jinja**를
제공한다. Transformers4.51.3은 이 파일을 자동으로 읽는 경로가 있어 반드시 manifest에
포함했다. `USE_TORCH=0`, `USE_TF=0`, `USE_FLAX=0`, offline/local_files_only 및
trust_remote_code=false로 고정 metadata를 읽어 `Qwen3MoeConfig` 생성과
`AutoTokenizer`의 Qwen2TokenizerFast 로딩이 통과했다. Torch와 vLLM 미import를 확인했다.

현재 client처럼 단일 system/user 메시지와 add_generation_prompt=true를 사용한
CPU 렌더링은 `<|im_start|>assistant` 뒤에서 시작하고 think tag를 만들지 않았다.
이 입력에서는 enable_thinking true/false의 렌더링이 같다. Template 전체에는 과거
assistant reasoning을 처리하는 코드도 있으므로 모든 대화형태에 think tag가 없다고
일반화하지 않는다. 이번 후보는 non-thinking 요청과 reasoning parser 비활성으로만
검토하며, hybrid 모델의 reasoning parser를 상속하지 않는다. 길이·출력 완결·한국어
요구사항 정확도는 이 간단한 CPU 확인으로 검증되지 않았다.

별도 검토자는 같은 저장 metadata를 사용해 실제 client의 system/user JSON과 V3 prompt로
**입력 길이만** 독립 검사했다. Manifest hash와 11개 작은 파일의 실제 bytes/SHA 및
Hub blob/LFS 대조가 통과했고, 로딩된 template와 별도 `.jinja`가 정확히 같았다.
V3 SHA는 `716137f3e275cb0030f1f497f8e23bbeeefd8a62eae757378231b7d910db3c3e`,
system 자체는2359 tokens다. 결과는 다음과 같다.

| 입력 집합 | 개수 | 입력 tokens 범위 | 최대 입력+출력 cap768 | 4096까지 여유 |
|---|---:|---:|---:|---:|
| Development | 40 | 2395–2770 | 3538 | 558 |
| Holdout 입력 길이만 | 80 | 2401–2775 | 3543 | 553 |

Development SHA는 `85734d7c5845bbc52af43941631adfa66f3b43cc7494177e1230de6dfb18ff88`,
holdout SHA는 `12c08e85a3b64c459fe7385e1cab35a4a036c6ceb3bc1d27d137ba3515e74d78`다.
모든 렌더링은 assistant prefix 뒤 newline에서 끝났으며 이 검증도 torch import,
GPU·네트워크·weight 접근 없이 수행됐다. Holdout 출력·판정을 조회하거나 prompt/gold를
조정하지 않았다. Context 예산 안에 있다는 결과는 출력768 이내 완결이나 의미 정확도
성공을 보장하지 않는다.

## A100 peak·디스크 예산과 실행 범위

context4096 / sequence1 / TP1 / FP16 KV의 이론량은
`2 × 48layers × 4KVheads × 128head_dim × 4096 × 2bytes` = **384MiB**다.
설치된 MoE source에 따른 추가 항목은 native262144 RoPE FP16 cache 약64MiB,
최대 layer W13 repack의 새 output 약192MiB, M4096/top8 MoE 중간 cache 약176MiB다.
이는 workspace 전체를 포괄하는 peak 측정이 아니다. Weight, KV, activation, CUDA
context, 임시 repack 및 allocator 여유를 포함하는 **24GiB(24,576MiB) 전체
startup/inference peak 추정**을 조건부 출발점으로 둔다. 측정값·hard cap·실행 허가가 아니다.
W13 repack loop에는 expert당 약1.5MiB의 임시 결과도 존재한다. 변환은 module별로
순차 수행하므로 전체 checkpoint의 두 배를 동시에 유지한다고 볼 근거는 없지만,
allocator 잔류와 실제 긴 prefill peak·throughput은 아직 측정하지 않았다.
[MoE kernel 경로](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/layers/fused_moe/fused_marlin_moe.py).

과거 free36,373MiB에만 대입하면 margin=max(6144,ceil(36373×.2))=7,275MiB,
추정+margin=**31,851MiB ≤ 36,373MiB**, model budget29,098MiB다. 후보의 runtime와
Torch fraction을 모두 .60으로 정한다면 명목 total40,960MiB 기준24,576MiB이며,
기존 watchdog의 estimate+allowance1024에 따른 aggregate 증가 한계는25,600MiB다.
아직 이 값으로 실행하지 않았다. 다른 자체 서버의 사용량을 무시하고 위 과거 free를
재사용하면 안 된다. 실행 시 기존 자체 서버의 정상 종료를 확인한 뒤 **GPU3만 새 preflight**를 해야 한다.
다른 GPU fallback, 타인 작업 변경, 동시 후보 적재는 허용하지 않는다. Sampling으로
관측한 aggregate 증가는 per-process peak나 강한 GPU 격리 보장이 아니다.

준비 시 statvfs 기준 디스크 free는 약54.10GiB였다. 위 manifest 한 사본을 저장한 뒤
약38.42GiB가 남는 산술이며 추가 runtime 설치나 중복 cache를 가정하지 않는다.
기존 downloader는 **20GiB reserve**를 유지한다. 빈 destination에서 필요한 최소
free는 **16,830,441,067 + 21,474,836,480 = 38,305,277,547bytes**다. 실제 다운로드
전후 디스크와 cache를 다시 확인하며 기존 모델·환경·평가 증거를 자동 삭제하지 않는다.

RTX5090는 **PREDICTED_UNVERIFIED**다. A100 cu118/SM80의 소스·symbol 확인을
RTX SM120 실행 증거로 사용하지 않는다. 동일 business code를 유지하되 RTX의
driver/CUDA/runtime/kernel, GPU1 가용량, peak와 종료·loopback 보호를 별도로 확인해야 한다.

이 준비는 기존 4B development 결과를 바꾸거나 미통과 gate를 완화하지 않는다.
4B 종료 후 root가 다음 비교를 결정했으므로 다운로드·새 preflight·startup·structured
output·고정 development 평가를 순서대로 진행할 수 있도록 준비했다. 이 문서의 검토자가
직접 수행한 결과는 **manifest와 정적 검토 준비 완료**이며 실제 실행 결과는 별도 증거다.
