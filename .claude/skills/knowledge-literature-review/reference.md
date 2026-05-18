# Literature Review — Reference

## Paper JSON Schema

```json
{
  "id": "arxiv:2105.12345",
  "arxiv_id": "2105.12345",
  "s2_id": "abc123...",
  "title": "Paper Title",
  "authors": ["Author One", "Author Two"],
  "year": 2021,
  "venue": "CVPR 2021",
  "abstract": "...",
  "url": "https://arxiv.org/abs/2105.12345",
  "pdf_url": "https://arxiv.org/pdf/2105.12345",
  "tags": [],
  "notes": "",
  "added_at": "2026-05-12T10:00:00",
  "references": ["arxiv:1906.04720"],
  "cited_by": [],
  "citation_count": 142,
  "reference_count": 45,
  "fields_of_study": ["Computer Science"]
}
```

## Semantic Scholar API

Base URL: `https://api.semanticscholar.org/graph/v1/`

| Operation | Endpoint |
|-----------|----------|
| Fetch paper | `GET /paper/arXiv:{id}?fields=title,authors,year,abstract,references,citations,externalIds,citationCount,referenceCount,venue,fieldsOfStudy` |
| References | `GET /paper/arXiv:{id}/references?fields=title,authors,year,externalIds,citationCount&limit=100` |
| Citations | `GET /paper/arXiv:{id}/citations?fields=title,authors,year,externalIds,citationCount&limit=100` |
| Search | `GET /paper/search?query={q}&fields=title,authors,year,abstract,externalIds,citationCount&limit=50` |

Set header `x-api-key: {S2_API_KEY}` if env var is set.

## arXiv API

Search: `http://export.arxiv.org/api/query?search_query=all:{query}&max_results={n}&sortBy=relevance`

Returns Atom XML. Key fields: `entry/id`, `entry/title`, `entry/author/name`, `entry/summary`, `entry/published`.

arXiv ID extraction: strip `http://arxiv.org/abs/` prefix from entry ID.

## graph.json Schema

```json
{
  "built_at": "2026-05-12T10:00:00",
  "paper_count": 150,
  "edge_count": 892,
  "edges": [{"from": "arxiv:2105.12345", "to": "arxiv:1906.04720"}]
}
```

## File Naming

Paper files: `papers/{year}_{arxiv_id_with_underscores}.json`
Example: `arxiv:2105.12345` → `papers/2021_2105_12345.json`
