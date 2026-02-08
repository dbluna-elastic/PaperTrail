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

## Project layout

- `config.py` – shared Elasticsearch client, index name, model ID, pipeline name
- `setup_elser.py` – deploy ELSER and create ingest pipeline
- `main.py` – create index and index arXiv papers
- `search.py` – semantic search (reusable function + CLI)
- `api.py` – FastAPI app with `/search` and `/health`
