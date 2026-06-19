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


def run_folder_watch_loop(
    runtime: V3Runtime,
    run_id: str,
    folder: str | Path,
    seen: set[str] | None = None,
    duration_seconds: float = 600,
    poll_interval_seconds: float = 1,
    max_iterations: int | None = None,
    max_retries: int = 2,
) -> dict[str, object]:
    seen = seen if seen is not None else set()
    attempts: dict[str, int] = {}
    failures: list[dict[str, str]] = []
    timings: list[float] = []
    started = time.monotonic()
    iterations = 0
    discovered = 0
    processed = 0
    failed = 0
    quarantined = 0
    stopped_reason = "duration"

    while True:
        if max_iterations is not None and iterations >= max_iterations:
            stopped_reason = "max_iterations"
            break
        if duration_seconds >= 0 and time.monotonic() - started >= duration_seconds:
            stopped_reason = "duration"
            break

        iterations += 1
        images = list_new_images(folder, seen)
        discovered += len(images)
        for image in images:
            image_key = str(image.resolve())
            attempt = attempts.get(image_key, 0) + 1
            attempts[image_key] = attempt
            started_ingest = time.perf_counter()
            try:
                runtime.ingest_image(run_id, str(image))
                processed += 1
                seen.add(image_key)
                attempts.pop(image_key, None)
            except Exception as exc:
                failed += 1
                failures.append({"image": str(image), "error": str(exc), "attempt": str(attempt)})
                if attempt > max_retries:
                    seen.add(image_key)
                    quarantined += 1
            finally:
                timings.append((time.perf_counter() - started_ingest) * 1000)

        stats = _loop_stats(
            folder=folder,
            iterations=iterations,
            discovered=discovered,
            processed=processed,
            failed=failed,
            failures=failures,
            timings=timings,
            seen=seen,
            quarantined=quarantined,
            started=started,
            stopped_reason="running",
        )
        runtime.store.write_artifact(run_id, "meta/folder_watch_summary.json", stats)

        if max_iterations is not None and iterations >= max_iterations:
            stopped_reason = "max_iterations"
            break
        if poll_interval_seconds > 0:
            time.sleep(poll_interval_seconds)

    stats = _loop_stats(
        folder=folder,
        iterations=iterations,
        discovered=discovered,
        processed=processed,
        failed=failed,
        failures=failures,
        timings=timings,
        seen=seen,
        quarantined=quarantined,
        started=started,
        stopped_reason=stopped_reason,
    )
    runtime.store.write_artifact(run_id, "meta/folder_watch_summary.json", stats)
    return stats


def _loop_stats(
    *,
    folder: str | Path,
    iterations: int,
    discovered: int,
    processed: int,
    failed: int,
    failures: list[dict[str, str]],
    timings: list[float],
    seen: set[str],
    quarantined: int,
    started: float,
    stopped_reason: str,
) -> dict[str, object]:
    return {
        "folder": str(Path(folder)),
        "iterations": iterations,
        "discovered": discovered,
        "processed": processed,
        "failed": failed,
        "failures": failures,
        "avg_ingest_ms": round(sum(timings) / len(timings), 3) if timings else 0,
        "seen": len(seen),
        "quarantined": quarantined,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "stopped_reason": stopped_reason,
    }
