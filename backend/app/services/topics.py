"""Student topic wizard and teacher review business rules."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models import Project, SchoolClass, TopicSubmission, User
from app.models.enums import NotificationType, ProjectStatus, TopicSubmissionStatus, UserRole
from app.repositories import classes as classes_repo
from app.repositories import notifications as notifications_repo
from app.repositories import projects as projects_repo
from app.repositories import reference as reference_repo
from app.repositories import topics as topics_repo
from app.repositories.projects import ProjectRow
from app.repositories.topics import SubmissionRow
from app.schemas.projects import (
    CheckMessage,
    InterestAreaBrief,
    ProjectOut,
    ProjectPatchRequest,
    ProjectPatchResponse,
    TopicDraftOut,
)
from app.schemas.topic import (
    RegistryTopicOut,
    SubmissionOut,
    TopicCheckOut,
    TopicCheckRequest,
    TopicSubmitRequest,
)
from app.services import checkpoints as checkpoints_service
from app.services import topic_check

SUBMITTABLE_PROJECT_STATUSES = (
    ProjectStatus.IDEA,
    ProjectStatus.TOPIC_DRAFT,
    ProjectStatus.TOPIC_SUBMITTED,
)


async def _student_context(session: AsyncSession, student: User) -> tuple[SchoolClass]:
    profile = await classes_repo.get_student_profile(session, student.id)
    if profile is None:
        raise ValidationError("Вы не привязаны к классу. Обратитесь к учителю.", "STUDENT_NO_CLASS")
    school_class = await classes_repo.get_by_id(session, profile.class_id)
    if school_class is None:
        raise ValidationError("Класс не найден. Обратитесь к учителю.", "STUDENT_NO_CLASS")
    return (school_class,)


async def _get_or_create_project(
    session: AsyncSession, student: User, school_class: SchoolClass
) -> Project:
    project = await projects_repo.get_student_project(
        session, student_id=student.id, academic_year_id=school_class.academic_year_id
    )
    if project is not None:
        return project

    project = await projects_repo.create(
        session,
        student_id=student.id,
        academic_year_id=school_class.academic_year_id,
        class_id=school_class.id,
    )
    await projects_repo.add_event(
        session, project_id=project.id, event_type="project_created", actor_id=student.id
    )
    return project


async def _load_project(session: AsyncSession, student: User) -> tuple[Project, SchoolClass]:
    (school_class,) = await _student_context(session, student)
    project = await projects_repo.get_student_project(
        session, student_id=student.id, academic_year_id=school_class.academic_year_id
    )
    if project is None:
        raise NotFoundError("Проект ещё не создан", "PROJECT_NOT_FOUND")
    return project, school_class


def _interest_brief(row: ProjectRow) -> InterestAreaBrief | None:
    project = row.project
    if project.interest_area_id is None or row.interest_area_name is None:
        return None
    return InterestAreaBrief(
        id=project.interest_area_id,
        slug=row.interest_area_slug or "",
        name=row.interest_area_name,
    )


def _topic_draft(submission: TopicSubmission | None) -> TopicDraftOut | None:
    if submission is None:
        return None
    return TopicDraftOut(
        id=submission.id,
        status=submission.status.value,
        title=submission.title,
        normalized_title=submission.normalized_title,
        research_question=submission.research_question,
        duplicate_score=float(submission.duplicate_score)
        if submission.duplicate_score is not None
        else None,
        broadness_score=submission.broadness_score,
        broadness_reasons=list(submission.broadness_reasons or []),
        review_comment=submission.review_comment,
        reviewed_at=submission.reviewed_at,
        updated_at=submission.updated_at,
    )


def serialize_project(
    row: ProjectRow,
    submission: TopicSubmission | None,
    *,
    next_checkpoint=None,
) -> ProjectOut:
    project = row.project
    return ProjectOut(
        id=project.id,
        status=project.status.value,
        class_id=project.class_id,
        class_label=row.class_label,
        class_grade=row.class_grade,
        academic_year_id=project.academic_year_id,
        academic_year_name=row.academic_year_name,
        interest_area=_interest_brief(row),
        research_question=project.research_question,
        topic_approved_at=project.topic_approved_at,
        product_defined_at=project.product_defined_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
        topic=_topic_draft(submission),
        next_checkpoint=next_checkpoint,
    )


async def get_my_project(session: AsyncSession, student: User) -> ProjectOut | None:
    (school_class,) = await _student_context(session, student)
    project = await projects_repo.get_student_project(
        session, student_id=student.id, academic_year_id=school_class.academic_year_id
    )
    if project is None:
        return None
    row = await projects_repo.get_row(session, project.id)
    if row is None:  # pragma: no cover - just loaded it
        raise NotFoundError("Проект не найден", "PROJECT_NOT_FOUND")
    submission = await topics_repo.get_latest_for_project(session, project.id)
    next_checkpoint = await checkpoints_service.next_for_project(
        session, project, school_id=school_class.school_id
    )
    return serialize_project(row, submission, next_checkpoint=next_checkpoint)


async def _save_draft(
    session: AsyncSession,
    *,
    student: User,
    project: Project,
    school_class: SchoolClass,
    title: str | None,
    research_question: str | None,
    warnings: list[CheckMessage],
) -> None:
    active = await topics_repo.get_active_for_project(session, project.id)
    if active is not None and active.status is TopicSubmissionStatus.SUBMITTED:
        if title is not None and topic_check.normalize_title(title) != active.normalized_title:
            raise ConflictError(
                "Тема уже на проверке — дождитесь решения учителя.", "TOPIC_UNDER_REVIEW"
            )
        return

    if title is not None:
        for finding in topic_check.validate_title(title, interest_area_name=None):
            warnings.append(finding)

    values: dict = {}
    if title is not None:
        values["title"] = title.strip()
        values["normalized_title"] = topic_check.normalize_title(title)
    if research_question is not None:
        values["research_question"] = research_question
    if project.interest_area_id is not None:
        values["interest_area_id"] = project.interest_area_id

    if not values:
        return

    if active is not None:
        values.pop("interest_area_id", None)
        await topics_repo.update_submission(
            session,
            active.id,
            values=values,
            expected_statuses=(TopicSubmissionStatus.DRAFT,),
        )
        return

    question = values.get("research_question") or project.research_question or ""
    if not title:
        return
    await topics_repo.create_submission(
        session,
        project_id=project.id,
        school_id=school_class.school_id,
        academic_year_id=school_class.academic_year_id,
        author_student_id=student.id,
        interest_area_id=project.interest_area_id,
        research_question=question,
        title=title.strip(),
        normalized_title=topic_check.normalize_title(title),
        status=TopicSubmissionStatus.DRAFT,
    )


async def update_my_project(
    session: AsyncSession, student: User, payload: ProjectPatchRequest
) -> ProjectPatchResponse:
    (school_class,) = await _student_context(session, student)
    project = await _get_or_create_project(session, student, school_class)
    fields = payload.model_fields_set
    warnings: list[CheckMessage] = []
    changed = False

    if "interest_area_id" in fields:
        area_id = payload.interest_area_id
        if area_id is None:
            project.interest_area_id = None
        else:
            area = await reference_repo.get_interest_area(session, area_id)
            if area is None or not area.is_active:
                raise ValidationError("Сфера интересов не найдена", "INVALID_INTEREST_AREA")
            project.interest_area_id = area.id
        changed = True
        await projects_repo.add_event(
            session,
            project_id=project.id,
            event_type="interest_area_selected",
            actor_id=student.id,
            payload={"interest_area_id": str(area_id) if area_id else None},
        )

    if "research_question" in fields:
        question = payload.research_question
        project.research_question = question.strip() if question and question.strip() else None
        if project.research_question:
            question_errors, question_warnings = topic_check.validate_research_question(
                project.research_question
            )
            warnings.extend(question_errors)
            warnings.extend(question_warnings)
        changed = True
        await projects_repo.add_event(
            session,
            project_id=project.id,
            event_type="research_question_saved",
            actor_id=student.id,
        )

    title = payload.topic_title if "topic_title" in fields else None
    if title is not None:
        changed = True
        await _save_draft(
            session,
            student=student,
            project=project,
            school_class=school_class,
            title=title,
            research_question=project.research_question,
            warnings=warnings,
        )

    now = datetime.now(UTC)
    if changed:
        project.last_activity_at = now
        if project.status is ProjectStatus.IDEA:
            project.status = ProjectStatus.TOPIC_DRAFT

    await session.commit()

    row = await projects_repo.get_row(session, project.id)
    if row is None:  # pragma: no cover
        raise NotFoundError("Проект не найден", "PROJECT_NOT_FOUND")
    submission = await topics_repo.get_latest_for_project(session, project.id)
    next_checkpoint = await checkpoints_service.next_for_project(
        session, project, school_id=school_class.school_id
    )
    return ProjectPatchResponse(
        project=serialize_project(row, submission, next_checkpoint=next_checkpoint),
        warnings=warnings,
    )


async def check_my_topic(
    session: AsyncSession, student: User, payload: TopicCheckRequest
) -> TopicCheckOut:
    (school_class,) = await _student_context(session, student)
    project = await projects_repo.get_student_project(
        session, student_id=student.id, academic_year_id=school_class.academic_year_id
    )
    interest_area_name = None
    exclude_id = None
    if project is not None:
        if project.interest_area_id is not None:
            area = await reference_repo.get_interest_area(session, project.interest_area_id)
            interest_area_name = area.name if area else None
        active = await topics_repo.get_active_for_project(session, project.id)
        if active is not None:
            exclude_id = active.id

    question = payload.research_question
    if question is None and project is not None:
        question = project.research_question

    return await topic_check.run_checks(
        session,
        school_id=school_class.school_id,
        academic_year_id=school_class.academic_year_id,
        title=payload.title,
        research_question=question,
        interest_area_name=interest_area_name,
        exclude_submission_id=exclude_id,
    )


async def submit_my_topic(
    session: AsyncSession, student: User, payload: TopicSubmitRequest
) -> ProjectOut:
    project, school_class = await _load_project(session, student)
    draft = await topics_repo.get_active_for_project(session, project.id)
    if draft is not None and draft.status is TopicSubmissionStatus.SUBMITTED:
        raise ConflictError("Тема уже отправлена на проверку.", "TOPIC_ALREADY_SUBMITTED")

    title = (payload.title or (draft.title if draft else "") or "").strip()
    question = (
        payload.research_question
        or (draft.research_question if draft else None)
        or project.research_question
        or ""
    ).strip()

    if project.interest_area_id is None:
        raise ValidationError("Сначала выберите сферу интересов.", "TOPIC_INCOMPLETE")
    if not title:
        raise ValidationError("Добавьте формулировку темы.", "TOPIC_INCOMPLETE")
    if not question:
        raise ValidationError("Добавьте исследовательский вопрос.", "TOPIC_INCOMPLETE")

    area = await reference_repo.get_interest_area(session, project.interest_area_id)
    check = await topic_check.run_checks(
        session,
        school_id=school_class.school_id,
        academic_year_id=school_class.academic_year_id,
        title=title,
        research_question=question,
        interest_area_name=area.name if area else None,
        exclude_submission_id=draft.id if draft else None,
    )

    if check.errors:
        raise ValidationError(
            "Проверьте формулировку темы и вопроса.",
            "TOPIC_INVALID",
            errors=[finding.model_dump() for finding in check.errors],
        )
    if check.duplicate.level == "block":
        raise ValidationError(
            "Такая тема уже есть в реестре или слишком похожа на другую.",
            "TOPIC_DUPLICATE",
            errors=[
                {
                    "field": "topic_title",
                    "message": "Измените формулировку: она повторяет существующую тему.",
                }
            ],
        )
    if check.broadness.level == "block":
        raise ValidationError(
            "Тема слишком широкая: добавьте объект, место, период или метод.",
            "TOPIC_TOO_BROAD",
            errors=[
                {"field": "topic_title", "message": reason} for reason in check.broadness.reasons
            ]
            or [{"field": "topic_title", "message": "Сузьте тему."}],
        )

    registry_match = next(
        (match for match in check.duplicate.matches if match.source == "registry"), None
    )
    values = {
        "title": title,
        "normalized_title": check.normalized_title,
        "research_question": question,
        "interest_area_id": project.interest_area_id,
        "status": TopicSubmissionStatus.SUBMITTED,
        "duplicate_score": check.duplicate.best_score or None,
        "duplicate_of_topic_id": registry_match.id if registry_match else None,
        "broadness_score": check.broadness.score,
        "broadness_reasons": list(check.broadness.reasons),
        "review_comment": None,
        "reviewed_by": None,
        "reviewed_at": None,
    }

    if draft is not None:
        updated = await topics_repo.update_submission(
            session,
            draft.id,
            values=values,
            expected_statuses=(TopicSubmissionStatus.DRAFT,),
        )
        if not updated:
            raise ConflictError("Заявка уже изменилась, обновите страницу.", "SUBMISSION_CHANGED")
        submission_id = draft.id
    else:
        created = await topics_repo.create_submission(
            session,
            project_id=project.id,
            school_id=school_class.school_id,
            academic_year_id=school_class.academic_year_id,
            author_student_id=student.id,
            interest_area_id=project.interest_area_id,
            research_question=question,
            title=title,
            normalized_title=check.normalized_title,
            status=TopicSubmissionStatus.SUBMITTED,
        )
        submission_id = created.id
        await topics_repo.update_submission(session, submission_id, values=values)

    updated = await projects_repo.update_fields(
        session,
        project.id,
        values={
            "status": ProjectStatus.TOPIC_SUBMITTED,
            "last_activity_at": datetime.now(UTC),
        },
        expected_statuses=SUBMITTABLE_PROJECT_STATUSES,
    )
    if not updated:
        raise ConflictError(
            "Статус проекта изменился, обновите страницу.", "PROJECT_STATUS_CHANGED"
        )

    await projects_repo.add_event(
        session,
        project_id=project.id,
        event_type="topic_submitted",
        actor_id=student.id,
        payload={"submission_id": str(submission_id), "title": title},
    )

    if school_class.curator_id is not None:
        await notifications_repo.create_in_app(
            session,
            user_id=school_class.curator_id,
            type=NotificationType.TOPIC_REVIEW,
            title="Новая тема на проверку",
            body=f"{student.full_name}: «{title}»",
            dedupe_key=f"topic_review:{submission_id}",
            project_id=project.id,
            payload={"submission_id": str(submission_id)},
        )

    await session.commit()
    return await get_my_project(session, student)


def serialize_submission(row: SubmissionRow) -> SubmissionOut:
    submission = row.submission
    duplicate_level = topic_check.duplicate_level_for_stored_score(
        float(submission.duplicate_score) if submission.duplicate_score is not None else None
    )
    broadness_level = topic_check.broadness_level_for_stored_score(submission.broadness_score)
    return SubmissionOut(
        id=submission.id,
        project_id=row.project_id,
        status=submission.status.value,
        title=submission.title,
        research_question=submission.research_question,
        student_full_name=row.student_full_name,
        class_label=row.class_label,
        interest_area_name=row.interest_area_name,
        submitted_at=submission.updated_at,
        duplicate_score=float(submission.duplicate_score)
        if submission.duplicate_score is not None
        else None,
        duplicate_level=duplicate_level,
        duplicate_of_title=row.duplicate_of_title,
        broadness_score=submission.broadness_score,
        broadness_level=broadness_level,
        broadness_reasons=list(submission.broadness_reasons or []),
        review_comment=submission.review_comment,
        reviewed_at=submission.reviewed_at,
    )


async def list_teacher_submissions(
    session: AsyncSession,
    teacher: User,
    *,
    status: str = "submitted",
    limit: int = 50,
    offset: int = 0,
) -> list[SubmissionOut]:
    try:
        status_enum = TopicSubmissionStatus(status)
    except ValueError as exc:
        raise ValidationError("Неизвестный статус заявки", "INVALID_STATUS") from exc
    rows = await topics_repo.list_teacher_submissions(
        session, teacher_id=teacher.id, status=status_enum, limit=limit, offset=offset
    )
    return [serialize_submission(row) for row in rows]


async def _load_reviewable(
    session: AsyncSession, teacher: User, submission_id: uuid.UUID
) -> SubmissionRow:
    row = await topics_repo.get_row(session, submission_id)
    if row is None:
        raise NotFoundError("Заявка не найдена", "SUBMISSION_NOT_FOUND")

    school_class = await classes_repo.get_by_id(session, row.class_id)
    if school_class is None:
        raise NotFoundError("Класс не найден", "CLASS_NOT_FOUND")

    if teacher.role is not UserRole.SUPER_ADMIN and school_class.curator_id != teacher.id:
        raise ForbiddenError("Эта заявка не из ваших классов", "SUBMISSION_ACCESS_DENIED")
    if row.student_id == teacher.id:
        raise ForbiddenError("Нельзя проверять свою собственную тему", "REVIEW_OWN_TOPIC")
    if row.submission.status is not TopicSubmissionStatus.SUBMITTED:
        raise ConflictError("Заявка уже обработана", "SUBMISSION_NOT_SUBMITTED")
    return row


async def approve_submission(
    session: AsyncSession,
    teacher: User,
    submission_id: uuid.UUID,
    *,
    comment: str | None,
) -> SubmissionOut:
    row = await _load_reviewable(session, teacher, submission_id)
    submission = row.submission
    duplicate_level = topic_check.duplicate_level_for_stored_score(
        float(submission.duplicate_score) if submission.duplicate_score is not None else None
    )
    broadness_level = topic_check.broadness_level_for_stored_score(submission.broadness_score)

    if duplicate_level == "block":
        raise ValidationError(
            "Тема повторяет существующую — утвердить её нельзя.", "TOPIC_DUPLICATE"
        )

    needs_comment = duplicate_level == "warn" or broadness_level != "ok"
    cleaned_comment = (comment or "").strip()
    if needs_comment and len(cleaned_comment) < 3:
        raise ValidationError(
            "Проверка нашла замечания — добавьте комментарий для ученика.",
            "REVIEW_COMMENT_REQUIRED",
            errors=[
                {
                    "field": "comment",
                    "message": "Объясните, почему тема утверждается несмотря на предупреждения.",
                }
            ],
        )

    existing = await topics_repo.get_topic_by_title(
        session, school_id=submission.school_id, normalized_title=submission.normalized_title
    )
    if existing is not None:
        raise ConflictError("Такая тема уже есть в реестре", "TOPIC_ALREADY_REGISTERED")

    now = datetime.now(UTC)
    try:
        await topics_repo.create_topic(
            session,
            school_id=submission.school_id,
            academic_year_id=submission.academic_year_id,
            title=submission.title,
            normalized_title=submission.normalized_title,
            research_question=submission.research_question,
            author_student_id=submission.author_student_id,
            source_submission_id=submission.id,
            approved_at=now,
        )
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Такая тема уже есть в реестре", "TOPIC_ALREADY_REGISTERED") from exc

    updated = await topics_repo.update_submission(
        session,
        submission.id,
        values={
            "status": TopicSubmissionStatus.APPROVED,
            "review_comment": cleaned_comment or None,
            "reviewed_by": teacher.id,
            "reviewed_at": now,
        },
        expected_statuses=(TopicSubmissionStatus.SUBMITTED,),
    )
    if not updated:
        raise ConflictError("Заявка уже обработана", "SUBMISSION_NOT_SUBMITTED")

    updated = await projects_repo.update_fields(
        session,
        row.project_id,
        values={
            "status": ProjectStatus.TOPIC_APPROVED,
            "topic_approved_at": now,
            "last_activity_at": now,
        },
        expected_statuses=(ProjectStatus.TOPIC_SUBMITTED,),
    )
    if not updated:
        raise ConflictError(
            "Статус проекта изменился, обновите страницу.", "PROJECT_STATUS_CHANGED"
        )

    await projects_repo.add_event(
        session,
        project_id=row.project_id,
        event_type="topic_approved",
        actor_id=teacher.id,
        payload={"submission_id": str(submission.id)},
    )
    await notifications_repo.create_in_app(
        session,
        user_id=submission.author_student_id,
        type=NotificationType.TOPIC_DECISION,
        title="Тема утверждена",
        body=f"Учитель утвердил тему «{submission.title}».",
        dedupe_key=f"topic_decision:{submission.id}:approved",
        project_id=row.project_id,
        payload={"submission_id": str(submission.id), "decision": "approved"},
    )
    await session.commit()

    refreshed = await topics_repo.get_row(session, submission.id)
    if refreshed is None:  # pragma: no cover
        raise NotFoundError("Заявка не найдена", "SUBMISSION_NOT_FOUND")
    return serialize_submission(refreshed)


async def reject_submission(
    session: AsyncSession,
    teacher: User,
    submission_id: uuid.UUID,
    *,
    comment: str,
) -> SubmissionOut:
    row = await _load_reviewable(session, teacher, submission_id)
    submission = row.submission
    cleaned_comment = comment.strip()
    now = datetime.now(UTC)

    updated = await topics_repo.update_submission(
        session,
        submission.id,
        values={
            "status": TopicSubmissionStatus.REJECTED,
            "review_comment": cleaned_comment,
            "reviewed_by": teacher.id,
            "reviewed_at": now,
        },
        expected_statuses=(TopicSubmissionStatus.SUBMITTED,),
    )
    if not updated:
        raise ConflictError("Заявка уже обработана", "SUBMISSION_NOT_SUBMITTED")

    updated = await projects_repo.update_fields(
        session,
        row.project_id,
        values={"status": ProjectStatus.TOPIC_DRAFT, "last_activity_at": now},
        expected_statuses=(ProjectStatus.TOPIC_SUBMITTED,),
    )
    if not updated:
        raise ConflictError(
            "Статус проекта изменился, обновите страницу.", "PROJECT_STATUS_CHANGED"
        )

    await projects_repo.add_event(
        session,
        project_id=row.project_id,
        event_type="topic_rejected",
        actor_id=teacher.id,
        payload={"submission_id": str(submission.id), "comment": cleaned_comment},
    )
    await notifications_repo.create_in_app(
        session,
        user_id=submission.author_student_id,
        type=NotificationType.TOPIC_DECISION,
        title="Тема отклонена",
        body=cleaned_comment,
        dedupe_key=f"topic_decision:{submission.id}:rejected",
        project_id=row.project_id,
        payload={"submission_id": str(submission.id), "decision": "rejected"},
    )
    await session.commit()

    refreshed = await topics_repo.get_row(session, submission.id)
    if refreshed is None:  # pragma: no cover
        raise NotFoundError("Заявка не найдена", "SUBMISSION_NOT_FOUND")
    return serialize_submission(refreshed)


async def list_registry(
    session: AsyncSession,
    teacher: User,
    *,
    academic_year_id: uuid.UUID | None = None,
    interest_area_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[RegistryTopicOut]:
    rows = await topics_repo.list_registry(
        session,
        teacher_id=teacher.id,
        academic_year_id=academic_year_id,
        interest_area_id=interest_area_id,
        limit=limit,
        offset=offset,
    )
    return [
        RegistryTopicOut(
            id=row.topic.id,
            title=row.topic.title,
            research_question=row.topic.research_question,
            author_full_name=row.author_full_name,
            interest_area_name=row.interest_area_name,
            academic_year_name=row.academic_year_name,
            approved_at=row.topic.approved_at,
        )
        for row in rows
    ]
