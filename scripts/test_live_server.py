import urllib.request
import json

base = "http://127.0.0.1:8000"

def get(path):
    url = base + path
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.read().decode("utf-8")

print("=== TESTING LIVE FASTAPI APPLICATION AT HTTP://127.0.0.1:8000 ===")

# 1. Root index.html
status, html = get("/")
print(f"GET / -> Status: {status}, HTML length: {len(html)}")
assert status == 200 and "DepoIndex" in html, "Failed to load /"

# 2. Topics list
status, body = get("/api/topics")
data = json.loads(body)
print(f"GET /api/topics -> Status: {status}, Topics Count: {data['count']}")
assert status == 200 and data["count"] == 29, f"Expected 29 topics, got {data['count']}"

# 3. Topic filter query
status, body = get("/api/topics?q=PEAKS")
data = json.loads(body)
print(f"GET /api/topics?q=PEAKS -> Status: {status}, Filtered Count: {data['count']}")
assert status == 200 and data["count"] > 0, "Filter query failed"

# 4. Topic details
status, body = get("/api/topics/T001")
data = json.loads(body)
print(f"GET /api/topics/T001 -> Status: {status}, Topic: {data['topic']['topic_id']}, Source Lines: {len(data['source_lines'])}")
assert status == 200 and len(data["source_lines"]) > 0, "Failed to load topic details"

# 5. Semantic search
status, body = get("/api/search?q=unenforceable")
data = json.loads(body)
print(f"GET /api/search?q=unenforceable -> Status: {status}, Results: {len(data['results'])}")
assert status == 200 and len(data["results"]) > 0, "Semantic search failed"

# 6. Completeness
status, body = get("/api/completeness")
data = json.loads(body)
print(f"GET /api/completeness -> Status: {status}, PDF Pages: {data['total_pdf_pages']}, Testimony Lines: {data['extracted_testimony_lines']}")
assert status == 200 and data["total_pdf_pages"] == 122 and data["extracted_testimony_lines"] == 2042, "Completeness mismatch"

# 7. Validation
status, body = get("/api/validation")
data = json.loads(body)
print(f"GET /api/validation -> Status: {status}, Available: {data['available']}, Reviewed: {data['entries_reviewed']}")
assert status == 200 and data["available"] is True and data["entries_reviewed"] >= 20, "Validation mismatch"

# 8. Provenance check
status, body = get("/api/provenance/check?topic_id=T001")
data = json.loads(body)
print(f"GET /api/provenance/check?topic_id=T001 -> Status: {status}, OK: {data['ok']}, Lines: {data['line_count']}")
assert status == 200 and data["ok"] is True, "Provenance check failed"

print("\nALL 8 LIVE ENDPOINT CHECKS PASSED SUCCESSFULLY!")
