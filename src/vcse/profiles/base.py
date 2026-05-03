from __future__ import annotations

from abc import ABC, abstractmethod

from vcse.cmcf.model import CMCFRecord
from vcse.intake.source import SourceRef


class SourceProfile(ABC):
    profile_id: str

    @abstractmethod
    def can_handle(self, rows: tuple[dict, ...]) -> bool:
        ...

    @abstractmethod
    def to_cmcf(self, rows: tuple[dict, ...], source: SourceRef) -> tuple[CMCFRecord, ...]:
        ...
