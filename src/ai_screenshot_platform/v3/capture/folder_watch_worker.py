from __future__ import annotations

import time
from pathlib import Path

from ai_screenshot_platform.v3.capture.folder_watch import list_new_images
from ai_screenshot_platform.v3.runtime import V3Runtime


def run_folder_watch_once(
    runtime: V3Runtime,
    run_id: str,
    folder: str | Path,
    seen: set[str] | None = None,
) -> dict[str, object]:
    seen = seen if seen is not None else set()
    images = list_new_images(folder, seen)
    timings: list[float] = []
    failures: list[dict[str, str]] = []
    processed = 0
    for image in images:
        image_key = str(image.resolve())
        started = time.perf_counter()
        try:
            runtime.ingest_image(run_id, str(image))
            processed += 1
        except Exception as exc:
            failures.append({"image": str(image), "error": str(exc)})
        finally:
            timings.append((time.perf_counter() - started) * 1000)
            seen.add(image_key)
    stats: dict[str, object] = {
        "folder": str(Path(folder)),
        "discovered": len(images),
        "processed": processed,
        "failed": len(failures),
        "failures": failures,
        "avg_ingest_ms": round(sum(timings) / len(timings), 3) if timings else 0,
        "seen": len(seen),
    }
    runtime.store.write_artifact(run_id, "meta/folder_watch_summary.json", stats)
    return stats
