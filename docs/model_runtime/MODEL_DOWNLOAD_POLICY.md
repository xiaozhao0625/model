# Model Download Policy

P13.5.0 is plan-only.

Before any download:

1. Record the official source.
2. Record version or revision.
3. Estimate disk and VRAM requirements.
4. Decide the target role.
5. Record expected SHA256 or source-provided checksums.
6. Confirm the provider is allowed for that role.
7. Keep `enabled=false` until health checks pass.

Forbidden in P13.5.0:

- downloading large models
- installing PaddleOCR or EasyOCR
- running online inference
- enabling worker-side heavy models during capture
- committing model or OCR files
