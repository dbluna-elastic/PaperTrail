# PaperTrail

Index arXiv CS papers into Elasticsearch with ELSER semantic embeddings and search them by meaning.

## Prerequisites

- Python 3.9+
- Elastic Cloud deployment with ML nodes enabled (for ELSER)

## Setup

1. **Environment**

   Copy `.env.example` to `.env` and set:

   - `ELASTIC_ENDPOINT` – your Elastic Cloud endpoint URL
   - `ELASTIC_API_KEY` – an API key with index and ML permissions

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Deploy ELSER and ingest pipeline (once)**

   ```bash
   python setup_elser.py
   ```

   This downloads/deploys the ELSER model (`.elser_model_2`) and creates the `papertrail-semantic-pipeline` ingest pipeline.

4. **Create index and index papers**

   ```bash
   python main.py
   ```

   This creates the `papertrail-papers` index (if needed), fetches recent arXiv CS papers, and bulk-indexes them through the semantic pipeline so summaries get ELSER embeddings.

## Search

**CLI**

```bash
python search.py "transformer attention mechanisms"
python search.py -n 20 "reinforcement learning"
```

**HTTP API**

```bash
uvicorn api:app --reload
```

Then:

- `GET /search?q=transformer%20attention&size=20` – semantic search; returns JSON with `hits` and `total`
- `GET /health` – health check

## Docker

- **Index papers (one-off):** `docker compose run --rm papertrail` – runs `setup_elser.py` then `main.py`.
- **Search website:** `docker compose up web` – runs the search API and UI on port 8000. Open http://localhost:8000 for the search interface.

Ensure `.env` is present with `ELASTIC_ENDPOINT` and `ELASTIC_API_KEY`.

## Summarize (Elastic Agent Builder)

The search UI includes a **Summarize** button on each result card. It uses [Elastic Agent Builder](https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/kibana-api) to generate a short AI summary of the paper’s title and abstract.

**Requirements:**

1. Create an agent in Kibana (Elastic Agent Builder) with instructions to summarize paper title and abstract (e.g. “Given a title and abstract, reply with a short 2–3 sentence summary.”).
2. Set these variables in `.env`:
   - `KIBANA_URL` – your Kibana base URL (e.g. `https://xxx.kb.us-central1.gcp.cloud.es.io`)
   - `KIBANA_API_KEY` – API key with `read_agent_builder` (or equivalent) for Kibana
   - `AGENT_ID` – the agent ID (defaults to `elastic-ai-agent` if unset)

If these are not set, clicking Summarize will show an error asking you to configure them.

## Observability (OpenLIT + Elastic)

When configured, the app sends traces to Elastic APM via [OpenLIT](https://github.com/openlit/openlit) (OpenTelemetry). You get request tracing for all routes and LLM spans for Summarize calls, including token usage.

**Setup:**

1. In Kibana go to **Observability → APM → Add data → OpenTelemetry** and complete the steps.
2. Copy `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` (use `Authorization=Bearer%20<API_KEY>` format).
3. Set them in `.env`:
   - `OTEL_EXPORTER_OTLP_ENDPOINT` – e.g. `https://<id>.apm.<region>.cloud.es.io:443`
   - `OTEL_EXPORTER_OTLP_HEADERS` – e.g. `Authorization=Bearer%20<your-api-key>`

If these are not set, the app runs as before and no traces are exported. The Summarize response still includes a `usage` object (input/output/total tokens) for the UI; token counts are estimated when Kibana does not return usage.

**Optional:** Import the OpenLIT GenAI dashboard (NDJSON) from [OpenLIT Elastic docs](https://docs.openlit.io/latest/sdk/destinations/elastic) via **Stack Management → Saved Objects** to view GenAI metrics in Kibana.

## Project layout

- `config.py` – shared Elasticsearch client, index name, model ID, pipeline name
- `setup_elser.py` – deploy ELSER and create ingest pipeline
- `main.py` – create index and index arXiv papers
- `search.py` – semantic search (reusable function + CLI)
- `api.py` – FastAPI app with `/search`, `/health`, and `/` (search UI)
- `static/index.html` – search UI (single-page app)
