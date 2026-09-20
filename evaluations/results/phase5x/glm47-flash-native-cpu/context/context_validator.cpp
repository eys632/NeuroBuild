// GLM-4.7-Flash context-only CPU validator; separate from immutable public/vocab proofs.
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
        ensure(argc == 4);
        const char * visible = std::getenv("CUDA_VISIBLE_DEVICES");
        ensure(visible != nullptr && std::string(visible).empty());
        stderr_capture = std::make_unique<stderr_counter>();
        common_log_set_verbosity_thold(-1);
        llama_log_set(silent_log, nullptr);
        const auto template_text = read_file(argv[1], 128 * 1024);
        const auto schema = json::parse(read_file(argv[2], 128 * 1024));
        const auto bundle = json::parse(read_bounded(std::cin, 16 * 1024 * 1024));
        ensure(bundle.at("reference_kind") == "official_pinned_tokenizer_no_normalizer_change");
        ensure(bundle.at("audited_official_vocab_pass") == true);
        ensure(bundle.at("max_output_tokens").is_number_integer() && bundle.at("max_output_tokens").get<int64_t>() == 768);
        const auto & requests = bundle.at("context_requests");
        ensure(requests.is_array() && !requests.empty() && requests.size() <= 120);
        ensure(bundle.at("expected_count").is_number_integer() && bundle.at("expected_count").get<int64_t>() == static_cast<int64_t>(requests.size()));
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
        ensure(!llama_vocab_get_add_bos(vocab) && !llama_vocab_get_add_eos(vocab));
        server_chat_params options{};
        options.use_jinja = true;
        options.prefill_assistant = false;
        options.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;
        options.enable_thinking = false;
        options.allow_image = options.allow_audio = options.allow_video = false;
        options.force_pure_content = false;
        options.chat_template_kwargs = {{"enable_thinking", "false"}};
        options.tmpls = common_chat_templates_init(model.get(), template_text);
        size_t largest = 0, smallest = std::numeric_limits<size_t>::max(), checked = 0;
        std::string fixed_grammar;
        check_stage = 100;
        for (const auto & request : requests) {
            const auto native = request_parse(request, options, schema);
            const auto & messages = request.at("messages");
            ensure(messages.size() == 2 && messages.at(0).at("role") == "system" && messages.at(1).at("role") == "user");
            const auto system = messages.at(0).at("content").get<std::string>();
            const auto user = messages.at(1).at("content").get<std::string>();
            const auto expected = "[gMASK]<sop><|system|>" + system + "<|user|>" + user + "<|assistant|></think>";
            const auto rendered = native.at("prompt").get<std::string>();
            ensure(rendered == expected && rendered.size() <= 128 * 1024);
            ensure(native.at("generation_prompt") == "<|assistant|></think>");
            const auto grammar = native.at("grammar").get<std::string>();
            if (checked == 0) fixed_grammar = grammar;
            ensure(grammar == fixed_grammar);
            json fields = json::object();
            for (const auto * key : {"temperature", "top_p", "top_k", "min_p", "presence_penalty", "frequency_penalty", "repeat_penalty", "repeat_last_n", "seed", "samplers", "max_tokens"}) fields[key] = native.at(key);
            common_params base;
            base.reasoning_format = COMMON_REASONING_FORMAT_DEEPSEEK;
            const auto sampling = server_schema::eval_llama_cmpl_schema(nullptr, base, {}, fields);
            const auto & sp = sampling.sampling;
            ensure(sp.temp == 1.0f && std::abs(sp.top_p - 0.95f) < 1e-6f && sp.top_k == 0 && sp.min_p == 0 &&
                   sp.penalty_present == 0 && sp.penalty_freq == 0 && sp.penalty_repeat == 1 &&
                   sp.penalty_last_n == 0 && sp.seed == 42 && sampling.n_predict == 768);
            std::vector<std::string> names;
            for (auto kind : sp.samplers) names.push_back(common_sampler_type_to_str(kind));
            ensure(names == std::vector<std::string>({"temperature", "top_k", "top_p", "min_p"}));
            const auto tokens = common_tokenize(vocab, rendered, true, true);
            ensure(!tokens.empty());
            ensure(common_detokenize(vocab, tokens, true) == rendered);
            largest = std::max(largest, tokens.size()); smallest = std::min(smallest, tokens.size());
            ++checked; ++check_stage;
        }
        ensure(checked == requests.size() && largest + 768 <= 4096);
        const auto stderr_bytes = stderr_capture->finish();
        ensure(stderr_bytes == 0);
        json result = {{"kind", "GLM47_FLASH_NATIVE_CONTEXT_CPU_COUNTS"}, {"status", "PASS"},
            {"input_count", checked}, {"min_input_tokens", smallest}, {"max_input_tokens", largest},
            {"max_input_plus_output", largest + 768}, {"all_context_system_user_bytes_exact", true},
            {"all_context_prompt_raw_roundtrips_exact", true}, {"embedded_template_exact_match", true},
            {"native_generation_prompt_exact", true}, {"native_schema_grammar_fixed", true},
            {"native_sampling_schema_binding", true}, {"grammar_lazy", false},
            {"core_dump_limit_zero", true}, {"model_context_created", false}, {"backend_init_called", false},
            {"weight_tensors_loaded", false}, {"public_tokenizer_cases_repeated", 0}, {"discarded_stderr_bytes", stderr_bytes}};
        std::cout << result.dump() << std::endl;
        return 0;
    } catch (const std::exception &) {
        const auto stderr_bytes = stderr_capture ? stderr_capture->finish() : 0;
        json failure = {{"kind", "GLM47_FLASH_NATIVE_CONTEXT_CPU_COUNTS"}, {"status", "FAIL"},
                        {"code", "CHECK_FAILED"}, {"stage", check_stage}, {"check_line", check_line},
                        {"discarded_stderr_bytes", stderr_bytes}};
        std::cout << failure.dump() << std::endl;
        return 1;
    }
}
