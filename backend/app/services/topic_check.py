"""Deterministic topic checks: normalization, question/title validation,
broadness scoring and duplicate lookup.

No LLM calls: every rule here is explainable and reproducible.
"""

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.enums import TopicSubmissionStatus
from app.repositories import topics as topics_repo
from app.schemas.projects import CheckMessage
from app.schemas.topic import BroadnessOut, DuplicateMatchOut, DuplicateOut, TopicCheckOut

NORMALIZE_STRIP_RE = re.compile(r"[^\w\s]", re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")

QUESTION_WORDS = (
    "как",
    "что",
    "почему",
    "зачем",
    "какой",
    "какая",
    "какие",
    "каким",
    "каких",
    "сколько",
    "где",
    "когда",
    "кто",
    "чем",
    "отчего",
    "насколько",
    "можно ли",
    "является ли",
    "влияет ли",
    "действительно ли",
    "стоит ли",
)

GENERIC_AUDIENCE_RE = re.compile(
    r"^(как|почему|зачем)\s+(влияет|влияют|воздействует|воздействуют|важно|полезно|вредно)"
    r"\s+.+\s+на\s+(людей|человека|общество|мир|жизнь|молодежь)$"
)
VAGUE_AUDIENCE_RE = re.compile(
    r"\b(на людей|на человека|на общество|на мир|на жизнь|в современном мире|для человечества)\b"
)

# Multiple words are stems: we match them inside the normalized title.
NARROWING_SIGNALS: dict[str, tuple[str, ...]] = {
    "place": (
        "москв",
        "петербург",
        "район",
        "город",
        "школ",
        "регион",
        "село",
        "деревн",
        "росси",
        "сибир",
        "урал",
        "крым",
        "област",
        "двор",
        "парк",
    ),
    "period": ("век", "период", "год", "лет", "месяц", "недел", "сезон"),
    "group": (
        "школьник",
        "ученик",
        "подростк",
        "студент",
        "класс",
        "дет",
        "младш",
        "старш",
        "взросл",
        "пенсионер",
        "семь",
        "девочк",
        "мальчик",
        "педагог",
        "учител",
    ),
    "technology": (
        "python",
        "arduino",
        "приложен",
        "сайт",
        "бот",
        "нейросет",
        "3d",
        "пластик",
        "дерев",
        "металл",
        "ткан",
        "бумаг",
        "датчик",
        "микроконтроллер",
        "робот",
        "смартфон",
    ),
    "comparison": (
        "сравнен",
        "по сравнению",
        "vs",
        "лучше",
        "эффективн",
        "дешевле",
        "быстрее",
    ),
    "method": (
        "метод",
        "эксперимент",
        "опрос",
        "анкет",
        "измерен",
        "наблюден",
        "моделирован",
        "анализ данных",
        "лаборатор",
        "тест",
    ),
}

NARROWING_HINTS = {
    "place": "Добавьте место: город, район или школу.",
    "period": "Укажите период или год.",
    "group": "Назовите группу людей: школьники, подростки, семья.",
    "technology": "Уточните технологию или материал.",
    "comparison": "Добавьте сравнение: с чем именно сравниваете.",
    "method": "Укажите метод: опрос, эксперимент, измерение.",
}

# Order used when we offer only the most useful missing narrowings.
SUGGESTION_ORDER = ("place", "period", "group", "method", "comparison", "technology")

BREADTH_WORDS = (
    "влияни",
    "роль",
    "польз",
    "вред",
    "проблем",
    "изучени",
    "исследовани",
    "анализ",
    "развити",
    "особенност",
)

GENERAL_WORDS = {
    "влияние",
    "роль",
    "польза",
    "вред",
    "проблема",
    "изучение",
    "исследование",
    "анализ",
    "развитие",
    "особенности",
    "экология",
    "искусство",
    "космос",
    "здоровье",
    "спорт",
    "техника",
    "история",
    "общество",
    "язык",
    "экономика",
    "медицина",
    "дизайн",
    "проект",
    "технологии",
    "технология",
    "наука",
    "культура",
    "образование",
}

STOPWORDS = {
    "и",
    "в",
    "во",
    "на",
    "с",
    "со",
    "о",
    "об",
    "для",
    "по",
    "из",
    "к",
    "у",
    "от",
    "до",
    "за",
    "не",
    "но",
    "а",
    "или",
    "как",
    "что",
    "это",
}


def normalize_title(title: str) -> str:
    """Lowercase, replace ``ё``, strip punctuation and collapse spaces."""
    value = title.strip().lower().replace("ё", "е")
    value = NORMALIZE_STRIP_RE.sub(" ", value)
    return WHITESPACE_RE.sub(" ", value).strip()


def word_count(text: str) -> int:
    normalized = normalize_title(text)
    return len(normalized.split()) if normalized else 0


def _stem_matches_word(word: str, stem: str) -> bool:
    """A stem matches only the beginning of a whole word (``школ`` -> ``школьной``).

    Plain substring search gave false positives: ``человек`` matched ``век``
    (period) and ``погода`` matched ``год``.
    """
    if " " in stem:
        return False
    return word.startswith(stem)


def _stem_matches_text(words: list[str], stem: str) -> bool:
    if " " in stem:
        return f" {stem} " in f" {' '.join(words)} "
    return any(_stem_matches_word(word, stem) for word in words)


def _contains_words(words: list[str], stems: tuple[str, ...]) -> bool:
    return any(_stem_matches_text(words, stem) for stem in stems)


def _first_word_for_stem(words: list[str], stem: str) -> str | None:
    """Return the actual word from the title that hit the stem."""
    if " " in stem:
        return stem if f" {stem} " in f" {' '.join(words)} " else None
    return next((word for word in words if _stem_matches_word(word, stem)), None)


def validate_title(title: str, *, interest_area_name: str | None = None) -> list[CheckMessage]:
    normalized = normalize_title(title)
    errors: list[CheckMessage] = []

    if not normalized:
        return [CheckMessage(field="topic_title", message="Введите тему проекта.")]

    words = normalized.split()
    if len(words) < 4:
        errors.append(
            CheckMessage(
                field="topic_title",
                message="Тема слишком короткая: нужно от 4 до 20 слов.",
            )
        )
    elif len(words) > 20:
        errors.append(
            CheckMessage(
                field="topic_title",
                message="Тема слишком длинная: сократите до 20 слов.",
            )
        )

    if interest_area_name and normalized == normalize_title(interest_area_name):
        errors.append(
            CheckMessage(
                field="topic_title",
                message="Тема не может совпадать с названием сферы интересов.",
            )
        )

    meaningful = [word for word in words if word not in STOPWORDS]
    if meaningful and all(word in GENERAL_WORDS for word in meaningful):
        errors.append(
            CheckMessage(
                field="topic_title",
                message="Тема состоит только из общих слов. Добавьте объект и уточнение.",
            )
        )

    return errors


def validate_research_question(
    question: str | None,
) -> tuple[list[CheckMessage], list[CheckMessage]]:
    errors: list[CheckMessage] = []
    warnings: list[CheckMessage] = []

    if question is None or not question.strip():
        errors.append(
            CheckMessage(
                field="research_question",
                message="Сформулируйте исследовательский вопрос.",
            )
        )
        return errors, warnings

    stripped = question.strip()
    normalized = normalize_title(stripped)
    words = normalized.split() if normalized else []

    if not stripped.endswith("?"):
        errors.append(
            CheckMessage(
                field="research_question",
                message="Исследовательский вопрос должен заканчиваться знаком «?».",
            )
        )

    if len(words) < 6:
        errors.append(
            CheckMessage(
                field="research_question",
                message="Вопрос слишком короткий: нужно от 6 до 40 слов.",
            )
        )
    elif len(words) > 40:
        errors.append(
            CheckMessage(
                field="research_question",
                message="Вопрос слишком длинный: сократите до 40 слов.",
            )
        )

    has_question_word = any(
        re.search(rf"(^|\s){re.escape(word)}(\s|$)", normalized) for word in QUESTION_WORDS
    )
    if not has_question_word:
        errors.append(
            CheckMessage(
                field="research_question",
                message="Начните вопрос со слова «как», «почему», «что» или «влияет ли».",
            )
        )

    if GENERIC_AUDIENCE_RE.match(normalized.rstrip("?")):
        errors.append(
            CheckMessage(
                field="research_question",
                message="В вопросе нет конкретного объекта: уточните, на кого или что влияет.",
            )
        )
    elif VAGUE_AUDIENCE_RE.search(normalized):
        warnings.append(
            CheckMessage(
                field="research_question",
                message="Формулировка «на людей» или «в мире» слишком общая — сузьте аудиторию.",
            )
        )

    return errors, warnings


def analyze_broadness(
    title: str,
    *,
    research_question: str | None = None,
    ok_threshold: int | None = None,
    warn_threshold: int | None = None,
) -> BroadnessOut:
    settings = get_settings()
    ok_at = settings.TOPIC_BROADNESS_OK if ok_threshold is None else ok_threshold
    warn_at = settings.TOPIC_BROADNESS_WARN if warn_threshold is None else warn_threshold

    normalized = normalize_title(title)
    words = normalized.split()
    reasons: list[str] = []
    suggestions: list[str] = []

    hard_block = False
    if len(words) < 4:
        hard_block = True
        reasons.append("В теме меньше четырёх слов — непонятно, что именно исследуется.")

    meaningful = [word for word in words if word not in STOPWORDS]
    if meaningful and all(word in GENERAL_WORDS for word in meaningful):
        hard_block = True
        reasons.append("Тема состоит только из общих слов без объекта и уточнения.")

    if research_question and GENERIC_AUDIENCE_RE.match(
        normalize_title(research_question).rstrip("?")
    ):
        hard_block = True
        reasons.append("Исследовательский вопрос не называет конкретный объект.")

    found_signals = [
        name for name, stems in NARROWING_SIGNALS.items() if _contains_words(words, stems)
    ]
    matched_breadth = [
        (stem, word)
        for stem in BREADTH_WORDS
        if (word := _first_word_for_stem(words, stem)) is not None
    ]

    score = 50 + 10 * len(found_signals) - 15 * len(matched_breadth)
    score = max(0, min(100, score))
    if hard_block:
        score = 0

    for _stem, word in matched_breadth:
        reasons.append(
            f"Слишком общее слово «{word}» — уточните объект и что именно вы исследуете."
        )

    if not found_signals:
        reasons.append(
            "Нет сужения: не указаны место, период, группа, технология, сравнение или метод."
        )
        suggestions.extend(
            (
                "Добавьте место: город, район или школу.",
                "Укажите период или год.",
                "Назовите группу людей.",
            )
        )
    else:
        missing = [NARROWING_HINTS[name] for name in SUGGESTION_ORDER if name not in found_signals]
        suggestions.extend(missing[:2])

    if hard_block:
        level = "block"
    elif score >= ok_at:
        level = "ok"
    elif score >= warn_at:
        level = "warn"
    else:
        level = "block"

    return BroadnessOut(
        score=score,
        level=level,
        reasons=reasons,
        suggestions=suggestions,
    )


async def check_duplicate(
    session: AsyncSession,
    *,
    school_id: uuid.UUID,
    academic_year_id: uuid.UUID,
    normalized_title: str,
    exclude_submission_id: uuid.UUID | None = None,
) -> DuplicateOut:
    settings = get_settings()
    rows = await topics_repo.find_duplicate_titles(
        session,
        school_id=school_id,
        academic_year_id=academic_year_id,
        normalized_title=normalized_title,
        threshold=min(settings.TOPIC_DUPLICATE_WARN, settings.TOPIC_DUPLICATE_BLOCK),
        exclude_submission_id=exclude_submission_id,
    )

    matches = [
        DuplicateMatchOut(source=source, id=row_id, title=title, score=round(score, 3))
        for source, row_id, title, score in rows
    ]
    exact = any(normalize_title(match.title) == normalized_title for match in matches)
    best_score = max((match.score for match in matches), default=0.0)

    if exact or best_score >= settings.TOPIC_DUPLICATE_BLOCK:
        level = "block"
    elif best_score >= settings.TOPIC_DUPLICATE_WARN:
        level = "warn"
    else:
        level = "ok"

    return DuplicateOut(
        level=level,
        exact=exact,
        best_score=round(best_score, 3),
        matches=matches,
    )


async def run_checks(
    session: AsyncSession,
    *,
    school_id: uuid.UUID,
    academic_year_id: uuid.UUID,
    title: str,
    research_question: str | None,
    interest_area_name: str | None = None,
    exclude_submission_id: uuid.UUID | None = None,
) -> TopicCheckOut:
    normalized_title = normalize_title(title)
    errors = validate_title(title, interest_area_name=interest_area_name)
    question_errors, question_warnings = validate_research_question(research_question)
    errors.extend(question_errors)

    broadness = analyze_broadness(title, research_question=research_question)
    duplicate = await check_duplicate(
        session,
        school_id=school_id,
        academic_year_id=academic_year_id,
        normalized_title=normalized_title,
        exclude_submission_id=exclude_submission_id,
    )

    can_submit = (
        not errors
        and duplicate.level != "block"
        and broadness.level != "block"
        and research_question is not None
    )

    return TopicCheckOut(
        title=title.strip(),
        normalized_title=normalized_title,
        errors=errors,
        warnings=question_warnings,
        duplicate=duplicate,
        broadness=broadness,
        can_submit=can_submit,
    )


def duplicate_level_for_stored_score(score: float | None, *, exact: bool = False) -> str:
    settings = get_settings()
    if exact:
        return "block"
    if score is None:
        return "ok"
    if score >= settings.TOPIC_DUPLICATE_BLOCK:
        return "block"
    if score >= settings.TOPIC_DUPLICATE_WARN:
        return "warn"
    return "ok"


def broadness_level_for_stored_score(score: int | None) -> str:
    settings = get_settings()
    if score is None:
        return "ok"
    if score >= settings.TOPIC_BROADNESS_OK:
        return "ok"
    if score >= settings.TOPIC_BROADNESS_WARN:
        return "warn"
    return "block"


def submission_is_pending(status: TopicSubmissionStatus) -> bool:
    return status in (TopicSubmissionStatus.SUBMITTED, TopicSubmissionStatus.APPROVED)
