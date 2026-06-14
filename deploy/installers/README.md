# P13 staged installers

This directory is for operator-provided installer packages used by the P13 staged installer backend.

Rules:

- Do not commit `.exe`, `.msi`, archives, or downloaded installers.
- Do not let scripts download installers from the internet.
- Add local installer files manually on M0.
- Copy `manifest.example.json` to `manifest.json` locally and fill in exact filenames and SHA256 values.
- Keep `manifest.json` local unless it contains no environment-specific installer names or hashes.
- P13.4.2.1 only permits staged installers for low-risk tools: `git`, `python`, `ffmpeg`, and `adb`.
- Drivers, browsers, OBS, Android Emulator, Redis, models, PaddleOCR, and EasyOCR are intentionally blocked.
