from bot.services.keywords import DigestMessage, categorize


def test_categorize_picks_insight_and_gratitude():
    messages = [
        DigestMessage("@anna", "Сегодня я наконец поняла, почему откладываю практику на потом."),
        DigestMessage("@ivan", "Спасибо всем за поддержку в этом сложном упражнении сегодня!"),
        DigestMessage("@petr", "ок"),
    ]
    picks = categorize(messages)
    assert picks["insight"].display_name == "@anna"
    assert picks["gratitude"].display_name == "@ivan"
    assert "breakthrough" not in picks


def test_categorize_prefers_more_keyword_hits():
    messages = [
        DigestMessage("@a", "Было сложно, но я справился и получилось выполнить задание!"),
        DigestMessage("@b", "Немного сложно было сегодня с практикой в целом."),
    ]
    picks = categorize(messages)
    assert picks["breakthrough"].display_name == "@a"


def test_categorize_ignores_too_short_messages():
    messages = [DigestMessage("@a", "инсайт")]
    picks = categorize(messages, min_length=15)
    assert "insight" not in picks


def test_categorize_returns_empty_dict_for_no_matches():
    messages = [DigestMessage("@a", "Просто обычное сообщение без ключевых слов вообще.")]
    picks = categorize(messages)
    assert picks == {}
