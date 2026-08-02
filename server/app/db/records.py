from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class RegionRecord:
    id: UUID
    code: str
    version: int
    source_checksum: str


@dataclass(frozen=True)
class AnalysisRecord:
    request_id: UUID
    status: str
    field_code: str
    started_at: datetime
    completed_at: datetime | None
