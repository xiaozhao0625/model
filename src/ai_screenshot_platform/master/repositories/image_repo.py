from __future__ import annotations

import sqlite3

from ai_screenshot_platform.master.models.entities import ImageRecord


class ImageRepo:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, record: ImageRecord) -> ImageRecord:
        self.connection.execute(
            "INSERT INTO images (image_id, run_id, bucket, path, hash) VALUES (?, ?, ?, ?, ?)",
            (record.image_id, record.run_id, record.bucket, record.path, record.hash),
        )
        self.connection.commit()
        return record

    def list_by_run(self, run_id: str) -> list[ImageRecord]:
        rows = self.connection.execute(
            "SELECT image_id, run_id, bucket, path, hash FROM images WHERE run_id = ? ORDER BY image_id",
            (run_id,),
        ).fetchall()
        return [
            ImageRecord(
                image_id=str(row["image_id"]),
                run_id=str(row["run_id"]),
                bucket=str(row["bucket"]),
                path=str(row["path"]),
                hash=str(row["hash"]),
            )
            for row in rows
        ]
