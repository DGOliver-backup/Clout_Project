import httpx
import time
import random
import numpy as np
import json
from typing import List

PROXY_URL = "http://127.0.0.1:8000"
FILES = ["small.txt", "medium.txt", "large.txt"]   
POLICIES = ["LRU", "LFU", "TTL"]
REQUEST_COUNT = 200

def set_policy(policy: str):
    print(f"\n🔄 Switching policy to: {policy}")
    httpx.post(f"{PROXY_URL}/cache/clear")
    httpx.post(f"{PROXY_URL}/cache/policy/{policy}")

def run_workload(policy: str, workload: List[str]):
    results = []
    print(f"🚀 Running workload for {policy} ...")

    for filename in workload:
        start = time.time()
        try:
            resp = httpx.get(f"{PROXY_URL}/{filename}")
            latency = (time.time() - start) * 1000

            results.append({
                "file": filename,
                "cache": resp.headers.get("X-Cache"),
                "reason": resp.headers.get("X-Cache-Reason"),
                "ttl": resp.headers.get("X-Cache-TTL"),
                "origin_latency": resp.headers.get("X-Origin-Latency-Ms"),
                "latency_ms": latency
            })

        except Exception as e:
            print(f"❌ Error fetching {filename}: {e}")

    return results

def get_stats():
    return httpx.get(f"{PROXY_URL}/cache/stats").json()

all_results = {}

for policy in POLICIES:
    set_policy(policy)

    # Zipf workload
    indices = np.random.zipf(1.2, REQUEST_COUNT)
    workload = [FILES[(i - 1) % len(FILES)] for i in indices]

    results = run_workload(policy, workload)
    stats = get_stats()

    all_results[policy] = {
        "stats": stats,
        "requests": results
    }

    print(f"📊 {policy} Hit Rate: {stats.get('hit_rate', 0):.2%}")
    print(f"📊 Avg Hit Latency: {stats.get('average_hit_latency_ms', 0):.2f}ms")
    print(f"📊 Origin Fetches: {stats.get('origin_fetches', 0)}")

with open("experiment_results.json", "w") as f:
    json.dump(all_results, f, indent=2)

print("\n✅ Experiment completed. Results saved to experiment_results.json")
