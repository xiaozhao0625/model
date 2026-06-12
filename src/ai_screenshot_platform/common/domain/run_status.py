from enum import StrEnum


class RunStatus(StrEnum):
    CREATED = "created"
    PENDING = "pending"
    LAUNCHING = "launching"
    WAITING_MANUAL = "waiting_manual"
    PROFILING = "profiling"
    RUNNING = "running"
    CAPTURE_RUNNING = "capture_running"
    CAPTURE_COMPLETED = "capture_completed"
    UPLOAD_PENDING = "upload_pending"
    UPLOADED_CONFIRMED = "uploaded_confirmed"
    LOCAL_DELETED = "local_deleted"
    COMPLETED = "completed"
    NEEDS_MANUAL_SEED = "needs_manual_seed"
    FAILED_LOW_YIELD = "failed_low_yield"
    SKIPPED_RISK = "skipped_risk"
