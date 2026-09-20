"""Loopback-only final-completion transport with explicit local server dialects.

No external fallback, redirects, environment proxies, response logging or stored
reasoning. This transport performs no IFC/approval operation.
"""

from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from http.client import HTTPException
import ipaddress
import json
import math
from pathlib import Path
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import UUID

from neurobuild.application.requirement_generation import GenerationContract, parse_generated_requirement
from neurobuild.application.requirements import MAX_RESPONSE_CHARS, MAX_SOURCE_CHARS
from neurobuild.domain.contracts import SemanticRequirement
from neurobuild.domain.errors import DomainError


MAX_HTTP_RESPONSE_BYTES = 262144
_ROOT = Path(__file__).resolve().parents[3]


def _error(code: str) -> None:
    messages = {
        "LOCAL_MODEL_CONFIG_INVALID": "Local model client configuration is invalid",
        "LOCAL_MODEL_INPUT_INVALID": "Local model requirement input is invalid",
        "LOCAL_MODEL_UNAVAILABLE": "Local model service is unavailable",
        "LOCAL_MODEL_TIMEOUT": "Local model request timed out",
        "LOCAL_MODEL_HTTP_ERROR": "Local model service rejected the request",
        "LOCAL_MODEL_RESPONSE_INVALID": "Local model response is invalid",
        "LOCAL_MODEL_TRUNCATED": "Local model did not complete the final response",
        "LOCAL_MODEL_RESPONSE_TOO_LARGE": "Local model response exceeds the size limit",
        "LOCAL_MODEL_REASONING_CONTENT": "Local model returned reasoning in final content",
    }
    raise DomainError(code, messages[code]) from None


def _clean_text(value: object, maximum: int) -> bool:
    return (type(value) is str and 0 < len(value) <= maximum and bool(value.strip())
            and not any(ord(char) == 0 or 0xD800 <= ord(char) <= 0xDFFF for char in value))


def _endpoint(base_url: str) -> str:
    if type(base_url) is not str or not base_url or any(char.isspace() for char in base_url):
        _error("LOCAL_MODEL_CONFIG_INVALID")
    try:
        parsed = urlsplit(base_url)
        if (parsed.scheme != "http" or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or parsed.path not in ("", "/", "/v1", "/v1/")):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        host = parsed.hostname
        # Fix localhost to a numeric loopback address; neither DNS rebinding nor
        # environment proxy settings can turn this into an external request.
        address = ipaddress.ip_address("127.0.0.1" if host == "localhost" else host)
        if (not address.is_loopback or "%" in str(address)
                or (address.version == 6 and address.ipv4_mapped is not None)):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        port = 80 if parsed.port is None else parsed.port
        if not 1 <= port <= 65535:
            _error("LOCAL_MODEL_CONFIG_INVALID")
    except (TypeError, ValueError):
        _error("LOCAL_MODEL_CONFIG_INVALID")
    authority = f"[{address.compressed}]" if address.version == 6 else address.compressed
    return f"http://{authority}:{port}/v1/chat/completions"


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _error("LOCAL_MODEL_RESPONSE_INVALID")
        result[key] = value
    return result


def _constant(_: str) -> None:
    _error("LOCAL_MODEL_RESPONSE_INVALID")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class Completion:
    """Final content and safe measured metadata; never the raw HTTP envelope."""

    content: str
    usage: dict[str, int] | None
    latency_seconds: float
    model: str


class StructuredOutputProtocol(StrEnum):
    LEGACY_GUIDED_JSON = "legacy_guided_json"
    STRUCTURED_OUTPUTS = "structured_outputs"
    LLAMA_CPP_JSON_SCHEMA = "llama_cpp_json_schema"


class SamplingProfile(StrEnum):
    LEGACY_GREEDY = "legacy_greedy"
    QWEN3_NONTHINKING = "qwen3_nonthinking"
    QWEN3_NONTHINKING_AWQ = "qwen3_nonthinking_awq"
    QWEN3_THINKING_AWQ = "qwen3_thinking_awq"
    QWEN38_NONTHINKING_LLAMA_CPP = "qwen38_nonthinking_llama_cpp"


class LocalJSONCompletionClient:
    """Shared safe transport for one explicitly configured JSON contract."""

    def __init__(
        self, base_url: str, model: str, *, timeout: float = 60.0, max_tokens: int = 768,
        prompt_path: Path, schema_path: Path, expected_schema_version: str,
        protocol: StructuredOutputProtocol | str = StructuredOutputProtocol.LEGACY_GUIDED_JSON,
        sampling_profile: SamplingProfile | str = SamplingProfile.LEGACY_GREEDY,
    ) -> None:
        self.endpoint = _endpoint(base_url)
        if type(protocol) not in (str, StructuredOutputProtocol):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        try:
            self._protocol = StructuredOutputProtocol(protocol)
        except ValueError:
            _error("LOCAL_MODEL_CONFIG_INVALID")
        if type(sampling_profile) not in (str, SamplingProfile):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        try:
            self._sampling_profile = SamplingProfile(sampling_profile)
        except ValueError:
            _error("LOCAL_MODEL_CONFIG_INVALID")
        if (self._sampling_profile is SamplingProfile.QWEN38_NONTHINKING_LLAMA_CPP
                and self._protocol is not StructuredOutputProtocol.LLAMA_CPP_JSON_SCHEMA):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        if (self._protocol is StructuredOutputProtocol.LLAMA_CPP_JSON_SCHEMA
                and self._sampling_profile not in (SamplingProfile.LEGACY_GREEDY,
                                                   SamplingProfile.QWEN38_NONTHINKING_LLAMA_CPP)):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        if not _clean_text(expected_schema_version, 64):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        self._expected_schema_version = expected_schema_version
        if (not _clean_text(model, 256) or any(ord(char) < 32 for char in model)
                or type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 300
                or type(max_tokens) is not int or not 1 <= max_tokens <= 2048):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        self.model = model
        self.timeout = float(timeout)
        self.max_tokens = max_tokens
        try:
            prompt_bytes = prompt_path.read_bytes()
            schema_bytes = schema_path.read_bytes()
            if not 0 < len(prompt_bytes) <= 65536 or not 0 < len(schema_bytes) <= 65536:
                _error("LOCAL_MODEL_CONFIG_INVALID")
            self._prompt = prompt_bytes.decode("utf-8")
            self._schema = json.loads(schema_bytes.decode("utf-8"))
            if not self._prompt.strip() or type(self._schema) is not dict:
                _error("LOCAL_MODEL_CONFIG_INVALID")
            # Explicit custom paths cannot silently select a different output
            # contract. Every generation requires the same version-enum binding.
            properties = self._schema.get("properties")
            version = properties.get("schema_version") if type(properties) is dict else None
            if (type(version) is not dict
                    or version.get("enum") != [self._expected_schema_version]):
                _error("LOCAL_MODEL_CONFIG_INVALID")
        except (OSError, UnicodeError, ValueError, AttributeError):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        self.prompt_sha256 = sha256(prompt_bytes).hexdigest()
        self.schema_sha256 = sha256(schema_bytes).hexdigest()
        self._opener = build_opener(ProxyHandler({}), _NoRedirect())

    @property
    def protocol(self) -> StructuredOutputProtocol:
        """Configured dialect, not a claim about the server's grammar backend."""
        return self._protocol

    @property
    def sampling_profile(self) -> SamplingProfile:
        """Explicit fixed recipe; never inferred from model name or response."""
        return self._sampling_profile

    @property
    def schema(self) -> dict:
        """Detached configured schema for validation and reproducible metadata."""
        return deepcopy(self._schema)

    @property
    def enable_thinking(self) -> bool:
        """Request mode only; matching server parser configuration is separate."""
        return self.sampling_profile is SamplingProfile.QWEN3_THINKING_AWQ

    @property
    def sampling_parameters(self) -> dict[str, int | float | list[str]]:
        """Fresh copy of exactly the sampling fields sent, also for manifests.

        Legacy omitted fields remain omitted; their server defaults are not
        represented as measured values. A profile does not select a server parser.
        """
        if self.sampling_profile is SamplingProfile.LEGACY_GREEDY:
            return {"temperature": 0, "seed": 42}
        if self.sampling_profile is SamplingProfile.QWEN3_NONTHINKING:
            return {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0,
                    "presence_penalty": 0.0, "frequency_penalty": 0.0,
                    "repetition_penalty": 1.0, "seed": 42}
        if self.sampling_profile is SamplingProfile.QWEN3_NONTHINKING_AWQ:
            return {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0,
                    "presence_penalty": 1.5, "frequency_penalty": 0.0,
                    "repetition_penalty": 1.0, "seed": 42}
        if self.sampling_profile is SamplingProfile.QWEN3_THINKING_AWQ:
            return {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
                    "presence_penalty": 1.5, "frequency_penalty": 0.0,
                    "repetition_penalty": 1.0, "seed": 42}
        if self.sampling_profile is SamplingProfile.QWEN38_NONTHINKING_LLAMA_CPP:
            # Native penalties include prompt tokens. Keep them disabled for
            # exact quote extraction; this is an explicit experimental recipe,
            # not the model card's presence-penalty recommendation.
            return {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0,
                    "presence_penalty": 0.0, "frequency_penalty": 0.0,
                    "repeat_penalty": 1.0, "repeat_last_n": 0, "seed": 42,
                    "samplers": ["temperature", "top_k", "top_p", "min_p"]}
        _error("LOCAL_MODEL_CONFIG_INVALID")

    def complete(self, source_text: str, *, axis_convention: str | None = None) -> Completion:
        """Return final content for synthetic evaluation, without semantic claims.

        Invalid final JSON may be returned for scoring; truncated envelopes,
        tool calls and explicit reasoning blocks never reach this boundary.
        ``latency_seconds`` is end-to-end, not TTFT or decode-only duration.
        """
        return self._complete(source_text, axis_convention=axis_convention)

    def _complete(
        self, source_text: str, *, axis_convention: str | None = None,
        classified_decision: str | None = None, schema_override: dict | None = None,
    ) -> Completion:
        """Internal staged transport; the caller binds a schema before the request.

        Additional context cannot replace the original source or axis context.
        The ordinary complete() path supplies neither override and retains its
        exact historical payload, including omission of sampling fields.
        """
        if not _clean_text(source_text, MAX_SOURCE_CHARS) or axis_convention not in (None, "project_xy"):
            _error("LOCAL_MODEL_INPUT_INVALID")
        selected_schema = self._schema
        user_input = {"source_text": source_text, "axis_convention": axis_convention}
        if (classified_decision is None) != (schema_override is None):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        if classified_decision is not None:
            if (type(classified_decision) is not str
                    or classified_decision not in ("READY", "CLARIFICATION", "UNSUPPORTED")
                    or type(schema_override) is not dict):
                _error("LOCAL_MODEL_CONFIG_INVALID")
            properties = schema_override.get("properties")
            version = properties.get("schema_version") if type(properties) is dict else None
            if type(version) is not dict or version.get("enum") != [self._expected_schema_version]:
                _error("LOCAL_MODEL_CONFIG_INVALID")
            selected_schema = deepcopy(schema_override)
            user_input["classified_decision"] = classified_decision
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._prompt},
                {"role": "user", "content": json.dumps(user_input, ensure_ascii=False)},
            ],
            **self.sampling_parameters, "max_tokens": self.max_tokens, "stream": False,
            "chat_template_kwargs": {"enable_thinking": self.enable_thinking},
        }
        if self.protocol is StructuredOutputProtocol.LEGACY_GUIDED_JSON:
            payload.update(guided_json=selected_schema, guided_decoding_backend="xgrammar:no-fallback")
        elif self.protocol is StructuredOutputProtocol.STRUCTURED_OUTPUTS:
            # Modern backend selection belongs to pinned server launch config.
            # Never add legacy fields, infer support, or retry without a schema.
            payload["structured_outputs"] = {"json": selected_schema}
        elif self.protocol is StructuredOutputProtocol.LLAMA_CPP_JSON_SCHEMA:
            payload["response_format"] = {"type": "json_schema", "json_schema": {"schema": selected_schema}}
        else:
            _error("LOCAL_MODEL_CONFIG_INVALID")
        request = Request(self.endpoint, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        started = time.monotonic()
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    _error("LOCAL_MODEL_HTTP_ERROR")
                content_type = response.headers.get_content_type()
                if content_type != "application/json":
                    _error("LOCAL_MODEL_RESPONSE_INVALID")
                declared = response.headers.get("Content-Length")
                if declared is not None:
                    try:
                        length = int(declared)
                    except ValueError:
                        _error("LOCAL_MODEL_RESPONSE_INVALID")
                    if length < 0:
                        _error("LOCAL_MODEL_RESPONSE_INVALID")
                    if length > MAX_HTTP_RESPONSE_BYTES:
                        _error("LOCAL_MODEL_RESPONSE_TOO_LARGE")
                chunks = []
                size = 0
                while True:
                    if time.monotonic() - started > self.timeout:
                        _error("LOCAL_MODEL_TIMEOUT")
                    chunk = response.read1(min(65536, MAX_HTTP_RESPONSE_BYTES + 1 - size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > MAX_HTTP_RESPONSE_BYTES:
                        _error("LOCAL_MODEL_RESPONSE_TOO_LARGE")
                raw = b"".join(chunks)
                if declared is not None and len(raw) != length:
                    _error("LOCAL_MODEL_RESPONSE_INVALID")
        except HTTPError as exc:
            exc.close()
            _error("LOCAL_MODEL_HTTP_ERROR")
        except (TimeoutError, socket.timeout):
            _error("LOCAL_MODEL_TIMEOUT")
        except URLError as exc:
            _error("LOCAL_MODEL_TIMEOUT" if isinstance(exc.reason, (TimeoutError, socket.timeout)) else "LOCAL_MODEL_UNAVAILABLE")
        except OSError:
            _error("LOCAL_MODEL_UNAVAILABLE")
        except HTTPException:
            _error("LOCAL_MODEL_RESPONSE_INVALID")
        elapsed = time.monotonic() - started
        if elapsed > self.timeout:
            _error("LOCAL_MODEL_TIMEOUT")
        try:
            envelope = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
        except (UnicodeError, ValueError, RecursionError):
            _error("LOCAL_MODEL_RESPONSE_INVALID")
        if (type(envelope) is not dict or envelope.get("model") != self.model
                or type(envelope.get("choices")) is not list or len(envelope["choices"]) != 1):
            _error("LOCAL_MODEL_RESPONSE_INVALID")
        choice = envelope["choices"][0]
        if type(choice) is not dict or type(choice.get("index")) is not int or choice["index"] != 0:
            _error("LOCAL_MODEL_RESPONSE_INVALID")
        if choice.get("finish_reason") != "stop":
            _error("LOCAL_MODEL_TRUNCATED")
        message = choice.get("message")
        if (type(message) is not dict or message.get("role") != "assistant"
                or message.get("tool_calls") not in (None, []) or message.get("function_call") is not None
                or not _clean_text(message.get("content"), MAX_RESPONSE_CHARS)):
            _error("LOCAL_MODEL_RESPONSE_INVALID")
        content = message["content"]
        if "<think" in content.lower() or "</think" in content.lower():
            _error("LOCAL_MODEL_REASONING_CONTENT")
        usage = envelope.get("usage")
        safe_usage = {}
        if usage is not None:
            if type(usage) is not dict:
                _error("LOCAL_MODEL_RESPONSE_INVALID")
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if key in usage and usage[key] is not None:
                    if type(usage[key]) is not int or not 0 <= usage[key] <= 2147483647:
                        _error("LOCAL_MODEL_RESPONSE_INVALID")
                    safe_usage[key] = usage[key]
            details = usage.get("completion_tokens_details")
            if details is not None:
                if type(details) is not dict:
                    _error("LOCAL_MODEL_RESPONSE_INVALID")
                count = details.get("reasoning_tokens")
                if count is not None:
                    if type(count) is not int or not 0 <= count <= 2147483647:
                        _error("LOCAL_MODEL_RESPONSE_INVALID")
                    safe_usage["reasoning_tokens"] = count
        return Completion(content, safe_usage or None, elapsed, self.model)


class LocalRequirementClient(LocalJSONCompletionClient):
    """One request with an explicitly selected generation contract."""

    def __init__(
        self, base_url: str, model: str, *, timeout: float = 60.0, max_tokens: int = 768,
        prompt_path: Path | None = None, schema_path: Path | None = None,
        protocol: StructuredOutputProtocol | str = StructuredOutputProtocol.LEGACY_GUIDED_JSON,
        sampling_profile: SamplingProfile | str = SamplingProfile.LEGACY_GREEDY,
        generation_contract: GenerationContract | str = GenerationContract.LEGACY,
    ) -> None:
        if type(generation_contract) not in (str, GenerationContract):
            _error("LOCAL_MODEL_CONFIG_INVALID")
        try:
            self._generation_contract = GenerationContract(generation_contract)
        except ValueError:
            _error("LOCAL_MODEL_CONFIG_INVALID")
        if self.generation_contract is GenerationContract.LEGACY:
            default_prompt = _ROOT / "prompts/requirement_v3.txt"
            default_schema = _ROOT / "schemas/semantic_requirement.schema.json"
        elif self.generation_contract is GenerationContract.QUOTES:
            default_prompt = _ROOT / "prompts/requirement_generation_v2_v1.txt"
            default_schema = _ROOT / "schemas/requirement_generation_v2.schema.json"
        elif self.generation_contract is GenerationContract.FACTS:
            default_prompt = _ROOT / "prompts/requirement_generation_v3_v1.txt"
            default_schema = _ROOT / "schemas/requirement_generation_v3.schema.json"
        else:
            _error("LOCAL_MODEL_CONFIG_INVALID")
        super().__init__(
            base_url, model, timeout=timeout, max_tokens=max_tokens,
            prompt_path=prompt_path or default_prompt, schema_path=schema_path or default_schema,
            expected_schema_version=self.generation_contract.value, protocol=protocol,
            sampling_profile=sampling_profile,
        )

    @property
    def generation_contract(self) -> GenerationContract:
        """Explicit output contract; never detected from model output or files."""
        return self._generation_contract

    def extract(
        self, source_text: str, *, requirement_id: UUID, project_id: UUID,
        base_revision_id: UUID, axis_convention: str | None = None,
    ) -> SemanticRequirement:
        if not all(type(value) is UUID for value in (requirement_id, project_id, base_revision_id)):
            _error("LOCAL_MODEL_INPUT_INVALID")
        result = self.complete(source_text, axis_convention=axis_convention)
        return parse_generated_requirement(
            result.content, generation_contract=self.generation_contract,
            source_text=source_text, requirement_id=requirement_id,
            project_id=project_id, base_revision_id=base_revision_id, axis_convention=axis_convention,
        )
