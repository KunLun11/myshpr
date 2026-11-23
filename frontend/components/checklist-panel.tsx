"use client";

import {
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  Circle,
  Clock,
  LoaderCircle,
  MinusCircle,
  PlayCircle,
  RotateCcw,
  SkipForward,
} from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type {
  ChecklistItemState,
  ChecklistState,
  ProjectChecklist,
} from "@/types/api";

const STATUS_META: Record<
  ChecklistState,
  { label: string; variant: "success" | "info" | "warning" | "secondary" | "danger"; Icon: typeof Circle }
> = {
  pending: { label: "Не начат", variant: "secondary", Icon: Circle },
  in_progress: { label: "В работе", variant: "info", Icon: Clock },
  done: { label: "Выполнен", variant: "success", Icon: CheckCircle2 },
  verified: { label: "Подтверждён", variant: "success", Icon: BadgeCheck },
  skipped: { label: "Пропущен", variant: "secondary", Icon: MinusCircle },
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Не удалось обновить чек-лист. Проверьте соединение.";
}

export function ChecklistPanel({
  initialChecklist,
  mode,
}: {
  initialChecklist: ProjectChecklist;
  mode: "student" | "teacher";
}) {
  const [checklist, setChecklist] = useState(initialChecklist);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const next = await api.get<ProjectChecklist>(
      mode === "teacher"
        ? `/teacher/projects/${initialChecklist.project_id}/checklist`
        : "/me/project/checklist",
    );
    setChecklist(next);
  }

  async function studentUpdate(item: ChecklistItemState, status: ChecklistState) {
    setPendingId(item.id);
    setError(null);
    try {
      await api.patch<ChecklistItemState>(
        `/me/project/checklist/${item.checklist_item_id}`,
        { status },
      );
      await refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPendingId(null);
    }
  }

  async function staffTransition(item: ChecklistItemState, action: "verify" | "skip") {
    setPendingId(item.id);
    setError(null);
    try {
      await api.post<ChecklistItemState>(
        `/teacher/checklist-states/${item.id}/${action}`,
        { comment: null },
      );
      await refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPendingId(null);
    }
  }

  const { progress, overdue_count } = checklist;
  const totalItems = checklist.stages.reduce((sum, stage) => sum + stage.total_count, 0);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-lg">Прогресс по этапам</CardTitle>
            {overdue_count > 0 ? (
              <Badge variant="warning">
                <AlertTriangle className="mr-1 size-3.5" aria-hidden="true" />
                {overdue_count} просрочено
              </Badge>
            ) : (
              <Badge variant="success">
                <CheckCircle2 className="mr-1 size-3.5" aria-hidden="true" />
                Без просрочек
              </Badge>
            )}
          </div>
          <CardDescription>
            Обязательные пункты: {progress.done} из {progress.required}. Всего пунктов:{" "}
            {totalItems}.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress.percent}
            aria-label="Готовность чек-листа"
            className="h-2.5 w-full overflow-hidden rounded-full bg-[var(--muted)]"
          >
            <div
              className="h-full rounded-full bg-[var(--primary)] transition-[width] duration-300"
              style={{ width: `${progress.percent}%` }}
            />
          </div>
          <p className="mt-2 text-sm text-[var(--muted-foreground)]">
            {progress.percent}% обязательных пунктов закрыто
          </p>
        </CardContent>
      </Card>

      {error ? <Alert>{error}</Alert> : null}

      {checklist.stages.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Чек-лист пока пуст</CardTitle>
            <CardDescription>
              Администратор школы ещё не добавил пункты для этого учебного года.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        checklist.stages.map((stage) => (
          <Card key={stage.stage}>
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="text-base">{stage.title}</CardTitle>
                <Badge variant={stage.required_done === stage.required_total ? "success" : "secondary"}>
                  {stage.done_count} из {stage.total_count}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {stage.items.map((item) => (
                  <li key={item.id}>
                    <ChecklistRow
                      item={item}
                      mode={mode}
                      pending={pendingId === item.id}
                      onStudentUpdate={studentUpdate}
                      onStaffTransition={staffTransition}
                    />
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}

function ChecklistRow({
  item,
  mode,
  pending,
  onStudentUpdate,
  onStaffTransition,
}: {
  item: ChecklistItemState;
  mode: "student" | "teacher";
  pending: boolean;
  onStudentUpdate: (item: ChecklistItemState, status: ChecklistState) => void;
  onStaffTransition: (item: ChecklistItemState, action: "verify" | "skip") => void;
}) {
  const meta = STATUS_META[item.status];
  const Icon = meta.Icon;
  const done = item.status === "done" || item.status === "verified";
  const locked = item.status === "verified" || item.status === "skipped";
  const canAct = mode === "student" ? !locked : !locked;

  return (
    <div className="flex flex-col gap-3 rounded-[var(--radius-md)] border border-[var(--border)] p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        <Icon
          className={
            item.status === "done" || item.status === "verified"
              ? "mt-0.5 size-4 shrink-0 text-[var(--success)]"
              : item.overdue
                ? "mt-0.5 size-4 shrink-0 text-[var(--warning)]"
                : "mt-0.5 size-4 shrink-0 text-[var(--muted-foreground)]"
          }
          aria-hidden="true"
        />
        <div className="min-w-0 space-y-1">
          <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
            {item.title}
            {item.is_required ? (
              <Badge variant="secondary" className="text-[10px]">
                обязательный
              </Badge>
            ) : null}
            {item.overdue ? (
              <Badge variant="warning">
                <AlertTriangle className="mr-1 size-3" aria-hidden="true" />
                просрочен
              </Badge>
            ) : null}
          </p>
          <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted-foreground)]">
            <Badge variant={meta.variant}>{meta.label}</Badge>
            {item.due_at ? <span>до {formatDate(item.due_at)}</span> : null}
            {item.verified_at ? <span>подтверждён {formatDate(item.verified_at)}</span> : null}
          </div>
          {item.description ? (
            <p className="text-sm text-[var(--muted-foreground)]">{item.description}</p>
          ) : null}
          {item.comment ? (
            <p className="text-sm text-[var(--info-soft-foreground)]">
              Комментарий учителя: {item.comment}
            </p>
          ) : null}
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-2">
        {pending ? (
          <LoaderCircle className="size-4 animate-spin text-[var(--muted-foreground)]" aria-hidden="true" />
        ) : null}
        {mode === "student" && canAct && item.status === "pending" ? (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onStudentUpdate(item, "in_progress")}
            disabled={pending}
          >
            <PlayCircle aria-hidden="true" />
            Начать
          </Button>
        ) : null}
        {mode === "student" && canAct ? (
          <Button
            size="sm"
            variant={done ? "outline" : "default"}
            onClick={() => onStudentUpdate(item, done ? "in_progress" : "done")}
            disabled={pending}
          >
            {done ? <RotateCcw aria-hidden="true" /> : <CheckCircle2 aria-hidden="true" />}
            {done ? "Вернуть в работу" : "Готово"}
          </Button>
        ) : null}
        {mode === "teacher" &&
        (item.status === "done" || item.status === "in_progress") ? (
          <Button size="sm" onClick={() => onStaffTransition(item, "verify")} disabled={pending}>
            <BadgeCheck aria-hidden="true" />
            Подтвердить
          </Button>
        ) : null}
        {mode === "teacher" && item.status === "pending" ? (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onStaffTransition(item, "skip")}
            disabled={pending}
          >
            <SkipForward aria-hidden="true" />
            Пропустить
          </Button>
        ) : null}
      </div>
    </div>
  );
}
