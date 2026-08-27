import pytest

from app.moderation import ModerationError, moderate


def test_clean_text_is_not_flagged():
    result = moderate("What a nice sunny day today.")
    assert result.flagged is False
    assert result.matches == []
    assert result.redacted_text == "What a nice sunny day today."


def test_word_boundary_avoids_classic_false_positive():
    """'assassin' contains 'ass' as a substring but must not be flagged -
    the textbook profanity-filter false positive (the "Scunthorpe problem")."""
    result = moderate("The assassin classic passed by.")
    assert result.flagged is False


def test_flags_and_redacts_known_terms():
    result = moderate("You are a bitch and an asshole.")
    assert result.flagged is True
    assert {m.term for m in result.matches} == {"bitch", "asshole"}
    assert result.match_count == 2
    assert result.redacted_text == "You are a ***** and an *******."
    # Redaction preserves length.
    for m in result.matches:
        assert result.redacted_text[m.start : m.end] == "*" * (m.end - m.start)


def test_multi_word_phrase_is_matched():
    # The source list includes multi-word phrases, not just single words.
    result = moderate("Let's talk about big black cats.")
    assert result.flagged is True
    assert any(m.term == "big black" for m in result.matches)


def test_leetspeak_substitution_is_detected():
    result = moderate("He is such an @sshole honestly.")
    assert result.flagged is True
    assert any(m.term == "asshole" for m in result.matches)
    # Documented scope boundary: leetspeak matches aren't redacted, since
    # their positions don't map cleanly onto the original text.
    assert "@sshole" in result.redacted_text


def test_repeated_character_obfuscation_is_detected():
    result = moderate("go to hell you biiiitch")
    assert result.flagged is True
    assert any(m.term == "bitch" for m in result.matches)


def test_empty_text_is_rejected():
    with pytest.raises(ModerationError):
        moderate("")
    with pytest.raises(ModerationError):
        moderate("   ")


def test_oversized_text_is_rejected():
    with pytest.raises(ModerationError):
        moderate("a" * 5001)


def test_exactly_max_length_is_accepted():
    result = moderate("a" * 5000)
    assert result.flagged is False
