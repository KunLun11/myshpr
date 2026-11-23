"""Admin student listing and CSV import (stage 6)."""

import csv
import io
import secrets
import uuid

from pydantic import EmailStr, TypeAdapter
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models import SchoolClass, StudentProfile, User
from app.models.enums import UserRole
from app.repositories import classes as classes_repo
from app.repositories import students as students_repo
from app.schemas.classes import (
    AdminStudentOut,
    ImportedStudentOut,
    ImportSkipOut,
    StudentImportResult,
)

MAX_IMPORT_BYTES = 1024 * 1024  # 1 MB
MAX_IMPORT_ROWS = 500
REQUIRED_COLUMNS = ("full_name", "email")

_email_adapter = TypeAdapter(EmailStr)


def _check_class_access(user: User, school_class: SchoolClass) -> None:
    if user.role is UserRole.SUPER_ADMIN:
        return
    if user.school_id is None or school_class.school_id != user.school_id:
        raise ForbiddenError("Класс не из вашей школы", "CLASS_ACCESS_DENIED")


async def list_students(
    session: AsyncSession,
    user: User,
    *,
    class_id: uuid.UUID | None = None,
    school_id: uuid.UUID | None = None,
    query: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[AdminStudentOut]:
    if user.role is UserRole.SUPER_ADMIN:
        target_school = school_id
    else:
        if school_id is not None and school_id != user.school_id:
            raise ForbiddenError("Нет доступа к этой школе", "SCHOOL_ACCESS_DENIED")
        target_school = user.school_id

    if class_id is not None:
        school_class = await classes_repo.get_by_id(session, class_id)
        if school_class is None:
            raise NotFoundError("Класс не найден", "CLASS_NOT_FOUND")
        _check_class_access(user, school_class)

    rows = await students_repo.list_students(
        session,
        school_id=target_school,
        class_id=class_id,
        query=query,
        limit=limit,
        offset=offset,
    )
    return [
        AdminStudentOut(
            user_id=row.user_id,
            full_name=row.full_name,
            email=row.email,
            is_active=row.is_active,
            created_at=row.created_at,
            class_id=row.class_id,
            class_label=row.class_label,
            class_grade=row.class_grade,
            academic_year_name=row.academic_year_name,
        )
        for row in rows
    ]


def _read_rows(content: bytes) -> list[tuple[int, dict[str, str]]]:
    if len(content) > MAX_IMPORT_BYTES:
        raise ValidationError("Файл больше 1 МБ", "IMPORT_FILE_TOO_LARGE")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("CSV должен быть в кодировке UTF-8", "IMPORT_BAD_ENCODING") from exc

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValidationError("Не удалось прочитать заголовок CSV", "IMPORT_NO_HEADER")
    headers = [name.strip().lower() for name in reader.fieldnames]
    missing = [name for name in REQUIRED_COLUMNS if name not in headers]
    if missing:
        raise ValidationError(
            "В CSV не хватает колонок: " + ", ".join(missing), "IMPORT_MISSING_COLUMNS"
        )

    rows: list[tuple[int, dict[str, str]]] = []
    for index, raw in enumerate(reader, start=2):
        normalized = {
            (key or "").strip().lower(): (value or "").strip()
            for key, value in raw.items()
            if key is not None
        }
        if not any(normalized.values()):
            continue
        rows.append((index, normalized))
    if len(rows) > MAX_IMPORT_ROWS:
        raise ValidationError(
            f"За один раз можно импортировать не больше {MAX_IMPORT_ROWS} учеников",
            "IMPORT_TOO_MANY_ROWS",
        )
    return rows


def _validate_email(value: str) -> str:
    email = value.strip()
    if not email or len(email) > 254:
        raise ValueError("Некорректный email")
    try:
        return _email_adapter.validate_python(email)
    except PydanticValidationError as exc:
        raise ValueError("Некорректный email") from exc


async def import_students(
    session: AsyncSession,
    user: User,
    *,
    class_id: uuid.UUID,
    content: bytes,
) -> StudentImportResult:
    school_class = await classes_repo.get_by_id(session, class_id)
    if school_class is None:
        raise NotFoundError("Класс не найден", "CLASS_NOT_FOUND")
    _check_class_access(user, school_class)

    rows = _read_rows(content)
    created: list[ImportedStudentOut] = []
    skipped: list[ImportSkipOut] = []

    pending: list[tuple[int, str, str, str]] = []
    for row_number, row in rows:
        full_name = row.get("full_name", "").strip()
        raw_email = row.get("email", "").strip()
        if not full_name:
            skipped.append(
                ImportSkipOut(row=row_number, email=raw_email or None, reason="Не указано ФИО")
            )
            continue
        if len(full_name) > 300:
            skipped.append(
                ImportSkipOut(row=row_number, email=raw_email or None, reason="ФИО слишком длинное")
            )
            continue
        try:
            email = _validate_email(raw_email)
        except ValueError as exc:
            skipped.append(ImportSkipOut(row=row_number, email=raw_email or None, reason=str(exc)))
            continue
        pending.append((row_number, full_name, email, raw_email))

    existing = await students_repo.existing_emails(session, [email for _, _, email, _ in pending])
    seen: set[str] = set()

    for row_number, full_name, email, raw_email in pending:
        key = email.lower()
        if key in existing or key in seen:
            skipped.append(
                ImportSkipOut(
                    row=row_number,
                    email=raw_email or None,
                    reason="Email уже есть в системе",
                )
            )
            continue
        seen.add(key)

        temp_password = secrets.token_urlsafe(9)
        student = User(
            school_id=school_class.school_id,
            role=UserRole.STUDENT,
            email=email,
            password_hash=hash_password(temp_password),
            full_name=full_name,
            must_change_password=True,
        )
        session.add(student)
        await session.flush()
        session.add(StudentProfile(user_id=student.id, class_id=school_class.id))
        created.append(
            ImportedStudentOut(
                user_id=student.id,
                full_name=full_name,
                email=email,
                temp_password=temp_password,
            )
        )

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Не удалось импортировать учеников", "STUDENT_IMPORT_CONFLICT") from exc

    return StudentImportResult(
        created=created,
        skipped=skipped,
        created_count=len(created),
        skipped_count=len(skipped),
    )
