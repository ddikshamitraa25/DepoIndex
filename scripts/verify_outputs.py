import os
import json

files = [
    'outputs/canonical_transcript.json',
    'outputs/chunks.json',
    'outputs/topic_index.json',
    'outputs/topic_index.md',
    'outputs/completeness_report.json',
    'outputs/run_summary.json',
    'outputs/stability_report.md'
]

print("=== VERIFYING OUTPUT FILES EXISTENCE & SIZE ===")
for f in files:
    assert os.path.exists(f), f"Missing {f}"
    size = os.path.getsize(f)
    print(f"{f}: {size} bytes - OK")

topics = json.load(open('outputs/topic_index.json', encoding='utf-8'))
print(f"\nTotal Topics in topic_index.json: {len(topics)}")
t0 = topics[0]
t_last = topics[-1]
print(f"First topic: {t0['topic_id']} | P{t0['start_page']}:L{t0['start_line']} - P{t0['end_page']}:L{t0['end_line']}")
print(f"  Title: {t0['topic']}")
print(f"  Ref: {t0['supporting_source_reference']}")
print(f"  Evidence: {t0['supporting_evidence'][:80]}...")
print(f"Last topic: {t_last['topic_id']} | P{t_last['start_page']}:L{t_last['start_line']} - P{t_last['end_page']}:L{t_last['end_line']}")
print(f"  Title: {t_last['topic']}")
print(f"  Ref: {t_last['supporting_source_reference']}")
print(f"  Evidence: {t_last['supporting_evidence'][:80]}...")

transcript = json.load(open('outputs/canonical_transcript.json', encoding='utf-8'))
print(f"\nCanonical transcript: {len(transcript['lines'])} lines, {transcript['total_pdf_pages']} total PDF pages")
testimony_lines = [ln for ln in transcript['lines'] if ln.get('is_testimony')]
print(f"Testimony lines count: {len(testimony_lines)}")

chunks = json.load(open('outputs/chunks.json', encoding='utf-8'))
print(f"Chunks count: {len(chunks)}")
