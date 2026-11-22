"""Domain enums and the project status rank mapping.

Enum *values* (not member names) are what gets stored in Postgres via the
shared ``SAEnum`` singletons below. Reusing a single ``SAEnum`` instance per
type prevents Alembic from creating duplicate enum types.
"""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def _enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class UserRole(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    SCHOOL_ADMIN = "school_admin"
    SUPER_ADMIN = "super_admin"


class ProjectStatus(StrEnum):
    IDEA = "idea"
    TOPIC_DRAFT = "topic_draft"
    TOPIC_SUBMITTED = "topic_submitted"
    TOPIC_APPROVED = "topic_approved"
    PRODUCT_DRAFT = "product_draft"
    PRODUCT_DEFINED = "product_defined"
    IN_PROGRESS = "in_progress"
    READY_FOR_DEFENSE = "ready_for_defense"
    DEFENDED = "defended"
    ARCHIVED = "archived"


PROJECT_STATUS_RANK: dict[ProjectStatus, int] = {
    ProjectStatus.IDEA: 10,
    ProjectStatus.TOPIC_DRAFT: 20,
    ProjectStatus.TOPIC_SUBMITTED: 30,
    ProjectStatus.TOPIC_APPROVED: 40,
    ProjectStatus.PRODUCT_DRAFT: 50,
    ProjectStatus.PRODUCT_DEFINED: 60,
    ProjectStatus.IN_PROGRESS: 70,
    ProjectStatus.READY_FOR_DEFENSE: 80,
    ProjectStatus.DEFENDED: 90,
}


def status_rank(status: ProjectStatus) -> int:
    return PROJECT_STATUS_RANK.get(status, 0)


class TopicSubmissionStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class TopicStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class CheckpointAudience(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    BOTH = "both"


class NotificationType(StrEnum):
    TOPIC_DECISION = "topic_decision"
    TOPIC_REVIEW = "topic_review"
    CHECKPOINT_DUE = "checkpoint_due"
    INACTIVITY = "inactivity"
    TEACHER_DIGEST = "teacher_digest"
    NEW_COMMENT = "new_comment"
    CHECKLIST_DUE = "checklist_due"


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class FileKind(StrEnum):
    RESEARCH_DRAFT = "research_draft"
    FINAL_WORK = "final_work"
    PRESENTATION = "presentation"
    PRODUCT_MEDIA = "product_media"
    OTHER = "other"


class FileStatus(StrEnum):
    UPLOADED = "uploaded"
    AVAILABLE = "available"
    QUARANTINED = "quarantined"
    DELETED = "deleted"


class CommentVisibility(StrEnum):
    STUDENT_VISIBLE = "student_visible"
    TEACHERS_ONLY = "teachers_only"


class ChecklistState(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    VERIFIED = "verified"
    SKIPPED = "skipped"


def _make_enum(enum_cls: type[StrEnum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=_enum_values,
        validate_strings=True,
        create_type=True,
    )


USER_ROLE_ENUM = _make_enum(UserRole, "user_role")
PROJECT_STATUS_ENUM = _make_enum(ProjectStatus, "project_status")
TOPIC_SUBMISSION_STATUS_ENUM = _make_enum(TopicSubmissionStatus, "topic_submission_status")
TOPIC_STATUS_ENUM = _make_enum(TopicStatus, "topic_status")
CHECKPOINT_AUDIENCE_ENUM = _make_enum(CheckpointAudience, "checkpoint_audience")
NOTIFICATION_TYPE_ENUM = _make_enum(NotificationType, "notification_type")
NOTIFICATION_CHANNEL_ENUM = _make_enum(NotificationChannel, "notification_channel")
NOTIFICATION_STATUS_ENUM = _make_enum(NotificationStatus, "notification_status")
FILE_KIND_ENUM = _make_enum(FileKind, "file_kind")
FILE_STATUS_ENUM = _make_enum(FileStatus, "file_status")
COMMENT_VISIBILITY_ENUM = _make_enum(CommentVisibility, "comment_visibility")
CHECKLIST_STATE_ENUM = _make_enum(ChecklistState, "checklist_state")
