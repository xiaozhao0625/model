from enum import StrEnum


class Bucket(StrEnum):
    FIXED = "fixed"
    LOW = "low"
    HIGH = "high"
    REJECTED = "rejected"
