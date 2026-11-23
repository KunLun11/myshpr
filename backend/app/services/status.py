"""Deterministic traffic-light status for the teacher dashboard.

The dashboard must explain *why* a student is red or yellow, never rely on
colour alone. This module is pure: it receives pre-aggregated metrics and
returns a colour plus human-readable reason codes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.models.enums import ProjectStatus, status_rank

if TYPE_CHECKING:
    from app.models import Checkpoint, Project


class TrafficLight(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass(frozen=True, slots=True)
class StatusReason:
    code: str
    label: str
    severity: TrafficLight


@dataclass(slots=True)
class StatusContext:
    now: datetime
    year_starts_on: date
    checkpoints: list[Checkpoint] = field(default_factory=list)
    inactive_days: float | None = None
    checklist_overdue: int = 0
    checklist_stalled: bool = False
    has_final_file: bool = True
    review_waiting_since: datetime | None = None


@dataclass(slots=True)
class StatusResult:
    color: TrafficLight
    reasons: list[StatusReason]
    next_checkpoint: Checkpoint | None = None


def _reason(code: str, label: str, severity: TrafficLight) -> StatusReason:
    return StatusReason(code=code, label=label, severity=severity)


def _plural_days(days: int) -> str:
    if days % 10 == 1 and days % 100 != 11:
        return f"{days} день"
    if days % 10 in (2, 3, 4) and days % 100 not in (12, 13, 14):
        return f"{days} дня"
    return f"{days} дней"


def evaluate(project: Project | None, ctx: StatusContext) -> StatusResult:
    """Compute the colour, reasons and the next unmet checkpoint."""
    settings = get_settings()

    if project is None:
        if ctx.now.date() >= ctx.year_starts_on:
            return StatusResult(
                color=TrafficLight.RED,
                reasons=[_reason("NO_PROJECT", "Проект не создан", TrafficLight.RED)],
            )
        return StatusResult(
            color=TrafficLight.GREEN,
            reasons=[_reason("YEAR_NOT_STARTED", "Учебный год ещё не начался", TrafficLight.GREEN)],
        )

    red: list[StatusReason] = []
    yellow: list[StatusReason] = []
    rank = status_rank(project.status)

    # --- Control points ----------------------------------------------------
    unmet = sorted(
        (
            checkpoint
            for checkpoint in ctx.checkpoints
            if status_rank(checkpoint.required_status) > rank
        ),
        key=lambda checkpoint: checkpoint.due_at,
    )
    next_checkpoint = unmet[0] if unmet else None

    overdue = [checkpoint for checkpoint in unmet if checkpoint.due_at < ctx.now]
    if overdue:
        first = overdue[0]
        red.append(
            _reason(
                "CHECKPOINT_OVERDUE",
                f"Просрочена контрольная точка «{first.title}»",
                TrafficLight.RED,
            )
        )
    elif next_checkpoint is not None:
        days_left = max((next_checkpoint.due_at.date() - ctx.now.date()).days, 0)
        if days_left <= settings.CHECKPOINT_SOON_DAYS:
            yellow.append(
                _reason(
                    "CHECKPOINT_SOON",
                    f"Контрольная точка «{next_checkpoint.title}» через {_plural_days(days_left)}",
                    TrafficLight.YELLOW,
                )
            )

    # --- Activity ----------------------------------------------------------
    if ctx.inactive_days is not None:
        if ctx.inactive_days >= settings.INACTIVITY_RED_DAYS:
            red.append(
                _reason(
                    "NO_ACTIVITY_14D",
                    f"Нет активности {_plural_days(int(ctx.inactive_days))}",
                    TrafficLight.RED,
                )
            )
        elif ctx.inactive_days >= settings.INACTIVITY_YELLOW_DAYS:
            yellow.append(
                _reason(
                    "NO_ACTIVITY_7D",
                    f"Нет активности {_plural_days(int(ctx.inactive_days))}",
                    TrafficLight.YELLOW,
                )
            )

    # --- Checklist ---------------------------------------------------------
    if ctx.checklist_overdue > 0:
        red.append(
            _reason(
                "CHECKLIST_OVERDUE",
                f"Просрочено обязательных пунктов чек-листа: {ctx.checklist_overdue}",
                TrafficLight.RED,
            )
        )
    if ctx.checklist_stalled:
        yellow.append(
            _reason(
                "CHECKLIST_STALLED",
                f"Обязательный пункт в работе дольше {settings.CHECKLIST_STALLED_DAYS} дней",
                TrafficLight.YELLOW,
            )
        )

    # --- Final work file before defence ------------------------------------
    if not ctx.has_final_file:
        ready_point = next(
            (
                checkpoint
                for checkpoint in ctx.checkpoints
                if checkpoint.required_status is ProjectStatus.READY_FOR_DEFENSE
            ),
            None,
        )
        if ready_point is not None:
            days_left = (ready_point.due_at.date() - ctx.now.date()).days
            if days_left <= settings.FINAL_FILE_DAYS_BEFORE:
                yellow.append(
                    _reason(
                        "NO_FINAL_FILE",
                        f"Нет итогового файла, до защиты {_plural_days(max(days_left, 0))}",
                        TrafficLight.YELLOW,
                    )
                )

    # --- Review queue ------------------------------------------------------
    if (
        project.status is ProjectStatus.TOPIC_SUBMITTED
        and ctx.review_waiting_since is not None
        and (ctx.now - ctx.review_waiting_since).days >= settings.REVIEW_WAIT_DAYS
    ):
        yellow.append(
            _reason(
                "REVIEW_WAITING",
                "Тема давно ждёт решения учителя",
                TrafficLight.YELLOW,
            )
        )

    reasons = red + yellow
    if red:
        color = TrafficLight.RED
    elif yellow:
        color = TrafficLight.YELLOW
    else:
        color = TrafficLight.GREEN
        reasons = [_reason("ON_TRACK", "Всё по плану: активность есть, просрочек нет", color)]

    return StatusResult(color=color, reasons=reasons, next_checkpoint=next_checkpoint)
