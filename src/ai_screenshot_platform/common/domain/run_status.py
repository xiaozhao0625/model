from enum import StrEnum


class RunStatus(StrEnum):
    CREATED = "created"
    CAPTURE_RUNNING = "capture_running"
    CAPTURE_COMPLETED = "capture_completed"
    UPLOAD_PENDING = "upload_pending"
    UPLOADED_CONFIRMED = "uploaded_confirmed"
    LOCAL_DELETED = "local_deleted"
    COMPLETED = "completed"
