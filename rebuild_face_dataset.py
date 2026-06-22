"""
rebuild_face_dataset.py
Rebuilds face dataset as 51 rows — one per face.
Converts structured JSON analysis → first-person Samudrika narrative.
Output: dataset_face_final.jsonl  (show to user before HF push)
"""
import json, urllib.request
from pathlib import Path

API_KEY  = "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"
MODEL    = "meta/llama-3.1-8b-instruct"
BASE_URL = "https://integrate.api.nvidia.com/v1"

HERE  = Path(__file__).parent
JSONL = HERE / "dataset.jsonl"
OUT   = HERE / "dataset_face_final.jsonl"

records = [json.loads(l) for l in JSONL.read_text().splitlines() if l.strip()]
print(f"Source: {len(records)} records\n")

# Resume
done = set()
if OUT.exists():
    for line in OUT.read_text().splitlines():
        try: done.add(json.loads(line)["file"])
        except: pass
print(f"Already done: {len(done)}\n")

def to_narrative(analysis, gender):
    """Convert structured JSON analysis to first-person Samudrika narrative."""

    a = analysis
    side = "right" if gender == "male" else "left"

    # Build a detailed summary of all features
    features_summary = []
    feat_map = {
        "face_shape":  ("face shape",  ["type","observation","shastra_meaning"]),
        "forehead":    ("forehead",    ["lines_count","width","observation","shastra_meaning"]),
        "eyebrows":    ("eyebrows",    ["shape","observation","shastra_meaning"]),
        "eyes":        ("eyes",        ["shape","pupil","observation","shastra_meaning"]),
        "nose":        ("nose",        ["type","nostrils","observation","shastra_meaning"]),
        "lips_mouth":  ("lips and mouth", ["size","color","observation","shastra_meaning"]),
        "chin":        ("chin",        ["shape","observation","shastra_meaning"]),
        "ears":        ("ears",        ["size","lobe","observation","shastra_meaning"]),
        "complexion":  ("complexion",  ["tone","observation","shastra_meaning"]),
    }
    for key, (label, fields) in feat_map.items():
        d = a.get(key, {})
        parts = [str(d.get(f,"")) for f in fields if d.get(f,"")]
        if parts:
            features_summary.append(f"{label.upper()}: {' | '.join(parts)}")

    features_text = '\n'.join(features_summary)
    overall = a.get("overall_reading","")
    predictions = a.get("key_predictions", [])
    dominant = a.get("dominant_quality","mixed")

    prompt = f"""You are a master of Samudrika Shastra — the ancient Indian science of face and body reading.

Below is a structured analysis of a {gender}'s face (examining the {side} side as per Samudrika tradition):

{features_text}

OVERALL: {overall}
DOMINANT QUALITY: {dominant}

Now write a flowing, first-person Samudrika Shastra reading addressed DIRECTLY to this person.
Use "your" throughout — speak as their Samudrika reader in a session.
Cover EVERY feature listed above (face shape, forehead, eyebrows, eyes, nose, lips, chin, ears, complexion).
Include the classical Shastra meaning for each feature.
End with overall life predictions and key destiny indicators.
Write in warm, authoritative, flowing prose — not bullet points, not JSON.
Minimum 300 words. Be specific and detailed."""

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
        "temperature": 0.4,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
    return resp["choices"][0]["message"]["content"].strip()

INSTRUCTION = "Give me a complete Samudrika Shastra reading of my face. Examine every feature — face shape, forehead, eyebrows, eyes, nose, lips, chin, ears, and complexion — and tell me what each reveals about my character, wealth, and destiny."

for rec in records:
    fname  = rec["file"]
    gender = rec["gender"]

    if fname in done:
        print(f"  skip: {fname}")
        continue

    print(f"  {fname} ({gender})...", end=" ", flush=True)
    try:
        narrative = to_narrative(rec["analysis"], gender)
        row = {
            "file":        fname,
            "gender":      gender,
            "image_path":  rec["image_path"],
            "instruction": INSTRUCTION,
            "text":        narrative,          # ← first-person reading, all features
            "analysis":    rec["analysis"],    # ← original JSON kept as reference
            "conversation": [
                {"role": "user",      "content": INSTRUCTION},
                {"role": "assistant", "content": narrative},
            ]
        }
        with open(OUT, 'a') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
        done.add(fname)
        print(f"✓ ({len(narrative)} chars)")
    except Exception as e:
        print(f"✗ {e}")

print(f"\n✅ {len(done)} rows saved → {OUT}")
