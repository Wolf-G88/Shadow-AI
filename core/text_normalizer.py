"""
Lightweight input normalization for Shadow AI.

Keeps runtime small while improving recognition, retrieval, and routing for
common shorthand, filler-prefixed, or slightly messy user phrasing.
"""

import re


_QUESTION_STARTERS = (
    "what", "when", "where", "who", "why", "how",
    "can", "could", "would", "will", "do", "does", "did",
    "is", "are", "am", "should"
)

_LEADING_FILLERS = (
    "hey", "yo", "ok", "okay", "alright", "listen",
    "shadow", "shadow ai", "shadow-ai"
)

_REPLACEMENTS = [
    (r"\bu\b", "you"),
    (r"\bur\b", "your"),
    (r"\bpls\b", "please"),
    (r"\bplz\b", "please"),
    (r"\bthx\b", "thanks"),
    (r"\bcuz\b", "because"),
    (r"\bcoz\b", "because"),
    (r"\bw\/\b", "with "),
    (r"\bw\/o\b", "without"),
]


def _strip_leading_fillers(text: str) -> str:
    words = text.split()
    if len(words) <= 2:
        return text

    lowered = text.lower()
    for filler in sorted(_LEADING_FILLERS, key=len, reverse=True):
        prefix = filler + " "
        if lowered.startswith(prefix):
            return text[len(prefix):].strip()
    return text


def _canonicalize_capability_query(text: str) -> str:
    lowered = text.lower().strip(" ?!.")
    lowered = re.sub(
        r"\b(please|thanks|thank you|real quick|if you can|when you get a sec)\b",
        "",
        lowered
    )
    lowered = re.sub(r"\s+", " ", lowered).strip()

    capability_patterns = [
        r"what all can shadow ai do( for me)?",
        r"what can shadow ai do( for me)?",
        r"what all can shadow do( for me)?",
        r"what can shadow do( for me)?",
        r"what all can you do",
        r"what can you do",
        r"what all you can do",
        r"what all u can do",
        r"what are your features",
        r"what are your capabilities",
        r"how can you help( me)?",
    ]

    for pattern in capability_patterns:
        if re.fullmatch(pattern, lowered):
            if "shadow" in lowered:
                return "what can shadow ai do for me?"
            return "what can you do?"

    return text


def _normalize_question_mark(text: str) -> str:
    if not text:
        return text
    if text[-1] in "?!.":
        return text

    first_word = text.split()[0].lower()
    if first_word in _QUESTION_STARTERS:
        return text + "?"
    return text


def normalize_user_text(text: str) -> str:
    """Normalize noisy user phrasing without heavy NLP dependencies."""
    if not text:
        return ""

    text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"([!?.,])\1+", r"\1", text)
    text = re.sub(r"\b4\b", "for", text)

    for pattern, replacement in _REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = _strip_leading_fillers(text)
    text = _canonicalize_capability_query(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = _normalize_question_mark(text)

    return text
