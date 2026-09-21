"""In-memory public template reference; stdout is a pipe, never a saved artifact."""
from pathlib import Path
import json,sys,os,resource
import jinja2
from jinja2.sandbox import ImmutableSandboxedEnvironment
ROOT=Path('/home/a202192020/NeuroBuild_v2')
assert Path(sys.prefix)==ROOT/'.conda-vllm' and os.environ.get('CUDA_VISIBLE_DEVICES')==''
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
assert len(sys.argv)==1
payload=json.loads(sys.stdin.buffer.read(1024*1024))
env=ImmutableSandboxedEnvironment(trim_blocks=True,lstrip_blocks=True,extensions=['jinja2.ext.loopcontrols'])
def fail(message):raise jinja2.TemplateError('PUBLIC_TEMPLATE_ERROR')
def tojson(x,ensure_ascii=False,indent=None,separators=None,sort_keys=False):
 return json.dumps(x,ensure_ascii=ensure_ascii,indent=indent,separators=separators,sort_keys=sort_keys)
env.globals['raise_exception']=fail;env.filters['tojson']=tojson
original=env.from_string(payload['original_template']);derived=env.from_string(payload['derived_template'])
rows=[]
for variables in payload['variables']:
 before=original.render(**variables);after=derived.render(**variables)
 assert before==after
 rows.append(before)
assert 'torch' not in sys.modules and 'transformers' not in sys.modules
sys.stdout.write(json.dumps({'rendered':rows,'jinja2_version':jinja2.__version__,'original_derived_equal':len(rows),'torch_imported':False},ensure_ascii=False))
