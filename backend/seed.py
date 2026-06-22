"""
AuditLens — Seed with sample audits
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

SAMPLE_URLS = [
    "https://example-dental.com",
    "https://warm-spa.com",
    "https://hvac-pros.net",
    "https://salon-glow.com",
]

for url in SAMPLE_URLS:
    r = client.post("/api/audits", json={"url": url})
    data = r.json()
    print(f"  Audit #{data['id']} for {url}: score={data['overall_score']}, status={data['status']}")

print(f"\nTotal audits: {len(client.get('/api/audits').json())}")
