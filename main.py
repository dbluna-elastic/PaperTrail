import arxiv
from elasticsearch import helpers

from config import (
    ELASTIC_API_KEY,
    ELASTIC_ENDPOINT,
    INDEX_NAME,
    PIPELINE_NAME,
    get_es_client,
)

if not ELASTIC_ENDPOINT or not ELASTIC_API_KEY:
    print("Error: ELASTIC_ENDPOINT and ELASTIC_API_KEY must be set in .env")
    exit(1)

es = get_es_client(request_timeout=300)

def create_index_if_not_exists():
    """Creates the index with the specified mapping if it doesn't exist."""
    mapping = {
        "properties": {
            "title": {"type": "text"},
            "summary": {"type": "text"},
            "authors": {"type": "keyword"},
            "published": {"type": "date"},
            "pdf_url": {"type": "keyword"},
            "categories": {"type": "keyword"},
            "content_embedding": {
                "properties": {
                    "tokens": {
                        "type": "rank_features"
                    }
                }
            }
        }
    }
    
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME, body={"mappings": mapping})
        print(f"Index '{INDEX_NAME}' created.")
    else:
        # Update mapping just in case
        es.indices.put_mapping(index=INDEX_NAME, body=mapping)
        print(f"Index '{INDEX_NAME}' exists. Mapping updated.")

def fetch_and_index():
    print("Starting paper fetch from arXiv...")
    
    # Search for papers in Computer Science (cat:cs.*)
    # Using sort_by=SubmittedDate to get recent ones
    search = arxiv.Search(
        query="cat:cs.*",
        max_results=1000,
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
            try:
                helpers.bulk(es, actions, pipeline=PIPELINE_NAME)
                print(f"Indexed {len(actions)} papers...")
            except helpers.BulkIndexError as e:
                print("Bulk Indexing Failed (Batch)!")
                if e.errors:
                    print(f"First error: {e.errors[0]}")
            actions = []

    try:
        if actions:
            helpers.bulk(es, actions, pipeline=PIPELINE_NAME)
            print(f"Indexed remaining {len(actions)} papers.")
    except helpers.BulkIndexError as e:
        print("Bulk Indexing Failed!")
        print(f"First error: {e.errors[0]}")
        # Continue or simple exit
        pass

    print(f"Total papers processed: {count}")

if __name__ == "__main__":
    if es.ping():
        print("Successfully connected to Elastic Cloud.")
        create_index_if_not_exists()
        fetch_and_index()
    else:
        print("Could not connect to Elastic Cloud.")
