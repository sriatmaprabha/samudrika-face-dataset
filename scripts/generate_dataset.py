"""
Samudrika Dataset Generator
Analyzes each face image using Nvidia vision API guided by Samudrika Shastra sl notes.
Produces: dataset.jsonl — one line per image with structured analysis.
"""
import base64, json, urllib.request, os, glob, subprocess
from pathlib import Path

API_KEY  = "YOUR_NVIDIA_API_KEY_HERE"
MODEL    = "meta/llama-3.2-90b-vision-instruct"
BASE_URL = "https://integrate.api.nvidia.com/v1"
OUT      = Path("/tmp/sl_faces/dataset.jsonl")

FACES_DIR = Path("/tmp/sl_faces/samudrika dataset")

SYSTEM_PROMPT = """You are an expert in Samudrika Shastra — the ancient Indian science of physiognomy (body and face reading). You analyze faces strictly according to classical Samudrika Shastra principles.

KEY RULES from the text:
- For WOMEN: examine the LEFT side of the face
- For MEN: examine the RIGHT side of the face

FACE ANALYSIS FRAMEWORK (examine in this order):
1. HEAD SHAPE: Round+big=wealth, Round+small=beauty+wealth, Long=poverty, Long+broad=long life
2. FOREHEAD: 5 lines=100 years life, 4=80yrs, 3=60yrs, 2=short life; vein in middle=leader; broad=riches
3. EYEBROWS: Even+arched+black+not joining=ruler; thick hair=strength; joined in middle=bad omen; hair facing down=ill health
4. EYES: Broad+equal+dark pupil+red corners=ruler; small pupil=long life; squint=poverty+liar; lotus-petal=riches
5. NOSE: Elevated+broad at bottom+small nostrils=ruler; big=wealth; depression in middle=deceitful; parrot-beak tip=strong+intelligent
6. LIPS & MOUTH: Small+red=riches+beauty; broad=tenacity; black mouth=deceitful
7. CHIN: Single chin=riches; clockwise whorl=good food; divided/thick=cunning
8. EARS: Long+hanging+soft=ideal; small inner opening=riches; clockwise whorl inside=ruler
9. COMPLEXION: Fair/wheat=good; very dark=inauspicious

For each feature observed, state:
1. What you observe (objective description)
2. The Samudrika Shastra interpretation from the classical text
3. Overall life prediction summary

Format your response as a structured JSON object."""

ANALYSIS_SCHEMA = {
    "gender": "male or female",
    "face_shape": {"observation": "", "shastra_meaning": ""},
    "forehead": {"observation": "", "shastra_meaning": ""},
    "eyebrows": {"observation": "", "shastra_meaning": ""},
    "eyes": {"observation": "", "shastra_meaning": ""},
    "nose": {"observation": "", "shastra_meaning": ""},
    "lips_mouth": {"observation": "", "shastra_meaning": ""},
    "chin": {"observation": "", "shastra_meaning": ""},
    "ears": {"observation": "", "shastra_meaning": ""},
    "complexion": {"observation": "", "shastra_meaning": ""},
    "overall_reading": "",
    "key_predictions": []
}

def convert_to_jpeg(img_path):
    """Convert avif/webp to jpeg using sips (macOS built-in)."""
    p = Path(img_path)
    if p.suffix.lower() in ['.jpg', '.jpeg']:
        return str(p)
    out = f"/tmp/{p.stem}.jpg"
    if not os.path.exists(out):
        subprocess.run(['sips', '-s', 'format', 'jpeg', str(p), '--out', out],
                       capture_output=True)
    return out

def image_to_b64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def analyze_face(img_path, gender):
    # Convert if needed
    jpeg_path = convert_to_jpeg(img_path)
    img_b64   = image_to_b64(jpeg_path)

    prompt = f"""Analyze this {gender}'s face according to Samudrika Shastra.
Remember: examine the {'LEFT' if gender=='female' else 'RIGHT'} side for {gender}s.

Return ONLY a valid JSON object with this exact structure:
{json.dumps(ANALYSIS_SCHEMA, indent=2)}

Fill every field with specific observations from the image and their Samudrika Shastra interpretation."""

    payload = {
        "model": MODEL,
        "messages": [{
            "role": "system", "content": SYSTEM_PROMPT
        }, {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": prompt}
            ]
        }],
        "max_tokens": 2000,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        resp = json.loads(r.read())
    content = resp["choices"][0]["message"]["content"].strip()

    # Extract JSON from response
    start = content.find('{')
    end   = content.rfind('}') + 1
    if start == -1 or end == 0:
        return None
    return json.loads(content[start:end])

# Load already done
done = set()
if OUT.exists():
    for line in OUT.read_text().splitlines():
        try:
            done.add(json.loads(line)["file"])
        except:
            pass

print(f"Already done: {len(done)}")

# Process all images
for gender in ["male", "female"]:
    imgs = sorted(glob.glob(str(FACES_DIR / gender / "*.*")))
    print(f"\n=== {gender.upper()} ({len(imgs)} images) ===")

    for img_path in imgs:
        fname = os.path.basename(img_path)
        if fname in done:
            print(f"  skip: {fname}")
            continue

        print(f"  {fname}...", end=" ", flush=True)
        try:
            analysis = analyze_face(img_path, gender)
            if not analysis:
                print("✗ no JSON")
                continue

            record = {
                "file": fname,
                "gender": gender,
                "image_path": img_path,
                "analysis": analysis,
                # For fine-tuning: the text that the model should output
                "target_text": json.dumps(analysis, ensure_ascii=False)
            }
            with open(OUT, 'a') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            done.add(fname)
            print(f"✓  {analysis.get('overall_reading','')[:80]}")
        except Exception as e:
            print(f"✗ {e}")

print(f"\n✅ Dataset: {len(done)} images → {OUT}")
print("Next: format as HuggingFace dataset and upload for Gemma 4 fine-tuning")
