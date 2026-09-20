# 모델 license 출처 보존

[qwen3-30b-a3b-instruct-2507.LICENSE](qwen3-30b-a3b-instruct-2507.LICENSE)는 원본
`Qwen/Qwen3-30B-A3B-Instruct-2507`의 Apache License 2.0 본문이다. 앞서 검증·보존한
`UPSTREAM_LICENSE`를 byte 변경 없이 복사했으며, 이번 보존 작업에서 다시 다운로드하지 않았다.

| 항목 | 값 |
|---|---|
| 원본 revision | `0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe` |
| 고정 원본 URL | [LICENSE](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/resolve/0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe/LICENSE) |
| Bytes | `11343` |
| SHA-256 | `05cab46843576551502bfdf712f84e93e6e9590d9997306ed4f6635ef82811d9` |
| 사용 후보 | `ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ` |
| 후보 revision | `9f41ff709102dbe73e614f9365f8280170db268e` |

후보는 **제3자 양자화 배포본**이다. 해당 revision의 README는 Apache-2.0과 원본
Qwen LICENSE 링크를 표기하지만 후보 repository 자체에는 LICENSE 파일이 없다.
이 사본을 후보 repository에서 받은 파일 또는 Qwen 공식 AWQ 배포의 증거로 표시하지 않는다.
[배포자 README](https://huggingface.co/ELVISIO/Qwen3-30B-A3B-Instruct-2507-AWQ/blob/9f41ff709102dbe73e614f9365f8280170db268e/README.md).

[고정 manifest](../models/qwen3-30b-a3b-instruct-2507-awq.json)의 `license_provenance`와
같은 bytes/hash를 보존한다. 이 파일은 downloader의15개 모델 파일 목록이나 합계에
추가되지 않으며 모델 manifest를 변경하지 않는다. 원본 revision은 **license 본문의
고정 출처**이지 양자화에 실제 사용된 base checkpoint revision의 독립 증명은 아니다.

모델 artifact의 revision·파일 해시를 고정한 재다운로드와 양자화 과정의 재생성은
다르다. 배포자가 설명한 ms-swift/calibration 설정을 독립 실행하지 않았으며,
도구·calibration 자료의 revision과 전체 환경을 고정해 같은 weight를 재생성한 검증도
없다. 이 license 보존을 그러한 검증이나 품질 통과로 해석하지 않는다.

## Qwen3-32B-AWQ 공식 배포본

[qwen3-32b-awq.LICENSE](qwen3-32b-awq.LICENSE)는 공식 후보 revision
`0499c3ac83fdef8810b907a23894ba91e95eddd8`의
[원문](https://huggingface.co/Qwen/Qwen3-32B-AWQ/resolve/0499c3ac83fdef8810b907a23894ba91e95eddd8/LICENSE)이다.
11,544bytes, SHA256 `5de36594c10839788a8c589443a8ef9d8b8d17c65a1b5807206ae037fc36c6bd`.
연구 시 검증한 파일을 byte 변경 없이 보존했고 downloader13파일에도 포함한다.
이는 양자화 재생성 또는 모델 품질 검증을 의미하지 않는다.
