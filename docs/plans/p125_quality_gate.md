# P12.5：OCR 与采集质量 Gate

## 目标

P12.5 补齐生产采集前的截图质量验收能力，判断截图是否可以进入有效数据集，并用 OCR 作为风险识别、场景提示和 Android fallback 的公共能力。

## 范围

- OCR 合同、disabled/mock provider、PaddleOCR/EasyOCR optional adapter 边界。
- OCR 风险词表、scene hints、Quality Gate 集成。
- 黑屏、白屏、低分辨率、模糊、browser chrome、任务栏、标题栏、near-duplicate 轻量检测。
- `quality_report.json`、`clean_dataset_manifest.jsonl`、`rejected_quality_manifest.jsonl`、`ocr_report.json`。

## 边界

- 默认 OCR 为 disabled/mock。
- 真实 OCR optional，不进入默认依赖。
- 不训练模型，不下载模型，不要求 GPU。
- 不修改原始 run 产物。
- Web content-only 必须证明未采集浏览器地址栏、标签栏或系统任务栏。
