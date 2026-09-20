"""Explicit postcompile inspection only: no ldd, native executable or GPU calls.

Do not execute until the parent confirms all compile phases are complete.
Read-only tools: root-owned readelf and ldconfig.real -p. Output is exclusive.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys

ROOT = Path('/home/a202192020/NeuroBuild_v2')
PIN = 'f072b103714dfa1eee531f80b24512faf38e3dd2'
SOURCE = ROOT / 'var/runtime-src' / ('llama.cpp-' + PIN)
BUILD = ROOT / 'var/runtime-build/llama-f072-sm80-cu118'
BIN = BUILD / 'bin'
ORIGINAL = ROOT / 'var/reports/llama-cuda-build.json'
RELINK = ROOT / 'var/reports/llama-rpath-relink.json'
OUTPUT = 'var/reports/llama-cuda-build-verified.json'
BOOTSTRAP = ROOT / 'var/research/bootstrap_llama_source.py'
BOOTSTRAP_SHA = '5a261566bff684e90c984f25674ff778080b60dce8637f5fecc6ccac42933c75'
SYSTEM_ROOTS = (Path('/usr'), Path('/lib'), Path('/lib64'))
SAFE_ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'CUDA_VISIBLE_DEVICES': ''}
LIBRARY = re.compile(r'lib[A-Za-z0-9_+.-]+\.so(?:\.[A-Za-z0-9_+.-]+)*')


def require(condition, code):
    if not condition:
        raise ValueError(code)


def plain_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_bootstrap():
    # Importing this exact helper defines its pure validators; its main is not run.
    require(plain_hash(BOOTSTRAP) == BOOTSTRAP_SHA, 'BOOTSTRAP_HELPER_CHANGED')
    spec = importlib.util.spec_from_file_location('verified_source_bootstrap', BOOTSTRAP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(ws, path):
    relative = path.relative_to(ROOT).as_posix()
    with ws.read_file(relative) as stream:
        before = os.fstat(stream.fileno())
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
    keys = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    require(all(getattr(before, key) == getattr(after, key) for key in keys), 'FILE_CHANGED_DURING_HASH')
    return {'path': relative, 'bytes': before.st_size, 'sha256': digest}


def read_json(ws, path, maximum=8 * 1024**2):
    with ws.read_file(path.relative_to(ROOT).as_posix()) as stream:
        data = stream.read(maximum + 1)
    require(len(data) <= maximum, 'JSON_SIZE_LIMIT')
    return ws_module.strict_json(data)


def library_inventory(ws):
    real, links = {}, {}
    with ws.parent((BIN / '_check').relative_to(ROOT).as_posix()):
        for path in sorted(BIN.iterdir()):
            info = path.lstat()
            require(info.st_uid == os.getuid(), 'BUILD_OUTPUT_OWNER_MISMATCH')
            if path.name == 'llama-server':
                require(stat.S_ISREG(info.st_mode), 'SERVER_NOT_REGULAR')
                continue
            require(LIBRARY.fullmatch(path.name) is not None, 'UNEXPECTED_BUILD_BIN_ENTRY')
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(path)
                require(LIBRARY.fullmatch(target) is not None and '/' not in target, 'NONLOCAL_LIBRARY_SYMLINK')
                links[path.name] = target
            else:
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'LIBRARY_NOT_REGULAR')
                real[path.name] = identity(ws, path)
    require(real and (BIN / 'llama-server').is_file(), 'MISSING_BUILD_OUTPUTS')
    mappings = []
    resolved = {name: BIN / name for name in real}
    for name, target in links.items():
        cursor, seen = name, set()
        while cursor in links:
            require(cursor not in seen and len(seen) < 16, 'LIBRARY_SYMLINK_CYCLE')
            seen.add(cursor)
            cursor = links[cursor]
        require(cursor in real, 'DANGLING_LIBRARY_SYMLINK')
        resolved[name] = BIN / cursor
        mappings.append({'path': (BIN / name).relative_to(ROOT).as_posix(), 'target': target,
                         'real_path': (BIN / cursor).relative_to(ROOT).as_posix()})
    return list(real.values()), mappings, resolved


def system_path(path):
    """Resolve root-owned system symlinks without traversing any user's HOME."""
    require(path.is_absolute(), 'SYSTEM_PROVIDER_NOT_ABSOLUTE')
    pending, resolved, hops = list(path.parts[1:]), Path('/'), 0
    while pending:
        component = pending.pop(0)
        if component in ('', '.'):
            continue
        if component == '..':
            resolved = resolved.parent
            continue
        candidate = resolved / component
        # /etc/alternatives may occur in system tool/CUDA symlink chains only.
        allowed = any(candidate == p or candidate.is_relative_to(p) or p.is_relative_to(candidate)
                      for p in (*SYSTEM_ROOTS, Path('/etc/alternatives'), Path('/sbin')))
        require(allowed and not {'stubs', 'compat'}.intersection(candidate.parts), 'UNSAFE_SYSTEM_PROVIDER')
        info = candidate.lstat()
        require(info.st_uid == 0 and (stat.S_ISLNK(info.st_mode) or not (info.st_mode & 0o022)),
                'SYSTEM_PROVIDER_NOT_ROOT_OWNED')
        if stat.S_ISLNK(info.st_mode):
            hops += 1
            require(hops <= 32, 'SYSTEM_SYMLINK_CYCLE')
            target = Path(os.readlink(candidate))
            if target.is_absolute():
                resolved = Path('/')
                pending = list(target.parts[1:]) + pending
            else:
                pending = list(target.parts) + pending
        else:
            require(not pending or stat.S_ISDIR(info.st_mode), 'SYSTEM_PROVIDER_PARENT_NOT_DIRECTORY')
            resolved = candidate
    require(any(resolved.is_relative_to(p) for p in (*SYSTEM_ROOTS, Path('/sbin'))), 'SYSTEM_PROVIDER_ESCAPE')
    return resolved


def tool_output(tool, *arguments):
    executable = system_path(Path(tool))
    require(executable.is_file(), 'MISSING_INSPECTION_TOOL')
    result = subprocess.run([str(executable), *arguments], stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, encoding='utf-8', errors='strict',
                            timeout=30, check=True, env=SAFE_ENV, cwd=ROOT)
    require(len(result.stdout) <= 2 * 1024**2 and len(result.stderr) <= 65536, 'TOOL_OUTPUT_LIMIT')
    require(not result.stderr.strip(), 'ELF_INSPECTION_WARNING')
    return result.stdout


def parse_dynamic(text):
    tags = {'NEEDED': [], 'RPATH': [], 'RUNPATH': [], 'SONAME': []}
    for line in text.splitlines():
        match = re.search(r'\((NEEDED|RPATH|RUNPATH|SONAME)\).*\[([^\]]*)\]', line)
        if match:
            tags[match[1]].append(match[2])
    require(all(len(tags[key]) <= 1 for key in ('RPATH', 'RUNPATH', 'SONAME')), 'DUPLICATE_DYNAMIC_TAG')
    require(all(LIBRARY.fullmatch(name) is not None or re.fullmatch(r'ld-linux-x86-64\.so\.2', name)
                for name in tags['NEEDED']), 'UNSAFE_NEEDED_NAME')
    require(len(tags['NEEDED']) == len(set(tags['NEEDED'])), 'DUPLICATE_NEEDED')
    return tags


def elf(path):
    header = tool_output('/usr/bin/readelf', '--wide', '--file-header', '--program-headers', str(path))
    require(re.search(r'Class:\s+ELF64\b', header) and re.search(r'Machine:\s+Advanced Micro Devices X86-64', header),
            'UNEXPECTED_ELF_ARCHITECTURE')
    interpreter = re.findall(r'\[Requesting program interpreter: ([^\]]+)\]', header)
    require(len(interpreter) <= 1, 'MULTIPLE_INTERPRETERS')
    tags = parse_dynamic(tool_output('/usr/bin/readelf', '--wide', '--dynamic', str(path)))
    return {'needed': tags['NEEDED'], 'rpath': tags['RPATH'], 'runpath': tags['RUNPATH'],
            'soname': tags['SONAME'][0] if tags['SONAME'] else None,
            'interpreter': interpreter[0] if interpreter else None}


def loader_cache():
    text = tool_output('/sbin/ldconfig.real', '-p')
    cache = {}
    for line in text.splitlines():
        match = re.fullmatch(r'\s*(\S+) \(([^)]+)\) => (\S+)\s*', line)
        if match and 'x86-64' in match[2]:
            cache.setdefault(match[1], []).append(Path(match[3]))
    require(cache, 'EMPTY_SYSTEM_LOADER_CACHE')
    return cache


def search_directories(values, origin):
    directories = []
    for value in values:
        for entry in value.split(':'):
            require(bool(entry), 'EMPTY_RPATH_COMPONENT')
            entry = entry.replace('${ORIGIN}', str(origin)).replace('$ORIGIN', str(origin))
            require('$' not in entry, 'UNSUPPORTED_RPATH_EXPANSION')
            path = Path(entry)
            require(path.is_absolute(), 'RELATIVE_RPATH')
            if path == BIN:
                directories.append(path)
            else:
                resolved = system_path(path)
                require(resolved.is_dir(), 'RPATH_NOT_DIRECTORY')
                directories.append(resolved)
    return directories


def linkage(inventory, names):
    cache = loader_cache()
    work = [(BIN / 'llama-server', [])] + [(ROOT / row['path'], []) for row in inventory]
    seen, records = {}, []
    while work:
        path, inherited = work.pop(0)
        key = str(path)
        if key in seen:
            require(seen[key] == inherited, 'AMBIGUOUS_INHERITED_RPATH')
            continue
        require(len(seen) < 128, 'ELF_DEPENDENCY_LIMIT')
        seen[key] = inherited
        info = elf(path)
        own_rpath = search_directories(info['rpath'], path.parent) if not info['runpath'] else []
        runpath = search_directories(info['runpath'], path.parent)
        inherited_next = own_rpath + inherited
        directories = inherited_next + runpath
        resolutions = []
        for needed in info['needed']:
            selected = None
            for directory in directories:
                candidate = directory / needed
                if directory == BIN:
                    selected = names.get(needed)
                elif candidate.exists() or candidate.is_symlink():
                    selected = system_path(candidate)
                if selected is not None:
                    break
            if selected is None:
                candidates = cache.get(needed, [])
                require(candidates, 'NEEDED_PROVIDER_NOT_FOUND:' + needed)
                selected = system_path(candidates[0])
            require(selected.is_file(), 'NEEDED_PROVIDER_NOT_REGULAR')
            resolutions.append({'needed': needed, 'provider': str(selected),
                                'provider_bytes': selected.stat().st_size})
            work.append((selected, inherited_next))
        if info['interpreter']:
            loader = system_path(Path(info['interpreter']))
            require(loader.is_file(), 'INTERPRETER_NOT_REGULAR')
            work.append((loader, []))
        records.append({'path': key, **info, 'resolved_needed': resolutions})
    require(any(row['soname'] == 'libcuda.so.1' for row in records), 'REAL_SYSTEM_DRIVER_PROVIDER_MISSING')
    return {'method': 'STATIC_READELF_RPATH_RUNPATH_SYSTEM_CACHE', 'ld_library_path': None,
            'limitations': 'Expected loader paths only; no executable/ldd/dlopen/GPU validation; hardware-capability cache alternatives not exercised',
            'objects': records}


def parse_cmake_cache(text):
    """Parse one cache assignment per physical line, never across comments."""
    cache = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith(('#', '//')):
            continue
        match = re.fullmatch(r'([^:=\r\n]+):(BOOL|FILEPATH|PATH|STRING|INTERNAL|STATIC|UNINITIALIZED)=(.*)', line)
        require(match is not None and match[1] == match[1].strip(), 'MALFORMED_CMAKE_CACHE_LINE')
        key, _, value = match.groups()
        require(key not in cache, 'DUPLICATE_CMAKE_CACHE_KEY')
        cache[key] = value
    return cache


def compile_evidence(ws, original):
    command_path = BUILD / 'compile_commands.json'
    require(identity(ws, command_path)['sha256'] == original['compile_commands_sha256'], 'COMPILE_COMMANDS_CHANGED')
    commands = read_json(ws, command_path)
    require(type(commands) is list and 0 < len(commands) <= 10000, 'INVALID_COMPILE_COMMANDS')
    cuda_count = 0
    for entry in commands:
        source = Path(entry['file'])
        require(source.is_relative_to(SOURCE) or source.is_relative_to(BUILD), 'COMPILE_SOURCE_OUTSIDE_PINNED_BUILD')
        require(Path(entry['directory']).is_relative_to(BUILD), 'COMPILE_WORKDIR_OUTSIDE_BUILD')
        args = shlex.split(entry['command'])
        require(not any(token.startswith('@') for token in args), 'UNINSPECTED_COMPILER_RESPONSE_FILE')
        if source.suffix == '.cu':
            cuda_count += 1
            require(source.is_relative_to(SOURCE) and args[0] == '/usr/local/cuda/bin/nvcc', 'WRONG_CUDA_COMPILER_OR_SOURCE')
            generated = [arg for arg in args if arg.startswith('--generate-code=')]
            require(generated == ['--generate-code=arch=compute_80,code=[sm_80]'], 'CUDA_ARCHITECTURE_CHANGED')
            require(not any(arg.startswith(('-arch', '--gpu-architecture', '-code', '--gpu-code', '-gencode'))
                            for arg in args), 'ADDITIONAL_CUDA_ARCHITECTURE_FLAG')
    require(cuda_count > 0, 'NO_CUDA_COMPILATION')
    cache_path = BUILD / 'CMakeCache.txt'
    with ws.read_file(cache_path.relative_to(ROOT).as_posix()) as stream:
        cache = parse_cmake_cache(stream.read().decode())
    for key, expected in original['settings'].items():
        require(cache.get(key) == expected, 'CMAKE_SETTING_CHANGED:' + key)
    with ws.read_file((BUILD / 'common/build-info.cpp').relative_to(ROOT).as_posix()) as stream:
        info = stream.read().decode()
    require('int LLAMA_BUILD_NUMBER = 0;' in info and 'char const * LLAMA_COMMIT = "' + PIN + '";' in info,
            'LLAMA_BUILD_IDENTITY_CHANGED')
    with ws.read_file((BUILD / 'ggml/ggml-config.cmake').relative_to(ROOT).as_posix()) as stream:
        ggml = re.findall(r'set\(GGML_BUILD_COMMIT "([^"]+)"\)', stream.read().decode())
    require(ggml == ['unknown'], 'UNEXPECTED_GGML_BUILD_STRING')
    return {'total_command_count': len(commands), 'cuda_command_count': cuda_count,
            'cuda_generate_code': 'arch=compute_80,code=[sm_80]', 'ptx_or_other_architecture_requested': False,
            'llama_build_commit': PIN, 'llama_build_number': 0, 'ggml_build_commit': ggml[0],
            'ggml_identity_limitation': 'Source archive has no Git history; enclosing repository excluded; GGML string unknown, full source tree pinned independently',
            'cmake_cache_sha256': identity(ws, cache_path)['sha256'],
            'generated_build_info_sha256': identity(ws, BUILD / 'common/build-info.cpp')['sha256']}


def main():
    global ws_module
    require(len(sys.argv) == 1 and os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'EXPLICIT_CPU_ONLY_INVOCATION_REQUIRED')
    require(Path(sys.prefix) == ROOT / '.conda', 'WRONG_PYTHON_ENVIRONMENT')
    ws_module = load_bootstrap()
    ws = ws_module.Workspace()
    try:
        ws.absent(OUTPUT)
        initial = read_json(ws, ORIGINAL)
        initial_identity = identity(ws, ORIGINAL)
        original = read_json(ws, RELINK)
        original_identity = identity(ws, RELINK)
        require(initial['status'] == 'COMPILE_PASS_NOT_RUNTIME_VALIDATED'
                and original['kind'] == 'LLAMA_SOURCE_IMMUTABLE_RPATH_RELINK'
                and original['original_compile_report_sha256'] == initial_identity['sha256'],
                'ORIGINAL_AND_RELINK_REPORT_BINDING')
        require([phase['name'] for phase in original['relink_phases']] == ['reconfigure-rpath', 'relink-server']
                and all(phase['exit_code'] == 0 and phase['native_cleanup']['cleanup_complete'] is True
                        and phase['native_cleanup']['native_reaped'] is True for phase in original['relink_phases']),
                'RELINK_NOT_SUCCESSFULLY_COMPLETE')
        require(original['status'] == 'COMPILE_PASS_NOT_RUNTIME_VALIDATED' and original['source_pin'] == PIN,
                'COMPILE_NOT_SUCCESSFULLY_COMPLETE')
        require(original['cuda_visible_devices'] == '' and original['gpu_queries_or_execution'] == 'NOT_REQUESTED',
                'ORIGINAL_NOT_CPU_ONLY')
        require([phase['name'] for phase in original['phases']] == ['configure', 'ggml-cuda', 'llama-server'], 'INCOMPLETE_PHASES')
        require(all(phase['exit_code'] == 0 and phase['native_cleanup']['native_reaped'] is True
                    and phase['native_cleanup']['cleanup_complete'] is True for phase in original['phases']), 'UNCLEAN_COMPILE_EXIT')
        bootstrap_path = ROOT / ws_module.REPORT
        require(identity(ws, bootstrap_path)['sha256'] == original['bootstrap_report_sha256'], 'SOURCE_REPORT_CHANGED')
        bootstrap = read_json(ws, bootstrap_path)
        require(bootstrap['status'] == 'PASS' and bootstrap['llama_commit'] == PIN, 'INVALID_SOURCE_REPORT')
        payloads = {}
        for name in ('commit.json', 'tree.json'):
            path = ROOT / ws_module.DOWNLOAD_DIR / name
            proof = next(row for row in bootstrap['downloads'] if row['path'] == path.relative_to(ROOT).as_posix())
            require(identity(ws, path)['sha256'] == proof['sha256'], 'TREE_METADATA_CHANGED')
            payloads[name] = read_json(ws, path)
        entries = ws_module.validate_tree(payloads['commit.json'], payloads['tree.json'])
        source = ws_module.verify_source(ws, entries)
        require(source == bootstrap['source_verification'], 'POSTBUILD_SOURCE_TREE_CHANGED')
        binary = identity(ws, BIN / 'llama-server')
        require(binary['sha256'] == original['binary_sha256'], 'SERVER_BINARY_CHANGED')
        inventory, links, names = library_inventory(ws)
        compilation = compile_evidence(ws, original)
        dynamic = linkage(inventory, names)
        # Recheck report/binary/library bytes after external metadata readers.
        require(identity(ws, ORIGINAL) == initial_identity, 'ORIGINAL_REPORT_CHANGED_DURING_VERIFICATION')
        require(identity(ws, RELINK) == original_identity, 'RELINK_REPORT_CHANGED_DURING_VERIFICATION')
        require(identity(ws, BIN / 'llama-server') == binary, 'BINARY_CHANGED_DURING_VERIFICATION')
        require(library_inventory(ws)[:2] == (inventory, links), 'LIBRARIES_CHANGED_DURING_VERIFICATION')
        output = dict(original)
        output.update(verification_kind='LLAMA_POSTCOMPILE_STATIC_VERIFICATION',
                      verified_at_utc=datetime.now(timezone.utc).isoformat(),
                      original_compile_report_sha256=initial_identity['sha256'],
                      rpath_relink_report_sha256=original_identity['sha256'],
                      verifier_sha256=identity(ws, Path(__file__).absolute())['sha256'],
                      source_verifier_sha256=BOOTSTRAP_SHA, source_reverification=source,
                      runtime_dependencies=inventory, runtime_dependency_symlinks=links,
                      compile_verification=compilation, elf_linkage=dynamic,
                      native_binary_executed=False, weights_read=False,
                      inspection_tools=['/usr/bin/readelf', '/sbin/ldconfig.real -p'])
        ws.put_json(OUTPUT, output)
        print(json.dumps({'status': output['status'], 'report': OUTPUT,
                          'runtime_dependency_count': len(inventory), 'source_blobs': source['verified_blobs']}))
    finally:
        ws.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'FAILED', 'error_type': type(error).__name__, 'error': str(error)}))
        raise SystemExit(1)
