// GLM-4.7-Flash public CPU contract; prepared, not yet compiled or executed.
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
        // Check all three published GLM stopping IDs without consuming one
        // before checking the others, so each sees the same grammar state.
        bool all_endings_accepted = true;
        for (const auto end_id : {154820, 154827, 154829}) {
            ensure(llama_vocab_is_eog(vocab, end_id));
            llama_token_data end{end_id, 0.0f, 0.0f};
            llama_token_data_array ending{&end, 1, -1, false};
            llama_grammar_apply_impl(*grammar, &ending);
            all_endings_accepted = all_endings_accepted && std::isfinite(end.logit);
        }
        return all_endings_accepted;
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
        const rlimit no_core{0, 0};
        ensure(setrlimit(RLIMIT_CORE, &no_core) == 0);
        ensure(argc == 3 || argc == 4);
        const char * visible = std::getenv("CUDA_VISIBLE_DEVICES");
        ensure(visible != nullptr && std::string(visible).empty());
        stderr_capture = std::make_unique<stderr_counter>();
        common_log_set_verbosity_thold(-1);
        llama_log_set(silent_log, nullptr);
        const auto template_text = read_file(argv[1], 128 * 1024);
        const auto schema = json::parse(read_file(argv[2], 128 * 1024));
        const auto bundle = json::parse(read_bounded(std::cin, 2 * 1024 * 1024));
        ensure(bundle.at("reference_kind") == "official_pinned_tokenizer_no_normalizer_change");
        ensure(bundle.at("cases").is_array() && bundle.at("cases").size() == 30);
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
        options.tmpls = common_chat_templates_init(nullptr, template_text, "[gMASK]", "<|endoftext|>");
        const auto native = request_parse(bundle.at("request"), options, schema);
        check_stage = 20;
        const auto & template_cases = bundle.at("template_cases");
        ensure(template_cases.is_array() && template_cases.size() == 20);
        size_t render_equal = 0;
        for (const auto & entry : template_cases) {
            const auto expected = entry.at("expected_render").get<std::string>();
            ensure(expected.size() <= 65536);
            ensure(render_direct(template_text, entry.at("variables")) == expected);
            ++render_equal;
        }
        const auto & messages = bundle.at("request").at("messages");
        ensure(messages.size() == 2 && messages.at(0).at("role") == "system" && messages.at(1).at("role") == "user");
        const auto system = messages.at(0).at("content").get<std::string>();
        const auto user = messages.at(1).at("content").get<std::string>();
        const auto expected_prompt = template_cases.at(0).at("expected_render").get<std::string>();
        const std::string expected_generation_prompt = "<|assistant|></think>";
        const auto exact_prompt = "[gMASK]<sop><|system|>" + system + "<|user|>" + user + expected_generation_prompt;
        ensure(expected_prompt == exact_prompt);
        ensure(native.at("prompt").get<std::string>() == expected_prompt);
        ensure(expected_prompt.find(system) != std::string::npos && expected_prompt.find(user) != std::string::npos);
        check_stage = 30;
        json sampling_fields = json::object();
        for (const auto * key : {"temperature", "top_p", "top_k", "min_p", "presence_penalty",
                                "frequency_penalty", "repeat_penalty", "repeat_last_n", "seed", "samplers", "max_tokens"}) {
            sampling_fields[key] = native.at(key);
        }
        common_params base;
        base.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;
        const auto parsed_sampling = server_schema::eval_llama_cmpl_schema(nullptr, base, {}, sampling_fields);
        const auto & sp = parsed_sampling.sampling;
        ensure(sp.temp == 1.0f && std::abs(sp.top_p - 0.95f) < 1e-6f && sp.top_k == 0 && sp.min_p == 0 &&
               sp.penalty_present == 0 && sp.penalty_freq == 0 && sp.penalty_repeat == 1 &&
               sp.penalty_last_n == 0 && sp.seed == 42 && parsed_sampling.n_predict == 768);
        std::vector<std::string> sampler_names;
        for (auto kind : sp.samplers) sampler_names.push_back(common_sampler_type_to_str(kind));
        ensure(sampler_names == std::vector<std::string>({"temperature", "top_k", "top_p", "min_p"}));
        const auto native_grammar = native.at("grammar").get<std::string>();
        common_chat_parser_params final_parser;
        final_parser.format = static_cast<common_chat_format>(native.at("chat_format").get<int>());
        final_parser.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;
        final_parser.reasoning_in_content = false;
        final_parser.generation_prompt = native.at("generation_prompt").get<std::string>();
        final_parser.parser.load(native.at("chat_parser").get<std::string>());
        final_parser.debug = false;
        ensure(final_parser.format == COMMON_CHAT_FORMAT_PEG_NATIVE);
        ensure(final_parser.generation_prompt == expected_generation_prompt);
        auto fenced = [](const std::string & text) { return "```json\n" + text + "\n```"; };
        size_t passing = 0, rejecting = 0, exact_final = 0;
        check_stage = 40;
        for (const auto & entry : bundle.at("cases")) {
            const auto text = entry.at("text").get<std::string>();
            ensure(text.size() <= 65536 && entry.at("accept").is_boolean());
            const bool expected = entry.at("accept").get<bool>();
            ensure(accepts(standalone, text) == expected);
            for (const auto & wire : {text, fenced(text)}) {
                ensure(accepts(native_grammar, final_parser.generation_prompt + wire) == expected);
                if (expected) {
                    const auto final = common_chat_parse(wire, false, final_parser);
                    ensure(final.content == text && final.reasoning_content.empty() && final.tool_calls.empty());
                    ensure(final.to_json_oaicompat().at("content") == text);
                    ++exact_final;
                }
            }
            expected ? ++passing : ++rejecting;
            ++check_stage;
        }
        ensure(passing == 10 && rejecting == 20 && exact_final == 20);
        const auto valid_json = bundle.at("cases").at(0).at("text").get<std::string>();
        const std::vector<std::string> bad_native{
            "```text\n" + valid_json + "\n```",
            "<tool_call>move<arg_key>x</arg_key><arg_value>1</arg_value></tool_call>",
            "<think>PUBLIC_UNFINISHED",
            valid_json + "<tool_call>"
        };
        for (const auto & text : bad_native) ensure(!accepts(native_grammar, final_parser.generation_prompt + text));
        // Pinned native response-format grammar has optional reasoning even
        // when the request disables thinking. Observe the configured prefix;
        // do not replace it with a different mode's generation prefix.
        const std::string public_thought = "PUBLIC_SYNTHETIC_BOUNDARY";
        const auto thought_wire = "<think>" + public_thought + "</think>" + valid_json;
        const bool configured_thought_accepted = accepts(native_grammar, final_parser.generation_prompt + thought_wire);
        const bool wrong_prefix_thought_accepted = accepts(native_grammar, "<|assistant|>" + thought_wire);
        ensure(configured_thought_accepted);
        const auto separated = common_chat_parse(thought_wire, false, final_parser);
        ensure(separated.content == valid_json && separated.reasoning_content == public_thought && separated.tool_calls.empty());
        ensure(separated.to_json_oaicompat().at("content") == valid_json);
        json result = {{"kind", "GLM47_FLASH_NATIVE_PUBLIC_CONTRACT_CPU_PREFLIGHT"}, {"status", "PASS"},
                       {"reference_kind", "official_pinned_tokenizer_no_normalizer_change"},
                       {"public_template_reference_cases", render_equal}, {"native_full_official_prompt_exact", true},
                       {"native_system_user_bytes_exact", true}, {"template_override_used", false},
                       {"schema_cases_accepted", passing}, {"schema_cases_rejected", rejecting},
                       {"native_final_content_exact_cases", exact_final}, {"native_protocol_rejection_cases", bad_native.size()},
                       {"artificial_thought_split_cases", 1}, {"configured_prefix_optional_reasoning_accepted", configured_thought_accepted},
                       {"wrong_prefix_thought_grammar_accepted", wrong_prefix_thought_accepted}, {"other_runtime_mode_executed", false},
                       {"artificial_thought_final_json_exact", true}, {"artificial_thought_reasoning_separated_exact", true},
                       {"artificial_thought_tool_call_count", separated.tool_calls.size()}, {"native_grammar_generation_prompt_prefilled", true},
                       {"native_grammar_prefill_bytes", final_parser.generation_prompt.size()},
                       {"native_sampling_schema_binding", true}, {"grammar_lazy", false},
                       {"core_dump_limit_zero", true}, {"final_json_bytes_unchanged", true},
                       {"native_request_prompt_bytes", expected_prompt.size()},
                       {"model_context_created", false}, {"backend_init_called", false}, {"weight_tensors_loaded", false},
                       {"native_tokenization", "NOT_RUN"}};
        bool gate_pass = true;
        if (argc == 4) {
            // Caller must bind the already-passed full-file/header receipt before supplying this path.
            check_stage = 100;
            ensure(bundle.at("audited_vocab_only") == true);
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
            ensure(llama_vocab_n_tokens(vocab) == 154880 && llama_vocab_bos(vocab) == 154822 &&
                   llama_vocab_eos(vocab) == 154820 && llama_vocab_eot(vocab) == 154827 && llama_vocab_pad(vocab) == 154820);
            ensure(llama_vocab_is_eog(vocab, 154820) && llama_vocab_is_eog(vocab, 154827) && llama_vocab_is_eog(vocab, 154829));
            ensure(!llama_vocab_get_add_bos(vocab) && !llama_vocab_get_add_eos(vocab));
            options.tmpls = common_chat_templates_init(model.get(), template_text);
            const auto actual_native = request_parse(bundle.at("request"), options, schema);
            ensure(actual_native.at("prompt") == native.at("prompt") && actual_native.at("grammar") == native.at("grammar") &&
                   actual_native.at("generation_prompt") == native.at("generation_prompt"));
            check_stage = 110;
            for (const auto & entry : bundle.at("cases")) {
                const auto text = entry.at("text").get<std::string>();
                for (const auto & wire : {text, fenced(text)}) {
                    ensure(accepts_tokens(vocab, native_grammar, final_parser.generation_prompt, wire) == entry.at("accept").get<bool>());
                }
                ++check_stage;
            }
            result["native_vocab_grammar_cases_accepted"] = passing * 2;
            result["native_vocab_grammar_cases_rejected"] = rejecting * 2;
            result["native_vocab_grammar_eog_checked"] = true;
            result["embedded_template_exact_match"] = true;
            result["vocab_backed_official_prompt_exact"] = true;
            const auto & parity = bundle.at("tokenizer_parity");
            ensure(parity.is_array() && parity.size() == 20);
            size_t matches = 0, roundtrips = 0, reference_roundtrips = 0;
            uint64_t mismatch_mask = 0, roundtrip_mismatch_mask = 0;
            check_stage = 200;
            for (size_t i = 0; i < parity.size(); ++i) {
                const auto & entry = parity.at(i);
                ensure(entry.is_object() && entry.size() == 2);
                const auto text = entry.at("text").get<std::string>();
                const auto & expected = entry.at("expected_token_ids");
                ensure(text.size() <= 8192 && expected.is_array() && expected.size() <= 4096);
                std::vector<llama_token> expected_tokens;
                for (const auto & id : expected) {
                    ensure(id.is_number_integer());
                    const auto n = id.get<int64_t>();
                    ensure(n >= 0 && n < llama_vocab_n_tokens(vocab));
                    expected_tokens.push_back(static_cast<llama_token>(n));
                }
                const auto actual = common_tokenize(vocab, text, false, true);
                const bool same = actual == expected_tokens;
                const bool raw = common_detokenize(vocab, actual, true) == text;
                matches += same; roundtrips += raw;
                reference_roundtrips += common_detokenize(vocab, expected_tokens, true) == text;
                if (!same) mismatch_mask |= uint64_t{1} << i;
                if (!raw) roundtrip_mismatch_mask |= uint64_t{1} << i;
                ++check_stage;
            }
            result["native_tokenization"] = "OBSERVED_VOCAB_ONLY";
            result["tokenizer_cases_checked"] = 20;
            result["tokenizer_id_match_count"] = matches;
            result["tokenizer_native_raw_roundtrip_count"] = roundtrips;
            result["tokenizer_reference_ids_raw_roundtrip_count"] = reference_roundtrips;
            result["tokenizer_id_mismatch_mask"] = mismatch_mask;
            result["tokenizer_raw_mismatch_mask"] = roundtrip_mismatch_mask;
            gate_pass = matches == 20 && roundtrips == 20 && reference_roundtrips == 20;
            result["official_hf_equivalence"] = gate_pass ? "PASS" : "FAIL";
            const auto space = common_tokenize(vocab, " ", false, true);
            ensure(space.size() == 1 && !llama_vocab_is_eog(vocab, space.at(0)) && common_detokenize(vocab, space, true) == " ");
            result["resource_probe_token_id"] = space.at(0);
            result["resource_probe_token_count"] = 1;
            result["resource_probe_raw_roundtrip"] = true;
            const auto public_tokens = common_tokenize(vocab, expected_prompt, true, true);
            ensure(!public_tokens.empty() && public_tokens.size() + 768 <= 4096);
            result["public_input_tokens"] = public_tokens.size();
            result["public_input_plus_output"] = public_tokens.size() + 768;
        }
        const auto stderr_bytes = stderr_capture->finish();
        ensure(stderr_bytes == 0);
        result["discarded_stderr_bytes"] = stderr_bytes;
        result["status"] = gate_pass ? "PASS" : "FAIL";
        std::cout << result.dump() << std::endl;
        return gate_pass ? 0 : 1;
    } catch (const std::exception &) {
        const auto stderr_bytes = stderr_capture ? stderr_capture->finish() : 0;
        json failure = {{"kind", "GLM47_FLASH_NATIVE_PUBLIC_CONTRACT_CPU_PREFLIGHT"}, {"status", "FAIL"},
                        {"code", "CHECK_FAILED"}, {"stage", check_stage}, {"check_line", check_line},
                        {"discarded_stderr_bytes", stderr_bytes}};
        std::cout << failure.dump() << std::endl;
        return 1;
    }
}
