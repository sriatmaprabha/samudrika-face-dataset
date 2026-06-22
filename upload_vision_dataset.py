"""
Uploads dataset_augmented.jsonl (612 vision pairs) to HuggingFace.
Each row: image (PIL) + instruction + text (answer) + gender
"""
import json, subprocess, warnings
from pathlib import Path
from PIL import Image
from datasets import Dataset, DatasetDict
import warnings
warnings.filterwarnings('ignore')

import os
HF_TOKEN = os.environ.get("HF_TOKEN", "")  # set: export HF_TOKEN=hf_xxxx
REPO     = "kailasa-ngpt/samudrika-face-dataset"
HERE     = Path(__file__).parent
JSONL    = HERE / "dataset_augmented.jsonl"

def to_pil(img_path):
    p = Path(img_path)
    if not p.exists():
        # Remap to local faces/ folder
        parts = Path(img_path).parts
        gender = "male" if "male" in img_path else "female"
        fname  = Path(img_path).name
        p = HERE / "faces" / gender / fname
    if p.suffix.lower() in ('.avif', '.webp'):
        tmp = Path(f"/tmp/{p.stem}_up.jpg")
        if not tmp.exists():
            subprocess.run(['sips','-s','format','jpeg','-Z','1024',
                            str(p),'--out',str(tmp)], capture_output=True)
        p = tmp
    return Image.open(p).convert("RGB")

pairs = [json.loads(l) for l in JSONL.read_text().splitlines() if l.strip()]
print(f"Loaded {len(pairs)} pairs")

images, instructions, texts, genders, pair_types = [], [], [], [], []

for i, p in enumerate(pairs):
    print(f"  [{i+1}/{len(pairs)}] {p['file']} ({p['pair_type']})...", end=" ", flush=True)
    try:
        pil = to_pil(p["image_path"])
        images.append(pil)
        instructions.append(p["conversation"][0]["content"])
        texts.append(p["conversation"][1]["content"])
        genders.append(p["gender"])
        pair_types.append(p["pair_type"])
        print("✓")
    except Exception as e:
        print(f"✗ {e}")

from datasets import Image as HFImage
ds = Dataset.from_dict({
    "image":       images,
    "instruction": instructions,
    "text":        texts,
    "gender":      genders,
    "pair_type":   pair_types,
}).cast_column("image", HFImage())

# Split: 80% train, 10% val, 10% test (on image level)
unique_files = list(dict.fromkeys(p["file"] for p in pairs))
n = len(unique_files)
train_files = set(unique_files[:int(n*0.8)])
val_files   = set(unique_files[int(n*0.8):int(n*0.9)])

indices = list(range(len(ds)))
train_idx = [i for i,p in enumerate(pairs) if p["file"] in train_files]
val_idx   = [i for i,p in enumerate(pairs) if p["file"] in val_files]
test_idx  = [i for i,p in enumerate(pairs) if p["file"] not in train_files and p["file"] not in val_files]

dd = DatasetDict({
    "train":      ds.select(train_idx),
    "validation": ds.select(val_idx),
    "test":       ds.select(test_idx),
})
print(f"\nSplit: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")
print(f"Uploading to {REPO}...")
dd.push_to_hub(REPO, token=HF_TOKEN)
print(f"✅ Vision dataset uploaded: https://huggingface.co/datasets/{REPO}")
