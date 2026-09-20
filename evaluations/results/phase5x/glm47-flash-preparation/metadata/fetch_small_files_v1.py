"""Pinned metadata only. No model weight URL is permitted by this helper."""
import datetime
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

BASE = Path(__file__).resolve().parent
TOTAL_CAP = 50 * 1024 * 1024
FILE_CAP = 24 * 1024 * 1024
CHOICES = {
    "upstream": ["config.json", "generation_config.json", "chat_template.jinja",
                 "tokenizer_config.json", "README.md", "model.safetensors.index.json", "tokenizer.json"],
    "gguf": ["README.md"],
}


class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = urllib.parse.urlsplit(newurl)
        host = url.hostname or ""
        allowed = host == "huggingface.co" or host.endswith(".huggingface.co") or host.endswith(".xethub.hf.co")
        if url.scheme != "https" or not allowed:
            raise ValueError("METADATA_REDIRECT_REJECTED")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main():
    records = []
    downloaded = 0
    opener = urllib.request.build_opener(Redirect())
    api_files = [BASE / (key + "-api.json") for key in CHOICES]
    api_bytes = sum(p.stat().st_size for p in api_files)
    for label, names in CHOICES.items():
        api = json.loads((BASE / (label + "-api.json")).read_bytes())
        listed = {x["rfilename"]: x for x in api["siblings"]}
        folder = BASE / label
        folder.mkdir(exist_ok=False)
        for name in names:
            metadata = listed[name]
            expected_size = metadata["size"]
            assert 0 < expected_size <= FILE_CAP
            assert downloaded + expected_size + api_bytes <= TOTAL_CAP
            assert not name.endswith((".gguf", ".safetensors", ".bin", ".pt"))
            url = "https://huggingface.co/" + api["id"] + "/resolve/" + api["sha"] + "/" + name
            request = urllib.request.Request(url, headers={"User-Agent": "NeuroBuild-metadata-audit", "Accept-Encoding": "identity"})
            path = folder / name
            with opener.open(request, timeout=30) as response, path.open("xb") as output:
                assert response.status == 200
                if response.headers.get("Content-Length") is not None:
                    assert int(response.headers["Content-Length"]) == expected_size
                count = 0
                digest = hashlib.sha256()
                git_digest = hashlib.sha1(b"blob " + str(expected_size).encode() + b"\0")
                while True:
                    chunk = response.read(min(1024 * 1024, expected_size - count + 1))
                    if not chunk:
                        break
                    count += len(chunk)
                    assert count <= expected_size
                    digest.update(chunk)
                    git_digest.update(chunk)
                    output.write(chunk)
                assert count == expected_size
                final_host = urllib.parse.urlsplit(response.geturl()).hostname
            if metadata.get("lfs"):
                assert metadata["lfs"]["size"] == count
                assert digest.hexdigest() == metadata["lfs"]["sha256"]
                verification = "LFS_SHA256_AND_SIZE"
            else:
                assert git_digest.hexdigest() == metadata["blobId"]
                verification = "GIT_BLOB_SHA1_AND_SIZE_PLUS_LOCAL_SHA256"
            downloaded += count
            records.append({"path": str(path.relative_to(BASE)), "source_url": url, "source_revision": api["sha"],
                            "bytes": count, "sha256": digest.hexdigest(), "api_blob_id": metadata["blobId"],
                            "verification": verification, "final_host": final_host,
                            "retrieved_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    receipt = {"kind": "GLM47_FLASH_PINNED_METADATA_FETCH", "status": "PASS", "records": records,
               "metadata_payload_bytes": downloaded, "api_payload_bytes": api_bytes,
               "total_downloaded_bytes": downloaded + api_bytes, "total_cap_bytes": TOTAL_CAP,
               "individual_file_cap_bytes": FILE_CAP, "authorization_headers": False,
               "model_weight_resolve_calls": 0, "model_weight_bytes": 0,
               "gpu_calls": 0, "model_inference_calls": 0, "installs": 0}
    with (BASE / "fetch_receipt.json").open("x") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "files": len(records), "bytes": downloaded + api_bytes}))


if __name__ == "__main__":
    main()
