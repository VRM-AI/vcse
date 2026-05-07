"""Input validation for renderer guard models."""

from __future__ import annotations

import math
import unicodedata
from typing import Any, Mapping

from vcse.render.model import ALLOWED_RENDER_MODES, NON_FINITE_VALUE, INVALID_RENDER_MODE


def _check_nan_inf(value: Any, path: str, issues: list[str]) -> None:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        issues.append(f"{NON_FINITE_VALUE}: NaN/Inf at {path}")
    elif isinstance(value, dict):
        for k, v in value.items():
            _check_nan_inf(v, f"{path}.{k}", issues)
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _check_nan_inf(item, f"{path}[{i}]", issues)


def validate_render_mode(render_mode: str, issues: list[str]) -> None:
    if render_mode not in ALLOWED_RENDER_MODES:
        issues.append(f"{INVALID_RENDER_MODE}: unknown render mode: {render_mode!r}")


def normalize_rendered_text(text: str) -> str:
    """NFC normalization + whitespace collapse (NORMALIZED_CANONICAL mode)."""
    normalized = unicodedata.normalize("NFC", text)
    return " ".join(normalized.split())
