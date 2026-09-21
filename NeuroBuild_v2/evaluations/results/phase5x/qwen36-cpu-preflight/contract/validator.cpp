// One NEW public request only. No GGUF argument, weights, tokenizer loop,
// context corpus, backend_init, HTTP listener or model decode.
// Reuse reviewed helpers; the historical main is compiled but never invoked.
#define main historical_qwen38_main_never_called
#include "../native-contract-validator/validator.cpp"
#undef main

int main(int argc, char ** argv) {
    std::unique_ptr<stderr_counter> drain;
    try {
        const rlimit no_core{0,0};
        ensure(setrlimit(RLIMIT_CORE,&no_core)==0);
        ensure(argc==3); // template + schema only; no model/GGUF argument allowed
        const char * mask=std::getenv("CUDA_VISIBLE_DEVICES");
        ensure(mask!=nullptr && std::string(mask).empty());
        drain=std::make_unique<stderr_counter>();
        common_log_set_verbosity_thold(-1);
        llama_log_set(silent_log,nullptr);
        const auto tmpl=read_file(argv[1],128*1024);
        const auto schema=json::parse(read_file(argv[2],128*1024));
        const auto bundle=json::parse(read_bounded(std::cin,256*1024));
        ensure(bundle.is_object() && bundle.size()==4);
        ensure(bundle.contains("request") && bundle.contains("expected_prompt")
               && bundle.contains("expected_generation_prompt") && bundle.contains("expected_final"));
        const auto & request=bundle.at("request");
        ensure(request.at("messages").is_array() && request.at("messages").size()==2);
        const auto & msgs=request.at("messages");
        ensure(msgs[0].at("role")=="system" && msgs[1].at("role")=="user");
        ensure(msgs[0].at("content").is_string() && !msgs[0].at("content").get<std::string>().empty());
        ensure(msgs[1].at("content").is_string() && !msgs[1].at("content").get<std::string>().empty());
        ensure(!request.contains("tools") && !request.contains("continue_final_message"));
        ensure(tmpl.find("<tool_call>")!=std::string::npos && tmpl.find("<function=")!=std::string::npos
               && tmpl.find("<parameter=")!=std::string::npos && tmpl.find("<think>")!=std::string::npos);
        server_chat_params options{};
        options.use_jinja=true;
        options.prefill_assistant=false;
        options.reasoning_format=COMMON_REASONING_FORMAT_DEEPSEEK;
        options.enable_thinking=false;
        options.allow_image=options.allow_audio=options.allow_video=false;
        options.force_pure_content=false;
        options.chat_template_kwargs={{"enable_thinking","false"}};
        options.tmpls=common_chat_templates_init(nullptr,tmpl,"<|endoftext|>","<|im_end|>");
        const auto native=request_parse(request,options,schema);
        const std::string prefix="<|im_start|>assistant\n<think>\n\n</think>\n\n";
        ensure(bundle.at("expected_generation_prompt")==prefix);
        ensure(native.at("generation_prompt")==prefix);
        ensure(native.at("prompt")==bundle.at("expected_prompt"));
        ensure(native.at("chat_format").get<int>()==static_cast<int>(COMMON_CHAT_FORMAT_PEG_NATIVE));
        json sampling_fields=json::object();
        for(const auto * key:{"temperature","top_p","top_k","min_p","presence_penalty",
                              "frequency_penalty","repeat_penalty","repeat_last_n","seed","samplers","max_tokens"})
            sampling_fields[key]=native.at(key);
        common_params defaults;
        defaults.reasoning_format=COMMON_REASONING_FORMAT_DEEPSEEK;
        const auto parsed=server_schema::eval_llama_cmpl_schema(nullptr,defaults,{},sampling_fields);
        const auto & sp=parsed.sampling;
        ensure(std::abs(sp.temp-.7f)<1e-6 && std::abs(sp.top_p-.8f)<1e-6 && sp.top_k==20
               && sp.min_p==0 && sp.penalty_present==1.5f && sp.penalty_freq==0
               && sp.penalty_repeat==1 && sp.penalty_last_n==64 && sp.seed==42 && parsed.n_predict==768);
        std::vector<std::string> names;
        for(auto kind:sp.samplers) names.push_back(common_sampler_type_to_str(kind));
        ensure(names==std::vector<std::string>({"penalties","top_k","top_p","min_p","temperature"}));
        const auto output=bundle.at("expected_final").get<std::string>();
        ensure(!output.empty() && output.size()<16384);
        const auto grammar=native.at("grammar").get<std::string>();
        ensure(accepts(grammar,prefix+output));
        ensure(!accepts(grammar,prefix+output+"x")); // one local changed-prefix wiring boundary, not old corpus
        common_chat_parser_params parser;
        parser.format=COMMON_CHAT_FORMAT_PEG_NATIVE;
        parser.reasoning_format=COMMON_REASONING_FORMAT_DEEPSEEK;
        parser.reasoning_in_content=false;
        parser.generation_prompt=prefix;
        parser.parser.load(native.at("chat_parser").get<std::string>());
        parser.debug=false;
        const auto final=common_chat_parse(output,false,parser);
        ensure(final.content==output && final.reasoning_content.empty() && final.tool_calls.empty());
        ensure(final.to_json_oaicompat().at("content")==output);
        const size_t discarded=drain->finish();
        ensure(discarded==0);
        json result={{"kind","QWEN36_NATIVE_SINGLE_PUBLIC_CPU_CHECK"},{"status","PASS"},
          {"public_request_count",1},{"native_full_system_user_prompt_exact",true},
          {"native_generation_prefix_exact",true},{"native_sampling_schema_binding",true},
          {"native_final_content_exact",true},{"native_trailing_suffix_rejected",true},
          {"grammar_lazy",false},{"grammar_triggers",0},{"generation_prefix_bytes",prefix.size()},
          {"native_prompt_bytes",native.at("prompt").get<std::string>().size()},
          {"core_dump_limit_zero",true},{"discarded_stderr_bytes",discarded},
          {"old_public_corpus_calls",0},{"tokenizer_parity_cases",0},{"context_requests",0},
          {"gguf_opened",false},{"model_context_created",false},{"backend_init_called",false},
          {"weight_tensors_loaded",false},{"model_inference_calls",0}};
        std::cout << result.dump() << std::endl;
        return 0;
    } catch (...) {
        const size_t discarded=drain ? drain->finish() : 0;
        std::cout << json{{"kind","QWEN36_NATIVE_SINGLE_PUBLIC_CPU_CHECK"},{"status","FAIL"},
          {"code","CHECK_FAILED"},{"check_line",check_line},{"discarded_stderr_bytes",discarded}}.dump() << std::endl;
        return 1;
    }
}
