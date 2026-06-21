"""
Stage 0 — Extract raw text from each PDF into JSON.
Run once. Output: data_sets/raw_text/<book_key>.json
Each file: { "book": "...", "pages": [ { "page": N, "text": "..." }, ... ] }
"""
import json, re, sys
from pathlib import Path
import pdfplumber

BASE   = Path(__file__).parent
OUT    = BASE / "raw_text"
OUT.mkdir(exist_ok=True)

BOOKS = [
    {
        "key":  "hast_samudrika_shastra",
        "name": "Hast Samudrika Shastra (Indian Palmistry)",
        "path": str(BASE.parent / "hasta samudrika lakshana" / "2015.125592.Hast-Samudrika-Shastra_text.pdf"),
        "lang": "en",
    },
    {
        "key":  "samudrika_shastra",
        "name": "Samudrika Shastra",
        "path": str(BASE.parent / "Samudrika Shastra_text.pdf"),
        "lang": "hi",
    },
    {
        "key":  "samudrak_shastra_part1_2",
        "name": "Samudrak Shastra Part 1 and 2",
        "path": str(BASE.parent / "Samudrak Shastra Part 1 and 2 _text.pdf"),
        "lang": "hi",
    },
    {
        "key":  "saral_samudrik_face_reading",
        "name": "Saral Samudrik Shastra — Face Reading",
        "path": str(BASE.parent / "222132270-Saral-Samudrik-Shastra-FaceReading.pdf"),
        "lang": "hi",
    },
    {
        "key":  "hast_rekha",
        "name": "Hast Rekha Shastra",
        "path": str(BASE.parent / "Hasth Rekha Shastra" / "2015.441965.Hast-Rekha_text.pdf"),
        "lang": "hi",
    },
    {
        "key":  "samudrika_laksanam",
        "name": "Samudrika Laksanam",
        "path": str(BASE.parent / "2015.408515.Samudrika-Laksanam.pdf"),
        "lang": "sa",
    },
]

def is_readable(text, min_alpha_ratio=0.45):
    if not text or len(text.strip()) < 30:
        return False
    alpha = sum(c.isalpha() for c in text)
    return alpha / max(len(text), 1) >= min_alpha_ratio

def clean(text):
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

for book in BOOKS:
    out_file = OUT / f"{book['key']}.json"
    if out_file.exists():
        print(f"  skip (exists): {book['key']}")
        continue

    path = Path(book['path'])
    if not path.exists():
        print(f"  NOT FOUND: {book['path']}")
        continue

    pages = []
    with pdfplumber.open(str(path)) as pdf:
        total = len(pdf.pages)
        print(f"\n{book['name']}  ({total} pages)")
        for i, page in enumerate(pdf.pages):
            raw = page.extract_text() or ""
            text = clean(raw)
            readable = is_readable(text)
            pages.append({
                "page":     i + 1,
                "text":     text if readable else "",
                "readable": readable,
            })
        readable_count = sum(1 for p in pages if p["readable"])
        print(f"  readable pages: {readable_count}/{total}")

    out_file.write_text(json.dumps({
        "book": book["name"],
        "key":  book["key"],
        "lang": book["lang"],
        "pages": pages,
    }, ensure_ascii=False, indent=2))
    print(f"  → saved: {out_file.name}")

print("\n✅ Extraction complete.")
