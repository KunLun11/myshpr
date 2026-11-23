"""Class and invite business rules."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models import AcademicYear, ClassInvite, SchoolClass, User
from app.models.enums import UserRole
from app.repositories import classes as classes_repo
from app.repositories.classes import ClassRow
from app.schemas.classes import ClassOut, InviteCreateRequest, InviteOut, TeacherStudentOut

# No 0/O/1/I to keep codes easy to dictate in a classroom.
INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
INVITE_CODE_LENGTH = 8
INVITE_MAX_DAYS = 90


def serialize_class(row: ClassRow) -> ClassOut:
    return ClassOut(
        id=row.school_class.id,
        grade=row.school_class.grade,
        label=row.school_class.label,
        academic_year_id=row.school_class.academic_year_id,
        academic_year_name=row.academic_year_name,
        curator_id=row.school_class.curator_id,
        students_count=row.students_count,
    )


async def list_teacher_students(
    session: AsyncSession, teacher_id: uuid.UUID
) -> list[TeacherStudentOut]:
    rows = await classes_repo.list_teacher_students(session, teacher_id)
    return [
        TeacherStudentOut(
            user_id=row.user_id,
            full_name=row.full_name,
            email=row.email,
            class_id=row.class_id,
            class_label=row.class_label,
            class_grade=row.class_grade,
            academic_year_name=row.academic_year_name,
            project_id=row.project_id,
            project_status=row.project_status,
        )
        for row in rows
    ]


async def create_class(
    session: AsyncSession,
    *,
    school_id: uuid.UUID,
    grade: int,
    label: str,
    academic_year_id: uuid.UUID | None,
    curator_id: uuid.UUID | None,
) -> ClassOut:
    year: AcademicYear | None
    if academic_year_id is None:
        year = await classes_repo.get_current_year(session, school_id)
        if year is None:
            raise ValidationError(
                "У школы не настроен текущий учебный год", "NO_CURRENT_ACADEMIC_YEAR"
            )
    else:
        year = await session.get(AcademicYear, academic_year_id)
        if year is None or year.school_id != school_id:
            raise ValidationError("Учебный год не найден в этой школе", "INVALID_ACADEMIC_YEAR")

    if curator_id is not None:
        curator = await session.get(User, curator_id)
        if (
            curator is None
            or curator.school_id != school_id
            or curator.deleted_at is not None
            or curator.role not in (UserRole.TEACHER, UserRole.SCHOOL_ADMIN)
        ):
            raise ValidationError("Куратор не найден в этой школе", "INVALID_CURATOR")

    school_class = SchoolClass(
        school_id=school_id,
        academic_year_id=year.id,
        grade=grade,
        label=label.strip(),
        curator_id=curator_id,
    )
    session.add(school_class)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Класс с таким названием уже существует", "CLASS_ALREADY_EXISTS"
        ) from exc

    row = await classes_repo.get_class_row(session, school_class.id)
    if row is None:  # pragma: no cover - just created
        raise NotFoundError("Класс не найден", "CLASS_NOT_FOUND")
    return serialize_class(row)


async def get_class(session: AsyncSession, class_id: uuid.UUID) -> ClassOut:
    row = await classes_repo.get_class_row(session, class_id)
    if row is None:
        raise NotFoundError("Класс не найден", "CLASS_NOT_FOUND")
    return serialize_class(row)


def _generate_code() -> str:
    return "".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))


async def _unique_code(session: AsyncSession) -> str:
    for _ in range(10):
        code = _generate_code()
        if not await classes_repo.code_exists(session, code):
            return code
    raise ConflictError("Не удалось создать код приглашения", "INVITE_CODE_CONFLICT")


async def create_invite(
    session: AsyncSession,
    *,
    school_class: SchoolClass,
    created_by: uuid.UUID,
    payload: InviteCreateRequest,
) -> InviteOut:
    max_uses = payload.max_uses
    if max_uses is None:
        # Default to the current class size; unlimited when the class is empty.
        size = await classes_repo.count_students(session, school_class.id)
        max_uses = size if size > 0 else None

    expires_in_days = min(payload.expires_in_days, INVITE_MAX_DAYS)
    invite = ClassInvite(
        class_id=school_class.id,
        code=await _unique_code(session),
        created_by=created_by,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
        max_uses=max_uses,
        uses_count=0,
    )
    session.add(invite)
    await session.commit()
    return serialize_invite(invite)


async def revoke_invite(session: AsyncSession, invite: ClassInvite) -> None:
    if invite.revoked_at is None:
        invite.revoked_at = datetime.now(UTC)
        await session.commit()


def serialize_invite(invite: ClassInvite) -> InviteOut:
    return InviteOut(
        id=invite.id,
        code=invite.code,
        expires_at=invite.expires_at,
        max_uses=invite.max_uses,
        uses_count=invite.uses_count,
        register_url=f"/register?code={invite.code}",
    )
