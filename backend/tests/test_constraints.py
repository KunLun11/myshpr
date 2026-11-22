"""Database constraint tests."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import ProjectFile, Topic, TopicSubmission
from app.models.enums import TopicSubmissionStatus
from tests.factories import (
    create_class,
    create_project,
    create_school,
    create_user,
    create_year,
)


async def _scaffold(session):
    school = await create_school(session)
    year = await create_year(session, school)
    student = await create_user(session, school)
    klass = await create_class(session, school, year)
    return school, year, student, klass


async def test_one_project_per_student_year(session) -> None:
    school, year, student, klass = await _scaffold(session)
    await create_project(session, student, year, klass)
    with pytest.raises(IntegrityError):
        await create_project(session, student, year, klass)


async def test_topic_unique_title_per_school(session) -> None:
    school, year, student, klass = await _scaffold(session)
    now = datetime.now(UTC)
    session.add(
        Topic(
            school_id=school.id,
            academic_year_id=year.id,
            title="Экология двора",
            normalized_title="экология двора",
            approved_at=now,
        )
    )
    await session.flush()
    with pytest.raises(IntegrityError):
        session.add(
            Topic(
                school_id=school.id,
                academic_year_id=year.id,
                title="Экология двора",
                normalized_title="экология двора",
                approved_at=now,
            )
        )
        await session.flush()


async def test_only_one_active_submission_per_project(session) -> None:
    school, year, student, klass = await _scaffold(session)
    project = await create_project(session, student, year, klass)
    session.add(
        TopicSubmission(
            project_id=project.id,
            school_id=school.id,
            academic_year_id=year.id,
            author_student_id=student.id,
            research_question="Как?",
            title="Первая тема",
            normalized_title="первая тема",
            status=TopicSubmissionStatus.SUBMITTED,
        )
    )
    await session.flush()
    with pytest.raises(IntegrityError):
        session.add(
            TopicSubmission(
                project_id=project.id,
                school_id=school.id,
                academic_year_id=year.id,
                author_student_id=student.id,
                research_question="Как?",
                title="Вторая тема",
                normalized_title="вторая тема",
                status=TopicSubmissionStatus.DRAFT,
            )
        )
        await session.flush()


async def test_project_file_size_check(session) -> None:
    school, year, student, klass = await _scaffold(session)
    project = await create_project(session, student, year, klass)
    with pytest.raises(IntegrityError):
        session.add(
            ProjectFile(
                project_id=project.id,
                uploaded_by=student.id,
                original_name="work.pdf",
                storage_key="projects/x/work.pdf",
                mime_type="application/pdf",
                size_bytes=0,
                checksum_sha256="deadbeef",
            )
        )
        await session.flush()
