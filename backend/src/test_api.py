"""
Module 10 test: exercise all five API endpoints against the real pipeline
using FastAPI's TestClient (real HTTP request/response cycle, same ASGI app
the server serves).
"""

import json
import warnings
warnings.filterwarnings('ignore')

from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)   # startup hook runs the full pipeline


def show(method, path, resp, note=""):
    print(f"\n--- {method} {path} -> {resp.status_code}  {note}")
    try:
        body = json.loads(resp.text)
        print(json.dumps(body, indent=2, ensure_ascii=False)[:2500])
    except Exception:
        print(resp.text[:1000])


print("=" * 80)
print("MODULE 10 TEST RESULTS — FastAPI backend (5 endpoints), real pipeline")
print("=" * 80)


# ---------- 0. root ----------
show("GET", "/", client.get("/"), "service info")

# ---------- 1. POST /ingest ----------
show("POST", "/ingest", client.post("/ingest", json={"note": "fresh export refresh"}))

# ---------- 2. GET /works/{work_id}/risk ----------
# a real HIGH / bypass work and a real LOW compliant work
show("GET", "/works/WS/MP18161/2024-2025/138071/risk",
     client.get("/works/WS/MP18161/2024-2025/138071/risk"), "disallowed-category High (98.0)")

show("GET", "/works/WS/MP620/2024-2025/133166/risk",
     client.get("/works/WS/MP620/2024-2025/133166/risk"), "known-compliant Low")

# edge case: unknown work
show("GET", "/works/WS/MP999/2099-2100/999999/risk",
     client.get("/works/WS/MP999/2099-2100/999999/risk"), "404 edge case")

# ---------- 3. GET /alerts ----------
show("GET", "/alerts?tier=High&limit=3",
     client.get("/alerts", params={"tier": "High", "limit": 3}), "top 3 High")
show("GET", "/alerts?tier=Medium&limit=3",
     client.get("/alerts", params={"tier": "Medium", "limit": 3}), "top 3 Medium")
show("GET", "/alerts?tier=High&ida=bareilly&limit=5",
     client.get("/alerts", params={"tier": "High", "ida": "bareilly", "limit": 5}),
     "High in BAREILLY (filters)")

# ---------- 4. POST /cases/{work_id}/action ----------
show("POST", "/cases/WS/MP18161/2024-2025/138071/action",
     client.post("/cases/WS/MP18161/2024-2025/138071/action",
                 json={"action": "escalated", "note": "Verified disallowed category", "reviewer": "audit@mspi"}),
     "record auditor action")
show("POST", "/cases/WS/MP18161/2024-2025/138071/action",
     client.post("/cases/WS/MP18161/2024-2025/138071/action",
                 json={"action": "unknown_thing"}),
     "invalid action -> 422")

# verify persistence file
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
f = ROOT / 'output' / 'audit_actions.json'
print(f"\n--- persisted audit_actions.json exists: {f.exists()}")
if f.exists():
    print(json.dumps(json.loads(f.read_text(encoding='utf-8')), indent=2))

# ---------- 5. GET /dashboard/summary ----------
show("GET", "/dashboard/summary?role=ministry",
     client.get("/dashboard/summary", params={"role": "ministry"}),
     "Ministry national view")
show("GET", "/dashboard/summary?role=state_nodal&state=Bihar",
     client.get("/dashboard/summary", params={"role": "state_nodal", "state": "Bihar"}),
     "State Nodal (Bihar)")
show("GET", "/dashboard/summary?role=district_authority&state=Bihar&ida=BAREILLY",
     client.get("/dashboard/summary", params={"role": "district_authority", "state": "Bihar", "ida": "BAREILLY"}),
     "District Authority (filter demo)")
show("GET", "/dashboard/summary?role=mp&mp=Hardeep",
     client.get("/dashboard/summary", params={"role": "mp", "mp": "Hardeep"}),
     "MP transparency view")
show("GET", "/dashboard/summary?role=bogus",
     client.get("/dashboard/summary", params={"role": "bogus"}),
     "invalid role -> 422")

print("\n=== END OF MODULE 10 API TEST ===")