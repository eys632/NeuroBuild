# Generation3 독립 CPU / fake 경계 검증 archive

`cpu_preflight.json`과 `boundary_review.json`은 실제 완료한 proof의 **원본 bytes**다.
`provenance.json`에 원래 ignored 경로·archive 경로·크기·SHA256을 기록했다.
실행한 helper2개와 실행에 사용한 baseline도 byte 동일하게 보존했다.

- CPU: actual client fake capture200회, context1024cap 포함 최댓값 개발3617/노출3622/v2길이3547.
  xgrammar0.1.18 compile5.957초,24fixtures(문법10수락/14거절, backend5수락/19거절).
- Boundary: 기존1.0/2.0 legacy/modern6wire pairs byte 동일, rawREADY10경로의 FP분자/분모 유지,
  예외정보 비노출 및 interrupt전파, canonicalbyte/기존2helperAST 불변.
- Root가 별도로 보고한 전체 회귀는346PASS/skip0/18.730초다. 이 helper가 실행한 회귀는 아니다.

V2는 입력 길이 집계와 hash만 포함한다. V2 원문·gold·case ID·개별길이·모델출력은 archive에 없다.
Helper 안의 synthetic text는 독립 구조검사용이며 v2 본문이 아니다. 이전 root 입력 노출 이력과
AI gold의 비인간 검수 한계는 계속 적용된다. 모델 품질이나 실제 GPU/server grammar 통과를 뜻하지 않는다.

## 재실행 경로

**Archive 위치에서 helper를 직접 실행하지 않는다.** 두 helper의 `ROOT=parents[2]`,
baseline 참조, boundary→CPU helper import는 원래 `var/research/` 위치를 전제로 한다.
`provenance.json`의 original_path로 byte 동일하게 복원한 후 hash를 확인한다.
원래 파일이 이미 있으면 같은 hash인지 확인하며, 다른 새 파일을 조용히 덮어쓰지 않는다.

Repository root에서 실행한 명령은 다음과 같다. 새 설치나 실제 모델 실행을 요구하지 않는다.

```sh
CUDA_VISIBLE_DEVICES='' USE_TORCH=0 USE_TF=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src .conda-vllm/bin/python var/research/verify_generation3_32b_preflight.py
CUDA_VISIBLE_DEVICES='' PYTHONPATH=src .conda/bin/python var/research/review_generation3_boundaries.py
```

CPU helper는 현재 source/metadata와 원래 입력 dataset으로 새로운 ignored proof를 만든다.
동일 결과를 주장하려면 원 proof에 기록된 source/prompt/schema/tokenizer hash와 dependency가 같아야 한다.
Boundary helper는 reachable Git checkpoint16d67895의 옛 client와 현재 client를 비교한다.
과거 weight tensor를 다시 읽거나 모델을 띄우지 않으며, tokenizer/config 파일은 필요하다.
기존 tracked proof는 재실행 결과로 덮어쓰지 않는다. 실패 시 source/gold를 출력하지 않는
고정 오류코드가 출력되므로, 원문 비노출을 유지한 별도 진단이 필요하다.
