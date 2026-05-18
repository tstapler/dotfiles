#!/usr/bin/env python3
# /// script
# dependencies = ["requests", "feedparser", "diskcache"]
# ///
"""
Fetch paper metadata for literature review.

Backends (in order of preference):
  openalex  - Free, no key, 100K req/day. Default when S2_API_KEY is not set.
  s2        - Semantic Scholar. Set S2_API_KEY env var for reliable access.
  crossref  - Supplement for reference lists only (not a full backend).

Usage:
  uv run fetch_papers.py search "3D gaussian splatting" --max 20
  uv run fetch_papers.py fetch arxiv:2308.04079
  uv run fetch_papers.py expand arxiv:2308.04079 --direction both
  uv run fetch_papers.py snowball arxiv:2308.04079 --recommendations
  uv run fetch_papers.py list

Environment:
  LITERATURE_DIR      Storage path (default: ~/Documents/personal-wiki/literature/)
  S2_API_KEY          Semantic Scholar API key — enables s2 backend
  LITERATURE_BACKEND  Force backend: openalex | s2 (default: openalex, or s2 if key set)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import diskcache
import feedparser
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LITERATURE_DIR = Path(os.environ.get(
    "LITERATURE_DIR",
    Path.home() / "Documents/personal-wiki/literature"
))
OA_MAILTO = "tystapler@gmail.com"
OA_BASE = "https://api.openalex.org"
S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_RECOMMEND_BASE = "https://api.semanticscholar.org/recommendations/v1"
CR_BASE = "https://api.crossref.org/works"
ARXIV_BASE = "http://export.arxiv.org/api/query"

S2_FIELDS = "title,authors,year,abstract,references,externalIds,citationCount,referenceCount,venue,fieldsOfStudy"
S2_REF_FIELDS = "title,authors,year,externalIds,citationCount"


def active_backend() -> str:
    """openalex by default; s2 if S2_API_KEY is set or LITERATURE_BACKEND forces it."""
    forced = os.environ.get("LITERATURE_BACKEND", "").lower()
    if forced in ("s2", "openalex"):
        return forced
    return "s2" if os.environ.get("S2_API_KEY") else "openalex"


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def paper_path(paper_id: str) -> Path:
    clean = paper_id.replace("arxiv:", "").replace(".", "_").replace("/", "_")
    return LITERATURE_DIR / "papers" / f"{clean}.json"


def load_paper(paper_id: str) -> Optional[dict]:
    path = paper_path(paper_id)
    return json.loads(path.read_text()) if path.exists() else None


def save_paper(paper: dict) -> None:
    LITERATURE_DIR.mkdir(parents=True, exist_ok=True)
    (LITERATURE_DIR / "papers").mkdir(exist_ok=True)
    paper_path(paper["id"]).write_text(json.dumps(paper, indent=2, ensure_ascii=False))
    _update_index(paper)
    print(f"  saved: {paper['id']} — {paper['title'][:70]}")


def load_index() -> dict:
    idx = LITERATURE_DIR / "index.json"
    return json.loads(idx.read_text()) if idx.exists() else {}


def _update_index(paper: dict) -> None:
    idx_path = LITERATURE_DIR / "index.json"
    index = load_index()
    index[paper["id"]] = {
        "file": str(paper_path(paper["id"]).relative_to(LITERATURE_DIR)),
        "title": paper["title"],
        "year": paper.get("year"),
        "citation_count": paper.get("citation_count", 0),
    }
    LITERATURE_DIR.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(json.dumps(index, indent=2, ensure_ascii=False))


def normalize_id(raw_id: str) -> Optional[str]:
    raw = raw_id.strip()
    if raw.startswith("arxiv:"):
        return raw.lower()
    if raw.startswith("http") and "/abs/" in raw:
        return f"arxiv:{raw.split('/abs/')[-1].split('v')[0]}"
    if "." in raw and not raw.startswith("http"):
        return f"arxiv:{raw.split('v')[0]}"
    return None


# ---------------------------------------------------------------------------
# S2 Rate limiter (diskcache-backed, shared across processes)
# ---------------------------------------------------------------------------

class S2RateLimiter:
    """
    Proactive sliding-window rate limiter for Semantic Scholar.
    Backed by diskcache so all concurrent processes share the same budget.

    Limits per 5-minute window:
      Without key: 100 requests  (~3s between requests)
      With key:    900 requests  (~0.3s between requests)

    On 429, parses the response to distinguish:
      - API Gateway 429 (TooManyRequestsException): normal window exhaustion
      - CloudFront WAF block (x-cache: Error from cloudfront): IP-level block,
        longer wait, resets local window since external consumption caused it
    """
    CACHE_DIR = Path.home() / ".cache" / "s2-ratelimit"
    WINDOW = 300
    MAX_NO_KEY = 100
    MAX_WITH_KEY = 900

    def __init__(self) -> None:
        self._cache = diskcache.Cache(str(self.CACHE_DIR))
        self._lock = diskcache.Lock(self._cache, "lock")
        self._limit = self.MAX_WITH_KEY if os.environ.get("S2_API_KEY") else self.MAX_NO_KEY

    def _window_timestamps(self, now: float) -> list[float]:
        ts: list[float] = self._cache.get("timestamps", [])
        return [t for t in ts if t > now - self.WINDOW]

    def wait_if_needed(self) -> None:
        with self._lock:
            now = time.time()
            ts = self._window_timestamps(now)
            if len(ts) >= self._limit:
                wait = min(ts) + self.WINDOW - now + 0.5
                if wait > 0:
                    print(f"  S2 budget full ({len(ts)}/{self._limit} in window), "
                          f"sleeping {wait:.1f}s...", file=sys.stderr)
                    time.sleep(wait)
                    now = time.time()
                    ts = self._window_timestamps(now)
            ts.append(now)
            self._cache.set("timestamps", ts)

    def record_429(self, resp: requests.Response) -> None:
        """Extract diagnostic headers, log them, sleep appropriately."""
        error_type = resp.headers.get("x-amzn-errortype", "")
        cache_status = resp.headers.get("x-cache", "")
        retry_after_raw = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
        server_date = resp.headers.get("date", "")
        is_cloudfront = "cloudfront" in cache_status.lower()

        retry_after: Optional[int] = None
        if retry_after_raw:
            try:
                retry_after = int(retry_after_raw)
            except ValueError:
                pass

        try:
            body = resp.json()
            print(f"  S2 429: {body.get('message','')[:120]}", file=sys.stderr)
        except Exception:
            pass

        block_type = "CloudFront IP block" if is_cloudfront else f"API Gateway 429 ({error_type})"
        wait = retry_after or (120 if is_cloudfront else 60)
        print(f"  Type: {block_type}", file=sys.stderr)
        print(f"  Retry-After: {retry_after}s" if retry_after else
              f"  No Retry-After — using {wait}s default", file=sys.stderr)
        if server_date:
            print(f"  Server time: {server_date}", file=sys.stderr)

        if is_cloudfront:
            with self._lock:
                self._cache.set("timestamps", [])
            print("  Reset local window (CloudFront block = external budget consumed)",
                  file=sys.stderr)

        print(f"  Waiting {wait}s...", file=sys.stderr)
        time.sleep(wait)


_s2_rl: Optional[S2RateLimiter] = None


def _get_s2_rl() -> S2RateLimiter:
    global _s2_rl
    if _s2_rl is None:
        _s2_rl = S2RateLimiter()
    return _s2_rl


def _s2_headers() -> dict:
    h = {
        "Accept": "application/json",
        "User-Agent": f"literature-review-tool/1.0 (personal research; contact {OA_MAILTO})",
    }
    key = os.environ.get("S2_API_KEY")
    if key:
        h["x-api-key"] = key
    return h


def _s2_get(url: str, params: dict) -> Optional[dict]:
    """S2 GET with proactive rate limiting and 429 diagnostics."""
    rl = _get_s2_rl()
    for attempt in range(4):
        try:
            rl.wait_if_needed()
            resp = requests.get(url, params=params, headers=_s2_headers(), timeout=15)
            if resp.status_code == 429:
                rl.record_429(resp)
                continue
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"  S2 network error ({attempt+1}/4): {e}", file=sys.stderr)
            time.sleep(5)
    print(f"  S2 gave up after 4 attempts: {url}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# OpenAlex backend
# ---------------------------------------------------------------------------

def _oa_get(url: str, params: dict) -> Optional[dict]:
    """OpenAlex GET — generous rate limits, simple retry on 429."""
    base = {"mailto": OA_MAILTO}
    base.update(params)
    headers = {"User-Agent": f"literature-review-tool/1.0 (mailto:{OA_MAILTO})"}
    for attempt in range(3):
        try:
            time.sleep(0.2)  # polite: 5 req/sec, well within 100K/day
            resp = requests.get(url, params=base, headers=headers, timeout=15)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 10))
                print(f"  OpenAlex rate limited, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"  OpenAlex error ({attempt+1}/3): {e}", file=sys.stderr)
            time.sleep(3)
    return None


def _oa_reconstruct_abstract(inverted: Optional[dict]) -> str:
    if not inverted:
        return ""
    words: dict[int, str] = {}
    for word, positions in inverted.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[i] for i in sorted(words))


def _oa_work_to_paper(work: dict, ref_arxiv_ids: list[str]) -> dict:
    ids = work.get("ids") or {}
    arxiv_id = _oa_extract_arxiv_id(work)
    doi = (ids.get("doi") or "").replace("https://doi.org/", "")
    paper_id = f"arxiv:{arxiv_id}" if arxiv_id else f"oa:{work.get('id','').split('/')[-1]}"

    authors = [
        (a.get("author") or {}).get("display_name", "")
        for a in (work.get("authorships") or [])
        if (a.get("author") or {}).get("display_name")
    ]
    venue = ((work.get("primary_location") or {}).get("source") or {}).get("display_name", "")
    concepts = [c.get("display_name", "") for c in (work.get("concepts") or [])[:5]]
    oa_id = work.get("id", "").split("/")[-1]

    return {
        "id": paper_id,
        "arxiv_id": arxiv_id,
        "s2_id": "",
        "oa_id": oa_id,
        "doi": doi,
        "title": work.get("title", ""),
        "authors": authors,
        "year": work.get("publication_year"),
        "venue": venue,
        "abstract": _oa_reconstruct_abstract(work.get("abstract_inverted_index")),
        "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else f"https://doi.org/{doi}" if doi else "",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
        "tags": [],
        "notes": "",
        "added_at": datetime.now().isoformat(),
        "references": ref_arxiv_ids,
        "cited_by": [],
        "citation_count": work.get("cited_by_count", 0),
        "reference_count": len(work.get("referenced_works") or []),
        "fields_of_study": concepts,
        "_oa_cited_by_api_url": work.get("cited_by_api_url", ""),
    }


OA_SELECT = ",".join([
    "id", "ids", "doi", "title", "authorships", "publication_year",
    "cited_by_count", "cited_by_api_url", "referenced_works",
    "primary_location", "abstract_inverted_index", "concepts",
])

# arXiv source ID in OpenAlex (used to filter search results to arXiv preprints)
OA_ARXIV_SOURCE_ID = "S4306400194"


def _oa_extract_arxiv_id(work: dict) -> str:
    """Extract arXiv ID from an OpenAlex work.

    Checks (in order): ids.arxiv, DOI (10.48550/arxiv.*), and locations URLs.
    Many published papers have their arXiv preprint listed in locations even when
    the primary DOI is a conference/journal DOI.
    """
    ids = work.get("ids") or {}
    # Legacy field: ids.arxiv
    arxiv_url = ids.get("arxiv", "")
    if arxiv_url:
        return arxiv_url.replace("https://arxiv.org/abs/", "").strip("/")
    # arXiv DOI: 10.48550/arXiv.XXXX.XXXXX or 10.48550/arxiv.XXXX
    doi = (ids.get("doi") or "").replace("https://doi.org/", "").lower()
    if doi.startswith("10.48550/arxiv."):
        return doi.replace("10.48550/arxiv.", "")
    # Check locations list for an arxiv.org URL (published papers with preprints)
    for loc in (work.get("locations") or []):
        lurl = (loc.get("landing_page_url") or "").lower()
        if "arxiv.org/abs/" in lurl:
            return lurl.split("arxiv.org/abs/")[-1].split("v")[0].strip("/")
    return ""


def _oa_resolve_refs(oa_ids: list[str]) -> list[str]:
    """Batch-resolve OpenAlex IDs → arXiv IDs. Returns list of arxiv:XXXX IDs.

    Includes `locations` in the select so _oa_extract_arxiv_id can find arXiv
    preprints even when the primary record is a journal/conference publication.
    """
    arxiv_ids = []
    for i in range(0, len(oa_ids), 50):
        batch = [oid.split("/")[-1] for oid in oa_ids[i:i + 50]]
        data = _oa_get(f"{OA_BASE}/works", {
            "filter": f"openalex:{'|'.join(batch)}",
            "select": "id,ids,locations",
            "per-page": len(batch),
        })
        if not data:
            continue
        for w in data.get("results", []):
            aid = _oa_extract_arxiv_id(w)
            if aid:
                arxiv_ids.append(f"arxiv:{aid}")
    return arxiv_ids


def _oa_find_canonical(title: str) -> Optional[dict]:
    """Find the most-cited OA version of a paper (usually the published venue record).

    arXiv preprints in OA often have 0 references; the published version has the full
    reference list and tracks most citations. This extra call is only triggered when
    the preprint record has no referenced_works.
    """
    data = _oa_get(f"{OA_BASE}/works", {
        "search": title,
        "sort": "cited_by_count:desc",
        "per-page": 3,
        "select": "id,ids,title,cited_by_count,referenced_works,cited_by_api_url",
    })
    if not data:
        return None
    candidates = data.get("results", [])
    return candidates[0] if candidates else None


def oa_fetch(arxiv_id: str) -> Optional[dict]:
    clean = arxiv_id.replace("arxiv:", "")
    # Use arXiv DOI (not arxiv.org/abs/ which 404s in OA)
    work = _oa_get(f"{OA_BASE}/works/https://doi.org/10.48550/arxiv.{clean}", {"select": OA_SELECT})
    if not work or work.get("error"):
        return None

    oa_refs = work.get("referenced_works") or []
    canonical_oa_id = work.get("id", "").split("/")[-1]

    # arXiv preprints often have 0 references in OA; find the published version.
    if not oa_refs and work.get("title"):
        canonical = _oa_find_canonical(work["title"])
        if canonical and canonical.get("cited_by_count", 0) > work.get("cited_by_count", 0):
            oa_refs = canonical.get("referenced_works") or oa_refs
            canonical_oa_id = canonical.get("id", "").split("/")[-1] or canonical_oa_id

    # Resolve OA reference IDs → arXiv IDs (API-resolved)
    ref_arxiv = _oa_resolve_refs(oa_refs) if oa_refs else []
    paper = _oa_work_to_paper(work, ref_arxiv)
    # Store canonical OA ID (for citation expansion) and raw OA ref IDs (for
    # graph matching: build_graph.py can match these against other papers' oa_id
    # even when the published DOI has no arXiv counterpart).
    paper["oa_id"] = canonical_oa_id
    paper["_oa_ref_ids"] = [r.split("/")[-1] for r in oa_refs]
    return paper


def oa_search(query: str, limit: int = 25) -> list[dict]:
    # filter=primary_location.source.id restricts to arXiv-primary papers.
    # sort cannot be combined with search (relevance is the implicit sort).
    data = _oa_get(f"{OA_BASE}/works", {
        "search": query,
        "filter": f"primary_location.source.id:{OA_ARXIV_SOURCE_ID}",
        "select": "id,ids,title,publication_year,cited_by_count",
        "per-page": min(limit, 200),
    })
    if not data:
        return []
    results = []
    for w in data.get("results", []):
        aid = _oa_extract_arxiv_id(w)
        if aid:
            results.append({"id": f"arxiv:{aid}", "arxiv_id": aid, "title": w.get("title", ""),
                            "cited_by_count": w.get("cited_by_count", 0)})
    print(f"  found {len(results)} arXiv papers via OpenAlex")
    return results


def oa_fetch_citing(oa_id: str, limit: int = 100) -> list[dict]:
    """Papers that cite a given OpenAlex ID, sorted newest first.

    Includes `locations` so _oa_extract_arxiv_id can find arXiv preprint URLs even
    when the citing paper's primary DOI is a conference/journal DOI.
    """
    if not oa_id:
        return []
    data = _oa_get(f"{OA_BASE}/works", {
        "filter": f"cites:{oa_id}",
        "select": "id,ids,title,publication_year,cited_by_count,locations",
        "per-page": min(limit, 200),
        "sort": "publication_year:desc",
    })
    if not data:
        return []
    results = []
    for w in data.get("results", []):
        aid = _oa_extract_arxiv_id(w)
        if aid:
            results.append({
                "id": f"arxiv:{aid}", "arxiv_id": aid, "title": w.get("title", ""),
                "year": w.get("publication_year"), "citation_count": w.get("cited_by_count", 0),
            })
    results.sort(key=lambda p: p.get("year") or 0, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Semantic Scholar backend
# ---------------------------------------------------------------------------

def _s2_to_paper(s2: dict) -> dict:
    ext = s2.get("externalIds") or {}
    arxiv_id = ext.get("ArXiv", "")
    paper_id = f"arxiv:{arxiv_id}" if arxiv_id else f"s2:{s2.get('paperId', '')}"
    refs = [
        f"arxiv:{(r.get('externalIds') or {}).get('ArXiv')}"
        for r in (s2.get("references") or [])
        if (r.get("externalIds") or {}).get("ArXiv")
    ]
    return {
        "id": paper_id, "arxiv_id": arxiv_id, "s2_id": s2.get("paperId", ""),
        "oa_id": "", "doi": ext.get("DOI", ""),
        "title": s2.get("title", ""),
        "authors": [a.get("name", "") for a in (s2.get("authors") or [])],
        "year": s2.get("year"), "venue": s2.get("venue", ""),
        "abstract": s2.get("abstract", ""),
        "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
        "tags": [], "notes": "", "added_at": datetime.now().isoformat(),
        "references": refs, "cited_by": [],
        "citation_count": s2.get("citationCount", 0),
        "reference_count": s2.get("referenceCount", 0),
        "fields_of_study": s2.get("fieldsOfStudy") or [],
        "_oa_cited_by_api_url": "",
    }


def s2_fetch(arxiv_id: str) -> Optional[dict]:
    s2_id = arxiv_id.replace("arxiv:", "arXiv:")
    data = _s2_get(f"{S2_BASE}/paper/{s2_id}", {"fields": S2_FIELDS})
    return _s2_to_paper(data) if data else None


def s2_fetch_citing(s2_id: str, limit: int = 100) -> list[dict]:
    if not s2_id:
        return []
    data = _s2_get(f"{S2_BASE}/paper/{s2_id}/citations",
                   {"fields": S2_REF_FIELDS, "limit": min(limit, 1000)})
    if not data:
        return []
    results = []
    for item in data.get("data", []):
        citing = item.get("citingPaper", {})
        ext = citing.get("externalIds") or {}
        if ext.get("ArXiv"):
            results.append({
                "id": f"arxiv:{ext['ArXiv']}", "arxiv_id": ext["ArXiv"],
                "title": citing.get("title", ""), "year": citing.get("year"),
                "citation_count": citing.get("citationCount", 0),
            })
    results.sort(key=lambda p: p.get("year") or 0, reverse=True)
    return results


def s2_search(query: str, limit: int = 25) -> list[dict]:
    data = _s2_get(f"{S2_BASE}/paper/search",
                   {"query": query, "fields": "title,externalIds,year,citationCount",
                    "limit": min(limit, 100)})
    if not data:
        return []
    results = [
        {"id": f"arxiv:{(p.get('externalIds') or {}).get('ArXiv')}",
         "arxiv_id": (p.get("externalIds") or {}).get("ArXiv", ""),
         "title": p.get("title", "")}
        for p in data.get("data", [])
        if (p.get("externalIds") or {}).get("ArXiv")
    ]
    print(f"  found {len(results)} arXiv papers via S2")
    return results


def s2_recommendations(s2_id: str, limit: int = 20) -> list[dict]:
    data = _s2_get(f"{S2_RECOMMEND_BASE}/papers/forpaper/{s2_id}",
                   {"fields": S2_REF_FIELDS, "limit": limit})
    if not data:
        return []
    results = []
    for rec in data.get("recommendedPapers", []):
        ext = rec.get("externalIds") or {}
        if ext.get("ArXiv"):
            results.append({
                "id": f"arxiv:{ext['ArXiv']}", "arxiv_id": ext["ArXiv"],
                "title": rec.get("title", ""), "year": rec.get("year"),
                "citation_count": rec.get("citationCount", 0),
            })
    results.sort(key=lambda p: p.get("year") or 0, reverse=True)
    return results


# ---------------------------------------------------------------------------
# arXiv search (fallback, no reference data)
# ---------------------------------------------------------------------------

def arxiv_search(query: str, limit: int = 25) -> list[dict]:
    print(f"Searching arXiv: '{query}' (max {limit})...")
    for attempt in range(4):
        if attempt:
            wait = 15 * attempt
            print(f"  arXiv rate limited, retrying in {wait}s...", file=sys.stderr)
            time.sleep(wait)
        try:
            resp = requests.get(ARXIV_BASE, params={
                "search_query": f"all:{query}", "max_results": limit, "sortBy": "relevance",
            }, timeout=30)
            if resp.status_code == 429:
                continue
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            results = []
            for entry in feed.entries:
                raw = entry.get("id", "")
                aid = raw.split("/abs/")[-1].split("v")[0] if "/abs/" in raw else ""
                if aid:
                    results.append({"id": f"arxiv:{aid}", "arxiv_id": aid,
                                    "title": entry.get("title", "").replace("\n", " ").strip()})
            print(f"  found {len(results)} results on arXiv")
            return results
        except requests.RequestException as e:
            print(f"  arXiv error ({attempt+1}/4): {e}", file=sys.stderr)
    return []


# ---------------------------------------------------------------------------
# Backend-agnostic wrappers
# ---------------------------------------------------------------------------

def backend_fetch(arxiv_id: str) -> Optional[dict]:
    be = active_backend()
    if be == "s2":
        return s2_fetch(arxiv_id)
    return oa_fetch(arxiv_id)


def backend_search(query: str, limit: int) -> list[dict]:
    be = active_backend()
    if be == "s2":
        results = s2_search(query, limit)
        if not results:
            print("S2 search returned nothing, trying OpenAlex...", file=sys.stderr)
            results = oa_search(query, limit)
    else:
        results = oa_search(query, limit)
        if not results:
            print("OpenAlex returned nothing, trying arXiv...", file=sys.stderr)
            results = arxiv_search(query, limit)
    return results


def backend_fetch_citing(paper: dict, limit: int) -> list[dict]:
    be = active_backend()
    if be == "s2":
        return s2_fetch_citing(paper.get("s2_id", ""), limit)
    # OpenAlex: try citation lookup first.
    # OA links arXiv preprints in ~5-10% of published-paper citers; for well-known
    # papers most follow-up work needs S2 to be found. When OA finds nothing,
    # try S2 with a single quick probe (no retry on IP block — avoid long hangs).
    oa_results = oa_fetch_citing(paper.get("oa_id", ""), limit)
    if oa_results:
        return oa_results
    arxiv_id = paper.get("arxiv_id", "")
    if not arxiv_id:
        return []
    # Single S2 attempt — if blocked, return [] immediately rather than hanging.
    rl = _get_s2_rl()
    try:
        rl.wait_if_needed()
        resp = requests.get(
            f"{S2_BASE}/paper/arXiv:{arxiv_id}",
            params={"fields": "paperId"},
            headers=_s2_headers(),
            timeout=8,
        )
        if resp.status_code == 429:
            print("  S2 blocked (no API key); skipping forward expansion. "
                  "Set S2_API_KEY for reliable citation lookup.", file=sys.stderr)
            return []
        resp.raise_for_status()
        s2_id = resp.json().get("paperId", "")
        if s2_id:
            return s2_fetch_citing(s2_id, limit)
    except requests.RequestException:
        pass
    return []


def _fetch_and_save(pid: str) -> Optional[dict]:
    paper = load_paper(pid)
    if paper is not None:
        return paper
    paper = backend_fetch(pid)
    if paper:
        save_paper(paper)
    return paper


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_search(args: argparse.Namespace) -> None:
    print(f"Backend: {active_backend()}")
    results = backend_search(args.query, args.max)
    if not results:
        print("No results found.")
        return
    print(f"Fetching full metadata for {len(results)} papers...")
    fetched = skipped = 0
    for p in results:
        if load_paper(p["id"]) is not None:
            skipped += 1
            continue
        paper = backend_fetch(p["id"])
        if paper:
            save_paper(paper)
            fetched += 1
        else:
            minimal = {**p, "s2_id": "", "oa_id": "", "doi": "", "authors": [],
                       "year": None, "venue": "", "abstract": "",
                       "url": f"https://arxiv.org/abs/{p['arxiv_id']}",
                       "pdf_url": f"https://arxiv.org/pdf/{p['arxiv_id']}",
                       "tags": [], "notes": "", "added_at": datetime.now().isoformat(),
                       "references": [], "cited_by": [], "citation_count": 0,
                       "reference_count": 0, "fields_of_study": []}
            save_paper(minimal)
            fetched += 1
    print(f"\nDone: {fetched} fetched, {skipped} already stored.")
    print("Run: uv run build_graph.py build && uv run build_graph.py top")


def cmd_fetch(args: argparse.Namespace) -> None:
    pid = normalize_id(args.paper_id)
    if not pid:
        print(f"Cannot parse: {args.paper_id}", file=sys.stderr)
        sys.exit(1)
    if load_paper(pid) and not args.force:
        print(f"Already stored: {pid} — use --force to re-fetch")
        return
    print(f"Fetching {pid} (backend: {active_backend()})...")
    paper = backend_fetch(pid)
    if not paper:
        print(f"Not found: {pid}", file=sys.stderr)
        sys.exit(1)
    save_paper(paper)


def cmd_expand(args: argparse.Namespace) -> None:
    """Follow reference/citation links from a seed paper.
    --direction backward : papers this paper cites (older work)
    --direction forward  : papers that cite this paper (newer work)
    --direction both     : bidirectional
    """
    pid = normalize_id(args.paper_id)
    if not pid:
        print(f"Cannot parse: {args.paper_id}", file=sys.stderr)
        sys.exit(1)

    to_fetch = {pid}
    fetched_ids: set[str] = set()

    for depth in range(args.depth + 1):
        batch = to_fetch - fetched_ids
        if not batch:
            break
        print(f"\nDepth {depth}: processing {len(batch)} papers...")
        next_ids: set[str] = set()

        for fid in sorted(batch):
            paper = _fetch_and_save(fid)
            fetched_ids.add(fid)
            if not paper or depth >= args.depth:
                continue

            if args.direction in ("backward", "both"):
                next_ids.update(paper.get("references", []))

            if args.direction in ("forward", "both"):
                citers = backend_fetch_citing(paper, args.max_new)
                print(f"  {fid}: {len(citers)} citing papers found")
                for c in citers[:args.max_new]:
                    next_ids.add(c["id"])

        to_fetch = next_ids

    print(f"\nExpansion complete ({len(fetched_ids)} papers). "
          "Run: uv run build_graph.py build")


def cmd_snowball(args: argparse.Namespace) -> None:
    """
    Snowball sampling from a seed paper:
      Round 1: seed's references (backward) + papers citing seed (forward, newest first)
      Round 2: citers of round-1 papers (second-order = most recent related work)
      Optional: semantic recommendations (S2 only)
    """
    pid = normalize_id(args.paper_id)
    if not pid:
        print(f"Cannot parse: {args.paper_id}", file=sys.stderr)
        sys.exit(1)

    all_fetched: set[str] = set()
    round1_ids: set[str] = set()

    print(f"\n=== Snowball from {pid} (backend: {active_backend()}) ===")
    seed = _fetch_and_save(pid)
    if not seed:
        print("Seed paper not found.", file=sys.stderr)
        sys.exit(1)
    all_fetched.add(pid)
    print(f"Seed: {seed['title'][:70]}")
    print(f"  Citations: {seed.get('citation_count', 0)} | "
          f"References: {seed.get('reference_count', 0)}")

    # Round 1a: backward — references
    refs = seed.get("references", [])
    print(f"\nRound 1 backward: {len(refs)} references")
    for ref_id in refs:
        if ref_id not in all_fetched:
            p = _fetch_and_save(ref_id)
            if p:
                round1_ids.add(ref_id)
            all_fetched.add(ref_id)

    # Round 1b: forward — papers citing the seed
    citers = backend_fetch_citing(seed, args.max_new)
    print(f"Round 1 forward: {len(citers)} papers cite seed (newest first, cap {args.max_new})")
    for c in citers[:args.max_new]:
        if c["id"] not in all_fetched:
            p = _fetch_and_save(c["id"])
            if p:
                round1_ids.add(c["id"])
            all_fetched.add(c["id"])

    # Round 2: citers of round-1 papers
    if args.rounds >= 2:
        print(f"\nRound 2: fetching citers of {len(round1_ids)} round-1 papers...")
        added = 0
        for r1_id in sorted(round1_ids):
            paper = load_paper(r1_id)
            if not paper:
                continue
            c2 = backend_fetch_citing(paper, 10)
            for c in c2[:10]:
                if c["id"] not in all_fetched:
                    if _fetch_and_save(c["id"]):
                        added += 1
                    all_fetched.add(c["id"])
        print(f"  Added {added} new papers via second-order citations")

    # S2 recommendations (only meaningful with S2 backend)
    if args.recommendations:
        if seed.get("s2_id"):
            print(f"\nFetching S2 semantic recommendations...")
            recs = s2_recommendations(seed["s2_id"], 20)
            added = sum(1 for r in recs
                        if r["id"] not in all_fetched and _fetch_and_save(r["id"]))
            print(f"  Added {added} recommended papers")
        else:
            print("  --recommendations requires S2 backend (seed has no s2_id)")

    print(f"\n=== Snowball complete: {len(all_fetched)} total papers ===")
    all_papers = [load_paper(p) for p in all_fetched]
    newest = sorted(
        [p for p in all_papers if p and p.get("year")],
        key=lambda p: p.get("year", 0), reverse=True
    )
    print("Newest papers added:")
    for p in newest[:15]:
        print(f"  [{p.get('year','')}] {p.get('title','')[:70]}")
    print("\nRun: uv run build_graph.py build && uv run build_graph.py top")


def cmd_list(args: argparse.Namespace) -> None:
    index = load_index()
    if not index:
        print("No papers stored. Run: fetch_papers.py search <query>")
        return
    papers = sorted(index.items(), key=lambda x: x[1].get("citation_count", 0), reverse=True)
    print(f"{'ID':<25} {'Year':<6} {'Cites':<8} Title")
    print("-" * 92)
    for pid, meta in papers[:args.n]:
        year = meta.get("year") or "????"
        cites = meta.get("citation_count", 0)
        print(f"{pid:<25} {year:<6} {cites:<8} {meta.get('title','')[:55]}")
    if len(papers) > args.n:
        print(f"... and {len(papers) - args.n} more (total: {len(papers)})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch papers for literature review",
        epilog=f"Active backend: {active_backend()} "
               f"(set LITERATURE_BACKEND=s2|openalex or S2_API_KEY to override)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("search", help="Search and fetch papers")
    p.add_argument("query")
    p.add_argument("--max", type=int, default=25)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("fetch", help="Fetch one paper by ID")
    p.add_argument("paper_id")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("expand", help="Follow reference/citation links from a paper")
    p.add_argument("paper_id")
    p.add_argument("--depth", type=int, default=1)
    p.add_argument("--direction", choices=["backward", "forward", "both"], default="backward")
    p.add_argument("--max-new", type=int, default=50)
    p.set_defaults(func=cmd_expand)

    p = sub.add_parser("snowball", help="Full bidirectional snowball from a seed paper")
    p.add_argument("paper_id")
    p.add_argument("--max-new", type=int, default=50)
    p.add_argument("--rounds", type=int, default=2)
    p.add_argument("--recommendations", action="store_true",
                   help="Add S2 semantic recommendations (requires s2 backend)")
    p.set_defaults(func=cmd_snowball)

    p = sub.add_parser("list", help="List stored papers sorted by citation count")
    p.add_argument("--n", type=int, default=50)
    p.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
