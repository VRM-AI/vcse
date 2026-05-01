"""Focused edge-case tests for math_solver hardening."""

import pytest

from vcse.agent.errors import ToolValidationError
from vcse.agent.tools import get_registry


def _run(expression: str):
    return get_registry().execute("math_solver", {"expression": expression})


def _assert_rejected(expression: str, contains: str | None = None) -> None:
    with pytest.raises(ToolValidationError) as exc_info:
        _run(expression)
    if contains:
        assert contains in str(exc_info.value)


def test_rejects_division_by_zero_float_one_over_zero():
    _assert_rejected("1.0/0.0", "math evaluation failed")


def test_rejects_division_by_zero_float_zero_over_zero():
    _assert_rejected("0.0/0.0", "math evaluation failed")


def test_rejects_nan_inf_output():
    _assert_rejected("1e309+1", "unsafe expression")


def test_rejects_zero_pow_negative_one():
    _assert_rejected("0**(-1)", "zero base with negative exponent")


def test_rejects_negative_base_fractional_exponent():
    _assert_rejected("(-1)**0.5", "negative base with fractional exponent")


def test_rejects_exponent_unaryop_bypass():
    _assert_rejected("2**(+13)", "exponent exceeds maximum absolute value")
    _assert_rejected("2**(-13)", "exponent exceeds maximum absolute value")


def test_rejects_subexpression_base_bypass():
    _assert_rejected("((500+500)/2)**12", "pow base must be a numeric constant")
    _assert_rejected("(999999+2)**12", "base exceeds maximum absolute value")


def test_rejects_oversized_exponent():
    _assert_rejected("2**100", "exponent exceeds maximum absolute value")


def test_still_evaluates_safe_expression():
    assert _run("2+2*3")["result"] == 8


def test_still_evaluates_safe_bounded_power():
    assert _run("2**10")["result"] == 1024


def test_json_serialization_safe_for_accepted_result():
    output = _run("1/2")
    assert output["result"] == 0.5


def test_invalid_ast_nodes_rejected():
    _assert_rejected("abs(1)", "unsafe expression")
