"""Greek personal-name recognizer (dictionary + morphology + context).

No model download required. The recognizer combines three cheap but effective
signals that work well on inflected Greek and OCR'd text:

1. **First-name dictionary** - a curated list of common Greek given names,
   matched accent/case-insensitively so inflected forms are largely covered.
2. **Surname morphology** - Greek surnames overwhelmingly end in a small set of
   suffixes (``-όπουλος``, ``-άκης``, ``-ίδης``, ``-ος``, ``-ου`` ...). A
   capitalized word with a strong suffix is likely a surname.
3. **Context** - a preceding title/honorific (``κ.``, ``Δρ.``, ``Καθηγητής``)
   strongly indicates a following name; an institutional stopword list
   suppresses look-alike administrative vocabulary (``Ελληνική Δημοκρατία``).

Consecutive capitalized words are merged into a single PERSON span
(``Γιώργος Παπαδόπουλος`` -> one entity). For stronger detection of unusual
names/organizations, an optional spaCy/Presidio backend can be enabled
separately (see :mod:`glossanon.recognizers.ml`).
"""

from __future__ import annotations

import re
from typing import List, Optional, Set

from ..normalization.greek import (
    GREEK_LETTERS,
    fold,
    is_greek_upper,
    normalize_sigma,
)
from ..resources import load_lines
from ..types import Entity, EntityType
from .base import Recognizer

_WORD_RE = re.compile("[" + re.escape(GREEK_LETTERS) + "]+")

# Minimum length for a suffix to count as a *strong* surname signal on its own.
_STRONG_SUFFIX_MIN = 3


class NameRecognizer(Recognizer):
    name = "names"
    supported_entities = (EntityType.PERSON,)

    def __init__(
        self,
        first_names: Optional[Set[str]] = None,
        surname_suffixes: Optional[List[str]] = None,
        titles: Optional[Set[str]] = None,
        stopwords: Optional[Set[str]] = None,
    ) -> None:
        self.first_names = first_names or {
            normalize_sigma(fold(n)) for n in load_lines("greek_first_names.txt")
        }
        suffixes = surname_suffixes or load_lines("greek_surname_suffixes.txt")
        # Sort longest-first so the most specific suffix matches first.
        self.suffixes = sorted({fold(s) for s in suffixes}, key=len, reverse=True)
        self.strong_suffixes = [s for s in self.suffixes if len(s) >= _STRONG_SUFFIX_MIN]
        self.titles = titles or {fold(t) for t in load_lines("greek_titles.txt")}
        self.stopwords = stopwords or {fold(w) for w in load_lines("greek_name_stopwords.txt")}

    # -- token helpers ---------------------------------------------------

    @staticmethod
    def _is_capitalized(token: str) -> bool:
        return bool(token) and is_greek_upper(token[0])

    def _is_stopword(self, token: str) -> bool:
        f = fold(token)
        # Titles signal a name is nearby; they are never part of the span.
        return f in self.stopwords or f in self.titles

    def _is_first_name(self, token: str) -> bool:
        f = normalize_sigma(fold(token))
        if f in self.first_names:
            return True
        # The genitive drops the final sigma ("Ιωάννης" -> "Ιωάννη").
        return (f + "σ") in self.first_names

    def _has_strong_suffix(self, token: str) -> bool:
        f = fold(token)
        return any(
            f.endswith(suf) and len(f) >= len(suf) + 2 for suf in self.strong_suffixes
        )

    def _has_name_evidence(self, token: str) -> bool:
        """Does this token, on its own, look like part of a person name?

        Used to trim leading words that merely happen to sit next to a name.
        A lone capital letter counts: it is an initial ("Δ." in "Δ. Νικολάου").
        """
        return (
            len(token) == 1
            or self._is_first_name(token)
            or self._has_strong_suffix(token)
        )

    # -- main entry ------------------------------------------------------

    def analyze(self, text: str, normalized: str) -> List[Entity]:
        tokens = [(m.group(0), m.start(), m.end()) for m in _WORD_RE.finditer(normalized)]
        entities: List[Entity] = []

        i = 0
        n = len(tokens)
        while i < n:
            tok, start, end = tokens[i]

            if not self._is_capitalized(tok) or self._is_stopword(tok):
                i += 1
                continue

            # Grow a run of capitalized, non-stopword tokens to catch "First Last".
            run = [(tok, start, end)]
            j = i + 1
            while j < n:
                ntok, nstart, nend = tokens[j]
                gap = normalized[run[-1][2]:nstart]
                gap_clean = gap.strip(" ")
                # Join across spaces, or a dot after an initial ("Γ. Παπαδόπουλος").
                gap_ok = gap != "" and len(gap) <= 3 and (
                    gap_clean == ""
                    or (gap_clean == "." and len(run[-1][0]) == 1)
                )
                if (
                    self._is_capitalized(ntok)
                    and not self._is_stopword(ntok)
                    and gap_ok
                ):
                    run.append((ntok, nstart, nend))
                    j += 1
                else:
                    break

            entity = self._score_run(run, tokens, i, normalized, text)
            if entity is not None:
                entities.append(entity)
            i = j if j > i else i + 1

        return entities

    def _title_before(self, tokens, run_index: int, normalized: str) -> bool:
        """Does a title token immediately precede the run?"""
        if run_index == 0:
            return False
        prev_tok, _, prev_end = tokens[run_index - 1]
        run_start = tokens[run_index][1]
        between = normalized[prev_end:run_start]
        # allow ". " or " " or "." between a title abbreviation and the name
        if between.strip(" .") != "":
            return False
        return fold(prev_tok) in self.titles

    def _score_run(self, run, tokens, run_index: int, normalized: str, text: str) -> Optional[Entity]:
        words = [w for (w, _, _) in run]
        has_first = any(self._is_first_name(w) for w in words)
        has_suffix = any(self._has_strong_suffix(w) for w in words)
        # A lone capital beside a full word ("Γ. Παπαδόπουλος") signals a person.
        has_initial = any(len(w) == 1 for w in words) and any(len(w) >= 2 for w in words)
        title = self._title_before(tokens, run_index, normalized)
        length = len(run)

        score: Optional[float] = None

        if title:
            # A title before any capitalized word is a strong cue.
            score = 0.85 + (0.1 if (has_first or has_suffix) else 0.0)
        elif length >= 2 and (has_first or has_suffix):
            score = 0.6
            if has_first:
                score += 0.2
            if has_suffix:
                score += 0.15
        elif length >= 2 and has_initial:
            # e.g. "Δ. Α. Νικολάου" - initials plus a capitalized word.
            score = 0.6
        elif length == 1 and has_first:
            score = 0.55
        elif length == 1 and has_suffix:
            score = 0.5

        if score is None:
            return None

        # Trim leading words with no name evidence: "Ακολουθεί Δ. Παπαδόπουλος".
        first_idx = 0
        for k, w in enumerate(words):
            if self._has_name_evidence(w):
                first_idx = k
                break

        start = run[first_idx][1]
        end = run[-1][2]
        return Entity(
            entity_type=EntityType.PERSON,
            start=start,
            end=end,
            text=text[start:end],
            score=min(score, 0.98),
            recognizer=self.name,
            metadata={
                "tokens": len(run),
                "first_name": has_first,
                "surname_suffix": has_suffix,
                "title": title,
            },
        )
