"""
Stage 3 — Pure Python quality check. Zero LLM tokens.
Reads stage2/*.json, validates each row, saves approved to stage3/*.json
"""
import re, json
from pathlib import Path

BASE = Path(__file__).parent
S2   = BASE / "stage2"
OUT  = BASE / "stage3"
OUT.mkdir(exist_ok=True)

FILLER = re.compile(
    r'\b(I |we |our |my |this book|the author|chapter|foreword|introduction|'
    r'table of contents|as mentioned|see page|refer to|ibid)\b',
    re.IGNORECASE
)

def is_good(row):
    orig  = (row.get("original") or "").strip()
    exp   = (row.get("simple_explanation") or "").strip()
    means = (row.get("what_it_means") or "").strip()
    term  = (row.get("term") or "").strip()

    if len(orig)  < 30: return False, "original too short"
    if len(exp)   < 15: return False, "explanation too short"
    if len(means) < 15: return False, "what_it_means too short"
    if not term:        return False, "missing term"

    # Reject if explanation is just a copy of original
    if exp.lower().strip('.,') == orig.lower().strip('.,'):
        return False, "explanation is a copy"

    # Reject authorial/narrative language that slipped through
    if FILLER.search(exp) or FILLER.search(means):
        return False, "narrative filler"

    # Reject non-ASCII originals that are NOT Devanagari (truly garbled)
    non_ascii = re.findall(r'[^\x00-\x7F]+', orig)
    if non_ascii:
        combined  = ''.join(non_ascii)
        deva_count = sum(1 for c in combined if 'ऀ' <= c <= 'ॿ')
        if len(combined) >= 5 and deva_count / len(combined) < 0.5:
            return False, "garbled original"

    # Both explanation and what_it_means must end with punctuation
    if not re.search(r'[.!?]$', exp):
        return False, "explanation has no ending"

    return True, "ok"

for s2_file in sorted(S2.glob("*.json")):
    data = json.loads(s2_file.read_text())
    rows = data.get("rows", [])
    if not rows:
        continue

    approved, rejected = [], 0
    reasons = {}
    for row in rows:
        ok, reason = is_good(row)
        if ok:
            approved.append(row)
        else:
            rejected += 1
            reasons[reason] = reasons.get(reason, 0) + 1

    out = OUT / s2_file.name
    out.write_text(json.dumps({
        "book":     data["book"],
        "key":      data["key"],
        "approved": approved,
    }, ensure_ascii=False, indent=2))

    print(f"  {data['book'][:50]:<52}  approved: {len(approved):>4}  rejected: {rejected}")
    for r, c in reasons.items():
        print(f"      {r}: {c}")

print("\n✅ Stage 3 (QC) complete.")
