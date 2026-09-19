# Common Backend environment (계획)

두 서버 공통 `.conda`, Python3.12. 환경은 아직 없다.
Phase1의 domain/contract에 필요한 최소 dependency부터 선택하고, Phase2에서 psycopg,
Phase3에서 IfcOpenShell, Phase5에서 공통 HTTP/validation 필요분을 추가한다.
jsonschema 등 정확한 버전은 각 단계에서 공식 Python/platform 지원을 확인해 고정한다.

향후 common source manifest와 lock/export를 여기에 둔다. torch/vLLM/Transformers/CUDA wheel은
이 환경에 넣지 않는다. Python patch/직접·간접 dependency/환경 재생성 명령을 기록하고
같은 lock를 두 서버에서 검증한다. 현재 설치용 requirements 파일은 없으며 설치하지 않았다.
