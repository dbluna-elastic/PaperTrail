import os
import time
import arxiv
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

# Load environment variables
load_dotenv()

ELASTIC_ENDPOINT = os.getenv("ELASTIC_ENDPOINT")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")

if not ELASTIC_ENDPOINT or not ELASTIC_API_KEY:
    print("Error: ELASTIC_ENDPOINT and ELASTIC_API_KEY must be set in .env")
    exit(1)

# Connect to Elastic Cloud
es = Elasticsearch(
    ELASTIC_ENDPOINT,
    api_key=ELASTIC_API_KEY
)

INDEX_NAME = "papertrail-papers"

def create_index_if_not_exists():
    """Creates the index with the specified mapping if it doesn't exist."""
    if not es.indices.exists(index=INDEX_NAME):
        mapping = {
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "summary": {"type": "text"},
                    "authors": {"type": "keyword"},
                    "published": {"type": "date"},
                    "pdf_url": {"type": "keyword"},
                    "categories": {"type": "keyword"}
                }
            }
        }
        es.indices.create(index=INDEX_NAME, body=mapping)
        print(f"Index '{INDEX_NAME}' created.")
    else:
        print(f"Index '{INDEX_NAME}' already exists.")

def fetch_and_index():
    print("Starting paper fetch from arXiv...")
    
    # Search for papers in Computer Science (cat:cs.*)
    # Using sort_by=SubmittedDate to get recent ones
    search = arxiv.Search(
        query="cat:cs.*",
        max_results=100, # Start with a smaller batch for testing
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    actions = []
    count = 0
    
    # arXiv client with delay to play nice
    client = arxiv.Client(
        page_size=100,
        delay_seconds=3.0,
        num_retries=3
    )

    for result in client.results(search):
        # Create the document structure
        doc = {
            "_index": INDEX_NAME,
            "_id": result.entry_id.split('/')[-1], # Use arXiv ID as ES Doc ID
            "_source": {
                "title": result.title,
                "summary": result.summary,
                "authors": [author.name for author in result.authors],
                "published": result.published,
                "pdf_url": result.pdf_url,
                "categories": result.categories
            }
        }
        actions.append(doc)
        count += 1

        # Bulk upload in chunks
        if len(actions) >= 50:
            helpers.bulk(es, actions)
            print(f"Indexed {len(actions)} papers...")
            actions = []

    if actions:
        helpers.bulk(es, actions)
        print(f"Indexed remaining {len(actions)} papers.")

    print(f"Total papers processed: {count}")

if __name__ == "__main__":
    if es.ping():
        print("Successfully connected to Elastic Cloud.")
        create_index_if_not_exists()
        fetch_and_index()
    else:
        print("Could not connect to Elastic Cloud.")
