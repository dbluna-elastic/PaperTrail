"""Minimal HTTP API for PaperTrail semantic search."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from config import ELASTIC_API_KEY, ELASTIC_ENDPOINT, get_es_client
from search import semantic_search

app = FastAPI(title="PaperTrail Search API")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/")
def index():
    """Serve the search UI."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_file)


@app.get("/search")
def search(q: str = "", size: int = 20):
    """
    Semantic search over papers.
    Query param: q (search text), size (max results, default 20).
    """
    if not ELASTIC_ENDPOINT or not ELASTIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="ELASTIC_ENDPOINT and ELASTIC_API_KEY must be set in .env",
        )
    if not q or not q.strip():
        return JSONResponse(content={"hits": [], "total": 0})

    try:
        es = get_es_client()
        if not es.ping():
            raise HTTPException(status_code=503, detail="Could not connect to Elastic Cloud.")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        resp = semantic_search(q.strip(), size=min(size, 100))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    hits_body = resp.get("hits", {})
    total = hits_body.get("total", {})
    if isinstance(total, dict):
        total = total.get("value", 0)
    hits = [
        {
            "id": h.get("_id"),
            "score": h.get("_score"),
            "title": h.get("_source", {}).get("title"),
            "summary": h.get("_source", {}).get("summary"),
            "authors": h.get("_source", {}).get("authors", []),
            "published": str(h.get("_source", {}).get("published", "")),
            "pdf_url": h.get("_source", {}).get("pdf_url"),
            "categories": h.get("_source", {}).get("categories", []),
        }
        for h in hits_body.get("hits", [])
    ]
    return JSONResponse(content={"hits": hits, "total": total})


@app.get("/health")
def health():
    """Health check; verifies env and optional ES connectivity."""
    if not ELASTIC_ENDPOINT or not ELASTIC_API_KEY:
        return JSONResponse(status_code=503, content={"status": "missing_env"})
    try:
        es = get_es_client()
        ok = es.ping()
        return JSONResponse(content={"status": "ok" if ok else "es_down"})
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
