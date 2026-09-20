// EXAONE 4.5 audited-GGUF public CPU vocabulary and native grammar checker.
// No HTTP listener/client, decode, context, backend_init, or model inference.
// Vocabulary only: empty devices, no_alloc, LOAD_MODE_NONE, no tensor weights.
#include "server-common.h"
#include "server-schema.h"
#include "json-schema-to-grammar.h"
#include "llama-grammar.h"
#include "unicode.h"
#include "jinja/runtime.h"
#include "jinja/parser.h"
#include "jinja/lexer.h"
#include "log.h"
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#include <atomic>
#include <thread>
#include <cerrno>
#include <unistd.h>
#include <cmath>
#include <cctype>
#include <sys/resource.h>

static int check_line = 0;
static int check_stage = 0;
static void ensure_at(bool good, int line) {
    if (!good) { check_line = line; throw std::runtime_error("CHECK_FAILED"); }
}
#define ensure(good) ensure_at((good), __LINE__)
// Direct fprintf(stderr) is used by the schema converter. Count and discard
// bytes in memory; no stderr text is retained on disk or copied into reports.
class stderr_counter {
    int saved = -1;
    int reader = -1;
    std::thread drain;
    std::atomic<size_t> bytes{0};
public:
    stderr_counter() {
        int ends[2];
        ensure(pipe(ends) == 0);
        reader = ends[0];
        saved = dup(STDERR_FILENO);
        if (saved < 0 || dup2(ends[1], STDERR_FILENO) < 0) {
            close(ends[0]); close(ends[1]);
            if (saved >= 0) close(saved);
            throw std::runtime_error("CAPTURE_FAILED");
        }
        close(ends[1]);
        try {
            drain = std::thread([this]() {
                char scratch[4096];
                for (;;) {
                    const auto n = read(reader, scratch, sizeof(scratch));
                    if (n > 0) bytes += static_cast<size_t>(n);
                    else if (n < 0 && errno == EINTR) continue;
                    else break;
                }
            });
        } catch (...) {
            dup2(saved, STDERR_FILENO); close(saved); close(reader);
            saved = reader = -1;
            throw;
        }
    }
    size_t finish() {
        if (saved >= 0) {
            fflush(stderr);
            int restored;
            do { restored = dup2(saved, STDERR_FILENO); } while (restored < 0 && errno == EINTR);
            if (restored < 0) close(STDERR_FILENO); // Ensure EOF; never deadlock on a pipe writer.
            close(saved); saved = -1;
            if (drain.joinable()) drain.join();
            close(reader); reader = -1;
        }
        return bytes.load();
    }
    ~stderr_counter() { finish(); }
};
static std::string read_bounded(std::istream & in, size_t cap) {
    std::string out;
    char chunk[8192];
    while (in) {
        in.read(chunk, sizeof(chunk));
        auto n = in.gcount();
        ensure(out.size() + static_cast<size_t>(n) <= cap);
        out.append(chunk, static_cast<size_t>(n));
    }
    return out;
}
static std::string read_file(const char * name, size_t cap) {
    std::ifstream in(name, std::ios::binary);
    ensure(in.good());
    return read_bounded(in, cap);
}
static bool accepts(const std::string & grammar_text, const std::string & input) {
    std::unique_ptr<llama_grammar, decltype(&llama_grammar_free_impl)> grammar(
        llama_grammar_init_impl(nullptr, grammar_text.c_str(), "root", false,
                                nullptr, 0, nullptr, 0), &llama_grammar_free_impl);
    ensure(grammar != nullptr);
    size_t offset = 0;
    try {
        while (offset < input.size()) {
            auto codepoint = unicode_cpt_from_utf8(input, offset);
            llama_grammar_accept_token(*grammar, 0, unicode_cpt_to_utf8(codepoint));
            if (llama_grammar_get_stacks(grammar.get()).empty()) return false;
        }
    } catch (const std::exception &) { return false; }
    const auto & stacks = llama_grammar_get_stacks(grammar.get());
    return std::any_of(stacks.begin(), stacks.end(), [](const auto & s) { return s.empty(); });
}
static bool accepts_tokens(const llama_vocab * vocab, const std::string & grammar_text,
                           const std::string & generation_prompt, const std::string & input) {
    ensure(vocab != nullptr);
    std::unique_ptr<llama_grammar, decltype(&llama_grammar_free_impl)> grammar(
        llama_grammar_init_impl(vocab, grammar_text.c_str(), "root", false,
                                nullptr, 0, nullptr, 0), &llama_grammar_free_impl);
    ensure(grammar != nullptr);
    const auto prefix_tokens = common_tokenize(vocab, generation_prompt, false, true);
    std::string prefix_pieces;
    for (size_t i = 0; i < prefix_tokens.size(); ++i) {
        const auto piece = common_token_to_piece(vocab, prefix_tokens[i], true);
        ensure(!piece.empty());
        if (i == 0 && std::isspace(static_cast<unsigned char>(piece[0])) &&
            !generation_prompt.empty() &&
            !std::isspace(static_cast<unsigned char>(generation_prompt[0]))) continue;
        prefix_pieces += piece;
        // Native prefill accepts tokens directly; it does not sample them.
        llama_grammar_accept_impl(*grammar, prefix_tokens[i]);
    }
    ensure(prefix_pieces == generation_prompt);
    const auto output_tokens = common_tokenize(vocab, input, false, true);
    std::string output_pieces;
    for (const auto token : output_tokens) output_pieces += common_token_to_piece(vocab, token, true);
    ensure(output_pieces == input);
    const auto eos = llama_vocab_eos(vocab);
    ensure(eos >= 0 && llama_vocab_is_eog(vocab, eos));
    try {
        for (const auto token : output_tokens) {
            // An EOG is a completion boundary, never a literal JSON byte.
            if (llama_vocab_is_eog(vocab, token)) return false;
            llama_token_data candidate{token, 0.0f, 0.0f};
            llama_token_data_array candidates{&candidate, 1, -1, false};
            llama_grammar_apply_impl(*grammar, &candidates);
            if (!std::isfinite(candidate.logit)) return false;
            llama_grammar_accept_impl(*grammar, token);
        }
        llama_token_data end{eos, 0.0f, 0.0f};
        llama_token_data_array ending{&end, 1, -1, false};
        llama_grammar_apply_impl(*grammar, &ending);
        return std::isfinite(end.logit);
    } catch (const std::exception &) { return false; }
}
static std::string render_direct(const std::string & text, const json & variables) {
    jinja::lexer lex;
    auto ast = jinja::parse_from_tokens(lex.tokenize(text));
    jinja::context context(text);
    jinja::global_from_json(context, variables, true);
    jinja::runtime runtime(context);
    auto values = runtime.execute(ast);
    auto parts = runtime.gather_string_parts(values);
    std::string result;
    for (const auto & part : parts->as_string().parts) result += part.val;
    return result;
}
static void silent_log(ggml_log_level, const char *, void *) {}
static json request_parse(json request, const server_chat_params & options, const json & schema) {
    ensure(request.at("response_format").at("type") == "json_schema");
    ensure(request.at("response_format").at("json_schema").at("schema") == schema);
    ensure(request.at("chat_template_kwargs").at("enable_thinking").is_boolean());
    ensure(request.at("chat_template_kwargs").at("enable_thinking") == false);
    ensure(options.reasoning_format == COMMON_REASONING_FORMAT_DEEPSEEK);
    if (request.contains("reasoning_format")) ensure(request.at("reasoning_format") == "deepseek");
    ensure(request.at("stream") == false);
    ensure(!request.contains("grammar") && !request.contains("guided_json") &&
           !request.contains("structured_outputs") && !request.contains("tools"));
    std::vector<raw_buffer> files;
    auto native = oaicompat_chat_params_parse(request, options, files);
    ensure(files.empty());
    ensure(native.contains("grammar") && !native.at("grammar").get<std::string>().empty());
    // This first candidate is nonthinking. A lazy grammar requires a distinct,
    // explicitly tested token-trigger replay before it can be accepted.
    ensure(native.at("grammar_lazy") == false);
    // Generic eager response-format grammar has no lazy tool trigger.
    ensure(native.at("grammar_triggers").is_array());
    ensure(native.at("grammar_triggers").empty());
    ensure(native.contains("chat_parser"));
    return native;
}

int main(int argc, char ** argv) {
    std::unique_ptr<stderr_counter> stderr_capture;
    try {
        // Fail before reading any request/template/model data if core dumps
        // cannot be disabled. The invocation wrapper enforces the same bound.
        const rlimit no_core{0, 0};
        ensure(setrlimit(RLIMIT_CORE, &no_core) == 0);
        ensure(argc == 4);
        const char * visible = std::getenv("CUDA_VISIBLE_DEVICES");
        ensure(visible != nullptr && std::string(visible).empty());
        stderr_capture = std::make_unique<stderr_counter>();
        common_log_set_verbosity_thold(-1);
        llama_log_set(silent_log, nullptr);
        // argv1 effective override, argv2 schema, argv3 root-audited vocab-only GGUF.
        const auto template_text = read_file(argv[1], 128 * 1024);
        const auto schema = json::parse(read_file(argv[2], 128 * 1024));
        const auto bundle = json::parse(read_bounded(std::cin, 16 * 1024 * 1024));
        ensure(schema.is_object() && !schema.empty());
        ensure(bundle.at("cases").is_array() && bundle.at("cases").size() <= 128);
        const auto standalone = json_schema_to_grammar(schema, true);
        ensure(!standalone.empty());
        server_chat_params options{};
        options.use_jinja = true;
        options.prefill_assistant = false;
        options.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;
        options.enable_thinking = false;
        options.allow_image = options.allow_audio = options.allow_video = false;
        options.force_pure_content = false;
        options.chat_template_kwargs = {{"enable_thinking", "false"}};
        options.tmpls = common_chat_templates_init(nullptr, template_text,
                                                  "[BOS]", "<|endofturn|>");
        const auto native = request_parse(bundle.at("request"), options, schema);
        check_stage = 20;
        const auto original_template = bundle.at("original_template").get<std::string>();
        ensure(original_template.size() <= 128*1024);
        const auto & template_cases = bundle.at("template_cases");
        ensure(template_cases.is_array() && template_cases.size() == 18);
        size_t render_equal = 0, original_render_mismatches = 0;
        for (const auto & entry : template_cases) {
            const auto expected = entry.at("expected_render").get<std::string>();
            ensure(expected.size() <= 65536);
            const auto actual = render_direct(template_text, entry.at("variables"));
            ensure(actual == expected);
            ++render_equal;
            original_render_mismatches += render_direct(original_template, entry.at("variables")) != expected;
        }
        const auto expected_prompt = template_cases.at(0).at("expected_render").get<std::string>();
        const auto original_system = bundle.at("request").at("messages").at(0).at("content").get<std::string>();
        const auto original_user = bundle.at("request").at("messages").at(1).at("content").get<std::string>();
        ensure(!original_system.empty() && native.at("prompt").get<std::string>() == expected_prompt);
        ensure(expected_prompt.find(original_system) != std::string::npos && expected_prompt.find(original_user) != std::string::npos);
        options.tmpls = common_chat_templates_init(nullptr, original_template, "[BOS]", "<|endofturn|>");
        const auto original_native = request_parse(bundle.at("request"), options, schema);
        const auto original_prompt = original_native.at("prompt").get<std::string>();
        ensure(original_prompt.find(original_system) == std::string::npos && original_prompt.find(original_user) != std::string::npos);
        ensure(original_prompt.size() == 177 && original_render_mismatches > 0);
        const std::string continue_witness = "{% for i in [0,1] %}{% if i == 0 %}SYSTEM{% continue %}{% endif %}USER{% endfor %}";
        ensure(render_direct(continue_witness, json::object()) == "USER");
        check_stage = 21;

        // Parse the actual forwarded scalar fields through the native schema.
        // Use only sampling fields here: vocab-level grammar/reasoning token
        // enforcement remains a separate future audit after GGUF validation.
        json sampling_fields = json::object();
        for (const auto * key : {"temperature","top_p","top_k","min_p","presence_penalty",
                                "frequency_penalty","repeat_penalty","repeat_last_n","seed",
                                "samplers","max_tokens"}) sampling_fields[key] = native.at(key);
        common_params base;
        base.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;
        const auto parsed_sampling = server_schema::eval_llama_cmpl_schema(nullptr,base,{},sampling_fields);
        const auto & sp = parsed_sampling.sampling;
        ensure(std::abs(sp.temp-0.6f)<1e-6 && std::abs(sp.top_p-0.95f)<1e-6 &&
               sp.top_k==20 && sp.min_p==0 && sp.penalty_present==1.5f && sp.penalty_freq==0 &&
               sp.penalty_repeat==1 && sp.penalty_last_n==64 && sp.seed==42 && parsed_sampling.n_predict==768);
        std::vector<std::string> sampler_names;
        for (auto kind : sp.samplers) sampler_names.push_back(common_sampler_type_to_str(kind));
        ensure(sampler_names == std::vector<std::string>({"penalties","top_k","top_p","min_p","temperature"}));
        const auto native_grammar = native.at("grammar").get<std::string>();
        common_chat_parser_params final_parser;
        final_parser.format = static_cast<common_chat_format>(native.at("chat_format").get<int>());
        final_parser.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;
        final_parser.reasoning_in_content = false;
        final_parser.generation_prompt = native.at("generation_prompt").get<std::string>();
        final_parser.parser.load(native.at("chat_parser").get<std::string>());
        final_parser.debug = false;
        ensure(final_parser.format == COMMON_CHAT_FORMAT_PEG_NATIVE);
        ensure(final_parser.generation_prompt == "<|assistant|>\n<think>\n\n</think>\n\n");
        ensure(native.at("prompt").get<std::string>().find(original_user) != std::string::npos);
        auto fenced = [](const std::string & text) { return "```json\n" + text + "\n```"; };
        size_t passing = 0, rejecting = 0, exact_final = 0;
        for (const auto & entry : bundle.at("cases")) {
            const auto text = entry.at("text").get<std::string>();
            ensure(text.size() <= 65536 && entry.at("accept").is_boolean());
            const bool expected = entry.at("accept").get<bool>();
            ensure(accepts(standalone, text) == expected);
            for (const auto & wire : {text, fenced(text)}) {
                ensure(accepts(native_grammar, final_parser.generation_prompt + wire) == expected);
                if (expected) {
                    auto final = common_chat_parse(wire, false, final_parser);
                    ensure(final.content == text && final.reasoning_content.empty() && final.tool_calls.empty());
                    ensure(final.to_json_oaicompat().at("content") == text);
                    ++exact_final;
                }
            }
            expected ? ++passing : ++rejecting;
        }
        ensure(passing == 10 && rejecting == 20 && exact_final == 20);
        const auto valid_json = bundle.at("cases").at(0).at("text").get<std::string>();
        std::vector<std::string> bad_native{
            "```text\n" + valid_json + "\n```",
            "<tool_call>{\"name\":\"move\",\"arguments\":{}}</tool_call>",
            "<think>PUBLIC_UNFINISHED",
            valid_json + "<tool_call>"
        };
        for (const auto & text : bad_native) ensure(!accepts(native_grammar, final_parser.generation_prompt + text));
        // Artificial public parser boundary, with the source-supported assistant
        // prefix before the template's empty think block. This is not a change
        // to the real request's nonthinking generation prompt or application data.
        auto thought_parser = final_parser;
        thought_parser.generation_prompt = "<|assistant|>\n";
        const std::string public_thought = "PUBLIC_SYNTHETIC_BOUNDARY";
        const auto thought_wire = "<think>\n" + public_thought + "\n</think>\n\n" + valid_json;
        ensure(accepts(native_grammar, thought_parser.generation_prompt + thought_wire));
        const auto separated = common_chat_parse(thought_wire, false, thought_parser);
        // Generic PEG until(closing tag) retains the preceding newline in
        // reasoning; mapper concatenates it without trimming. Final JSON is exact.
        ensure(separated.content == valid_json);
        ensure(separated.reasoning_content == public_thought + "\n");
        ensure(separated.tool_calls.empty());
        ensure(separated.to_json_oaicompat().at("content") == valid_json);
        json result = {{"status","PASS"}, {"kind","EXAONE45_NATIVE_PUBLIC_CONTRACT_CPU_PREFLIGHT"},
                       {"public_template_reference_cases",render_equal}, {"original_template_native_mismatches",original_render_mismatches},
                       {"original_native_system_present",false}, {"original_native_prompt_bytes",original_prompt.size()},
                       {"derived_native_system_and_user_exact",true}, {"derived_native_prompt_equals_official_reference",true},
                       {"nested_continue_witness_reproduced",true}, {"schema_cases_accepted",passing}, {"schema_cases_rejected",rejecting},
                       {"native_final_content_exact_cases",exact_final},
                       {"native_grammar_generation_prompt_prefilled",true},
                       {"native_grammar_prefill_bytes",final_parser.generation_prompt.size()},
                       {"core_dump_limit_zero",true},
                       {"native_sampling_schema_binding",true},
                       {"native_request_grammar_nonempty",true}, {"grammar_lazy",false},
                       {"grammar_triggers",native.at("grammar_triggers").size()},
                       {"native_protocol_rejection_cases",bad_native.size()},
                       {"artificial_thought_split_cases",1},
                       {"final_json_bytes_unchanged",true}, {"native_grammar_bytes",native_grammar.size()}, {"public_user_bytes_present_unchanged",true},
                       {"standalone_grammar_bytes",standalone.size()},
                       {"native_request_prompt_bytes",native.at("prompt").get<std::string>().size()},
                       {"model_context_created",false}, {"backend_init_called",false},
                       {"weight_tensors_loaded",false}, {"native_tokenization","NOT_RUN"}};
        check_stage = 100;
        auto params = llama_model_default_params();
        ggml_backend_dev_t devices[] = {nullptr};
        params.devices = devices; params.n_gpu_layers = 0;
        params.vocab_only = true; params.no_alloc = true;
        params.load_mode = LLAMA_LOAD_MODE_NONE; params.load_mtp = false;
        std::unique_ptr<llama_model, decltype(&llama_model_free)> model(
            llama_model_load_from_file(argv[3], params), &llama_model_free);
        ensure(model != nullptr);
        const auto * vocab = llama_model_get_vocab(model.get());
        const char * embedded = llama_model_chat_template(model.get(), nullptr);
        ensure(embedded != nullptr && original_template == embedded);
        ensure(llama_vocab_bos(vocab) == 1 && llama_vocab_eos(vocab) == 53);
        ensure(!llama_vocab_get_add_bos(vocab) && !llama_vocab_get_add_eos(vocab));
        options.tmpls = common_chat_templates_init(model.get(), template_text);
        const auto actual_native = request_parse(bundle.at("request"), options, schema);
        ensure(actual_native.at("prompt") == native.at("prompt"));
        ensure(actual_native.at("prompt").get<std::string>() == expected_prompt);
        ensure(actual_native.at("grammar") == native.at("grammar"));
        ensure(actual_native.at("generation_prompt") == native.at("generation_prompt"));
        result["embedded_original_template_exact_match"] = true;
        result["effective_override_vocab_render_exact"] = true;
        result["native_vocab_grammar_generation_prompt_exact"] = true;
        result["native_vocab_bos_id"] = 1; result["native_vocab_eos_id"] = 53;
        result["native_vocab_add_bos"] = false; result["native_vocab_add_eos"] = false;
        check_stage = 110;
        for (const auto & entry : bundle.at("cases")) {
            const auto text = entry.at("text").get<std::string>();
            for (const auto & wire : {text,fenced(text)}) {
                ensure(accepts_tokens(vocab,native_grammar,final_parser.generation_prompt,wire) == entry.at("accept").get<bool>());
            }
            ++check_stage;
        }
        result["native_vocab_grammar_cases_accepted"] = passing*2;
        result["native_vocab_grammar_cases_rejected"] = rejecting*2;
        result["native_vocab_grammar_eog_checked"] = true;
        check_stage = 200;
        const auto reference_kind=bundle.at("reference_kind").get<std::string>();
        ensure(reference_kind=="official_hf_nfc" || reference_kind=="derived_hf_nfc_disabled");
        const auto & parity = bundle.at("tokenizer_parity");
        ensure(parity.is_array() && parity.size() == 20);
        size_t id_matches=0, raw_roundtrips=0, expected_raw_roundtrips=0;
        uint64_t mismatch_mask=0, raw_mismatch_mask=0;
        for (size_t i=0; i<parity.size(); ++i) {
            const auto & entry = parity.at(i);
            ensure(entry.is_object() && entry.size()==2);
            const auto text = entry.at("text").get<std::string>();
            ensure(text.size()<=8192);
            const auto & expected = entry.at("expected_token_ids");
            ensure(expected.is_array() && expected.size()<=4096);
            std::vector<llama_token> expected_tokens;
            for (const auto & id: expected) {
                ensure(id.is_number_integer()); const auto n=id.get<int64_t>();
                ensure(n>=0 && n<llama_vocab_n_tokens(vocab)); expected_tokens.push_back(static_cast<llama_token>(n));
            }
            const auto actual_tokens=common_tokenize(vocab,text,false,true);
            const bool same=actual_tokens==expected_tokens;
            const bool raw=common_detokenize(vocab,actual_tokens,true)==text;
            id_matches+=same; raw_roundtrips+=raw;
            expected_raw_roundtrips+=common_detokenize(vocab,expected_tokens,true)==text;
            if (!same) mismatch_mask |= uint64_t{1}<<i;
            if (!raw) raw_mismatch_mask |= uint64_t{1}<<i;
            ++check_stage;
        }
        result["tokenizer_cases_checked"]=parity.size(); result["tokenizer_id_match_count"]=id_matches;
        result["tokenizer_id_mismatch_mask"]=mismatch_mask; result["tokenizer_native_raw_roundtrip_count"]=raw_roundtrips;
        result["tokenizer_native_raw_mismatch_mask"]=raw_mismatch_mask;
        result["tokenizer_reference_ids_raw_roundtrip_count"]=expected_raw_roundtrips;
        result["tokenizer_reference_parity"]=(id_matches==20 ? "PASS" : "FAIL");
        result["native_tokenization"]="OBSERVED_VOCAB_ONLY";
        const auto space=common_tokenize(vocab," ",false,true);
        ensure(space.size()==1 && !llama_vocab_is_eog(vocab,space.at(0)) && common_detokenize(vocab,space,true)==" ");
        result["resource_probe_token_id"]=space.at(0); result["resource_probe_token_count"]=1;
        result["resource_probe_raw_roundtrip"]=true;
        const auto public_tokens=common_tokenize(vocab,actual_native.at("prompt").get<std::string>(),true,true);
        result["public_input_tokens"]=public_tokens.size(); result["public_input_plus_output"]=public_tokens.size()+768;
        ensure(!public_tokens.empty() && public_tokens.size()+768<=4096);
        const bool reference_pass=id_matches==20 && raw_roundtrips==20;
        result["status"]=reference_pass ? "PASS" : "FAIL";
        result["reference_kind"]=reference_kind;
        result["reference_gate_pass"]=reference_pass;
        result["official_hf_equivalence"] = reference_kind=="official_hf_nfc" ? (reference_pass ? "PASS" : "FAIL") : "NOT_ASSERTED_BY_DERIVED_REFERENCE";
        if (reference_pass) {
            const auto & contexts=bundle.at("context_requests");
            ensure(contexts.is_array() && !contexts.empty() && contexts.size()<=200);
            ensure(bundle.at("max_output_tokens").is_number_integer() && bundle.at("max_output_tokens").get<int64_t>()==768);
            size_t largest=0,smallest=std::numeric_limits<size_t>::max();
            check_stage=300;
            for (const auto & request : contexts) {
                const auto rendered=request_parse(request,options,schema).at("prompt").get<std::string>();
                const auto & messages=request.at("messages");
                ensure(messages.size()==2 && messages.at(0).at("role")=="system" && messages.at(1).at("role")=="user");
                const auto system=messages.at(0).at("content").get<std::string>();
                const auto user=messages.at(1).at("content").get<std::string>();
                const auto exact="<|system|>\n"+system+"<|endofturn|>\n<|user|>\n"+user+"<|endofturn|>\n"+final_parser.generation_prompt;
                ensure(rendered==exact && rendered.size()<=128*1024);
                const auto tokens=common_tokenize(vocab,rendered,true,true);
                ensure(!tokens.empty());
                largest=std::max(largest,tokens.size());smallest=std::min(smallest,tokens.size());
                ++check_stage;
            }
            ensure(largest+768<=4096);
            result["input_count"]=contexts.size();result["min_input_tokens"]=smallest;
            result["max_input_tokens"]=largest;result["max_input_plus_output"]=largest+768;
            result["all_context_system_user_bytes_exact"]=true;
        }
        const auto stderr_bytes = stderr_capture->finish();
        ensure(stderr_bytes == 0);
        result["discarded_stderr_bytes"] = stderr_bytes;
        std::cout << result.dump() << std::endl;
        return reference_pass ? 0 : 1;
    } catch (const std::exception &) {
        const auto stderr_bytes = stderr_capture ? stderr_capture->finish() : 0;
        json failure = {{"kind","EXAONE45_NATIVE_PUBLIC_CONTRACT_CPU_PREFLIGHT"},{"status","FAIL"},
                        {"code","CHECK_FAILED"},{"stage",check_stage},{"check_line",check_line},
                        {"discarded_stderr_bytes",stderr_bytes}};
        std::cout << failure.dump() << std::endl;
        return 1;
    }
}
