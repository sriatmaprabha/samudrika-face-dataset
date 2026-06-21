"""
Stage 1 — Pure Python filter. Zero LLM tokens.
Reads raw_text/*.json, extracts only palmistry sentences, saves to stage1/*.json
Supports: English (Latin) and Hindi (Devanagari). Skips garbled text.
"""
import re, json
from pathlib import Path

BASE  = Path(__file__).parent
RAW   = BASE / "raw_text"
OUT   = BASE / "stage1"
OUT.mkdir(exist_ok=True)

# Books whose OCR is completely broken and have no vision-OCR replacement yet
# Remove a key from this set once 05_ocr.py has produced a clean raw_text file for it
SKIP_KEYS = set()  # all books now go through OCR via 05_ocr.py

# ── English palmistry keywords ────────────────────────────────
KEYWORDS = re.compile(
    r'\b(line of (life|heart|head|fate|sun|health|mars|mercury|saturn|apollo|jupiter)|'
    r'life line|heart line|head line|fate line|sun line|health line|marriage line|'
    r'children line|girdle of venus|rascette|bracelet|'
    r'mount of (venus|jupiter|saturn|apollo|mercury|moon|mars|lower mars|upper mars)|'
    r'mount of|'
    r'thumb|index finger|middle finger|ring finger|little finger|'
    r'finger nail|spatulate|conic hand|square hand|psychic hand|elementary hand|philosophic hand|'
    r'cheirognomy|cheiromancy|hasta samudrika|samudrika shastra|'
    r'island|triangle|cross|grille|star sign|fork|trident|fish sign|flag sign|'
    r'yav|chela|quadrangle|great triangle|'
    r'palm|palmist|palmistry|hand reading|hand-reading|'
    r'karma|destiny|fate|will power|vitality|constitution)\b',
    re.IGNORECASE
)

# ── Reject patterns (English) ─────────────────────────────────
REJECT   = re.compile(r'^(chapter|page|foreword|introduction|contents|index|part |section |\d+[\.\s])', re.IGNORECASE)
TOC_LINE = re.compile(r'\s{3,}\d+\s*$')
NOISE    = re.compile(r'[\^*#@$%&]{3,}')

# ── Devanagari / Hindi helpers ────────────────────────────────
# Digit immediately adjacent to Devanagari letter (no space) = garbled OCR
DEVA_GARBLED = re.compile(r'[ऀ-ॿ]\d|\d[ऀ-ॿ]')

def page_script(text):
    """Returns 'hindi', 'english', or 'garbled'."""
    total = max(len(text), 1)
    deva  = sum(1 for c in text if 'ऀ' <= c <= 'ॿ')
    if deva / total > 0.25:
        # Allow up to 4 digit-adjacent-to-Devanagari occurrences (OCR page numbers, footnotes)
        # More than 4 means the encoding itself is broken
        if len(DEVA_GARBLED.findall(text)) > 4:
            return 'garbled'
        return 'hindi'
    ascii_alpha = sum(1 for c in text if c.isascii() and c.isalpha())
    if ascii_alpha / total > 0.3:
        return 'english'
    return 'garbled'

def split_hindi(text):
    """Split Hindi text on danda (।) boundaries."""
    text = re.sub(r'\n+', ' ', text).strip()
    parts = re.split(r'[।॥]+', text)
    return [p.strip() for p in parts if p.strip()]

def split_english(text):
    text = re.sub(r'-\n([a-z])', r'\1', text)
    text = re.sub(r'\n+', ' ', text)
    return [p.strip() for p in re.split(r'(?<=[.!?])\s+', text)]

def is_meaningful_hindi(s):
    total = max(len(s), 1)
    if len(s) < 40 or len(s) > 600:
        return False
    deva = sum(1 for c in s if 'ऀ' <= c <= 'ॿ')
    if deva / total < 0.35:
        return False
    if DEVA_GARBLED.search(s):
        return False
    digits = sum(1 for c in s if c.isdigit())
    if digits / total > 0.15:
        return False
    return True

def is_meaningful_english(s):
    if len(s) < 50 or len(s) > 600:
        return False
    if REJECT.match(s):
        return False
    if TOC_LINE.search(s):
        return False
    if NOISE.search(s):
        return False
    # Reject long non-ASCII runs (garbled OCR in English text)
    if re.search(r'[^\x00-\x7F]{6,}', s):
        return False
    if not KEYWORDS.search(s):
        return False
    if not re.search(r'\b(is|are|was|were|has|have|had|will|can|may|indicate|show|reveal|'
                     r'denote|suggest|mean|point|signify|represent|gives|marks|tells|implies)\b',
                     s, re.IGNORECASE):
        return False
    return True

def get_term_english(s):
    m = KEYWORDS.search(s)
    return m.group(0).title() if m else "General"

def get_term_hindi(s):
    # Common palmistry terms in Hindi
    HINDI_TERMS = [
        ('जीवन रेखा', 'Life Line'), ('हृदय रेखा', 'Heart Line'), ('मस्तक रेखा', 'Head Line'),
        ('भाग्य रेखा', 'Fate Line'), ('सूर्य रेखा', 'Sun Line'), ('विवाह रेखा', 'Marriage Line'),
        ('शुक्र पर्वत', 'Mount of Venus'), ('बृहस्पति पर्वत', 'Mount of Jupiter'),
        ('हस्तरेखा', 'Palmistry'), ('हस्त', 'Hand'), ('अंगूठा', 'Thumb'),
        ('तर्जनी', 'Index Finger'), ('मध्यमा', 'Middle Finger'), ('अनामिका', 'Ring Finger'),
        ('कनिष्ठा', 'Little Finger'), ('नाखून', 'Nail'), ('पर्वत', 'Mount'),
        ('रेखा', 'Line'), ('हथेली', 'Palm'),
    ]
    for hindi, english in HINDI_TERMS:
        if hindi in s:
            return english
    return 'General'

for raw_file in sorted(RAW.glob("*.json")):
    data     = json.loads(raw_file.read_text())
    book     = data["book"]

    if data.get("key") in SKIP_KEYS:
        print(f"  skip (garbled OCR): {book[:55]}")
        continue

    readable = [p for p in data["pages"] if p.get("readable") and p.get("text")]

    sentences = []
    for page in readable:
        script = page_script(page["text"])
        if script == 'garbled':
            continue
        if script == 'hindi':
            for sent in split_hindi(page["text"]):
                if is_meaningful_hindi(sent):
                    sentences.append({
                        "page":     page["page"],
                        "sentence": sent,
                        "term":     get_term_hindi(sent),
                        "lang":     "hi",
                    })
        else:
            for sent in split_english(page["text"]):
                if is_meaningful_english(sent):
                    sentences.append({
                        "page":     page["page"],
                        "sentence": sent,
                        "term":     get_term_english(sent),
                        "lang":     "en",
                    })

    out = OUT / raw_file.name
    out.write_text(json.dumps({"book": book, "key": data["key"], "sentences": sentences},
                              ensure_ascii=False, indent=2))
    print(f"  {book[:55]:<55}  {len(sentences):>5} sentences")

print("\n✅ Stage 1 (filter) complete.")
