"""
Stage 2 — Nvidia LLM drafting. Only meaningful sentences go in.
Reads stage1/*.json, drafts simple explanation + insight, saves to stage2/*.json
Batches 12 sentences per API call to minimise tokens.
"""
import json, time, urllib.request, urllib.error
from pathlib import Path

BASE   = Path(__file__).parent
S1     = BASE / "stage1"
OUT    = BASE / "stage2"
OUT.mkdir(exist_ok=True)
CFG    = json.loads((BASE / "config.json").read_text())

API_KEY  = CFG["nvidia_api_key"]
MODEL    = CFG["nvidia_model"]
BASE_URL = CFG["nvidia_base_url"]
BATCH    = 8    # sentences per call — keeps responses fast and reliable

SYSTEM_PROMPT = """You are an expert in Samudrika Shastra — the ancient Indian science of body reading (palmistry, physiognomy). You receive sentences extracted from classical palmistry texts. Sentences may be in English or Hindi.

For each sentence return a JSON object with exactly these fields:
- "page": (copy from input)
- "term": the primary palmistry concept in English (e.g. "Life Line", "Mount of Jupiter", "Thumb")
- "original": the cleaned sentence (fix obvious OCR typos; for Hindi, keep in Devanagari script)
- "simple_explanation": for English sentences: 1-2 plain English sentences explaining what this teaches (max 60 words). For Hindi sentences: begin with "Translation: [English translation]." then add 1 sentence of explanation. Max 70 words total.
- "what_it_means": practical interpretation in English — what does this feature reveal about the person's character, health, destiny, or relationships? Speak like a wise guru. Max 50 words.

Return a JSON array of objects, one per input sentence. No extra text."""

def call_nvidia(sentences):
    numbered = "\n".join(
        f'{i+1}. [page {s["page"]}] {s["sentence"]}'
        for i, s in enumerate(sentences)
    )
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Process these {len(sentences)} sentences:\n\n{numbered}"},
        ],
        "max_tokens": 3000,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())
    return resp["choices"][0]["message"]["content"]

def parse_response(text, sentences):
    # Extract JSON array from response
    text = text.strip()
    start = text.find('[')
    end   = text.rfind(']') + 1
    if start == -1 or end == 0:
        return []
    try:
        rows = json.loads(text[start:end])
        # Ensure page is set
        for i, row in enumerate(rows):
            if not row.get("page") and i < len(sentences):
                row["page"] = sentences[i]["page"]
        return rows
    except Exception:
        return []

for s1_file in sorted(S1.glob("*.json")):
    data      = json.loads(s1_file.read_text())
    book      = data["book"]
    sentences = data["sentences"]

    if not sentences:
        print(f"  skip (0 sentences): {book[:50]}")
        continue

    out = OUT / s1_file.name
    batches = [sentences[i:i+BATCH] for i in range(0, len(sentences), BATCH)]

    # Resume: load existing rows + find which batch to continue from
    rows = []
    start_batch = 0
    if out.exists():
        existing = json.loads(out.read_text())
        ex_rows = existing.get("rows", [])
        ex_done = existing.get("batches_done", 0)
        if ex_done >= len(batches):
            print(f"  skip (complete, {len(ex_rows)} rows): {book[:45]}")
            continue
        if ex_rows:
            rows = ex_rows
            start_batch = ex_done
            print(f"\n  {book[:55]}  (resuming from batch {start_batch+1}/{len(batches)}, {len(rows)} rows so far)")
        else:
            print(f"\n  {book[:55]}")
    else:
        print(f"\n  {book[:55]}")

    for bi, batch in enumerate(batches):
        if bi < start_batch:
            continue
        print(f"    batch {bi+1}/{len(batches)} ({len(batch)} sentences)...", end=" ", flush=True)
        try:
            raw    = call_nvidia(batch)
            parsed = parse_response(raw, batch)
            rows.extend(parsed)
            print(f"✓ {len(parsed)} rows")
        except Exception as e:
            print(f"✗ error: {e}")
        # Save progress after every batch (crash-safe)
        out.write_text(json.dumps({"book": book, "key": data["key"],
                                   "rows": rows, "batches_done": bi + 1},
                                  ensure_ascii=False, indent=2))
        if bi < len(batches) - 1:
            time.sleep(0.5)

    print(f"  → {len(rows)} rows saved")

print("\n✅ Stage 2 (draft) complete.")
