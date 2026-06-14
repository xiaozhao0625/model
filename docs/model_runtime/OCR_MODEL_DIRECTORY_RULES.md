# OCR / Model Directory Rules

Runtime files must stay outside the Git repository.

## Allowed Runtime Roots

- M0:
  - `E:\work\models`
  - `E:\work\ocr`
  - `E:\work\model_runtime`
- W1/W2/W3:
  - `D:\work\models`
  - `D:\work\ocr`
  - `D:\work\model_runtime`

## Repository Policy

Do not commit:

- model weights
- OCR weights
- virtual environments
- model caches
- installer archives
- generated local manifests with absolute paths or hash state
- logs and deploy reports

Only example manifests, scripts, and documentation should be committed.
