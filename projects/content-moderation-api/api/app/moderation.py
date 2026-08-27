"""Wordlist-based content moderation: detect profanity/explicit terms in text.

Uses the LDNOOBW English word list (CC BY 4.0) - see data/NOTICE.md for
attribution. 403 terms and phrases, unmodified from the source.

Honest about scope: this is pattern/wordlist matching, not a machine-learning
toxicity classifier. It catches known terms (and common leetspeak
obfuscation of them); it does not understand context, sarcasm, or reclaimed
language, and it will not catch novel insults that aren't on the list. A
fast, cheap first-pass filter - not a substitute for a full moderation
pipeline on high-stakes content. Said plainly in the product docs, not just
here.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

_WORDLIST_PATH = Path(__file__).parent / "data" / "en_wordlist.txt"
_MAX_TEXT_LENGTH = 5000  # ~403 compiled patterns run against the input twice (plain + leetspeak pass); cap input size so that stays cheap.

_LEET_MAP = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)
_REPEATED_CHAR_RE = re.compile(r"(.)\1{2,}")  # 3+ repeats of the same char, e.g. "shiiiit"


class ModerationError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class Match:
    term: str
    # -1/-1 means the term was only found via the leetspeak-normalized pass;
    # its position doesn't map cleanly back onto the original text, so it
    # contributes to flagged/match_count but not to redaction.
    start: int
    end: int


@dataclass
class ModerationResult:
    flagged: bool
    matches: list[Match]
    match_count: int
    redacted_text: str

    def to_dict(self) -> dict:
        return {
            "flagged": self.flagged,
            "matches": [asdict(m) for m in self.matches],
            "match_count": self.match_count,
            "redacted_text": self.redacted_text,
        }


@lru_cache(maxsize=1)
def _load_terms() -> tuple[str, ...]:
    terms = {
        line.strip().lower()
        for line in _WORDLIST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    return tuple(sorted(terms, key=len, reverse=True))


@lru_cache(maxsize=1)
def _compiled_patterns() -> tuple[tuple[str, re.Pattern], ...]:
    # Word-boundary matching on both single words and multi-word phrases.
    # This is what keeps "assassin" from getting flagged for containing
    # "ass": \b requires a word/non-word transition, and "assassin" has no
    # such transition after position 3.
    return tuple(
        (term, re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)) for term in _load_terms()
    )


def _leetspeak_variant(text: str) -> str:
    collapsed = _REPEATED_CHAR_RE.sub(r"\1", text)
    return collapsed.translate(_LEET_MAP)


def moderate(text: str) -> ModerationResult:
    if not isinstance(text, str) or not text.strip():
        raise ModerationError("text must be a non-empty string", 422)
    if len(text) > _MAX_TEXT_LENGTH:
        raise ModerationError(f"text exceeds the {_MAX_TEXT_LENGTH}-character limit", 422)

    normalized = unicodedata.normalize("NFKC", text)

    matches: list[Match] = []
    seen_terms: set[str] = set()
    for term, pattern in _compiled_patterns():
        for m in pattern.finditer(normalized):
            matches.append(Match(term=term, start=m.start(), end=m.end()))
            seen_terms.add(term)

    leet_text = _leetspeak_variant(normalized)
    for term, pattern in _compiled_patterns():
        if term in seen_terms:
            continue
        if pattern.search(leet_text):
            matches.append(Match(term=term, start=-1, end=-1))
            seen_terms.add(term)

    matches.sort(key=lambda m: m.start if m.start >= 0 else 10**9)

    redacted = normalized
    for m in sorted((m for m in matches if m.start >= 0), key=lambda m: m.start, reverse=True):
        redacted = redacted[: m.start] + "*" * (m.end - m.start) + redacted[m.end :]

    return ModerationResult(
        flagged=bool(matches),
        matches=matches,
        match_count=len(matches),
        redacted_text=redacted,
    )
