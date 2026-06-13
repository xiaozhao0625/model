from __future__ import annotations

import json
from typing import Any


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)


def _list_json(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def _loads(value: Any, default: Any):
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(str(value))


class ProductionReadinessRepo:
    def __init__(self, connection) -> None:
        self.connection = connection

    def upsert_quality_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            "app_id": payload.get("app_id", ""),
            "run_id": payload["run_id"],
            "total_images": int(payload.get("total_images", 0)),
            "accepted_count": int(payload.get("accepted_count", 0)),
            "rejected_count": int(payload.get("rejected_count", 0)),
            "quality_pass_rate": float(payload.get("quality_pass_rate", 0)),
            "black_screen_count": int(payload.get("black_screen_count", 0)),
            "white_screen_count": int(payload.get("white_screen_count", 0)),
            "blurry_count": int(payload.get("blurry_count", 0)),
            "wrong_window_count": int(payload.get("wrong_window_count", 0)),
            "browser_chrome_count": int(payload.get("browser_chrome_count", 0)),
            "taskbar_count": int(payload.get("taskbar_count", 0)),
            "near_duplicate_count": int(payload.get("near_duplicate_count", 0)),
            "ocr_risk_hit_count": int(payload.get("ocr_risk_hit_count", 0)),
            "reject_reason_distribution": payload.get("reject_reason_distribution", {}),
            "bucket_distribution": payload.get("bucket_distribution", {}),
            "source_path": payload.get("source_path"),
        }
        if not record["quality_pass_rate"] and record["total_images"]:
            record["quality_pass_rate"] = record["accepted_count"] / max(record["total_images"], 1)
        self.connection.execute(
            """
            INSERT INTO quality_reports (
                app_id, run_id, total_images, accepted_count, rejected_count, quality_pass_rate,
                black_screen_count, white_screen_count, blurry_count, wrong_window_count,
                browser_chrome_count, taskbar_count, near_duplicate_count, ocr_risk_hit_count,
                reject_reason_distribution, bucket_distribution, source_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                app_id = excluded.app_id,
                total_images = excluded.total_images,
                accepted_count = excluded.accepted_count,
                rejected_count = excluded.rejected_count,
                quality_pass_rate = excluded.quality_pass_rate,
                black_screen_count = excluded.black_screen_count,
                white_screen_count = excluded.white_screen_count,
                blurry_count = excluded.blurry_count,
                wrong_window_count = excluded.wrong_window_count,
                browser_chrome_count = excluded.browser_chrome_count,
                taskbar_count = excluded.taskbar_count,
                near_duplicate_count = excluded.near_duplicate_count,
                ocr_risk_hit_count = excluded.ocr_risk_hit_count,
                reject_reason_distribution = excluded.reject_reason_distribution,
                bucket_distribution = excluded.bucket_distribution,
                source_path = excluded.source_path
            """,
            (
                record["app_id"],
                record["run_id"],
                record["total_images"],
                record["accepted_count"],
                record["rejected_count"],
                record["quality_pass_rate"],
                record["black_screen_count"],
                record["white_screen_count"],
                record["blurry_count"],
                record["wrong_window_count"],
                record["browser_chrome_count"],
                record["taskbar_count"],
                record["near_duplicate_count"],
                record["ocr_risk_hit_count"],
                _json(record["reject_reason_distribution"]),
                _json(record["bucket_distribution"]),
                record["source_path"],
            ),
        )
        self.connection.commit()
        return self.get_quality_report(record["run_id"]) or record

    def list_quality_reports(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM quality_reports ORDER BY created_at DESC").fetchall()
        return [self._quality_from_row(row) for row in rows]

    def get_quality_report(self, run_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM quality_reports WHERE run_id = ?", (run_id,)).fetchone()
        return self._quality_from_row(row) if row is not None else None

    def upsert_ocr_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            "app_id": payload.get("app_id", ""),
            "run_id": payload["run_id"],
            "provider": payload.get("provider", "disabled"),
            "available": bool(payload.get("available", False)),
            "status": payload.get("status", "unknown"),
            "risk_hits": payload.get("risk_hits", []),
            "scene_hints": payload.get("scene_hints", []),
            "unavailable_reason": payload.get("unavailable_reason"),
            "paddleocr_status": payload.get("paddleocr_optional_status", payload.get("paddleocr_status", "unknown")),
            "easyocr_status": payload.get("easyocr_optional_status", payload.get("easyocr_status", "unknown")),
            "source_path": payload.get("source_path"),
        }
        self.connection.execute(
            """
            INSERT INTO ocr_reports (
                app_id, run_id, provider, available, status, risk_hits, scene_hints,
                unavailable_reason, paddleocr_status, easyocr_status, source_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                app_id = excluded.app_id,
                provider = excluded.provider,
                available = excluded.available,
                status = excluded.status,
                risk_hits = excluded.risk_hits,
                scene_hints = excluded.scene_hints,
                unavailable_reason = excluded.unavailable_reason,
                paddleocr_status = excluded.paddleocr_status,
                easyocr_status = excluded.easyocr_status,
                source_path = excluded.source_path
            """,
            (
                record["app_id"],
                record["run_id"],
                record["provider"],
                int(record["available"]),
                record["status"],
                _list_json(record["risk_hits"]),
                _list_json(record["scene_hints"]),
                record["unavailable_reason"],
                record["paddleocr_status"],
                record["easyocr_status"],
                record["source_path"],
            ),
        )
        self.connection.commit()
        return self.get_ocr_report(record["run_id"]) or record

    def list_ocr_reports(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM ocr_reports ORDER BY created_at DESC").fetchall()
        return [self._ocr_from_row(row) for row in rows]

    def get_ocr_report(self, run_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM ocr_reports WHERE run_id = ?", (run_id,)).fetchone()
        return self._ocr_from_row(row) if row is not None else None

    def latest_ocr_status(self) -> dict[str, Any]:
        row = self.connection.execute("SELECT * FROM ocr_reports ORDER BY created_at DESC LIMIT 1").fetchone()
        if row is None:
            return {
                "provider": "disabled",
                "available": False,
                "status": "unavailable",
                "risk_hits": [],
                "scene_hints": [],
                "unavailable_reason": "no_ocr_report",
                "paddleocr_optional_status": "unknown",
                "easyocr_optional_status": "unknown",
            }
        return self._ocr_from_row(row)

    def ingest_tool_health(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.connection.execute(
            """
            INSERT INTO tool_health_snapshots (
                machine_name, worker_id, worker_type, status, tools, master_ready, worker_ready, source_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("machine_name"),
                payload.get("worker_id"),
                payload.get("worker_type"),
                payload.get("status", "unknown"),
                _json(payload.get("tools", {})),
                _json(payload.get("master_ready", {})),
                _json(payload.get("worker_ready", {})),
                payload.get("source_path"),
            ),
        )
        android = payload.get("android")
        if android:
            self.connection.execute(
                """
                INSERT INTO android_runtime_snapshots (
                    worker_id, profile_id, adb_available, devices, selected_device, screencap_status,
                    ui_dump_status, ocr_fallback_status, input_status, skipped_reason, source_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("worker_id"),
                    android.get("profile_id"),
                    int(bool(android.get("adb_available", False))),
                    _list_json(android.get("devices", [])),
                    android.get("selected_device"),
                    android.get("screencap_status", "unknown"),
                    android.get("ui_dump_status", "unknown"),
                    android.get("ocr_fallback_status", "unknown"),
                    android.get("input_status", "unknown"),
                    android.get("skipped_reason"),
                    payload.get("source_path"),
                ),
            )
        self.connection.commit()
        return self.tool_health()

    def tool_health(self) -> dict[str, Any]:
        tool = self.connection.execute("SELECT * FROM tool_health_snapshots ORDER BY created_at DESC LIMIT 1").fetchone()
        android = self.android_runtime()
        return {
            "machine_ready": str(tool["status"]) if tool is not None else "unknown",
            "master_ready": self._ready_status(tool, "master_ready"),
            "worker_ready": self._ready_status(tool, "worker_ready"),
            "tools": _loads(tool["tools"], {}) if tool is not None else {},
            "android": android,
        }

    def android_runtime(self) -> dict[str, Any]:
        row = self.connection.execute("SELECT * FROM android_runtime_snapshots ORDER BY created_at DESC LIMIT 1").fetchone()
        if row is None:
            return {
                "adb_available": False,
                "devices": [],
                "selected_device": None,
                "screencap_status": "unknown",
                "ui_dump_status": "unknown",
                "ocr_fallback_status": "unknown",
                "input_status": "unknown",
            }
        return {
            "adb_available": bool(row["adb_available"]),
            "devices": _loads(row["devices"], []),
            "selected_device": row["selected_device"],
            "screencap_status": row["screencap_status"],
            "ui_dump_status": row["ui_dump_status"],
            "ocr_fallback_status": row["ocr_fallback_status"],
            "input_status": row["input_status"],
        }

    def upsert_behavior_candidate(self, payload: dict[str, Any]) -> dict[str, Any]:
        enabled = bool(payload.get("enabled", payload.get("status") == "approved"))
        status = payload.get("status", "pending_review")
        if status != "approved":
            enabled = False
        self.connection.execute(
            """
            INSERT INTO behavior_candidates (
                candidate_pack_id, base_pack_id, game_type, version, status, enabled, issues,
                recommendations, rollback_target, created_from_run_id, pack_content, source_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(candidate_pack_id) DO UPDATE SET
                base_pack_id = excluded.base_pack_id,
                game_type = excluded.game_type,
                version = excluded.version,
                status = excluded.status,
                enabled = excluded.enabled,
                issues = excluded.issues,
                recommendations = excluded.recommendations,
                rollback_target = excluded.rollback_target,
                created_from_run_id = excluded.created_from_run_id,
                pack_content = excluded.pack_content,
                source_path = excluded.source_path,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                payload["candidate_pack_id"],
                payload.get("base_pack_id", ""),
                payload.get("game_type", ""),
                payload.get("version", ""),
                status,
                int(enabled),
                _list_json(payload.get("issues", [])),
                _list_json(payload.get("recommendations", [])),
                payload.get("rollback_target", payload.get("base_pack_id", "")),
                payload.get("created_from_run_id", ""),
                _json(payload.get("pack_content", {})),
                payload.get("source_path"),
            ),
        )
        self.connection.commit()
        return self.get_behavior_candidate(payload["candidate_pack_id"]) or payload

    def list_behavior_candidates(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM behavior_candidates ORDER BY created_at DESC").fetchall()
        return [self._candidate_from_row(row) for row in rows]

    def get_behavior_candidate(self, candidate_pack_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM behavior_candidates WHERE candidate_pack_id = ?", (candidate_pack_id,)).fetchone()
        return self._candidate_from_row(row) if row is not None else None

    def review_candidate(self, candidate_pack_id: str, decision: str, reviewer: str | None, reason: str | None) -> dict[str, Any]:
        candidate = self.get_behavior_candidate(candidate_pack_id)
        if candidate is None:
            raise KeyError(f"candidate not found: {candidate_pack_id}")
        if candidate["status"] != "pending_review" and decision in {"approved", "rejected"}:
            raise ValueError("only pending_review candidates can be approved or rejected")
        enabled = decision == "approved"
        self.connection.execute(
            "UPDATE behavior_candidates SET status = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE candidate_pack_id = ?",
            (decision, int(enabled), candidate_pack_id),
        )
        self.connection.execute(
            """
            INSERT INTO behavior_candidate_reviews (
                candidate_pack_id, decision, reviewer, reason, enabled_after_review
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (candidate_pack_id, decision, reviewer, reason, int(enabled)),
        )
        self.connection.commit()
        return self.get_behavior_candidate(candidate_pack_id) or candidate

    def rollback_candidate(self, candidate_pack_id: str, reviewer: str | None, reason: str | None) -> dict[str, Any]:
        candidate = self.get_behavior_candidate(candidate_pack_id)
        if candidate is None:
            raise KeyError(f"candidate not found: {candidate_pack_id}")
        self.connection.execute(
            "UPDATE behavior_candidates SET status = ?, enabled = 0, updated_at = CURRENT_TIMESTAMP WHERE candidate_pack_id = ?",
            ("pending_review", candidate_pack_id),
        )
        self.connection.execute(
            """
            INSERT INTO behavior_candidate_rollbacks (
                candidate_pack_id, rollback_target, reason, reviewer
            ) VALUES (?, ?, ?, ?)
            """,
            (candidate_pack_id, candidate["rollback_target"], reason, reviewer),
        )
        self.connection.commit()
        return self.get_behavior_candidate(candidate_pack_id) or candidate

    def ingest_diagnostic(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.connection.execute(
            """
            INSERT INTO deployment_diagnostics (
                machine_name, role, status, report_type, payload, source_path
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("machine_name"),
                payload.get("role"),
                payload.get("status", "unknown"),
                payload.get("report_type", "diagnostic"),
                _json(payload.get("payload", {})),
                payload.get("source_path"),
            ),
        )
        self.connection.commit()
        return self.list_diagnostics()[0]

    def list_diagnostics(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM deployment_diagnostics ORDER BY created_at DESC").fetchall()
        return [self._diagnostic_from_row(row) for row in rows]

    def _quality_from_row(self, row) -> dict[str, Any]:
        return {
            "app_id": row["app_id"],
            "run_id": row["run_id"],
            "total_images": int(row["total_images"]),
            "accepted_count": int(row["accepted_count"]),
            "rejected_count": int(row["rejected_count"]),
            "quality_pass_rate": float(row["quality_pass_rate"]),
            "black_screen_count": int(row["black_screen_count"]),
            "white_screen_count": int(row["white_screen_count"]),
            "blurry_count": int(row["blurry_count"]),
            "wrong_window_count": int(row["wrong_window_count"]),
            "browser_chrome_count": int(row["browser_chrome_count"]),
            "taskbar_count": int(row["taskbar_count"]),
            "near_duplicate_count": int(row["near_duplicate_count"]),
            "ocr_risk_hit_count": int(row["ocr_risk_hit_count"]),
            "reject_reason_distribution": _loads(row["reject_reason_distribution"], {}),
            "bucket_distribution": _loads(row["bucket_distribution"], {}),
            "source_path": row["source_path"],
        }

    def _ocr_from_row(self, row) -> dict[str, Any]:
        return {
            "app_id": row["app_id"],
            "run_id": row["run_id"],
            "provider": row["provider"],
            "available": bool(row["available"]),
            "status": row["status"],
            "risk_hits": _loads(row["risk_hits"], []),
            "scene_hints": _loads(row["scene_hints"], []),
            "unavailable_reason": row["unavailable_reason"],
            "paddleocr_optional_status": row["paddleocr_status"],
            "easyocr_optional_status": row["easyocr_status"],
            "source_path": row["source_path"],
        }

    def _candidate_from_row(self, row) -> dict[str, Any]:
        return {
            "candidate_pack_id": row["candidate_pack_id"],
            "base_pack_id": row["base_pack_id"],
            "game_type": row["game_type"],
            "version": row["version"],
            "status": row["status"],
            "enabled": bool(row["enabled"]),
            "issues": _loads(row["issues"], []),
            "recommendations": _loads(row["recommendations"], []),
            "rollback_target": row["rollback_target"],
            "created_from_run_id": row["created_from_run_id"],
            "pack_content": _loads(row["pack_content"], {}),
            "source_path": row["source_path"],
        }

    def _diagnostic_from_row(self, row) -> dict[str, Any]:
        return {
            "machine_name": row["machine_name"],
            "role": row["role"],
            "status": row["status"],
            "report_type": row["report_type"],
            "payload": _loads(row["payload"], {}),
            "source_path": row["source_path"],
        }

    def _ready_status(self, row, column: str) -> str:
        if row is None:
            return "unknown"
        value = _loads(row[column], {})
        if isinstance(value, dict):
            return str(value.get("status", row["status"]))
        return str(row["status"])
