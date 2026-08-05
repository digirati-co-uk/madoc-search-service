import os
import json
import requests
import time

URL = "http://localhost:8000/api/search/iiif"

def ingest_all():
    directory = "synthetic_data"
    if not os.path.exists(directory):
        print(f"Directory {directory} not found. Run generate_manifests.py first.")
        return

    files = [f for f in os.listdir(directory) if f.endswith(".json")]
    
    print(f"Ingesting {len(files)} manifests...")
    start_time = time.time()
    
    for idx, filename in enumerate(files):
        with open(os.path.join(directory, filename), 'r') as f:
            data = json.load(f)
            resp = requests.post(URL, json=data)
            if resp.status_code not in (200, 201):
                print(f"Failed to ingest {filename}: {resp.status_code} - {resp.text}")
        
        if (idx + 1) % 50 == 0:
            print(f"Ingested {idx + 1}/{len(files)}")
            
    print(f"Ingestion completed in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    ingest_all()
