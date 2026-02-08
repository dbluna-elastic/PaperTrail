"""Shared configuration and Elasticsearch client for PaperTrail."""
import os

from dotenv import load_dotenv

load_dotenv()

ELASTIC_ENDPOINT = os.getenv("ELASTIC_ENDPOINT")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")

INDEX_NAME = "papertrail-papers"
MODEL_ID = ".elser_model_2"
PIPELINE_NAME = "papertrail-semantic-pipeline"


def get_es_client(request_timeout=30):
    """Return an Elasticsearch client. Use request_timeout=300 for long operations (e.g. setup)."""
    from elasticsearch import Elasticsearch
    return Elasticsearch(
        ELASTIC_ENDPOINT,
        api_key=ELASTIC_API_KEY,
        request_timeout=request_timeout,
    )
