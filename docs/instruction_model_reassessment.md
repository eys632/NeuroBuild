# Instruction 전용 소형 후보 재검토

2026-09-20 KST. 대상은 **Qwen/Qwen3-4B-Instruct-2507** 하나다. 기존14B의 prompt·sampling 실험을 보존하면서, 반복된 instruction/원문 추출 실패에 대해 다른 post-training checkpoint도 비교할 근거가 있는지 조사했다. **선정 아님 / 한국어 BIM 품질 미검증 / GPU 실행 미검증**이다. 크기가 작다는 이유로 최종 모델로 채택하지 않는다.

공식 모델 카드·Hub metadata와 작은 config/tokenizer/license 문서를 메모리에서 읽고 기존 설치 소스와 대조했다. Weight나 새 tokenizer 파일을 받거나 저장하지 않았고 환경 설치·GPU 호출·production 소스 수정은 하지 않았다. 아래 CPU 검증은 모델 weight를 로드하지 않았다.

## 후보의 차이와 조사 결과

공식 카드는 이 모델을 기존 Qwen3-4B non-thinking의 instruction-following·도구 사용 등 개선판으로 소개한다. **Non-thinking만 지원**하고 think block을 생성하지 않으며 enable_thinking=false 지정도 필요 없다고 설명한다. 이 주장과 공개 benchmark가 기존14B보다 한국어 BIM에서 우수하다는 증거는 아니다. 한국어의 조건·제외 대상·원문 숫자 복사에 대한 자체 실측이 필요하다. [공식 모델 카드](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507).

| 항목 | 기존 Qwen3-14B-AWQ | 검토 후보4B-Instruct-2507 |
|---|---|---|
| 모드 | Thinking/non-thinking hybrid | Non-thinking 전용 |
| 모델 계열 | Qwen3ForCausalLM | 같은 architecture |
| 이번 checkpoint 정밀도 | AWQ W4A16/FP16 activation | **BF16 원본**, quantization 없음 |
| Weight blob 합 | 약9.292GiB | **7.49247GiB** |
| 모델 품질 근거 | 기존 NeuroBuild development 실측 있음 | NeuroBuild 실측 없음 |
| 현재 환경 호환성 | A100 실제 실행됨 | 공식 최소버전+로컬 소스+CPU config/template 근거, 실행 미검증 |

## 고정 가능한 공개 revision·파일

조회한 공개 revision은 **`cdbee75f17c01a7cc42f958dc650907174af0554`**이며 Hub lastModified는 `2025-09-17T06:56:53Z`, private=false, gated=false다. License metadata와 해당 revision의 LICENSE에서 Apache License 2.0 표기를 확인했다. [공식 API metadata](https://huggingface.co/api/models/Qwen/Qwen3-4B-Instruct-2507?blobs=true), [고정 revision 파일](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/tree/cdbee75f17c01a7cc42f958dc650907174af0554), [LICENSE](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/cdbee75f17c01a7cc42f958dc650907174af0554/LICENSE).

| Weight file | Bytes | Hub LFS SHA-256 |
|---|---:|---|
| `model-00001-of-00003.safetensors` | 3,957,900,840 | `75311d91bb08cf0b882913da464a1e722a31fb44db35208663487efb7a3d8ed6` |
| `model-00002-of-00003.safetensors` | 3,987,450,520 | `0b48adbb1f60e901153d91907ba11ce63bd4b8b584482e730f48808d055dfba1` |
| `model-00003-of-00003.safetensors` | 99,630,640 | `7dd39ccca5e4de123c74c14af44c9bf2eb75df33b4614382af0134528e060d5d` |
| 합계 | **8,044,982,000** | **7.49247GiB** |

Hub safetensors metadata는 BF16 parameter4,022,468,096개를 보고한다. 전체 repository 파일 합은8,060,917,568bytes=7.50731GiB다. `tokenizer.json`은11,422,654bytes, tokenizer config9,377bytes, weight index32,819bytes다. Index의 `metadata.total_size`는8,045,591,552로 실제 Hub weight blob 합과609,552bytes 차이가 있다. 디스크 예산에는 blob size를 사용하고 다운로드 검증에는 각 blob hash를 사용한다. Index의 weight_map398개에는 별도 lm_head.weight가 없으며 tied embedding 설정과 일치한다. [고정 weight index](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/cdbee75f17c01a7cc42f958dc650907174af0554/model.safetensors.index.json).

작은 문서를 조회해 계산한 SHA-256은 다음과 같다. 이 hash는 문서 bytes를 메모리에서 확인한 것이며 새 파일 설치 증거가 아니다.

| 파일 | SHA-256 |
|---|---|
| config.json | `5beea1a4a34c62782bfb2f911c606741a3bab8f92d80a118fa053c28af12e8ba` |
| generation_config.json | `835fffe355c9438e7a25be099b3fccaa98350b83451f9fd2d99512e74f1ade48` |
| tokenizer_config.json | `a62ff0a2472a0fa1b8eaabcb57c59b58afa42a22831dc141400b6e0cf2b65ce3` |
| LICENSE | `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e` |

## 현재 vLLM0.8.5/Transformers4.51.3와의 대조

공식 Quickstart는 **vLLM≥0.8.5**를 안내하고 Transformers4.51.0 미만에서 qwen3 인식 오류가 난다고 명시한다. 현재 설치는 vLLM0.8.5+cu118/Transformers4.51.3이므로 더 최신 runtime 설치를 선행 조건으로 삼을 이유는 발견하지 못했다. 이는 모델 로딩·kernel 실행 보장이 아니다. [공식 Quickstart](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507#quickstart).

| Config | 새 후보 값 | 로컬 소스 확인 |
|---|---|---|
| architectures/model_type | Qwen3ForCausalLM/qwen3 | vLLM registry와 Transformers Qwen3Config 존재 |
| layers/hidden/intermediate | 36 / 2560 / 9728 | 기존 Qwen3 implementation의 config 필드 |
| Q heads/KV heads/head_dim | 32 / 8 / **128** | explicit head_dim 사용; hidden_size÷heads=80으로 추정하면 틀림 |
| tie_word_embeddings | true | vLLM이 embedding을 lm_head로 공유하고 중복 lm_head load를 생략 |
| rope_theta/rope_scaling | 5,000,000 / null | 기존 Qwen3가 base와 scaling을 읽음; 새 rope type 없음 |
| max_position_embeddings | 262144 | 실행은 **max_model_len4096으로 제한** |
| use_sliding_window | false | 기존 지원 필드; 새 sliding attention 없음 |
| torch_dtype | bfloat16 | launcher가 이미 명시적 bfloat16을 허용 |
| quantization_config/auto_map | 없음 | AWQ/Marlin 또는 custom remote model code를 요구하지 않음 |

[공식 config](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/cdbee75f17c01a7cc42f958dc650907174af0554/config.json), [vLLM0.8.5 Qwen3 구현](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/models/qwen3.py), [registry](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/models/registry.py), [Transformers4.51.3 Qwen3Config](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/configuration_qwen3.py).

현재 환경에서 `Qwen3Config(**공식 config)`를 CPU로 생성해 정상 해석함을 확인했다. Standard metadata 외에 생성자가 모르는 새 architecture 설정은 없었다. `USE_TORCH=0/USE_TF=0/USE_FLAX=0`을 적용했고 torch 미import를 확인했다. VLLM model class 자체를 instantiate하거나 weight tensor shape/kernel을 실행한 검증은 아니다.

새 tokenizer는 Qwen2Tokenizer, vocab_size151936이다. 새 `tokenizer.json`의 공식 SHA **`aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4`**가 이미 있는14B tokenizer.json의 실제 hash와 동일했다. Tokenizer config 차이는 chat_template와 model_max_length 두 필드뿐이었다. 따라서 새 파일을 받지 않고 같은 로컬 tokenizer에 새 template만 메모리에서 넘겨 CPU 렌더링했다. 성공했고 thinking true/false가 동일한 문자열을 만들며 think tag는 없었다. Template SHA는 `64f85b198065d0fba2a81f37e10ed68161ce2c19a754c7100e67e0ca2ee9c326`다. [고정 tokenizer config](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/cdbee75f17c01a7cc42f958dc650907174af0554/tokenizer_config.json).

Tokenizer의 model_max_length1,010,000을 실제 지원 context나 실행 예산으로 사용하지 않는다. 모델 config와 별개인 tokenizer 상한이며 실행에는4096을 명시한다. 기존 legacy guided_json/xgrammar:no-fallback 경로를 유지하되 **reasoning parser는 끈 별도 non-thinking 서버**로 평가해야 한다. 현재14B thinking 서버에 false 요청만 보내는 방식으로 대체하지 않는다. 모델별 별도 business logic은 필요 없다.

## A100 자원 추정과 RTX 범위

4096 tokens/sequence1/BF16 KV의 이론량은 `2(K,V) × 36layers × 8KVheads × 128head_dim × 4096 × 2bytes` = **603,979,776bytes=576MiB**다. Weight blob+KV는 약8.055GiB다. Activation, CUDA context, attention workspace, allocator, 로딩 임시 메모리를 포함한 보수적 **전체 startup/inference peak 추정16GiB(16,384MiB)**를 다음 preflight의 출발점으로 제안한다. 측정값이나 hard cap 보장이 아니다.

기존 RoPE 구현은 config의262144 위치를 위한 cache도 만들 수 있다. BF16 cache 자체는 약64MiB이며 같은 설정의 get_rope 객체를 공유하지만 초기 FP32 계산과 다른 workspace도 있으므로 weight+KV만 전체 peak로 쓰지 않는다. [v0.8.5 RoPE 구현](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/model_executor/layers/rotary_embedding.py).

14B 작업을 정상 종료한 뒤 **GPU3만 새로 측정**해야 한다. 같은 GPU에 두 후보를 동시에 적재하는 계획이 아니다. 조건은 기존 정책대로 `16384MiB + max(6144MiB, 측정 min_free의20%) ≤ min_free`다. 과거 종료 후 free36373MiB라는 값에 대입하면 margin7275MiB, 합23659MiB지만 **현재 가용량의 증거는 아니다**. 실제 startup/inference peak와 watchdog 여유를 검증한 뒤에만 fit으로 기록한다.

이번 read-only `df -h /`는 여유62G, 사용률97%를 보였다. 추가 checkpoint는 약7.51GiB이며, 기존 downloader는 별도로 **20GiB의 디스크 여유를 남기는 조건**을 강제한다. 따라서 빈 destination에서 필요한 최소 free는 **27.507313GiB**다. 실행 직전 실제 free를 다시 확인하며 기존 모델이나 cache를 임의 삭제하지 않는다. Runtime을 재설치할 근거는 발견하지 못했다.

RTX5090 32GB에서도 같은 BF16 checkpoint의 weight+KV 산술은 작지만 **PREDICTED_UNVERIFIED**다. A100 cu118 환경을 SM120에 복사해서 실행할 수 있다는 뜻은 아니다. RTX에 맞는 driver/CUDA/PyTorch/vLLM build, native BF16 attention kernel, process/socket/종료 보호와 physical GPU1의 실제 가용량을 별도 검증해야 한다. A100의16GiB 추정을 RTX의 측정 peak로 재사용하지 않는다.

## 비교를 진행한다면

먼저 진행 중인14B v7 통제 실험을 완료·보존한 뒤 root가 비교 필요성을 결정한다. 후보를 받기로 결정한 경우 위 revision·file hash·license를 고정하고 기존 환경에서 작은 startup/structured-output 확인부터 한다. BF16/무양자화로 처음 비교하면 AWQ 양자화 여부도 달라지므로 차이를 parameter 수나 instruction tuning 하나의 효과로 단정하지 않는다.

공식 권장 sampling은 T=.7/top_p=.8/top_k20/min_p0이다. BF16 카드의 presence_penalty는0–2 조정 안내이지 AWQ 카드처럼1.5 고정 권고는 아니다. [Best Practices](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507#best-practices).

| 설정 | 고정 revision의 generation_config.json | 최초 비교 profile 제안 |
|---|---|---|
| do_sample | true | vLLM temperature>0 sampling |
| temperature / top_p / top_k | .7 / .8 / 20 | **.7 / .8 / 20** |
| min_p | 파일에 없음; 카드 권고0 | **0** |
| presence_penalty | 파일에 없음; 카드가0–2 조정 안내 | **0** |
| frequency_penalty | 파일에 없음 | **0** |
| repetition_penalty | 파일에 없음 | **1** |
| seed | 파일에 없음 | **42** |
| bos / eos / pad IDs | 151643 / [151645,151643] /151643 | checkpoint 값 보존 |
| thinking / parser | Non-thinking 전용 template | **false / 없음** |
| max_tokens / timeout | 파일에 없음 | **768 / 60초** |
| context / concurrency | 실행값은 파일에 없음 | **4096 / 1** |

[공식 generation config](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/cdbee75f17c01a7cc42f958dc650907174af0554/generation_config.json). 표 오른쪽의 penalty0/0/1과seed·예산은 **이번 비교를 위한 제안**이며 모델 카드가 그 전체 profile을 지정했다는 뜻은 아니다. 모든 값을 요청과 manifest에 명시해 상속 default에 맡기지 않는다. 현재 AWQ 전용 presence1.5 profile을 BF16 후보에 자동 재사용하지 않는다.

원문을 복사하는 작업은 target·instruction·evidence 사이에 같은 문자열이 반복된다. 양의 presence/frequency 또는1보다 큰 repetition penalty가 필요한 반복까지 억제할 가능성은 있으나, 이 모델에서 실패 원인으로 실측한 사실은 아니다. 따라서 첫 비교는 반복을 별도로 억제하지 않는0/0/1을 출발점으로 제안하며, penalty 변경이 필요하면 사전 고정한 별도 profile/run으로 비교한다. 모델·정밀도·일부 sampling이 동시에 달라지는 비교의 한계도 기록한다. 아직 이 profile을 구현하거나 실행하지 않았다.

현재 고정된 development 전체로 raw FP·unsafe accepted·target·원문 unit/숫자·조건 보존을 평가한다. 작은 모델이나 instruction 전용이라는 이유로 schema100/semantic≥95/rawFP0/unsafeaccepted0 gate를 낮추지 않는다. 품질 차이는 실제 결과 전까지 알 수 없으며, 이 조사는 기존 runtime에서 검토할 수 있는 **대안 실험의 근거**다. 다른 소형 후보까지 확장하거나 최종 모델을 선정하지 않았다.

## 비교 준비: 고정 manifest와 v3 context 확인

14B v7 실험을 보존한 뒤 별도 비교 후보로 준비한 [download manifest](../runtime/models/qwen3-4b-instruct-2507.json)는 위 공개 revision을 고정한다. LICENSE/README와 추론에 필요한12개 파일을 포함하고 `.gitattributes`는 제외했다. Manifest SHA-256은 **`70546521745f90e12e4fee0db9f73a7ec8a9296928b06b39d0f282cf1030c056`**, 파일 합은 **8,060,915,998bytes=7.507313GiB**다. Weight3개는 고정 Hub API의 LFS SHA-256과 size를 기록했고, 작은 파일은 고정 URL의 bytes/size/Git blob SHA-1을 확인한 뒤 SHA-256을 계산했다. 동일한 tokenizer.json은 공식 LFS size/hash와 기존 로컬 bytes를 대조했다. Index의398개 tensor가 참조하는 shard 집합은 manifest의3개 weight와 정확히 같다. Config와 tokenizer config에 `auto_map`이 없어 custom remote code를 요구하는 경로는 발견하지 못했다. 이 metadata 검증에서 weight를 내려받거나 모델을 실행하지 않았다.

[Downloader](../scripts/download_model.py)의 `RESERVE = 20 * 1024**3`는 최초 남은 파일 합과 파일별 저장 전에 검사된다. 새 다운로드의 전체 **8,060,915,998 + 21,474,836,480 = 29,535,752,478bytes**가 최소 free 조건이다. 이미 검증된 파일을 재사용할 때는 남은 bytes 기준이지만20GiB reserve는 유지된다. 이는 GPU 메모리 예산과 별개다.

새 공식 tokenizer config를 메모리에서만 읽어 manifest SHA와 대조하고, bytes가 동일한 기존 로컬 tokenizer에 새 chat template를 명시해 **CPU context 검증**을 수행했다. `USE_TORCH=0`, `USE_TF=0`, `USE_FLAX=0`, tokenizer offline/`trust_remote_code=False`를 사용했고 torch 미import를 확인했다. Weight 로딩이나 HTTP 추론은 수행하지 않았다. 실제 client와 같은 system/user JSON, `add_generation_prompt=True`, `enable_thinking=False`를 적용했다. Holdout은 입력 길이만 확인했으며 모델 출력이나 판정 조정에는 사용하지 않았다.

| 고정 입력 | 개수 | 최대 입력 tokens | 출력 cap768 포함 | 4096까지 여유 |
|---|---:|---:|---:|---:|
| Development | 40 | 2770 | **3538** | 558 |
| Holdout 입력 길이만 | 80 | 2775 | **3543** | 553 |

System v3 자체는2359 tokens다. V3 SHA는 `716137f3e275cb0030f1f497f8e23bbeeefd8a62eae757378231b7d910db3c3e`, template SHA는 `64f85b198065d0fba2a81f37e10ed68161ce2c19a754c7100e67e0ca2ee9c326`이다. Development/holdout 파일 SHA는 각각 `85734d7c5845bbc52af43941631adfa66f3b43cc7494177e1230de6dfb18ff88`, `12c08e85a3b64c459fe7385e1cab35a4a036c6ceb3bc1d27d137ba3515e74d78`다. 모든120개 입력이 context 예산 안에 들었지만 출력768 이내 완결이나 의미 정확도를 보장하지 않는다. Prompt·schema·scorer·gold는 변경하지 않았다. 실제 모델 로딩과 품질 검증은 별도 실험 결과로 기록해야 한다.
