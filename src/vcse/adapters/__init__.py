"""Source adapters for compiler inputs."""

from vcse.adapters.base import ExtractedRow, SourceAdapter
from vcse.adapters.registry import ADAPTERS, get_adapter

__all__ = ["SourceAdapter", "ExtractedRow", "ADAPTERS", "get_adapter"]
