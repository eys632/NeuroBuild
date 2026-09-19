# Git 조사 및 공통 v2 운영

2026-09-19 GitHub `https://github.com/eys632/NeuroBuild.git`를 읽기 전용으로 조사했다.
`git ls-remote --symref ... HEAD 'refs/heads/*'` 결과 기본 branch와 유일한 remote branch는 `main`이었다.
HEAD는 `09145974c17d1a09abdd2c48863e940fe68678b9`이며 기존 구현 정리 commit이다.

| 최근 이력 | 내용 |
|---|---|
| 0914597 | 기존 구현내용 v1으로 정리 |
| c7a28d5 | Add ver_th from neurobuild_real_v2 |
| dbcea6f | Add root README for repository layout |
| 73cd81d | Add origin and FineTuning folders |
| a47cee3 | Initial commit |

기존 tree는 `NeuroBuild_v1/`과 `NeuroBuild_v2/readme.md`(2 bytes)로 구성됐다.
완전한 기존 v2 복구자료가 있다고 가정하지 않는다. source는 참고자료로만 보존하고 실행/import하지 않는다.
현재 clone의 `origin` fetch/push URL은 동일 HTTPS 주소다. remote write 인증/권한은 검증하지 않았다.

## 결정

`origin/main`을 부모로 하는 **공통 local `v2`**를 만들었다. main 및 원격의 기존 branch를 수정하지 않았다.
orphan branch, history rewrite, 기존 데이터 삭제, force push를 사용하지 않는다.
새 Phase0 파일은 checkout 최상위에 추가하며 legacy tree는 그대로 보존한다.
두 서버는 이 공통v2의 동일 commit을 사용한다. 서버별 장기 branch는 만들지 않는다.

최초 clone은 `--filter=blob:none --no-checkout --single-branch --branch main`으로 metadata부터 조사하고,
`v2` checkout에서 기존 tree를 보존했다. 최종 checkout은 sparse가 아니다.
기능 개발 시 필요하면 짧은 `feature/...`를 v2에서 만들고 공통 branch에 통합한다.

## 이번 milestone 상태

Phase0 문서·설정·진단 도구·synthetic seed를 검토하고 stage한다.
조사 시 `git config --get user.name`, `git config --get user.email`은 모두 비어 있었다.
사용자의 작성자 정보를 추측하거나 기존 commit 작성자로 가장하지 않는다.
정보가 제공되면 이 repository에만 작성자를 설정하고 의미 있는 milestone commit을 만들 수 있다.
현재 원격v2 생성/push는 수행하지 않았으므로 **이번 기반 파일은 아직 GitHub 백업 완료가 아니다**.

권장 commit message: `chore: establish cross-server NeuroBuild v2 phase 0 foundation`.
검토 명령:

```sh
git status --short --branch
git diff --cached --check
git diff --cached --stat
git diff --cached --name-status
```

작성자 설정과 검토가 완료된 다음 local commit, 이후 인증된 사용자가 공통 branch를 push하는 순서다.
사용할 push 명령은 `git push -u origin v2`이며 force 옵션을 붙이지 않는다. 이번 작업에서는 실행하지 않았다.
remote가 바뀌었다면 fetch/차이를 먼저 확인하고 기존 작업을 덮어쓰지 않는다.

다른 서버의 **새 clone**은 remotev2 push 후 `git clone --branch v2 https://github.com/eys632/NeuroBuild.git`로 준비할 수 있다.
기존 clone에 미커밋 작업이 있으면 보존하고 checkout 전에 조사한다.
본 clone은 처음에 single-branch였으므로 원격v2를 명시적으로 가져올 경우 다음처럼 한다.

```sh
git fetch origin refs/heads/v2:refs/remotes/origin/v2
```

Git에는 environment/weight/cache/DB/user IFC/runtime artifact/local secret을 넣지 않는다.
`.gitignore`는 새 파일의 실수를 줄이는 장치이며 과거 commit을 자동 정리하거나 이미 tracked인 자료를 지우는 기능이 아니다.
과거 tree의 전면 보안 audit은 이번 범위가 아니며, 새 파일의 제외/secret 여부와 legacy 미변경을 확인한다.
user data는 별도 backup/restore 대상이며 Git push가 이를 보호하지 않는다.
