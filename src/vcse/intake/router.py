from __future__ import annotations

from vcse.adapters.base import SourceAdapter
from vcse.adapters.csv_adapter import CSVAdapter
from vcse.adapters.html_table_adapter import HTMLTableAdapter
from vcse.adapters.json_adapter import JSONAdapter
from vcse.adapters.jsonl_adapter import JSONLAdapter
from vcse.profiles.base import SourceProfile
from vcse.profiles.generic_records import GenericRecordsProfile
from vcse.profiles.historical_events import HistoricalEventsProfile


class IntakeRouter:
    def __init__(self) -> None:
        self._adapters: tuple[SourceAdapter, ...] = (
            JSONAdapter(),
            JSONLAdapter(),
            CSVAdapter(),
            HTMLTableAdapter(),
        )
        self._profiles: tuple[SourceProfile, ...] = (
            HistoricalEventsProfile(),
            GenericRecordsProfile(),
        )

    def select_adapter(self, detected_format: str) -> SourceAdapter | None:
        for adapter in self._adapters:
            if detected_format in adapter.supported_formats:
                return adapter
        return None

    def select_profile(self, rows: tuple[dict, ...], requested_profile: str | None = None) -> SourceProfile:
        if requested_profile:
            for profile in self._profiles:
                if profile.profile_id == requested_profile:
                    return profile
            raise ValueError(f"UNKNOWN_PROFILE: {requested_profile}")

        for profile in self._profiles:
            if profile.profile_id == "historical_events" and profile.can_handle(rows):
                return profile
        return GenericRecordsProfile()
