# A100 model runtime 계획

- 환경: project root의 `.conda-vllm`, Python3.12 우선 검토; 미생성.
- GPU3만 `CUDA_VISIBLE_DEVICES=3`, process 내부 cuda:0, TP=1.
- 실측: A100-PCIE-40GB/CC8.0, driver535.183.01, Toolkit11.8.
- 현재 GPU3 점유 process3개 발견. 실행 금지/보고 완료. 다른 GPU fallback 금지.
- vLLM/Torch/CUDA/Python/Transformers/xgrammar의 검증된 조합은 아직 없다.
- 최신 모델의 architecture/quant kernel 지원과 driver535/JIT 제약을 함께 해결한 뒤
  설치용 manifest/lock 및 exact model revision/launch args를 이 디렉터리에 기록한다.
- 설정 예제는 `configs/a100.json`; model/dtype/quant는 최종 미선택이다.
- root disk96% 사용, 대형 설치 보류. [환경 계획](../../docs/environment.md)을 따른다.

이 문서는 launch script가 아니다. 시스템 driver/CUDA를 변경하지 않는다.
