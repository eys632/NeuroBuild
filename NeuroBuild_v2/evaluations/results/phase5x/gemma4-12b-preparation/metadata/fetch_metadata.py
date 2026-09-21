"""Bounded public metadata retrieval; never retrieves weights or weight ranges."""
import argparse
import hashlib
import json
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIMIT = 99 * 1024 * 1024  # strictly below the authorized total 100 MiB
REPOS = {
    "gguf": ("google/gemma-4-12B-it-qat-q4_0-gguf", "29d097773436b69ff9feafd636ab4cf873786537"),
    "qat-unquantized": ("google/gemma-4-12B-it-qat-q4_0-unquantized", "b6ed86275a6a5735884e208bfed95b445a684ca2"),
    "original-it": ("google/gemma-4-12B-it", "707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7"),
}
ALLOWED_FILES = {"README.md", "LICENSE", "LICENSE.txt", "config.json", "generation_config.json", "tokenizer_config.json", "tokenizer.json", "chat_template.jinja", "model.safetensors.index.json", "processor_config.json"}

class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        host = parsed.hostname or ""
        if parsed.scheme != "https" or not (host in {"huggingface.co", "ai.google.dev", "www.apache.org"} or host.endswith(".huggingface.co") or host.endswith(".hf.co")):
            raise RuntimeError("unapproved redirect host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("apis", "files", "license"))
    args = parser.parse_args()
    ledger_path = ROOT / "download_ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {"limit_bytes": LIMIT, "network_payload_bytes": 0, "disk_free_before_bytes": shutil.disk_usage(ROOT).free, "records": []}
    opener = urllib.request.build_opener(PublicRedirect())

    def fetch(url, relative, cap, expected=None):
        dest = ROOT / relative
        if dest.exists():
            raise RuntimeError("refusing overwrite: " + relative)
        request = urllib.request.Request(url, headers={"User-Agent": "NeuroBuild-metadata-research/1", "Accept-Encoding": "identity"})
        remaining = min(cap, LIMIT - ledger["network_payload_bytes"])
        with opener.open(request, timeout=60) as response:
            declared = response.headers.get("Content-Length")
            if declared is not None and int(declared) > remaining:
                raise RuntimeError("declared metadata size exceeds cap")
            data = response.read(remaining + 1)
            ledger["network_payload_bytes"] += len(data)
            if len(data) > remaining:
                raise RuntimeError("metadata body exceeds cap")
            final_host = urllib.parse.urlparse(response.url).hostname
        sha = hashlib.sha256(data).hexdigest()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if expected:
            if len(data) != expected["size"]:
                raise RuntimeError("remote size mismatch")
            if expected.get("lfs"):
                if sha != expected["lfs"]["sha256"]:
                    raise RuntimeError("LFS sha mismatch")
            elif blob != expected["blobId"]:
                raise RuntimeError("git blob mismatch")
        dest.parent.mkdir(exist_ok=True, parents=True)
        with dest.open("xb") as stream:
            stream.write(data)
        ledger["records"].append({"path": relative, "url": url, "final_host": final_host, "bytes": len(data), "sha256": sha, "git_blob_sha1": blob, "hf_expected": expected, "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
        return data

    if args.phase == "apis":
        for label, (repo, revision) in REPOS.items():
            data = fetch(f"https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true", f"{label}-api.json", 2 * 1024 * 1024)
            info = json.loads(data)
            if info["sha"] != revision or info["id"] != repo:
                raise RuntimeError("repository pin mismatch")
        repo, revision = REPOS["gguf"]
        fetch(f"https://huggingface.co/api/models/{repo}/commits/{revision}", "gguf-commits.json", 2 * 1024 * 1024)
    elif args.phase == "files":
        for label, (repo, revision) in REPOS.items():
            info = json.loads((ROOT / f"{label}-api.json").read_text())
            for entry in info["siblings"]:
                name = entry["rfilename"]
                if name not in ALLOWED_FILES:
                    continue
                # One official tokenizer payload suffices; compare original IT blob metadata.
                if label == "original-it" and name in {"tokenizer.json", "model.safetensors.index.json"}:
                    continue
                cap = 45 * 1024 * 1024 if name == "tokenizer.json" else 2 * 1024 * 1024
                fetch(f"https://huggingface.co/{repo}/resolve/{revision}/{name}", f"{label}/{name}", cap, entry)
    else:
        fetch("https://ai.google.dev/gemma/docs/gemma_4_license", "official-license/gemma4-license.html", 2 * 1024 * 1024)
        fetch("https://www.apache.org/licenses/LICENSE-2.0.txt", "official-license/APACHE-2.0.txt", 128 * 1024)
    print(json.dumps({"phase": args.phase, "records": len(ledger["records"]), "network_payload_bytes": ledger["network_payload_bytes"], "limit_bytes": LIMIT}))

if __name__ == "__main__":
    main()
