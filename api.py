"""Minimal HTTP API for PaperTrail semantic search."""
import json
import urllib.error
import urllib.request
from pathlib import Path

from pydantic import BaseModel

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from config import (
    AGENT_ID,
    ELASTIC_API_KEY,
    ELASTIC_ENDPOINT,
    KIBANA_API_KEY,
    KIBANA_URL,
    get_es_client,
)
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


class SummarizeBody(BaseModel):
    title: str = ""
    summary: str = ""


@app.post("/summarize")
def summarize(body: SummarizeBody):
    """
    Get a short AI summary of a paper using Elastic Agent Builder.
    Body: { "title": string, "summary": string } (summary = abstract).
    """
    if not KIBANA_URL or not KIBANA_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Summarize is not configured (set KIBANA_URL and KIBANA_API_KEY in .env).",
        )
    title = (body.title or "").strip()
    summary_text = (body.summary or "").strip()
    if not title and not summary_text:
        raise HTTPException(status_code=400, detail="Provide at least title or summary.")

    prompt = f"Summarize this paper in 2-3 sentences.\n\nTitle: {title}\n\nAbstract: {summary_text}"
    payload = json.dumps({"input": prompt, "agent_id": AGENT_ID}).encode("utf-8")

    req = urllib.request.Request(
        f"{KIBANA_URL}/api/agent_builder/converse",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"ApiKey {KIBANA_API_KEY}",
            "kbn-xsrf": "true",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            err = json.loads(body)
            msg = err.get("message") or err.get("error") or body or str(e)
        except Exception:
            msg = body or str(e)
        raise HTTPException(status_code=502, detail=f"Kibana Agent Builder error: {msg}")
    except urllib.error.URLError as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach Kibana: {e.reason}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Kibana converse response: response.message contains the agent reply
    reply = (data.get("response") or {}).get("message", "")
    if not reply and data.get("steps"):
        for step in data.get("steps", []):
            if step.get("type") == "response" and step.get("message"):
                reply = step["message"]
                break
    if not reply:
        reply = json.dumps(data)[:500]

    return JSONResponse(content={"summary": reply})


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
