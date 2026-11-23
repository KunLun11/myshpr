"""Deterministic topic checks: normalization, validation and broadness."""

import pytest

from app.services import topic_check
from app.services.topic_check import (
    analyze_broadness,
    normalize_title,
    validate_research_question,
    validate_title,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Влияние   ИНТЕРНЕТА  ", "влияние интернета"),
        ("Ёлка, «ёж»!", "елка еж"),
        ("Интернет-вещей", "интернет вещей"),
        ("Python: 3D-печать", "python 3d печать"),
        ("Тема — с тире…", "тема с тире"),
        ("ÉCOLE", "école"),
    ],
)
def test_normalize_title(raw: str, expected: str) -> None:
    assert normalize_title(raw) == expected


def test_normalize_title_is_deterministic() -> None:
    assert normalize_title("  Влияние  ШУМА ") == normalize_title("влияние шума")


def test_title_rejects_general_only() -> None:
    errors = validate_title("Экология")
    assert errors
    assert any("общих слов" in error.message for error in errors)


def test_title_rejects_short_and_long() -> None:
    assert validate_title("Влияние")
    long_title = " ".join(["слово"] * 21)
    assert validate_title(long_title)


def test_title_rejects_area_name() -> None:
    errors = validate_title("Экология", interest_area_name="Экология")
    assert any("сферы интересов" in error.message for error in errors)


def test_question_requires_question_mark() -> None:
    errors, _ = validate_research_question("Шум влияет на сон школьников")
    assert any("?" in error.message for error in errors)


def test_question_rejects_too_short() -> None:
    errors, _ = validate_research_question("Почему?")
    assert errors


def test_question_accepts_construction_with_li() -> None:
    errors, warnings = validate_research_question("Влияет ли шум на сон школьников?")
    assert not errors
    assert warnings == []


def test_question_rejects_generic_audience() -> None:
    errors, _ = validate_research_question("Как влияет интернет на людей?")
    assert any("конкретного объекта" in error.message for error in errors)


def test_question_warns_about_vague_audience() -> None:
    _, warnings = validate_research_question(
        "Как шум в школьной столовой влияет на людей в современном мире?"
    )
    assert warnings


BROADNESS_CASES = [
    ("Экология", "block"),
    ("Влияние", "block"),
    ("Изучение космоса", "block"),
    ("Роль спорта", "block"),
    ("Влияние и роль развития", "block"),
    ("Роль искусства в жизни", "block"),
    ("Изучение проблемы загрязнения воды", "block"),
    ("Проблема мусора в мире", "block"),
    ("Влияние интернета на людей", "block"),
    ("Изучение загрязнения воды в реке Москве", "warn"),
    ("Влияние шума на здоровье школьников в Москве", "warn"),
    ("Влияние шума на сон школьников 9 класса в школе №5", "warn"),
    ("Анализ данных опроса о питании в школьной столовой", "warn"),
    ("Проблема пластиковых отходов в парке у школы", "warn"),
    ("Роль музыки в жизни подростков 10 класса", "warn"),
    ("Особенности сна учеников младших классов", "warn"),
    ("Исследование качества воздуха в школьном дворе методом датчиков", "warn"),
    ("Анализ успеваемости учеников 9 класса по математике за год", "warn"),
    ("Вред фастфуда для здоровья подростков в Москве", "warn"),
    ("Польза комнатных растений для воздуха в классе", "warn"),
    ("Развитие робототехники в школе: сравнение кружков", "warn"),
    ("Влияние нейросетей на обучение студентов", "warn"),
    ("Влияние цвета стен на настроение учеников в школе", "warn"),
    ("Анализ цен на школьные обеды в столовой за месяц", "warn"),
    ("Изучение микроклимата в кабинете биологии с помощью датчиков Arduino", "warn"),
    ("Влияние громкой музыки на внимание школьников", "warn"),
    ("Влияние шума в школьной столовой на внимание учеников", "warn"),
    ("Влияние гаджетов на сон человека", "block"),
    ("Особенности питания подростков в школьной столовой", "warn"),
    ("Сравнение качества воды в реке Москве за 2024 год", "ok"),
    ("Разработка приложения на Python для расписания школьников", "ok"),
    ("Сравнение эффективности бумажных и пластиковых пакетов в магазинах района", "ok"),
    ("Сравнение веса рюкзаков учеников 5 и 9 классов", "ok"),
    ("Сравнение скорости разложения бумаги и пластика в почве", "ok"),
]


@pytest.mark.parametrize(("title", "expected_level"), BROADNESS_CASES)
def test_broadness_levels(title: str, expected_level: str) -> None:
    result = analyze_broadness(title)
    assert result.level == expected_level, (title, result)


def test_hard_block_sets_zero_score() -> None:
    assert analyze_broadness("Экология").score == 0


def test_broadness_reason_shows_full_word_not_stem() -> None:
    result = analyze_broadness("Влияние шума в школьной столовой на внимание учеников")
    assert any("«влияние»" in reason for reason in result.reasons)
    assert all("«влияни»" not in reason for reason in result.reasons)


def test_broadness_ignores_stems_inside_words() -> None:
    # «человека» содержит «век», «погода» — «год»: это не сужение по периоду.
    assert analyze_broadness("Влияние гаджетов на сон человека").level == "block"


def test_broadness_suggests_relevant_missing_narrowing() -> None:
    result = analyze_broadness("Влияние шума в школьной столовой на внимание учеников")
    assert result.level == "warn"
    assert "Укажите период или год." in result.suggestions
    assert all("технологию" not in suggestion for suggestion in result.suggestions)


def test_ok_title_has_suggestions_or_no_reasons() -> None:
    result = analyze_broadness("Сравнение качества воды в реке Москве за 2024 год")
    assert result.level == "ok"
    assert 70 <= result.score <= 100


def test_duplicate_level_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        topic_check,
        "get_settings",
        lambda: type("S", (), {"TOPIC_DUPLICATE_WARN": 0.55, "TOPIC_DUPLICATE_BLOCK": 0.85})(),
    )
    assert topic_check.duplicate_level_for_stored_score(0.9) == "block"
    assert topic_check.duplicate_level_for_stored_score(0.6) == "warn"
    assert topic_check.duplicate_level_for_stored_score(0.2) == "ok"
    assert topic_check.duplicate_level_for_stored_score(None) == "ok"
