"""In-memory original GLM template reference; pipe output must never be archived."""
from pathlib import Path
import hashlib, json, sys, os, resource

ROOT = Path('/home/a202192020/NeuroBuild_v2')
PIN = 'd63ad536c3c81880043e22ec7fd08db42b4d8fb7c89c7138bc562bfa25281375'

def main():
    assert Path(sys.prefix) == ROOT / '.conda-vllm'
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == '' and len(sys.argv) == 1
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    import jinja2
    from jinja2.sandbox import ImmutableSandboxedEnvironment
    raw = sys.stdin.buffer.read(1024 * 1024 + 1)
    assert len(raw) <= 1024 * 1024
    payload = json.loads(raw)
    assert set(payload) == {'original_template', 'variables'}
    assert hashlib.sha256(payload['original_template'].encode()).hexdigest() == PIN
    assert len(payload['variables']) == 20
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True,
                                       extensions=['jinja2.ext.loopcontrols'])
    def fail(_): raise jinja2.TemplateError('PUBLIC_TEMPLATE_ERROR')
    def tojson(x, ensure_ascii=False, indent=None, separators=None, sort_keys=False):
        return json.dumps(x, ensure_ascii=ensure_ascii, indent=indent,
                          separators=separators, sort_keys=sort_keys)
    env.globals['raise_exception'] = fail
    env.filters['tojson'] = tojson
    original = env.from_string(payload['original_template'])
    rows = [original.render(**variables) for variables in payload['variables']]
    assert all(len(row.encode()) <= 65536 for row in rows)
    assert 'torch' not in sys.modules and 'transformers' not in sys.modules
    sys.stdout.write(json.dumps({'rendered': rows, 'jinja2_version': jinja2.__version__,
                                'reference_cases': 20, 'template_override_used': False,
                                'torch_imported': False}, ensure_ascii=False))

if __name__ == '__main__':
    try: main()
    except Exception as exc:
        # Never print a Jinja exception containing source text.
        sys.stdout.write(json.dumps({'status': 'FAIL', 'error_type': type(exc).__name__}))
        raise SystemExit(1)
