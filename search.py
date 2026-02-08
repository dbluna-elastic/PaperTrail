"""Semantic search over PaperTrail papers using ELSER text expansion."""
import argparse
import sys

from config import (
    ELASTIC_API_KEY,
    ELASTIC_ENDPOINT,
    INDEX_NAME,
    MODEL_ID,
    get_es_client,
)


def semantic_search(query: str, size: int = 20):
    """
    Run semantic search using ELSER text_expansion (inference-in-search).
    Returns list of hits with _source and _score.
    """
    if not query or not query.strip():
        return {"hits": {"hits": []}}

    es = get_es_client()
    resp = es.search(
        index=INDEX_NAME,
        body={
            "query": {
                "text_expansion": {
                    "content_embedding.tokens": {
                        "model_id": MODEL_ID,
                        "model_text": query.strip(),
                    }
                }
            },
            "size": size,
        },
    )
    return resp


def main():
    if not ELASTIC_ENDPOINT or not ELASTIC_API_KEY:
        print("Error: ELASTIC_ENDPOINT and ELASTIC_API_KEY must be set in .env")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Semantic search over PaperTrail papers")
    parser.add_argument("query", nargs="*", help="Search query (words joined if multiple)")
    parser.add_argument("-n", "--size", type=int, default=10, help="Max number of results (default 10)")
    args = parser.parse_args()

    q = " ".join(args.query) if args.query else ""
    if not q:
        print("Usage: python search.py <query>")
        print("Example: python search.py transformer attention mechanisms")
        sys.exit(1)

    es = get_es_client()
    if not es.ping():
        print("Could not connect to Elastic Cloud.")
        sys.exit(1)

    resp = semantic_search(q, size=args.size)
    hits = resp.get("hits", {}).get("hits", [])

    if not hits:
        print("No results found.")
        return

    for i, hit in enumerate(hits, 1):
        src = hit.get("_source", {})
        score = hit.get("_score", 0)
        title = src.get("title", "")
        summary = (src.get("summary") or "")[:200]
        if len((src.get("summary") or "")) > 200:
            summary += "..."
        pdf_url = src.get("pdf_url", "")
        print(f"{i}. [{score:.2f}] {title}")
        print(f"   {summary}")
        print(f"   {pdf_url}")
        print()


if __name__ == "__main__":
    main()
