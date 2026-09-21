#!/usr/bin/env python3
"""Print declared Phase 0 settings; never start or probe a model runtime."""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILES = ("a100", "rtx5090")
URL_ENV = {
    "PUBLIC_BASE_URL": "public_base_url",
    "FRONTEND_BASE_URL": "frontend_base_url",
    "API_BASE_URL": "api_base_url",
    "MODEL_SERVER_URL": "model_server_url",
}


def read_config(name):
    try:
        with (PROJECT_ROOT / "configs" / name).open(encoding="utf-8") as source:
            value = json.load(source)
    except (OSError, ValueError):
        raise ValueError("Cannot read valid JSON from configs/" + name) from None
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object in configs/" + name)
    return value


def merge(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def validate_url(name, value):
    message = name + " must be an http(s) origin without credentials, path, query or fragment"
    if not isinstance(value, str) or not value or any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError(message)
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
        if (
            parsed.scheme not in ("http", "https")
            or not hostname
            or "@" in parsed.netloc
            or parsed.netloc.endswith(":")
            or "?" in value
            or "#" in value
            or parsed.path not in ("", "/")
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise ValueError(message)
        if ":" in hostname:
            ipaddress.IPv6Address(hostname)
        elif not all(
            re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
            for label in hostname.rstrip(".").split(".")
        ):
            raise ValueError(message)
    except ValueError:
        # Do not echo a rejected URL, which might contain credentials.
        raise ValueError(message) from None


def load_settings(profile):
    settings = merge(read_config("common.json"), read_config(profile + ".json"))
    network = settings["network"]
    for variable, key in URL_ENV.items():
        if variable in os.environ:
            network[key] = os.environ[variable]
        validate_url(variable, network[key])
    runtime = settings["runtime"]
    if "NEUROBUILD_MODEL_ID" in os.environ:
        runtime["model_id"] = os.environ["NEUROBUILD_MODEL_ID"] or None
    if runtime["model_id"] is not None and (
        not isinstance(runtime["model_id"], str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,255}", runtime["model_id"]) is None
    ):
        raise ValueError("NEUROBUILD_MODEL_ID must be a model identifier or empty")
    gpu = settings["gpu"]
    if settings["profile"] != profile or str(gpu["physical_index"]) != gpu["cuda_visible_devices"]:
        raise ValueError("Profile and GPU configuration are inconsistent")
    if runtime["tensor_parallel_size"] != 1:
        raise ValueError("Only tensor_parallel_size=1 is allowed")
    mask = os.environ.get("CUDA_VISIBLE_DEVICES")
    if mask is not None and mask != gpu["cuda_visible_devices"]:
        raise ValueError(
            "CUDA_VISIBLE_DEVICES conflicts with profile {}; required value is {}. "
            "No fallback is allowed.".format(profile, gpu["cuda_visible_devices"])
        )
    return settings, mask


def git_info():
    def git(*arguments):
        try:
            return subprocess.run(
                ["git", "--no-optional-locks", "-C", str(PROJECT_ROOT)] + list(arguments),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
                timeout=5,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None

    commit = git("rev-parse", "--verify", "HEAD")
    status = git("status", "--porcelain", "--untracked-files=normal")
    return {"commit": commit, "dirty": None if status is None else bool(status)}


def print_text(info):
    gpu = info["gpu"]
    runtime = info["runtime"]
    network = info["network"]
    rows = [
        ("Profile", info["profile"]),
        ("Hostname (current)", info["hostname"]),
        ("GPU (configured)", gpu["name"]),
        ("Physical GPU", gpu["physical_index"]),
        ("Required CUDA mask", gpu["cuda_visible_devices"]),
        ("Current CUDA mask", info["current_cuda_visible_devices"] or "UNSET"),
        ("Process device", gpu["process_device"]),
        ("VRAM class (GB)", gpu["vram_class_gb"]),
        ("Hardware status", gpu["hardware_status"]),
        ("Runtime status", runtime["status"]),
        ("Public", network["public_base_url"]),
        ("Frontend", network["frontend_base_url"]),
        ("API", network["api_base_url"]),
        ("Model Server", network["model_server_url"]),
        ("Model", runtime["model_id"] or "UNSET"),
        ("Tensor parallel", runtime["tensor_parallel_size"]),
        ("GPU memory target", runtime["gpu_memory_utilization"]),
        ("Context target", runtime["max_model_len"]),
        ("Parameter status", runtime["parameter_status"]),
        ("Git Commit", info["git"]["commit"] or "UNKNOWN"),
        ("Git Dirty", "UNKNOWN" if info["git"]["dirty"] is None else info["git"]["dirty"]),
    ]
    print("NeuroBuild Runtime — declared configuration, no runtime probes")
    for label, value in rows:
        print("{:<21}: {}".format(label, value))
    print("URLs are configured targets; service availability was not checked.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, help="Required here or via NEUROBUILD_PROFILE; CLI wins")
    parser.add_argument("--json", action="store_true", help="Print the same declared information as JSON")
    args = parser.parse_args()
    profile = args.profile if args.profile is not None else os.environ.get("NEUROBUILD_PROFILE")
    if profile not in PROFILES:
        parser.error("Specify --profile a100|rtx5090 or a valid NEUROBUILD_PROFILE; no automatic selection")
    try:
        settings, mask = load_settings(profile)
    except (ValueError, KeyError, TypeError) as error:
        # Keep malformed local config failures concise and avoid dumping values.
        parser.error(str(error) if isinstance(error, ValueError) else "Invalid runtime configuration structure")
    info = dict(settings)
    info.update(
        hostname=socket.gethostname(),
        current_cuda_visible_devices=mask,
        information_kind="DECLARED_CONFIGURATION_NOT_RUNTIME_PROBE",
        git=git_info(),
    )
    if args.json:
        print(json.dumps(info, indent=2, ensure_ascii=False))
    else:
        print_text(info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
