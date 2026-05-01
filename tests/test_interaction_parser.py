"""Tests for pattern parser."""

from vcse.interaction.parser import PatternParser
from vcse.interaction.frames import FrameStatus, ClaimFrame, GoalFrame, ConstraintFrame


def test_parse_claim_x_is_a_y():
    parser = PatternParser()
    result = parser.parse("Socrates is a man")
    assert result.status == FrameStatus.PARSED
    assert len(result.frames) >= 1
    assert isinstance(result.frames[0], ClaimFrame)
    assert result.frames[0].subject == "socrates"
    assert result.frames[0].relation == "is_a"
    assert result.frames[0].object == "man"


def test_parse_all_x_are_y():
    parser = PatternParser()
    result = parser.parse("All men are mortal")
    assert result.status == FrameStatus.PARSED
    assert len(result.frames) >= 1


def test_parse_question_is_x_y():
    parser = PatternParser()
    result = parser.parse("Is Socrates a man?")
    assert result.status == FrameStatus.PARSED
    assert len(result.frames) >= 1


def test_parse_multiple_statements():
    parser = PatternParser()
    result = parser.parse("All men are mortal. Socrates is a man.")
    assert result.status == FrameStatus.PARSED
    assert len(result.frames) >= 2


def test_parse_arithmetic_equals():
    parser = PatternParser()
    result = parser.parse("x equals 5")
    assert result.status == FrameStatus.PARSED
    assert len(result.frames) >= 1


def test_parse_arithmetic_greater_than():
    parser = PatternParser()
    result = parser.parse("x is greater than 0")
    assert result.status == FrameStatus.PARSED


def test_parse_unsupported():
    parser = PatternParser()
    result = parser.parse("xyzzy plugh")
    # Any output is acceptable
    assert result.status in [FrameStatus.PARSED, FrameStatus.UNSUPPORTED, FrameStatus.PARTIAL]


def test_parse_empty():
    parser = PatternParser()
    result = parser.parse("")
    assert result.status == FrameStatus.FAILED


def test_parse_can_socrates_die_as_goal_without_modal_in_subject():
    parser = PatternParser()
    result = parser.parse("can socrates is_a mortal")
    assert result.status == FrameStatus.PARSED
    assert len(result.frames) >= 1
    assert isinstance(result.frames[0], GoalFrame)
    assert result.frames[0].subject == "socrates"
    assert result.frames[0].relation == "is_a"
    assert result.frames[0].object == "mortal"


def test_parse_rejects_none_input_cleanly():
    parser = PatternParser()
    result = parser.parse(None)  # type: ignore[arg-type]
    assert result.status == FrameStatus.FAILED
    assert "string" in result.errors[0].lower()


def test_parse_rejects_non_string_input_cleanly():
    parser = PatternParser()
    result = parser.parse(123)  # type: ignore[arg-type]
    assert result.status == FrameStatus.FAILED
    assert "string" in result.errors[0].lower()


def test_parse_rejects_oversized_payload():
    parser = PatternParser()
    result = parser.parse("a" * 1_000_001)
    assert result.status == FrameStatus.FAILED
    assert "max length" in result.errors[0].lower()


def test_parse_rejects_excessive_statement_count():
    parser = PatternParser()
    text = "x.\n" * 10_001
    result = parser.parse(text)
    assert result.status == FrameStatus.FAILED
    assert "statement count" in result.errors[0].lower()
