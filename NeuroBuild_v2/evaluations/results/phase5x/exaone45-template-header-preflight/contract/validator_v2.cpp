// EXAONE 4.5 metadata-only CPU checker; actual native HTTP/chat/GBNF/parser.
// No HTTP listener/client, decode, context, backend_init, or model inference.
// Only public synthetic request/corpus; GGUF/model/context loading is absent.
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
        ensure(argc == 3);
        const char * visible = std::getenv("CUDA_VISIBLE_DEVICES");
        ensure(visible != nullptr && std::string(visible).empty());
        stderr_capture = std::make_unique<stderr_counter>();
        common_log_set_verbosity_thold(-1);
        llama_log_set(silent_log, nullptr);
        // argv1 is verified template; argv2 exact schema. No model argument exists.
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
        const auto original_user = bundle.at("request").at("messages").at(1).at("content").get<std::string>();
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
                       {"schema_cases_accepted",passing}, {"schema_cases_rejected",rejecting},
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
        const auto stderr_bytes = stderr_capture->finish();
        ensure(stderr_bytes == 0);
        result["discarded_stderr_bytes"] = stderr_bytes;
        std::cout << result.dump() << std::endl;
        return 0;
    } catch (const std::exception &) {
        const auto stderr_bytes = stderr_capture ? stderr_capture->finish() : 0;
        json failure = {{"kind","EXAONE45_NATIVE_PUBLIC_CONTRACT_CPU_PREFLIGHT"},{"status","FAIL"},
                        {"code","CHECK_FAILED"},{"stage",check_stage},{"check_line",check_line},
                        {"discarded_stderr_bytes",stderr_bytes}};
        std::cout << failure.dump() << std::endl;
        return 1;
    }
}
