# V3 Model Directory

This directory is intentionally ignored by Git and is reserved for local OCR/UI model weights.

V3 does not download or enable models automatically. Use the scripts under `scripts/v3/model/` only after checking model source, size, license, and hash requirements.

Expected local layout:

```text
models/
  showui/
  paddleocr/
  fasttext/
  omniparser/
```

Do not commit model weights, caches, or local manifests.
