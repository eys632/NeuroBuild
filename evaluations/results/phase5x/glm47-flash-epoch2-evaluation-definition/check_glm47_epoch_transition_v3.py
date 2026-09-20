"""Only the new epoch transition: saved metadata positive and mutations.

No imports of runtime collectors, process checks, native/HTTP/model calls,
dataset/result files or old12 metadata controls. Main runs only on root GO.
"""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy

ROOT=Path('/home/a202192020/NeuroBuild_v2')
FREEZER='var/research/freeze_native_glm47_diagnostic_v3.py'
REPLAY='var/research/replay_native_glm47_exposed_v3.py'
OUTPUT='var/research/glm47-epoch-transition-v3-proof.json'

def sha(name):return hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
def read(name):return json.loads((ROOT/name).read_bytes())

def main():
    f=runpy.run_path(str(ROOT/FREEZER),run_name='new_epoch_controls_only')
    r=runpy.run_path(str(ROOT/REPLAY),run_name='new_epoch_controls_only')
    paths=[f['START']+'launch_config.json',f['EVALUATION_START']+'launch_config.json',
        f['START']+'runtime_metadata.json',f['EVALUATION_START']+'runtime_metadata.json',
        f['START']+'startup.json',f['EVALUATION_START']+'startup.json',
        f['START']+'resource_report.json',f['EVALUATION_START']+'resource_report.json',
        f['EVALUATION_START']+'listeners.json',f['FINAL_GUARD']]
    original=[read(p) for p in paths]
    assert sha(f['EVALUATION_START']+'startup.json')==f['EVALUATION_STARTUP_SHA']
    assert sha(f['EVALUATION_START']+'launch_config.json')==f['EVALUATION_CONFIG_SHA']
    assert sha(f['FINAL_GUARD'])==f['FINAL_GUARD_SHA']
    funcs=[f['validate_epoch_transition'],r['validate_epoch_transition']]
    for validate in funcs:validate(*deepcopy(original))
    mutations=[
        ('changed_batch',lambda x:x[1].update(batch_size=32)),
        ('changed_template_policy',lambda x:x[1].update(chat_template_path='unexpected')),
        ('reused_output_path',lambda x:x[1].update(report_file=x[0]['report_file'])),
        ('changed_build_identity',lambda x:x[3].update(build_report_sha256='0'*64)),
        ('old_guard_not_stopped',lambda x:x[9].update(state='RUNNING')),
        ('old_child_not_reaped',lambda x:x[9]['shutdown'].update(child_reaped=False)),
        ('old_final_wrong_pid',lambda x:x[9].update(child_pid=-1)),
        ('reused_old_child_identity',lambda x:x[5].update(pid=x[4]['pid'],process_start_ticks=x[4]['process_start_ticks'])),
        ('new_guard_before_old_stop',lambda x:x[7].update(started_at_utc=x[6]['started_at_utc'])),
        ('new_listener_wrong_pid',lambda x:x[8].update(pid=-1)),
        ('new_cpu_proof_changed',lambda x:x[5].update(cpu_proof_sha256='0'*64)),
        ('new_guard_below_floor',lambda x:x[7].update(minimum_observed_free_mib=x[7]['required_free_floor_mib']-1)),
    ]
    rejected=[]
    for label,change in mutations:
        for validate in funcs:
            changed=deepcopy(original);change(changed)
            try:validate(*changed)
            except (AssertionError,ValueError,KeyError):pass
            else:raise AssertionError('accepted_'+label)
        rejected.append(label)
    report={'kind':'GLM47_EPOCH_TRANSITION_NEW_CONTROLS','status':'PASS_NEW_EPOCH_TRANSITION_CONTROLS_ONLY',
        'helper_sha256':sha(FREEZER),'replay_sha256':sha(REPLAY),
        'selfcheck_sha256':sha(str(Path(__file__).relative_to(ROOT))),
        'actual_saved_epoch2_transition_positive':'PASS_BOTH_CONSUMERS',
        'tampering_rejected':rejected,'saved_metadata_sha256':{p:sha(p) for p in paths},
        'core_functions_invoked':0,'old12_controls_rerun':0,'public_resource_calls':0,
        'dataset_or_result_body_reads':0,'model_native_gpu_http_calls':0,
        'scope':'Only new epoch transition metadata; not runtime execution, prior smoke replay or quality evaluation.'}
    with (ROOT/OUTPUT).open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({'status':report['status'],'controls':len(rejected),'sha256':sha(OUTPUT),
        'helper_sha256':report['helper_sha256'],'replay_sha256':report['replay_sha256']}))

if __name__=='__main__':main()
