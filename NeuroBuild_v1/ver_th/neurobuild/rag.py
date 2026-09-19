from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, List

import requests

from . import config
from .models import RagHit

TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")


def tokenize(text: str) -> set[str]:
    return {tok.lower() for tok in TOKEN_RE.findall(text or "") if len(tok) > 1}


class SimpleJsonlRAG:
    def __init__(self, path: Path, source_name: str):
        self.path = path
        self.source_name = source_name
        self.docs = self._load(path)

    def _load(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        docs = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    docs.append(json.loads(line))
                except Exception:
                    continue
        return docs

    def search(self, query: str, top_k: int = 4) -> List[RagHit]:
        q = tokenize(query)
        scored: list[RagHit] = []
        for idx, doc in enumerate(self.docs):
            text = " ".join(str(doc.get(k, "")) for k in ["title", "text", "jurisdiction", "tags"])
            d = tokenize(text)
            if not d:
                continue
            overlap = len(q & d)
            soft = sum(1 for token in q if token in text.lower())
            score = overlap * 2.0 + soft * 0.5
            if score <= 0:
                score = 0.15 if idx < 2 else 0
            if score > 0:
                scored.append(
                    RagHit(
                        source=self.source_name,
                        title=str(doc.get("title", f"{self.source_name} #{idx + 1}")),
                        text=str(doc.get("text", "")),
                        score=round(score, 3),
                        meta={k: v for k, v in doc.items() if k not in {"title", "text"}},
                    )
                )
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]


class NeurobuildKnowledge:
    def __init__(self):
        self.legal = SimpleJsonlRAG(config.DATA_DIR / "legal_korea_seed.jsonl", "legal_seed")
        self.design = SimpleJsonlRAG(config.DATA_DIR / "design_trends_seed.jsonl", "design_seed")
        self.budget = SimpleJsonlRAG(config.DATA_DIR / "budget_kr_seed.jsonl", "budget_seed")

    def legal_search(self, query: str, top_k: int = 5) -> List[RagHit]:
        hits = self.legal.search(query, top_k=top_k)
        hits.extend(search_law_open_api(query, top_k=2))
        seen = set()
        uniq = []
        for hit in sorted(hits, key=lambda x: x.score, reverse=True):
            key = hit.title
            if key not in seen:
                uniq.append(hit)
                seen.add(key)
        return uniq[:top_k]

    def design_search(self, query: str, top_k: int = 5) -> List[RagHit]:
        return self.design.search(query, top_k=top_k)

    def budget_search(self, query: str, top_k: int = 5) -> List[RagHit]:
        return self.budget.search(query, top_k=top_k)


def search_law_open_api(query: str, top_k: int = 2) -> List[RagHit]:
    """Optional live hook for Korea Law Open API.

    If LAW_OPEN_API_OC is not configured or the network fails, returns [].
    """
    if not config.LAW_OPEN_API_OC:
        return []
    try:
        params = {
            "OC": config.LAW_OPEN_API_OC,
            "target": "law",
            "type": "JSON",
            "query": query[:40] or "건축법",
            "display": str(top_k),
        }
        resp = requests.get("https://www.law.go.kr/DRF/lawSearch.do", params=params, timeout=8)
        if resp.status_code >= 400:
            return []
        data = resp.json()
        law_list = data.get("LawSearch", {}).get("law", [])
        if isinstance(law_list, dict):
            law_list = [law_list]
        hits = []
        for item in law_list[:top_k]:
            title = str(item.get("법령명한글") or item.get("법령명") or "국가법령정보센터 검색 결과")
            law_id = str(item.get("법령ID") or item.get("MST") or "")
            text = (
                f"{title} 검색 결과입니다. 법령ID/MST={law_id}. 실제 조항 본문 검토는 "
                "관할 지자체 조례와 함께 추가 확인이 필요합니다."
            )
            hits.append(RagHit(source="law_open_api", title=title, text=text, score=3.0, meta=item))
        return hits
    except Exception:
        return []


def hits_to_context(hits: Iterable[RagHit]) -> str:
    chunks = []
    for idx, hit in enumerate(hits, 1):
        chunks.append(f"[{idx}] {hit.title} / source={hit.source}\n{hit.text}")
    return "\n\n".join(chunks)
