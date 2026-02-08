import time

from config import (
    ELASTIC_API_KEY,
    ELASTIC_ENDPOINT,
    MODEL_ID,
    PIPELINE_NAME,
    get_es_client,
)

if not ELASTIC_ENDPOINT or not ELASTIC_API_KEY:
    print("Error: ELASTIC_ENDPOINT and ELASTIC_API_KEY must be set in .env")
    exit(1)

es = get_es_client(request_timeout=300)

def deploy_elser():
    print(f"Checking status of model '{MODEL_ID}'...")
    try:
        # Check if model exists
        try:
            es.ml.get_trained_models(model_id=MODEL_ID)
            print(f"Model '{MODEL_ID}' already downloaded.")
        except Exception:
            print(f"Model '{MODEL_ID}' not found. Downloading...")
            # ELSER is a pre-configured model, we trigger its download via this call
            # using the service_settings to auto-download if available or put_trained_model 
            # for ELSER usually requires just ensuring it's available.
            # actually for .elser_model_2 we need to "put" it from the registry
            es.ml.put_trained_model(
                model_id=MODEL_ID,
                input={"field_names": ["text_field"]}
            )
            print("Model downloaded.")

        # Check deployment
        max_retries = 60 # Increase to 5 minutes
        for i in range(max_retries):
            try:
                stats = es.ml.get_trained_models_stats(model_id=MODEL_ID)
                if not stats or 'trained_model_stats' not in stats:
                     print("Waiting for model stats...")
                     time.sleep(5)
                     continue

                state = stats['trained_model_stats'][0].get('deployment_stats', {}).get('state')
                print(f"Current model state: {state}")
                
                if state == 'started':
                     print(f"Model '{MODEL_ID}' is already deployed and started.")
                     break
                elif state == 'starting':
                    print("Model is starting... waiting.")
                    time.sleep(5)
                    continue
                else:
                    print(f"Starting deployment for '{MODEL_ID}'...")
                    es.ml.start_trained_model_deployment(
                        model_id=MODEL_ID,
                        number_of_allocations=1,
                        wait_for="started",
                        timeout="2m"
                    )
                    print("Model deployed successfully.")
                    break
            except Exception as e:
                # If it's the specific "download task running" error, wait and retry
                error_str = str(e)
                if "download task is currently running" in error_str:
                    print("Model download in progress. Waiting...")
                    time.sleep(10)
                elif "resource_already_exists_exception" in error_str or "existing deployment with the same id" in error_str:
                     print("Model already deployed (caught exception).")
                     break
                else:
                    print(f"Deployment attempt {i+1} failed: {e}")
                    if i < max_retries - 1:
                        time.sleep(5)
                    else:
                        raise e
            
    except Exception as e:
        print(f"Error during model setup: {e}")
        print("Ensure your Elastic Cloud instance has ML nodes enabled and sufficient resources.")

def create_pipeline():
    print(f"Creating ingest pipeline '{PIPELINE_NAME}'...")
    pipeline_body = {
        "description": "Pipeline to generate embeddings for PaperTrail papers using ELSER",
        "processors": [
            {
                "inference": {
                    "model_id": MODEL_ID,
                    "target_field": "content_embedding",
                    "field_map": {
                        "summary": "text_field"
                    },
                    "inference_config": {
                        "text_expansion": {
                            "results_field": "tokens"
                        }
                    }
                }
            }
        ]
    }
    es.ingest.put_pipeline(id=PIPELINE_NAME, body=pipeline_body)
    print(f"Pipeline '{PIPELINE_NAME}' created/updated.")

if __name__ == "__main__":
    if es.ping():
        deploy_elser()
        create_pipeline()
    else:
        print("Could not connect to Elastic Cloud.")
