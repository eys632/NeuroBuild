# Gemma4-12B QAT 사전 준비

공식 metadata와 조건부 구조·자원 검토를 마쳤고 고정 가중치 다운로드는 통과했다.
**Header/CPU 증거 승계·GPU runtime·모델 품질은 아직 미검증**이다.
Phase5.x 미완료·모델 미채택이며 GPU 모델 서버는 종료 상태다.
[후보·최소 검증 계획](../gemma4_12b_candidate.md).

## 확인한 사실

Official GGUF revision29d097773436b69ff9feafd636ab4cf873786537의 README와
6,975,879,296B weight를 크기·전체 SHA로 검증했다. 다운로드 exit0/stderr0, verified files2다.
Download receipt SHA `eebba0743c8304a7670c66b5905e8b34b40946d6e0cfb507c0aece79645a379f`.
고정 f072 binary나 환경을 재설치·재빌드하지 않았으며 다운로드 중 GPU/native model 호출은0회다.
Generic guardian의 `native_pid` 필드는 이 다운로드 child를 가리키며 모델 실행 증거가 아니다.

사전 disk 여유로는 다운로드 후20GiB+512MiB reserve가 부족했다.
GLM 결과95ebee2 push 뒤 종료된 own GLM cache 한 파일만 회수했다.
Exact manifest·STOPPED/exit0/reaped·header·소유 UID·regular/single-link·inode/mtime/ctime·전체 SHA,
project lock·접근 가능한 own FD/maps의 미사용 검사를 통과했다. 다른 사용자 내용에는 접근하지 않았다.
Same-UID 로그인 infrastructure2건의 maps/FD permission 한계는 기존 명시 식별과 함께 기록했다.
삭제 범위는 재다운로드 가능한 weight18,244,193,920B 한 개이며 모든 metadata·평가·복원 manifest는 보존했다.
Cleanup receipt SHA `f8f255e09d1b33fe9641beeda8d90069b8dd1f6d78d5013563e06527c2f60d88`.
회수 후 free43,746,529,280B, 새 다운로드 중 최소 free36,766,171,136B로 floor22,011,707,392B를 유지했다.

## 변경과 회귀

Evaluator의 `build_manifest`에 기존 Gemma4 profile과 공식12B/Q4_0의 exact pair만 추가했다.
Gemma31과 다른 세 profile의 기존 제한은 유지한다. Client·prompt·schema·parser·scorer 함수는 변경하지 않았다.
새 정상 identity 경계1개와 잘못된 publisher/model suffix/quantization/다른 profile6조합을 검증하는 test를 추가했다.

실제 PostgreSQL/IfcOpenShell, headless/empty CUDA 환경의 전체 **418 tests PASS, skip0,21.412초**다.
이번 production 변경 후 첫 회귀이며 이전416 PASS를 별도 새 실행이라고 재사용하지 않았다.
Log SHA `2652a0b4cc990b9e97cfbe1a9840c00232b2c5036e1c1783a964d209b6d73916`.
Evaluator SHA `48b919e8ef9ec41ee2765c66fd5d752202248f53502616ec01d687be87f42f24`,
test SHA `1bb28fd6cc1b208e21a2693933febd337958055dc90d5d566c91dbdefb470fe7`.
모델 품질·완료125개 평가·public/vocab/context corpus는 이 회귀에서 재실행하지 않았다.

## 한계와 다음 단계

Metadata의 tokenizer/template 동일성만으로 실제 GGUF tokenizer나 품질을 승인하지 않는다.
48층 구조와 payload/tensor coverage, 추가 suppressed ID2개, 기존 CPU 증거의 입력 동등성을 먼저 확인한다.
공식 QAT repo에 source index/정확한 conversion revision은 없어 해당 검증의 한계를 기록했다.
Header가 사전 조건과 다르면 원본 FAIL을 보존하고 원인을 검토한다.
원본 GGUF나 gold를 수정해 통과시키지 않는다. 비필수 runtime 최적화는 future optimization이다.

[준비 증거](../../evaluations/results/phase5x/gemma4-12b-preparation/README.md).
