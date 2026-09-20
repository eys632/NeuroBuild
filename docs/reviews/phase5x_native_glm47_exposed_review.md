# GLM 첫 단회 결과 독립 검토

**저장 결과 재검산 PASS, 1차 품질 gate FAIL**이다. 새로운 모델 출력이나 과거125개 진단을 재평가하지 않았다.

사전 동결한 `replay_native_glm47_exposed_v3.py`
SHA `386ba1d07bcba38c8d88509da5743443fb1330c3c866d39117f71195549f2576`를
clean/pushed `750fe09a8b7955dfe8db25f0c2e0fc589e077f36`의 고정 snapshot과 함께 한 번 실행했다.
Snapshot record SHA `0ebf959ba0b7f1333b51b74d464323c98440848009ca50fb68ab97be7891f1b1`이며
30개 원본 Git blob과 source/prompt/schema/parser/adapter/scorer 연결을 검증했다.
현재 epoch2와 과거 epoch1 완료 runtime 증거를 구분해 연결했고 frozen239 파일을 전후 대조했다.

Warmup5와 trial120의 final JSON이 모두 보존되어 첫 전체125행의 단계·판정·집계가 일치했다.
Schema120, parser118, semantic104, rawFP1/58, unsafe1/120, FN6/62, raw관측120/120이다.
Warmup은 별도5/5, 오류코드는 UNGROUNDED_REQUIREMENT2이며 timeout/truncation은0이다.
동일 모델의 반복 출력 재현성이나 unseen 자료의 품질을 입증하는 검사는 아니다.

Proof SHA `883854e2afa30a7c0c068ea24f3ec6e513eaaa5731963a8e1bb84a709754a34d`.
모델·네트워크·GPU·weight payload 호출/읽기0, 기존 평가 재생0이다.
Gold는 AUTO-GENERATED / NOT HUMAN VERIFIED이며 원본 오류/분모/threshold를 변경하지 않았다.
명백한 FAIL이므로 같은 후보 추가 반복·V2·미사용80개 호출 없이 종료했다.

실행 중 manifest 독립 검토도 setup issue0이었다. 회귀416 PASS의 source pins는 현재와 동일하며,
문서·증거 보존만으로 동일 suite를 다시 실행하지 않았다.
정확한 요청/결과/재검산/종료와 GPU3 반환 증거는
[보관본](../../evaluations/results/phase5x/exposed-native-glm47-diagnostic/README.md)에 있다.
