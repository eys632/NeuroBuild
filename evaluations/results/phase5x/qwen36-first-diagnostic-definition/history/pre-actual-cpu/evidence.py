"""Pure saved-receipt validators shared by prospective freeze and offline replay.

No file/process/network entrypoints. Callbacks may read only frozen metadata;
all corpus paths below are compared as already-computed byte hashes.
"""
import json
import math
import os
import re
from contract import *


def check(value,code):
    if not value:raise AssertionError(code)


def exact(a,b,code):
    dump=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
    check(dump(a)==dump(b),code)


def validate_cpu(cpu,load,hashes):
    """Saved metadata only; exact final aggregate schema is still a blocked slot.

    The current single-public request differs from historical tokenizer/context
    observations. No Gemma proof or oldV2 split may satisfy this candidate.
    """
    check(CPU_SCHEMA_FINAL is True and type(CPU_EXPECTED_PROJECTION) is dict
          and type(CPU_REFS) is dict and set(CPU_REFS)==set(CPU_REF_KEYS),
          'actual_qwen36_cpu_schema_pending')
    check(CPU_SHA is not None and hashes[CPU]==hashes[CPU_ARCHIVED_PROOF]==CPU_SHA,'cpu_pin')
    expected={'kind':CPU_KIND,'status':CPU_STATUS,'candidate_variant':VARIANT,
              'model_id':MODEL,'revision':REVISION,'gguf_sha256':GGUF_SHA,'header_sha256':HEADER_SHA,
              'template_sha256':TEMPLATE_SHA,'tokenizer_json_sha256':TOKENIZER_SHA,'source_pin':SOURCE_PIN,
              'protocol':'llama_cpp_json_schema','sampling_profile':PROFILE,'source_sha256':CPU_SOURCE,
              'sampling_request_parameters':SAMPLING,'enable_reasoning':False,'enable_thinking':False,
              'max_output_tokens':768,'max_context_tokens':4096,'application_input_output_nfc_repair':False,
              'proof_refs':CPU_REFS,'sampling_equivalent':False}
    exact({k:cpu[k] for k in expected},expected,'qwen36_identity_scope')
    # Root-reviewed actual observation map must cover every remaining semantic
    # input, rather than letting historical PASS be relabelled as a fresh run.
    mandatory={'splits','resource_probe_token','historical_hf_equivalence',
               'historical_raw_reference','new_executions','normalization_limitation'}
    check(mandatory<=set(CPU_EXPECTED_PROJECTION),'cpu_expected_projection_incomplete')
    exact({k:cpu[k] for k in CPU_EXPECTED_PROJECTION},CPU_EXPECTED_PROJECTION,'qwen36_actual_scope')
    for ref in CPU_REFS.values():
        check(set(ref)=={'path','sha256'} and hashes[ref['path']]==ref['sha256'],'cpu_reference_pin')
    check(CPU_REFS['header']=={'path':HEADER,'sha256':HEADER_SHA}
          and CPU_REFS['tokenizer_comparison']=={'path':TOKENIZER_COMPARISON,'sha256':TOKENIZER_COMPARISON_SHA},
          'new_header_comparison_edges')
    for path,sha in CPU_SOURCE.items():check(hashes[path]==sha,'cpu_current_source')
    check(hashes[PATHS['dataset']]==DATASET_SHA,'exposed120_dataset_binding')
    check(set(cpu['splits'])=={'exposed120'},'no_old_v2_or_unseen_context_split')
    split=cpu['splits']['exposed120']
    check(split['dataset_sha256']==DATASET_SHA and type(split['input_count']) is int
          and split['input_count']==120 and split['measurement_kind']=='CARRIED_FORWARD'
          and split['measured_model_id']=='ggml-org/Qwen3.8-27B-GGUF','historical_exposed_scope')
    for k in ('min_input_tokens','max_input_tokens','max_input_plus_output'):
        check(type(split[k]) is int,'context_count_type')
    check(0<split['min_input_tokens']<=split['max_input_tokens']
          and split['max_input_plus_output']==split['max_input_tokens']+768<=4096,'context_budget')
    check(cpu['historical_hf_equivalence']['status']=='FAIL'
          and cpu['historical_raw_reference']['status']=='PASS','historical_official_raw_distinction')
    check(cpu['resource_probe_token']['text']==' '
          and type(cpu['resource_probe_token']['token_id']) is int
          and cpu['resource_probe_token']['native_token_count']==1
          and cpu['resource_probe_token']['native_roundtrip'] is True
          and cpu['resource_probe_token']['measurement_kind']=='CARRIED_FORWARD_BY_TYPED_VOCAB_EQUALITY',
          'resource_token_scope')
    check(cpu['resource_probe_token']['token_id']==RESOURCE_TOKEN_ID,'resource_token_pin')
    header=load(HEADER)
    exact([header['model_id'],header['revision'],header['file_sha256'],header['file_bytes']],
          [MODEL,REVISION,GGUF_SHA,GGUF_BYTES],'actual_header_identity')
    check(header['kind']=='GGUF_HEADER_AUDIT' and header['status']=='PASS'
          and header['full_file_sha256_verified'] is True and header['header']['tensor_count']==733,
          'actual_header_scope')
    return cpu


def cpu_scope(cpu):
    return {k:cpu[k] for k in ('status','splits','historical_hf_equivalence',
             'historical_raw_reference','new_executions','sampling_equivalent')}



def validate_regression(receipt,hashes):
    check(hashes[REGRESSION]==REGRESSION_SHA and hashes[REGRESSION_LOG]==REGRESSION_LOG_SHA,'regression_pin')
    check(receipt['kind']=='QWEN36_EXPLICIT_NATIVE_PROFILE_REGRESSION'
          and type(receipt['exit_code']) is int and receipt['exit_code']==0
          and receipt['real_postgresql'] is True and receipt['real_ifcopenshell'] is True
          and receipt['headless'] is True and receipt['cuda_visible_devices']==''
          and receipt['log_sha256']==REGRESSION_LOG_SHA,'regression_scope')
    for path,sha in receipt['source_sha256'].items():check(hashes[path]==sha,'regression_source')
    for path,sha in {**FIXED_SOURCE,**RUNTIME_DEFINITION_PINS}.items():check(hashes[path]==sha,'fixed_production_source')


def validate_single_epoch(cpu,provenance,startup,runtime,launch,guard,listeners,public,resource,hashes):
    check(CONFIG_SHA is not None and hashes[CONFIG]==hashes[START+'launch_config.json']==CONFIG_SHA,'config_exact')
    check(startup['kind']=='QWEN36_NATIVE_STARTUP_HTTP_PROOF' and startup['status']=='PASS'
          and startup['http_get_calls']==3 and startup['model_inference_calls']==0
          and startup['native_startup_warmup_enabled'] is True
          and startup['model_inference_calls_scope']=='Explicit HTTP generation calls only; native startup warmup is enabled'
          and startup['raw_http_bodies_saved'] is False,'startup_scope')
    exact([startup['chat_template_sha256'],startup['embedded_chat_template_sha256'],startup['embedded_chat_template_bytes'],
           startup['props_reported_template_sha256'],startup['props_reported_template_bytes']],
          [TEMPLATE_SHA,TEMPLATE_SHA,TEMPLATE_BYTES,PROPS_TEMPLATE_SHA,PROPS_TEMPLATE_BYTES],'raw_props_template_distinction')
    check(runtime['startup_report_sha256']==hashes[START+'startup.json']
          and runtime['listener_report_sha256']==hashes[START+'listeners.json']
          and runtime['launch_config_sha256']==CONFIG_SHA
          and startup['resource_report_sha256']==hashes[START+'resource_report.json'],'startup_hash_edges')
    expected_runtime={'runtime_kind':'llama_cpp','profile':'a100','physical_gpu':3,'logical_gpu':0,
          'llama_cpp_commit':SOURCE_PIN,'cuda_architecture':'80-real','max_sequences':1,'max_model_len':4096,
          'enable_reasoning':False,'reasoning_parser':'deepseek','quantization':'Q4_K_M',
          'gguf_sha256':GGUF_SHA,'gguf_header_sha256':HEADER_SHA,'chat_template_sha256':TEMPLATE_SHA}
    exact({k:runtime[k] for k in expected_runtime},expected_runtime,'runtime_identity')
    expected_launch={'profile':'a100','model_revision':REVISION,'model_sha256':GGUF_SHA,'source_commit':SOURCE_PIN,
          'model_header_report':HEADER,'model_header_report_sha256':HEADER_SHA,'enable_reasoning':False,
          'max_seconds':GUARD_MAX_SECONDS,'max_model_len':4096,'port':8003,'served_model_name':SERVED_MODEL,
          'estimated_peak_mib':28672,'peak_allowance_mib':0,'batch_size':64,'ubatch_size':64}
    exact({k:launch[k] for k in expected_launch},expected_launch,'launch_identity')
    check(launch.get('chat_template_path') is None and launch.get('chat_template_sha256') is None,'no_template_override')
    for runtime_key,launch_key in {'binary_sha256':'binary_sha256','build_report_sha256':'build_report_sha256',
          'source_provenance_sha256':'source_report_sha256','gguf_header_sha256':'model_header_report_sha256'}.items():
        check(runtime[runtime_key]==launch[launch_key],'runtime_launch_artifacts')
    check(guard['state']=='RUNNING' and guard['native_identity_verified'] is True
          and guard['physical_gpu_index']==3 and guard['required_cuda_visible_devices']=='3'
          and guard['native_output_policy']=='DISCARD_STDOUT_STDERR' and guard['native_core_dump_limit_bytes']==0
          and guard['max_num_seqs']==1 and guard['max_model_len']==4096
          and guard['batch_size']==guard['ubatch_size']==64
          and guard['minimum_observed_free_mib']>=guard['required_free_floor_mib']
          and guard['observed_baseline_relative_peak_mib']<=guard['aggregate_increment_limit_mib']==28672,'guard_scope_budget')
    for key in ('binary_sha256','source_report_sha256','build_report_sha256','source_commit','model_sha256',
                'model_revision','model_header_report_sha256'):
        check(guard['native_artifacts'][key]==launch[key],'guard_artifact_binding')
    check('chat_template_override' not in guard['native_artifacts'],'guard_no_override')
    check(listeners['verdict']=='PASS' and listeners['all_loopback'] is True and listeners['snapshot_complete'] is True
          and listeners['uid']==os.getuid() and listeners['pid']==guard['child_pid']==startup['pid']
          and listeners['process_start_ticks']==startup['process_start_ticks'],'own_loopback_epoch')
    check(public['kind']=='QWEN36_NATIVE_PUBLIC_PRODUCTION_SMOKE' and public['status']=='PASS'
          and public['sampling_profile']==PROFILE and public['http_calls_attempted']==1
          and public['quality_gate_pass'] is False and public['generated_body_retained'] is False,'qwen36_public_smoke')
    check(resource['kind']=='QWEN36_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE' and resource['status']=='PASS'
          and resource['http_post_calls']==1 and resource['tokens_evaluated']==resource['timings/prompt_n']==3328
          and resource['tokens_predicted']==resource['timings/predicted_n']==768 and resource['tokens_cached']==4095
          and resource['stop'] is True and resource['truncated'] is True and resource['stop_type']=='limit'
          and resource['grammar_enabled'] is False and resource['generated_body_retained'] is False
          and resource['quality_evaluation'] is False,'qwen36_resource_boundary')
    check(resource['guard_required_free_floor_mib']==guard['required_free_floor_mib']
          and resource['guard_aggregate_increment_limit_mib']==28672
          and resource['guard_minimum_observed_free_mib']>=resource['guard_required_free_floor_mib']
          and resource['guard_aggregate_peak_mib']<=28672,'resource_guard_budget')
    for proof in (startup,public,resource):
        check(proof['launch_config_sha256']==CONFIG_SHA and proof['pid']==startup['pid']
              and proof['process_start_ticks']==startup['process_start_ticks']
              and proof['guard_started_at_utc']==guard['started_at_utc'],'same_single_epoch')
        exact({k:proof[k] for k in provenance},provenance,'runtime_cpu_provenance')
    return {'pid':startup['pid'],'start_ticks':startup['process_start_ticks'],
            'guard_started_at_utc':guard['started_at_utc']}


def provenance_projection(cpu):
    """Proposed runtime consumer projection; exact actual API remains pending."""
    return {'model_id':MODEL,'model_revision':REVISION,'candidate_variant':VARIANT,
            'cpu_proof_sha256':CPU_SHA,'cpu_proof_kind':CPU_KIND,'cpu_proof_status':CPU_STATUS,
            'chat_template_sha256':TEMPLATE_SHA,'tokenizer_json_sha256':TOKENIZER_SHA,
            'cpu_measurement_scope':cpu_scope(cpu),
            'normalization_limitation':cpu['normalization_limitation'],
            'application_input_output_nfc_repair':False,'cpu_proof_refs':cpu['proof_refs'],
            'cpu_source_sha256':cpu['source_sha256']}
