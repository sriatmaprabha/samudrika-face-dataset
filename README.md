# Samudrika Face Dataset

A face image dataset annotated with **Samudrika Shastra** — the ancient Indian science of physiognomy (face and body reading).

## Dataset

- **50 face images**: 25 male + 25 female
- **Mixed ethnicities** and lighting conditions
- **Formats**: jpg, webp, avif (convert with `sips` on macOS before use)

```
images/
  male/    — 25 images (male1–male25)
  female/  — 25 images (female1–female25)
```

## Annotation Schema

Each image is annotated with structured Samudrika Shastra analysis:

| Field | Description |
|---|---|
| `face_shape` | Type (oval/round/long/square/broad) + Shastra meaning |
| `forehead` | Lines visible (0–5), width, life-span prediction |
| `eyebrows` | Shape, color, ruler/wealth indicators |
| `eyes` | Shape, pupil color, prosperity markers |
| `nose` | Type, nostril size, leadership/wealth signs |
| `lips_mouth` | Size, color, character indicators |
| `chin` | Shape, fortune indicators |
| `ears` | Size, lobe type, ruling class markers |
| `complexion` | Tone, auspiciousness |
| `overall_reading` | 3–4 sentence life prediction summary |
| `key_predictions` | Top 3 Shastra predictions |

**Key rule** (from classical text):
- For **women** → examine the **LEFT** side of the face
- For **men** → examine the **RIGHT** side of the face

## Intended Use

Fine-tuning **Gemma 4 31B Vision** (via [Unsloth](https://github.com/unslothai/unsloth)) to perform Samudrika Shastra face readings from images.

## Scripts

- `scripts/generate_dataset.py` — annotates all images using Nvidia Vision API, outputs `dataset.jsonl`
- `scripts/preprocess.py` — image audit, format conversion, metadata CSV

## Source

Annotations derived from classical Samudrika Shastra texts including:
- Samudrika Laksanam
- Saral Samudrik Shastra (Face Reading)
- Hast Samudrika Shastra
- Samudrika Shastra (various editions)

## License

Research and educational use. Images are for dataset development purposes.
