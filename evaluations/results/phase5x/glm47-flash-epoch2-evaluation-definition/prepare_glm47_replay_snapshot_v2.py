"""Prepare a future frozen GLM replay snapshot only; never runs replay or inference.

Invoke only with the clean checkpoint and independent freeze/replay pins supplied
by root. Dataset is copied/hash-checked as opaque bytes; no JSONL parser exists.
Partial output is preserved on failure and an existing directory is never reused.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

ROOT = Path('/home/a202192020/NeuroBuild_v2')
OUT = ROOT / 'var/review-tools/glm47-exposed-review'
FREEZE = 'evaluations/hardening_v1_exposed_native_glm47_diagnostic_freeze.json'
REPLAY = 'var/research/replay_native_glm47_exposed_v3.py'
VARIANT = 'glm47-flash-gguf-nonthinking-v1'
PATHS = ('evaluations/hardening_v1_exposed_native_glm47_diagnostic_freeze.json', 'evaluations/requirement_hardening_v1_exposed_regression.jsonl', 'evaluations/results/phase5x/glm47-flash-preparation/metadata/provenance.json', 'evaluations/results/phase5x/glm47-flash-preparation/metadata/upstream/chat_template.jinja', 'prompts/requirement_generation_v2_v2.txt', 'runtime/models/glm47-flash-q4-k.json', 'schemas/requirement_generation_v2.schema.json', 'schemas/requirement_generation_v2_decision_branches.schema.json', 'schemas/semantic_requirement.schema.json', 'scripts/evaluate_requirements.py', 'scripts/gpu_preflight.py', 'scripts/llama_server.py', 'scripts/model_guard.py', 'scripts/native_model_bootstrap.py', 'scripts/verify_model_listeners.py', 'src/neurobuild/__init__.py', 'src/neurobuild/application/__init__.py', 'src/neurobuild/application/requirement_facts.py', 'src/neurobuild/application/requirement_generation.py', 'src/neurobuild/application/requirements.py', 'src/neurobuild/application/workflow.py', 'src/neurobuild/domain/__init__.py', 'src/neurobuild/domain/contracts.py', 'src/neurobuild/domain/errors.py', 'src/neurobuild/infrastructure/__init__.py', 'src/neurobuild/infrastructure/artifacts.py', 'src/neurobuild/infrastructure/ifc_engine.py', 'src/neurobuild/infrastructure/local_model.py', 'src/neurobuild/infrastructure/persistence.py', 'src/neurobuild/infrastructure/staged_requirement.py')


def require(ok, code):
    if not ok:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    result = subprocess.run(['git', '--no-replace-objects', *args], cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=30, check=False)
    require(result.returncode == 0, 'GIT_COMMAND_FAILED')
    return result.stdout


def source_bytes(name):
    path = ROOT
    for part in Path(name).parts:
        path /= part
        info = path.lstat()
        require(not stat.S_ISLNK(info.st_mode) and info.st_uid == os.getuid(), 'SOURCE_PATH_NOT_OWNED')
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= 2*1024**2,
            'SOURCE_FILE_INVALID')
    return path.read_bytes()


def committed_blob(commit, name):
    rows = git('ls-tree', '-lz', commit, '--', name).split(b'\0')
    require(len(rows) == 2 and rows[-1] == b'', 'GIT_TREE_ENTRY_COUNT')
    meta, entry = rows[0].split(b'\t', 1)
    mode, kind, oid, size = meta.split()
    require(entry.decode() == name and kind == b'blob' and mode in (b'100644', b'100755'), 'GIT_TREE_ENTRY_INVALID')
    require(int(size) <= 2*1024**2, 'BLOB_TOO_LARGE')
    raw = git('show', commit + ':' + name)
    require(len(raw) == int(size), 'GIT_BLOB_SIZE')
    actual_oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    require(actual_oid == oid.decode(), 'GIT_OBJECT_HASH')
    require(source_bytes(name) == raw, 'CURRENT_FILE_DIFFERS_FROM_CHECKPOINT')
    return raw, {'oid': actual_oid, 'mode': mode.decode(), 'bytes': len(raw)}


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--freeze-sha256', required=True)
    parser.add_argument('--replay-sha256', required=True)
    args = parser.parse_args()
    require(re.fullmatch('[a-f0-9]{40}', args.source_commit) is not None, 'COMMIT_FORMAT')
    require(all(re.fullmatch('[a-f0-9]{64}', s) for s in (args.freeze_sha256,args.replay_sha256)), 'HASH_FORMAT')
    require(git('rev-parse', 'HEAD').decode().strip() == args.source_commit, 'HEAD_NOT_EXPECTED_COMMIT')
    require(git('status', '--porcelain', '--untracked-files=normal') == b'', 'WORKTREE_NOT_CLEAN')
    require(not OUT.exists() and not OUT.is_symlink(), 'SNAPSHOT_OUTPUT_ALREADY_EXISTS')
    require(len(PATHS) == len(set(PATHS)) == 30, 'PATH_COUNT')
    require(sha(source_bytes(REPLAY)) == args.replay_sha256, 'REPLAY_HELPER_HASH')
    freeze_raw, _ = committed_blob(args.source_commit, FREEZE)
    require(sha(freeze_raw) == args.freeze_sha256, 'FREEZE_HASH')
    freeze = json.loads(freeze_raw)  # Metadata only; dataset is never decoded/parsed.
    require(freeze['candidate_variant'] == VARIANT and freeze['sha256'][REPLAY] == args.replay_sha256,
            'FROZEN_CANDIDATE_REPLAY_BINDING')
    blobs, hashes, objects = {}, {}, {}
    for name in PATHS:
        raw, obj = committed_blob(args.source_commit, name)
        hashed = sha(raw)
        if name in freeze['sha256']:
            require(hashed == freeze['sha256'][name], 'FROZEN_SOURCE_HASH')
        blobs[name], hashes[name], objects[name] = raw, hashed, obj
    require(sum(len(v) for v in blobs.values()) <= 8*1024**2, 'TOTAL_SNAPSHOT_TOO_LARGE')
    for parent in (ROOT, ROOT/'var', ROOT/'var/review-tools'):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid(), 'OUTPUT_PARENT_INVALID')
    OUT.mkdir()
    snapshot = OUT / 'source_snapshot'; snapshot.mkdir()
    for name, raw in blobs.items():
        dest = snapshot / name; dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream:
            stream.write(raw)
        dest.chmod(int(objects[name]['mode'], 8) & 0o777)
        require(sha(dest.read_bytes()) == hashes[name], 'COPIED_SOURCE_HASH')
    result = {
        'source_snapshot_commit': args.source_commit,
        'provenance': 'Exact git show blob bytes from pinned clean commit. Prior EXAONE30 closure adapted only at candidate freeze/manifest/provenance/template paths. GLM template is the archived official original, with no override. Exposed120 dataset copied as opaque bytes without parsing or output. No result, V2/unused holdout body, weight, binary, environment, replay or model invocation.',
        'native_diagnostic_freeze_sha256': args.freeze_sha256,
        'replay_helper_sha256': args.replay_sha256,
        'sha256': hashes, 'git_blobs': objects,
    }
    write_json(snapshot/'snapshot.json',result)
    require(git('rev-parse','HEAD').decode().strip() == args.source_commit and
            git('status','--porcelain','--untracked-files=normal') == b'', 'CHECKPOINT_CHANGED_DURING_SNAPSHOT')
    require(all(sha(source_bytes(name)) == hashed for name,hashed in hashes.items()), 'SOURCE_CHANGED_DURING_SNAPSHOT')
    require(sha(source_bytes(REPLAY)) == args.replay_sha256, 'REPLAY_CHANGED_DURING_SNAPSHOT')
    prep = {'kind':'GLM47_REPLAY_SOURCE_SNAPSHOT_PREPARATION','status':'PREPARED_REPLAY_NOT_RUN',
        'created_at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':args.source_commit,
        'snapshot_path':str(snapshot.relative_to(ROOT)),'snapshot_sha256':sha((snapshot/'snapshot.json').read_bytes()),
        'file_count':len(PATHS),'file_bytes':sum(len(v) for v in blobs.values()),
        'git_blob_sha1_and_sha256_verified':True,'current_files_match_commit':True,
        'freeze_path':FREEZE,'freeze_sha256':args.freeze_sha256,'replay_helper_path':REPLAY,
        'replay_helper_sha256':args.replay_sha256,'snapshot_builder_sha256':sha(Path(__file__).read_bytes()),
        'dataset_bytes_copied_without_parsing':True,'result_reads':0,'actual_replays':0,
        'tests_run':0,'model_calls':0,'http_calls':0,'gpu_calls':0,'native_invocations':0}
    write_json(OUT/'preparation.json',prep)
    print(json.dumps({'status':prep['status'],'snapshot_path':prep['snapshot_path'],
                      'snapshot_sha256':prep['snapshot_sha256'],'file_count':len(PATHS)},sort_keys=True))


if __name__ == '__main__':
    main()
