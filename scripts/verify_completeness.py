import json

report = json.load(open('outputs/completeness_report.json', encoding='utf-8'))

print("=== COMPLETENESS REPORT AUDIT ===")
print("Total PDF Pages Scanned:", report["total_pdf_pages"])
print("Testimony Pages Count:", len(report["testimony_pages"]))
print(f"Testimony Page Range: P{report['testimony_page_start']} to P{report['testimony_page_end']}")
print("Extracted Lines (Total):", report["extracted_lines"])
print("Extracted Testimony Lines:", report["extracted_testimony_lines"])
print("Chunks Created:", report["chunks_created"])
print("Gaps Detected Count:", len(report["gaps_detected"]))
print("Duplicate Lines Count:", len(report["duplicate_lines"]))
print("Extraction Warnings Count:", len(report["extraction_warnings"]))

# Verify testimony continuity: every page from testimony_page_start to testimony_page_end must be present
expected_pages = set(range(report["testimony_page_start"], report["testimony_page_end"] + 1))
actual_testimony_pages = set(report["extracted_testimony_pages"])
missing_testimony_pages = sorted(expected_pages - actual_testimony_pages)
print("Missing Testimony Pages in Range:", missing_testimony_pages)
assert not missing_testimony_pages, f"Missing pages: {missing_testimony_pages}"

# Verify lines per page: each testimony page should have consecutive lines
transcript = json.load(open('outputs/canonical_transcript.json', encoding='utf-8'))
lines_by_page = {}
for ln in transcript["lines"]:
    if ln.get("is_testimony"):
        lines_by_page.setdefault(ln["page"], []).append(ln["line"])

dropped_lines = []
for p, lns in sorted(lines_by_page.items()):
    expected_lns = list(range(1, max(lns) + 1))
    if lns != expected_lns:
        diff = set(expected_lns) - set(lns)
        dropped_lines.append((p, diff))

print("Dropped / Skipped Lines Count Across Testimony Pages:", len(dropped_lines))
assert not dropped_lines, f"Dropped lines: {dropped_lines}"
print("Completeness Status: PASS (100% Complete, Zero Silent Gaps)")
