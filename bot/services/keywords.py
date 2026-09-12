from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DigestMessage:
    """A minimal, SQLAlchemy-independent view of a chat message, for easy testing."""

    display_name: str
    text: str


@dataclass(frozen=True)
class Category:
    key: str
    title: str
    emoji: str
    stems: tuple[str, ...]


# Word stems are matched as case-insensitive substrings, which is a cheap way to cover
# Russian inflections (e.g. "поня" catches "понял", "поняла", "понимаю", "понимание").
CATEGORIES: tuple[Category, ...] = (
    Category(
        "insight",
        "Инсайт дня",
        "\U0001f4a1",
        ("инсайт", "осозна", "поня", "открыл", "заметил", "заметила", "разгляде"),
    ),
    Category(
        "breakthrough",
        "Прорыв дня",
        "\U0001f680",
        ("прорыв", "получилось", "получил", "смогл", "справил", "преодол", "победил"),
    ),
    Category(
        "gratitude",
        "Благодарность дня",
        "\U0001f64f",
        ("благодар", "спасибо", "признател"),
    ),
    Category(
        "challenge",
        "Вызов дня",
        "\U0001f4aa",
        ("сложно", "трудно", "тяжело", "непросто", "тревог", "страх"),
    ),
    Category(
        "pride",
        "Гордость дня",
        "⭐",
        ("горд", "довольна собой", "довольный собой", "рада за себя", "рад за себя"),
    ),
)

CATEGORIES_BY_KEY: dict[str, Category] = {category.key: category for category in CATEGORIES}


def _score(text: str, stems: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(lowered.count(stem) for stem in stems)


def categorize(messages: list[DigestMessage], *, min_length: int = 15) -> dict[str, DigestMessage]:
    """Pick one representative message per rubric category.

    Among messages matching the same category, prefer the one with more keyword
    hits, then the longer one — a reflective paragraph makes a better digest quote
    than a bare "спасибо всем".
    """
    result: dict[str, DigestMessage] = {}
    for category in CATEGORIES:
        best: DigestMessage | None = None
        best_score = 0
        for message in messages:
            text = message.text.strip()
            if len(text) < min_length:
                continue
            score = _score(text, category.stems)
            if score == 0:
                continue
            if best is None or score > best_score or (score == best_score and len(text) > len(best.text.strip())):
                best = message
                best_score = score
        if best is not None:
            result[category.key] = best
    return result
