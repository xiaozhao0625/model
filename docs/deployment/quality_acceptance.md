# 质量验收说明

## 验收对象

质量 Gate 判断截图是否可以进入有效数据集。输入可以来自 Web、PC App、PC Game、Android Worker，也可以来自 dry-run mock 数据。

## 拒绝原因

- `black_screen`
- `white_screen`
- `blurry`
- `low_resolution`
- `browser_chrome_visible`
- `os_taskbar_visible`
- `title_bar_visible`
- `wrong_window`
- `near_duplicate`
- `dangerous_page`
- `detector_unavailable`

## 输出文件

- `quality_report.json`
- `clean_dataset_manifest.jsonl`
- `rejected_quality_manifest.jsonl`
- `ocr_report.json`

输出写入独立质量目录，不删除、不修改原始 run 产物。
