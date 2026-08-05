import requests
import time
import statistics
import argparse

URL = "http://localhost:8000/api/search/search"

PROFILES = {
    "Cold Global Facet": {
        "facet_types": ["metadata"]
    },
    "Text Search + Facets": {
        "fulltext": "History",
        "facet_types": ["metadata"]
    },
    "Deep Filtered Facets": {
        "facets": [
            {"type": "metadata", "subtype": "Author", "value": "John Smith"}
        ],
        "facet_types": ["metadata"]
    },
    "Pagination": {
        "page": 20
    }
}

def run_benchmark(name, payload, iterations=100):
    latencies = []
    
    # Warmup
    for _ in range(5):
        requests.post(URL, json=payload)
        
    for _ in range(iterations):
        start = time.time()
        resp = requests.post(URL, json=payload)
        latencies.append((time.time() - start) * 1000) # in ms
        if resp.status_code != 200:
            print(f"Error {resp.status_code}: {resp.text}")
            
    return {
        "name": name,
        "mean": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p95": statistics.quantiles(latencies, n=100)[94] if len(latencies) >= 2 else latencies[0],
        "p99": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 2 else latencies[0]
    }

def main(output_file):
    results = []
    for name, payload in PROFILES.items():
        print(f"Running profile: {name}...")
        res = run_benchmark(name, payload)
        results.append(res)
        print(f"  Mean: {res['mean']:.2f}ms | p95: {res['p95']:.2f}ms")
        
    with open(output_file, 'w') as f:
        f.write("Profile,Mean,Median,p95,p99\n")
        for r in results:
            f.write(f"{r['name']},{r['mean']},{r['median']},{r['p95']},{r['p99']}\n")
            
    print(f"Wrote results to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Output CSV file name")
    args = parser.parse_args()
    main(args.output)
