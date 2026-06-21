"""
Stage 0-OCR — Vision LLM OCR for scanned / garbled-encoding PDFs.
Uses meta/llama-3.2-11b-vision-instruct via Nvidia API.
Renders each PDF page as a JPEG, sends to vision model, extracts clean text.
Output: raw_text/<key>.json  (same format as 00_extract_text.py)
Resume-safe: already-processed pages are skipped on re-run.
"""
import fitz, base64, json, time, urllib.request
from pathlib import Path

BASE    = Path(__file__).parent
OUT     = BASE / "raw_text"
OUT.mkdir(exist_ok=True)
CFG     = json.loads((BASE / "config.json").read_text())

API_KEY  = CFG["nvidia_api_key"]
BASE_URL = CFG["nvidia_base_url"]
MODEL    = "meta/llama-3.2-11b-vision-instruct"

DPI         = 120    # good balance: readable text, small payload (~50-80KB/page)
JPEG_Q      = 75
TIMEOUT     = 90     # seconds per page
PAUSE       = 0.8    # seconds between pages

# ── Books to OCR ─────────────────────────────────────────────────────────────
DESKTOP = Path.home() / "Desktop" / "samudrika_lakshana"
BOOKS = [
    {
        "key":  "samudrika_laksanam",
        "book": "Samudrika Laksanam",
        "pdf":  DESKTOP / "2015.408515.Samudrika-Laksanam.pdf",
        "lang": "en",   # English / Tamil
    },
    {
        "key":  "saral_samudrik_face_reading",
        "book": "Saral Samudrik Shastra — Face Reading",
        "pdf":  DESKTOP / "222132270-Saral-Samudrik-Shastra-FaceReading.pdf",
        "lang": "hi",   # Hindi
    },
    {
        "key":  "samudrika_shastra",
        "book": "Samudrika Shastra",
        "pdf":  DESKTOP / "Samudrika Shastra_text.pdf",
        "lang": "hi",   # Hindi/Sanskrit
    },
    {
        "key":  "hast_samudrika_shastra_v2",
        "book": "Hast Samudrika Shastra (v2)",
        "pdf":  DESKTOP / "hasta samudrika lakshana" / "2015.125592.Hast-Samudrika-Shastra_text.pdf",
        "lang": "hi",
    },
    {
        "key":  "hast_rekha_v2",
        "book": "Hast Rekha Shastra (v2)",
        "pdf":  DESKTOP / "Hasth Rekha Shastra" / "2015.441965.Hast-Rekha_text.pdf",
        "lang": "hi",
    },
]

def ocr_page(pix, lang):
    img_b64 = base64.b64encode(pix.tobytes("jpeg", jpg_quality=JPEG_Q)).decode()
    if lang == "hi":
        prompt = ("This is a page from a classical Hindi/Sanskrit book on palmistry "
                  "(Samudrika Shastra / Hast Rekha Shastra). "
                  "Extract all text exactly as written in Devanagari script. "
                  "Output only the extracted text, nothing else.")
    else:
        prompt = ("Extract all text from this page exactly as it appears. "
                  "Output only the extracted text, nothing else.")

    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": prompt},
            ]
        }],
        "max_tokens": 2000,
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        resp = json.loads(r.read())
    return resp["choices"][0]["message"]["content"].strip()

def is_readable(text):
    """Rough check: at least 30 chars of real content."""
    return len(text.strip()) >= 30

for book_cfg in BOOKS:
    pdf_path = book_cfg["pdf"]
    key      = book_cfg["key"]
    book     = book_cfg["book"]
    lang     = book_cfg["lang"]
    out_file = OUT / f"{key}.json"

    if not pdf_path.exists():
        print(f"  skip (PDF not found): {book}")
        continue

    # Load existing progress
    existing_pages = {}
    if out_file.exists():
        try:
            existing = json.loads(out_file.read_text())
            for p in existing.get("pages", []):
                existing_pages[p["page"]] = p
        except Exception:
            pass

    doc       = fitz.open(str(pdf_path))
    total     = len(doc)
    new_count = sum(1 for i in range(total) if (i+1) not in existing_pages)

    if new_count == 0:
        print(f"  skip (all {total} pages done): {book}")
        doc.close()
        continue

    start_count = len(existing_pages)
    print(f"\n  {book}  ({total} pages, {start_count} already done, {new_count} to OCR)")
    pages = list(existing_pages.values())

    for i in range(total):
        pg_num = i + 1
        if pg_num in existing_pages:
            continue

        print(f"    page {pg_num}/{total}...", end=" ", flush=True)
        try:
            pix  = doc[i].get_pixmap(dpi=DPI)
            text = ocr_page(pix, lang)
            readable = is_readable(text)
            pages.append({"page": pg_num, "text": text, "readable": readable})
            print(f"✓ {len(text)} chars")
        except Exception as e:
            pages.append({"page": pg_num, "text": "", "readable": False})
            print(f"✗ {e}")

        # Save after every page (crash/network safe)
        pages_sorted = sorted(pages, key=lambda p: p["page"])
        out_file.write_text(json.dumps(
            {"book": book, "key": key, "pages": pages_sorted},
            ensure_ascii=False, indent=2
        ))

        if i < total - 1:
            time.sleep(PAUSE)

    readable_count = sum(1 for p in pages if p.get("readable"))
    print(f"  → {readable_count}/{total} readable pages  →  {out_file.name}")
    doc.close()

print("\n✅ OCR complete. Now run: python3 01_filter.py → 02_draft.py → 03_qc.py → 04_write_excel.py")
