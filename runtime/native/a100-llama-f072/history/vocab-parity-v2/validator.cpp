// DRAFT: compile/run only after parent review. Exact pinned native HTTP/chat/grammar.
// No HTTP listener/client, decode, context, backend_init, or model inference.
// stdin contains synthetic request/corpus; optional future GGUF is vocab-only.
#include "server-common.h"
#include "server-schema.h"
#include "json-schema-to-grammar.h"
#include "llama-grammar.h"
#include "unicode.h"
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

static void ensure(bool good) { if (!good) throw std::runtime_error("CHECK_FAILED"); }
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
// Mirror common/sampling.cpp's eager output-format grammar prefill, then
// constrain actual vocab token candidates. This path runs only with the
// optional, audited vocab-only model; it creates no context or logits.
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
        ensure(argc == 3 || argc == 4);
        const char * visible = std::getenv("CUDA_VISIBLE_DEVICES");
        ensure(visible != nullptr && std::string(visible).empty());
        stderr_capture = std::make_unique<stderr_counter>();
        common_log_set_verbosity_thold(-1);
        llama_log_set(silent_log, nullptr);
        // argv1 is verified template; argv2 exact schema. Optional argv3 is the
        // already header/SHA-audited GGUF; runner must bind paths/hashes first.
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
                                                  "<|endoftext|>", "<|im_end|>");
        const auto native = request_parse(bundle.at("request"), options, schema);
        // Parse the actual forwarded scalar fields through the native schema.
        // Use only sampling fields here: grammar/reasoning token setup needs
        // the optional real vocab and is tested by separate paths below.
        json sampling_fields = json::object();
        for (const auto * key : {"temperature","top_p","top_k","min_p","presence_penalty",
                                "frequency_penalty","repeat_penalty","repeat_last_n","seed",
                                "samplers","max_tokens"}) sampling_fields[key] = native.at(key);
        common_params base;
        base.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;
        const auto parsed_sampling = server_schema::eval_llama_cmpl_schema(nullptr,base,{},sampling_fields);
        const auto & sp = parsed_sampling.sampling;
        ensure(std::abs(sp.temp-0.7f)<1e-6 && std::abs(sp.top_p-0.8f)<1e-6 &&
               sp.top_k==20 && sp.min_p==0 && sp.penalty_present==0 && sp.penalty_freq==0 &&
               sp.penalty_repeat==1 && sp.penalty_last_n==0 && sp.seed==42 && parsed_sampling.n_predict==768);
        std::vector<std::string> sampler_names;
        for (auto kind : sp.samplers) sampler_names.push_back(common_sampler_type_to_str(kind));
        ensure(sampler_names == std::vector<std::string>({"temperature","top_k","top_p","min_p"}));
        const auto native_grammar = native.at("grammar").get<std::string>();
        common_chat_parser_params final_parser;
        final_parser.format = static_cast<common_chat_format>(native.at("chat_format").get<int>());
        final_parser.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;
        final_parser.reasoning_in_content = false;
        final_parser.generation_prompt = native.at("generation_prompt").get<std::string>();
        final_parser.parser.load(native.at("chat_parser").get<std::string>());
        final_parser.debug = false;
        size_t passing = 0, rejecting = 0;
        for (const auto & entry : bundle.at("cases")) {
            const auto text = entry.at("text").get<std::string>();
            ensure(text.size() <= 65536 && entry.at("accept").is_boolean());
            const bool expected = entry.at("accept").get<bool>();
            ensure(accepts(standalone, text) == expected);
            // Native output-format grammar starts before generation_prompt;
            // the server sampler prefills that already-rendered assistant text.
            ensure(accepts(native_grammar, final_parser.generation_prompt + text) == expected);
            if (expected) {
                auto final = common_chat_parse(text, false, final_parser);
                ensure(final.content == text && final.reasoning_content.empty() && final.tool_calls.empty());
                ensure(final.to_json_oaicompat().at("content") == text);
            }
            expected ? ++passing : ++rejecting;
        }
        ensure(passing >= 7 && rejecting >= 10);
        json result = {{"status","PASS"}, {"kind","NATIVE_CONTRACT_CPU_PREFLIGHT"},
                       {"schema_cases_accepted",passing}, {"schema_cases_rejected",rejecting},
                       {"native_final_content_exact_cases",passing},
                       {"native_grammar_generation_prompt_prefilled",true},
                       {"native_grammar_prefill_bytes",final_parser.generation_prompt.size()},
                       {"core_dump_limit_zero",true},
                       {"native_sampling_schema_binding",true},
                       {"native_request_grammar_nonempty",true}, {"grammar_lazy",false},
                       {"grammar_triggers",0}, {"native_grammar_bytes",native_grammar.size()},
                       {"standalone_grammar_bytes",standalone.size()},
                       {"native_request_prompt_bytes",native.at("prompt").get<std::string>().size()},
                       {"model_context_created",false}, {"backend_init_called",false},
                       {"weight_tensors_loaded",false}, {"native_tokenization","NOT_RUN"}};
        if (argc == 4) {
            // Root alone may enable this AFTER full GGUF SHA/header audit.
            auto params = llama_model_default_params();
            ggml_backend_dev_t devices[] = {nullptr};
            params.devices = devices;
            params.n_gpu_layers = 0;
            params.vocab_only = true;
            params.no_alloc = true;
            params.load_mode = LLAMA_LOAD_MODE_NONE;
            params.load_mtp = false;
            std::unique_ptr<llama_model, decltype(&llama_model_free)> model(
                llama_model_load_from_file(argv[3], params), &llama_model_free);
            ensure(model != nullptr);
            const auto * vocab = llama_model_get_vocab(model.get());
            const char * embedded = llama_model_chat_template(model.get(), nullptr);
            ensure(embedded != nullptr && template_text == embedded);
            options.tmpls = common_chat_templates_init(model.get(), "");
            const auto actual_native = request_parse(bundle.at("request"), options, schema);
            ensure(actual_native.at("prompt") == native.at("prompt"));
            ensure(actual_native.at("grammar") == native.at("grammar"));
            ensure(actual_native.at("generation_prompt") == native.at("generation_prompt"));
            for (const auto & entry : bundle.at("cases")) {
                ensure(accepts_tokens(vocab, native_grammar, final_parser.generation_prompt,
                                      entry.at("text").get<std::string>()) == entry.at("accept").get<bool>());
            }
            result["native_vocab_grammar_cases_accepted"] = passing;
            result["native_vocab_grammar_cases_rejected"] = rejecting;
            result["native_vocab_grammar_eog_checked"] = true;
            result["tokenizer_metadata_parity"] = "NOT_RUN";
            if (bundle.contains("tokenizer_parity")) {
                const auto & parity = bundle.at("tokenizer_parity");
                ensure(parity.is_array() && !parity.empty() && parity.size() <= 32);
                for (const auto & entry : parity) {
                    ensure(entry.is_object() && entry.size() == 2);
                    const auto text = entry.at("text").get<std::string>();
                    ensure(text.size() <= 8192);
                    const auto & expected = entry.at("expected_token_ids");
                    ensure(expected.is_array() && expected.size() <= 4096);
                    std::vector<llama_token> expected_tokens;
                    for (const auto & id : expected) {
                        ensure(id.is_number_integer());
                        const auto token_id = id.get<int64_t>();
                        ensure(token_id >= 0 && token_id <= std::numeric_limits<llama_token>::max());
                        expected_tokens.push_back(static_cast<llama_token>(token_id));
                    }
                    ensure(common_tokenize(vocab, text, false, true) == expected_tokens);
                }
                result["tokenizer_metadata_parity"] = "PASS";
                result["tokenizer_metadata_parity_cases"] = parity.size();
            }
            ensure(bundle.at("context_requests").is_array() && bundle.at("context_requests").size() <= 200);
            size_t largest = 0, smallest = std::numeric_limits<size_t>::max();
            for (const auto & request : bundle.at("context_requests")) {
                const auto rendered = request_parse(request, options, schema).at("prompt").get<std::string>();
                ensure(rendered.size() <= 128 * 1024);
                int32_t n = llama_tokenize(vocab, rendered.data(), static_cast<int32_t>(rendered.size()),
                                           nullptr, 0, true, true);
                ensure(n < 0 && n != std::numeric_limits<int32_t>::min());
                n = -n;
                std::vector<llama_token> tokens(static_cast<size_t>(n));
                ensure(llama_tokenize(vocab, rendered.data(), static_cast<int32_t>(rendered.size()),
                                       tokens.data(), n, true, true) == n);
                largest = std::max(largest, static_cast<size_t>(n));
                smallest = std::min(smallest, static_cast<size_t>(n));
            }
            ensure(!bundle.at("context_requests").empty());
            const size_t cap = bundle.at("max_output_tokens").get<size_t>();
            ensure(cap == 768 && largest + cap <= 4096);
            result["native_tokenization"] = "PASS_VOCAB_ONLY";
            result["embedded_template_exact_match"] = true;
            result["native_embedded_vs_external_prompt_grammar_match"] = true;
            result["input_count"] = bundle.at("context_requests").size();
            result["min_input_tokens"] = smallest;
            result["max_input_tokens"] = largest;
            result["max_input_plus_output"] = largest + cap;
        }
        const auto stderr_bytes = stderr_capture->finish();
        ensure(stderr_bytes == 0);
        result["discarded_stderr_bytes"] = stderr_bytes;
        std::cout << result.dump() << std::endl;
        return 0;
    } catch (const std::exception &) {
        // Never echo exception.what(), source strings, model outputs, or tokens.
        const auto stderr_bytes = stderr_capture ? stderr_capture->finish() : 0;
        std::cout << json({{"kind","NATIVE_CONTRACT_CPU_PREFLIGHT"},{"status","FAIL"},
                          {"code","CHECK_FAILED"},{"discarded_stderr_bytes",stderr_bytes}}).dump() << std::endl;
        return 1;
    }
}
