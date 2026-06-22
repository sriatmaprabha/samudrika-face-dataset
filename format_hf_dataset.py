"""
format_hf_dataset.py
Converts dataset.jsonl → HuggingFace dataset and uploads to Hub.

Output dataset columns (matching LaTeX OCR format exactly):
  image  — PIL Image object
  text   — Samudrika analysis JSON string (the target output)
  gender — "male" or "female" (metadata)

Usage:
  python3 format_hf_dataset.py --token hf_xxxx --repo uskfoundation/samudrika-face-dataset
"""
import json, subprocess, argparse
from pathlib import Path
from PIL import Image
import io

HERE = Path(__file__).parent
JSONL = HERE / "dataset.jsonl"

def convert_to_jpeg_pil(img_path: str) -> Image.Image:
    p = Path(img_path)
    suffix = p.suffix.lower()
    if suffix in ('.avif', '.webp'):
        # Convert via sips to a temp JPEG, then open with PIL
        tmp = Path(f"/tmp/{p.stem}_hf.jpg")
        if not tmp.exists():
            subprocess.run(
                ['sips', '-s', 'format', 'jpeg', '-Z', '1024', str(p), '--out', str(tmp)],
                capture_output=True
            )
        return Image.open(tmp).convert("RGB")
    else:
        return Image.open(img_path).convert("RGB")

def main(token, repo_id):
    from datasets import Dataset, Features, Image as HFImage, Value

    print(f"Loading {JSONL}...")
    records = [json.loads(l) for l in JSONL.read_text().splitlines() if l.strip()]
    print(f"  {len(records)} records")

    images, texts, genders = [], [], []

    for i, rec in enumerate(records):
        img_path = rec["image_path"]
        # Remap path if running on a different machine
        if not Path(img_path).exists():
            # Try relative to HERE
            fname  = rec["file"]
            gender = rec["gender"]
            img_path = str(HERE / "faces" / gender / fname)

        print(f"  [{i+1}/{len(records)}] {rec['file']}...", end=" ", flush=True)
        try:
            pil = convert_to_jpeg_pil(img_path)
            images.append(pil)
            texts.append(rec["target_text"])
            genders.append(rec["gender"])
            print(f"✓ {pil.size}")
        except Exception as e:
            print(f"✗ {e}")

    print(f"\nBuilding HuggingFace dataset ({len(images)} images)...")
    ds = Dataset.from_dict({
        "image":  images,
        "text":   texts,
        "gender": genders,
    }).cast_column("image", HFImage())

    print(f"Dataset: {ds}")
    print(f"Columns: {ds.column_names}")
    print(f"Sample text (first 200 chars): {ds[0]['text'][:200]}")

    # Train/val/test split — split on images (not augmented pairs)
    # 40 train / 6 val / 5 test  (approx 80/12/10)
    n = len(ds)
    n_test = max(5, int(n * 0.10))
    n_val  = max(5, int(n * 0.10))
    n_train = n - n_test - n_val

    ds_train = ds.select(range(n_train))
    ds_val   = ds.select(range(n_train, n_train + n_val))
    ds_test  = ds.select(range(n_train + n_val, n))

    print(f"\nSplit: train={len(ds_train)}, val={len(ds_val)}, test={len(ds_test)}")

    from datasets import DatasetDict
    dataset_dict = DatasetDict({
        "train":      ds_train,
        "validation": ds_val,
        "test":       ds_test,
    })

    print(f"\nUploading to HuggingFace Hub: {repo_id}...")
    dataset_dict.push_to_hub(repo_id, token=token)
    print(f"\n✅ Uploaded: https://huggingface.co/datasets/{repo_id}")
    print()
    print("In Colab, replace the dataset cell with:")
    print(f'  dataset = load_dataset("{repo_id}", split="train")')
    print()
    print("And replace the instruction with:")
    print('  instruction = "Analyze this person\'s face according to Samudrika Shastra.')
    print('  Examine the right side for males and left side for females."')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--token",  required=True, help="HuggingFace write token (hf_xxxx)")
    parser.add_argument("--repo",   default="uskfoundation/samudrika-face-dataset",
                        help="HuggingFace repo ID")
    args = parser.parse_args()
    main(args.token, args.repo)
