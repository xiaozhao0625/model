from __future__ import annotations

from ai_screenshot_platform.workers.android.adb_runtime import AdbRuntimeResult


class SnapshotManager:
    def list_snapshots(self):
        return AdbRuntimeResult("unsupported", "snapshot_disabled")

    def restore_snapshot(self, snapshot_id: str):
        return AdbRuntimeResult("unsupported", "snapshot_disabled")

    def create_snapshot(self, snapshot_id: str):
        return AdbRuntimeResult("unsupported", "snapshot_disabled")
