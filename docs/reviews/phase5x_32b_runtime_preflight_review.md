# 32B CPU·runtime 사전 독립 검토

2026-09-20 UTC. **제한된 exposed120 진단 준비 PASS; 새 모델의 의미 품질과 채택은 미검증.**
공식 `Qwen/Qwen3-32B-AWQ` revision `0499c3ac83fdef8810b907a23894ba91e95eddd8`의
CPU 증거, 설치된 loader 소스, 자체 서버 로그와 root가 보존한 기동 증거를 독립 검토했다.
이 검토자는 GPU 조회·HTTP health·모델 호출·프로세스 종료·weight payload 재검사를 하지 않았다.
새 holdout v2 입력/gold도 읽지 않았다. 검토 범위에서 새 blocker는 발견하지 못했다.

## CPU 증거와 보존된 경고

[다운로드 기록](../../evaluations/results/phase5x/32b-download.json)의13개 파일 목록은
[고정 manifest](../../runtime/models/qwen3-32b-awq.json)와 일치한다.
전체19,341,523,989bytes의 SHA 검증은 downloader가 수행한 기록이며 이 검토에서 반복하지 않았다.
[Header 검사](../../evaluations/results/phase5x/32b-header-audit.json)는 config에서 도출한
1,603개 tensor의 이름·shape·shard 배치와 실제 offset coverage를 대조한다.
707개 BF16과896개 I32의 합계, shard byte 합계, 현재 shard의 device/inode/size/mtime가
기록과 일치함을 확인했다. Payload를 다시 읽지 않았다.

`config.torch_dtype=float16`과 실제 BF16 저장은 다르다. 최초 저장 dtype 가정 실패를
지우지 않고 별도 [CPU 변환 검사](../../evaluations/results/phase5x/32b-dtype-cast-audit.json)로
보완한 절차가 적절하다. Index의 `metadata.total_size`는 실제 tensor data
19,325,298,688bytes보다13,107,200bytes 크다. 원인을 확정하지 않고 경고로 남기며,
index의 tensor 이름/배치와 실제 header coverage 검증을 유지했다.

변환 증거의707개 tensor 결과를 독립 합산했다. 1,800,295,424개 값에서 원본 비유한 값,
FP16 유한 범위 초과, 변환 후 비유한 값은 모두0이고 최대 절댓값은27.25다.
448개 quantization scale tensor의243,793,920개 값은 전부 양수이며 변경과 zero 변환이0이다.
일반 tensor에는392,411개 rounding과2,335개 nonzero→zero가 있다.
Zero 변환은 embedding1,211개와 lm_head1,124개에만 나타난다.
이는 경고를 보존한 유한 값 변환 검사이며 양자화 충실도나 언어 품질 통과를 뜻하지 않는다.

설치된 source6개의 SHA가 변환 증거와 일치한다. `model_loader/loader.py:450`의
`set_default_torch_dtype(model_config.dtype)` 안에서 parameter를 만들고,
`awq_marlin.py:237`은 `params_dtype`로 scales를 생성한다.
`parameter.py:109/130/155/184`, `weight_utils.py:587`과 embedding loader는
preallocated destination의 `copy_`를 사용한다. Norm도 선택된 기본 dtype으로 생성된다.
Marlin scale 재배열은 로딩 뒤에 수행된다. 따라서 BF16 저장 자체가 FP16 로딩 차단 사유는
아니다. CPU copy 결과는 GPU 변환 결과의 bitwise 동일성이나 실제 kernel/품질을 증명하지 않는다.

[Tokenizer/grammar 증거](../../evaluations/results/phase5x/generation2-32b-cpu-preflight.json)는
실제 metadata9개, 내장 template, `enable_thinking=false`, branch schema와 prompt v2를 묶는다.
Template의 빈 `<think>` prefix는 생성된 reasoning과 구분되어 있다.
Grammar valid8/invalid14, prompt 예시7개의 schema→adapter→기존 parser 검증이 기록되었다.
노출된 development40/기존 holdout80의 input+output768 최대값은3,682/3,687로4096 이내다.
이 검토는 해당 도구와 결과를 확인했으며 tokenizer/grammar 검사를 재실행하지 않았다.
V2 길이만의 집계 증거는 품질 평가나 완전 맹검 증거로 사용하지 않는다.

## 실제 A100 기동 경계

[Launch](../../evaluations/results/phase5x/32b-generation2-v2-launch/launch_config.json),
[runtime metadata](../../evaluations/results/phase5x/32b-generation2-v2-launch/runtime_metadata.json),
[startup](../../evaluations/results/phase5x/32b-generation2-v2-launch/startup.json),
[resource snapshot](../../evaluations/results/phase5x/32b-generation2-v2-launch/resource_report.json),
[listener snapshot](../../evaluations/results/phase5x/32b-generation2-v2-launch/listeners.json)의
hash·model path·alias·PID 연결을 확인했다. Root의 health200/모델 목록 기록은
`neurobuild-local`, 정확한 로컬 revision 경로, max context4096을 가리킨다.
자체 child3467850의 관측 TCP listener5개는 모두127.0.0.1이다.
이는 해당 PID의 해당 시점 TCP 검사이며 미래 listener나 UDP 전체를 보장하지 않는다.

자체 로그에서 실제 FP16/AWQMarlin, V0/uni/TP1, FileStore world1, eager,
weight loading18.1453GiB, profiling activation0.76GiB/non-Torch0.09GiB,
KV256 blocks와 application startup complete를 확인했다.
보존된 startup 기록의 inference call 수는0이다. 이 초기화에는 engine profiling/warmup이
포함되지만 사용자 요청의 schema·parser·의미 정확도는 아직 평가하지 않았다.

Fresh GPU3 preflight5회는 free36,373MiB/utilization0으로 기록됐다.
Margin7,275MiB, 가용 budget29,098MiB에서 계획 peak25,600MiB를 빼면3,498MiB가 남는다.
vLLM/Torch fraction은 각각0.60, allowance0, watchdog 증가 한도25,600MiB다.
기동 snapshot의 aggregate baseline 대비 증가 최대20,332MiB와 최소 free16,042MiB는
각 한도25,600MiB와 floor7,275MiB 안에 있다. Aggregate 변화는 다른 workload의 해제도
포함하므로 자체 process peak의 상한이나 hard isolation이 아니다.
현재 설정은 A100 physical3만의 증거이며 RTX5090 physical1은 미검증이다.

## Freeze와 후속 판단

[진단 freeze](../../evaluations/hardening_v1_exposed_generation2_32b_diagnostic_freeze.json)의 SHA는
`0e525113175e9617c2f46f3e32958b184dd4d76918873157ee978de25d26e023`이다.
포함된29개 hash 중 v2 freeze/exposure addendum2개를 제외한27개를 독립 대조했다.
V2 관련 전체 보존 검사는 root/freeze helper가 수행한 기록이며 이 검토자가9개 파일을
다시 읽었다고 주장하지 않는다. Replay용049ab13 snapshot의17개 tracked source/설정도
현재 파일과 일치한다. 실제 runtime metadata와 launch SHA, launcher SHA, resource SHA,
template, alias 및 동일 child PID의 startup/listener 연결이 일치한다.

실험은 `single`, generation2, decision branch schema, prompt v2, legacy greedy T0/seed42,
output768/timeout60/context4096의 **노출된120개×1+warmup5**다.
Schema120/120, 의미≥114/120, raw READY FP0/58, unsafe0/120이 다음 정식 회귀의 진입 조건이다.
진단 PASS만으로 채택하거나 Phase6으로 진행하지 않는다. 후속 정식 회귀와 holdout은 별도 gate다.
현재 문서 작성 시32B 진단은 미실행이며 준비한 replay helper도 실행하지 않았다.
이전 실패 결과, 사람 미검수 synthetic gold, 과거 root v2 입력 부분 노출 한계는 유지한다.
