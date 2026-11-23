"""Import every model so Alembic's ``target_metadata`` sees them all."""

from app.models.audit import AuditLog
from app.models.checklist import ChecklistItem, ProjectChecklistState
from app.models.comment import ProjectComment
from app.models.enums import (
    ChecklistState,
    CheckpointAudience,
    CommentVisibility,
    FileKind,
    FileStatus,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    ProjectStatus,
    TopicStatus,
    TopicSubmissionStatus,
    UserRole,
)
from app.models.file import ProjectFile
from app.models.notifications import Checkpoint, Notification
from app.models.project import Project, ProjectEvent
from app.models.reference import InterestArea, ProductCategory
from app.models.school import AcademicYear, ClassInvite, School, SchoolClass
from app.models.topic import Topic, TopicSubmission
from app.models.user import RefreshToken, StudentProfile, User

__all__ = [
    "AcademicYear",
    "AuditLog",
    "ChecklistItem",
    "ChecklistState",
    "Checkpoint",
    "CheckpointAudience",
    "ClassInvite",
    "CommentVisibility",
    "FileKind",
    "FileStatus",
    "InterestArea",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "NotificationType",
    "ProductCategory",
    "Project",
    "ProjectChecklistState",
    "ProjectComment",
    "ProjectEvent",
    "ProjectFile",
    "ProjectStatus",
    "RefreshToken",
    "School",
    "SchoolClass",
    "StudentProfile",
    "Topic",
    "TopicStatus",
    "TopicSubmission",
    "TopicSubmissionStatus",
    "User",
    "UserRole",
]
