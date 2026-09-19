#!/usr/bin/env python3
"""Download a pinned public model manifest into this project's ignored storage."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
RESERVE = 20 * 1024**3


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(manifest_path):
    manifest = json.loads(manifest_path.read_text())
    model, revision = manifest['model_id'], manifest['revision']
    if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+', model) or not re.fullmatch(r'[a-f0-9]{40}', revision):
        raise ValueError('Invalid pinned public model identity')
    storage = (ROOT / 'var' / 'models').resolve()
    destination = storage / model.replace('/', '--') / revision
    if not storage.is_relative_to(ROOT.resolve()) or not destination.resolve().is_relative_to(storage):
        raise ValueError('Model storage must stay within the project')
    metadata = destination / 'neurobuild-manifest.json'
    if metadata.is_symlink() or (metadata.exists() and not metadata.is_file()):
        raise ValueError('Model manifest must be a regular local file')
    if metadata.exists() and json.loads(metadata.read_text()) != manifest:
        raise ValueError('Existing model metadata differs from its manifest')
    files = manifest['files']
    names = set()
    needed = 0
    for entry in files:
        name = entry['name']
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name) or name in names
                or name == 'neurobuild-manifest.json' or name.endswith('.part')):
            raise ValueError('Invalid or duplicate model filename')
        names.add(name)
        if type(entry['bytes']) is not int or entry['bytes'] <= 0 or not re.fullmatch(r'[a-f0-9]{64}', entry['sha256']):
            raise ValueError('Every model file needs a positive size and SHA256')
        target = destination / name
        partial = target.with_suffix(target.suffix + '.part')
        if any(path.is_symlink() or (path.exists() and not path.is_file()) for path in (target, partial)):
            raise ValueError('Model files must be regular local files')
        if target.exists():
            if target.stat().st_size != entry['bytes'] or digest(target) != entry['sha256']:
                raise ValueError('Existing model file differs from its manifest')
        else:
            needed += entry['bytes']
    destination.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(destination).free < needed + RESERVE:
        raise RuntimeError('Insufficient disk space for model plus 20 GiB reserve')
    for entry in files:
        target = destination / entry['name']
        if target.exists():
            continue
        if shutil.disk_usage(destination).free < entry['bytes'] + RESERVE:
            raise RuntimeError('Free disk space decreased below the download budget')
        partial = target.with_suffix(target.suffix + '.part')
        url = f'https://huggingface.co/{model}/resolve/{revision}/{entry["name"]}'
        print(json.dumps({'downloading': entry['name'], 'bytes': entry['bytes']}), flush=True)
        subprocess.run(['curl', '--disable', '--fail', '--location', '--proto', '=https', '--proto-redir', '=https',
                        '--retry', '3', '--connect-timeout', '30', '--max-time', '1800',
                        '--continue-at', '-', '--output', str(partial), url], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if partial.stat().st_size != entry['bytes'] or digest(partial) != entry['sha256']:
            raise ValueError('Downloaded model file failed size or SHA256 verification')
        partial.replace(target)
        print(json.dumps({'verified': entry['name'], 'sha256': entry['sha256']}), flush=True)
    if not metadata.exists():
        fd, name = tempfile.mkstemp(prefix='.manifest-', dir=destination)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(manifest, stream, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.link(name, metadata)  # no overwrite, including a competing symlink
        finally:
            os.unlink(name)
    print(json.dumps({'model_path': str(destination), 'verified_files': len(files)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    download(args.manifest)
