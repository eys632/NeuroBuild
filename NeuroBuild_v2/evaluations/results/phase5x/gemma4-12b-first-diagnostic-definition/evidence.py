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


def validate_carry(cpu,load,hashes):
    check(CPU_SHA is not None and hashes[CPU]==hashes[CPU_ARCHIVED_PROOF]==CPU_SHA,'carry_pin')
    expected={'kind':CPU_KIND,'status':CPU_STATUS,'candidate_variant':VARIANT,
              'model_id':MODEL,'revision':REVISION,'gguf_sha256':GGUF_SHA,'header_sha256':HEADER_SHA,
              'template_sha256':TEMPLATE_SHA,'tokenizer_json_sha256':TOKENIZER_SHA,'source_pin':SOURCE_PIN,
              'protocol':'llama_cpp_json_schema','sampling_profile':PROFILE,'source_sha256':CPU_SOURCE,
              'sampling_request_parameters':SAMPLING,'enable_reasoning':False,'enable_thinking':False,
              'max_output_tokens':768,'max_context_tokens':4096,'application_input_output_nfc_repair':False,
              'proof_refs':CPU_REFS,'sampling_behavior':SUPPRESSION,
              'new_executions':dict.fromkeys(('native_public','vocab','context','model_inference','http','gpu'),0),
              'current_dataset_hash_verified_by_producer':False,
              'future_freeze_must_bind_current_dataset_bytes_to_historical_split_hashes':True,
              'new_model_runtime_status':'NOT_RUN','new_model_quality_status':'NOT_RUN'}
    exact({k:cpu[k] for k in expected},expected,'carry_identity_scope')
    for ref in CPU_REFS.values():check(hashes[ref['path']]==ref['sha256'],'carry_reference_pin')
    for path,sha in CPU_SOURCE.items():check(hashes[path]==sha,'carry_current_source')
    check(hashes[PATHS['dataset']]==DATASET_SHA and hashes[V2_DATASET]==V2_DATASET_SHA,'current_context_dataset_bytes')
    old=load(CPU_REFS['historical_aggregate']['path']);public=load(CPU_REFS['public_contract']['path'])
    witness=load(CPU_REFS['normalization_witness']['path'])
    expected_history={'measured_model_id':'google/gemma-4-31B-it-qat-q4_0-gguf',
                      'measured_revision':'59dde24573e7e61570dba08b18a2e1fe246955ed',
                      'measured_gguf_sha256':'179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b',
                      'original_status':'PASS','measurement_status_for_new_candidate':CPU_STATUS,
                      'public_contract':public['native'],'official_tokenizer_parity':old['official_tokenizer_parity'],
                      'splits':old['splits']}
    exact(cpu['historical_measurements'],expected_history,'historical_observations_exact')
    exact(old['official_tokenizer_parity'],{'status':'PASS','case_count':20,'id_match_count':20,
          'native_original_roundtrip_count':20},'historical_public20')
    for key,count,sha,max_tokens in [('exposed120',120,DATASET_SHA,2646),('v2_length80',80,V2_DATASET_SHA,2593)]:
        row=old['splits'][key]
        exact([row['input_count'],row['dataset_sha256'],row['max_input_tokens'],row['max_input_plus_output']],
              [count,sha,max_tokens,max_tokens+768],'historical_context_counts')
        check(type(row['min_input_tokens']) is int and 0<row['min_input_tokens']<=max_tokens
              and row['max_input_plus_output']<=4096,'context_budget')
    exact(cpu['resource_probe_token'],{'text':' ','token_id':236743,'native_token_count':1,'native_roundtrip':True},
          'resource_token_from_historical_vocab')
    check(cpu['resource_probe_token_suppression_disjoint'] is True
          and 236743 not in SUPPRESSION['additional_suppressed_ids'],'resource_token_suppression_collision')
    exact(cpu['normalization_limitation'],old['normalization_limitation'],'normalization_history')
    check(cpu['normalization_limitation']['official_hf_literal_u2581_raw_roundtrip'] is False
          and cpu['normalization_limitation']['global_unicode_roundtrip_guarantee'] is False
          and cpu['normalization_limitation']['input_output_repair'] is False
          and cpu['literal_u2581_witness_status']==witness['status']=='FAIL_NATIVE_ORIGINAL_ROUNDTRIP',
          'normalization_limitation_retained')
    header=load(HEADER);comparison=load(TOKENIZER_COMPARISON)
    check(hashes[HEADER]==HEADER_SHA and hashes[TOKENIZER_COMPARISON]==TOKENIZER_COMPARISON_SHA,'actual12_header_compare_pin')
    exact([header['model_id'],header['revision'],header['file_sha256'],header['file_bytes']],
          [MODEL,REVISION,GGUF_SHA,GGUF_BYTES],'actual12_header_identity')
    check(header['kind']=='GGUF_HEADER_AUDIT' and header['status']=='PASS'
          and header['full_file_sha256_verified'] is True and header['header']['tensor_count']==667
          and header['bindings']['suppression_wire_type']=='INT32(5)'
          and header['bindings']['suppression_eog_disjoint'] is True,'actual12_header_scope')
    exact(header['bindings']['suppress_tokens'],[258883,258882],'actual12_suppression')
    check(comparison['status']=='PASS_EXACT_TYPED_TOKENIZER_METADATA_EXCEPT_DECLARED_SUPPRESSION'
          and comparison['new_header_sha256']==HEADER_SHA
          and comparison['old_header_sha256']==CPU_REFS['old_header']['sha256']
          and comparison['sampling_difference']['complete_effective_sampling_equivalent'] is False,'typed_tokenizer_equivalence')
    return cpu


def validate_regression(receipt,hashes):
    check(hashes[REGRESSION]==REGRESSION_SHA and hashes[REGRESSION_LOG]==REGRESSION_LOG_SHA,'regression_pin')
    check(receipt['kind']=='GEMMA12_EXACT_NATIVE_IDENTITY_REGRESSION'
          and type(receipt['exit_code']) is int and receipt['exit_code']==0
          and receipt['real_postgresql'] is True and receipt['real_ifcopenshell'] is True
          and receipt['headless'] is True and receipt['cuda_visible_devices']==''
          and receipt['log_sha256']==REGRESSION_LOG_SHA,'regression_scope')
    for path,sha in receipt['source_sha256'].items():check(hashes[path]==sha,'regression_source')
    for path,sha in {**FIXED_SOURCE,**RUNTIME_DEFINITION_PINS}.items():check(hashes[path]==sha,'fixed_production_source')


def validate_single_epoch(cpu,provenance,startup,runtime,launch,guard,listeners,public,resource,hashes):
    check(CONFIG_SHA is not None and hashes[CONFIG]==hashes[START+'launch_config.json']==CONFIG_SHA,'config_exact')
    check(startup['kind']=='GEMMA4_12B_NATIVE_STARTUP_HTTP_PROOF' and startup['status']=='PASS'
          and startup['http_get_calls']==3 and startup['model_inference_calls']==0
          and startup['native_startup_warmup_enabled'] is True
          and startup['model_inference_calls_scope']=='Explicit HTTP generation calls only; native startup warmup is enabled'
          and startup['raw_http_bodies_saved'] is False,'startup_scope')
    exact([startup['chat_template_sha256'],startup['embedded_chat_template_sha256'],startup['embedded_chat_template_bytes'],
           startup['props_reported_template_sha256'],startup['props_reported_template_bytes']],
          [TEMPLATE_SHA,TEMPLATE_SHA,18683,PROPS_TEMPLATE_SHA,18682],'raw_props_template_distinction')
    check(runtime['startup_report_sha256']==hashes[START+'startup.json']
          and runtime['listener_report_sha256']==hashes[START+'listeners.json']
          and runtime['launch_config_sha256']==CONFIG_SHA
          and startup['resource_report_sha256']==hashes[START+'resource_report.json'],'startup_hash_edges')
    expected_runtime={'runtime_kind':'llama_cpp','profile':'a100','physical_gpu':3,'logical_gpu':0,
          'llama_cpp_commit':SOURCE_PIN,'cuda_architecture':'80-real','max_sequences':1,'max_model_len':4096,
          'enable_reasoning':False,'reasoning_parser':'deepseek','quantization':'Q4_0',
          'gguf_sha256':GGUF_SHA,'gguf_header_sha256':HEADER_SHA,'chat_template_sha256':TEMPLATE_SHA}
    exact({k:runtime[k] for k in expected_runtime},expected_runtime,'runtime_identity')
    expected_launch={'profile':'a100','model_revision':REVISION,'model_sha256':GGUF_SHA,'source_commit':SOURCE_PIN,
          'model_header_report':HEADER,'model_header_report_sha256':HEADER_SHA,'enable_reasoning':False,
          'max_seconds':7200,'max_model_len':4096,'port':8003,'served_model_name':'neurobuild-gemma4-12b-qat-q4-0',
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
    check(public['kind']=='GEMMA4_12B_NATIVE_PUBLIC_PRODUCTION_SMOKE' and public['status']=='PASS'
          and public['sampling_profile']==PROFILE and public['http_calls_attempted']==1
          and public['quality_gate_pass'] is False and public['generated_body_retained'] is False,'new12_public_smoke')
    check(resource['kind']=='GEMMA4_12B_NATIVE_PUBLIC_CONTEXT_RESOURCE_PROBE' and resource['status']=='PASS'
          and resource['http_post_calls']==1 and resource['tokens_evaluated']==resource['timings/prompt_n']==3328
          and resource['tokens_predicted']==resource['timings/predicted_n']==768 and resource['tokens_cached']==4095
          and resource['stop'] is True and resource['truncated'] is True and resource['stop_type']=='limit'
          and resource['grammar_enabled'] is False and resource['generated_body_retained'] is False
          and resource['quality_evaluation'] is False,'new12_resource_boundary')
    check(resource['guard_required_free_floor_mib']==guard['required_free_floor_mib']
          and resource['guard_aggregate_increment_limit_mib']==28672
          and resource['guard_minimum_observed_free_mib']>=resource['guard_required_free_floor_mib']
          and resource['guard_aggregate_peak_mib']<=28672,'resource_guard_budget')
    for proof in (startup,public,resource):
        check(proof['launch_config_sha256']==CONFIG_SHA and proof['pid']==startup['pid']
              and proof['process_start_ticks']==startup['process_start_ticks']
              and proof['guard_started_at_utc']==guard['started_at_utc'],'same_single_epoch')
        exact({k:proof[k] for k in provenance},provenance,'runtime_carry_provenance')
    return {'pid':startup['pid'],'start_ticks':startup['process_start_ticks'],
            'guard_started_at_utc':guard['started_at_utc']}


def provenance_projection(cpu):
    return {'model_id':MODEL,'model_revision':REVISION,'candidate_variant':VARIANT,
            'cpu_proof_sha256':CPU_SHA,'cpu_proof_kind':CPU_KIND,'cpu_proof_status':CPU_STATUS,
            'chat_template_sha256':TEMPLATE_SHA,'tokenizer_json_sha256':TOKENIZER_SHA,
            'tokenizer_contract':'carried_forward_by_exact_typed_tokenizer_and_effective_input_equivalence',
            'historical_measurements':cpu['historical_measurements'],'new_cpu_executions':cpu['new_executions'],
            'sampling_behavior':cpu['sampling_behavior'],'normalization_limitation':cpu['normalization_limitation'],
            'literal_u2581_witness_status':cpu['literal_u2581_witness_status'],
            'application_input_output_nfc_repair':False,'cpu_proof_refs':cpu['proof_refs'],
            'cpu_source_sha256':cpu['source_sha256'],'cpu_checks_rerun':False}
