import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json
from src.extraction.models import CanonicalTranscript, TopicRecord
from src.provenance.validator import ProvenanceValidator

raw_transcript = json.load(open('outputs/canonical_transcript.json', encoding='utf-8'))
transcript = CanonicalTranscript(**raw_transcript)
validator = ProvenanceValidator(transcript)

by_loc = transcript.by_page_line()
by_id = transcript.line_index()

topics_raw = json.load(open('outputs/topic_index.json', encoding='utf-8'))
print(f"=== VERIFYING PROVENANCE FOR ALL {len(topics_raw)} TOPICS ===")

all_ok = True
topics_checked = 0
invalid_refs = 0
missing_sids = 0
evidence_mismatches = 0
order_violations = 0

prev_loc = (0, 0)

for t in topics_raw:
    topics_checked += 1
    tid = t["topic_id"]
    sp, sl = t["start_page"], t["start_line"]
    ep, el = t["end_page"], t["end_line"]
    
    # 1. Start / End existence
    if (sp, sl) not in by_loc:
        print(f"[{tid}] Start line does not exist: P{sp}:L{sl}")
        invalid_refs += 1
        all_ok = False
    if (ep, el) not in by_loc:
        print(f"[{tid}] End line does not exist: P{ep}:L{el}")
        invalid_refs += 1
        all_ok = False
        
    # 2. Chronological start <= end
    if (sp, sl) > (ep, el):
        print(f"[{tid}] Invalid range: P{sp}:L{sl} > P{ep}:L{el}")
        invalid_refs += 1
        all_ok = False
        
    # 3. Chronological topic order
    if (sp, sl) < prev_loc:
        print(f"[{tid}] Order violation: P{sp}:L{sl} < previous {prev_loc}")
        order_violations += 1
        all_ok = False
    prev_loc = (sp, sl)
    
    # 4. Source IDs exist
    sids = t.get("source_ids", [])
    if not sids:
        print(f"[{tid}] Empty source_ids list")
        missing_sids += 1
        all_ok = False
    for sid in sids:
        if sid not in by_id:
            print(f"[{tid}] Missing source_id: {sid}")
            missing_sids += 1
            all_ok = False
            
    # 5. Supporting evidence verification
    rec = TopicRecord(**t)
    ok, notes = validator.validate_topic(rec)
    if not ok:
        print(f"[{tid}] ProvenanceValidator reported issues: {notes}")
        evidence_mismatches += 1
        all_ok = False

print("\n=== PROVENANCE SUMMARY ===")
print(f"Topics checked: {topics_checked}")
print(f"Invalid references: {invalid_refs}")
print(f"Missing source IDs: {missing_sids}")
print(f"Evidence mismatches: {evidence_mismatches}")
print(f"Order violations: {order_violations}")
print(f"Overall Provenance Status: {'PASS (100% Deterministic Provenance)' if all_ok else 'FAIL'}")
assert all_ok, "Provenance verification failed"
