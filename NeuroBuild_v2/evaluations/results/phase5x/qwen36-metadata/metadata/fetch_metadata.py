"""Pinned public metadata only. No credentials, weight payloads, or range requests."""
import argparse
import hashlib
import json
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOTAL_CAP = 128 * 1024 * 1024
FILE_CAP = 64 * 1024 * 1024
REPOS = {
    "upstream": ("Qwen/Qwen3.6-35B-A3B", "995ad96eacd98c81ed38be0c5b274b04031597b0"),
    "gguf": ("ggml-org/Qwen3.6-35B-A3B-GGUF", "baec3ebee244827cda0f4557eafa8b28f7545fa6"),
}
ALLOWED = {"README.md", "LICENSE", "LICENSE.txt", ".src_sha", "config.json",
           "generation_config.json", "tokenizer_config.json", "chat_template.jinja",
           "tokenizer.json", "model.safetensors.index.json", "convert.log"}

class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urllib.parse.urlparse(newurl)
        host = p.hostname or ""
        if p.scheme != "https" or p.username or p.password or not (
                host == "huggingface.co" or host.endswith(".huggingface.co") or host.endswith(".hf.co")):
            raise ValueError("UNAPPROVED_REDIRECT")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("apis", "files"))
    args = parser.parse_args()
    ledger_path = ROOT / "download_ledger.json"
    ledger = json.loads(ledger_path.read_bytes()) if ledger_path.exists() else {
        "total_cap_bytes": TOTAL_CAP, "individual_cap_bytes": FILE_CAP,
        "network_payload_bytes": 0, "disk_free_before_bytes": shutil.disk_usage(ROOT).free,
        "records": [], "failures": [], "weight_or_range_requests": 0, "auth_used": False}
    opener = urllib.request.build_opener(PublicRedirect())
    def save_ledger():
        tmp = ledger_path.with_suffix(".tmp")
        with tmp.open("x", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2); f.write("\n")
        tmp.replace(ledger_path)
    def fetch(url, relative, expected=None):
        dest = ROOT / relative
        if dest.exists() or dest.is_symlink(): raise ValueError("REFUSE_OVERWRITE")
        cap = FILE_CAP if expected else 2 * 1024 * 1024
        budget = TOTAL_CAP - ledger["network_payload_bytes"]
        # Keep the EOF-detection byte inside both authorized bounds.
        limit = min(cap - 1, budget - 1)
        if limit <= 0 or (expected and not 0 <= expected["size"] <= limit):
            raise ValueError("METADATA_SIZE_CAP")
        req = urllib.request.Request(url, headers={"User-Agent": "NeuroBuild-pinned-metadata/1",
                                                   "Accept-Encoding": "identity"})
        received = 0
        try:
            with opener.open(req, timeout=45) as response:
                declared = response.headers.get("Content-Length")
                if declared is not None and int(declared) > limit: raise ValueError("DECLARED_SIZE_CAP")
                chunks = []
                while received <= limit:
                    block = response.read(min(65536, limit + 1 - received))
                    if not block: break
                    chunks.append(block); received += len(block)
                    ledger["network_payload_bytes"] += len(block)
                if received > limit: raise ValueError("STREAM_SIZE_CAP")
                data = b"".join(chunks)
                final_host = urllib.parse.urlparse(response.url).hostname
            digest = hashlib.sha256(data).hexdigest()
            blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            if expected:
                if len(data) != expected["size"]: raise ValueError("EXPECTED_SIZE_MISMATCH")
                if expected.get("lfs"):
                    if digest != expected["lfs"]["sha256"]: raise ValueError("LFS_SHA_MISMATCH")
                elif blob != expected["blobId"]: raise ValueError("GIT_BLOB_MISMATCH")
            else:
                doc = json.loads(data)
                label = relative.removesuffix("-api.json")
                if (doc["id"], doc["sha"]) != REPOS[label]: raise ValueError("API_REVISION_MISMATCH")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as f: f.write(data)
            ledger["records"].append({"path": relative, "source_url": url, "final_host": final_host,
                "bytes": len(data), "sha256": digest, "git_blob_sha1": blob, "expected_hf_metadata": expected,
                "retrieved_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            save_ledger()
            return data
        except Exception as error:
            ledger["failures"].append({"path": relative, "received_bytes": received,
                                        "error_type": type(error).__name__})
            save_ledger()
            raise
    if args.phase == "apis":
        for label, (repo, revision) in REPOS.items():
            fetch(f"https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true", label + "-api.json")
    else:
        selected = []
        for label, (repo, revision) in REPOS.items():
            doc = json.loads((ROOT / (label + "-api.json")).read_bytes())
            if (doc["id"], doc["sha"]) != (repo, revision): raise ValueError("API_REVISION_MISMATCH")
            for entry in doc["siblings"]:
                if entry["rfilename"] in ALLOWED:
                    selected.append((label, repo, revision, entry))
        if sum(e[3]["size"] + 1 for e in selected) > TOTAL_CAP - ledger["network_payload_bytes"]:
            raise ValueError("SELECTED_TOTAL_CAP")
        selected.sort(key=lambda item: item[3]["rfilename"] == "tokenizer.json")
        for label, repo, revision, entry in selected:
            name = entry["rfilename"]
            relative = label + "/" + name
            dest = ROOT / relative
            if dest.exists():
                records = [r for r in ledger["records"] if r["path"] == relative]
                if len(records) != 1 or hashlib.sha256(dest.read_bytes()).hexdigest() != records[0]["sha256"]:
                    raise ValueError("EXISTING_METADATA_CHANGED")
                continue
            suffix = "?download=true" if entry.get("lfs") else ""
            fetch(f"https://huggingface.co/{repo}/resolve/{revision}/{name}{suffix}", relative, entry)
    print(json.dumps({"phase": args.phase, "files": len(ledger["records"]),
        "network_payload_bytes": ledger["network_payload_bytes"], "weight_or_range_requests": 0}))

if __name__ == "__main__": main()
