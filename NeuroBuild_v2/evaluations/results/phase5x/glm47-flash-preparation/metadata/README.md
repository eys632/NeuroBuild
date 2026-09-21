# GLM-4.7-Flash 후보 메타데이터

고정 revision의 작은 파일 수집은 완료했다. **모델 다운로드·native 실행·GPU 실행·품질 검사는 수행하지 않았다.**
이 자료는 다음 조건부 CPU/자원 검사의 입력이며 모델 채택 근거가 아니다.

- 원본: `zai-org/GLM-4.7-Flash@7dd20894a642a0aa287e9827cb1a1f7f91386b67`.
- 변환본: `ggml-org/GLM-4.7-Flash-GGUF@7559e96b7e324ab405897dc2b91492b0f376ad4a`.
- 후보 한 파일: `GLM-4.7-Flash-Q4_K.gguf`, 18,244,193,920 B,
  SHA256 `b6019edc5fbe37d3660d2e994d16c839a7855a6f03362c5dcf8142ba479cd0d2`.
  파일명 Q4_K만 관측했으며 실제 GGUF file type·tensor dtype·Q4_K_M 여부는 미검증이다.

API 두 파일과 원본 config/generation config/tokenizer config/tokenizer/template/card/index,
GGUF card의 실제 수집량은 총 21,133,497 B다. 한 파일 24 MiB/전체 50 MiB 한도 안에서 HTTPS로 수집했다.
일반 파일은 API의 Git blob SHA1·size와 대조하고 별도 SHA256을 계산했으며, tokenizer는
API의 LFS SHA256·20,217,442 B를 대조했다. `fetch_receipt.json`과 `api_receipt.json`에 URL·핀·해시가 있다.
첫 수집은 tokenizer CDN host가 좁은 allowlist에 없어 본문 수신 전에 멈췄다.
`fetch_first_attempt.json`과 v1 helper를 보존한 뒤 실제 HF CDN `us.aws.cdn.hf.co`만 추가하고,
먼저 받은 6개 파일을 검증해 재사용했다. signed redirect query는 저장하지 않았다.

[원본 card](https://huggingface.co/zai-org/GLM-4.7-Flash/blob/7dd20894a642a0aa287e9827cb1a1f7f91386b67/README.md)는
MIT를 선언한다. 두 pinned repository의 전체 파일 목록에는 별도 LICENSE 파일이 없다.
[GGUF card](https://huggingface.co/ggml-org/GLM-4.7-Flash-GGUF/blob/7559e96b7e324ab405897dc2b91492b0f376ad4a/README.md)는
43 B이고 base model 이름만 적는다. GGUF의 라이선스 선언, 원본 변환 revision, converter commit,
변환 명령과 양자화·calibration 출처는 제공하지 않는다. 원본의 현재 고정 metadata를 실제 변환 입력으로 단정하지 않는다.
이 공백은 `license_provenance.json`과 `provenance.json`에 따로 기록했다.
원저자 Z.ai와 변환 게시자 ggml-org를 구분하며, 없는 라이선스 원문이나 attribution을 만들지 않았다.

원본 config는 main 47층+MTP 1층, hidden 2048, vocab 154880, routed experts 64개 중 4개와 shared 1개다.
Index에는 9,703개 이름이 있고 layer47이 존재한다. Index `metadata.total_size=31,221,488,576`은
48개 shard의 API 파일 크기 합계 62,444,175,504 B와 다르므로 검증된 tensor-byte 합계로 쓰지 않는다.
실제 weight/header를 읽지 않았다. A3B 표기는 전체 weight 상주 메모리가 3B라는 뜻이 아니다.

Tokenizer JSON은 20,217,442 B/SHA256 `19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d`다.
정적 normalizer는 null, model은 ByteLevel 전처리의 BPE이며 vocab 154820+added tokens 36개다.
Config의 vocab 154880과 tokenizer entry 수를 동일하다고 가정하지 않는다.
이전 모델의 NFC 비활성화 reference 계약을 자동 승계하지 않는다. 실제 ID/roundtrip은 아직 검사하지 않았다.

공식 template는 3,120 B/SHA256 `d63ad536c3c81880043e22ec7fd08db42b4d8fb7c89c7138bc562bfa25281375`이며,
고정 f072 native source의 `models/templates/GLM-4.7-Flash.jinja`와 바이트가 같다.
System role이 독립 분기로 존재하고 Jinja continue는 없다. Nonthinking assistant suffix는
`<|assistant|></think>`다. 실제 native render·embedded GGUF template·generation grammar가
이와 일치한다는 주장은 아직 하지 않는다.

공식 card의 일반 benchmark 설정은 T1/P0.95, 최대 생성 131072 token이다.
이는 한국어 nonthinking 정확 인용에 대한 추천·보증이 아니다. Generation config는 T1만 명시한다.
별도 프로젝트 중립 recipe 제안은 top-k0/min-p0/presence0/frequency0/repeat1/window0/seed42,
sampler 순서 temperature→top_k→top_p→min_p, thinking=false다. 이 추가 항목과 output768/context4096은
공식 추천이라고 표시하지 않는다. 실제 production profile 선정은 root의 별도 결정이다.

`public_cpu_contract_plan.md`와 `public_tokenizer_cases_design.json`은 설계만 작성했다.
20개 공개 문자열에 대한 token IDs·roundtrip·native grammar·평가 자료의 길이를 실행하지 않았다.
`candidate_download_manifest_draft.json`은 root 검토를 위한 초안이며 다운로드 승인이나 실행 기록이 아니다.
모든 변경은 이 ignored 폴더 안에만 있고 기존 결과·prompt·schema·parser·production source는 바꾸지 않았다.

재수집할 때는 `api_receipt.json`의 immutable revision API 응답을 먼저 보존·검증하고,
`fetch_small_files.py`로 해당 exact 파일만 받는다. 기존 파일은 기대 Git/LFS 핀과 맞아야 재사용한다.
환경 설치는 필요 없으며 `.conda`의 stdlib만 사용했다. 최종 `integrity.json`은 이 폴더 파일의 SHA256과 크기를 기록한다.
