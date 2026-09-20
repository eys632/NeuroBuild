# GLM 고정 metadata 보존

원본 metadata 수집은8파일+2API/21,133,497B다. 여기는 최종 immutable 자료와 수집 실패 이력을 그대로 보존한다.
`metadata_original_integrity.json`은 원래 ignored 조사 폴더 전체21파일의 manifest다.
이 Git archive 자체의 파일 집합은 별도 `archive_integrity.json`이 정의한다.

큰 tokenizer.json(20,217,442B)과 safetensors index(871,830B)는 ignored 자료로 유지하고 여기에는 복제하지 않았다.
두 파일의 고정 URL/revision/Git·LFS/SHA/크기는 API, fetch receipt, provenance, 원본 integrity에 남아 있다.
`fetch_small_files.py`와 보존된 고정 API 입력으로 다시 받을 수 있다. Weight는 Git에 포함하지 않는다.

현재 LICENSE 파일 부재·GGUF conversion 원본 revision 부재를 그대로 기록했다.
이 폴더의 prepared/not-run 상태는 수집 당시 역사이며 이후 실제 실행 여부는 STATUS와 별도 receipt가 정의한다.
