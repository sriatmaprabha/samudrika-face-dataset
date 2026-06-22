"""
augment_dataset.py
Expands dataset.jsonl from 51 records to 600+ training pairs.

Strategy:
  1. 3 full-reading prompt variations per image  →  153 pairs
  2. 9 feature-level prompts per image           →  459 pairs
  Total: ~612 pairs

Output: dataset_augmented.jsonl (keeps dataset.jsonl unchanged)
"""
import json
from pathlib import Path

HERE  = Path(__file__).parent
JSONL = HERE / "dataset.jsonl"
OUT   = HERE / "dataset_augmented.jsonl"

records = [json.loads(l) for l in JSONL.read_text().splitlines() if l.strip()]
print(f"Source: {len(records)} records")

# ── Full-reading prompt variations ──────────────────────────────────────────

FULL_INSTRUCTIONS = [
    # Variation 1 — direct
    "Analyze this {gender}'s face according to Samudrika Shastra. "
    "Examine the {side} side. Return a structured JSON reading.",

    # Variation 2 — classical framing
    "You are a Samudrika Shastra expert. Perform a classical face reading "
    "for this {gender}. Examine the {side} side of the face as per tradition.",

    # Variation 3 — prediction focused
    "Based on Samudrika Shastra, what does this {gender}'s face reveal about "
    "their character, wealth, and destiny? Examine the {side} side.",
]

# ── Feature-level prompts ────────────────────────────────────────────────────

FEATURE_PROMPTS = {
    "face_shape": (
        "What is the shape of this {gender}'s face according to Samudrika Shastra, "
        "and what does it indicate?",
        ["type", "observation", "shastra_meaning", "quality"]
    ),
    "forehead": (
        "Examine the forehead of this {gender} according to Samudrika Shastra. "
        "How many lines are visible, how wide is it, and what does it predict?",
        ["lines_count", "width", "observation", "shastra_meaning", "quality"]
    ),
    "eyebrows": (
        "Describe the eyebrows of this {gender} and their Samudrika Shastra meaning.",
        ["shape", "observation", "shastra_meaning", "quality"]
    ),
    "eyes": (
        "According to Samudrika Shastra, what do the eyes of this {gender} reveal "
        "about their nature and destiny?",
        ["shape", "pupil", "observation", "shastra_meaning", "quality"]
    ),
    "nose": (
        "Examine the nose of this {gender} according to Samudrika Shastra. "
        "What does its shape and size indicate?",
        ["type", "nostrils", "observation", "shastra_meaning", "quality"]
    ),
    "lips_mouth": (
        "What do the lips and mouth of this {gender} reveal according to Samudrika Shastra?",
        ["size", "color", "observation", "shastra_meaning", "quality"]
    ),
    "chin": (
        "Describe the chin of this {gender} and its Samudrika Shastra interpretation.",
        ["shape", "observation", "shastra_meaning", "quality"]
    ),
    "ears": (
        "According to Samudrika Shastra, what do the ears of this {gender} indicate "
        "about their life and fortune?",
        ["size", "lobe", "observation", "shastra_meaning", "quality"]
    ),
    "complexion": (
        "What does the complexion of this {gender} indicate according to Samudrika Shastra?",
        ["tone", "observation", "shastra_meaning", "quality"]
    ),
}

# ── Generate augmented pairs ─────────────────────────────────────────────────

def make_pair(rec, instruction, answer_text, pair_type):
    """One training pair: image + instruction → answer."""
    return {
        "file":       rec["file"],
        "gender":     rec["gender"],
        "image_path": rec["image_path"],
        "pair_type":  pair_type,
        # For HuggingFace dataset (matches LaTeX OCR format):
        "text":       answer_text,
        # Full conversation for Unsloth:
        "conversation": [
            {"role": "user",      "content": instruction},
            {"role": "assistant", "content": answer_text},
        ]
    }

augmented = []

for rec in records:
    a      = rec["analysis"]
    gender = rec["gender"]
    side   = "right" if gender == "male" else "left"

    # ── 1. Full-reading variations (3 per image) ──────────────────────────
    full_answer = rec["target_text"]  # the complete JSON analysis
    for i, tmpl in enumerate(FULL_INSTRUCTIONS):
        instruction = tmpl.format(gender=gender, side=side)
        augmented.append(make_pair(rec, instruction, full_answer, f"full_v{i+1}"))

    # ── 2. Feature-level prompts (9 per image) ────────────────────────────
    for feat, (prompt_tmpl, fields) in FEATURE_PROMPTS.items():
        feat_data = a.get(feat, {})
        if not feat_data:
            continue
        # Extract only the relevant fields for this feature
        feat_answer = {k: feat_data.get(k, "") for k in fields}
        feat_answer["feature"] = feat

        instruction = prompt_tmpl.format(gender=gender, side=side)
        augmented.append(make_pair(
            rec, instruction,
            json.dumps(feat_answer, ensure_ascii=False),
            f"feature_{feat}"
        ))

# Write output
with open(OUT, "w") as f:
    for pair in augmented:
        f.write(json.dumps(pair, ensure_ascii=False) + "\n")

# Stats
full_pairs    = [p for p in augmented if p["pair_type"].startswith("full")]
feature_pairs = [p for p in augmented if p["pair_type"].startswith("feature")]
males    = [p for p in augmented if p["gender"] == "male"]
females  = [p for p in augmented if p["gender"] == "female"]

print(f"\n✅ Augmented dataset: {len(augmented)} pairs")
print(f"   Full-reading pairs : {len(full_pairs)}  ({len(records)} images × 3 prompts)")
print(f"   Feature-level pairs: {len(feature_pairs)}  ({len(records)} images × 9 features)")
print(f"   Male pairs         : {len(males)}")
print(f"   Female pairs       : {len(females)}")
print(f"\nSaved: {OUT}")
print(f"\nSample pairs:")
for p in augmented[:2]:
    print(f"  [{p['pair_type']}] {p['file']}")
    print(f"    Q: {p['conversation'][0]['content'][:80]}")
    print(f"    A: {p['conversation'][1]['content'][:80]}")
    print()
